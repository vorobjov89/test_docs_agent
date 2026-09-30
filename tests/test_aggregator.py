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
            "conditions": [
                {
                    "name": "price",
                    "value": "50",
                    "source_page": 2,
                }
            ],
        },
        addenda=[
            {
                "document_id": "ADD2",
                "effective_date": "01.03.2024",
                "changes": [
                    {
                        "section": "price",
                        "change_type": "modify",
                        "old_value": "100",
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
                        "old_value": "50",
                        "new_value": "100",
                    }
                ],
            },
        ],
    )

    history = ContractAggregator().aggregate(chain)

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

    history = ContractAggregator().aggregate(chain)

    assert history.base_contract is None
    assert history.current_conditions == {}

    assert history.history[0]["type"] == "warning"


def test_aggregator_replaces_section():

    chain = ContractChain(
        contract_id="D300",
        base_contract={
            "document_id": "D300",
            "document_type": "contract",
            "conditions": [
                {
                    "name": "payment_terms",
                    "value": "Оплата в течение 10 дней",
                }
            ],
        },
        addenda=[
            {
                "document_id": "ADD1",
                "effective_date": "01.01.2024",
                "changes": [
                    {
                        "section": "payment_terms",
                        "change_type": "replace_section",
                        "new_text": "Оплата в течение 30 дней",
                    }
                ],
            }
        ],
    )

    history = ContractAggregator().aggregate(chain)

    # Полная замена раздела фиксируется отдельно.
    assert len(history.replacements) == 1

    replacement = history.replacements[0]

    assert replacement["section"] == "payment_terms"

    # Исходное структурированное состояние не считается
    # полностью реконструированным после replace_section.
    assert (
        history.current_conditions["payment_terms"]
        == "Оплата в течение 10 дней"
    )

    # Само изменение должно присутствовать в истории.
    assert history.history[0]["changes"]
    assert (
        history.history[0]["changes"][0]["change_type"]
        == "replace_section"
    )


def test_aggregator_records_failed_change():

    chain = ContractChain(
        contract_id="D400",
        base_contract={
            "document_id": "D400",
            "document_type": "contract",
            "conditions": [
                {
                    "name": "price",
                    "value": "50",
                }
            ],
        },
        addenda=[
            {
                "document_id": "ADD1",
                "effective_date": "01.01.2024",
                "changes": [
                    {
                        "section": "price",
                        "change_type": "modify",
                        "old_value": "999",
                        "new_value": "100",
                    }
                ],
            }
        ],
    )

    history = ContractAggregator().aggregate(chain)

    assert history.current_conditions["price"] == "50"

    assert history.history[0]["failed_changes"]

    assert (
        history.history[0]["failed_changes"][0]["old_value"]
        == "999"
    )