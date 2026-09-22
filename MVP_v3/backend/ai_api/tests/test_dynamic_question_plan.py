from __future__ import annotations

import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from contracts.ai_internal.case_snapshot import CaseSnapshotAiInput, CaseSnapshotFact, CaseSnapshotQuestion, CaseSnapshotVerification
from contracts.ai_internal.work_card import CaseWorkCardInput
from contracts.question_target import (
    canonical_question_scope, decode_follow_up_target, encode_follow_up_target,
    is_follow_up_target, follow_up_registration_allowed,
)
from ai_api.app.domains.case_support.case_snapshot_adapter import CaseSnapshotAiAdapter
from ai_api.app.domains.case_support.copilot_service import CaseCopilotProviderError
from ai_api.app.domains.case_support.question_policy import validate_follow_up_question
from ai_api.app.domains.case_support.work_card_service import CaseWorkCardService


def state(answer="기억이 잘 안 나요", status="ANSWERED"):
    return CaseSnapshotAiInput(case_id="CASE-DYNAMIC", questions=[CaseSnapshotQuestion(
        question_id="cq-parent", target_field="transfer_status", question_text="송금하셨나요?",
        status=status, answer_text=answer,
    )])


def proposal(text="은행 앱이나 거래 알림에서 실제 이체 내역을 확인할 수 있나요?"):
    return dict(question_id="llm-parent", target_field="qf1:incident_claim:wrong-parent",
                question_text=text, reason="기억 대신 거래 기록을 확인합니다.", priority="P1",
                options=[], customer_explanation=None, answer_mode="TEXT", allow_free_text=True)


def card_payload(questions):
    return dict(card_type="QUESTION_PLAN", title="확인 질문", summary="거래 기록 확인",
                context_sources=[], rationale=[], next_action="담당자가 검토합니다.", questions=questions,
                warnings=[], suggested_claim=None, suggested_target=None, suggested_action_type=None,
                suggested_action_note=None, suggested_notice=None, suggested_transition=None)


class FollowUpContractTest(unittest.TestCase):
    def test_round_trip_and_canonical_basic(self):
        for scope in ("transfer_status", "authentication_information_exposure", "remote_control_app"):
            with self.subTest(scope=scope):
                target = encode_follow_up_target(scope, "question-" + "a" * 32)
                self.assertLessEqual(len(target), 100)
                self.assertEqual(decode_follow_up_target(target).parent_question_id, "question-" + "a" * 32)
                self.assertEqual(canonical_question_scope(target), scope)
                self.assertTrue(is_follow_up_target(target))
        self.assertFalse(is_follow_up_target("transfer_status"))

    def test_malformed_and_overflow_rejected(self):
        for target in ("qf2:transfer_status:p", "qf1:no_scope:p", "qf1:transfer_status:",
                       "qf1:transfer_status:p:extra", "qf1:transfer_status:P", " qf1:transfer_status:p",
                       "qf1:transfer_status:" + "a" * 100):
            with self.subTest(target=target), self.assertRaises(ValueError):
                # The contract rejects whitespace around a reserved identity, too.
                decode_follow_up_target(target)
        with self.assertRaises(ValueError):
            encode_follow_up_target("transfer_status", "p" * 100)

    def test_parent_and_active_history_invariants(self):
        target = encode_follow_up_target("transfer_status", "cq-parent")
        parent = state().questions[0].model_dump()
        self.assertFalse(follow_up_registration_allowed(target, "거래 기록 확인", []))
        self.assertTrue(follow_up_registration_allowed(target, "거래 기록 확인", [parent]))
        for status in ("PENDING", "ASKED", "ANSWERED", "SKIPPED"):
            with self.subTest(status=status):
                child = dict(parent, question_id="cq-child", target_field=target, status=status)
                self.assertFalse(follow_up_registration_allowed(target, "다른 거래 기록 확인", [parent, child]))


class DynamicPolicyTest(unittest.TestCase):
    def test_transfer_request_is_not_a_clear_transfer_answer(self):
        adapter = CaseSnapshotAiAdapter()
        for answer, state_name in (("송금하라고 했어요", "UNCERTAIN"),
                                   ("송금하지 않았어요", "CLEAR_CUSTOMER_STATEMENT"),
                                   ("아니요", "CLEAR_CUSTOMER_STATEMENT")):
            with self.subTest(answer=answer):
                current = state(answer)
                policy = adapter.question_eligibilities(current)["transfer_status"]
                self.assertEqual(policy.evaluation.state.value, state_name)
                self.assertFalse(policy.allow_basic_question)
                self.assertEqual(bool(adapter.follow_up_parents(current)), state_name == "UNCERTAIN")

    def test_remote_installation_request_and_actual_installation_are_distinct(self):
        adapter = CaseSnapshotAiAdapter()
        request_fact = CaseSnapshotFact(fact_id="request", field="remote_control_app",
                                        value="원격제어 앱 설치 요구", status="CONFIRMED")
        current = CaseSnapshotAiInput(case_id="CASE-DYNAMIC", facts=[request_fact])
        policy = adapter.question_eligibilities(current)["remote_control_app"]
        self.assertEqual(policy.evaluation.state.value, "UNRESOLVED")
        self.assertTrue(policy.allow_basic_question)
        installed = request_fact.model_copy(update={"value": "설치됨"})
        policy = adapter.question_eligibilities(current.model_copy(update={"facts": [installed]}))["remote_control_app"]
        self.assertEqual(policy.evaluation.state.value, "STAFF_CONFIRMED")
        self.assertFalse(policy.allow_basic_question)
        answered_request = CaseSnapshotQuestion(
            question_id="q-app", target_field="remote_control_app",
            question_text="실제로 설치하셨나요?", status="ANSWERED", answer_text="설치 안내만 받았어요",
        )
        policy = adapter.question_eligibilities(CaseSnapshotAiInput(
            case_id="CASE-DYNAMIC", questions=[answered_request],
        ))["remote_control_app"]
        self.assertEqual(policy.evaluation.state.value, "UNCERTAIN")
        self.assertFalse(policy.allow_basic_question)

    def test_unlinked_completed_verification_does_not_suppress_question(self):
        verification = CaseSnapshotVerification(
            verification_task_id="v1", target="은행", claim="송금 여부 확인",
            status="COMPLETED", result_summary="확인 완료",
        )
        policy = CaseSnapshotAiAdapter.question_eligibilities(CaseSnapshotAiInput(
            case_id="CASE-DYNAMIC", verifications=[verification],
        ))["transfer_status"]
        self.assertEqual(policy.evaluation.state.value, "UNRESOLVED")
        self.assertTrue(policy.allow_basic_question)

    def test_auth_follow_checks_past_action_without_requesting_actual_code(self):
        parent = state().questions[0].model_copy(update={
            "target_field": "authentication_information_exposure", "question_text": "OTP를 알려주셨나요?",
        })
        raw = proposal("상대방에게 숫자로 된 인증번호를 읽어주거나 메시지로 보낸 기억이 있는지 다시 확인해주실 수 있나요?")
        raw["target_field"] = encode_follow_up_target(parent.target_field, parent.question_id)
        self.assertEqual(validate_follow_up_question(raw, parent).target_field, raw["target_field"])

    def test_uncertain_parent_selected_but_clear_waiting_skipped_missing_are_suppressed(self):
        adapter = CaseSnapshotAiAdapter()
        uncertain = state()
        policy = adapter.question_eligibilities(uncertain)["transfer_status"]
        self.assertEqual(policy.evaluation.state.value, "UNCERTAIN")
        self.assertFalse(policy.allow_basic_question)
        self.assertTrue(policy.allow_follow_up)
        self.assertEqual(list(adapter.follow_up_parents(uncertain)), [encode_follow_up_target("transfer_status", "cq-parent")])
        for current in (state("송금했어요"), state(None, "ASKED"), state(None, "PENDING"),
                        state(None, "SKIPPED"), CaseSnapshotAiInput(case_id="CASE-DYNAMIC")):
            with self.subTest(current=current):
                self.assertEqual(adapter.follow_up_parents(current), {})

    def test_confirmed_fact_suppresses_uncertain_parent(self):
        current = state()
        current.facts = CaseSnapshotAiInput(facts=[dict(fact_id="f", field="transfer_status", value="송금함", status="CONFIRMED")]).facts
        self.assertEqual(CaseSnapshotAiAdapter.follow_up_parents(current), {})

    def test_follow_target_restored_and_relation_retained_without_current_selection(self):
        current = state()
        target = encode_follow_up_target("transfer_status", "cq-parent")
        current.questions.append(CaseSnapshotQuestion(question_id="cq-child", target_field=target,
            question_text="거래 기록 확인", status="ASKED"))
        policies = CaseSnapshotAiAdapter.question_eligibilities(current)
        self.assertNotIn(target, policies)
        self.assertFalse(policies["transfer_status"].allow_follow_up)
        self.assertEqual(decode_follow_up_target(current.questions[1].target_field).parent_question_id, "cq-parent")
        current.questions[1] = current.questions[1].model_copy(update={"status": "ANSWERED", "answer_text": "송금했어요"})
        self.assertFalse(policies["transfer_status"].evaluation.is_sufficient)
        self.assertNotIn(target, CaseSnapshotAiAdapter._current_field_values(current))
        self.assertNotIn("transfer_status", CaseSnapshotAiAdapter._current_field_values(current))
        self.assertEqual(CaseSnapshotAiAdapter.follow_up_parents(current), {})

    def test_repeat_secret_and_money_instruction_rejected(self):
        parent = state().questions[0]
        for text in ("정말 송금하셨나요?", "송금하셨나요?", "거래내역 확인을 위해 OTP를 입력하세요",
                     "거래내역 확인 후 지금 송금하세요"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                raw = proposal(text)
                raw["target_field"] = encode_follow_up_target(parent.target_field, parent.question_id)
                validate_follow_up_question(raw, parent)


class DynamicGenerationTest(unittest.IsolatedAsyncioTestCase):
    async def generate(self, questions, *, current=None, error=None):
        create = AsyncMock(return_value=SimpleNamespace(output_text=json.dumps(card_payload(questions), ensure_ascii=False)), side_effect=error)
        client = SimpleNamespace(responses=SimpleNamespace(create=create))
        request = CaseWorkCardInput(case_id="CASE-DYNAMIC", card_type="QUESTION_PLAN", question_state=current or state())
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}), patch(
            "ai_api.app.domains.case_support.work_card_service.AsyncOpenAI", return_value=client
        ):
            result = await CaseWorkCardService().generate(request)
        return result, create

    async def test_meaningful_question_has_server_identity_and_bounded_input(self):
        result, create = await self.generate([proposal()])
        target = encode_follow_up_target("transfer_status", "cq-parent")
        self.assertEqual(result.questions[0].target_field, target)
        self.assertEqual(result.questions[0].question_id, target)
        sent = json.loads(create.await_args.kwargs["input"])["follow_up"]
        self.assertEqual(sent["canonical_scope"], "transfer_status")
        self.assertEqual(sent["semantic_state"], "UNCERTAIN")
        self.assertEqual(sent["parent_answer"], "기억이 잘 안 나요")
        self.assertIn("기록 확인", sent["purpose"])

    async def test_paraphrase_is_not_accepted(self):
        with self.assertRaises(CaseCopilotProviderError):
            await self.generate([proposal("정말 송금하셨나요?")])

    async def test_provider_failure_is_not_fabricated(self):
        with self.assertRaises(CaseCopilotProviderError):
            await self.generate([], error=RuntimeError("provider unavailable"))

    async def test_empty_result_stays_empty_and_multiple_per_parent_rejected(self):
        result, _ = await self.generate([])
        self.assertEqual(result.questions, [])
        with self.assertRaises(CaseCopilotProviderError):
            await self.generate([proposal(), proposal()])

    async def test_case_mismatch_rejected_before_provider(self):
        current = state()
        current.case_id = "OTHER"
        with self.assertRaises(CaseCopilotProviderError):
            await self.generate([], current=current)
