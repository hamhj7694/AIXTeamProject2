from __future__ import annotations

import unittest

from ai_api.app.domains.case_support.question_service import QuestionIntelligenceService
from contracts.ai_internal.mvp_workflow import CaseBrief, QuestionPriority, TargetField, UnresolvedItem
from contracts.diagnosis import Evidence, RiskLevel


class QuestionIntelligenceTest(unittest.TestCase):
    def _brief(self, unresolved_items: list[UnresolvedItem]) -> CaseBrief:
        return CaseBrief(
            summary="미확인 정보가 있습니다.", incident_type="미확인", risk_level=RiskLevel.HIGH, risk_score=90,
            risk_evidence=[Evidence(turn=1, event_family="MONEY_MOVEMENT", subtype="TRANSFER", text="송금을 요구함")],
            unresolved_items=unresolved_items,
        )

    def test_p0_questions_are_prioritized_and_validate_contract(self) -> None:
        brief = self._brief([
            UnresolvedItem(target_field=TargetField.TRANSFER_PURPOSE, description="목적 미확인", priority=QuestionPriority.P1),
            UnresolvedItem(target_field=TargetField.TRANSFER_STATUS, description="송금 여부 미확인", priority=QuestionPriority.P1),
            UnresolvedItem(target_field=TargetField.PERSONAL_INFORMATION_EXPOSURE, description="개인정보 여부 미확인", priority=QuestionPriority.P0),
        ])
        result = QuestionIntelligenceService().recommend_questions(brief)
        self.assertEqual([item.priority for item in result], [QuestionPriority.P0, QuestionPriority.P0, QuestionPriority.P1])
        self.assertEqual(result[0].execution_mode.value, "HUMAN_REVIEW_REQUIRED")
        self.assertTrue(result[1].evidence_refs)

    def test_only_unresolved_fields_are_used_and_duplicates_are_removed(self) -> None:
        brief = self._brief([
            UnresolvedItem(target_field=TargetField.TRANSFER_STATUS, description="송금 여부 미확인", priority=QuestionPriority.P0),
            UnresolvedItem(target_field=TargetField.TRANSFER_STATUS, description="중복", priority=QuestionPriority.P0),
        ])
        result = QuestionIntelligenceService().recommend_questions(brief)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].target_field, TargetField.TRANSFER_STATUS)
        self.assertFalse(any(item.target_field is TargetField.AUTHENTICATION_INFORMATION_EXPOSURE for item in result))
