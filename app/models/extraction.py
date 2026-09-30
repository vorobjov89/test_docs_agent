from pydantic import BaseModel, Field

from app.models.contract import ContractChange


class ExtractedDocument(BaseModel):
    document_type: str

    document_id: str | None = None

    contract_id: str | None = None

    referenced_contract_id: str | None = None

    contract_number: str | None = None

    document_date: str | None = None

    effective_date: str | None = None

    contract_type: str | None = None

    subject: str | None = None

    parties: list[str] = Field(
        default_factory=list
    )

    changes: list[ContractChange] = Field(
        default_factory=list
    )


class ExtractedChunk(BaseModel):
    changes: list[ContractChange] = Field(
        default_factory=list
    )
