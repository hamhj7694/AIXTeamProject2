from __future__ import annotations

import unittest

from pydantic import ValidationError

from ai_api.app.domains.case_support.answer_service import CustomerAnswerStructuringService
from ai_api.app.domains.case_support.brief_update_service import BriefUpdateService
from ai_api.app.domains.case_support.question_service import QuestionIntelligenceService
from contracts.ai_internal.mvp_workflow import (
    CaseBrief,
    QuestionPriority,
    QuestionRecommendationContext,
    TargetField,
    UnresolvedItem,
)
from contracts.diagnosis import RiskLevel


class QuestionRecommendationContextTest(unittest.TestCase):
    @staticmethod
    def _brief() -> CaseBrief:
        return CaseBrief(
            summary="사건 확인이 필요합니다.",
            incident_type="사칭 의심",
            risk_level=RiskLevel.HIGH,
            risk_score=90,
            unresolved_items=[
                UnresolvedItem(target_field=TargetField.TRANSFER_STATUS, description="실제 송금 여부 확인 필요", priority=QuestionPriority.P0),
                UnresolvedItem(target_field=TargetField.PERSONAL_INFORMATION_EXPOSURE, description="개인정보 제공 여부 확인 필요", priority=QuestionPriority.P0),
                UnresolvedItem(target_field=TargetField.AUTHENTICATION_INFORMATION_EXPOSURE, description="인증정보 제공 여부 확인 필요", priority=QuestionPriority.P0),
                UnresolvedItem(target_field=TargetField.CLAIMED_ORGANIZATION, description="기관 소속 확인 필요", priority=QuestionPriority.P1),
            ],
        )

    def _fields(self, context: QuestionRecommendationContext | None = None) -> set[TargetField]:
        return {
            item.target_field
            for item in QuestionIntelligenceService().recommend_questions(self._brief(), context)
        }

    def test_unconfirmed_fields_are_recommended(self) -> None:
        self.assertIn(TargetField.TRANSFER_STATUS, self._fields())

    def test_confirmed_field_is_not_recommended(self) -> None:
        fields = self._fields(QuestionRecommendationContext(
            confirmed_fields=[TargetField.PERSONAL_INFORMATION_EXPOSURE],
        ))
        self.assertNotIn(TargetField.PERSONAL_INFORMATION_EXPOSURE, fields)

    def test_pending_field_is_not_recommended(self) -> None:
        fields = self._fields(QuestionRecommendationContext(
            pending_question_fields=[TargetField.TRANSFER_STATUS],
        ))
        self.assertNotIn(TargetField.TRANSFER_STATUS, fields)

    def test_explicit_answer_can_be_marked_confirmed_and_excluded(self) -> None:
        answer = CustomerAnswerStructuringService().structure_answer(
            TargetField.TRANSFER_STATUS, "송금했어요",
        )
        fields = self._fields(QuestionRecommendationContext(
            confirmed_fields=[TargetField.TRANSFER_STATUS],
        ))

        self.assertFalse(answer.unresolved)
        self.assertEqual(answer.structured_value, "TRANSFERRED")
        self.assertNotIn(TargetField.TRANSFER_STATUS, fields)

    def test_answered_question_id_blocks_only_the_same_question_text(self) -> None:
        fields = self._fields(QuestionRecommendationContext(
            answered_question_ids=["q_claimed_organization", "q_claimed_organization"],
        ))
        self.assertNotIn(TargetField.CLAIMED_ORGANIZATION, fields)

    def test_ambiguous_answer_keeps_target_unresolved_without_confirming_it(self) -> None:
        brief = self._brief()
        answer = CustomerAnswerStructuringService().structure_answer(
            TargetField.TRANSFER_STATUS, "기억이 안 나요",
        )
        update = BriefUpdateService().update(brief, answer)
        context = QuestionRecommendationContext(
            answered_question_ids=["q_transfer_status"],
        )

        self.assertTrue(answer.unresolved)
        self.assertIsNone(answer.structured_value)
        self.assertIn(TargetField.TRANSFER_STATUS, {
            item.target_field for item in update.unresolved_items
        })
        self.assertNotIn(TargetField.TRANSFER_STATUS, context.excluded_target_fields())
        # 현재 MVP에는 후속 질문 문구가 없으므로 같은 문장만 반복하지 않는다.
        self.assertNotIn(TargetField.TRANSFER_STATUS, self._fields(context))

    def test_transfer_request_does_not_remove_unconfirmed_transfer_status_question(self) -> None:
        self.assertIn(TargetField.TRANSFER_STATUS, self._fields())

    def test_context_rejects_frontend_state(self) -> None:
        with self.assertRaises(ValidationError):
            QuestionRecommendationContext.model_validate({"selected": True})


if __name__ == "__main__":
    unittest.main()
