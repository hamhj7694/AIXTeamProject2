"""결정론적 MVP case-support 서비스를 하나의 동기 흐름으로 연결한다."""
from __future__ import annotations

from contracts.ai_internal.mvp_workflow import (
    BriefUpdateResult,
    CaseBrief,
    CustomerAnswerResult,
    QuestionCandidate,
    TargetField,
)
from contracts.diagnosis import DiagnosisResult

from .answer_service import CustomerAnswerStructuringService
from .brief_service import CaseBriefService
from .brief_update_service import BriefUpdateService
from .question_service import QuestionIntelligenceService


class MvpWorkflowService:
    """기존 AI 서비스를 조합하는 동기 MVP orchestration 계층.

    LLM 보강 경로(``CaseBriefService.build``)는 의도적으로 사용하지 않는다.
    이 서비스는 fixture 기반의 재현 가능한 기본 경로만 제공한다.
    """

    def __init__(self) -> None:
        self._brief_service = CaseBriefService()
        self._question_service = QuestionIntelligenceService()
        self._answer_service = CustomerAnswerStructuringService()
        self._brief_update_service = BriefUpdateService()

    def build_brief(self, diagnosis: DiagnosisResult) -> CaseBrief:
        return self._brief_service.build_brief(diagnosis)

    def recommend_questions(self, brief: CaseBrief) -> list[QuestionCandidate]:
        return self._question_service.recommend_questions(brief)

    def structure_answer(
        self, target_field: TargetField, raw_answer: str,
    ) -> CustomerAnswerResult:
        return self._answer_service.structure_answer(target_field, raw_answer)

    def update_brief(
        self, brief: CaseBrief, answer: CustomerAnswerResult,
    ) -> BriefUpdateResult:
        return self._brief_update_service.update(brief, answer)
