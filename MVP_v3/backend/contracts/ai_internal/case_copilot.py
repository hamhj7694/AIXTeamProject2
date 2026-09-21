"""Minimal, bounded contract for a CaseCopilot reply."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from contracts.diagnosis import StrictModel
from contracts.public_api.case_context_v2 import PublicCaseFactV2


class CopilotLegacyFact(StrictModel):
    fact_id: str
    case_id: str
    field: str
    value: str
    source: str
    status: str
    evidence_message_id: str | None = None
    source_question_id: str | None = None
    confirmed_by: str | None = None
    confirmed_at: datetime | None = None
    created_at: datetime | None = None


class CopilotQuestionAnswer(StrictModel):
    question_id: str
    case_id: str
    canonical_scope: str
    parent_question_id: str | None = None
    question_text: str
    answer_text: str | None = None
    status: Literal["PENDING", "ASKED", "ANSWERED", "SKIPPED"]
    answer_message_id: str | None = None
    created_at: datetime | None = None
    asked_at: datetime | None = None
    answered_at: datetime | None = None


class CopilotVerification(StrictModel):
    verification_task_id: str
    case_id: str
    target: str
    claim: str
    status: str
    result_summary: str | None = None
    version: int | None = None
    evidence_url: str | None = None
    verified_by: str | None = None
    rag_source: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CopilotMessage(StrictModel):
    message_id: str
    case_id: str
    actor_type: str
    actor_user_id: str | None = Field(default=None, max_length=64)
    actor_display_name: str | None = Field(default=None, max_length=80)
    actor_role: str | None = Field(default=None, max_length=64)
    channel: str | None = Field(default=None, max_length=40)
    audience: str | None = Field(default=None, max_length=40)
    content: str
    created_at: datetime | None = None


class BankCopilotSourceContext(StrictModel):
    """Bounded original records, not inferred current/correction relationships."""
    facts: list[PublicCaseFactV2] = Field(default_factory=list, max_length=100)
    legacy_facts: list[CopilotLegacyFact] = Field(default_factory=list, max_length=100)
    questions: list[CopilotQuestionAnswer] = Field(default_factory=list, max_length=50)
    verifications: list[CopilotVerification] = Field(default_factory=list, max_length=20)
    messages: list[CopilotMessage] = Field(default_factory=list, max_length=20)
    truncated: bool = False


class CustomerServiceQuestion(StrictModel):
    """Server-selected question cards currently exposed to this Case's customer."""

    source: Literal['CSR_QUESTION_CARD'] = 'CSR_QUESTION_CARD'
    status: Literal['ASKED'] = 'ASKED'
    question_text: str = Field(min_length=1, max_length=1_000)
    customer_explanation: str = Field(default='', max_length=1_000)
    options: list[str] = Field(default_factory=list, max_length=10)


class CaseCopilotInput(StrictModel):
    case_id: str = Field(min_length=1, max_length=80)
    prompt: str = Field(min_length=1, max_length=6_000)
    requester_user_id: str | None = Field(default=None, max_length=64)
    requester_display_name: str | None = Field(default=None, max_length=80)
    requester_role: str | None = Field(default=None, max_length=64)
    case_summary: str = Field(default="", max_length=4_000)
    workflow_status: str = Field(default="TRIAGE", max_length=80)
    fraud_type: str | None = Field(default=None, max_length=160)
    transfer_status: str | None = Field(default=None, max_length=80)
    primary_assignee: str | None = Field(default=None, max_length=160)
    participants: list[str] = Field(default_factory=list, max_length=30)
    known_facts: list[str] = Field(default_factory=list, max_length=30)
    staff_context: list[str] = Field(default_factory=list, max_length=30)
    retrieved_context: list[str] = Field(default_factory=list, max_length=6)
    recent_conversation: list[str] = Field(default_factory=list, max_length=20)
    pending_actions: list[str] = Field(default_factory=list, max_length=20)
    customer_progress: list[str] = Field(default_factory=list, max_length=10)
    customer_service_questions: list[CustomerServiceQuestion] = Field(default_factory=list, max_length=5)
    published_verification_results: list[str] = Field(default_factory=list, max_length=10)
    attachment_summaries: list[str] = Field(default_factory=list, max_length=10)
    unresolved_verifications: list[str] = Field(default_factory=list, max_length=10)
    assistant_mode: Literal["BANK_INTERNAL", "CUSTOMER_SUPPORT"] = "BANK_INTERNAL"
    response_style: Literal["CONVERSATIONAL", "BRIEF"] = "CONVERSATIONAL"
    source_context: BankCopilotSourceContext | None = None

    @model_validator(mode="after")
    def validate_source_context(self):
        if self.source_context is not None:
            if self.assistant_mode != "BANK_INTERNAL":
                raise ValueError("source_context is bank-only")
            for collection in (self.source_context.facts, self.source_context.legacy_facts,
                               self.source_context.questions, self.source_context.verifications,
                               self.source_context.messages):
                if any(item.case_id != self.case_id for item in collection):
                    raise ValueError("source_context Case mismatch")
        return self


class CaseCopilotOutput(StrictModel):
    content: str = Field(min_length=1, max_length=5_000)
    model_mode: str = Field(min_length=1, max_length=100)
