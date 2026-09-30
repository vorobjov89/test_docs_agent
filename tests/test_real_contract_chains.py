import json

from app.services.contract_chain_builder import ContractChainBuilder


def test_real_contract_chains():
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

    print("\n=== CONTRACT CHAINS ===")

    for chain in chains:
        print(
            f"\n{chain.contract_id}"
            f" | status={chain.status}"
        )

        print(
            "base:",
            (
                chain.base_contract.get("document_id")
                if chain.base_contract
                else None
            ),
        )

        print(
            "addenda:",
            [
                x.get("document_id")
                for x in chain.addenda
            ],
        )

        print(
            "warnings:",
            chain.warnings,
        )

    assert len(chains) > 0