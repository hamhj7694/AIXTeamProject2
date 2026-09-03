from __future__ import annotations

import unittest

from ai_api.app.domains.case_support.answer_service import CustomerAnswerStructuringService
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
                UnresolvedItem(target_field=TargetField.TRANSFER_STATUS, description="송금 여부 확인", priority=QuestionPriority.P0),
                UnresolvedItem(target_field=TargetField.PERSONAL_INFORMATION_EXPOSURE, description="개인정보 제공 확인", priority=QuestionPriority.P0),
            ],
        )

    def _fields(self, context: QuestionRecommendationContext | None = None) -> set[TargetField]:
        return {item.target_field for item in QuestionIntelligenceService().recommend_questions(self._brief(), context)}

    def test_confirmed_and_pending_fields_are_not_recommended(self) -> None:
        self.assertNotIn(TargetField.TRANSFER_STATUS, self._fields(QuestionRecommendationContext(
            confirmed_fields=[TargetField.TRANSFER_STATUS],
        )))
        self.assertNotIn(TargetField.PERSONAL_INFORMATION_EXPOSURE, self._fields(QuestionRecommendationContext(
            pending_question_fields=[TargetField.PERSONAL_INFORMATION_EXPOSURE],
        )))

    def test_answered_question_id_blocks_only_the_same_question(self) -> None:
        fields = self._fields(QuestionRecommendationContext(answered_question_ids=["q_transfer_status"]))
        self.assertNotIn(TargetField.TRANSFER_STATUS, fields)
        self.assertIn(TargetField.PERSONAL_INFORMATION_EXPOSURE, fields)

    def test_answer_received_is_not_fact_confirmed(self) -> None:
        answer = CustomerAnswerStructuringService().structure_answer(TargetField.TRANSFER_STATUS, "기억이 안 나요")
        self.assertTrue(answer.unresolved)
        # 답변 수신만으로 confirmed_fields가 되지는 않지만 같은 질문 ID는 반복하지 않는다.
        self.assertNotIn(TargetField.TRANSFER_STATUS, self._fields(QuestionRecommendationContext(
            answered_question_ids=["q_transfer_status"],
        )))


if __name__ == "__main__":
    unittest.main()
