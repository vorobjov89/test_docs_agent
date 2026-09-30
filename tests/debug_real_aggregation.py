import json

from app.services.contract_chain_builder import ContractChainBuilder
from app.services.aggregator import ContractAggregator


def main():
    with open("data/processed/documents.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        documents = data["documents"]
    else:
        documents = data

    print(f"Документов: {len(documents)}")

    # ---------------------------------------------------------
    # Диагностика входных документов
    # ---------------------------------------------------------

    print("\n" + "=" * 80)
    print("ДИАГНОСТИКА ДОКУМЕНТОВ")
    print("=" * 80)

    for index, document in enumerate(documents, start=1):
        print(f"\nDOCUMENT #{index}")
        print(f"keys: {list(document.keys())}")

        print(
            f"document_type: "
            f"{document.get('document_type')!r}"
        )

        print(
            f"document_id: "
            f"{document.get('document_id')!r}"
        )

        print(
            f"contract_id: "
            f"{document.get('contract_id')!r}"
        )

        print(
            f"referenced_contract_id: "
            f"{document.get('referenced_contract_id')!r}"
        )

    # ---------------------------------------------------------
    # Проверяем _get_contract_id напрямую
    # ---------------------------------------------------------

    builder = ContractChainBuilder()

    print("\n" + "=" * 80)
    print("РЕЗУЛЬТАТ _get_contract_id()")
    print("=" * 80)

    for index, document in enumerate(documents, start=1):
        contract_id = builder._get_contract_id(document)

        print(
            f"{index:02d}. "
            f"type={document.get('document_type')!r} "
            f"document_id={document.get('document_id')!r} "
            f"-> contract_id={contract_id!r}"
        )

    # ---------------------------------------------------------
    # Строим chains
    # ---------------------------------------------------------

    chains = builder.build(documents)

    print("\n" + "=" * 80)
    print("CHAINS")
    print("=" * 80)

    print(f"Всего chains: {len(chains)}")

    if not chains:
        print(
            "\n!!! ContractChainBuilder не создал ни одной chain."
        )
        print(
            "Сначала исправляем это, aggregator пока не трогаем."
        )
        return

    # ---------------------------------------------------------
    # Aggregator
    # ---------------------------------------------------------

    aggregator = ContractAggregator()

    for chain in chains:
        print("\n" + "=" * 80)
        print(f"CHAIN: {chain.contract_id}")
        print("=" * 80)

        print(f"STATUS: {chain.status}")
        print(
            f"BASE: "
            f"{chain.base_contract is not None}"
        )
        print(
            f"ADDENDA: "
            f"{len(chain.addenda)}"
        )

        if chain.base_contract:
            base = chain.base_contract

            print(
                f"BASE DOCUMENT: "
                f"{base.get('document_id')} | "
                f"{base.get('filename')}"
            )

        for addendum in chain.addenda:
            print(
                f"  - {addendum.get('document_id')} "
                f"| effective={addendum.get('effective_date')} "
                f"| document_date={addendum.get('document_date')} "
                f"| changes={len(addendum.get('changes', []))}"
            )

        if chain.warnings:
            print("\nCHAIN WARNINGS:")

            for warning in chain.warnings:
                print(f"  ! {warning}")

        # -----------------------------------------------------
        # Aggregation
        # -----------------------------------------------------

        history = aggregator.aggregate(chain)

        print(
            f"\nCURRENT CONDITIONS: "
            f"{len(history.current_conditions)}"
        )

        print(
            f"HISTORY EVENTS: "
            f"{len(history.history)}"
        )

        if history.warnings:
            print("\nAGGREGATOR WARNINGS:")

            for warning in history.warnings:
                print(f"  ! {warning}")

        # -----------------------------------------------------
        # Changes
        # -----------------------------------------------------

        for event in history.history:
            applied = event.get("changes", [])
            failed = event.get("failed_changes", [])

            print(
                f"\n  {event.get('addendum_id')}: "
                f"applied={len(applied)}, "
                f"failed={len(failed)}"
            )

            for change in applied:
                print(
                    f"      APPLIED: "
                    f"{change.get('section')} "
                    f"[{change.get('change_type')}]"
                )

            for change in failed:
                print(
                    f"      FAILED: "
                    f"{change.get('section')} "
                    f"[{change.get('change_type')}]"
                )

                print(
                    f"          description: "
                    f"{change.get('description')}"
                )

        # -----------------------------------------------------
        # Final state
        # -----------------------------------------------------

        if chain.contract_id in {
            "D150641492-09",
            "D220600738-01",
            "D210003801-01",
            "D210262441-01",
        }:
            print("\nFINAL CURRENT CONDITIONS:")

            for name, value in history.current_conditions.items():
                print(f"\n  [{name}]")
                print(f"  {value}")


if __name__ == "__main__":
    main()