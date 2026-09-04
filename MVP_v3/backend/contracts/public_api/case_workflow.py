"""Public Case workflow resources owned by the General API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class PublicWorkflowModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PublicQuestionCandidateResponse(PublicWorkflowModel):
    question_id: str
    target_field: str
    question_text: str
    reason: str
    priority: Literal["P0", "P1", "P2"]
    options: list[str] = Field(default_factory=list, max_length=8)
    customer_explanation: str | None = Field(default=None, max_length=500)
    answer_mode: Literal["SINGLE_CHOICE", "TEXT", "CHOICE_OR_TEXT"] = "CHOICE_OR_TEXT"
    allow_free_text: bool = True


class PublicCaseSupportBrief(PublicWorkflowModel):
    """화면에 필요한 Case-support Brief만 노출하는 공개 투영이다."""
    summary: str
    incident_type: str
    risk_level: str
    risk_score: float
    next_checks: list[str] = Field(default_factory=list)


class PublicCaseContextProjection(PublicWorkflowModel):
    """AI가 최신 Shared Case 상태로 재구성한 화면용 사건 맥락."""

    key_signals: list[str] = Field(default_factory=list)
    offender_claims: list[str] = Field(default_factory=list)
    offender_demands: list[str] = Field(default_factory=list)


class PublicUnresolvedItemResponse(PublicWorkflowModel):
    target_field: str
    description: str
    priority: Literal["P0", "P1", "P2"]


class PublicCaseSupportSnapshotResponse(PublicWorkflowModel):
    """General API가 AI 내부 snapshot을 화면 안전 형태로 변환한 결과다."""
    case_id: str
    available: bool
    case_brief: PublicCaseSupportBrief | None = None
    case_context: PublicCaseContextProjection | None = None
    recommended_questions: list[PublicQuestionCandidateResponse] = Field(default_factory=list)
    unresolved_items: list[PublicUnresolvedItemResponse] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class PublicQueueCustomerQuestionsRequest(PublicWorkflowModel):
    questions: list[PublicQuestionCandidateResponse] = Field(min_length=1, max_length=10)
    requested_by: str = Field(min_length=1, max_length=80)


class PublicCustomerQuestionResponse(PublicWorkflowModel):
    question_id: str
    case_id: str
    source: Literal["BANK_SELECTED", "CUSTOMER_AGENT"]
    target_field: str
    question_text: str
    reason: str
    priority: Literal["P0", "P1", "P2"]
    status: Literal["PENDING", "ASKED", "ANSWERED", "SKIPPED"]
    sequence: int
    requested_by: str | None = None
    asked_at: str | None = None
    answered_at: str | None = None
    answer_message_id: str | None = None
    answer_text: str | None = None
    options: list[str] = Field(default_factory=list, max_length=8)
    customer_explanation: str | None = Field(default=None, max_length=500)
    answer_mode: Literal["SINGLE_CHOICE", "TEXT", "CHOICE_OR_TEXT"] = "CHOICE_OR_TEXT"
    allow_free_text: bool = True


class PublicCustomerQuestionView(PublicWorkflowModel):
    """Customer-facing projection: never expose the internal requester or reason."""
    question_id: str
    case_id: str
    question_text: str
    priority: Literal["P0", "P1", "P2"]
    status: Literal["PENDING", "ASKED", "ANSWERED", "SKIPPED"]
    sequence: int
    answered_at: str | None = None
    answer_message_id: str | None = None
    answer_text: str | None = None
    options: list[str] = Field(default_factory=list, max_length=8)
    customer_explanation: str | None = Field(default=None, max_length=500)
    answer_mode: Literal["SINGLE_CHOICE", "TEXT", "CHOICE_OR_TEXT"] = "CHOICE_OR_TEXT"
    allow_free_text: bool = True


class PublicAnswerCustomerQuestionRequest(PublicWorkflowModel):
    raw_answer: str = Field(min_length=1, max_length=10_000)
    actor_user_id: str = Field(min_length=1, max_length=64)
    actor_display_name: str = Field(min_length=1, max_length=80)


class PublicCaseFactResponse(PublicWorkflowModel):
    fact_id: str
    case_id: str
    field: str
    value: str
    source: Literal["AI_EXTRACTED", "HUMAN_CONFIRMED", "VERIFIED", "UNRESOLVED"]
    status: Literal["PROPOSED", "CONFIRMED", "UNRESOLVED"]
    confidence: float = Field(ge=0, le=1)
    evidence_message_id: str | None = None
    source_question_id: str | None = None
    confirmed_by: str | None = None
    confirmed_at: str | None = None
    created_at: str


class PublicConfirmCaseFactRequest(PublicWorkflowModel):
    confirmed_by: str = Field(min_length=1, max_length=80)


class PublicPersonalNoteCreateRequest(PublicWorkflowModel):
    author_id: str = Field(min_length=1, max_length=80)
    content: str = Field(min_length=1, max_length=10_000)


class PublicPersonalNoteUpdateRequest(PublicWorkflowModel):
    author_id: str = Field(min_length=1, max_length=80)
    content: str = Field(min_length=1, max_length=10_000)


class PublicPersonalNoteResponse(PublicWorkflowModel):
    note_id: str
    case_id: str
    author_id: str
    content: str
    visibility: Literal["PRIVATE_TO_AUTHOR"]
    created_at: str
    updated_at: str


class PublicCreateVerificationRequest(PublicWorkflowModel):
    claim: str = Field(min_length=1, max_length=10_000)
    target: str = Field(min_length=1, max_length=255)


class PublicUpdateVerificationRequest(PublicWorkflowModel):
    expected_version: int = Field(ge=1)
    status: Literal["PENDING", "IN_PROGRESS", "COMPLETED", "ON_HOLD", "FAILED"]
    result_summary: str | None = Field(default=None, max_length=10_000)
    evidence_url: str | None = Field(default=None, max_length=2_000)
    verified_by: str | None = Field(default=None, max_length=80)
    rag_source: str | None = Field(default=None, max_length=255)
    customer_visible: bool | None = None


class PublicVerificationResponse(PublicWorkflowModel):
    verification_task_id: str
    case_id: str
    claim: str
    target: str
    status: str
    version: int = Field(ge=1)
    created_at: str
    updated_at: str
    result_summary: str | None = None
    evidence_url: str | None = None
    verified_by: str | None = None
    rag_source: str | None = None
    customer_visible: bool = False


class PublicCustomerVerificationResult(PublicWorkflowModel):
    """Minimal customer projection; internal evidence and reviewer details stay private."""

    verification_task_id: str
    target: str
    result_summary: str
    published_at: str | None = None


class PublicCreateActionRequest(PublicWorkflowModel):
    action_type: str = Field(min_length=1, max_length=64)
    actor_type: Literal["BANK_STAFF", "SYSTEM"]
    note: str = Field(min_length=1, max_length=10_000)


class PublicUpdateActionRequest(PublicWorkflowModel):
    status: Literal["REQUESTED", "COMPLETED"]
    updated_by: str = Field(min_length=1, max_length=128)


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
    updated_at: str | None = None
    updated_by: str | None = None


class PublicCaseBundleResponse(PublicWorkflowModel):
    case: dict[str, Any]
    live_report: dict[str, Any] | None
    questions: list[dict[str, Any]]
    progress_items: list[dict[str, Any]]
    verification_tasks: list[PublicVerificationResponse]
    customer_verification_results: list[PublicCustomerVerificationResult] = Field(default_factory=list)
    recent_messages: list[dict[str, Any]]
    recent_actions: list[PublicActionResponse]
    recent_events: list[dict[str, Any]]
    voice_session: PublicVoiceSessionResponse | None
    cursor: str | None


def to_public_customer_question(record: dict[str, Any]) -> PublicCustomerQuestionResponse:
    return PublicCustomerQuestionResponse.model_validate({
        "question_id": record["question_id"], "case_id": record["case_id"],
        "source": record.get("source", "CUSTOMER_AGENT"), "target_field": record["target_field"],
        "question_text": record["question_text"], "reason": record["reason"],
        "priority": record["priority"], "status": record["status"], "sequence": record["sequence"],
        "requested_by": record.get("requested_by"), "asked_at": record.get("asked_at"),
        "answered_at": record.get("answered_at"), "answer_message_id": record.get("answer_message_id"), "answer_text": record.get("answer_text"),
        "options": record.get("options", []),
        "customer_explanation": record.get("customer_explanation"),
        "answer_mode": record.get("answer_mode", "CHOICE_OR_TEXT"),
        "allow_free_text": record.get("allow_free_text", True),
    })


def to_public_customer_question_view(record: dict[str, Any]) -> PublicCustomerQuestionView:
    return PublicCustomerQuestionView.model_validate({
        "question_id": record["question_id"], "case_id": record["case_id"],
        "question_text": record["question_text"], "priority": record["priority"],
        "status": record["status"], "sequence": record["sequence"],
        "answered_at": record.get("answered_at"), "answer_message_id": record.get("answer_message_id"), "answer_text": record.get("answer_text"),
        "options": record.get("options", []),
        "customer_explanation": record.get("customer_explanation"),
        "answer_mode": record.get("answer_mode", "CHOICE_OR_TEXT"),
        "allow_free_text": record.get("allow_free_text", True),
    })


def to_public_verification(record: dict[str, Any]) -> PublicVerificationResponse:
    return PublicVerificationResponse.model_validate(record)


def to_public_action(record: dict[str, Any]) -> PublicActionResponse:
    return PublicActionResponse.model_validate(record)
