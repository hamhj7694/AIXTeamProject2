"""Minimal, bounded contract for a CaseCopilot reply."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from contracts.diagnosis import StrictModel


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


class CaseCopilotOutput(StrictModel):
    content: str = Field(min_length=1, max_length=5_000)
    model_mode: str = Field(min_length=1, max_length=100)
