"""결정론적 MVP case-support 서비스를 하나의 동기 흐름으로 연결한다."""
from __future__ import annotations

from contracts.ai_internal.mvp_workflow import (
    BriefUpdateResult,
    CaseBrief,
    CustomerAnswerBriefUpdateResult,
    CustomerAnswerResult,
    QuestionCandidate,
    QuestionRecommendationContext,
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

    def recommend_questions(
        self,
        brief: CaseBrief,
        question_context: QuestionRecommendationContext | None = None,
    ) -> list[QuestionCandidate]:
        return self._question_service.recommend_questions(brief, question_context)

    def structure_answer(
        self, target_field: TargetField, raw_answer: str,
    ) -> CustomerAnswerResult:
        return self._answer_service.structure_answer(target_field, raw_answer)

    def update_brief(
        self, brief: CaseBrief, answer: CustomerAnswerResult,
    ) -> BriefUpdateResult:
        return self._brief_update_service.update(brief, answer)

    def process_customer_answer(
        self,
        brief: CaseBrief,
        selected_question: QuestionCandidate,
        answer_text: str,
        *,
        source_reference: str | None = None,
    ) -> CustomerAnswerBriefUpdateResult:
        """답변 수신과 사실 확정을 분리한 안전한 Brief 갱신 흐름이다."""
        structured_answer = self.structure_answer(selected_question.target_field, answer_text)
        brief_update = self.update_brief(brief, structured_answer)
        warnings = list(structured_answer.warnings)

        if (
            not structured_answer.unresolved
            and not brief_update.resolved_items
            and "Selected question target is not unresolved in the current brief." not in warnings
        ):
            warnings.append("Selected question target is not unresolved in the current brief.")

        return CustomerAnswerBriefUpdateResult(
            selected_question=selected_question,
            structured_answer=structured_answer,
            brief_update=brief_update,
            unresolved_items=list(brief_update.unresolved_items),
            warnings=warnings,
            source_reference=source_reference,
        )
