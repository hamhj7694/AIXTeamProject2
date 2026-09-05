"""AI-side proposal contract for Case Context v2.

The response deliberately contains proposals only. It has no fields capable of
confirming facts, completing bank tasks, publishing customer data, or writing a
staff decision record.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from contracts.diagnosis import StrictModel


class AiEvidenceReferenceV2(StrictModel):
    type: Literal[
        "MESSAGE", "QUESTION_ANSWER", "BANK_TRANSACTION", "VERIFICATION_RESULT",
        "ATTACHMENT", "STRUCTURED_SIGNAL", "STAFF_RECORD",
    ]
    id: str = Field(min_length=1, max_length=100)
    revision: int | None = Field(default=None, ge=1)


class AiKnownFactV2(StrictModel):
    fact_id: str
    semantic_key: str
    display_label: str
    display_value: str
    status: Literal["PROPOSED", "CONFIRMED", "REJECTED", "SUPERSEDED"]
    source_kind: str
    evidence_refs: list[AiEvidenceReferenceV2] = Field(default_factory=list)


class AiGapStateV2(StrictModel):
    gap_id: str
    semantic_key: str
    title: str
    reason: str
    status: Literal[
        "OPEN", "AWAITING_CUSTOMER", "AWAITING_INSTITUTION",
        "STAFF_REVIEW_REQUIRED", "RESOLVED", "DISMISSED",
    ]
    priority: Literal["URGENT", "HIGH", "NORMAL"]


class AiSuggestionStateV2(StrictModel):
    suggestion_id: str
    dedupe_key: str
    title: str
    status: Literal["PROPOSED", "ACCEPTED", "DISMISSED", "EXPIRED", "SUPERSEDED"]
    related_gap_ids: list[str] = Field(default_factory=list)


class AiTaskStateV2(StrictModel):
    task_id: str
    task_type: str
    title: str
    status: Literal["TODO", "IN_PROGRESS", "BLOCKED", "COMPLETED", "CANCELLED"]
    result_summary: str | None = None


class AiDecisionSummaryV2(StrictModel):
    decision_id: str
    decision_type: str
    title: str
    rationale: str


class CaseContextAiInputV2(StrictModel):
    schema_version: Literal["case-context-ai-input.v2"] = "case-context-ai-input.v2"
    case_id: str
    source_revision: int = Field(ge=1)
    privacy_safe_signals: list[dict[str, Any]] = Field(default_factory=list)
    facts: list[AiKnownFactV2] = Field(default_factory=list)
    gaps: list[AiGapStateV2] = Field(default_factory=list)
    questions: list[dict[str, Any]] = Field(default_factory=list)
    verifications: list[dict[str, Any]] = Field(default_factory=list)
    suggestions: list[AiSuggestionStateV2] = Field(default_factory=list)
    tasks: list[AiTaskStateV2] = Field(default_factory=list)
    decisions: list[AiDecisionSummaryV2] = Field(default_factory=list)


class ProposedContextBulletV2(StrictModel):
    semantic_key: str
    text: str
    evidence_refs: list[AiEvidenceReferenceV2] = Field(default_factory=list)


class ProposedGapV2(StrictModel):
    semantic_key: str
    title: str
    reason: str
    priority: Literal["URGENT", "HIGH", "NORMAL"]
    evidence_refs: list[AiEvidenceReferenceV2] = Field(default_factory=list)


class ProposedSuggestionV2(StrictModel):
    suggestion_type: Literal[
        "CUSTOMER_QUESTION", "INSTITUTION_VERIFICATION", "TRANSACTION_REVIEW",
        "PROTECTIVE_ACTION", "DOCUMENT_REQUEST", "STAFF_REVIEW",
    ]
    title: str
    rationale: str
    priority: Literal["URGENT", "HIGH", "NORMAL"]
    related_gap_keys: list[str] = Field(default_factory=list)
    evidence_refs: list[AiEvidenceReferenceV2] = Field(default_factory=list)
    dedupe_key: str
    execution_mode: Literal["HUMAN_REVIEW_REQUIRED", "AUTO_CUSTOMER_QUESTION_ALLOWED"] = "HUMAN_REVIEW_REQUIRED"


class CaseContextAiProposalV2(StrictModel):
    schema_version: Literal["case-context-ai-proposal.v2"] = "case-context-ai-proposal.v2"
    source_revision: int = Field(ge=1)
    summary_bullets: list[ProposedContextBulletV2] = Field(default_factory=list, max_length=4)
    context_items: list[ProposedContextBulletV2] = Field(default_factory=list)
    proposed_gap_upserts: list[ProposedGapV2] = Field(default_factory=list)
    proposed_suggestions: list[ProposedSuggestionV2] = Field(default_factory=list)
    obsolete_suggestion_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    model_version: str
    prompt_version: str
