from __future__ import annotations

import json
import unittest
from pathlib import Path

from ai_api.app.domains.case_support import MvpWorkflowService
from contracts.ai_internal.mvp_workflow import TargetField
from contracts.diagnosis import DiagnosisResult


class CustomerAnswerBriefUpdateTest(unittest.TestCase):
    @staticmethod
    def _brief_and_question():
        fixture = Path(__file__).resolve().parents[2] / "contracts" / "ai_internal" / "fixtures" / "diagnosis.high.v1.json"
        diagnosis = DiagnosisResult.model_validate(json.loads(fixture.read_text(encoding="utf-8"))["response"])
        workflow = MvpWorkflowService()
        brief = workflow.build_brief(diagnosis)
        question = next(item for item in workflow.recommend_questions(brief) if item.target_field is TargetField.TRANSFER_STATUS)
        return workflow, brief, question

    def test_explicit_non_transfer_answer_updates_only_the_selected_unresolved_field(self) -> None:
        workflow, brief, question = self._brief_and_question()
        result = workflow.process_customer_answer(brief, question, "송금한 적 없어요.", source_reference="message-123")

        self.assertEqual(result.structured_answer.structured_value, "NOT_TRANSFERRED")
        self.assertEqual(result.brief_update.resolved_items[0].target_field, TargetField.TRANSFER_STATUS)
        self.assertEqual(result.source_reference, "message-123")

    def test_request_or_ambiguous_answer_does_not_confirm_a_fact(self) -> None:
        workflow, brief, question = self._brief_and_question()
        for answer_text in ("상대방이 송금하라고 했어요.", "기억이 안 나요."):
            with self.subTest(answer_text=answer_text):
                result = workflow.process_customer_answer(brief, question, answer_text)
                self.assertTrue(result.structured_answer.unresolved)
                self.assertEqual(result.brief_update.resolved_items, [])
                self.assertEqual(result.unresolved_items, brief.unresolved_items)


if __name__ == "__main__":
    unittest.main()
