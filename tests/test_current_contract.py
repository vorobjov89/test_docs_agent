import json

from app.services.aggregator import ContractAggregator
from app.services.contract_chain_builder import ContractChainBuilder


CONTRACT_ID = "D220600738-01"
PROCESSED_FILE = "data/processed/documents.json"


def test_aggregation():
    with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
        results = json.load(f)

    documents = [
        result["data"]
        for result in results
        if result.get("data")
        and result.get("status") in {"success", "partial"}
    ]

    chains = ContractChainBuilder().build(documents)

    chain = next(
        (
            chain
            for chain in chains
            if chain.contract_id == CONTRACT_ID
        ),
        None,
    )

    if chain is None:
        raise RuntimeError(
            f"Договор {CONTRACT_ID} не найден."
        )

    history = ContractAggregator().aggregate(chain)

    print("\n")
    print("=" * 100)
    print(f"CONTRACT: {CONTRACT_ID}")
    print("=" * 100)

    print("\n")
    print("=" * 100)
    print("CHAIN")
    print("=" * 100)

    print(f"contract_id: {chain.contract_id}")
    print(f"status: {chain.status}")
    print(f"base_contract: {chain.base_contract is not None}")
    print(f"addenda_count: {len(chain.addenda)}")

    if chain.warnings:
        print("\nCHAIN WARNINGS:")
        for warning in chain.warnings:
            print(f"- {warning}")

    print("\n")
    print("=" * 100)
    print("CURRENT CONDITIONS")
    print("=" * 100)

    if not history.current_conditions:
        print("Нет текущих условий.")

    for key, value in history.current_conditions.items():
        print(f"\n[{key}]")
        print(value)

    print("\n")
    print("=" * 100)
    print("HISTORY")
    print("=" * 100)

    if not history.history:
        print("История изменений отсутствует.")

    for index, item in enumerate(history.history, start=1):
        print(f"\n--- HISTORY ITEM {index} ---")
        print(json.dumps(
            item,
            ensure_ascii=False,
            indent=2,
        ))

    print("\n")
    print("=" * 100)
    print("WARNINGS")
    print("=" * 100)

    if not history.warnings:
        print("Предупреждений нет.")

    for warning in history.warnings:
        print(f"- {warning}")

    print("\n")
    print("=" * 100)
    print("FULL AGGREGATED RESULT")
    print("=" * 100)

    print(
        history.model_dump_json(
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    test_aggregation()
