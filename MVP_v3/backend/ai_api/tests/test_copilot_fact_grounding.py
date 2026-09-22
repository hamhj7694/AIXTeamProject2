"""Fact status grounding regressions; provider replies are fixtures, not live AI."""

import os
import unittest
from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from contracts.ai_internal.case_copilot import CaseCopilotInput, BankCopilotSourceContext
from contracts.public_api.case_context_v2 import PublicCaseFactV2
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
                case_id=f"grounding-{sha256(self._testMethodName.encode()).hexdigest()[:12]}-{mode}",
                prompt="송금 여부를 설명해 주세요",
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

    async def test_customer_proposed_reply_is_replaced_with_safe_explanation(self):
        result, _ = await self.generate("CUSTOMER_SUPPORT", ["송금함 (PROPOSED)"], "송금한 것이 확인되었습니다.")
        self.assertIn("확정하기 어렵습니다", result.content)
        self.assertNotIn("송금한 것이 확인되었습니다", result.content)

    async def test_confirmed_bank_reply_is_delivered(self):
        result, _ = await self.generate("BANK_INTERNAL", ["송금함 (CONFIRMED)"], "송금한 것이 확인되었습니다.")
        self.assertEqual(result.content, "송금한 것이 확인되었습니다.")

    async def test_previous_ai_reply_cannot_authorize_certainty(self):
        result, _ = await self.generate(
            "CUSTOMER_SUPPORT", ["질문: 송금 여부 / 고객 답변: 송금했어요"],
            "송금한 것이 확인되었습니다.", recent_conversation=["이전 AI: 송금함 (CONFIRMED)"],
        )
        self.assertIn("확정하기 어렵습니다", result.content)


def source_fact(source="CUSTOMER_STATEMENT", status="PROPOSED", **updates):
    data = dict(fact_id="f-transfer", case_id="SOURCE-CASE", semantic_key="transfer.actual.status",
        display_label="송금", value={"status": "TRANSFERRED", "amount_krw": 10_000_000},
        display_value="1,000만원 송금함", source_kind=source, status=status, version=1,
        created_at="2026-09-18T01:00:00Z", updated_at="2026-09-18T01:00:00Z")
    if status == "CONFIRMED":
        data.update(confirmed_by="staff", confirmed_at="2026-09-18T02:00:00Z")
    if status == "SUPERSEDED":
        data["supersedes_fact_id"] = "f-current"
    data.update(updates)
    return PublicCaseFactV2.model_validate(data)


class SourceAwareGroundingTest(unittest.TestCase):
    def check(self, response, facts=(), verifications=(), **extra):
        return CopilotQualityEvaluator.evaluate(assistant_mode="BANK_INTERNAL", prompt="송금 근거는 무엇인가요?",
            response=response, grounding_context=["송금함 (CONFIRMED) 공식 확인 결과"],
            source_context=BankCopilotSourceContext(facts=list(facts), verifications=list(verifications), **extra))

    def test_customer_statement_is_attributed_and_objective_claim_blocked(self):
        fact = source_fact()
        good = "고객은 1,000만원을 송금했다고 진술했습니다. 현재 전달된 거래 Evidence만으로 실제 이체 완료 여부는 확인되지 않았습니다."
        self.assertNotIn("unsupported_certainty", self.check(good, [fact]).failed_criteria)
        for bad in ("고객이 1,000만원을 송금했습니다.", "고객이 1,000만원을 보냈습니다.",
                    "고객 진술로 1,000만원 송금한 사실이 확정되었습니다."):
            with self.subTest(reply=bad):
                self.assertIn("unsupported_certainty", self.check(bad, [fact]).failed_criteria)

    def test_unsupported_certainty_exposes_rule_without_changing_result(self):
        fact = source_fact(
            semantic_key="device.remote_control_app",
            display_label="원격제어 앱",
            value={"installed": True},
            display_value="원격제어 앱 설치 요구",
        )
        result = self.check("원격제어 앱 설치 요구가 확인되었습니다.", [fact])
        self.assertIn("unsupported_certainty", result.failed_criteria)
        check = next(item for item in result.checks if item.criterion == "unsupported_certainty")
        self.assertEqual(check.rule, "unattributed_certainty_without_confirmed_source")

    def test_negative_confirmation_state_is_not_mistaken_for_certainty(self):
        fact = source_fact()
        safe = (
            "고객은 1,000만원을 송금했다고 진술했습니다. "
            "하지만 이 내용은 아직 확인된 상태가 아닙니다."
        )
        self.assertNotIn("unsupported_certainty", self.check(safe, [fact]).failed_criteria)

        unsafe = (
            "고객이 1,000만원을 송금했습니다.",
            "1,000만원을 송금한 것이 확인되었습니다.",
            "송금 영수증이 제출되어 있습니다.",
        )
        for reply in unsafe:
            with self.subTest(reply=reply):
                self.assertIn("unsupported_certainty", self.check(reply, [fact]).failed_criteria)

    def test_bank_record_allows_only_its_own_value(self):
        reply = "은행 거래기록에서 1,000만원 이체 내역이 확인됩니다."
        self.assertNotIn("unsupported_certainty", self.check(reply, [source_fact("BANK_RECORD", "CONFIRMED")]).failed_criteria)
        for fact in (source_fact(), source_fact("BANK_RECORD"), source_fact("STAFF_OBSERVATION", "CONFIRMED")):
            with self.subTest(source=fact.source_kind, status=fact.status):
                self.assertIn("unsupported_certainty", self.check(reply, [fact]).failed_criteria)
        self.assertIn("unsupported_certainty", self.check(reply.replace("1,000", "2,000"), [source_fact("BANK_RECORD", "CONFIRMED")]).failed_criteria)

    def test_confirmed_customer_source_stays_customer_and_staff_confirmation_is_separate(self):
        fact = source_fact(status="CONFIRMED")
        self.assertIn("unsupported_certainty", self.check("은행 거래기록에서 1,000만원 이체 내역이 확인됩니다.", [fact]).failed_criteria)
        self.assertIn("unsupported_certainty", self.check("고객이 1,000만원을 송금했습니다.", [fact]).failed_criteria)
        self.assertNotIn("unsupported_certainty", self.check("고객은 1,000만원을 송금했다고 진술했습니다. 담당자가 이 송금 내용을 확인했습니다.", [fact]).failed_criteria)
        self.assertIn("unsupported_certainty", self.check("담당자가 이 송금 내용을 확인했습니다.", [source_fact()]).failed_criteria)

    def test_reference_alone_never_authorizes_verification(self):
        fact = source_fact(evidence_refs=[{"type": "BANK_TRANSACTION", "id": "transaction"}])
        self.assertIn("unsupported_certainty", self.check("1,000만원 송금한 것이 공식 검증되었습니다.", [fact]).failed_criteria)

    def test_only_completed_linked_revision_authorizes_its_claim(self):
        fact = source_fact(evidence_refs=[{"type": "VERIFICATION_RESULT", "id": "verification", "revision": 2}])
        base = dict(verification_task_id="verification", case_id="SOURCE-CASE", target="송금 거래",
                    claim="1,000만원 송금 여부", result_summary="1,000만원 송금한 기록 확인", version=2)
        reply = "1,000만원 송금한 것이 공식 검증되었습니다."
        self.assertNotIn("unsupported_certainty", self.check(reply, [fact], [dict(base, status="COMPLETED")]).failed_criteria)
        for changes in (dict(status="PENDING"), dict(status="FAILED"), dict(status="COMPLETED", result_summary=""),
                        dict(status="COMPLETED", version=1), dict(status="COMPLETED", verification_task_id="unrelated")):
            with self.subTest(changes=changes):
                self.assertIn("unsupported_certainty", self.check(reply, [fact], [dict(base, **changes)]).failed_criteria)

    def test_unrelated_completed_result_does_not_verify_transfer(self):
        fact = source_fact(semantic_key="offender.claimed_organization", display_value="검찰청 주장",
            value={"text": "검찰청"}, evidence_refs=[{"type": "VERIFICATION_RESULT", "id": "v-org"}])
        check = dict(verification_task_id="v-org", case_id="SOURCE-CASE", target="검찰청 기관",
            claim="기관 실재 여부", status="COMPLETED", result_summary="기관 실재 확인")
        self.assertIn("unsupported_certainty", self.check("1,000만원 송금한 것이 공식 검증되었습니다.", [fact], [check]).failed_criteria)

    def test_rejected_and_superseded_current_grounding_excluded(self):
        for status, updates in (("REJECTED", {"rejection_reason": "근거 불일치"}), ("SUPERSEDED", {})):
            with self.subTest(status=status):
                fact = source_fact("BANK_RECORD", status, **updates)
                self.assertIn("unsupported_certainty", self.check("은행 거래기록에서 1,000만원 이체 내역이 확인됩니다.", [fact]).failed_criteria)

    def test_superseded_reference_blocks_old_customer_message_as_current_basis(self):
        fact = source_fact(status="SUPERSEDED", evidence_refs=[{"type": "MESSAGE", "id": "old"}])
        old = dict(message_id="old", case_id="SOURCE-CASE", actor_type="CUSTOMER", content="1,000만원 송금했어요")
        self.assertIn("unsupported_certainty", self.check("고객은 1,000만원 송금했다고 진술했습니다.", [fact], messages=[old]).failed_criteria)

    def test_absent_evidence_does_not_mean_no_transfer_and_ai_text_is_not_evidence(self):
        self.assertNotIn("unsupported_certainty", self.check("현재 전달된 거래 Evidence만으로 실제 이체 완료 여부는 확인되지 않았습니다.").failed_criteria)
        for reply in ("현재 은행 거래기록은 없습니다.", "고객이 송금한 사실은 아직 확인되지 않았습니다.",
                      "고객이 송금한 것이 공식 검증되지 않았습니다."):
            with self.subTest(reply=reply):
                self.assertNotIn("unsupported_certainty", self.check(reply).failed_criteria)
        self.assertIn("unsupported_certainty", self.check("거래 Evidence가 없으므로 고객은 송금하지 않았습니다.").failed_criteria)
        ai = dict(message_id="ai", case_id="SOURCE-CASE", actor_type="BANK_AGENT", content="1,000만원 송금함 (CONFIRMED)")
        self.assertIn("unsupported_certainty", self.check("1,000만원 송금한 것이 확인되었습니다.", messages=[ai]).failed_criteria)

    def test_receipt_not_supplied_is_not_invented(self):
        self.assertIn("unsupported_certainty", self.check("송금 영수증이 제출되어 있습니다.", [source_fact()]).failed_criteria)

    def test_conflicting_values_are_not_selected_by_timestamp(self):
        positive = source_fact("BANK_RECORD", "CONFIRMED")
        negative = source_fact("BANK_RECORD", "CONFIRMED", fact_id="f-negative",
                              value={"status": "NOT_TRANSFERRED"}, display_value="송금하지 않음", updated_at="2026-09-18T05:00:00Z")
        for facts in ([positive, negative], [negative, positive]):
            with self.subTest(order=[f.fact_id for f in facts]):
                self.assertIn("unsupported_certainty", self.check("송금한 것이 확인되었습니다.", facts).failed_criteria)
        conflicting_string = CopilotQualityEvaluator.evaluate(assistant_mode="BANK_INTERNAL", prompt="송금 근거",
            response="은행 거래기록에서 1,000만원 이체 내역이 확인됩니다.",
            grounding_context=["transfer_status: NOT_TRANSFERRED (CONFIRMED)"],
            source_context=BankCopilotSourceContext(facts=[positive]))
        self.assertIn("unsupported_certainty", conflicting_string.failed_criteria)

    def test_bank_only_context_and_case_boundaries(self):
        context = BankCopilotSourceContext(facts=[source_fact()])
        for mode, case in (("CUSTOMER_SUPPORT", "SOURCE-CASE"), ("BANK_INTERNAL", "OTHER")):
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                CaseCopilotInput(case_id=case, prompt="근거", assistant_mode=mode, source_context=context)


class SourceAwareProviderTest(unittest.IsolatedAsyncioTestCase):
    async def generate(self, reply, *, error=None, context=None):
        create = AsyncMock(return_value=SimpleNamespace(output_text=reply), side_effect=error)
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}), patch(
            "ai_api.app.domains.case_support.copilot_service.AsyncOpenAI",
            return_value=SimpleNamespace(responses=SimpleNamespace(create=create)),
        ):
            result = await CaseCopilotService().generate(CaseCopilotInput(case_id="SOURCE-CASE", prompt="송금 근거를 설명해 주세요",
                source_context=context or BankCopilotSourceContext(facts=[source_fact()])))
        return result, create.await_args.kwargs

    async def test_source_preserved_to_provider_and_direct_answer_policy_kept(self):
        reply = "고객은 1,000만원을 송금했다고 진술했습니다. 실제 거래기록은 아직 확인이 필요합니다."
        result, args = await self.generate(reply)
        self.assertEqual(result.content, reply)
        self.assertIn('"source_kind":"CUSTOMER_STATEMENT"', args["input"])
        self.assertIn('"status":"PROPOSED"', args["input"])
        for rule in ("실제 질문에 직접 답변", "CONFIRMED여도 BANK_RECORD가 아닙니다", "timestamp만으로", "Evidence 미전달은 거래 미발생이 아닙니다"):
            self.assertIn(rule, args["instructions"])

    async def test_unsupported_objective_reply_is_not_delivered(self):
        result, _ = await self.generate("고객이 1,000만원 송금했습니다.")
        self.assertIn("확정하기 어렵습니다", result.content)
        self.assertNotIn("1,000만원", result.content)

    async def test_proposed_ai_extraction_prompt_requires_uncertain_wording(self):
        fact = source_fact("AI_EXTRACTION")
        reply = (
            "현재 객관적으로 확인된 사항은 없습니다. "
            "AI 분석에서 제안된 정황으로 송금 관련 내용이 있으며 추가 확인이 필요합니다."
        )
        result, args = await self.generate(reply, context=BankCopilotSourceContext(facts=[fact]))

        self.assertEqual(result.content, reply)
        for rule in (
            "질문이 '확인된 사항'을 묻더라도",
            "현재 객관적으로 확인된 사항은 없습니다",
            "AI 분석에서 제안된 정황",
            "위 승인 근거가 있는 값 범위에서는",
        ):
            self.assertIn(rule, args["instructions"])

    async def test_quality_log_distinguishes_user_text_normalization(self):
        provider_output = "confirmed-provider-marker-7f3a"
        with self.assertLogs(
            "ai_api.app.domains.case_support.copilot_service",
            level="WARNING",
        ) as captured_logs:
            result, _ = await self.generate(provider_output)

        log_output = "\n".join(captured_logs.output)
        self.assertIn("criteria=unsupported_certainty", log_output)
        self.assertIn("rules=staff_claim_without_confirmed_staff_source", log_output)
        self.assertIn("normalization_changed=True", log_output)
        self.assertIn("raw_rules=none", log_output)
        self.assertIn("normalized_rules=staff_claim_without_confirmed_staff_source", log_output)
        self.assertNotIn(provider_output, log_output)
        self.assertNotIn(provider_output, result.content)
        self.assertIn("추가 확인", result.content)

    async def test_bank_record_reply_delivered_without_promoting_customer_source(self):
        result, _ = await self.generate("은행 거래기록에서 1,000만원 이체 내역이 확인됩니다.",
            context=BankCopilotSourceContext(facts=[source_fact("BANK_RECORD", "CONFIRMED")]))
        self.assertIn("거래기록", result.content)

    async def test_provider_failure_stays_error(self):
        with self.assertRaises(CaseCopilotProviderError):
            await self.generate("", error=RuntimeError("provider unavailable"))
