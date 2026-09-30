import re

from langchain_openai import ChatOpenAI

from app.config import (
    API_KEY,
    FOLDER_ID,
    MODEL,
    BASE_URL,
)

from app.models.extraction import (
    ExtractedDocument,
    ExtractedChunk,
)


CHUNK_PAGES = 8
OVERLAP_PAGES = 1


DOCUMENT_METADATA_PROMPT = """
Ты анализируешь юридический документ.

Определи реквизиты самого документа и его связь
с основным договором, если такая связь явно указана.

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

5.1. Если документ содержит самостоятельные реквизиты договора,
стороны, предмет договора и условия, устанавливающие
основные договорные отношения между сторонами, классифицируй
его как "contract", если в тексте нет ЯВНОЙ формулировки,
что данный документ является дополнительным соглашением
к другому договору.

5.2. Если документ имеет собственный номер вида DXXXXXXXXX-XX
и содержит самостоятельный предмет договора, это само по себе
не является признаком addendum.

5.3. Не классифицируй документ как addendum только потому,
что в нём встречаются:
- слово "соглашение";
- ссылка на другой договор;
- формулировки об изменении условий;
- приложения;
- номер другого договора.

5.4. Для addendum должна существовать явная связь:
текущий документ является дополнительным соглашением,
а другой документ является основным договором, который
этим соглашением изменяется.

5.5. Если документ по структуре является самостоятельным
договором, а ссылка на другой договор встречается только
в контексте его содержания, классифицируй документ как
"contract".

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
    в документе.

    Если предмет невозможно определить надежно —
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

    "Соглашение № ..."
    и
    "Дополнительное соглашение № ... к Договору ..."
    — это разные случаи.

20. Если документ является дополнительным соглашением,
    обязательно попытайся определить основной договор,
    который изменяется данным документом.

    referenced_contract_id — это идентификатор основного договора,
    к которому относится дополнительное соглашение.

    Извлекай его, если в тексте явно присутствует номер договора,
    например:

    - "к Договору № D210003801-01"
    - "к Договору D210003801-01"
    - "Договор коммерческого представительства от D210003801-01"
    - "изменения в Договор D210003801-01"
    - "к договору D210003801-01"

    Если основной договор явно указан, но формулировка отличается
    от приведенных примеров, всё равно извлеки его номер.

    Не путай referenced_contract_id с document_id:
    document_id — идентификатор текущего документа,
    referenced_contract_id — идентификатор основного договора.

21. Если в документе есть несколько номеров договоров,
    внимательно определи, какой из них является именно
    основным договором, который изменяется данным документом.

    Не выбирай номер только по его расположению.

22. Для addendum:
    - document_id — номер самого дополнительного соглашения;
    - referenced_contract_id — номер основного договора;
    - contract_id — номер основного договора, если он явно
      определен.

23. Для основного договора:
    - document_id — идентификатор основного договора;
    - contract_id — идентификатор основного договора.

24. Если идентификатор невозможно надежно определить,
    верни null.

25. Не используй имя файла как источник document_id,
    contract_id или referenced_contract_id.

26. Если документ содержит собственный предмет соглашения
    и устанавливает самостоятельные обязательства сторон,
    но не содержит явной ссылки на изменяемый основной договор,
    не классифицируй его как addendum.
"""


CHUNK_PROMPT = """
Ты анализируешь часть уже распознанного юридического документа.

Тип документа, номер документа, основной договор и другие
реквизиты уже определены отдельно.

Твоя задача — извлечь из данного фрагмента юридически значимые
изменения, дополнения, отмены и новые условия, относящиеся
к основному договору.

ВАЖНО:

Для дополнительного соглашения изменением считается не только
явная формулировка вида:

- "внести изменения";
- "изложить пункт в новой редакции";
- "дополнить пункт";
- "заменить пункт";
- "признать пункт утратившим силу".

Дополнительное соглашение также может вводить новый блок
юридически значимых условий, который начинает регулировать
отношения сторон.

Например:

- новые права или обязанности сторон;
- новый порядок действий сторон;
- дополнительные обязательства;
- новые правила расчета или выплаты вознаграждения;
- новые показатели, лимиты, ставки или тарифы;
- новые требования к исполнению договора;
- новые правила ответственности;
- новое приложение к договору;
- новая редакция существующего приложения;
- отмена или прекращение действия ранее заключенного
  дополнительного соглашения.

Такие положения также необходимо извлекать как изменения.

Извлекай только информацию, которая явно присутствует
в данном фрагменте.

Правила:

1. Не придумывай изменения.

2. Если в данном фрагменте действительно нет юридически
   значимых изменений или новых условий, верни:

   changes=[]

3. Если документ является дополнительным соглашением и фрагмент
   содержит новые юридически значимые условия, не возвращай
   changes=[] только потому, что в тексте отсутствует явная
   формулировка "внести изменения".

4. Для каждого изменения указывай:

   - section
   - section_context, если контекст явно определяется
   - change_type
   - description
   - old_value, если он явно указан
   - new_value, если он явно указан
   - old_text, если он явно указан
   - new_text, если он явно присутствует
   - source_page, если страницу можно определить

5. Допустимые значения change_type:

   add
   modify
   delete
   replace_section

6. Используй change_type="add", если:

   - вводится новое условие;
   - устанавливаются новые права или обязанности;
   - вводится дополнительное обязательство;
   - устанавливаются новые показатели, ставки, размеры
     вознаграждения или порядок его расчета;
   - вводится новый порядок действий;
   - добавляется новое приложение;
   - дополнительное соглашение содержит самостоятельный новый
     блок регулирования, относящийся к основному договору.

7. Используй change_type="modify", если существующее условие
   изменяется частично или устанавливается новое значение
   существующего условия.

8. Используй change_type="delete", если существующее условие
   или ранее действовавшее положение отменяется.

9. Если документ явно устанавливает, что ранее заключенное
   дополнительное соглашение или иное условие больше не действует,
   используй change_type="delete" или "modify" в зависимости
   от характера изменения и явно опиши это в description.

10. Используй change_type="replace_section", если явно указано,
    что существующий раздел, пункт или приложение излагается
    в новой редакции.

11. Для replace_section в section указывай конкретный заменяемый
    раздел, пункт или приложение, если его можно определить.

    Например:

    section = "Приложение №6 к Договору"

12. Если дополнительное соглашение вводит новый большой раздел
    условий, который не является заменой конкретного пункта
    основного договора, можно представить этот блок как одно
    или несколько укрупненных изменений типа "add".

    Не разбивай автоматически каждый подпункт нового блока
    на отдельное изменение, если это не нужно для понимания
    содержания.

13. Если в одном фрагменте содержится несколько самостоятельных
    юридически значимых изменений, извлеки их отдельно.

14. Не считай изменением:

    - преамбулу;
    - реквизиты сторон сами по себе;
    - подписи;
    - номера страниц;
    - техническое оформление;
    - повторение текста без изменения юридического содержания.

15. Если приложение содержит новую редакцию приложения договора,
    извлеки это как replace_section.

16. Если приложение является новым приложением и явно вводится
    дополнительным соглашением, извлеки его как add.

17. Если точный текст новой редакции присутствует
    в данном фрагменте, сохраняй его в new_text.

18. Для replace_section в new_text сохраняй фактический текст
    новой редакции раздела или приложения, если он присутствует
    в данном фрагменте.

19. Для большого нового блока условий допускается использовать
    в new_text фактический текст этого блока, если он целиком
    присутствует в данном фрагменте.

20. Если точный текст невозможно однозначно определить,
    оставляй new_text=null.

21. description должен кратко объяснять юридический смысл
    изменения, а не просто повторять заголовок раздела.

22. Не пересказывай весь документ.

23. Не определяй заново:

    - document_type
    - document_id
    - contract_id
    - referenced_contract_id
    - contract_number
    - parties

24. Не используй имя файла как источник информации.

25. Работай только с текстом данного фрагмента.

26. Всегда указывай source_page, если в начале фрагмента
    присутствуют маркеры вида [PAGE N].

27. Не создавай изменение только потому, что в тексте
    упоминается другой договор или другое дополнительное
    соглашение.

28. Если документ содержит одновременно явную замену
    существующего пункта и новые дополнительные условия,
    извлеки оба типа изменений.

29. Не требуй наличия слов "изменение", "дополнение",
    "новая редакция" или аналогичных слов, если из текста
    явно следует, что дополнительное соглашение устанавливает
    новые юридически значимые условия.

30. Приоритет — полнота извлечения юридически значимых изменений
    при сохранении требования не придумывать информацию.
"""


class DocumentExtractor:

    def __init__(self):

        if FOLDER_ID:
            self.llm = ChatOpenAI(
                model=MODEL,
                base_url=BASE_URL,
                api_key=API_KEY,
                temperature=0,
                default_headers={
                    "OpenAI-Project": FOLDER_ID
                },
            )
        else:
            self.llm = ChatOpenAI(
                model=MODEL,
                base_url=BASE_URL,
                api_key=API_KEY,
                temperature=0,
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

        chunks = self._make_chunks(
            pages
        )

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

        return self._parse_chunk_result(
            result
        )

    def _parse_document_result(
        self,
        result,
    ) -> ExtractedDocument:

        parsed = result.get(
            "parsed"
        )

        if parsed is not None:
            return parsed

        parsing_error = result.get(
            "parsing_error"
        )

        raw = result.get(
            "raw"
        )

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

        parsed = result.get(
            "parsed"
        )

        if parsed is not None:
            return parsed

        parsing_error = result.get(
            "parsing_error"
        )

        raw = result.get(
            "raw"
        )

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

        full_text = "\n\n".join(
            (
                f"[PAGE {index}]\n{page}"
            )
            for index, page in enumerate(
                pages,
                start=1,
            )
        )

        MAX_CHARS = 30000

        if len(full_text) <= MAX_CHARS:
            return full_text

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

        # Первые страницы:
        # название, номер, дата, стороны.
        for index in range(
            min(3, len(pages))
        ):
            selected_indices.add(index)

        # Последние страницы:
        # подписи и реквизиты.
        for index in range(
            max(0, len(pages) - 2),
            len(pages),
        ):
            selected_indices.add(index)

        # Страницы с ключевыми признаками.
        for index, page in enumerate(pages):

            page_lower = page.lower()

            if any(
                keyword in page_lower
                for keyword in keywords
            ):
                selected_indices.add(index)

        selected_pages = []

        current_chars = 0

        for index in sorted(
            selected_indices
        ):

            page_text = (
                f"[PAGE {index + 1}]\n"
                f"{pages[index]}"
            )

            if (
                current_chars + len(page_text)
                > MAX_CHARS
            ):
                continue

            selected_pages.append(
                page_text
            )

            current_chars += len(
                page_text
            )

        return "\n\n".join(
            selected_pages
        )

    def _make_chunks(
        self,
        pages: list[str],
    ) -> list[str]:

        chunks = []

        step = (
            CHUNK_PAGES
            - OVERLAP_PAGES
        )

        for start in range(
            0,
            len(pages),
            step,
        ):

            end = min(
                start + CHUNK_PAGES,
                len(pages),
            )

            chunk_pages = pages[
                start:end
            ]

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
                chunks.append(
                    chunk_text
                )

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

            value = getattr(
                document,
                field,
            )

            if isinstance(
                value,
                str,
            ):

                normalized = (
                    value
                    .strip()
                    .lower()
                )

                if normalized in {
                    "null",
                    "none",
                    "n/a",
                    "не указано",
                    "",
                }:
                    setattr(
                        document,
                        field,
                        None,
                    )

        # ---------------------------------------------------------
        # Нормализация идентификаторов.
        # ---------------------------------------------------------
        #
        # LLM может вернуть:
        # d210003801-01
        # D210003801_01
        # D210003801 - 01
        #
        # Приводим такие значения к единому виду.
        #
        document.document_id = (
            self._normalize_contract_id(
                document.document_id
            )
        )

        document.contract_id = (
            self._normalize_contract_id(
                document.contract_id
            )
        )

        document.referenced_contract_id = (
            self._normalize_contract_id(
                document.referenced_contract_id
            )
        )

        document.contract_number = (
            self._normalize_contract_id(
                document.contract_number
            )
        )

        # ---------------------------------------------------------
        # Для addendum / termination:
        #
        # contract_number обычно является номером
        # самого документа, если document_id не определён.
        # ---------------------------------------------------------

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

        # ---------------------------------------------------------
        # Fallback:
        #
        # Если LLM не определила ссылку на основной договор,
        # пытаемся извлечь её из subject.
        #
        # ВАЖНО:
        # не требуем символ "№".
        #
        # Поддерживаются:
        #
        # № D210003801-01
        # D210003801-01
        # Договор D210003801-01
        # от D210003801-01 от ...
        # ---------------------------------------------------------

        if (
            document.document_type == "addendum"
            and document.referenced_contract_id is None
            and document.subject
        ):

            referenced_contract_id = (
                self._extract_contract_id(
                    document.subject
                )
            )

            if referenced_contract_id:
                document.referenced_contract_id = (
                    referenced_contract_id
                )

        # ---------------------------------------------------------
        # Для addendum основной contract_id —
        # это ID договора, который изменяется.
        # ---------------------------------------------------------

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

        # ---------------------------------------------------------
        # Для основного договора:
        #
        # его ID одновременно является ID документа.
        # ---------------------------------------------------------

        if (
            document.document_type == "contract"
            and document.document_id is None
            and document.contract_id
        ):
            document.document_id = (
                document.contract_id
            )

        return document

    @staticmethod
    def _extract_contract_id(
        text: str | None,
    ) -> str | None:

        if not text:
            return None

        # Ищем стандартный формат идентификатора:
        #
        # D210003801-01
        #
        # Допускаем пробелы вокруг дефиса и "_" вместо "-",
        # поскольку OCR/LLM иногда искажает формат.
        match = re.search(
            r"\bD\d{9,}\s*[-_]\s*\d+\b",
            text,
            flags=re.IGNORECASE,
        )

        if not match:
            return None

        value = match.group(0)

        value = (
            value
            .upper()
            .replace("_", "-")
            .replace(" ", "")
        )

        return value

    @staticmethod
    def _normalize_contract_id(
        value: str | None,
    ) -> str | None:

        if not value:
            return None

        value = value.strip()

        if not value:
            return None

        # Normal ID: D150641492-09 / D150641492_09
        match = re.search(
            r"\bD\d{9,}\s*[-_]\s*\d+\b",
            value,
            flags=re.IGNORECASE,
        )

        if match:
            return (
                match.group(0)
                .upper()
                .replace("_", "-")
                .replace(" ", "")
            )

        # OCR variant: 0150641492-09 -> D150641492-09
        # The leading zero replaces the letter D.
        ocr_match = re.search(
            r"\b0(\d{9,})\s*[-_]\s*(\d+)\b",
            value,
        )

        if ocr_match:
            return (
                f"D{ocr_match.group(1)}-"
                f"{ocr_match.group(2)}"
            )

        return value
