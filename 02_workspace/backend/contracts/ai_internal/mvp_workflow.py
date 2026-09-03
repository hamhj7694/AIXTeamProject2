"""공모전 MVP의 Diagnosis 이후 AI 내부 Contract.

저장·전송 Contract가 아니라 AI가 담당자에게 추천하는 구조화 결과다.
"""
from __future__ import annotations

from enum import Enum

from pydantic import Field

from contracts.diagnosis import Evidence, RiskLevel, StrictModel


class QuestionPriority(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"


class TargetField(str, Enum):
    TRANSFER_STATUS = "transfer_status"
    TRANSFER_PURPOSE = "transfer_purpose"
    CLAIMED_ORGANIZATION = "claimed_organization"
    INCIDENT_CLAIM = "incident_claim"
    PERSONAL_INFORMATION_EXPOSURE = "personal_information_exposure"
    AUTHENTICATION_INFORMATION_EXPOSURE = "authentication_information_exposure"


class ExecutionMode(str, Enum):
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"


class QuestionRecommendationContext(StrictModel):
    """질문 추천 중복을 막기 위해 AI가 알아야 하는 최소 상태.

    DB verification row나 화면 상태가 아닌, 질문 대상 항목의 의미 상태만 보존한다.
    ``confirmed_fields``와 ``pending_question_fields``만 추천 대상 Field를
    제외한다. 답변 도착은 사실 확인이 아니므로, ``answered_question_ids``는
    같은 문장을 반복하지 않기 위한 AI 질문 후보 ID 목록으로만 사용한다.
    """

    confirmed_fields: list[TargetField] = Field(default_factory=list)
    pending_question_fields: list[TargetField] = Field(default_factory=list)
    answered_question_ids: list[str] = Field(default_factory=list)

    def excluded_target_fields(self) -> set[TargetField]:
        return {
            *self.confirmed_fields,
            *self.pending_question_fields,
        }

    def has_answered_question(self, question_id: str) -> bool:
        return question_id in self.answered_question_ids


class UnresolvedItem(StrictModel):
    target_field: TargetField
    description: str
    priority: QuestionPriority


class CaseBrief(StrictModel):
    schema_version: str = "case_brief.v1"
    summary: str
    incident_type: str
    risk_level: RiskLevel
    risk_score: float = Field(ge=0, le=100)
    impersonation_target: str | None = None
    claims: list[str] = Field(default_factory=list)
    transfer_context: str | None = None
    mentioned_amount_krw: float | None = Field(default=None, ge=0)
    risk_evidence: list[Evidence] = Field(default_factory=list)
    counter_evidence: list[Evidence] = Field(default_factory=list)
    unresolved_items: list[UnresolvedItem] = Field(default_factory=list)
    next_checks: list[str] = Field(default_factory=list)


class QuestionCandidate(StrictModel):
    question_id: str
    priority: QuestionPriority
    target_field: TargetField
    question: str
    reason: str
    evidence_refs: list[Evidence] = Field(default_factory=list)
    execution_mode: ExecutionMode = ExecutionMode.HUMAN_REVIEW_REQUIRED


class CustomerAnswerResult(StrictModel):
    target_field: TargetField
    raw_answer: str = Field(min_length=1)
    structured_value: str | None = None
    confidence: float = Field(ge=0, le=1)
    unresolved: bool
    evidence_text: str | None = None
    warnings: list[str] = Field(default_factory=list)


class ResolvedItem(StrictModel):
    target_field: TargetField
    structured_value: str
    evidence_text: str


class BriefUpdateResult(StrictModel):
    schema_version: str = "brief_update.v1"
    updated_summary: str
    resolved_items: list[ResolvedItem] = Field(default_factory=list)
    unresolved_items: list[UnresolvedItem] = Field(default_factory=list)
    risk_evidence: list[Evidence] = Field(default_factory=list)
    counter_evidence: list[Evidence] = Field(default_factory=list)
    next_checks: list[str] = Field(default_factory=list)
