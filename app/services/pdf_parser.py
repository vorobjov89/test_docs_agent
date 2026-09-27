from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image


class PDFParser:

    def parse(
        self,
        path: str | Path,
    ) -> tuple[str, int]:

        pages = self.parse_pages(path)

        full_text = "\n".join(pages).strip()

        if not full_text:
            raise ValueError(
                f"Could not extract text from {path}"
            )

        return full_text, len(pages)

    def parse_pages(
        self,
        path: str | Path,
    ) -> list[str]:

        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(path)

        if path.suffix.lower() != ".pdf":
            raise ValueError(
                f"Unsupported file type: {path.suffix}"
            )

        doc = pymupdf.open(path)

        pages = []

        try:
            for page in doc:
                text = page.get_text("text").strip()

                if text:
                    pages.append(text)
                    continue

                ocr_text = self._ocr_page(page)

                pages.append(
                    ocr_text if ocr_text else ""
                )

        finally:
            doc.close()

        return pages

    def _ocr_page(
        self,
        page: pymupdf.Page,
    ) -> str:

        pixmap = page.get_pixmap(
            dpi=300,
            alpha=False,
        )

        image = Image.frombytes(
            "RGB",
            [
                pixmap.width,
                pixmap.height,
            ],
            pixmap.samples,
        )

        text = pytesseract.image_to_string(
            image,
            lang="rus+eng",
            config="--psm 6",
        )

        return text.strip()
    