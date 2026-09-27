import json

from app.models.contract import ContractChain
from app.services.aggregator import ContractAggregator
from app.services.contract_chain_builder import ContractChainBuilder


def test_real_contract_aggregation():

    with open(
        "data/processed/documents.json",
        encoding="utf-8",
    ) as f:
        results = json.load(f)

    documents = [
        item["data"]
        for item in results
        if item.get("data")
    ]

    builder = ContractChainBuilder()
    chains = builder.build(documents)

    aggregator = ContractAggregator()

    print("\n=== CONTRACT HISTORIES ===")

    for chain in chains:

        history = aggregator.aggregate(chain)

        print(
            f"\n--- {history.contract_id} ---"
        )

        print(
            "base:",
            (
                history.base_contract.get(
                    "document_id"
                )
                if history.base_contract
                else None
            ),
        )

        print(
            "addenda:",
            [
                item.get("document_id")
                for item in history.addenda
            ],
        )

        print(
            "current_conditions:",
            history.current_conditions,
        )

        print("history:")

        for item in history.history:
            print(
                f"  {item.get('addendum_id')}: "
                f"{len(item.get('changes', []))} changes"
            )

    assert len(chains) > 0