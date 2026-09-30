from app.models.contract import ContractChain
from app.services.clusterer import ContractClusterer


def test_contract_clustering():

    chains = [
        ContractChain(
            contract_id="D1",
            base_contract={
                "contract_type": "услуги",
                "subject": "оказание услуг связи",
            },
        ),
        ContractChain(
            contract_id="D2",
            base_contract={
                "contract_type": "услуги",
                "subject": "оказание услуг связи",
            },
        ),
        ContractChain(
            contract_id="D3",
            base_contract={
                "contract_type": "аренда",
                "subject": "аренда помещения",
            },
        ),
    ]

    clusterer = ContractClusterer()

    clusters = clusterer.cluster(chains)

    assert len(clusters) == 2

    all_contract_ids = {
        contract_id
        for cluster in clusters
        for contract_id in cluster.contract_ids
    }

    assert all_contract_ids == {
        "D1",
        "D2",
        "D3",
    }