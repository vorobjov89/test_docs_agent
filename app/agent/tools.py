from pathlib import Path
import json

from langchain.tools import tool

from app.models.contract import ContractChain
from app.services.contract_chain_builder import ContractChainBuilder
from app.services.aggregator import ContractAggregator
from app.services.clusterer import ContractClusterer


PROCESSED_FILE = Path(
    "data/processed/documents.json"
)


def _load_documents() -> list[dict]:
    if not PROCESSED_FILE.exists():
        raise FileNotFoundError(
            f"Не найден файл {PROCESSED_FILE}"
        )

    with PROCESSED_FILE.open(
        "r",
        encoding="utf-8",
    ) as f:
        results = json.load(f)

    return [
        result["data"]
        for result in results
        if result.get("data")
        and result.get("status") in {
            "success",
            "partial",
        }
    ]


def _build_chains() -> list[ContractChain]:
    documents = _load_documents()

    builder = ContractChainBuilder()

    return builder.build(documents)


@tool
def get_extraction_issues(
    contract_ids: str | None = None,
) -> str:
    """
    Показать документы, которые были обработаны частично или отклонены,
    чтобы определить, может ли история договоров быть неполной.

    Если contract_ids не указан, возвращаются проблемы по всем документам.

    Если contract_ids указан через запятую, например:
        "D200262543-01,D220600738-01"

    возвращаются только проблемы документов, относящихся
    к указанным договорным цепочкам.
    """
    if not PROCESSED_FILE.exists():
        raise FileNotFoundError(
            f"Не найден файл {PROCESSED_FILE}"
        )

    with PROCESSED_FILE.open(
        "r",
        encoding="utf-8",
    ) as f:
        results = json.load(f)

    requested_ids = None

    if contract_ids:
        requested_ids = {
            contract_id.strip()
            for contract_id in contract_ids.split(",")
            if contract_id.strip()
        }

    issues = []

    for result in results:
        status = result.get("status")

        if status not in {
            "partial",
            "rejected",
            "error",
        }:
            continue

        data = result.get("data") or {}

        document_id = data.get("document_id")
        document_type = data.get("document_type")
        contract_id = data.get("contract_id")
        referenced_contract_id = data.get(
            "referenced_contract_id"
        )
        subject = data.get("subject")

        # Если переданы конкретные договоры,
        # оставляем только связанные с ними документы.
        if requested_ids is not None:
            related_ids = {
                value
                for value in (
                    contract_id,
                    referenced_contract_id,
                )
                if value
            }

            if not requested_ids.intersection(related_ids):
                continue

        if status == "partial":
            issues.append({
                "filename": result.get("filename"),
                "status": "partial",
                "failed_chunks": result.get(
                    "failed_chunks",
                    [],
                ),
                "contract_id": contract_id,
                "referenced_contract_id": referenced_contract_id,
                "document_id": document_id,
                "document_type": document_type,
                "subject": subject,
            })

        elif status == "rejected":
            issues.append({
                "filename": result.get("filename"),
                "status": "rejected",
                "errors": result.get(
                    "errors",
                    [],
                ),
                "document_id": document_id,
                "document_type": document_type,
                "subject": subject,
                "contract_id": contract_id,
                "referenced_contract_id": referenced_contract_id,
            })

        elif status == "error":
            issues.append({
                "filename": result.get("filename"),
                "status": "error",
                "error": result.get("error"),
                "document_id": document_id,
                "document_type": document_type,
                "contract_id": contract_id,
                "referenced_contract_id": referenced_contract_id,
            })

    if not issues:
        if requested_ids is not None:
            return (
                "Проблем извлечения для указанных "
                "договорных цепочек не обнаружено."
            )

        return "Проблем извлечения не обнаружено."

    return json.dumps(
        issues,
        ensure_ascii=False,
        indent=2,
    )


@tool
def get_contracts() -> str:
    """
    Получить список договоров и их цепочек.

    Возвращает идентификаторы договоров, наличие основного
    договора, количество дополнительных соглашений,
    статус цепочки и предупреждения.
    """

    chains = _build_chains()

    result = []

    for chain in chains:
        result.append(
            {
                "contract_id": chain.contract_id,
                "status": chain.status,
                "base_contract": (
                    chain.base_contract is not None
                ),
                "addenda_count": len(chain.addenda),
                "warnings": chain.warnings,
            }
        )

    return json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
    )


@tool
def get_contract_history(
    contract_id: str,
) -> str:
    """
    Получить агрегированную историю конкретного договора.

    contract_id — идентификатор основной цепочки договора.
    Возвращает основной договор, дополнительные соглашения,
    актуальные условия и историю изменений.
    """

    chains = _build_chains()

    chain = next(
        (
            chain
            for chain in chains
            if chain.contract_id == contract_id
        ),
        None,
    )

    if chain is None:
        return json.dumps(
            {
                "error": (
                    f"Договор {contract_id} "
                    "не найден."
                )
            },
            ensure_ascii=False,
        )

    aggregator = ContractAggregator()

    history = aggregator.aggregate(chain)

    return history.model_dump_json(
        ensure_ascii=False,
        indent=2,
    )


@tool
def get_contract_clusters() -> str:
    """
    Получить кластеры договоров.

    Кластеризация выполняется по типу договора и предмету.
    Возвращает список кластеров и входящие в них договоры.
    """

    chains = _build_chains()

    clusterer = ContractClusterer()

    clusters = clusterer.cluster(chains)

    return json.dumps(
        [
            cluster.model_dump()
            for cluster in clusters
        ],
        ensure_ascii=False,
        indent=2,
    )


@tool
def compare_contracts(
    contract_ids: str,
) -> str:
    """
    Сравнить несколько договоров.

    contract_ids — идентификаторы договоров через запятую.

    Возвращает предмет, тип договора и актуальные условия
    для каждого указанного договора.
    """

    ids = [
        contract_id.strip()
        for contract_id in contract_ids.split(",")
        if contract_id.strip()
    ]

    chains = _build_chains()

    aggregator = ContractAggregator()

    result = []

    for contract_id in ids:
        chain = next(
            (
                chain
                for chain in chains
                if chain.contract_id == contract_id
            ),
            None,
        )

        if chain is None:
            result.append(
                {
                    "contract_id": contract_id,
                    "error": "Договор не найден.",
                }
            )
            continue

        history = aggregator.aggregate(chain)

        result.append({
            "contract_id": contract_id,
            "current_conditions": history.current_conditions,
            "replacements": history.replacements,
            "warnings": history.warnings,
            "history": history.history,
        })

    return json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
    )


@tool
def compare_cluster_contracts(cluster_id: str) -> str:
    """
    Сравнивает договоры, входящие в указанный кластер, по доступным
    структурированным условиям.

    Если в кластере находится только один договор, возвращает его
    доступные условия и указывает, что междоговорное сравнение
    невозможно из-за отсутствия второго договора.
    """
    chains = _build_chains()

    clusterer = ContractClusterer()
    clusters = clusterer.cluster(chains)

    cluster = next(
        (cluster for cluster in clusters if cluster.cluster_id == cluster_id),
        None,
    )

    if cluster is None:
        return json.dumps(
            {"error": f"Кластер {cluster_id} не найден."},
            ensure_ascii=False,
            indent=2,
        )

    aggregator = ContractAggregator()

    contract_histories = {}
    for contract_id in cluster.contract_ids:
        chain = next(
            (chain for chain in chains if chain.contract_id == contract_id),
            None,
        )

        if chain is None:
            continue

        history = aggregator.aggregate(chain)

        contract_histories[contract_id] = {
            "contract_type": (
                chain.base_contract.get("contract_type")
                if chain.base_contract
                else None
            ),
            "subject": (
                chain.base_contract.get("subject")
                if chain.base_contract
                else None
            ),
            "current_conditions": history.current_conditions,
            "replacements": history.replacements,
            "warnings": history.warnings,
        }

    differences = {}

    all_condition_names = set()

    for data in contract_histories.values():
        all_condition_names.update(
            data["current_conditions"].keys()
        )

    for condition_name in sorted(all_condition_names):
        values = {}

        for contract_id, data in contract_histories.items():
            value = data["current_conditions"].get(condition_name)

            if value is not None:
                values[contract_id] = value

        if len(set(values.values())) > 1:
            differences[condition_name] = values

    return json.dumps(
        {
            "cluster_id": cluster.cluster_id,
            "label": cluster.label,
            "description": cluster.description,
            "contract_ids": cluster.contract_ids,
            "contracts": contract_histories,
            "differences": differences,
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
def get_cluster_details(cluster_id: str) -> str:
    """Показать состав кластера: договоры
    и документы каждой договорной цепочки."""
    chains = _build_chains()

    clusterer = ContractClusterer()
    clusters = clusterer.cluster(chains)

    cluster = next(
        (cluster for cluster in clusters if cluster.cluster_id == cluster_id),
        None,
    )

    if cluster is None:
        return json.dumps(
            {"error": f"Кластер {cluster_id} не найден."},
            ensure_ascii=False,
            indent=2,
        )

    result = []

    for contract_id in cluster.contract_ids:
        chain = next(
            (chain for chain in chains if chain.contract_id == contract_id),
            None,
        )

        if chain is None:
            continue

        documents = []

        if chain.base_contract is not None:
            documents.append({
                "document_id": chain.base_contract.get("document_id"),
                "document_type": chain.base_contract.get("document_type"),
                "document_date": chain.base_contract.get("document_date"),
            })

        for addendum in chain.addenda:
            documents.append({
                "document_id": addendum.get("document_id"),
                "document_type": addendum.get("document_type"),
                "document_date": addendum.get("document_date"),
            })

        result.append({
            "contract_id": contract_id,
            "document_count": len(documents),
            "documents": documents,
        })

    return json.dumps(
        {
            "cluster_id": cluster.cluster_id,
            "label": cluster.label,
            "description": cluster.description,
            "contract_count": len(result),
            "document_count": sum(
                item["document_count"] for item in result
            ),
            "contracts": result,
        },
        ensure_ascii=False,
        indent=2,
    )


TOOLS = [
    get_extraction_issues,
    get_contracts,
    get_contract_history,
    get_contract_clusters,
    compare_contracts,
    compare_cluster_contracts,
    get_cluster_details,
]
