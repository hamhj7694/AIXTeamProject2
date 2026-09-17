from __future__ import annotations

import unittest

from contracts.ai_internal.context_fact_extraction import ContextFactProposal

from ai_api.app.domains.case_support.verification_policy import (
    VerificationRecommendation,
    VerificationResult,
    VerificationSemanticMapper,
    VerificationSubject,
)


def result(**updates) -> VerificationResult:
    value = {
        "verification_task_id": "verification-1",
        "version": 2,
        "claim": "공식 기관의 연락인지 확인",
        "target": "서울중앙지검 소속 여부",
        "status": "COMPLETED",
        "result_summary": "공식 기관 소속이 아닌 것으로 확인됨",
    }
    value.update(updates)
    return VerificationResult.model_validate(value)


class VerificationPolicyTest(unittest.TestCase):
    def test_organization_result_maps_to_existing_organization_key(self) -> None:
        proposal = VerificationSemanticMapper.map_result(result())

        self.assertIsNotNone(proposal)
        self.assertEqual(proposal.semantic_key, "offender.claimed_organization")
        self.assertEqual(proposal.value["name"], "서울중앙지검 소속 여부")
        self.assertIn("verification_result", proposal.value)

    def test_contact_result_maps_to_existing_contact_key(self) -> None:
        proposal = VerificationSemanticMapper.map_result(result(
            target="발신 전화번호 확인",
            subject=VerificationSubject.CONTACT,
        ))

        self.assertIsNotNone(proposal)
        self.assertEqual(proposal.semantic_key, "offender.contact")
        self.assertEqual(proposal.value["value"], "발신 전화번호 확인")

    def test_non_organization_result_is_not_forced_into_organization_key(self) -> None:
        proposal = VerificationSemanticMapper.map_result(result(
            target="계좌 지급정지 처리 여부",
            result_summary="접수 여부를 확인함",
        ))

        self.assertIsNone(proposal)

    def test_unmapped_completed_result_does_not_create_a_generic_fact(self) -> None:
        proposal = VerificationSemanticMapper.map_result(result(
            target="기타 확인 항목",
            result_summary="확인 완료",
        ))

        self.assertIsNone(proposal)

    def test_incomplete_result_does_not_create_a_fact(self) -> None:
        self.assertIsNone(VerificationSemanticMapper.map_result(result(
            status="IN_PROGRESS", result_summary=None,
        )))

    def test_recommendation_and_result_have_distinct_models(self) -> None:
        recommendation = VerificationRecommendation(
            claim="기관 소속 여부 확인",
            target="서울중앙지검",
            rationale="상대방의 소속 주장을 공식 채널에서 확인해야 합니다.",
        )

        self.assertEqual(recommendation.kind, "RECOMMENDATION")
        self.assertEqual(result().kind, "RESULT")

    def test_mapped_value_matches_existing_semantic_fact_contract(self) -> None:
        for subject in (VerificationSubject.ORGANIZATION, VerificationSubject.CONTACT):
            proposal = VerificationSemanticMapper.map_result(result(subject=subject))

            ContextFactProposal(
                semantic_key=proposal.semantic_key,
                display_label=proposal.display_label,
                value=proposal.value,
                display_value=proposal.display_value,
                confidence=proposal.confidence,
                evidence_message_id="verification-result",
            )


if __name__ == "__main__":
    unittest.main()
