"""Public append-only Message and Timeline Event contracts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


MessageActor = Literal["CUSTOMER", "BANK_STAFF", "CUSTOMER_AGENT", "BANK_AGENT", "VERIFICATION", "SYSTEM"]


class PublicActivityModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PublicCreateMessageRequest(PublicActivityModel):
    actor_type: MessageActor
    content: str = Field(min_length=1, max_length=10_000)
    client_request_id: str | None = Field(default=None, max_length=100)


class PublicMessageResponse(PublicActivityModel):
    message_id: str
    case_id: str
    actor_type: MessageActor
    content: str
    created_at: str


class PublicCaseEventResponse(PublicActivityModel):
    event_id: int
    case_id: str
    event_type: str
    actor_type: str
    payload: dict[str, Any]
    occurred_at: str


def to_public_message(record: dict[str, Any]) -> PublicMessageResponse:
    return PublicMessageResponse.model_validate({
        "message_id": record["message_id"], "case_id": record["case_id"],
        "actor_type": record["actor_type"], "content": record["content"], "created_at": record["created_at"],
    })


def to_public_event(record: dict[str, Any]) -> PublicCaseEventResponse:
    return PublicCaseEventResponse.model_validate(record)
