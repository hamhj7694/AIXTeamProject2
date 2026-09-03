"""General Case snapshot을 AI workflow에 연결하기 위한 내부 의미 Contract."""
from __future__ import annotations

from pydantic import Field

from contracts.ai_internal.mvp_workflow import CaseBrief, QuestionCandidate, UnresolvedItem
from contracts.diagnosis import DiagnosisResult, StrictModel


class CaseSnapshotAiInput(StrictModel):
    """AI workflow가 필요로 하는 최소 Case 입력.

    General API의 DB row나 Public DTO를 복사하지 않는다. snapshot의 구조 차이는
    adapter가 흡수하고, AI core에는 case 식별자·검증된 diagnosis·경고만 전달한다.
    """

    case_id: str | None = None
    diagnosis: DiagnosisResult | None = None
    warnings: list[str] = Field(default_factory=list)


class CaseSnapshotPresentationFixture(StrictModel):
    """Chat Contract가 확정되기 전 결과 소비 방식을 보이는 내부 fixture."""

    case_id: str | None = None
    case_brief: CaseBrief | None = None
    recommended_questions: list[QuestionCandidate] = Field(default_factory=list)
    unresolved_items: list[UnresolvedItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
