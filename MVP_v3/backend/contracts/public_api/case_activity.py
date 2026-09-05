"""Public append-only Message and Timeline Event contracts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .collaboration import MessageAudience, MessageChannel


MessageActor = Literal["CUSTOMER", "BANK_STAFF", "CUSTOMER_AGENT", "BANK_AGENT", "VERIFICATION", "SYSTEM"]
MessageKind = Literal["CHAT", "AI_REQUEST", "AI_RESPONSE", "SYSTEM_EVENT", "REPORT_CARD"]
MessageVisibility = Literal["BANK_INTERNAL", "CUSTOMER", "AI_PRIVATE"]


class PublicActivityModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PublicAttachmentResponse(PublicActivityModel):
    attachment_id: str
    case_id: str
    original_name: str
    mime_type: str
    size_bytes: int = Field(ge=1)
    sha256: str
    uploaded_by: str
    status: Literal["UPLOADED", "LINKED"]
    visibility: MessageVisibility
    ai_readable: bool = True
    download_url: str
    created_at: str


class PublicCreateMessageRequest(PublicActivityModel):
    actor_type: MessageActor
    actor_user_id: str = Field(min_length=1, max_length=64)
    actor_display_name: str = Field(min_length=1, max_length=80)
    actor_role: str | None = Field(default=None, max_length=64)
    content: str = Field(default="", max_length=10_000)
    channel: MessageChannel = "CUSTOMER"
    audience: MessageAudience = "CUSTOMER"
    visibility: MessageVisibility = "CUSTOMER"
    message_kind: MessageKind = "CHAT"
    mentions: list[str] = Field(default_factory=list, max_length=10)
    reply_to_message_id: str | None = Field(default=None, max_length=64)
    client_request_id: str | None = Field(default=None, max_length=100)
    attachment_ids: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def require_content_or_attachment(self) -> "PublicCreateMessageRequest":
        if not self.content.strip() and not self.attachment_ids:
            raise ValueError("메시지 내용 또는 첨부 파일이 필요합니다.")
        return self


class PublicCustomerEmergencyRequest(PublicActivityModel):
    actor_user_id: str = Field(min_length=1, max_length=64)
    actor_display_name: str = Field(min_length=1, max_length=80)


class PublicMessageResponse(PublicActivityModel):
    message_id: str
    case_id: str
    actor_type: MessageActor
    actor_user_id: str
    actor_display_name: str
    actor_role: str | None = None
    content: str
    channel: MessageChannel
    audience: MessageAudience
    visibility: MessageVisibility
    message_kind: MessageKind
    private_owner_user_id: str | None = None
    mentions: list[str]
    reply_to_message_id: str | None = None
    client_request_id: str | None = None
    attachments: list[PublicAttachmentResponse] = Field(default_factory=list)
    created_at: str


def to_public_attachment(record: dict[str, Any], *, download_view: Literal["bank", "customer"] = "customer") -> PublicAttachmentResponse:
    case_id = record["case_id"]
    attachment_id = record["attachment_id"]
    return PublicAttachmentResponse.model_validate({
        "attachment_id": attachment_id,
        "case_id": case_id,
        "original_name": record["original_name"],
        "mime_type": record["mime_type"],
        "size_bytes": record["size_bytes"],
        "sha256": record["sha256"],
        "uploaded_by": record["uploaded_by"],
        "status": record.get("status", "UPLOADED"),
        "visibility": record.get("visibility", "CUSTOMER"),
        "ai_readable": record.get("ai_readable", True),
        "download_url": f"/api/cases/{case_id}/attachments/{attachment_id}/content?view={download_view}",
        "created_at": record["created_at"],
    })


class PublicCaseEventResponse(PublicActivityModel):
    event_id: int
    case_id: str
    event_type: str
    actor_type: str
    payload: dict[str, Any]
    occurred_at: str


def to_public_message(record: dict[str, Any]) -> PublicMessageResponse:
    actor_type = record["actor_type"]
    display_name = {
        "CUSTOMER": "고객", "BANK_STAFF": "은행 담당자", "CUSTOMER_AGENT": "Customer Agent",
        "BANK_AGENT": "CaseCopilot", "VERIFICATION": "기관 검증 담당자", "SYSTEM": "시스템",
    }.get(actor_type, actor_type)
    return PublicMessageResponse.model_validate({
        "message_id": record["message_id"], "case_id": record["case_id"],
        "actor_type": actor_type,
        "actor_user_id": record.get("actor_user_id", actor_type.lower()),
        "actor_display_name": record.get("actor_display_name", display_name),
        "actor_role": record.get("actor_role"),
        "content": record["content"],
        "channel": record.get("channel", "CUSTOMER"),
        "audience": record.get("audience", "CUSTOMER"),
        "visibility": record.get("visibility", record.get("audience", "CUSTOMER")),
        "message_kind": record.get("message_kind", "CHAT"),
        "private_owner_user_id": record.get("private_owner_user_id"),
        "mentions": record.get("mentions", []),
        "reply_to_message_id": record.get("reply_to_message_id"),
        "client_request_id": record.get("client_request_id"),
        "attachments": [to_public_attachment(item).model_dump(mode="json") for item in record.get("attachments", [])],
        "created_at": record["created_at"],
    })


def to_public_event(record: dict[str, Any]) -> PublicCaseEventResponse:
    return PublicCaseEventResponse.model_validate(record)
