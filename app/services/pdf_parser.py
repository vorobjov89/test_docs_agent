from pathlib import Path

import pymupdf


class PDFParser:

    def parse(self, path: str | Path) -> tuple[str, int]:
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(path)

        if path.suffix.lower() != ".pdf":
            raise ValueError(
                f"Unsupported file type: {path.suffix}"
            )

        doc = pymupdf.open(path)

        pages = []

        for page in doc:
            text = page.get_text("text")
            pages.append(text)

        doc.close()

        full_text = "\n".join(pages).strip()

        if not full_text:
            raise ValueError(
                f"Could not extract text from {path.name}"
            )

        return full_text, len(pages)