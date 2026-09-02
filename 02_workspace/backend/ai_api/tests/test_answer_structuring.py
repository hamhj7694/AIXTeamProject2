from __future__ import annotations

import unittest

from ai_api.app.domains.case_support.answer_service import CustomerAnswerStructuringService
from contracts.ai_internal.mvp_workflow import TargetField


class CustomerAnswerStructuringTest(unittest.TestCase):
    def setUp(self) -> None:
        self.service = CustomerAnswerStructuringService()

    def test_transfer_answers_are_structured(self) -> None:
        self.assertEqual(
            self.service.structure_answer(TargetField.TRANSFER_STATUS, "아직 송금 안 했어요").structured_value,
            "NOT_TRANSFERRED",
        )
        self.assertEqual(
            self.service.structure_answer(TargetField.TRANSFER_STATUS, "송금했어요").structured_value,
            "TRANSFERRED",
        )

    def test_personal_information_negative_answer_is_structured(self) -> None:
        result = self.service.structure_answer(TargetField.PERSONAL_INFORMATION_EXPOSURE, "개인정보는 제공 안 했어요")
        self.assertEqual(result.structured_value, "NOT_EXPOSED")
        self.assertFalse(result.unresolved)

    def test_ambiguous_answer_is_preserved_as_unresolved(self) -> None:
        raw_answer = "아마 아직 안 했던 것 같아요"
        result = self.service.structure_answer(TargetField.TRANSFER_STATUS, raw_answer)
        self.assertTrue(result.unresolved)
        self.assertIsNone(result.structured_value)
        self.assertEqual(result.raw_answer, raw_answer)
        self.assertGreaterEqual(result.confidence, 0)
        self.assertLessEqual(result.confidence, 1)

    def test_unsupported_field_uses_safe_fallback(self) -> None:
        result = self.service.structure_answer(TargetField.CLAIMED_ORGANIZATION, "검찰청이라고 했어요")
        self.assertTrue(result.unresolved)
        self.assertEqual(result.raw_answer, "검찰청이라고 했어요")
