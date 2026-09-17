"""Public Case lifecycle patch contract."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .case_enums import CaseMode, CaseStatus


class PublicCasePatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    case_name: str | None = Field(default=None, max_length=200)
    status: CaseStatus | None = None
    mode: CaseMode | None = None

    @field_validator("case_name")
    @classmethod
    def normalize_case_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("사건 이름을 입력해 주세요.")
        return normalized


class PublicCaseTransitionError(BaseModel):
    code: Literal["CASE_NOT_FOUND", "VERSION_CONFLICT", "INVALID_STATE_TRANSITION"]
    message: str
    current_version: int | None = None
