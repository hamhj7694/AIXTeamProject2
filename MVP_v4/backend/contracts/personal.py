"""Actor-private workspace data; never included in a Shared Case projection."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field
from backend.contracts.case import StrictCaseModel, Version


class CreatePersonalNote(StrictCaseModel):
    client_request_id: UUID
    content: str = Field(min_length=1, max_length=4000)


class SetPersonalBookmark(StrictCaseModel):
    client_request_id: UUID
    target_entity_type: Literal["EVENT"] = "EVENT"
    target_entity_id: UUID
    expected_version: int = Field(ge=0)
    active: bool


class PersonalNote(StrictCaseModel):
    id: UUID
    content: str
    version: Version
    created_at: datetime


class PersonalBookmark(StrictCaseModel):
    id: UUID
    target_entity_type: Literal["EVENT"]
    target_entity_id: UUID
    version: Version
    active: bool
    available: bool


class PersonalWorkspace(StrictCaseModel):
    actor_id: str
    notes: list[PersonalNote]
    bookmarks: list[PersonalBookmark]
