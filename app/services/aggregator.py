import re
from datetime import datetime

from app.models.contract import ContractChain, ContractHistory


class ContractAggregator:
    def aggregate(self, chain: ContractChain) -> ContractHistory:
        if chain.base_contract is None:
            return ContractHistory(
                contract_id=chain.contract_id,
                base_contract=None,
                addenda=chain.addenda,
                current_conditions={},
                replacements=[],
                history=[
                    {
                        "type": "warning",
                        "message": (
                            "Основной договор отсутствует "
                            "в наборе документов."
                        ),
                    }
                ],
                warnings=list(chain.warnings),
            )

        addenda = self._sort_addenda(chain.addenda)

        current_conditions = self._build_initial_state(
            chain.base_contract
        )

        replacements = []
        history = []
        warnings = list(chain.warnings)

        base_failed_chunks = chain.base_contract.get(
            "failed_chunks",
            [],
        )

        if base_failed_chunks:
            warnings.append(
                "Основной договор извлечён частично: "
                f"не обработано чанков: {len(base_failed_chunks)}."
            )

        for addendum in addenda:
            changes = addendum.get("changes", [])

            applied_changes = []
            failed_changes = []

            for change in changes:
                change_type = change.get("change_type")

                if change_type == "replace_section":
                    applied = self._apply_replacement(
                        current_conditions=current_conditions,
                        replacements=replacements,
                        change=change,
                        addendum=addendum,
                    )
                else:
                    applied = self._apply_change(
                        current_conditions=current_conditions,
                        change=change,
                    )

                if applied:
                    applied_changes.append(change)
                else:
                    failed_changes.append(change)

            failed_chunks = addendum.get(
                "failed_chunks",
                [],
            )

            event_warnings = []

            if failed_chunks:
                event_warnings.append(
                    "Дополнительное соглашение извлечено частично: "
                    f"не обработано чанков: {len(failed_chunks)}."
                )

            if failed_changes:
                if failed_chunks or base_failed_chunks:
                    event_warnings.append(
                        "Не все изменения удалось применить. "
                        "Причиной может быть неполное извлечение "
                        "основного договора или "
                        "дополнительного соглашения."
                    )
                else:
                    event_warnings.append(
                        "Не все изменения удалось применить: "
                        "соответствующие условия отсутствуют "
                        "в текущем состоянии договора, "
                        "неоднозначны или не совпадают "
                        "с извлечёнными идентификаторами разделов."
                    )

            event = {
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
                "failed_changes": failed_changes,
            }

            if event_warnings:
                event["warnings"] = event_warnings

                warnings.extend(
                    [
                        (
                            f"{event['addendum_id']}: "
                            f"{warning}"
                        )
                        for warning in event_warnings
                    ]
                )

            history.append(event)

        return ContractHistory(
            contract_id=chain.contract_id,
            base_contract=chain.base_contract,
            addenda=addenda,
            current_conditions=current_conditions,
            replacements=replacements,
            history=history,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Initial state
    # ------------------------------------------------------------------

    def _build_initial_state(
        self,
        base_contract: dict,
    ) -> dict[str, str]:
        conditions: dict[str, str] = {}

        if base_contract.get("subject"):
            conditions["subject"] = base_contract["subject"]

        if base_contract.get("contract_type"):
            conditions["contract_type"] = (
                base_contract["contract_type"]
            )

        for condition in base_contract.get(
            "conditions",
            [],
        ):
            name = condition.get("name")
            value = condition.get("value")

            if not name or not value:
                continue

            normalized_name = self._normalize_section(name)

            if not normalized_name:
                continue

            context = condition.get("section_context")

            if context:
                key = (
                    f"{context}::{normalized_name}"
                )
            else:
                key = normalized_name

            conditions[key] = value

        return conditions

    # ------------------------------------------------------------------
    # Apply point changes
    # ------------------------------------------------------------------

    def _apply_change(
        self,
        current_conditions: dict[str, str],
        change: dict,
    ) -> bool:
        section = self._normalize_section(
            change.get("section")
        )

        if not section:
            return False

        context = self._get_change_context(change)

        change_type = change.get("change_type")

        old_content = (
            change.get("old_text")
            or change.get("old_value")
        )

        new_content = (
            change.get("new_text")
            or change.get("new_value")
        )

        # --------------------------------------------------------------
        # ADD
        # --------------------------------------------------------------

        if change_type == "add":
            if new_content is None:
                return False

            if context:
                key = (
                    f"{context}::{section}"
                )
            else:
                key = section

            if key not in current_conditions:
                current_conditions[key] = new_content
                return True

            return False

        # --------------------------------------------------------------
        # MODIFY
        # --------------------------------------------------------------

        if change_type == "modify":
            if new_content is None:
                return False

            matching_keys = self._find_matching_keys(
                current_conditions=current_conditions,
                section=section,
                context=context,
            )

            if not matching_keys:
                return False

            # Если один и тот же пункт существует,
            # например, в основном договоре и приложениях,
            # без контекста мы не можем безопасно выбрать.
            if len(matching_keys) > 1:
                return False

            matched_key = matching_keys[0]

            current_value = current_conditions[
                matched_key
            ]

            if old_content is not None:
                if old_content not in current_value:
                    return False

                current_conditions[matched_key] = (
                    current_value.replace(
                        old_content,
                        new_content,
                        1,
                    )
                )
            else:
                current_conditions[matched_key] = (
                    new_content
                )

            return True

        # --------------------------------------------------------------
        # DELETE
        # --------------------------------------------------------------

        if change_type == "delete":
            matching_keys = self._find_matching_keys(
                current_conditions=current_conditions,
                section=section,
                context=context,
            )

            if len(matching_keys) != 1:
                return False

            current_conditions.pop(
                matching_keys[0]
            )

            return True

        # --------------------------------------------------------------
        # REPLACE_SECTION
        #
        # Full replacements are processed separately in
        # _apply_replacement().
        # --------------------------------------------------------------

        if change_type == "replace_section":
            return False

        return False

    # ------------------------------------------------------------------
    # Apply full section / appendix replacement
    # ------------------------------------------------------------------

    def _apply_replacement(
        self,
        current_conditions: dict[str, str],
        replacements: list[dict],
        change: dict,
        addendum: dict,
    ) -> bool:
        new_text = change.get("new_text")

        if not new_text:
            return False

        section = change.get("section")

        if not section:
            return False

        section = section.strip()

        context = self._get_change_context(change)

        # Сначала удаляем из структурированного состояния
        # условия, которые больше не являются актуальными.
        self._remove_replaced_conditions(
            current_conditions=current_conditions,
            section=section,
            context=context,
        )

        replacement = {
            "section": section,
            "context": context,
            "text": new_text,
            "source_addendum": (
                addendum.get("document_id")
                or "unknown"
            ),
            "source_page": change.get(
                "source_page"
            ),
            "effective_date": addendum.get(
                "effective_date"
            ),
            "document_date": addendum.get(
                "document_date"
            ),
        }

        # Если более позднее допсоглашение снова заменяет
        # тот же раздел/приложение, старая редакция
        # должна быть заменена новой.
        for index, existing in enumerate(
            replacements
        ):
            if (
                existing.get("section") == section
                and existing.get("context") == context
            ):
                replacements[index] = replacement
                return True

        replacements.append(replacement)

        return True

    def _remove_replaced_conditions(
        self,
        current_conditions: dict[str, str],
        section: str,
        context: str | None,
    ) -> None:
        """
        Удаляет из current_conditions условия,
        которые полностью заменяются новым текстом.

        Например:

            Раздел 1-8 Соглашения

        удаляет:

            Основной договор::1
            Основной договор::1.1
            ...
            Основной договор::8.2

        но сохраняет:

            Основной договор::9
            Основной договор::9.1

        Для приложения удаляются только условия
        соответствующего приложения.
        """

        # --------------------------------------------------------------
        # Full replacement of sections 1-8
        # --------------------------------------------------------------

        if re.search(
            r"раздел\s*1\s*[-–]\s*8",
            section,
            flags=re.IGNORECASE,
        ):
            keys_to_remove = []

            for key in current_conditions:
                raw_section = self._extract_raw_section(
                    key
                )

                # 1, 1.1, 1.2, 2, 2.1 ... 8.2
                if re.fullmatch(
                    r"[1-8](?:\.\d+)*",
                    raw_section,
                ):
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                current_conditions.pop(
                    key,
                    None,
                )

            return

        # --------------------------------------------------------------
        # Full replacement of an appendix
        # --------------------------------------------------------------

        if context and re.fullmatch(
            r"Приложение\s+№\d+",
            context,
            flags=re.IGNORECASE,
        ):
            prefix = f"{context}::"

            keys_to_remove = [
                key
                for key in current_conditions
                if key.startswith(prefix)
            ]

            for key in keys_to_remove:
                current_conditions.pop(
                    key,
                    None,
                )

    # ------------------------------------------------------------------
    # Context handling
    # ------------------------------------------------------------------

    @staticmethod
    def _get_change_context(
        change: dict,
    ) -> str | None:
        """
        Определяет контекст изменения.

        Приоритет:
        1. Явно извлечённый section_context.
        2. Приложение №N в section.
        3. Явная ссылка на договор.
        4. Полная замена разделов 1-8 Соглашения.
        """

        explicit = change.get(
            "section_context"
        )

        if explicit:
            return explicit

        section = change.get("section")

        if not section:
            return None

        value = section.strip()

        # --------------------------------------------------------------
        # Приложение №N
        # --------------------------------------------------------------

        match = re.search(
            r"Приложение\s+№\s*(\d+)",
            value,
            flags=re.IGNORECASE,
        )

        if match:
            return (
                f"Приложение №{match.group(1)}"
            )

        # --------------------------------------------------------------
        # Раздел 1-8 Соглашения
        # --------------------------------------------------------------

        if re.search(
            r"раздел(?:ы)?\s+1\s*[-–]\s*8",
            value,
            flags=re.IGNORECASE,
        ):
            return "Основной договор"

        # --------------------------------------------------------------
        # Пункт X договора
        # --------------------------------------------------------------

        if re.search(
            r"\bдоговора\b",
            value,
            flags=re.IGNORECASE,
        ):
            return "Основной договор"

        return None

    # ------------------------------------------------------------------
    # Find matching conditions
    # ------------------------------------------------------------------

    @staticmethod
    def _find_matching_keys(
        current_conditions: dict[str, str],
        section: str,
        context: str | None = None,
    ) -> list[str]:
        if context:
            key = f"{context}::{section}"

            if key in current_conditions:
                return [key]

            return []

        suffix = f"::{section}"

        matches = []

        for key in current_conditions:
            if key == section:
                matches.append(key)

            elif key.endswith(suffix):
                matches.append(key)

        return matches

    # ------------------------------------------------------------------
    # Key helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_raw_section(
        key: str,
    ) -> str:
        """
        Из:

            Основной договор::3.2

        получает:

            3.2

        А из:

            3.2

        получает:

            3.2
        """

        if "::" in key:
            return key.split(
                "::",
                1,
            )[1]

        return key

    # ------------------------------------------------------------------
    # Addenda sorting
    # ------------------------------------------------------------------

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

    @staticmethod
    def _parse_date(
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

        match = re.search(
            r"(\d{1,2})\s+"
            r"(января|февраля|марта|апреля|мая|июня|"
            r"июля|августа|сентября|октября|ноября|декабря)"
            r"\s+(\d{4})",
            value.lower(),
        )

        if match:
            day = int(match.group(1))
            month = russian_months[
                match.group(2)
            ]
            year = int(match.group(3))

            try:
                return datetime(
                    year,
                    month,
                    day,
                )
            except ValueError:
                return None

        return None

    # ------------------------------------------------------------------
    # Section normalization
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_section(
        value: str | None,
    ) -> str | None:
        if not value:
            return None

        value = re.sub(
            r"\s+",
            " ",
            value.strip(),
        )

        # Пункт 12.2 договора -> 12.2
        match = re.match(
            r"^Пункт\s+(.+?)\s+договора\.?$",
            value,
            flags=re.IGNORECASE,
        )

        if match:
            return match.group(1).strip()

        # п. 12.2 -> 12.2
        match = re.match(
            r"^п\.\s*(\d+(?:\.\d+)*)$",
            value,
            flags=re.IGNORECASE,
        )

        if match:
            return match.group(1)

        # Раздел 3 договора -> 3
        match = re.match(
            r"^Раздел\s+(.+?)\s+договора\.?$",
            value,
            flags=re.IGNORECASE,
        )

        if match:
            return match.group(1).strip()

        # Раздел 3 -> 3
        match = re.match(
            r"^Раздел\s+(.+)$",
            value,
            flags=re.IGNORECASE,
        )

        if match:
            return match.group(1).strip()

        # Приложение № 2 -> Приложение №2
        match = re.match(
            r"^Приложение\s+№\s*(\d+)$",
            value,
            flags=re.IGNORECASE,
        )

        if match:
            return (
                f"Приложение №{match.group(1)}"
            )

        return value
