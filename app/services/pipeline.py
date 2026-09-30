from pathlib import Path

from app.services.pdf_parser import PDFParser
from app.services.extractor import DocumentExtractor
from app.services.validator import ExtractionValidator


class DocumentPipeline:

    def __init__(self):
        self.parser = PDFParser()
        self.extractor = DocumentExtractor()
        self.validator = ExtractionValidator()

    def process(
        self,
        path: str | Path,
    ) -> dict:

        path = Path(path)

        # Сбрасываем состояние предыдущего документа.
        self.extractor.failed_chunks = []

        pages = self.parser.parse_pages(path)

        if not pages:
            raise ValueError(
                f"Could not extract text from {path.name}"
            )

        extracted = self.extractor.extract_pages(
            pages
        )

        errors = self.validator.validate(
            extracted
        )

        failed_chunks = list(
            self.extractor.failed_chunks
        )

        # Ошибки в обязательных метаданных.
        if errors:
            return {
                "status": "rejected",
                "filename": path.name,
                "pages": len(pages),
                "errors": errors,
                "failed_chunks": failed_chunks,
                "data": extracted.model_dump(),
            }

        # Документ распознан, но часть чанков
        # не удалось обработать.
        if failed_chunks:
            return {
                "status": "partial",
                "filename": path.name,
                "pages": len(pages),
                "failed_chunks": failed_chunks,
                "data": extracted.model_dump(),
            }

        # Документ обработан полностью.
        return {
            "status": "success",
            "filename": path.name,
            "pages": len(pages),
            "failed_chunks": [],
            "data": extracted.model_dump(),
        }
