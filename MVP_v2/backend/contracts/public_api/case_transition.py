"""Public Case lifecycle patch contract."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from .case_enums import CaseMode, CaseStatus


class PublicCasePatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    status: CaseStatus | None = None
    mode: CaseMode | None = None


class PublicCaseTransitionError(BaseModel):
    code: Literal["CASE_NOT_FOUND", "VERSION_CONFLICT", "INVALID_STATE_TRANSITION"]
    message: str
    current_version: int | None = None
