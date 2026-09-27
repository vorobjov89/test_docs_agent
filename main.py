import json
from pathlib import Path

from app.services.pipeline import DocumentPipeline


INPUT_DIR = Path("data/input")
OUTPUT_FILE = Path("data/processed/documents.json")


def main():
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    files = sorted(INPUT_DIR.rglob("*.pdf"))

    if not files:
        print(f"PDF-файлы не найдены в {INPUT_DIR}")
        return

    pipeline = DocumentPipeline()

    results = []

    print(f"Найдено PDF: {len(files)}")
    print()

    for index, file in enumerate(files, start=1):
        # testset = {
        #     "D240114026-01.pdf",
        #     "Проект Договора.pdf",
        #     "Договор ЛК МР Москва и МОАриадна.pdf",
        # }
        # if file.name not in testset:
        #     continue

        print(f"[{index}/{len(files)}] Обработка: {file.name}")

        try:
            result = pipeline.process(file)

            result["filename"] = file.name

            results.append(result)

            if result["status"] == "success":
                data = result.get("data", {})

                print(
                    f"  OK: "
                    f"type={data.get('document_type')}, "
                    f"document_id={data.get('document_id')}, "
                    f"contract_id={data.get('contract_id')}, "
                    f"referenced_contract_id="
                    f"{data.get('referenced_contract_id')}"
                )

            elif result["status"] == "partial":
                print(
                    f"  PARTIAL: "
                    f"failed_chunks={result.get('failed_chunks', [])}"
                )

            elif result["status"] == "rejected":
                print(
                    f"  REJECTED: "
                    f"{result.get('errors', [])}"
                )

        except Exception as exc:
            print(f"  ERROR: {exc}")

            results.append(
                {
                    "status": "error",
                    "filename": file.name,
                    "error": str(exc),
                }
            )

        print()

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            results,
            f,
            ensure_ascii=False,
            indent=2,
        )

    success_count = sum(
        1
        for result in results
        if result["status"] == "success"
    )

    partial_count = sum(
        1
        for result in results
        if result["status"] == "partial"
    )

    rejected_count = sum(
        1
        for result in results
        if result["status"] == "rejected"
    )

    error_count = sum(
        1
        for result in results
        if result["status"] == "error"
    )

    print("=" * 60)
    print("Готово")
    print("=" * 60)
    print(f"Всего документов: {len(results)}")
    print(f"Успешно:           {success_count}")
    print(f"Частично:           {partial_count}")
    print(f"Отклонено:         {rejected_count}")
    print(f"Ошибок:            {error_count}")
    print()
    print(f"Результат сохранён: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
