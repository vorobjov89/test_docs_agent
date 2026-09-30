from app.agent.agent import ContractAgent


def main():
    agent = ContractAgent()

    print("Contract Agent")
    print("Введите 'exit' для выхода.")

    while True:
        query = input("\n> ").strip()

        if query.lower() in {"exit", "quit"}:
            break

        if len(query.strip()) < 3:
            print(
                "Запрос слишком короткий."
                "Опишите, что нужно сделать с документами."
            )
            continue

        if not query:
            continue

        answer = agent.run(query)

        print("\n============================================================")
        print("FINAL ANSWER")
        print("============================================================")
        print(answer)


if __name__ == "__main__":
    main()
