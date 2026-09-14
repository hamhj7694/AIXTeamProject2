"""Bounded AI contract for extracting reviewable Case Context facts from one message."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


SemanticKey = Literal[
    "transfer.actual.status",
    "transfer.requested.amount",
    "transfer.actual.amount",
    "exposure.personal_information",
    "exposure.account_information",
    "exposure.authentication_information",
    "exposure.identity_or_card",
    "exposure.occurred_at",
    "device.remote_control_app",
    "offender.claimed_organization",
    "offender.claimed_person_or_role",
    "offender.requested_account",
    "offender.contact",
    "offender.incident_claim",
    "circumstance.demand",
    "circumstance.tactic",
]


class ContextFactExtractionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ContextFactExtractionMessage(ContextFactExtractionModel):
    message_id: str = Field(min_length=1, max_length=64)
    case_id: str = Field(min_length=1, max_length=64)
    actor_type: Literal["CUSTOMER", "BANK_STAFF"]
    content: str = Field(min_length=1, max_length=10_000)
    created_at: str | None = None


class ExistingContextFact(ContextFactExtractionModel):
    fact_id: str
    semantic_key: SemanticKey
    value: dict[str, Any]
    status: Literal["PROPOSED", "CONFIRMED", "REJECTED", "SUPERSEDED"]


class ContextFactExtractionInput(ContextFactExtractionModel):
    schema_version: Literal["context-fact-extraction.v1"] = "context-fact-extraction.v1"
    message: ContextFactExtractionMessage
    existing_facts: list[ExistingContextFact] = Field(default_factory=list, max_length=200)


class ContextFactProposal(ContextFactExtractionModel):
    semantic_key: SemanticKey
    display_label: str = Field(min_length=1, max_length=255)
    value: dict[str, Any]
    display_value: str = Field(min_length=1, max_length=3000)
    confidence: float = Field(ge=0, le=1)
    evidence_message_id: str = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def validate_typed_value(self):
        value = self.value
        if self.semantic_key in {"transfer.requested.amount", "transfer.actual.amount"}:
            amount = value.get("amount_krw")
            if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0 or value.get("currency") != "KRW":
                raise ValueError("금액 사실은 0 이상의 정수 amount_krw와 currency=KRW가 필요합니다.")
        elif self.semantic_key == "transfer.actual.status":
            if value.get("status") not in {"TRANSFERRED", "NOT_TRANSFERRED", "UNKNOWN"}:
                raise ValueError("실제 이체 상태 값이 유효하지 않습니다.")
        elif self.semantic_key == "exposure.occurred_at":
            if not any(isinstance(value.get(key), str) and value[key].strip() for key in ("occurred_at", "from", "to")):
                raise ValueError("발생 시점에는 occurred_at 또는 기간 값이 필요합니다.")
        elif self.semantic_key.startswith("exposure.") or self.semantic_key == "device.remote_control_app":
            if not isinstance(value.get("status"), str) or not value["status"].strip():
                raise ValueError("노출·기기 사실은 status가 필요합니다.")
            if "types" in value and (not isinstance(value["types"], list) or not all(isinstance(item, str) for item in value["types"])):
                raise ValueError("노출 types는 문자열 배열이어야 합니다.")
        elif self.semantic_key == "offender.claimed_organization":
            if not isinstance(value.get("name"), str) or not value["name"].strip():
                raise ValueError("사칭 기관에는 name이 필요합니다.")
        elif self.semantic_key == "offender.claimed_person_or_role":
            if not any(isinstance(value.get(key), str) and value[key].strip() for key in ("role", "role_or_title")):
                raise ValueError("사칭 인물·역할에는 role_or_title이 필요합니다.")
        elif self.semantic_key in {"offender.incident_claim", "circumstance.demand", "circumstance.tactic", "offender.requested_account", "offender.contact"}:
            if not any(isinstance(value.get(key), str) and value[key].strip() for key in ("text", "account_ref", "value")):
                raise ValueError("서술 사실에는 text 또는 해당 식별 문자열이 필요합니다.")
        return self


class ContextFactExtractionOutput(ContextFactExtractionModel):
    schema_version: Literal["context-fact-proposals.v1"] = "context-fact-proposals.v1"
    proposals: list[ContextFactProposal] = Field(default_factory=list, max_length=24)
    model_version: str = Field(default="deterministic-v1", max_length=100)
    prompt_version: str = Field(default="context-fact-v1", max_length=100)

    @model_validator(mode="after")
    def proposals_reference_the_input_message(self):
        return self
