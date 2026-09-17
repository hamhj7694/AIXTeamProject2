"""Fact status grounding regressions; provider replies are fixtures, not live AI."""

import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from contracts.ai_internal.case_copilot import CaseCopilotInput
from ai_api.app.domains.case_support.copilot_quality import CopilotQualityEvaluator
from ai_api.app.domains.case_support.copilot_service import CaseCopilotService, CaseCopilotProviderError


class FactGroundingTest(unittest.TestCase):
    def check(self, facts, reply, mode="BANK_INTERNAL"):
        return CopilotQualityEvaluator.evaluate(
            assistant_mode=mode, prompt="송금 여부를 알려 주세요", response=reply, context=facts,
        )

    def test_proposed_does_not_support_certainty_but_allows_uncertainty(self):
        facts = ["transfer.actual.status: TRANSFERRED (PROPOSED)"]
        self.assertIn("unsupported_certainty", self.check(facts, "송금한 것이 확인되었습니다.").failed_criteria)
        self.assertNotIn("unsupported_certainty", self.check(facts, "고객 진술상 송금했으며 추가 확인이 필요합니다.").failed_criteria)

    def test_confirmed_supports_fact_but_not_official_verification(self):
        facts = ["transfer.actual.status: TRANSFERRED (CONFIRMED)"]
        self.assertNotIn("unsupported_certainty", self.check(facts, "송금한 것이 확인되었습니다.").failed_criteria)
        self.assertIn("unsupported_certainty", self.check(facts, "송금한 것이 공식 검증되었습니다.").failed_criteria)

    def test_localized_v2_status_is_supported(self):
        for status, fails in [("확인 전 진술", True), ("담당자 확인", False)]:
            with self.subTest(status=status):
                result = self.check([f"사실: 송금 여부: 송금함 ({status})"], "송금한 것이 확인되었습니다.")
                self.assertEqual("unsupported_certainty" in result.failed_criteria, fails)

    def test_unrelated_confirmed_fact_cannot_confirm_transfer(self):
        facts = ["transfer_status: TRANSFERRED (PROPOSED)", "연락처: 010 (CONFIRMED)"]
        self.assertIn("unsupported_certainty", self.check(facts, "송금한 것이 확인되었습니다.").failed_criteria)

    def test_conflicting_proposals_never_confirm_either_value(self):
        facts = [f"transfer.actual.status: {value} (PROPOSED)" for value in ("TRANSFERRED", "NOT_TRANSFERRED")]
        for reply in ("송금한 것이 확인되었습니다.", "송금하지 않은 것이 맞습니다.", "송금 여부가 확실합니다."):
            with self.subTest(reply=reply):
                self.assertIn("unsupported_certainty", self.check(facts, reply).failed_criteria)

    def test_confirmed_negative_is_not_evidence_for_positive_proposal(self):
        facts = ["transfer_status: TRANSFERRED (PROPOSED)", "transfer_status: NOT_TRANSFERRED (CONFIRMED)"]
        self.assertIn("unsupported_certainty", self.check(facts, "송금한 것이 확인되었습니다.").failed_criteria)
        self.assertNotIn("unsupported_certainty", self.check(facts, "송금하지 않은 것이 확인되었습니다.").failed_criteria)

    def test_rejected_and_superseded_do_not_support_certainty(self):
        for status in ("REJECTED", "SUPERSEDED"):
            with self.subTest(status=status):
                self.assertIn("unsupported_certainty", self.check(
                    [f"송금함 ({status})"], "송금한 것이 확인되었습니다.",
                ).failed_criteria)

    def test_conflicting_confirmed_records_are_not_resolved_by_order(self):
        facts = ["transfer_status: TRANSFERRED (CONFIRMED)", "transfer_status: NOT_TRANSFERRED (CONFIRMED)"]
        for ordered in (facts, list(reversed(facts))):
            with self.subTest(facts=ordered):
                self.assertIn("unsupported_certainty", self.check(ordered, "송금한 것이 확인되었습니다.").failed_criteria)

    def test_confirmed_transfer_does_not_confirm_entire_case(self):
        self.assertIn("unsupported_certainty", self.check(
            ["transfer_status: TRANSFERRED (CONFIRMED)"], "무조건 보이스피싱입니다.",
        ).failed_criteria)

    def test_customer_status_enum_is_not_public_reply_text(self):
        result = self.check([], "송금 상태는 PROPOSED입니다.", "CUSTOMER_SUPPORT")
        self.assertIn("internal_visibility", result.failed_criteria)

    def test_each_assertion_needs_its_own_evidence(self):
        result = self.check(["연락처: 번호 일치 (CONFIRMED)"], "연락처는 확인되었습니다. 송금한 것이 확인되었습니다.")
        self.assertIn("unsupported_certainty", result.failed_criteria)


class FactGroundingProviderTest(unittest.IsolatedAsyncioTestCase):
    async def generate(self, mode, facts, reply, **kwargs):
        create = AsyncMock(return_value=SimpleNamespace(output_text=reply))
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}), patch(
            "ai_api.app.domains.case_support.copilot_service.AsyncOpenAI",
            return_value=SimpleNamespace(responses=SimpleNamespace(create=create)),
        ):
            result = await CaseCopilotService().generate(CaseCopilotInput(
                case_id=f"grounding-{self._testMethodName}-{mode}", prompt="송금 여부를 설명해 주세요",
                assistant_mode=mode, known_facts=facts, **kwargs,
            ))
        return result, create.await_args.kwargs

    async def test_modes_preserve_status_and_conflict_prompt(self):
        facts = ["송금함 (PROPOSED)", "송금하지 않음 (CONFIRMED)"]
        for mode in ("CUSTOMER_SUPPORT", "BANK_INTERNAL"):
            with self.subTest(mode=mode):
                result, args = await self.generate(mode, facts, "송금 여부는 추가 확인이 필요합니다.")
                self.assertTrue(all(fact in args["input"] for fact in facts))
                for rule in ("PROPOSED", "CONFIRMED", "값이 충돌", "완료된 Verification", "상태 없는 고객 답변"):
                    self.assertIn(rule, args["instructions"])
                self.assertNotIn("PROPOSED", result.content)
                if mode == "CUSTOMER_SUPPORT":
                    self.assertIn("그대로 출력하지 마세요", args["instructions"])

    async def test_customer_proposed_reply_is_rejected(self):
        with self.assertRaises(CaseCopilotProviderError):
            await self.generate("CUSTOMER_SUPPORT", ["송금함 (PROPOSED)"], "송금한 것이 확인되었습니다.")

    async def test_confirmed_bank_reply_is_delivered(self):
        result, _ = await self.generate("BANK_INTERNAL", ["송금함 (CONFIRMED)"], "송금한 것이 확인되었습니다.")
        self.assertEqual(result.content, "송금한 것이 확인되었습니다.")

    async def test_previous_ai_reply_cannot_authorize_certainty(self):
        with self.assertRaises(CaseCopilotProviderError):
            await self.generate(
                "CUSTOMER_SUPPORT", ["질문: 송금 여부 / 고객 답변: 송금했어요"],
                "송금한 것이 확인되었습니다.", recent_conversation=["이전 AI: 송금함 (CONFIRMED)"],
            )
