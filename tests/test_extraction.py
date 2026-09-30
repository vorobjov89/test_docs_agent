from app.models.contract import (
    ChangeType,
    ContractChange,
)
from app.models.extraction import ExtractedDocument
from app.services.validator import ExtractionValidator


def test_addendum_without_contract_reference():
    document = ExtractedDocument(
        document_type="addendum",
    )

    validator = ExtractionValidator()

    errors = validator.validate(document)

    assert errors


def test_valid_addendum():
    document = ExtractedDocument(
        document_type="addendum",
        document_id="D210262441-02",
        referenced_contract_id="D210262441-01",
        changes=[
            ContractChange(
                change_type=ChangeType.MODIFY,
                description="Изменена стоимость",
                old_value="100",
                new_value="200",
            )
        ],
    )

    validator = ExtractionValidator()

    errors = validator.validate(document)

    assert errors == []


def test_contract_changes_are_extracted():
    document = ExtractedDocument(
        document_type="contract",
        changes=[
            ContractChange(
                change_type=ChangeType.ADD,
                description="Добавлено условие о стоимости",
                new_value="100000 рублей",
                source_page=3,
            )
        ],
    )

    assert len(document.changes) == 1
    assert document.changes[0].change_type == ChangeType.ADD
    assert document.changes[0].description == "Добавлено условие о стоимости"
    assert document.changes[0].new_value == "100000 рублей"
    assert document.changes[0].source_page == 3
