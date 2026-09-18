"""P3-1 의미 상태 unit 검사. production Eligibility 연결 검사가 아니다."""

import unittest

from contracts.ai_internal.case_snapshot import CaseSnapshotFact, CaseSnapshotQuestion, CaseSnapshotVerification
from ai_api.app.domains.case_support.question_state_evaluator import QuestionStateEvaluator
from ai_api.app.domains.case_support.verification_policy import VerificationResult


SCOPE = "authentication_information_exposure"


def question(status, answer=None, field=SCOPE):
    return CaseSnapshotQuestion(
        question_id="q-auth", target_field=field, question_text="OTP를 제공했나요?",
        status=status, answer_text=answer,
    )


def fact(status="CONFIRMED", field=SCOPE, value="제공하지 않음"):
    return CaseSnapshotFact(fact_id="fact-auth", field=field, value=value, status=status)


def verification(status="COMPLETED", summary="제공 여부 확인 결과 등록"):
    return CaseSnapshotVerification(
        verification_task_id="verify-auth", target="확인 대상", claim="확인 요청",
        status=status, result_summary=summary,
    )


class QuestionStateEvaluatorTest(unittest.TestCase):
    def check(self, state, sufficient=False, follow_up=False, **kwargs):
        result = QuestionStateEvaluator.evaluate(semantic_scope=SCOPE, **kwargs)
        self.assertEqual(result.state.value, state)
        self.assertEqual(result.is_sufficient, sufficient)
        self.assertEqual(result.allow_follow_up, follow_up)
        return result

    def test_no_information_is_unresolved(self):
        self.check("UNRESOLVED", follow_up=True)

    def test_pending_and_asked_without_answer_are_waiting(self):
        for status in ("PENDING", "ASKED"):
            with self.subTest(status=status):
                self.check("WAITING", question=question(status))

    def test_answered_negative_is_statement_not_verified(self):
        self.check("CLEAR_CUSTOMER_STATEMENT", sufficient=True,
                   question=question("ANSWERED", "OTP는 안 알려줬어요"))

    def test_answered_without_content_is_not_sufficient(self):
        self.check("UNRESOLVED", follow_up=True, question=question("ANSWERED", "  "))

    def test_uncertainty_fallback(self):
        for answer in ("기억이 안 나요", "잘 모르겠어요", "확실하지 않아요", "기억나지 않아요", "애매해요", "헷갈려요"):
            with self.subTest(answer=answer):
                self.check("UNCERTAIN", follow_up=True, question=question("ANSWERED", answer))

    def test_explicit_uncertainty_overrides_answered(self):
        self.check("UNCERTAIN", follow_up=True, question=question("ANSWERED", "제공했어요"), is_uncertain=True)

    def test_explicit_normalized_clear_state_overrides_fallback(self):
        self.check("CLEAR_CUSTOMER_STATEMENT", sufficient=True, answer_text="잘 모르겠어요", is_uncertain=False)

    def test_conflict_and_correction_override_clear_statement(self):
        for flags in ({"has_conflict": True}, {"correction_needed": True}):
            with self.subTest(flags=flags):
                self.check("CONFLICT", follow_up=True, question=question("ANSWERED", "제공했어요"), **flags)

    def test_staff_confirmation_is_not_verified(self):
        self.check("STAFF_CONFIRMED", sufficient=True, fact=fact())

    def test_staff_confirmation_overrides_statement_and_uncertainty(self):
        self.check("STAFF_CONFIRMED", sufficient=True, fact=fact(), is_uncertain=True,
                   question=question("ANSWERED", "제공했어요"))

    def test_completed_verification_requires_explicit_matching_scope(self):
        self.check("VERIFIED", sufficient=True, verification=verification(), verification_scope=SCOPE)
        for scope in (None, "claimed_organization"):
            with self.subTest(scope=scope):
                self.check("UNRESOLVED", follow_up=True, verification=verification(), verification_scope=scope)

    def test_verification_result_model_is_reused(self):
        result = VerificationResult(verification_task_id="v1", version=1, claim="확인 요청",
                                    target="확인 대상", status="COMPLETED", result_summary="등록된 확인 결과")
        self.check("VERIFIED", sufficient=True, verification=result, verification_scope=SCOPE)

    def test_pending_failed_and_empty_verification_do_not_verify(self):
        for result in (verification("PENDING"), verification("FAILED"), verification(summary=" ")):
            with self.subTest(result=result):
                self.check("UNRESOLVED", follow_up=True, verification=result, verification_scope=SCOPE)

    def test_verified_overrides_staff_uncertainty_and_lifecycle(self):
        for status in ("PENDING", "ASKED", "SKIPPED", "ANSWERED"):
            with self.subTest(status=status):
                self.check("VERIFIED", sufficient=True, fact=fact(), is_uncertain=True,
                           question=question(status), verification=verification(), verification_scope=SCOPE)

    def test_unresolved_conflict_is_not_erased_by_previous_confirmation(self):
        self.check("CONFLICT", follow_up=True, has_conflict=True, fact=fact(),
                   verification=verification(), verification_scope=SCOPE)

    def test_skipped_is_not_sufficient_or_immediate_follow_up(self):
        self.check("SKIPPED", question=question("SKIPPED"))

    def test_later_answer_overrides_waiting_or_skipped(self):
        for status in ("ASKED", "SKIPPED"):
            with self.subTest(status=status):
                self.check("CLEAR_CUSTOMER_STATEMENT", sufficient=True, question=question(status, "제공하지 않았어요"))

    def test_proposed_fact_alone_does_not_promote_or_suffice(self):
        self.check("UNRESOLVED", follow_up=True, fact=fact("PROPOSED"))
        self.check("CLEAR_CUSTOMER_STATEMENT", sufficient=True, fact=fact("PROPOSED"), answer_text="OTP는 안 알려줬어요")

    def test_unrelated_question_and_fact_do_not_resolve_scope(self):
        self.check("UNRESOLVED", follow_up=True, fact=fact(field="transfer_status"),
                   question=question("ANSWERED", "송금했어요", field="transfer_status"))

    def test_empty_confirmed_fact_does_not_suffice(self):
        self.check("UNRESOLVED", follow_up=True, fact=fact(value=" "))

    def test_empty_scope_is_rejected(self):
        with self.assertRaises(ValueError):
            QuestionStateEvaluator.evaluate(semantic_scope=" ")
