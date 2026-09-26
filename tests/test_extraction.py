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