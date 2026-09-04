"""Structured AI proposal used to render one bank work card."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from contracts.diagnosis import StrictModel


WorkCardType = Literal["FACT_REVIEW", "QUESTION_PLAN", "VERIFICATION_REQUEST", "BANK_ACTION", "CUSTOMER_NOTICE", "CASE_TRANSITION"]


class WorkCardQuestion(StrictModel):
    question_id: str
    target_field: str
    question_text: str
    reason: str
    priority: Literal["P0", "P1", "P2"]
    options: list[str] = Field(default_factory=list, max_length=8)
    customer_explanation: str | None = None
    answer_mode: Literal["SINGLE_CHOICE", "TEXT", "CHOICE_OR_TEXT"] = "CHOICE_OR_TEXT"
    allow_free_text: bool = True


class CaseWorkCardInput(StrictModel):
    case_id: str
    card_type: WorkCardType
    case_summary: str = Field(default="", max_length=4_000)
    workflow_status: str = "TRIAGE"
    case_mode: str = "PREVENT"
    fraud_type: str | None = None
    known_facts: list[str] = Field(default_factory=list, max_length=30)
    recent_conversation: list[str] = Field(default_factory=list, max_length=20)
    pending_actions: list[str] = Field(default_factory=list, max_length=20)
    attachment_summaries: list[str] = Field(default_factory=list, max_length=10)
    unresolved_items: list[str] = Field(default_factory=list, max_length=20)
    pending_verifications: list[str] = Field(default_factory=list, max_length=20)
    question_candidates: list[WorkCardQuestion] = Field(default_factory=list, max_length=10)


class CaseWorkCardOutput(StrictModel):
    card_type: WorkCardType
    title: str
    summary: str
    context_sources: list[str] = Field(default_factory=list, max_length=6)
    rationale: list[str] = Field(default_factory=list, max_length=8)
    next_action: str
    questions: list[WorkCardQuestion] = Field(default_factory=list, max_length=10)
    suggested_claim: str | None = None
    suggested_target: str | None = None
    suggested_action_type: str | None = None
    suggested_action_note: str | None = None
    suggested_notice: str | None = None
    suggested_transition: str | None = None
    warnings: list[str] = Field(default_factory=list, max_length=8)
    model_mode: str
