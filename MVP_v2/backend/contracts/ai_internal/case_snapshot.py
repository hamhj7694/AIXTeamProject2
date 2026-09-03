"""General Case snapshot을 AI workflow에 연결하기 위한 내부 의미 Contract."""
from __future__ import annotations

from pydantic import Field

from contracts.ai_internal.mvp_workflow import (
    CaseBrief,
    QuestionCandidate,
    QuestionRecommendationContext,
    UnresolvedItem,
)
from contracts.diagnosis import DiagnosisResult, StrictModel


class CaseSnapshotAiInput(StrictModel):
    """AI workflow가 필요로 하는 최소 Case 입력이다."""

    case_id: str | None = None
    diagnosis: DiagnosisResult | None = None
    question_context: QuestionRecommendationContext = Field(default_factory=QuestionRecommendationContext)
    warnings: list[str] = Field(default_factory=list)


class CaseSnapshotPresentationFixture(StrictModel):
    """Public Chat Contract 확정 전 Case-support 결과를 담는 내부 fixture다."""

    case_id: str | None = None
    case_brief: CaseBrief | None = None
    recommended_questions: list[QuestionCandidate] = Field(default_factory=list)
    unresolved_items: list[UnresolvedItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
