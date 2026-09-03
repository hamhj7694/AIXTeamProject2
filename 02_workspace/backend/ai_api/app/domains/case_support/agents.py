"""Role-based facades for the existing deterministic case-support workflow.

These agents deliberately do not contain AI business logic. They make each
responsibility explicit while preserving the validated workflow outputs.
"""
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

from .workflow import MvpWorkflowService


class CaseSupportAgent:
    """Build a case brief from an existing diagnosis result."""

    def __init__(self, workflow: MvpWorkflowService | None = None) -> None:
        self._workflow = workflow or MvpWorkflowService()

    def build_brief(self, diagnosis: DiagnosisResult) -> CaseBrief:
        return self._workflow.build_brief(diagnosis)


class CustomerVerificationAgent:
    """Recommend human-reviewed questions and structure customer answers."""

    def __init__(self, workflow: MvpWorkflowService | None = None) -> None:
        self._workflow = workflow or MvpWorkflowService()

    def recommend_questions(
        self,
        brief: CaseBrief,
        question_context: QuestionRecommendationContext | None = None,
    ) -> list[QuestionCandidate]:
        # QuestionCandidate keeps HUMAN_REVIEW_REQUIRED from the existing contract.
        return self._workflow.recommend_questions(brief, question_context)

    def structure_answer(
        self, target_field: TargetField, raw_answer: str,
    ) -> CustomerAnswerResult:
        return self._workflow.structure_answer(target_field, raw_answer)

    def process_answer_and_update_brief(
        self,
        brief: CaseBrief,
        selected_question: QuestionCandidate,
        answer_text: str,
        *,
        source_reference: str | None = None,
    ) -> CustomerAnswerBriefUpdateResult:
        """Expose the existing workflow as one customer-answer invocation."""
        return self._workflow.process_customer_answer(
            brief,
            selected_question,
            answer_text,
            source_reference=source_reference,
        )


class CaseUpdateAgent:
    """Apply a structured customer answer to a case brief."""

    def __init__(self, workflow: MvpWorkflowService | None = None) -> None:
        self._workflow = workflow or MvpWorkflowService()

    def update_brief(
        self, brief: CaseBrief, answer: CustomerAnswerResult,
    ) -> BriefUpdateResult:
        return self._workflow.update_brief(brief, answer)
