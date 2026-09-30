import json

from app.services.contract_chain_builder import ContractChainBuilder
from app.services.aggregator import ContractAggregator


TARGET_CONTRACT_ID = "D210262441-01"
TARGET_ADDENDUM_ID = "D250134282-01"


def main():
    with open("data/processed/documents.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        documents = data["documents"]
    else:
        documents = data

    documents = [
        document["data"]
        for document in documents
        if document.get("data")
    ]

    print(f"Документов: {len(documents)}")

    # ---------------------------------------------------------
    # Диагностика загруженных документов
    # ---------------------------------------------------------
    print("\n" + "=" * 80)
    print("ДОКУМЕНТЫ")
    print("=" * 80)

    for document in documents:
        document_id = document.get("document_id")
        document_type = document.get("document_type")
        contract_id = document.get("contract_id")
        referenced_contract_id = document.get("referenced_contract_id")

        print(
            f"{document_id} | "
            f"type={document_type} | "
            f"contract_id={contract_id} | "
            f"referenced={referenced_contract_id}"
        )

    # ---------------------------------------------------------
    # Построение цепочек договоров
    # ---------------------------------------------------------
    builder = ContractChainBuilder()

    print("\n" + "=" * 80)
    print("CONTRACT CHAINS")
    print("=" * 80)

    chains = builder.build(documents)

    for chain in chains:
        print(f"\nКонтракт: {chain.contract_id}")
        print(f"Статус: {chain.status}")
        print(f"Основной договор: "
              f"{chain.base_contract.get('document_id') if chain.base_contract else None}")

        print("Дополнительные соглашения:")

        for addendum in chain.addenda:
            print(
                f"  - {addendum.get('document_id')} | "
                f"date={addendum.get('document_date')} | "
                f"effective={addendum.get('effective_date')}"
            )

        if chain.warnings:
            print("Warnings:")
            for warning in chain.warnings:
                print(f"  ! {warning}")

    # ---------------------------------------------------------
    # Агрегация
    # ---------------------------------------------------------
    aggregator = ContractAggregator()

    for chain in chains:
        history = aggregator.aggregate(chain)

        # Обычная краткая диагностика для всех контрактов
        print("\n" + "=" * 80)
        print(f"AGGREGATION: {chain.contract_id}")
        print("=" * 80)

        print(
            f"Current conditions: "
            f"{len(history.current_conditions)}"
        )

        print(
            f"History events: "
            f"{len(history.history)}"
        )

        if history.warnings:
            print("Warnings:")
            for warning in history.warnings:
                print(f"  ! {warning}")

        for event in history.history:
            applied = event.get("changes", [])
            failed = event.get("failed_changes", [])

            print(
                f"\n{event.get('addendum_id')}: "
                f"applied={len(applied)}, "
                f"failed={len(failed)}"
            )

        # -----------------------------------------------------
        # Подробная диагностика только нужного договора
        # -----------------------------------------------------
        if chain.contract_id != TARGET_CONTRACT_ID:
            continue

        print("\n\n")
        print("#" * 80)
        print(f"# ПОДРОБНАЯ ДИАГНОСТИКА {TARGET_CONTRACT_ID}")
        print("#" * 80)

        # -----------------------------------------------------
        # Основной договор
        # -----------------------------------------------------
        print("\n" + "=" * 80)
        print("BASE CONTRACT")
        print("=" * 80)

        if chain.base_contract is None:
            print("Основной договор отсутствует.")
        else:
            print(
                json.dumps(
                    chain.base_contract,
                    ensure_ascii=False,
                    indent=2,
                )
            )

        # -----------------------------------------------------
        # Все дополнительные соглашения
        # -----------------------------------------------------
        print("\n" + "=" * 80)
        print("ADDENDA")
        print("=" * 80)

        for addendum in chain.addenda:
            print("\n" + "-" * 80)
            print(
                f"ADDENDUM: "
                f"{addendum.get('document_id')}"
            )
            print("-" * 80)

            print(
                json.dumps(
                    addendum,
                    ensure_ascii=False,
                    indent=2,
                )
            )

        # -----------------------------------------------------
        # Отдельно D250134282-01
        # -----------------------------------------------------
        print("\n" + "#" * 80)
        print(f"# TARGET ADDENDUM: {TARGET_ADDENDUM_ID}")
        print("#" * 80)

        target_addendum = None

        for addendum in chain.addenda:
            if addendum.get("document_id") == TARGET_ADDENDUM_ID:
                target_addendum = addendum
                break

        if target_addendum is None:
            print(
                f"Дополнительное соглашение "
                f"{TARGET_ADDENDUM_ID} не найдено."
            )
        else:
            print("\nMETADATA:")
            print(
                json.dumps(
                    {
                        "document_id": target_addendum.get("document_id"),
                        "document_type": target_addendum.get("document_type"),
                        "document_date": target_addendum.get("document_date"),
                        "effective_date": target_addendum.get("effective_date"),
                        "contract_id": target_addendum.get("contract_id"),
                        "referenced_contract_id": target_addendum.get(
                            "referenced_contract_id"
                        ),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )

            print("\nCHANGES:")

            changes = target_addendum.get("changes", [])

            if not changes:
                print("Изменения отсутствуют.")
            else:
                for index, change in enumerate(changes, start=1):
                    print("\n" + "-" * 80)
                    print(f"CHANGE #{index}")
                    print("-" * 80)

                    print(
                        json.dumps(
                            change,
                            ensure_ascii=False,
                            indent=2,
                        )
                    )

        # -----------------------------------------------------
        # History
        # -----------------------------------------------------
        print("\n" + "#" * 80)
        print("# AGGREGATION HISTORY")
        print("#" * 80)

        for index, event in enumerate(history.history, start=1):
            print("\n" + "-" * 80)
            print(f"EVENT #{index}")
            print("-" * 80)

            print(
                json.dumps(
                    event,
                    ensure_ascii=False,
                    indent=2,
                )
            )

        # -----------------------------------------------------
        # Текущее состояние
        # -----------------------------------------------------
        print("\n" + "#" * 80)
        print("# CURRENT CONDITIONS")
        print("#" * 80)

        for key, value in history.current_conditions.items():
            print("\n" + "-" * 80)
            print(f"KEY: {key}")
            print("-" * 80)
            print(value)

        # -----------------------------------------------------
        # Отдельно failed changes
        # -----------------------------------------------------
        print("\n" + "#" * 80)
        print("# FAILED CHANGES")
        print("#" * 80)

        found_failed = False

        for event in history.history:
            failed_changes = event.get("failed_changes", [])

            if not failed_changes:
                continue

            found_failed = True

            print(
                f"\nADDENDUM: "
                f"{event.get('addendum_id')}"
            )

            for index, change in enumerate(
                failed_changes,
                start=1,
            ):
                print("\n" + "-" * 80)
                print(f"FAILED CHANGE #{index}")
                print("-" * 80)

                print(
                    json.dumps(
                        change,
                        ensure_ascii=False,
                        indent=2,
                    )
                )

        if not found_failed:
            print("Неудачных изменений нет.")


if __name__ == "__main__":
    main()
