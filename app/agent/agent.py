from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.reflection import AgentReflection
from app.agent.tools import TOOLS, get_extraction_issues
from app.config import (
    MODEL,
    BASE_URL,
    API_KEY,
    FOLDER_ID,
)

MAX_MESSAGES = 12


class ContractAgent:
    def __init__(self):
        if FOLDER_ID:
            model = ChatOpenAI(
                model=MODEL,
                base_url=BASE_URL,
                api_key=API_KEY,
                temperature=0,
                default_headers={
                    "OpenAI-Project": FOLDER_ID
                },
            )
        else:
            model = ChatOpenAI(
                model=MODEL,
                base_url=BASE_URL,
                api_key=API_KEY,
                temperature=0,
            )

        self.agent = create_agent(
            model=model,
            tools=TOOLS,
            system_prompt=SYSTEM_PROMPT,
        )

        self.reflection = AgentReflection()

        # In-process conversational memory.
        # История живёт в рамках одного запуска agent_main.py.
        self.messages = []

    def _trim_history(self) -> None:
        if len(self.messages) > MAX_MESSAGES:
            self.messages = self.messages[-MAX_MESSAGES:]

    def run(self, query: str) -> str:
        self._trim_history()
        query = query.strip()

        print(f"[AGENT] Запрос: {query}")

        self.messages.append(
            {
                "role": "user",
                "content": query,
            }
        )

        result = self.agent.invoke(
            {
                "messages": self.messages,
            }
        )

        # Сохраняем всю историю диалога вместе с tool calls
        # и результатами инструментов.
        self.messages = result["messages"]

        messages = result["messages"]
        self._trim_history()

        self._log_messages(messages)

        print("[QUALITY] Проверка качества исходных данных...")

        extraction_issues = get_extraction_issues.invoke({})

        print("[QUALITY RESULT]")
        print(extraction_issues)

        answer = self._get_final_answer(messages)

        tool_results = self._get_tool_results(messages)

        tool_results += (
            "\n\nTOOL: get_extraction_issues\n"
            + extraction_issues
        )

        print("[REFLECTION] Проверка ответа...")

        reflection = self.reflection.check(
            query=query,
            answer=answer,
            tool_results=tool_results,
        )

        print("[REFLECTION]")
        print(f"passed: {reflection.passed}")

        if reflection.issues:
            for issue in reflection.issues:
                print(f"- {issue}")

        if reflection.passed:
            print("[REFLECTION] Проверка пройдена.")
            return answer

        # ---------------------------------------------------------
        # Первая проверка не пройдена → запрашиваем исправление
        # ---------------------------------------------------------

        print(
            "[REFLECTION] Обнаружены проблемы. "
            "Запрашиваю исправленный ответ."
        )

        answer, regenerated_messages = self._regenerate(
            query=query,
            previous_answer=answer,
            issues=reflection.issues,
        )

        # ---------------------------------------------------------
        # Повторная проверка исправленного ответа
        # ---------------------------------------------------------

        print("[REFLECTION] Повторная проверка исправленного ответа...")

        regenerated_tool_results = self._get_tool_results(
            regenerated_messages
        )

        regenerated_tool_results += (
            "\n\nTOOL: get_extraction_issues\n"
            + extraction_issues
        )

        reflection = self.reflection.check(
            query=query,
            answer=answer,
            tool_results=regenerated_tool_results,
        )

        print("[REFLECTION]")
        print(f"passed: {reflection.passed}")

        if reflection.issues:
            for issue in reflection.issues:
                print(f"- {issue}")

        if reflection.passed:
            print("[REFLECTION] Исправленный ответ прошёл проверку.")
        else:
            print(
                "[REFLECTION] Исправленный ответ всё ещё "
                "содержит проблемы."
            )

        return answer

    def _get_final_answer(self, messages) -> str:
        for message in reversed(messages):
            if (
                message.type == "ai"
                and message.content
                and not getattr(message, "tool_calls", [])
            ):
                return message.content

        return ""

    def _get_tool_results(self, messages) -> str:
        results = []

        for message in messages:
            if message.type == "tool":
                results.append(
                    f"TOOL: {message.name}\n"
                    f"{message.content}"
                )

        return "\n\n".join(results)

    def _log_messages(self, messages):
        for message in messages:
            tool_calls = getattr(message, "tool_calls", [])

            if tool_calls:
                for call in tool_calls:
                    tool_name = call["name"]
                    tool_args = call.get("args", {})

                    if tool_args:
                        args_text = ", ".join(
                            f"{key}={value}"
                            for key, value in tool_args.items()
                        )
                        print(
                            f"[AGENT ACTION] Следующий шаг: "
                            f"вызвать {tool_name} ({args_text})"
                        )
                    else:
                        print(
                            f"[AGENT ACTION] Следующий шаг: "
                            f"вызвать {tool_name}"
                        )

                    print(f"[TOOL] {tool_name}")

            if message.type == "tool":
                print(f"[TOOL RESULT] {message.name}")

    def _regenerate(
        self,
        query: str,
        previous_answer: str,
        issues: list[str],
    ):
        correction = (
            "Исправь предыдущий ответ по результатам проверки качества.\n\n"
            f"Исходный запрос пользователя:\n{query}\n\n"
            f"Предыдущий ответ:\n{previous_answer}\n\n"
            "Замечания проверки:\n"
            + "\n".join(f"- {issue}" for issue in issues)
            + "\n\n"
            "Сформируй новый ответ на исходный запрос. "
            "Если предыдущий ответ не использовал нужный инструмент, "
            "самостоятельно вызови необходимый инструмент. "
            "Не ограничивайся исправлением текста предыдущего ответа."
        )

        result = self.agent.invoke(
            {
                "messages": [
                    HumanMessage(content=correction),
                ]
            }
        )

        messages = result["messages"]
        answer = self._get_final_answer(messages)

        return answer, messages