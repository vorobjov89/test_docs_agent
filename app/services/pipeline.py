from pathlib import Path

from app.services.pdf_parser import PDFParser
from app.services.extractor import DocumentExtractor
from app.services.validator import ExtractionValidator


class DocumentPipeline:

    def __init__(self):
        self.parser = PDFParser()
        self.extractor = DocumentExtractor()
        self.validator = ExtractionValidator()

    def process(self, path: str | Path) -> dict:

        path = Path(path)

        # 1. PDF → text
        text, pages = self.parser.parse(path)

        # 2. text → structured data
        extracted = self.extractor.extract(text)

        # 3. validation
        errors = self.validator.validate(
            extracted
        )

        if errors:
            return {
                "status": "rejected",
                "filename": path.name,
                "pages": pages,
                "errors": errors,
                "data": extracted.model_dump(),
            }

        return {
            "status": "success",
            "filename": path.name,
            "pages": pages,
            "data": extracted.model_dump(),
        }