import json

from app.services.pipeline import DocumentPipeline


def main():
    pipeline = DocumentPipeline()

    result = pipeline.process(
        "data/input/Задание_Договор D210262441-01/D250134282-01.pdf"
    )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()