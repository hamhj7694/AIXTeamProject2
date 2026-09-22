"""Target public contract for the separated Case Context v2 resources.

The General API owns these resources. AI may propose gaps and suggestions, but it
cannot confirm facts, complete staff tasks, write staff decisions, or approve
customer disclosure.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


FactSource = Literal[
    "AI_EXTRACTION", "CUSTOMER_STATEMENT", "STAFF_OBSERVATION",
    "BANK_RECORD", "OFFICIAL_VERIFICATION",
]
FactStatus = Literal["PROPOSED", "CONFIRMED", "REJECTED", "SUPERSEDED"]
GapStatus = Literal[
    "OPEN", "AWAITING_CUSTOMER", "AWAITING_INSTITUTION",
    "STAFF_REVIEW_REQUIRED", "RESOLVED", "DISMISSED",
]
SuggestionStatus = Literal["PROPOSED", "ACCEPTED", "DISMISSED", "EXPIRED", "SUPERSEDED"]
TaskStatus = Literal["TODO", "IN_PROGRESS", "BLOCKED", "COMPLETED", "CANCELLED"]
Priority = Literal["URGENT", "HIGH", "NORMAL"]
InternalVisibility = Literal["BANK_INTERNAL", "CUSTOMER_SHARED"]


class CaseContextV2Model(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PublicEvidenceRef(CaseContextV2Model):
    type: Literal[
        "MESSAGE", "QUESTION_ANSWER", "BANK_TRANSACTION", "VERIFICATION_RESULT",
        "ATTACHMENT", "STRUCTURED_SIGNAL", "STRUCTURED_ATOM", "STAFF_RECORD",
    ]
    id: str = Field(min_length=1, max_length=100)
    revision: int | None = Field(default=None, ge=1)
    summary: str | None = Field(default=None, max_length=300)


class PublicCaseFactV2(CaseContextV2Model):
    fact_id: str
    case_id: str
    semantic_key: str
    display_label: str
    value: dict[str, Any]
    display_value: str
    source_kind: FactSource
    status: FactStatus
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence_refs: list[PublicEvidenceRef] = Field(default_factory=list)
    visibility: InternalVisibility = "BANK_INTERNAL"
    confirmed_by: str | None = None
    confirmed_at: datetime | None = None
    rejection_reason: str | None = None
    supersedes_fact_id: str | None = None
    version: int = Field(ge=1)
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_review_state(self):
        if self.status == "CONFIRMED" and (not self.confirmed_by or not self.confirmed_at):
            raise ValueError("확정 사실에는 확인자와 확인 시각이 필요합니다.")
        if self.status == "REJECTED" and not self.rejection_reason:
            raise ValueError("거절된 사실 후보에는 사유가 필요합니다.")
        if self.status == "SUPERSEDED" and not self.supersedes_fact_id:
            raise ValueError("대체된 사실에는 새 사실 참조가 필요합니다.")
        return self


class PublicCaseGapV2(CaseContextV2Model):
    gap_id: str
    case_id: str
    semantic_key: str
    title: str
    reason: str
    priority: Priority
    status: GapStatus
    source: Literal["AI", "BANK_STAFF", "SYSTEM_RULE"]
    evidence_refs: list[PublicEvidenceRef] = Field(default_factory=list)
    related_question_ids: list[str] = Field(default_factory=list)
    related_verification_ids: list[str] = Field(default_factory=list)
    resolution_fact_id: str | None = None
    dismissal_reason: str | None = None
    visibility: Literal["BANK_INTERNAL"] = "BANK_INTERNAL"
    source_revision: int = Field(ge=1)
    version: int = Field(ge=1)
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_terminal_state(self):
        if self.status == "RESOLVED" and not self.resolution_fact_id:
            raise ValueError("해소된 미확인 사항에는 연결된 확정 사실이 필요합니다.")
        if self.status == "DISMISSED" and not self.dismissal_reason:
            raise ValueError("제외한 미확인 사항에는 사유가 필요합니다.")
        return self


class PublicAiSuggestionV2(CaseContextV2Model):
    suggestion_id: str
    case_id: str
    suggestion_type: Literal[
        "CUSTOMER_QUESTION", "INSTITUTION_VERIFICATION", "TRANSACTION_REVIEW",
        "PROTECTIVE_ACTION", "DOCUMENT_REQUEST", "STAFF_REVIEW",
    ]
    title: str
    rationale: str
    priority: Priority
    status: SuggestionStatus
    related_gap_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[PublicEvidenceRef] = Field(default_factory=list)
    dedupe_key: str
    execution_mode: Literal["HUMAN_REVIEW_REQUIRED", "AUTO_CUSTOMER_QUESTION_ALLOWED"]
    source_revision: int = Field(ge=1)
    model_version: str | None = None
    prompt_version: str | None = None
    accepted_task_id: str | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    dismissal_reason: str | None = None
    version: int = Field(ge=1)
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_review_state(self):
        if self.status == "ACCEPTED" and not self.accepted_task_id:
            raise ValueError("채택된 AI 제안에는 생성된 담당자 업무가 필요합니다.")
        if self.status == "DISMISSED" and not self.dismissal_reason:
            raise ValueError("제외한 AI 제안에는 사유가 필요합니다.")
        if self.status in {"ACCEPTED", "DISMISSED"} and (not self.reviewed_by or not self.reviewed_at):
            raise ValueError("AI 제안 검토 결과에는 검토자와 검토 시각이 필요합니다.")
        return self


class PublicCaseTaskV2(CaseContextV2Model):
    task_id: str
    case_id: str
    source: Literal["STAFF_CREATED", "AI_SUGGESTION_ACCEPTED", "SYSTEM_REQUIRED"]
    source_suggestion_id: str | None = None
    task_type: Literal[
        "CUSTOMER_CONTACT", "INSTITUTION_VERIFICATION", "TRANSACTION_REVIEW",
        "PROTECTIVE_ACTION", "DOCUMENT_REVIEW", "OTHER",
    ]
    title: str
    description: str
    priority: Priority
    status: TaskStatus
    assignee_user_id: str | None = None
    due_at: datetime | None = None
    related_gap_ids: list[str] = Field(default_factory=list)
    related_verification_ids: list[str] = Field(default_factory=list)
    result_code: str | None = None
    result_summary: str | None = None
    evidence_refs: list[PublicEvidenceRef] = Field(default_factory=list)
    customer_visibility: Literal["INTERNAL_ONLY", "RESULT_SHAREABLE", "RESULT_PUBLISHED"] = "INTERNAL_ONLY"
    completed_by: str | None = None
    completed_at: datetime | None = None
    cancellation_reason: str | None = None
    version: int = Field(ge=1)
    created_by: str
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_terminal_state(self):
        if self.status == "COMPLETED" and (
            not self.result_summary or not self.completed_by or not self.completed_at
        ):
            raise ValueError("완료 업무에는 결과, 완료자, 완료 시각이 필요합니다.")
        if self.status == "CANCELLED" and not self.cancellation_reason:
            raise ValueError("취소 업무에는 사유가 필요합니다.")
        return self


class PublicDecisionRecordV2(CaseContextV2Model):
    decision_id: str
    case_id: str
    decision_type: Literal["FACT_REVIEW", "TASK_DECISION", "CASE_STATUS", "CUSTOMER_DISCLOSURE", "OTHER"]
    title: str
    rationale: str
    related_entity_type: Literal["FACT", "GAP", "SUGGESTION", "TASK", "VERIFICATION", "CASE"]
    related_entity_id: str
    visibility: InternalVisibility = "BANK_INTERNAL"
    actor_user_id: str
    supersedes_decision_id: str | None = None
    created_at: datetime


class PublicContextBulletV2(CaseContextV2Model):
    bullet_id: str
    text: str
    evidence_refs: list[PublicEvidenceRef] = Field(default_factory=list)


class PublicCaseContextViewV2(CaseContextV2Model):
    schema_version: Literal["case-context.v2"] = "case-context.v2"
    case_id: str
    source_revision: int = Field(ge=1)
    projection_revision: int | None = Field(default=None, ge=1)
    projection_status: Literal["CURRENT", "UPDATING", "STALE", "FAILED", "UNCACHED"]
    generated_by: Literal["LLM", "DETERMINISTIC_FALLBACK", "LAST_SUCCESS"]
    generated_at: datetime | None = None
    summary_bullets: list[PublicContextBulletV2] = Field(default_factory=list, max_length=4)
    customer_exposure: list[PublicContextBulletV2] = Field(default_factory=list)
    key_signals: list[PublicContextBulletV2] = Field(default_factory=list)
    offender_claims: list[PublicContextBulletV2] = Field(default_factory=list)
    offender_demands: list[PublicContextBulletV2] = Field(default_factory=list)
    manipulation_tactics: list[PublicContextBulletV2] = Field(default_factory=list)
    confirmed_facts: list[PublicCaseFactV2] = Field(default_factory=list)
    proposed_facts: list[PublicCaseFactV2] = Field(default_factory=list)
    open_gaps: list[PublicCaseGapV2] = Field(default_factory=list)
    ai_suggestions: list[PublicAiSuggestionV2] = Field(default_factory=list)
    active_tasks: list[PublicCaseTaskV2] = Field(default_factory=list)
    archived_tasks: list[PublicCaseTaskV2] = Field(default_factory=list)
    recent_decisions: list[PublicDecisionRecordV2] = Field(default_factory=list)


class PublicCaseContextResourcesV2(CaseContextV2Model):
    """Stored resources that support, but do not themselves equal, the AI projection."""

    schema_version: Literal["case-context-resources.v2"] = "case-context-resources.v2"
    case_id: str
    context_revision: int = Field(ge=1)
    facts: list[PublicCaseFactV2] = Field(default_factory=list)
    gaps: list[PublicCaseGapV2] = Field(default_factory=list)
    ai_suggestions: list[PublicAiSuggestionV2] = Field(default_factory=list)
    tasks: list[PublicCaseTaskV2] = Field(default_factory=list)
    decisions: list[PublicDecisionRecordV2] = Field(default_factory=list)
    unmapped_observations: list[dict[str, Any]] = Field(default_factory=list, max_length=200)


class PublicContextWorkspaceResponse(CaseContextV2Model):
    """Combined workspace contract used by the bank Context V2 screen.

    The V2 resources are strongly typed.  Older Fact-shaped response fields
    are intentionally absent; all fact reads and reviews use the V2 contract.
    """

    case_id: str
    context_revision: int = Field(ge=1)
    permissions_mode: Literal["MVP_OPEN", "ROLE_BASED"]
    can_write: bool
    can_review: bool
    can_review_suggestions: bool
    # Inference-first clients consume one stream of active context items and
    # do not branch on the legacy confirmation status.
    context_facts: list[PublicCaseFactV2] = Field(default_factory=list)
    confirmed_facts: list[PublicCaseFactV2] = Field(default_factory=list)
    proposed_facts: list[PublicCaseFactV2] = Field(default_factory=list)
    open_gaps: list[PublicCaseGapV2] = Field(default_factory=list)
    archived_gaps: list[PublicCaseGapV2] = Field(default_factory=list)
    gap_history: list[dict[str, Any]] = Field(default_factory=list)
    ai_suggestions: list[PublicAiSuggestionV2] = Field(default_factory=list)
    reviewed_suggestions: list[PublicAiSuggestionV2] = Field(default_factory=list)
    active_tasks: list[PublicCaseTaskV2] = Field(default_factory=list)
    archived_tasks: list[PublicCaseTaskV2] = Field(default_factory=list)
    recent_decisions: list[PublicDecisionRecordV2] = Field(default_factory=list)
    legacy_suggestions: list[dict[str, Any]] = Field(default_factory=list)
    legacy_gaps: list[dict[str, Any]] = Field(default_factory=list)
    legacy_records: list[dict[str, Any]] = Field(default_factory=list)
    legacy_archived_suggestions: list[dict[str, Any]] = Field(default_factory=list)


class PublicSuggestionReviewResultV2(CaseContextV2Model):
    suggestion: PublicAiSuggestionV2
    created_task: PublicCaseTaskV2 | None = None


class PublicReviewFactV2Request(CaseContextV2Model):
    expected_version: int = Field(ge=1)
    decision: Literal["CONFIRM", "REJECT", "RESTORE", "UNCONFIRM", "INVALIDATE"]
    reason: str = Field(min_length=1, max_length=1000)
    supersedes_fact_id: str | None = Field(default=None, max_length=64)


class PublicContextPanelItemV3(CaseContextV2Model):
    item_id: str
    semantic_key: str
    label: str
    display_value: str
    value: dict[str, Any] = Field(default_factory=dict)
    source_kind: str
    status: str
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence_refs: list[PublicEvidenceRef] = Field(default_factory=list)
    visibility: InternalVisibility = "BANK_INTERNAL"
    masked: bool = False
    version: int = Field(default=1, ge=1)


class PublicContextPanelSectionV3(CaseContextV2Model):
    section_id: Literal[
        "SUMMARY", "EXPOSURE", "IMPERSONATION_CONTACT", "FRAUD_CIRCUMSTANCES",
        "FACT_VERIFICATION", "STAFF_ACTIONS", "CUSTOMER_SHARE",
    ]
    title: str
    items: list[PublicContextPanelItemV3] = Field(default_factory=list)
    groups: dict[str, list[PublicContextPanelItemV3]] = Field(default_factory=dict)


class PublicStructuredAtomV3(CaseContextV2Model):
    """Privacy-safe Atom projection for bank staff; source text is excluded."""

    atom_id: str
    atom_class: str
    predicate: str
    action_state: str | None = None
    modality: str | None = None
    claim_status: str
    source_turn_id: int = Field(ge=1)


class PublicStructuredRelationV3(CaseContextV2Model):
    relation_id: str
    relation_type: str
    source_atom_id: str
    target_atom_id: str
    confidence: float = Field(ge=0, le=1)


class PublicStructuredSignalV3(CaseContextV2Model):
    signal_id: str
    signal_code: str
    severity: str
    confidence: float = Field(ge=0, le=1)
    claim_status: str
    atom_ids: list[str] = Field(default_factory=list)


class PublicStructuredContextV3(CaseContextV2Model):
    source_revision: int = Field(ge=1)
    atoms: list[PublicStructuredAtomV3] = Field(default_factory=list)
    relations: list[PublicStructuredRelationV3] = Field(default_factory=list)
    signals: list[PublicStructuredSignalV3] = Field(default_factory=list)
    feature_codes: dict[str, list[str]] = Field(default_factory=dict)


class PublicContextPanelV3(CaseContextV2Model):
    schema_version: Literal["context-panel.v3"] = "context-panel.v3"
    case_id: str
    view: Literal["bank", "customer"]
    source_revision: int = Field(ge=1)
    projection_status: Literal["CURRENT", "UPDATING", "STALE", "FAILED", "UNCACHED"] = "CURRENT"
    generated_by: Literal["DETERMINISTIC_FALLBACK", "LAST_SUCCESS", "LLM"] = "DETERMINISTIC_FALLBACK"
    updated_at: datetime | None = None
    structured_context: PublicStructuredContextV3 | None = None
    sections: list[PublicContextPanelSectionV3] = Field(min_length=7, max_length=7)


class PublicCreateFactV2Request(CaseContextV2Model):
    client_request_id: str = Field(min_length=8, max_length=100)
    semantic_key: str = Field(min_length=3, max_length=160, pattern=r"^[a-z0-9_]+(?:\.[a-z0-9_]+)+$")
    display_label: str = Field(min_length=1, max_length=255)
    value: dict[str, Any]
    display_value: str = Field(min_length=1, max_length=3000)
    evidence_refs: list[PublicEvidenceRef] = Field(default_factory=list)
    visibility: InternalVisibility = "BANK_INTERNAL"
    supersedes_fact_id: str | None = Field(default=None, max_length=64)


class PublicCreateGapV2Request(CaseContextV2Model):
    client_request_id: str = Field(min_length=8, max_length=100)
    semantic_key: str = Field(min_length=3, max_length=160, pattern=r"^[a-z0-9_]+(?:\.[a-z0-9_]+)+$")
    title: str = Field(min_length=1, max_length=300)
    reason: str = Field(min_length=1, max_length=3000)
    priority: Priority
    evidence_refs: list[PublicEvidenceRef] = Field(default_factory=list)


class PublicUpdateGapV2Request(CaseContextV2Model):
    expected_version: int = Field(ge=1)
    status: GapStatus | None = None
    reason: str | None = Field(default=None, max_length=1000)
    resolution_fact_id: str | None = Field(default=None, max_length=64)
    edited_title: str | None = Field(default=None, min_length=1, max_length=300)
    edited_reason: str | None = Field(default=None, min_length=1, max_length=3000)

    @model_validator(mode="after")
    def require_manual_reason(self):
        if self.status is None and self.edited_title is None and self.edited_reason is None:
            raise ValueError("하나 이상의 확인 항목 필드를 변경해야 합니다.")
        if self.status == "DISMISSED" and not self.reason:
            raise ValueError("미확인 사항 제외에는 사유가 필요합니다.")
        if self.status == "RESOLVED" and not self.resolution_fact_id:
            raise ValueError("미확인 사항 해소에는 확정 사실 연결이 필요합니다.")
        return self


class PublicReviewSuggestionV2Request(CaseContextV2Model):
    expected_version: int = Field(ge=1)
    decision: Literal["ACCEPT", "DISMISS"]
    edited_title: str | None = Field(default=None, max_length=300)
    edited_description: str | None = Field(default=None, max_length=3000)
    reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def require_dismissal_reason(self):
        if self.decision == "DISMISS" and not self.reason:
            raise ValueError("AI 제안 제외에는 사유가 필요합니다.")
        return self


class PublicCreateTaskV2Request(CaseContextV2Model):
    client_request_id: str = Field(min_length=8, max_length=100)
    task_type: Literal[
        "CUSTOMER_CONTACT", "INSTITUTION_VERIFICATION", "TRANSACTION_REVIEW",
        "PROTECTIVE_ACTION", "DOCUMENT_REVIEW", "OTHER",
    ]
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1, max_length=3000)
    priority: Priority
    assignee_user_id: str | None = Field(default=None, max_length=64)
    due_at: datetime | None = None
    related_gap_ids: list[str] = Field(default_factory=list)


class PublicUpdateTaskV2Request(CaseContextV2Model):
    expected_version: int = Field(ge=1)
    status: Literal["TODO", "IN_PROGRESS", "BLOCKED"] | None = None
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, min_length=1, max_length=3000)
    priority: Priority | None = None
    assignee_user_id: str | None = Field(default=None, max_length=64)
    due_at: datetime | None = None

    @model_validator(mode="after")
    def require_change(self):
        values = (self.status, self.title, self.description, self.priority, self.assignee_user_id, self.due_at)
        if all(value is None for value in values):
            raise ValueError("하나 이상의 업무 필드를 변경해야 합니다.")
        return self


class PublicCompleteTaskV2Request(CaseContextV2Model):
    expected_version: int = Field(ge=1)
    result_code: str | None = Field(default=None, max_length=100)
    result_summary: str = Field(min_length=1, max_length=3000)
    evidence_refs: list[PublicEvidenceRef] = Field(default_factory=list)


class PublicCancelTaskV2Request(CaseContextV2Model):
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=1000)


class PublicCreateDecisionV2Request(CaseContextV2Model):
    client_request_id: str = Field(min_length=8, max_length=100)
    decision_type: Literal["FACT_REVIEW", "TASK_DECISION", "CASE_STATUS", "CUSTOMER_DISCLOSURE", "OTHER"]
    title: str = Field(min_length=1, max_length=300)
    rationale: str = Field(min_length=1, max_length=3000)
    related_entity_type: Literal["FACT", "GAP", "SUGGESTION", "TASK", "VERIFICATION", "CASE"]
    related_entity_id: str = Field(min_length=1, max_length=100)
    visibility: InternalVisibility = "BANK_INTERNAL"
    supersedes_decision_id: str | None = Field(default=None, max_length=64)
