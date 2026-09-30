from enum import Enum

from pydantic import BaseModel, Field


class ChangeType(str, Enum):
    ADD = "add"
    MODIFY = "modify"
    DELETE = "delete"
    REPLACE_SECTION = "replace_section"


class ContractParty(BaseModel):
    name: str


class ContractCondition(BaseModel):
    name: str
    value: str
    source_page: int | None = None
    section_context: str | None = None


class ContractChange(BaseModel):
    section: str | None = None
    section_context: str | None = None
    change_type: ChangeType
    description: str
    old_value: str | None = None
    new_value: str | None = None
    old_text: str | None = None
    new_text: str | None = None
    source_page: int | None = None


class Contract(BaseModel):
    contract_id: str

    contract_number: str | None = None
    contract_date: str | None = None

    contract_type: str | None = None
    subject: str | None = None

    parties: list[ContractParty] = Field(
        default_factory=list
    )

    conditions: list[ContractCondition] = Field(
        default_factory=list
    )


class Addendum(BaseModel):
    addendum_id: str

    contract_id: str

    addendum_number: str | None = None
    addendum_date: str | None = None
    effective_date: str | None = None

    changes: list[ContractChange] = Field(
        default_factory=list
    )


class ContractHistory(BaseModel):
    contract_id: str

    base_contract: dict | None = None

    addenda: list[dict] = Field(
        default_factory=list
    )

    current_conditions: dict[str, str] = Field(
        default_factory=dict
    )

    history: list[dict] = Field(
        default_factory=list
    )

    warnings: list[str] = Field(
        default_factory=list
    )

    replacements: list[dict] = Field(default_factory=list)


class ContractChain(BaseModel):
    contract_id: str

    base_contract: dict | None = None

    addenda: list[dict] = Field(
        default_factory=list
    )

    status: str = "complete"

    warnings: list[str] = Field(
        default_factory=list
    )


class ContractCluster(BaseModel):
    cluster_id: str

    contract_ids: list[str] = Field(
        default_factory=list
    )

    label: str

    description: str | None = None
