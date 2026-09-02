"""Role-based facades for the existing deterministic case-support workflow.

These agents deliberately do not contain AI business logic. They make each
responsibility explicit while preserving the validated workflow outputs.
"""
from __future__ import annotations

from contracts.ai_internal.mvp_workflow import (
    BriefUpdateResult,
    CaseBrief,
    CustomerAnswerResult,
    QuestionCandidate,
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

    def recommend_questions(self, brief: CaseBrief) -> list[QuestionCandidate]:
        # QuestionCandidate keeps HUMAN_REVIEW_REQUIRED from the existing contract.
        return self._workflow.recommend_questions(brief)

    def structure_answer(
        self, target_field: TargetField, raw_answer: str,
    ) -> CustomerAnswerResult:
        return self._workflow.structure_answer(target_field, raw_answer)


class CaseUpdateAgent:
    """Apply a structured customer answer to a case brief."""

    def __init__(self, workflow: MvpWorkflowService | None = None) -> None:
        self._workflow = workflow or MvpWorkflowService()

    def update_brief(
        self, brief: CaseBrief, answer: CustomerAnswerResult,
    ) -> BriefUpdateResult:
        return self._workflow.update_brief(brief, answer)
