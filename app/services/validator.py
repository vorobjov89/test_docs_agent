from app.models.extraction import ExtractedDocument


class ExtractionValidator:

    def validate(
        self,
        result: ExtractedDocument,
    ) -> list[str]:

        errors: list[str] = []

        if not result.document_type:
            errors.append(
                "Не удалось определить тип документа."
            )

        if result.document_type == "contract":

            if not result.document_id:
                errors.append(
                    "Для основного договора не определён "
                    "идентификатор документа."
                )

            if not result.contract_id:
                errors.append(
                    "Для основного договора не определён "
                    "contract_id."
                )

        if result.document_type == "addendum":

            if not result.document_id:
                errors.append(
                    "Для дополнительного соглашения не определён "
                    "идентификатор документа."
                )

            if not result.referenced_contract_id:
                errors.append(
                    "Не удалось определить договор, "
                    "к которому относится дополнительное соглашение."
                )

        return errors
