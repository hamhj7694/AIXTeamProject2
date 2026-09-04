"""General Case snapshot을 AI workflow에 연결하기 위한 내부 의미 Contract."""
from __future__ import annotations

from typing import Literal

from pydantic import Field

from contracts.ai_internal.mvp_workflow import (
    CaseBrief,
    QuestionCandidate,
    QuestionRecommendationContext,
    UnresolvedItem,
)
from contracts.diagnosis import DiagnosisResult, StrictModel


class CaseSnapshotQuestion(StrictModel):
    question_id: str
    target_field: str
    question_text: str
    priority: Literal["P0", "P1", "P2"] = "P1"
    status: Literal["PENDING", "ASKED", "ANSWERED", "SKIPPED"]
    answer_text: str | None = None


class CaseSnapshotFact(StrictModel):
    fact_id: str
    field: str
    value: str
    status: Literal["PROPOSED", "CONFIRMED", "UNRESOLVED"]


class CaseSnapshotVerification(StrictModel):
    verification_task_id: str
    target: str
    claim: str
    status: str
    result_summary: str | None = None


class CaseSnapshotAction(StrictModel):
    action_id: str
    action_type: str
    status: str
    note: str = ""


class CaseSnapshotAiInput(StrictModel):
    """AI workflow가 초기 진단과 최신 Shared Case 상태를 함께 보는 입력이다."""

    case_id: str | None = None
    diagnosis: DiagnosisResult | None = None
    question_context: QuestionRecommendationContext = Field(default_factory=QuestionRecommendationContext)
    questions: list[CaseSnapshotQuestion] = Field(default_factory=list)
    facts: list[CaseSnapshotFact] = Field(default_factory=list)
    verifications: list[CaseSnapshotVerification] = Field(default_factory=list)
    actions: list[CaseSnapshotAction] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CaseContextProjection(StrictModel):
    """최신 Shared Case에서 은행 화면에 투영할 사건 맥락."""

    key_signals: list[str] = Field(default_factory=list)
    offender_claims: list[str] = Field(default_factory=list)
    offender_demands: list[str] = Field(default_factory=list)


class CaseSnapshotPresentation(StrictModel):
    """Case-support 결과를 서비스 경계로 전달하는 내부 응답 모델."""

    case_id: str | None = None
    case_brief: CaseBrief | None = None
    case_context: CaseContextProjection | None = None
    recommended_questions: list[QuestionCandidate] = Field(default_factory=list)
    unresolved_items: list[UnresolvedItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
