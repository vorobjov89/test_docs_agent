from enum import Enum

from pydantic import BaseModel


class DocumentType(str, Enum):
    CONTRACT = "contract"
    ADDENDUM = "addendum"
    TERMINATION = "termination"
    OTHER = "other"


class Document(BaseModel):
    document_id: str
    filename: str

    document_type: DocumentType

    document_date: str | None = None

    contract_id: str | None = None
    referenced_contract_id: str | None = None

    text: str

    pages: int