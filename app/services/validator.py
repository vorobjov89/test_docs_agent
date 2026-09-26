from app.models.extraction import ExtractedDocument


class ExtractionValidator:

    def validate(
        self,
        result: ExtractedDocument,
    ) -> list[str]:

        errors: list[str] = []

        if result.document_type == "addendum":
            if not result.referenced_contract_id:
                errors.append(
                    "Не удалось определить договор, "
                    "к которому относится дополнительное соглашение."
                )

        if (
            result.document_type == "addendum"
            and not result.changes
        ):
            errors.append(
                "Дополнительное соглашение не содержит "
                "распознанных изменений."
            )

        return errors