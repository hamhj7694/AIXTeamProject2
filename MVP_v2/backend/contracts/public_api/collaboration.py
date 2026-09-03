"""Public contracts for the MVP v2 Case collaboration room."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


MessageChannel = Literal["TEAM", "CUSTOMER", "AI_INTERNAL"]
MessageAudience = Literal["BANK_INTERNAL", "CUSTOMER"]
CaseMemberRole = Literal["CASE_OWNER", "CHAT_OPERATOR", "REVIEWER", "VIEWER"]
PresenceState = Literal["VIEWING", "TYPING", "AWAY", "OFFLINE"]


class PublicCollaborationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PublicCaseMemberUpsertRequest(PublicCollaborationModel):
    user_id: str = Field(min_length=1, max_length=64)
    display_name: str = Field(min_length=1, max_length=80)
    role: CaseMemberRole


class PublicPrimaryAssigneeRequest(PublicCollaborationModel):
    display_name: str | None = Field(default=None, max_length=80)


class PublicPrimaryAssigneeResponse(PublicCollaborationModel):
    case_id: str
    display_name: str | None


class PublicCaseMemberResponse(PublicCollaborationModel):
    case_id: str
    user_id: str
    display_name: str
    role: CaseMemberRole
    status: Literal["ACTIVE", "REMOVED"]
    assigned_at: str
    updated_at: str


class PublicPresenceHeartbeatRequest(PublicCollaborationModel):
    user_id: str = Field(min_length=1, max_length=64)
    display_name: str = Field(min_length=1, max_length=80)
    presence: PresenceState = "VIEWING"
    channel: MessageChannel = "TEAM"


class PublicCasePresenceResponse(PublicCollaborationModel):
    case_id: str
    user_id: str
    display_name: str
    presence: PresenceState
    channel: MessageChannel
    last_seen_at: str
    expires_at: str


class PublicAiInvocationRequest(PublicCollaborationModel):
    prompt: str = Field(min_length=1, max_length=10_000)
    channel: Literal["TEAM", "AI_INTERNAL"] = "TEAM"
    requester_user_id: str = Field(min_length=1, max_length=64)
    requester_display_name: str = Field(min_length=1, max_length=80)
    client_request_id: str | None = Field(default=None, max_length=100)


class PublicAiInvocationResponse(PublicCollaborationModel):
    invocation_id: str
    message_id: str
    case_id: str
    channel: Literal["TEAM", "AI_INTERNAL"]
    content: str
    model_mode: Literal["MVP_DETERMINISTIC"]
    created_at: str


class PublicAiShareRequest(PublicCollaborationModel):
    shared_by_user_id: str = Field(min_length=1, max_length=64)
    shared_by_display_name: str = Field(min_length=1, max_length=80)
