from __future__ import annotations

import unittest

from ai_api.app.domains.case_support.question_policy import QuestionSource, normalize_question
from ai_api.app.domains.case_support.question_policy import question_eligibility, question_eligibility_from_context
from ai_api.app.domains.case_support.question_state_evaluator import QuestionStateEvaluator
from contracts.ai_internal.case_snapshot import CaseSnapshotQuestion, CaseSnapshotFact, CaseSnapshotVerification
from contracts.ai_internal.mvp_workflow import QuestionRecommendationContext


class QuestionEligibilityTest(unittest.TestCase):
    def test_semantic_states_drive_basic_and_follow_up_separately(self) -> None:
        scope = "authentication_information_exposure"
        for status, answer, fact_status, expected, sufficient, basic, follow in (
            (None, None, None, "UNRESOLVED", False, True, True),
            ("PENDING", None, None, "WAITING", False, False, False),
            ("ASKED", None, None, "WAITING", False, False, False),
            ("ANSWERED", "OTP는 알려주지 않았어요", None, "CLEAR_CUSTOMER_STATEMENT", True, False, False),
            ("ANSWERED", "기억이 안 나요", None, "UNCERTAIN", False, False, True),
            (None, None, "PROPOSED", "UNRESOLVED", False, True, True),
            (None, None, "CONFIRMED", "STAFF_CONFIRMED", True, False, False),
            ("ANSWERED", "기억이 안 나요", "CONFIRMED", "STAFF_CONFIRMED", True, False, False),
            ("SKIPPED", None, None, "SKIPPED", False, False, False),
        ):
            with self.subTest(status=status, fact_status=fact_status, expected=expected):
                q = CaseSnapshotQuestion(question_id="q", target_field=scope, question_text="OTP를 제공했나요?",
                                         status=status, answer_text=answer) if status else None
                fact = CaseSnapshotFact(fact_id="f", field=scope, value="제공하지 않음",
                                        status=fact_status) if fact_status else None
                evaluation = QuestionStateEvaluator.evaluate(semantic_scope=scope, question=q, fact=fact)
                result = question_eligibility(evaluation)
                self.assertEqual(evaluation.state.value, expected)
                self.assertEqual(evaluation.is_sufficient, sufficient)
                self.assertEqual(result.allow_basic_question, basic)
                self.assertEqual(result.allow_follow_up, follow)
                self.assertEqual(result.suppression_reason is None, basic)

    def test_verification_scope_and_explicit_conflict_use_evaluator_precedence(self) -> None:
        verification = CaseSnapshotVerification(verification_task_id="v", target="기관", claim="확인",
                                                status="COMPLETED", result_summary="등록된 결과")
        for scope, conflict, state, basic, follow in (
            ("transfer_status", False, "VERIFIED", False, False),
            ("claimed_organization", False, "UNRESOLVED", True, True),
            ("transfer_status", True, "CONFLICT", False, True),
        ):
            with self.subTest(scope=scope, conflict=conflict):
                evaluation = QuestionStateEvaluator.evaluate(semantic_scope="transfer_status",
                    verification=verification, verification_scope=scope, has_conflict=conflict)
                result = question_eligibility(evaluation)
                self.assertEqual(evaluation.state.value, state)
                self.assertEqual((result.allow_basic_question, result.allow_follow_up), (basic, follow))

    def test_active_lifecycle_still_blocks_immediate_follow_up(self) -> None:
        evaluation = QuestionStateEvaluator.evaluate(semantic_scope="transfer_status", is_uncertain=True)
        result = question_eligibility(evaluation, has_active_question=True)
        self.assertFalse(result.allow_basic_question)
        self.assertFalse(result.allow_follow_up)
        self.assertFalse(result.evaluation.is_sufficient)

    def test_field_history_without_raw_evidence_never_promotes_semantic_state(self) -> None:
        for context in (
            QuestionRecommendationContext(confirmed_fields=["transfer_status"]),
            QuestionRecommendationContext(answered_question_fields=["transfer_status"]),
        ):
            with self.subTest(context=context):
                result = question_eligibility_from_context("transfer_status", "q_transfer_status", context)
                self.assertEqual(result.evaluation.state.value, "UNRESOLVED")
                self.assertFalse(result.evaluation.is_sufficient)
                self.assertFalse(result.allow_basic_question)
                self.assertTrue(result.allow_follow_up)


def question(**updates):
    value = {
        "question_id": "q-1",
        "target_field": "exposure_scope",
        "question_text": "어떤 정보를 제공하셨나요?",
        "reason": "노출 범위를 확인해야 합니다.",
        "priority": "P1",
        "options": ["계좌번호", "신분증", "OTP"],
        "answer_mode": "CHOICE_OR_TEXT",
        "allow_free_text": True,
    }
    value.update(updates)
    return value


class QuestionPolicyTest(unittest.TestCase):
    def test_default_is_single_select(self) -> None:
        result = normalize_question(question(), source=QuestionSource.LLM)

        self.assertFalse(result.allow_multi_select)
        self.assertEqual(result.source, QuestionSource.LLM)

    def test_explicit_multi_select_is_preserved(self) -> None:
        result = normalize_question(
            question(allow_multi_select=True), source=QuestionSource.LLM,
        )

        self.assertTrue(result.allow_multi_select)
        self.assertEqual(len(result.options), 3)

    def test_options_are_trimmed_deduplicated_and_blank_values_are_removed(self) -> None:
        result = normalize_question(
            question(options=[" 계좌번호 ", "", "계좌번호", "신분증"]), source=QuestionSource.LLM,
        )

        self.assertEqual(result.options, ["계좌번호", "신분증"])

    def test_invalid_multi_select_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            normalize_question(
                question(options=["계좌번호", "계좌번호"], allow_multi_select=True),
                source=QuestionSource.LLM,
            )

    def test_more_than_eight_unique_options_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            normalize_question(
                question(options=[f"선택 {index}" for index in range(9)]), source=QuestionSource.LLM,
            )

    def test_malformed_options_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            normalize_question(question(options="계좌번호"), source=QuestionSource.LLM)
        with self.assertRaises(ValueError):
            normalize_question(question(options=["계좌번호", 123]), source=QuestionSource.LLM)

    def test_malformed_multi_select_flag_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            normalize_question(question(allow_multi_select="true"), source=QuestionSource.LLM)

    def test_text_question_does_not_keep_options_or_multi_select(self) -> None:
        result = normalize_question(
            question(answer_mode="TEXT", allow_multi_select=True), source=QuestionSource.LLM,
        )

        self.assertEqual(result.options, [])
        self.assertFalse(result.allow_multi_select)
        self.assertTrue(result.allow_free_text)

    def test_source_distinguishes_deterministic_and_llm_questions(self) -> None:
        deterministic = normalize_question(question(), source=QuestionSource.DETERMINISTIC)
        llm = normalize_question(question(), source=QuestionSource.LLM)

        self.assertEqual(deterministic.source, QuestionSource.DETERMINISTIC)
        self.assertEqual(llm.source, QuestionSource.LLM)

    def test_sensitive_value_request_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            normalize_question(
                question(question_text="OTP 인증번호를 입력해 주세요."), source=QuestionSource.LLM,
            )


if __name__ == "__main__":
    unittest.main()
