import re

from langchain_openai import ChatOpenAI

from app.config import (
    YANDEX_API_KEY,
    YANDEX_FOLDER_ID,
    MODEL_URI,
    BASE_URL
)

from app.models.extraction import (
    ExtractedDocument,
    ExtractedChunk,
)


CHUNK_PAGES = 8
OVERLAP_PAGES = 1


DOCUMENT_METADATA_PROMPT = """
Ты анализируешь юридический документ.

Определи реквизиты самого документа.

Извлекай только информацию, которая явно присутствует
в предоставленном тексте.

Правила:

1. Не придумывай значения.
2. Если значение отсутствует или его нельзя надежно определить —
   верни null.
3. document_type может быть только:
   contract
   addendum
   termination
   other

4. document_type = "contract", если документ является
   самостоятельным основным договором или самостоятельным
   соглашением, устанавливающим договорные обязательства
   сторон.

5. document_type = "addendum" только если документ ЯВНО
   является дополнительным соглашением к уже существующему
   основному договору.

   Признаки addendum:
   - используется формулировка "Дополнительное соглашение";
   - явно указано, что документ заключен "к Договору ...";
   - явно указан номер основного договора, который изменяется
     данным документом.

   ВАЖНО:
   Само наличие слова "Соглашение" или номера
   "Соглашение № ..." НЕ означает, что документ является
   дополнительным соглашением.

   Если документ называется "Соглашение № ...", но не содержит
   явной ссылки на основной договор, классифицируй его как
   "contract".

6. Для документа о расторжении/прекращении:
   document_type = "termination",
   только если это явно следует из содержания документа.

7. Не используй имя файла для определения связей.
8. Не путай номер дополнительного соглашения
   с номером основного договора.
9. Не анализируй изменения условий в этом запросе.

10. Если документ содержит реквизиты основного договора
    и не является дополнительным соглашением или документом
    о расторжении/прекращении, классифицируй его как "contract".

11. Если документ является основным договором,
    его document_type должен быть "contract",
    даже если в заголовке документа используется
    нестандартное название.

12. Определи contract_type, если из документа явно следует
тип договора или соглашения.

Для классического договора используй краткое название вида:
- договор оказания услуг
- договор поставки
- договор аренды
- договор коммерческого представительства

Для соглашения, дополнительного соглашения или иного
самостоятельного документа не придумывай тип основного договора.
Если тип документа нельзя надежно определить —
верни contract_type = null.

13. Определи subject для основного договора, соглашения
или иного самостоятельного документа.

subject — это краткое описание того, о чем документ
и какие основные обязательства или отношения он регулирует.

Если есть раздел:
"Предмет договора",
"Предмет соглашения",
"1. Предмет договора",
"2. Предмет соглашения"
или аналогичный раздел, используй его.

Например, для соглашения, устанавливающего дополнительные
плановые показатели и вознаграждение партнеру, subject может
быть сформулирован как:
"установление дополнительных обязательств Партнера
по выполнению плановых показателей и выплата дополнительного
вознаграждения".

14. subject должен быть кратким и содержательным.
Не копируй весь раздел документа целиком.

15. Не придумывай subject.
Он должен основываться на явно присутствующей информации
в документе. Если предмет невозможно определить надежно —
верни null.

16. parties:
    извлеки стороны договора, если они явно указаны.

17. Для contract_type и subject используй информацию
    из всего предоставленного текста документа,
    а не только из первых строк.

18. Не включай в subject номера договоров,
    даты, реквизиты сторон или длинные фрагменты текста.

19. Не используй наличие слова "Соглашение" как единственный
признак дополнительного соглашения.

"Соглашение № ..." и
"Дополнительное соглашение № ... к Договору ..."
— это разные случаи.

Если документ содержит собственный предмет соглашения
и устанавливает самостоятельные обязательства сторон,
но не содержит явной ссылки на изменяемый основной договор,
не классифицируй его как addendum.
"""


CHUNK_PROMPT = """
Ты анализируешь часть уже распознанного юридического документа.

Тип документа, номер договора и другие реквизиты
уже определены отдельно.

Твоя задача — найти в этом фрагменте изменения условий договора.

Извлекай только изменения, которые явно присутствуют
в данном фрагменте.

Правила:

1. Не придумывай изменения.

2. Если в данном фрагменте нет изменений,
   верни:

   changes=[]

3. Для каждого изменения указывай:

   - section
   - change_type
   - description
   - old_value, если он явно указан
   - new_value, если он явно указан
   - old_text, если он явно указан
   - new_text, если он явно присутствует
   - source_page, если страницу можно определить

4. Допустимые значения change_type:

   add
   modify
   delete
   replace_section

5. Если раздел заменяется новой редакцией,
   используй:

   change_type="replace_section"

6. Если условие добавляется,
   используй:

   change_type="add"

7. Если существующее условие изменяется,
   используй:

   change_type="modify"

8. Если условие отменяется,
   используй:

   change_type="delete"

9. Не пересказывай фактический текст документа
   вместо new_text.

10. Если точный текст новой редакции присутствует
    в этом фрагменте, сохраняй его в new_text.

11. Для replace_section в new_text сохраняй
    фактический текст новой редакции раздела,
    если он присутствует в данном фрагменте.

12. Если точный текст невозможно однозначно определить,
    оставляй new_text=null.

13. Не определяй заново:

    - document_type
    - document_id
    - contract_id
    - referenced_contract_id
    - contract_number
    - parties

14. Не используй имя файла как источник информации.

15. Работай только с текстом данного фрагмента.
"""


class DocumentExtractor:

    def __init__(self):

        self.llm = ChatOpenAI(
            model=MODEL_URI,
            base_url=BASE_URL,
            api_key=YANDEX_API_KEY,
            temperature=0,
            default_headers={"OpenAI-Project": YANDEX_FOLDER_ID},
            #max_tokens=MAX_TOKENS
        )

        self.document_llm = (
            self.llm.with_structured_output(
                ExtractedDocument,
                include_raw=True,
            )
        )

        self.chunk_llm = (
            self.llm.with_structured_output(
                ExtractedChunk,
                include_raw=True,
            )
        )

        self.failed_chunks: list[int] = []

    def extract(
        self,
        text: str,
    ) -> ExtractedDocument:

        result = self.document_llm.invoke(
            [
                (
                    "system",
                    DOCUMENT_METADATA_PROMPT,
                ),
                (
                    "human",
                    text,
                ),
            ]
        )

        document = self._parse_document_result(
            result
        )

        return self._normalize_document(
            document
        )

    def extract_pages(
        self,
        pages: list[str],
    ) -> ExtractedDocument:

        if not pages:
            raise ValueError(
                "Не переданы страницы документа."
            )

        self.failed_chunks = []

        metadata_text = self._build_metadata_text(
            pages
        )

        document = self.extract(
            metadata_text
        )

        chunks = self._make_chunks(pages)

        all_changes = []

        for index, chunk in enumerate(
            chunks,
            start=1,
        ):
            print(
                f"    Extraction chunk "
                f"{index}/{len(chunks)}"
            )

            try:
                extracted_chunk = self._extract_chunk(
                    chunk
                )

                all_changes.extend(
                    extracted_chunk.changes
                )

            except Exception as exc:
                self.failed_chunks.append(index)

                print(
                    f"    Chunk {index} failed: "
                    f"{exc}"
                )

        document.changes = all_changes

        return document

    def _extract_chunk(
        self,
        chunk: str,
    ) -> ExtractedChunk:

        result = self.chunk_llm.invoke(
            [
                (
                    "system",
                    CHUNK_PROMPT,
                ),
                (
                    "human",
                    chunk,
                ),
            ]
        )

        return self._parse_chunk_result(result)

    def _parse_document_result(
        self,
        result,
    ) -> ExtractedDocument:

        parsed = result.get("parsed")

        if parsed is not None:
            return parsed

        parsing_error = result.get(
            "parsing_error"
        )

        raw = result.get("raw")

        raw_content = getattr(
            raw,
            "content",
            None,
        )

        raise RuntimeError(
            "LLM не вернул структурированный "
            "результат для metadata. "
            f"parsing_error={parsing_error}; "
            f"raw_content={raw_content}"
        )

    def _parse_chunk_result(
        self,
        result,
    ) -> ExtractedChunk:

        parsed = result.get("parsed")

        if parsed is not None:
            return parsed

        parsing_error = result.get(
            "parsing_error"
        )

        raw = result.get("raw")

        raw_content = getattr(
            raw,
            "content",
            None,
        )

        raise RuntimeError(
            "LLM не вернул структурированный "
            "результат для chunk. "
            f"parsing_error={parsing_error}; "
            f"raw_content={raw_content}"
        )

    def _build_metadata_text(
        self,
        pages: list[str],
    ) -> str:

        # Для коротких документов передаём весь текст.
        full_text = "\n\n".join(
            (
                f"[PAGE {index}]\n{page}"
            )
            for index, page in enumerate(
                pages,
                start=1,
            )
        )

        # Ориентировочный безопасный лимит.
        # Не пытаемся использовать весь лимит 32768 токенов:
        # оставляем запас на system prompt и токенизацию.
        MAX_CHARS = 30000

        if len(full_text) <= MAX_CHARS:
            return full_text

        # Для больших документов выбираем страницы,
        # наиболее полезные для определения metadata.
        keywords = [
            "дополнительное соглашение",
            "к договору",
            "предмет договора",
            "предмет соглашения",
            "стороны",
            "заключили настоящий договор",
            "заключили настоящее соглашение",
            "реквизиты",
        ]

        selected_indices: set[int] = set()

        # Первые страницы обычно содержат:
        # название документа, номер, дату и стороны.
        for index in range(
            min(3, len(pages))
        ):
            selected_indices.add(index)

        # Последние страницы могут содержать
        # подписи и реквизиты.
        for index in range(
            max(0, len(pages) - 2),
            len(pages),
        ):
            selected_indices.add(index)

        # Добавляем страницы с ключевыми признаками.
        for index, page in enumerate(pages):
            page_lower = page.lower()

            if any(
                keyword in page_lower
                for keyword in keywords
            ):
                selected_indices.add(index)

        selected_pages = []

        current_chars = 0

        for index in sorted(selected_indices):

            page_text = (
                f"[PAGE {index + 1}]\n"
                f"{pages[index]}"
            )

            # Не превышаем жёсткий лимит.
            if (
                current_chars + len(page_text)
                > MAX_CHARS
            ):
                continue

            selected_pages.append(page_text)

            current_chars += len(page_text)

        return "\n\n".join(selected_pages)

    def _make_chunks(
        self,
        pages: list[str],
    ) -> list[str]:

        chunks = []

        step = CHUNK_PAGES - OVERLAP_PAGES

        for start in range(
            0,
            len(pages),
            step,
        ):
            end = min(
                start + CHUNK_PAGES,
                len(pages),
            )

            chunk_pages = pages[start:end]

            chunk_text = "\n\n".join(
                (
                    f"[PAGE {page_number}]\n"
                    f"{page_text}"
                )
                for page_number, page_text in enumerate(
                    chunk_pages,
                    start=start + 1,
                )
            )

            if chunk_text.strip():
                chunks.append(chunk_text)

            if end >= len(pages):
                break

        return chunks

    def _normalize_document(
        self,
        document: ExtractedDocument,
    ) -> ExtractedDocument:

        nullable_fields = [
            "document_id",
            "contract_id",
            "referenced_contract_id",
            "contract_number",
            "document_date",
            "effective_date",
            "contract_type",
            "subject",
        ]

        for field in nullable_fields:
            value = getattr(document, field)

            if isinstance(value, str):
                normalized = value.strip().lower()

                if normalized in {
                    "null",
                    "none",
                    "n/a",
                    "не указано",
                }:
                    setattr(
                        document,
                        field,
                        None,
                    )

        # Для addendum/termination:
        # contract_number содержит собственный номер документа,
        # если LLM не заполнила document_id.
        if (
            document.document_type in {
                "addendum",
                "termination",
            }
            and document.document_id is None
            and document.contract_number
        ):
            document.document_id = (
                document.contract_number
            )

        # Если LLM не определила ссылку на основной договор,
        # пытаемся извлечь её из уже сформированного subject.
        if (
            document.document_type == "addendum"
            and document.referenced_contract_id is None
            and document.subject
        ):
            match = re.search(
                r"№\s*(D\d{9,}-\d+)",
                document.subject,
                flags=re.IGNORECASE,
            )

            if match:
                document.referenced_contract_id = (
                    match.group(1)
                )

        # Для addendum основной contract_id — это ID
        # договора, который изменяется.
        if (
            document.document_type in {
                "addendum",
                "termination",
            }
            and document.contract_id is None
            and document.referenced_contract_id
        ):
            document.contract_id = (
                document.referenced_contract_id
            )

        # Для основного договора его ID является
        # одновременно ID документа.
        if (
            document.document_type == "contract"
            and document.document_id is None
            and document.contract_id
        ):
            document.document_id = (
                document.contract_id
            )

        return document