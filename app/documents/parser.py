
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pymupdf

from .models import Document, DocumentType


ID_RE = re.compile(r"(?<![A-Za-z0-9])D\d{6,}(?:-\d{2})?(?![A-Za-z0-9])", re.I)
OCR_NUM_ID_RE = re.compile(r"\b0?(\d{9,})-(\d{2})\b")

MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4,
    "мая": 5, "июня": 6, "июля": 7, "августа": 8,
    "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}

RUS_DATE_RE = re.compile(
    r"(?:«\s*)?(\d{1,2})(?:\s*»)?\s+"
    r"(января|февраля|марта|апреля|мая|июня|июля|августа|"
    r"сентября|октября|ноября|декабря)\s+(\d{4})",
    re.I,
)
NUM_DATE_RE = re.compile(r"\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b")


def normalize_id(value: str) -> str:
    value = value.upper()
    if "-" not in value:
        # Most source IDs have a two-digit suffix. Do not invent it.
        return value
    return value


def extract_ids(text: str) -> list[str]:
    ids = {normalize_id(x) for x in ID_RE.findall(text)}
    # OCR can drop the Latin D and keep a leading zero (e.g. 0220600738-01).
    for number, suffix in OCR_NUM_ID_RE.findall(text):
        ids.add(f"D{number}-{suffix}")
    return sorted(ids)


def extract_dates(text: str) -> list[date]:
    result: list[date] = []

    for day, month, year in RUS_DATE_RE.findall(text):
        try:
            result.append(date(int(year), MONTHS[month.lower()], int(day)))
        except ValueError:
            pass

    for day, month, year in NUM_DATE_RE.findall(text):
        try:
            result.append(date(int(year), int(month), int(day)))
        except ValueError:
            pass

    return sorted(set(result))


def infer_type(text: str, filename: str) -> DocumentType:
    header = text[:500].lower()

    # Classify from the document title, not from definitions in the body.
    if re.search(r"(?:^|\n)\s*дополнительное\s+соглашение", header):
        return DocumentType.ADDENDUM
    if re.search(r"(?:^|\n)\s*(?:договор|cоглашение|соглашение)\b", header):
        if "договор" in header[:250]:
            return DocumentType.CONTRACT
        return DocumentType.AGREEMENT

    sample = filename.lower()
    if "договор" in sample:
        return DocumentType.CONTRACT
    if "соглашение" in sample:
        return DocumentType.ADDENDUM

    return DocumentType.UNKNOWN


def extract_document_id(text: str, path: Path) -> str:
    header = text[:3000]

    # Prefer the ID explicitly attached to the document title.
    title_patterns = [
        r"дополнительное\s+соглашение\s+№\s*\d+\s*\(\s*(D\d{6,}(?:-\d{2})?)\s*\)",
        r"дополнительное\s+соглашение\s+№\s*(D\d{6,}(?:-\d{2})?)",
        r"(?:договор|соглашение|cоглашение|Cоглашение)\s*(?:коммерческого представительства)?\s*№\s*(D\d{6,}(?:-\d{2})?)",
    ]
    for pattern in title_patterns:
        match = re.search(pattern, header, flags=re.I)
        if match:
            return normalize_id(match.group(1))

    # For scanned PDFs OCR can corrupt the title ID. The filename is then
    # the safer fallback, provided it contains a canonical ID.
    filename_ids = extract_ids(path.stem)
    if filename_ids:
        return filename_ids[0]

    ids = extract_ids(header)
    if ids:
        return ids[0]
    return path.stem


def extract_parties(text: str) -> list[str]:
    parties: list[str] = []

    known_patterns = [
        r"Публичное Акционерное Общество\s+«[^»]+»",
        r"Публичное акционерное общество\s+«[^»]+»",
        r"Общество с ограниченной ответственностью\s+«[^»]+»",
        r"Индивидуальный предприниматель\s+[А-ЯЁ][^,.\n]{2,80}",
    ]

    for pattern in known_patterns:
        parties.extend(re.findall(pattern, text, flags=re.I))

    # Deduplicate while preserving order.
    return list(dict.fromkeys(x.strip() for x in parties))



def extract_parent_contract_ids(text: str, document_id: str) -> list[str]:
    """Extract IDs that are explicitly described as the base contract/agreement."""
    header = text[:5000]
    patterns = [
        r"(?:к|по)\s+(?:Договору|договору)\s*(?:коммерческого представительства)?\s*(?:№\s*)?(?:от\s*)?(D\d{6,}(?:-\d{2})?)",
        r"(?:к|по)\s+(?:Cоглашению|Соглашению|соглашению)\s*(?:№\s*)?(?:от\s*)?(D\d{6,}(?:-\d{2})?)",
    ]
    found = []
    for pattern in patterns:
        found.extend(re.findall(pattern, header, flags=re.I))
    return list(dict.fromkeys(normalize_id(x) for x in found if normalize_id(x) != document_id))


def extract_effective_date(text: str) -> date | None:
    # For addenda, effective dates are often more informative than a missing
    # signature date. Use the first explicit "распространяет ... с DATE" clause.
    patterns = [
        r"(?:распространяет[^.]{0,120}?отношения[^.]{0,80}?с\s+)(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+(\d{4})",
        r"(?:вступает в силу|действует)[^.]{0,100}?\bс\s+(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+(\d{4})",
        r"(?:распространяет[^.]{0,120}?с\s+)(\d{2})[./](\d{2})[./](\d{4})",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.I)
        if not m:
            continue
        try:
            if len(m.groups()) == 3 and m.group(2).isdigit():
                return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            return date(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1)))
        except (ValueError, KeyError):
            continue
    return None

def _ocr_pdf(pdf: pymupdf.Document) -> str:
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("OCR dependencies are not installed") from exc

    pages = []
    for page in list(pdf)[:1]:
        pix = page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False)
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        # "Cyrillic" is available in the standard tessdata used by the
        # development environment; deployments can override this later.
        pages.append(pytesseract.image_to_string(image, lang="Cyrillic", timeout=20))
    return "\\n".join(pages)


def extract_title_date(text: str, document_id: str) -> date | None:
    header = text[:5000]
    pos = header.lower().find(document_id.lower())
    if pos < 0:
        # OCR may have removed D or changed the prefix.
        numeric = document_id[1:] if document_id.upper().startswith("D") else document_id
        pos = header.find(numeric)
    if pos < 0:
        # OCR may corrupt the document number itself. Fall back to the
        # document-title region and take the last date before the parties.
        title_pos = re.search(r"дополнительное\s+соглашение|договор|соглашение", header, re.I)
        if not title_pos:
            return None
        pos = title_pos.start()

    segment = header[pos:pos + 900]
    # For an addendum the first date can be the parent contract date, so
    # prefer the last date before the parties section.
    party_pos = re.search(r"Публичное|Общество с ограниченной|Индивидуальный предприниматель", segment, re.I)
    candidate = segment[:party_pos.start()] if party_pos else segment
    dates = extract_dates(candidate)
    if dates:
        return dates[-1]
    return None


def parse_pdf(path: Path) -> Document:
    warnings: list[str] = []

    with pymupdf.open(path) as pdf:
        pages = [page.get_text("text") for page in pdf]
        text = "\\n".join(pages)

        if len(text.strip()) < 100:
            warnings.append("PDF contains little/no extractable text; OCR fallback was used.")
            try:
                text = _ocr_pdf(pdf)
            except Exception as exc:
                warnings.append(f"OCR failed: {exc}")

        ids = extract_ids(text)
        dates = extract_dates(text)

        doc_id = extract_document_id(text, path)
        document_type = infer_type(text, path.name)

        # Last-resort metadata fallback for image-only PDFs whose OCR cannot
        # recognize the contract number reliably.
        if not extract_ids(path.stem) and doc_id == path.stem:
            for parent in path.parents:
                folder_ids = extract_ids(parent.name)
                if folder_ids:
                    doc_id = folder_ids[0]
                    warnings.append(
                        "Document ID was recovered from the source folder because OCR "
                        "could not reliably recognize the title."
                    )
                    break

        # The earliest date is often the original contract date, while the
        # latest can be an amendment date or a date inside the body.
        # For now, select the first date occurring in the first 2500 chars.
        document_date = extract_title_date(text, doc_id)
        if document_date is None:
            header_dates = extract_dates(text[:2500])
            document_date = header_dates[0] if header_dates else (dates[0] if dates else None)

        referenced = [x for x in ids if x != doc_id]
        parent_ids = extract_parent_contract_ids(text, doc_id)
        if not parent_ids and document_type == DocumentType.ADDENDUM:
            # Source folder is only a fallback for OCR failures. The main
            # relationship algorithm never depends on folder names.
            folder_candidates = []
            for parent in path.parents:
                folder_candidates.extend(extract_ids(parent.name))
            folder_candidates = [x for x in folder_candidates if x != doc_id]
            if folder_candidates:
                parent_ids = [folder_candidates[0]]
                warnings.append(
                    "Parent contract ID was recovered from the source folder because "
                    "the scanned title was not parsed reliably."
                )
            else:
                fallback_parents = [x for x in ids if x != doc_id]
                if fallback_parents:
                    parent_ids = [fallback_parents[0]]
                    warnings.append(
                        "Parent contract ID was inferred from the first non-self document ID; "
                        "explicit parent relation was not parsed."
                    )
        effective_date = extract_effective_date(text)

        return Document(
            document_id=doc_id,
            path=path,
            text=text,
            page_count=len(pdf),
            document_type=document_type,
            document_date=document_date,
            referenced_contract_ids=referenced,
            parent_contract_ids=parent_ids,
            effective_date=effective_date,
            parties=extract_parties(text),
            extraction_warnings=warnings,
        )
