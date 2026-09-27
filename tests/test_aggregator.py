from app.models.contract import ContractChain
from app.services.aggregator import ContractAggregator


def test_aggregator_applies_changes_in_order():

    chain = ContractChain(
        contract_id="D100",
        base_contract={
            "document_id": "D100",
            "document_type": "contract",
            "contract_id": "D100",
            "contract_type": "услуги",
            "subject": "Оказание услуг",
        },
        addenda=[
            {
                "document_id": "ADD2",
                "effective_date": "01.03.2024",
                "changes": [
                    {
                        "section": "price",
                        "change_type": "modify",
                        "new_value": "200",
                    }
                ],
            },
            {
                "document_id": "ADD1",
                "effective_date": "01.01.2024",
                "changes": [
                    {
                        "section": "price",
                        "change_type": "modify",
                        "new_value": "100",
                    }
                ],
            },
        ],
    )

    aggregator = ContractAggregator()

    history = aggregator.aggregate(chain)

    assert history.current_conditions["price"] == "200"

    assert [
        item["addendum_id"]
        for item in history.history
    ] == [
        "ADD1",
        "ADD2",
    ]


def test_aggregator_handles_incomplete_chain():

    chain = ContractChain(
        contract_id="D200",
        base_contract=None,
        addenda=[
            {
                "document_id": "ADD1",
                "effective_date": "01.01.2024",
                "changes": [],
            }
        ],
        status="incomplete",
        warnings=[
            "Основной договор отсутствует."
        ],
    )

    aggregator = ContractAggregator()

    history = aggregator.aggregate(chain)

    assert history.base_contract is None
    assert history.current_conditions == {}

    assert history.history[0]["type"] == "warning"