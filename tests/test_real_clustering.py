import json

from app.services.clusterer import ContractClusterer
from app.services.contract_chain_builder import ContractChainBuilder


def test_real_contract_clustering():

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

    clusterer = ContractClusterer()

    clusters = clusterer.cluster(chains)

    print("\n=== CONTRACT CLUSTERS ===")

    for cluster in clusters:
        print(
            f"\n{cluster.cluster_id}"
        )

        print(
            "label:",
            cluster.label,
        )

        print(
            "description:",
            cluster.description,
        )

        print(
            "contracts:",
            cluster.contract_ids,
        )

    assert len(clusters) > 0