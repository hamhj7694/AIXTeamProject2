from datetime import datetime
from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator

TaskStatus = Literal['TODO', 'IN_PROGRESS', 'BLOCKED', 'COMPLETED', 'CANCELLED']


class StrictTaskModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class CaseTask(StrictTaskModel):
    id: UUID
    case_id: UUID
    title: str
    status: TaskStatus
    result: str | None
    cancel_reason: str | None
    version: int = Field(ge=1)
    updated_at: datetime


class TaskSuggestion(StrictTaskModel):
    id: UUID
    case_id: UUID
    proposal: dict[str, Any]
    source_revision: int = Field(ge=1)
    status: Literal['PENDING','ACCEPTED','EDITED','REJECTED','STALE']
    version: int = Field(ge=1)
    updated_at: datetime


class TaskCreate(StrictTaskModel):
    client_request_id: UUID
    expected_case_version: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=300)


class TaskUpdate(TaskCreate):
    expected_version: int = Field(ge=1)
    status: TaskStatus
    result: str | None = Field(default=None, max_length=4000)
    cancel_reason: str | None = Field(default=None, max_length=4000)

    @model_validator(mode='after')
    def require_outcome(self):
        if self.status == 'COMPLETED' and not self.result:
            raise ValueError('Task completion requires a result')
        if self.status == 'CANCELLED' and not self.cancel_reason:
            raise ValueError('Task cancellation requires a reason')
        return self


class SuggestionDecision(StrictTaskModel):
    client_request_id: UUID
    expected_case_version: int = Field(ge=1)
    expected_version: int = Field(ge=1)
    decision: Literal['ACCEPT','EDIT','REJECT']
    title: str | None = Field(default=None, min_length=1, max_length=300)

    @model_validator(mode='after')
    def edited_title(self):
        if self.decision == 'EDIT' and not self.title:
            raise ValueError('Edited adoption requires a title')
        if self.decision != 'EDIT' and self.title is not None:
            raise ValueError('Only edited adoption accepts a changed title')
        return self
