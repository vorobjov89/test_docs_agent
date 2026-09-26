
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from pathlib import Path


class DocumentType(str, Enum):
    """
    Поделили все документы на четыре типа:
    - контракт
    - дополнение
    - соглашение
    - иное/неизвестно
    """
    CONTRACT = "contract"
    ADDENDUM = "addendum"
    AGREEMENT = "agreement"
    UNKNOWN = "unknown"


@dataclass
class Document:
    document_id: str
    path: Path
    text: str
    page_count: int
    document_type: DocumentType = DocumentType.UNKNOWN
    document_date: date | None = None
    referenced_contract_ids: list[str] = field(default_factory=list)
    referenced_document_ids: list[str] = field(default_factory=list)
    parent_contract_ids: list[str] = field(default_factory=list)
    effective_date: date | None = None
    parties: list[str] = field(default_factory=list)
    extraction_warnings: list[str] = field(default_factory=list)
