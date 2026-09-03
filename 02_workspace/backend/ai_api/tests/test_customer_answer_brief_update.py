from __future__ import annotations

import json
import unittest
from pathlib import Path

from ai_api.app.domains.case_support import MvpWorkflowService
from ai_api.app.domains.case_support.answer_service import CustomerAnswerStructuringService
from contracts.ai_internal.mvp_workflow import CustomerAnswerBriefUpdateResult, TargetField
from contracts.diagnosis import DiagnosisResult


class CustomerAnswerBriefUpdateTest(unittest.TestCase):
    @staticmethod
    def _brief_and_transfer_question():
        fixture = (
            Path(__file__).resolve().parents[2]
            / "contracts"
            / "ai_internal"
            / "fixtures"
            / "diagnosis.high.v1.json"
        )
        diagnosis = DiagnosisResult.model_validate(
            json.loads(fixture.read_text(encoding="utf-8"))["response"]
        )
        workflow = MvpWorkflowService()
        brief = workflow.build_brief(diagnosis)
        question = next(
            item
            for item in workflow.recommend_questions(brief)
            if item.target_field is TargetField.TRANSFER_STATUS
        )
        return workflow, brief, question

    def test_explicit_answer_is_structured_and_updates_the_brief(self) -> None:
        workflow, brief, question = self._brief_and_transfer_question()

        result = workflow.process_customer_answer(
            brief,
            question,
            "\uc1a1\uae08\ud55c \uc801 \uc5c6\uc5b4\uc694.",
            source_reference="message-123",
        )

        self.assertEqual(result.structured_answer.structured_value, "NOT_TRANSFERRED")
        self.assertEqual(result.brief_update.resolved_items[0].target_field, TargetField.TRANSFER_STATUS)
        self.assertEqual(result.unresolved_items, result.brief_update.unresolved_items)
        self.assertEqual(result.warnings, [])
        self.assertEqual(result.source_reference, "message-123")
        self.assertEqual(CustomerAnswerBriefUpdateResult.model_validate(result.model_dump()), result)

    def test_ambiguous_answer_preserves_unresolved_items_and_warnings(self) -> None:
        workflow, brief, question = self._brief_and_transfer_question()

        result = workflow.process_customer_answer(brief, question, "\uc798 \ubaa8\ub974\uaca0\uc5b4\uc694.")

        self.assertTrue(result.structured_answer.unresolved)
        self.assertEqual(result.brief_update.resolved_items, [])
        self.assertEqual(result.unresolved_items, brief.unresolved_items)
        self.assertTrue(result.warnings)

    def test_explicit_non_transfer_variants_are_structured(self) -> None:
        workflow, brief, question = self._brief_and_transfer_question()

        for answer_text in (
            "\uc1a1\uae08\ud55c \uc801 \uc5c6\uc5b4\uc694.",
            "\uc1a1\uae08\ud558\uc9c0 \uc54a\uc558\uc5b4\uc694.",
            "\uc544\ub2c8\uc694, \ubcf4\ub0b4\uc9c0 \uc54a\uc558\uc2b5\ub2c8\ub2e4.",
        ):
            with self.subTest(answer_text=answer_text):
                result = workflow.process_customer_answer(brief, question, answer_text)
                self.assertEqual(result.structured_answer.structured_value, "NOT_TRANSFERRED")
                self.assertFalse(result.structured_answer.unresolved)

    def test_ambiguous_or_request_only_transfer_answers_remain_unresolved(self) -> None:
        workflow, brief, question = self._brief_and_transfer_question()

        for answer_text in (
            "\uae30\uc5b5\uc774 \uc548 \ub098\uc694.",
            "\uc1a1\uae08\ud588\uc744 \uc218\ub3c4 \uc788\uc5b4\uc694.",
            "\uc0c1\ub300\ubc29\uc774 \uc1a1\uae08\ud558\ub77c\uace0 \ud588\uc5b4\uc694.",
        ):
            with self.subTest(answer_text=answer_text):
                result = workflow.process_customer_answer(brief, question, answer_text)
                self.assertTrue(result.structured_answer.unresolved)
                self.assertIsNone(result.structured_answer.structured_value)

    def test_stale_question_answer_is_not_promoted_to_a_fact(self) -> None:
        workflow, brief, question = self._brief_and_transfer_question()
        current_brief = brief.model_copy(
            update={
                "unresolved_items": [
                    item
                    for item in brief.unresolved_items
                    if item.target_field is not TargetField.TRANSFER_STATUS
                ]
            }
        )

        result = workflow.process_customer_answer(current_brief, question, "\uc1a1\uae08\ud588\uc5b4\uc694.")

        self.assertFalse(result.structured_answer.unresolved)
        self.assertEqual(result.brief_update.resolved_items, [])
        self.assertIn("Selected question target is not unresolved", result.warnings[0])

    def test_information_request_is_not_mistaken_for_actual_exposure(self) -> None:
        service = CustomerAnswerStructuringService()
        result = service.structure_answer(
            TargetField.PERSONAL_INFORMATION_EXPOSURE,
            "\uac1c\uc778\uc815\ubcf4\ub97c \uc81c\uacf5\ud558\ub77c\uace0 \uc694\uccad\ud588\uc5b4\uc694.",
        )

        self.assertTrue(result.unresolved)
        self.assertIsNone(result.structured_value)

    def test_explicit_non_exposure_is_preserved_when_a_request_is_mentioned(self) -> None:
        service = CustomerAnswerStructuringService()
        result = service.structure_answer(
            TargetField.PERSONAL_INFORMATION_EXPOSURE,
            "\uac1c\uc778\uc815\ubcf4\ub97c \uc81c\uacf5\ud558\ub77c\uace0 \ud588\uc9c0\ub9cc \uc81c\uacf5 \uc548 \ud588\uc5b4\uc694.",
        )

        self.assertFalse(result.unresolved)
        self.assertEqual(result.structured_value, "NOT_EXPOSED")


if __name__ == "__main__":
    unittest.main()
