"""Offline P2-D scenarios: supplied context, arithmetic, and advisory quality."""
import os
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from contracts.ai_internal.case_copilot import BankCopilotSourceContext, CaseCopilotInput, CopilotMessage
from contracts.public_api.case_context_v2 import PublicCaseFactV2, PublicEvidenceRef
from ai_api.app.domains.case_support.copilot_accumulation import review_case_transfer_facts, review_transfers, money_values
from ai_api.app.domains.case_support.copilot_quality import CopilotQualityEvaluator
from ai_api.app.domains.case_support.bank_policy import bank_instructions
from ai_api.app.domains.case_support.copilot_service import (
    COPILOT_REPLY_SCHEMA, CaseCopilotService, _bank_case_fallback,
    _contains_internal_code, _prioritize_bank_items, normalize_recommended_actions,
)


RECORDS = ["고객: 의사 사칭한테 300만원 보냈어.", "고객: 검사 사칭한테 700만원 보냈어."]


class AccumulationTest(unittest.TestCase):
    def test_bank_chat_acknowledges_new_transfer_and_updates_recorded_total(self):
        now = datetime.now(timezone.utc)
        facts = []
        for fact_id, message_id, amount, source in (
            ("f1", "m1", 5_000_000, "CUSTOMER_STATEMENT"),
            ("f2", "m2", 2_000_000, "STAFF_OBSERVATION"),
        ):
            facts.append(PublicCaseFactV2(
                fact_id=fact_id, case_id="VP-CHAT", semantic_key="transfer.actual.amount",
                display_label="실제 이체 금액", value={"amount_krw": amount, "currency": "KRW", "direction": "OUT", "amount_scope": "EVENT"},
                display_value=f"{amount:,}원 송금", source_kind=source, status="PROPOSED",
                evidence_refs=[PublicEvidenceRef(type="MESSAGE", id=message_id)], version=1,
                created_at=now, updated_at=now,
            ))
        messages = [
            CopilotMessage(message_id="m1", case_id="VP-CHAT", actor_type="CUSTOMER", content="500만원 송금했다고 합니다"),
            CopilotMessage(message_id="m2", case_id="VP-CHAT", actor_type="BANK_STAFF", content="200만원 더 송금했다니까?"),
        ]
        source = BankCopilotSourceContext(facts=facts, messages=messages)
        result = _bank_case_fallback(CaseCopilotInput(
            case_id="VP-CHAT", prompt="200만원 더 송금했다니까?", source_context=source,
        ))
        self.assertIn("추가 송금 2,000,000원", result.content)
        self.assertIn("총 7,000,000원", result.content)
        self.assertIn("은행 거래내역으로 검증된 금액과는 구분", result.content)

    def test_separate_additional_transfer_reports_sum_and_repeated_followup_is_not_double_counted(self):
        facts = [
            {"fact_id": "f1", "semantic_key": "transfer.actual.amount", "status": "PROPOSED",
             "source_kind": "CUSTOMER_STATEMENT", "value": {"amount_krw": 5_000_000, "direction": "OUT", "amount_scope": "EVENT"},
             "evidence_refs": [{"type": "MESSAGE", "id": "m1"}]},
            {"fact_id": "f2", "semantic_key": "transfer.actual.amount", "status": "PROPOSED",
             "source_kind": "STAFF_OBSERVATION", "value": {"amount_krw": 2_000_000, "direction": "OUT", "amount_scope": "EVENT"},
             "evidence_refs": [{"type": "MESSAGE", "id": "m2"}]},
            {"fact_id": "f3", "semantic_key": "transfer.actual.amount", "status": "PROPOSED",
             "source_kind": "STAFF_OBSERVATION", "value": {"amount_krw": 2_000_000, "direction": "OUT", "amount_scope": "EVENT"},
             "evidence_refs": [{"type": "MESSAGE", "id": "m3"}]},
        ]
        messages = [
            {"message_id": "m1", "content": "고객이 500만원 송금했다고 말함"},
            {"message_id": "m2", "content": "200만원 더 송금했데!"},
            {"message_id": "m3", "content": "200만원 더 송금했다니까?"},
        ]
        result = review_case_transfer_facts(facts, messages)
        self.assertEqual(result.total_won, 7_000_000)
        self.assertEqual(len(result.items), 2)
        self.assertFalse(result.needs_review)

    def test_machine_checklist_ids_are_not_presented_as_chat_advice(self):
        readable = _prioritize_bank_items([
            "AI_CHECKLIST:P1:circumstance.demand: 추가 확인 사항에 대한 고객 답변 검토하세요. (REQUESTED)",
            "AI_CHECKLIST:P1:transfer_purpose: 송금 요구 이유 확인 필요 (REQUESTED)",
        ])
        self.assertTrue(any("상대방 요구:" in item for item in readable))
        self.assertTrue(any("송금 요구 이유:" in item for item in readable))
        self.assertFalse(any("AI_CHECKLIST" in item or "REQUESTED" in item for item in readable))
        self.assertTrue(_contains_internal_code("미완료 업무: AI_CHECKLIST:P1:circumstance.demand"))
        self.assertFalse(_contains_internal_code("우선 상대방 요구 내용을 확인해 주세요."))

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


class BankOneStepTest(unittest.TestCase):
    def test_brief_policy_and_schema_allow_three_relevant_actions(self):
        request = CaseCopilotInput(case_id="one-step", prompt="지금 뭘 해야 해?", response_style="BRIEF")
        instructions = bank_instructions(request)
        self.assertIn("**지금 할 일:**", instructions)
        self.assertIn("최대 세 개까지", instructions)
        self.assertEqual(COPILOT_REPLY_SCHEMA["properties"]["recommended_actions"]["maxItems"], 3)

    def test_recommendations_keep_up_to_three_distinct_valid_actions(self):
        raw = [
            {"action_key": "DRAFT_REPLY", "kind": "TOOL", "target_channel": "TEAM"},
            {"action_key": "CUSTOMER_QUESTION", "kind": "TOOL", "target_channel": "TEAM"},
            {"action_key": "OFFICIAL_VERIFICATION", "kind": "TOOL", "target_channel": "TEAM"},
        ]
        actions = normalize_recommended_actions(raw, "BANK_INTERNAL")
        self.assertEqual([action.action_key for action in actions], ["CUSTOMER_QUESTION", "OFFICIAL_VERIFICATION"])

    def test_brief_fallback_chooses_one_active_task_and_matching_tool(self):
        request = CaseCopilotInput(
            case_id="one-step", prompt="현재 사건 정리", response_style="BRIEF",
            case_summary="기관 사칭 신고가 접수됨",
            case_state={"tasks": [
                {"task_id": "routine", "title": "자료 정리", "task_type": "DOCUMENT_REVIEW", "priority": "NORMAL", "status": "TODO", "version": 1},
                {"task_id": "urgent", "title": "고객 노출 여부 질문", "task_type": "CUSTOMER_CONTACT", "priority": "URGENT", "status": "TODO", "version": 2},
            ]},
        )
        result = _bank_case_fallback(request)
        self.assertEqual(result.content.count("**지금 할 일:**"), 1)
        self.assertIn("고객 노출 여부 질문", result.content)
        self.assertNotIn("자료 정리", result.content)
        self.assertEqual(len(result.recommended_actions), 1)
        self.assertEqual(result.recommended_actions[0].action_key, "CUSTOMER_QUESTION")
        self.assertEqual(result.recommended_actions[0].target_id, "urgent")


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
        if mode == "BANK_INTERNAL":
            import json
            reply = json.dumps({"content": reply, "recommended_actions": [], "task_intents": []}, ensure_ascii=False)
        create = AsyncMock(return_value=SimpleNamespace(output_text=reply))
        provider_module = (
            "ai_api.app.domains.case_support.customer_support_service.AsyncOpenAI"
            if mode == "CUSTOMER_SUPPORT"
            else "ai_api.app.domains.case_support.copilot_service.AsyncOpenAI"
        )
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}), patch(
            provider_module,
            return_value=SimpleNamespace(responses=SimpleNamespace(create=create)),
        ):
            result = await CaseCopilotService().generate(CaseCopilotInput(
                case_id=f"direct-{self._testMethodName[:40]}-{mode}", prompt="총 얼마 사기당했어?",
                assistant_mode=mode, recent_conversation=history,
            ))
        self.assertEqual(create.await_count, 1)
        return result, create.await_args.kwargs

    async def test_bank_role_receives_case_turns_and_arithmetic_grounding(self):
        _, args = await self.call("BANK_INTERNAL", RECORDS)
        self.assertTrue(all(r in args["input"] for r in RECORDS))
        self.assertIn("10,000,000원", args["input"])
        for rule in ("직접 답변", "최신 정보 하나만", "중복 합산하지", "CONFIRMED", "PROPOSED", "번호 목록"):
            self.assertIn(rule, args["instructions"])
        self.assertIn("은행 직원의 내부 작업", args["instructions"])

    async def test_customer_receives_only_the_public_recent_conversation(self):
        _, args = await self.call("CUSTOMER_SUPPORT", [RECORDS[1]], "현재 상황을 알려 주세요.")
        self.assertNotIn("의사 사칭", args["input"])
        self.assertNotIn("10,000,000원", args["input"])
        self.assertIn(RECORDS[1], args["input"])
        self.assertIn("현재 질문에 먼저 직접 답하고", args["instructions"])

    async def test_customer_direct_reply_is_delivered_without_retry(self):
        reply = "은행에 문의하세요."
        result, _ = await self.call("CUSTOMER_SUPPORT", RECORDS, reply)
        self.assertEqual(result.content, reply)
