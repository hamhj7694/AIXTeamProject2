"""Public Case workflow resources owned by the General API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class PublicWorkflowModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PublicCreateVerificationRequest(PublicWorkflowModel):
    claim: str = Field(min_length=1, max_length=10_000)
    target: str = Field(min_length=1, max_length=255)


class PublicUpdateVerificationRequest(PublicWorkflowModel):
    expected_version: int = Field(ge=1)
    status: Literal["PENDING", "IN_PROGRESS", "COMPLETED", "ON_HOLD", "FAILED"]


class PublicVerificationResponse(PublicWorkflowModel):
    verification_task_id: str
    case_id: str
    claim: str
    target: str
    status: str
    version: int = Field(ge=1)
    created_at: str
    updated_at: str


class PublicCreateActionRequest(PublicWorkflowModel):
    action_type: str = Field(min_length=1, max_length=64)
    actor_type: Literal["BANK_STAFF", "SYSTEM"]
    note: str = Field(min_length=1, max_length=10_000)


class PublicActionCommandRequest(PublicWorkflowModel):
    note: str = Field(min_length=1, max_length=10_000)


class PublicCreateVoiceSessionRequest(PublicWorkflowModel):
    participants: list[str] = Field(min_length=1, max_length=10)


class PublicUpdateVoiceSessionRequest(PublicWorkflowModel):
    status: Literal["ACTIVE", "ENDED", "FAILED"]


class PublicVoiceSessionResponse(PublicWorkflowModel):
    session_id: str
    case_id: str
    status: Literal["REQUESTED", "ACTIVE", "ENDED", "FAILED"]
    participants: list[str]
    started_at: str | None
    ended_at: str | None
    created_at: str


class PublicCreateTranscriptRequest(PublicWorkflowModel):
    speaker: str = Field(min_length=1, max_length=32)
    content: str = Field(min_length=1, max_length=10_000)
    started_at: str | None = None


class PublicTranscriptResponse(PublicWorkflowModel):
    segment_id: str
    session_id: str
    case_id: str
    speaker: str
    content: str
    started_at: str | None
    created_at: str


class PublicFinalizeReportRequest(PublicWorkflowModel):
    expected_version: int = Field(ge=1)
    note: str = Field(default="", max_length=10_000)


class PublicReportResponse(PublicWorkflowModel):
    report_id: str
    case_id: str
    report_version: int
    status: Literal["LIVE", "FINAL"]
    sections: list[dict[str, Any]]
    created_at: str


class PublicActionResponse(PublicWorkflowModel):
    action_id: str
    case_id: str
    action_type: str
    status: str
    actor_type: str
    note: str
    created_at: str


class PublicCaseBundleResponse(PublicWorkflowModel):
    case: dict[str, Any]
    live_report: dict[str, Any] | None
    questions: list[dict[str, Any]]
    progress_items: list[dict[str, Any]]
    verification_tasks: list[PublicVerificationResponse]
    recent_messages: list[dict[str, Any]]
    recent_actions: list[PublicActionResponse]
    recent_events: list[dict[str, Any]]
    voice_session: PublicVoiceSessionResponse | None
    cursor: str | None


def to_public_verification(record: dict[str, Any]) -> PublicVerificationResponse:
    return PublicVerificationResponse.model_validate(record)


def to_public_action(record: dict[str, Any]) -> PublicActionResponse:
    return PublicActionResponse.model_validate(record)
