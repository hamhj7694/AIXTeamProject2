from __future__ import annotations

import json
import unittest
from pathlib import Path

from ai_api.app.domains.case_support import MvpWorkflowService
from ai_api.app.domains.case_support.answer_service import CustomerAnswerStructuringService
from ai_api.app.domains.case_support.brief_service import CaseBriefService
from ai_api.app.domains.case_support.brief_update_service import BriefUpdateService
from ai_api.app.domains.case_support.question_service import QuestionIntelligenceService
from contracts.ai_internal.mvp_workflow import TargetField
from contracts.diagnosis import DiagnosisResult


class MvpWorkflowContractTest(unittest.TestCase):
    @staticmethod
    def _high_diagnosis() -> DiagnosisResult:
        path = Path(__file__).resolve().parents[2] / "contracts" / "ai_internal" / "fixtures" / "diagnosis.high.v1.json"
        return DiagnosisResult.model_validate(json.loads(path.read_text(encoding="utf-8"))["response"])

    def test_high_diagnosis_to_question_answer_update(self) -> None:
        diagnosis = self._high_diagnosis()
        workflow = MvpWorkflowService()
        brief = workflow.build_brief(diagnosis)
        questions = workflow.recommend_questions(brief)
        self.assertTrue(any(item.target_field is TargetField.TRANSFER_STATUS for item in questions))
        self.assertTrue(all(item.execution_mode.value == "HUMAN_REVIEW_REQUIRED" for item in questions))
        answer = workflow.structure_answer(TargetField.TRANSFER_STATUS, "네, 아직 돈은 안 보냈어요.")
        self.assertEqual(answer.structured_value, "NOT_TRANSFERRED")
        update = workflow.update_brief(brief, answer)
        self.assertEqual(update.resolved_items[0].target_field, TargetField.TRANSFER_STATUS)

    def test_ambiguous_answer_stays_unresolved(self) -> None:
        answer = MvpWorkflowService().structure_answer(TargetField.TRANSFER_STATUS, "잘 모르겠습니다.")
        self.assertTrue(answer.unresolved)
        self.assertIsNone(answer.structured_value)
        self.assertTrue(answer.warnings)

    def test_workflow_delegates_to_deterministic_services(self) -> None:
        diagnosis = self._high_diagnosis()
        workflow = MvpWorkflowService()

        brief = workflow.build_brief(diagnosis)
        self.assertEqual(brief, CaseBriefService().build_brief(diagnosis))

        questions = workflow.recommend_questions(brief)
        self.assertEqual(questions, QuestionIntelligenceService().recommend_questions(brief))

        answer = workflow.structure_answer(TargetField.TRANSFER_STATUS, "아직 송금 안 했어요")
        self.assertEqual(
            answer,
            CustomerAnswerStructuringService().structure_answer(
                TargetField.TRANSFER_STATUS, "아직 송금 안 했어요",
            ),
        )

        update = workflow.update_brief(brief, answer)
        self.assertEqual(update, BriefUpdateService().update(brief, answer))
        self.assertTrue(update.resolved_items)
        self.assertTrue(update.unresolved_items)
        self.assertEqual(update.__class__.model_validate(update.model_dump()), update)
