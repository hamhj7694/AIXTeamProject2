"""Shared Case boundary types. Persistence and API behavior are added in P1-002."""
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Visibility(StrEnum):
    CUSTOMER = "CUSTOMER"
    BANK_INTERNAL = "BANK_INTERNAL"
    AI_PRIVATE = "AI_PRIVATE"


class CaseMode(StrEnum):
    PREVENT = "PREVENT"
    RECOVERY = "RECOVERY"


class CaseStatus(StrEnum):
    TRIAGE = "TRIAGE"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class LossStatus(StrEnum):
    UNKNOWN = "UNKNOWN"
    NO_LOSS = "NO_LOSS"
    LOSS_CONFIRMED = "LOSS_CONFIRMED"


class ParticipantRole(StrEnum):
    CUSTOMER = "CUSTOMER"
    BANK_STAFF = "BANK_STAFF"


class ActorRole(StrEnum):
    CUSTOMER = "CUSTOMER"
    BANK_STAFF = "BANK_STAFF"
    SYSTEM = "SYSTEM"
    AI = "AI"


class EventType(StrEnum):
    CASE_CREATED = "CASE_CREATED"
    CASE_UPDATED = "CASE_UPDATED"
    ENTITY_CREATED = "ENTITY_CREATED"
    ENTITY_UPDATED = "ENTITY_UPDATED"
    ENTITY_DELETED = "ENTITY_DELETED"


class EntityType(StrEnum):
    CASE = "CASE"
    PARTICIPANT = "PARTICIPANT"
    CONTEXT_FEATURE = "CONTEXT_FEATURE"
    CONTEXT_ITEM = "CONTEXT_ITEM"
    MESSAGE = "MESSAGE"
    QUESTION = "QUESTION"
    ANSWER = "ANSWER"
    FACT = "FACT"
    VERIFICATION = "VERIFICATION"
    TASK = "TASK"
    CUSTOMER_PROGRESS = "CUSTOMER_PROGRESS"
    AI_SUGGESTION = "AI_SUGGESTION"
    CASE_BRIEF = "CASE_BRIEF"
    REPORT = "REPORT"
    NOTE = "NOTE"
    BOOKMARK = "BOOKMARK"
    ATTACHMENT = "ATTACHMENT"


Version = Annotated[int, Field(ge=1)]
Revision = Annotated[int, Field(ge=1)]
Fingerprint = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class StrictCaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class WritePrecondition(StrictCaseModel):
    client_request_id: UUID
    expected_version: Version | None = None


class SharedCase(StrictCaseModel):
    id: UUID
    status: CaseStatus
    mode: CaseMode
    loss_status: LossStatus
    primary_assignee_id: str | None = Field(default=None, max_length=128)
    revision: Revision
    fingerprint: Fingerprint
    version: Version
    created_at: datetime
    updated_at: datetime


class CaseParticipant(StrictCaseModel):
    id: UUID
    case_id: UUID
    participant_id: str = Field(min_length=1, max_length=128)
    role: ParticipantRole
    version: Version


class CaseEvent(StrictCaseModel):
    id: UUID
    case_id: UUID
    event_type: EventType
    entity_type: EntityType
    entity_id: UUID | None = None
    actor_role: ActorRole
    actor_id: str | None = Field(default=None, max_length=128)
    visibility: Visibility
    case_revision: Revision
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ActorContext(StrictCaseModel):
    """Identity supplied by trusted server authentication middleware, never by request bodies or query values."""
    actor_id: str = Field(min_length=1, max_length=128)
    role: ActorRole


class CreateCaseRequest(StrictCaseModel):
    client_request_id: UUID
    mode: CaseMode = CaseMode.PREVENT
    loss_status: LossStatus = LossStatus.UNKNOWN
    # A bank employee needs the customer identity to open a case on the customer's behalf.
    customer_participant_id: str | None = Field(default=None, min_length=1, max_length=128)


class CreateEventRequest(WritePrecondition):
    event_type: EventType
    entity_type: EntityType
    entity_id: UUID | None = None
    visibility: Visibility = Visibility.BANK_INTERNAL
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("payload")
    @classmethod
    def forbid_source_text(cls, value: dict[str, Any]) -> dict[str, Any]:
        StructuredFeaturePayload(schema_version="event", values=value)
        return value


class CaseProjection(StrictCaseModel):
    case: SharedCase
    participants: list[CaseParticipant]
    events: list[CaseEvent]


class CaseEntityUpsert(StrictCaseModel):
    entity_type: EntityType
    entity_id: UUID
    version: Version
    data: dict[str, Any]


class CaseDelta(StrictCaseModel):
    case_id: UUID
    revision: Revision
    fingerprint: Fingerprint
    unchanged: bool
    upserts: list[CaseEntityUpsert] = Field(default_factory=list)
    deleted_entity_ids: list[UUID] = Field(default_factory=list)


class CreateMlIntakeRequest(WritePrecondition):
    source_event_id: str = Field(min_length=1, max_length=128)
    features: dict[str, float]

    @field_validator("features")
    @classmethod
    def require_finite_features(cls, value: dict[str, float]) -> dict[str, float]:
        import math
        if not value or any(isinstance(item, bool) or not math.isfinite(item) for item in value.values()):
            raise ValueError("features must be finite numbers")
        return value


class CreateTestTextIntakeRequest(WritePrecondition):
    source_event_id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=2000)


class StructuredFeaturePayload(StrictCaseModel):
    """Text source/transcript cannot cross this contract boundary."""
    schema_version: str = Field(min_length=1, max_length=40)
    values: dict[str, Any] = Field(default_factory=dict)

    @field_validator("values")
    @classmethod
    def forbid_reconstructable_source_text(cls, value: dict[str, Any]) -> dict[str, Any]:
        blocked = {"text", "raw_text", "transcript", "utterance", "call_audio", "source_text"}

        def visit(item: Any) -> None:
            if isinstance(item, dict):
                for key, child in item.items():
                    if str(key).lower() in blocked:
                        raise ValueError("Structured features cannot contain source text")
                    visit(child)
            elif isinstance(item, list):
                for child in item:
                    visit(child)

        visit(value)
        return value
