from datetime import datetime

from app.models.contract import ContractChain, ContractHistory


class ContractAggregator:

    def aggregate(
        self,
        chain: ContractChain,
    ) -> ContractHistory:

        if chain.base_contract is None:
            return ContractHistory(
                contract_id=chain.contract_id,
                base_contract=None,
                addenda=chain.addenda,
                current_conditions={},
                history=[
                    {
                        "type": "warning",
                        "message": (
                            "Основной договор отсутствует "
                            "в наборе документов."
                        ),
                    }
                ],
            )

        addenda = self._sort_addenda(
            chain.addenda
        )

        current_conditions = (
            self._build_initial_state(
                chain.base_contract
            )
        )

        history = []

        for addendum in addenda:
            changes = addendum.get(
                "changes",
                [],
            )

            applied_changes = []

            for change in changes:
                applied = self._apply_change(
                    current_conditions,
                    change,
                )

                if applied:
                    applied_changes.append(change)

            history.append(
                {
                    "addendum_id": (
                        addendum.get("document_id")
                        or "unknown"
                    ),
                    "effective_date": addendum.get(
                        "effective_date"
                    ),
                    "document_date": addendum.get(
                        "document_date"
                    ),
                    "changes": applied_changes,
                }
            )

        return ContractHistory(
            contract_id=chain.contract_id,
            base_contract=chain.base_contract,
            addenda=addenda,
            current_conditions=current_conditions,
            history=history,
        )

    def _sort_addenda(
        self,
        addenda: list[dict],
    ) -> list[dict]:

        return sorted(
            addenda,
            key=self._parse_document_date,
        )

    def _parse_document_date(
        self,
        document: dict,
    ) -> datetime:

        effective_date = document.get(
            "effective_date"
        )

        parsed = self._parse_date(
            effective_date
        )

        if parsed:
            return parsed

        document_date = document.get(
            "document_date"
        )

        parsed = self._parse_date(
            document_date
        )

        if parsed:
            return parsed

        return datetime.max

    def _parse_date(
        self,
        value: str | None,
    ) -> datetime | None:

        if not value:
            return None

        value = value.strip()

        formats = [
            "%d.%m.%Y",
            "%d-%m-%Y",
            "%Y-%m-%d",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(
                    value,
                    fmt,
                )
            except ValueError:
                pass

        russian_months = {
            "января": 1,
            "февраля": 2,
            "марта": 3,
            "апреля": 4,
            "мая": 5,
            "июня": 6,
            "июля": 7,
            "августа": 8,
            "сентября": 9,
            "октября": 10,
            "ноября": 11,
            "декабря": 12,
        }

        parts = value.lower().split()

        if len(parts) >= 3:
            try:
                day = int(parts[0])
                month = russian_months.get(parts[1])
                year = int(parts[2])

                if month:
                    return datetime(
                        year,
                        month,
                        day,
                    )
            except ValueError:
                pass

        return None

    def _build_initial_state(
        self,
        base_contract: dict,
    ) -> dict[str, str]:

        conditions: dict[str, str] = {}

        if base_contract.get("subject"):
            conditions["subject"] = (
                base_contract["subject"]
            )

        if base_contract.get("contract_type"):
            conditions["contract_type"] = (
                base_contract["contract_type"]
            )

        return conditions

    def _apply_change(
        self,
        current_conditions: dict[str, str],
        change: dict,
    ) -> bool:

        section = change.get("section")

        if not section:
            return False

        change_type = change.get(
            "change_type"
        )

        new_content = (
            change.get("new_text")
            or change.get("new_value")
        )

        if change_type in {
            "add",
            "modify",
            "replace_section",
        }:
            if new_content is None:
                return False

            current_conditions[section] = (
                new_content
            )

            return True

        if change_type == "delete":
            current_conditions.pop(
                section,
                None,
            )

            return True

        return False