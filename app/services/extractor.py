from langchain_openai import ChatOpenAI

from app.config import (
    YANDEX_API_KEY,
    YANDEX_FOLDER_ID,
    MODEL_URI,
    BASE_URL
)
from app.models.extraction import ExtractedDocument


EXTRACTION_PROMPT = """
Ты извлекаешь структурированные данные из юридических документов.

Твоя задача — извлечь только информацию, которая явно присутствует
в тексте документа.

Правила:

1. Не придумывай значения.
2. Если значение отсутствует или не может быть надежно определено,
   возвращай null.
3. Не делай вывод о текущем состоянии договора.
4. Для дополнительного соглашения определи договор,
   к которому оно относится, если такая связь явно указана.
5. Фиксируй изменения условий договора.
6. Если целый раздел заменяется новой редакцией,
   используй change_type="replace_section".
7. Если условие добавляется, используй change_type="add".
8. Если существующее условие изменяется,
   используй change_type="modify".
9. Если условие отменяется,
   используй change_type="delete".
10. Имя файла не является доказательством связи документов.
11. Для каждого изменения указывай страницу,
    если страницу можно определить.
12. Если информация неоднозначна, не угадывай.

Если значение не подтверждается текстом документа,
не записывай его как факт.
"""


class DocumentExtractor:

    def __init__(self):
        self.llm = ChatOpenAI(
            model=MODEL_URI,
            base_url=BASE_URL,
            api_key=YANDEX_API_KEY,
            temperature=0,
            default_headers={"OpenAI-Project": YANDEX_FOLDER_ID},
        )

        self.structured_llm = (
            self.llm.with_structured_output(
                ExtractedDocument
            )
        )

    def extract(
        self,
        text: str,
    ) -> ExtractedDocument:

        response = self.structured_llm.invoke(
            [
                (
                    "system",
                    EXTRACTION_PROMPT,
                ),
                (
                    "human",
                    f"""
Извлеки структурированные данные
из следующего документа.

ТЕКСТ ДОКУМЕНТА:

{text}
""",
                ),
            ]
        )

        return response