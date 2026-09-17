"""Public Case workflow resources owned by the General API."""

from __future__ import annotations

import hashlib
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from .customer_progress import CustomerProgressItem


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
    allow_multi_select: bool = False


class PublicQuestionOption(PublicWorkflowModel):
    option_id: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=500)


class PublicCaseSupportBrief(PublicWorkflowModel):
    """화면에 필요한 Case-support Brief만 노출하는 공개 투영이다."""
    summary: str
    incident_type: str
    risk_level: str
    risk_score: float
    next_checks: list[str] = Field(default_factory=list)


class PublicCaseContextProjection(PublicWorkflowModel):
    """AI가 최신 Shared Case 상태로 재구성한 화면용 사건 맥락."""

    situation_summary: str = ""
    key_signals: list[str] = Field(default_factory=list)
    offender_claims: list[str] = Field(default_factory=list)
    offender_demands: list[str] = Field(default_factory=list)
    manipulation_tactics: list[str] = Field(default_factory=list)
    customer_exposure: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    # AI가 계산한 금액 이벤트를 Context Panel에 전달한다.
    # 원문이 아닌 개인정보 비식별 구조화 값만 공개 투영에 포함한다.
    money_events: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    confirmed_facts: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    proposed_facts: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    unresolved_items: list[str] = Field(default_factory=list, max_length=100)
    verification_records: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    staff_actions: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    projection_revision: int | None = Field(default=None, ge=1)


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
    source_revision: int | None = Field(default=None, ge=1)
    projection_revision: int | None = Field(default=None, ge=1)
    projection_status: Literal["CURRENT", "UPDATING", "STALE", "FAILED", "UNCACHED"] = "UNCACHED"


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
    allow_multi_select: bool = False
    option_items: list[PublicQuestionOption] = Field(default_factory=list, max_length=8)
    question_version: int = Field(default=1, ge=1)
    answer_payload: dict[str, Any] | None = None
    answer_question_version: int | None = Field(default=None, ge=1)


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
    allow_multi_select: bool = False
    option_items: list[PublicQuestionOption] = Field(default_factory=list, max_length=8)
    question_version: int = Field(default=1, ge=1)
    answer_payload: dict[str, Any] | None = None
    answer_question_version: int | None = Field(default=None, ge=1)


class PublicAnswerCustomerQuestionRequest(PublicWorkflowModel):
    raw_answer: str | None = Field(default=None, min_length=1, max_length=10_000)
    selected_option_ids: list[str] = Field(default_factory=list, max_length=8)
    free_text: str | None = Field(default=None, max_length=10_000)
    question_version: int | None = Field(default=None, ge=1)
    actor_user_id: str = Field(min_length=1, max_length=64)
    actor_display_name: str = Field(min_length=1, max_length=80)

    @model_validator(mode="after")
    def require_answer_content(self):
        if not self.raw_answer and not self.selected_option_ids and not (self.free_text or "").strip():
            raise ValueError("선택지 또는 직접 입력 답변이 필요합니다.")
        if len(set(self.selected_option_ids)) != len(self.selected_option_ids):
            raise ValueError("같은 선택지를 중복 선택할 수 없습니다.")
        return self


def question_option_items(question_id: str, options: list[str]) -> list[dict[str, str]]:
    """Give legacy string options stable IDs without changing their stored labels."""
    return [
        {
            "option_id": f"opt-{hashlib.sha256(f'{question_id}:{index}:{label}'.encode()).hexdigest()[:20]}",
            "label": label,
        }
        for index, label in enumerate(options)
    ]


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
    title: str | None = Field(default=None, min_length=1, max_length=300)
    note: str = Field(min_length=1, max_length=10_000)
    visibility: Literal["BANK_INTERNAL", "CUSTOMER_SHARED"] = "BANK_INTERNAL"

    @model_validator(mode="after")
    def normalize_title(self):
        if self.title is not None and not self.title.strip():
            raise ValueError("Action title must not be blank.")
        return self


class PublicUpdateActionRequest(PublicWorkflowModel):
    # None is a temporary compatibility path for the frozen legacy frontend.
    # New clients must echo the Action response version to receive conflict protection.
    expected_version: int | None = Field(default=None, ge=1)
    status: Literal["REQUESTED", "IN_PROGRESS", "COMPLETED", "CANCELLED"] | None = None
    title: str | None = Field(default=None, min_length=1, max_length=300)
    note: str | None = Field(default=None, min_length=1, max_length=10_000)
    visibility: Literal["BANK_INTERNAL", "CUSTOMER_SHARED"] | None = None
    updated_by: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def require_change(self):
        if self.status is None and self.title is None and self.note is None and self.visibility is None:
            raise ValueError("Action 변경값을 하나 이상 제공해야 합니다.")
        if self.title is not None and not self.title.strip():
            raise ValueError("Action title must not be blank.")
        if self.note is not None and not self.note.strip():
            raise ValueError("체크리스트 내용은 비워둘 수 없습니다.")
        return self


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
    note: str | None = None
    summary_source_revision: int | None = None
    current_context_revision: int | None = None
    is_stale: bool | None = None


class PublicActionResponse(PublicWorkflowModel):
    action_id: str
    case_id: str
    action_type: str
    status: str
    actor_type: str
    title: str | None = None
    note: str
    visibility: Literal["BANK_INTERNAL", "CUSTOMER_SHARED"] = "BANK_INTERNAL"
    version: int = 1
    created_at: str
    updated_at: str | None = None
    updated_by: str | None = None


class PublicCaseBundleResponse(PublicWorkflowModel):
    customer_progress: list[CustomerProgressItem] = Field(default_factory=list)
    case: dict[str, Any]
    live_report: dict[str, Any] | None
    final_report: PublicReportResponse | None = None
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
    options = record.get("options", [])
    return PublicCustomerQuestionResponse.model_validate({
        "question_id": record["question_id"], "case_id": record["case_id"],
        "source": record.get("source", "CUSTOMER_AGENT"), "target_field": record["target_field"],
        "question_text": record["question_text"], "reason": record["reason"],
        "priority": record["priority"], "status": record["status"], "sequence": record["sequence"],
        "requested_by": record.get("requested_by"), "asked_at": record.get("asked_at"),
        "answered_at": record.get("answered_at"), "answer_message_id": record.get("answer_message_id"), "answer_text": record.get("answer_text"),
        "options": options,
        "customer_explanation": record.get("customer_explanation"),
        "answer_mode": record.get("answer_mode", "CHOICE_OR_TEXT"),
        "allow_free_text": record.get("allow_free_text", True),
        "allow_multi_select": record.get("allow_multi_select", False),
        "option_items": record.get("option_items") or question_option_items(record["question_id"], options),
        "question_version": record.get("question_version", 1),
        "answer_payload": record.get("answer_payload"),
        "answer_question_version": record.get("answer_question_version"),
    })


def to_public_customer_question_view(record: dict[str, Any]) -> PublicCustomerQuestionView:
    options = record.get("options", [])
    return PublicCustomerQuestionView.model_validate({
        "question_id": record["question_id"], "case_id": record["case_id"],
        "question_text": record["question_text"], "priority": record["priority"],
        "status": record["status"], "sequence": record["sequence"],
        "answered_at": record.get("answered_at"), "answer_message_id": record.get("answer_message_id"), "answer_text": record.get("answer_text"),
        "options": options,
        "customer_explanation": record.get("customer_explanation"),
        "answer_mode": record.get("answer_mode", "CHOICE_OR_TEXT"),
        "allow_free_text": record.get("allow_free_text", True),
        "allow_multi_select": record.get("allow_multi_select", False),
        "option_items": record.get("option_items") or question_option_items(record["question_id"], options),
        "question_version": record.get("question_version", 1),
        "answer_payload": record.get("answer_payload"),
        "answer_question_version": record.get("answer_question_version"),
    })


def to_public_verification(record: dict[str, Any]) -> PublicVerificationResponse:
    return PublicVerificationResponse.model_validate(record)


def to_public_action(record: dict[str, Any]) -> PublicActionResponse:
    return PublicActionResponse.model_validate(record)
