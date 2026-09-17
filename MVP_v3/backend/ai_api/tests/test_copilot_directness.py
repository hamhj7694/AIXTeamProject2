"""Offline P2-D scenarios: supplied context, arithmetic, and advisory quality."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from contracts.ai_internal.case_copilot import CaseCopilotInput
from ai_api.app.domains.case_support.copilot_accumulation import review_transfers, money_values
from ai_api.app.domains.case_support.copilot_quality import CopilotQualityEvaluator
from ai_api.app.domains.case_support.copilot_service import CaseCopilotService


RECORDS = ["고객: 의사 사칭한테 300만원 보냈어.", "고객: 검사 사칭한테 700만원 보냈어."]


class AccumulationTest(unittest.TestCase):
    def test_distinct_recipients_are_added_in_won(self):
        result = review_transfers(RECORDS)
        self.assertEqual(result.total_won, 10_000_000)
        self.assertEqual(len(result.items), 2)
        self.assertTrue(all(i.basis == "고객 진술·확인 필요" for i in result.items))

    def test_repeated_mentions_are_not_double_counted(self):
        result = review_transfers([*RECORDS, RECORDS[0], "질문 답변: 의사 사칭에게 3,000,000원 송금함"])
        self.assertEqual(result.total_won, 10_000_000)

    def test_mixed_statuses_are_retained(self):
        result = review_transfers([RECORDS[0] + " (CONFIRMED)", RECORDS[1] + " (PROPOSED)"])
        self.assertEqual([i.basis for i in result.items], ["담당자 확인", "고객 진술·확인 필요"])

    def test_removed_fact_is_not_added(self):
        result = review_transfers([RECORDS[0] + " (REJECTED)", RECORDS[1]])
        self.assertEqual(result.total_won, 7_000_000)

    def test_old_statement_cannot_resurrect_superseded_fact(self):
        result = review_transfers([*RECORDS, RECORDS[0] + " (SUPERSEDED)"])
        self.assertIsNone(result.total_won)

    def test_conflicting_or_corrected_or_unidentified_mentions_are_not_totalled(self):
        for extra in ("의사 사칭에게 500만원 송금함", "300만원이 아니라 700만원 보냈어", "300만원 보냈어"):
            with self.subTest(extra=extra):
                self.assertIsNone(review_transfers([*RECORDS, extra]).total_won)

    def test_missing_history_is_not_reconstructed(self):
        # A / Integration follow-up: this input cannot establish a missing first transfer.
        result = review_transfers([RECORDS[1]])
        self.assertEqual(result.total_won, 7_000_000)
        self.assertNotIn("의사", result.context_note())

    def test_non_money_numbers_are_not_amounts(self):
        self.assertEqual(money_values("9월 16일 3번 통화했고 전화는 010-1234-5678"), ())
        self.assertIsNone(review_transfers(["의사 사칭에게 3번 송금함"]).total_won)

    def test_complex_or_negative_amount_is_not_silently_totalled(self):
        for item in ("의사 사칭에게 1억 300만원 송금함", "의사 사칭에게 300만원 보내지 않았어"):
            with self.subTest(item=item):
                self.assertIsNone(review_transfers([item]).total_won)

    def test_unparsed_money_prevents_misleading_partial_total(self):
        result = review_transfers([*RECORDS, "경찰 사칭에게 오백만원 보냈어"])
        self.assertIsNone(result.total_won)

    def test_correction_without_amount_prevents_automatic_total(self):
        result = review_transfers([*RECORDS, "의사 사칭에게 보낸 게 아니야"])
        self.assertIsNone(result.total_won)

    def test_previous_ai_text_is_not_added_as_a_transfer(self):
        result = review_transfers([*RECORDS, "안전 상담 AI: 경찰 사칭에게 500만원 송금함"])
        self.assertEqual(result.total_won, 10_000_000)


class DirectnessEvaluationTest(unittest.TestCase):
    def evaluate(self, response, prompt="총 얼마 사기당했어?", records=RECORDS):
        return CopilotQualityEvaluator.evaluate(assistant_mode="CUSTOMER_SUPPORT", prompt=prompt, response=response, context=records)

    def test_referral_only_with_case_data_is_advisory_failure(self):
        result = self.evaluate("정확한 내용은 은행에 문의하세요.")
        self.assertIn("relevance", result.failed_criteria)
        self.assertFalse(CopilotQualityEvaluator.runtime_blocking_failures(result))

    def test_unknown_then_official_followup_is_allowed(self):
        result = self.evaluate("현재 정보로 확인할 수 없습니다. 공식 기관 확인이 필요합니다.", records=[])
        self.assertNotIn("relevance", result.failed_criteria)

    def test_unrequested_short_five_step_list_is_detected(self):
        reply = "1. 은행 문의\n2. 거래 내역 확인\n3. 경찰 신고\n4. 자료 보관\n5. 계좌 점검"
        result = self.evaluate(reply)
        self.assertIn("conciseness", result.failed_criteria)
        self.assertIn("relevance", result.failed_criteria)

    def test_requested_list_is_not_rejected_for_numbering(self):
        result = self.evaluate("1. 대화 자료 보관\n2. 거래 내역 확인\n3. 공식 번호 확인", "해야 할 일 3개 알려줘")
        self.assertNotIn("conciseness", result.failed_criteria)

    def test_generic_warning_is_not_an_answer_to_amount_question(self):
        result = self.evaluate("보이스피싱을 조심하세요. 은행은 항상 공식 번호를 이용하세요.")
        self.assertIn("relevance", result.failed_criteria)

    def test_latest_only_answer_misses_accumulated_information(self):
        result = self.evaluate("검사 사칭에게 700만원을 보냈다고 말씀하셨습니다.")
        self.assertIn("completeness", result.failed_criteria)
        self.assertFalse(CopilotQualityEvaluator.runtime_blocking_failures(result))

    def test_correct_total_or_full_breakdown_passes_completeness(self):
        for reply in ("고객 진술 기준 합계는 1,000만원입니다.", "의사 사칭 300만원, 검사 사칭 700만원을 말씀하셨습니다."):
            with self.subTest(reply=reply):
                self.assertNotIn("completeness", self.evaluate(reply).failed_criteria)


class DirectnessProviderTest(unittest.IsolatedAsyncioTestCase):
    async def call(self, mode, history, reply="고객 진술 기준 합계는 1,000만원입니다."):
        create = AsyncMock(return_value=SimpleNamespace(output_text=reply))
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}), patch(
            "ai_api.app.domains.case_support.copilot_service.AsyncOpenAI",
            return_value=SimpleNamespace(responses=SimpleNamespace(create=create)),
        ):
            result = await CaseCopilotService().generate(CaseCopilotInput(
                case_id=f"direct-{self._testMethodName[:40]}-{mode}", prompt="총 얼마 사기당했어?",
                assistant_mode=mode, recent_conversation=history,
                staff_context=["직원 메모: 고객 비공개"] if mode == "CUSTOMER_SUPPORT" else [],
            ))
        self.assertEqual(create.await_count, 1)
        return result, create.await_args.kwargs

    async def test_both_roles_receive_all_turns_and_arithmetic_with_grounding(self):
        for mode in ("CUSTOMER_SUPPORT", "BANK_INTERNAL"):
            with self.subTest(mode=mode):
                _, args = await self.call(mode, RECORDS)
                self.assertTrue(all(r in args["input"] for r in RECORDS))
                self.assertIn("10,000,000원", args["input"])
                self.assertNotIn("직원 메모: 고객 비공개", args["input"])
                for rule in ("직접 답변", "최신 정보 하나만", "중복 합산하지", "CONFIRMED", "PROPOSED", "번호 목록"):
                    self.assertIn(rule, args["instructions"])
                self.assertIn("쉽고 차분한 한국어" if mode == "CUSTOMER_SUPPORT" else "은행 직원의 내부 작업", args["instructions"])

    async def test_missing_history_stays_missing_in_provider_input(self):
        _, args = await self.call("CUSTOMER_SUPPORT", [RECORDS[1]], "현재 대화에는 700만원 송금 진술이 있습니다.")
        self.assertNotIn("의사 사칭", args["input"])
        self.assertNotIn("10,000,000원", args["input"])

    async def test_ux_failure_does_not_block_response_or_retry(self):
        reply = "은행에 문의하세요."
        result, _ = await self.call("CUSTOMER_SUPPORT", RECORDS, reply)
        self.assertEqual(result.content, reply)
