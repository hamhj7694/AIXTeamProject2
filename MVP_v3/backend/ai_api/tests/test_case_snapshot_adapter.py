from __future__ import annotations

import json
import unittest
from pathlib import Path

from ai_api.app.domains.case_support import CaseSnapshotAiAdapter


class CaseSnapshotAiAdapterTest(unittest.TestCase):
    def test_uncertain_answer_survives_live_state_without_basic_repeat(self) -> None:
        fixture = Path(__file__).resolve().parents[2] / "contracts" / "ai_internal" / "fixtures" / "diagnosis.high.v1.json"
        diagnosis = json.loads(fixture.read_text(encoding="utf-8"))["response"]
        adapter = CaseSnapshotAiAdapter()
        snapshot = {
            "case_id": "VP-UNCERTAIN", "diagnosis": diagnosis,
            "question_context": {"answered_question_fields": ["authentication_information_exposure"]},
            "questions": [{"question_id": "q-auth", "target_field": "authentication_information_exposure",
                "question_text": "OTP를 제공했나요?", "status": "ANSWERED", "answer_text": "기억이 안 나요"}],
        }
        result = adapter.build_presentation(snapshot)
        policy = adapter.question_eligibilities(adapter.adapt(snapshot))["authentication_information_exposure"]
        self.assertEqual(policy.evaluation.state.value, "UNCERTAIN")
        self.assertFalse(policy.evaluation.is_sufficient)
        self.assertTrue(policy.allow_follow_up)
        self.assertIn("authentication_information_exposure", {item.target_field.value for item in result.unresolved_items})
        self.assertNotIn("authentication_information_exposure", {item.target_field.value for item in result.recommended_questions})

    def test_proposed_only_and_unscoped_completed_verification_do_not_resolve(self) -> None:
        fixture = Path(__file__).resolve().parents[2] / "contracts" / "ai_internal" / "fixtures" / "diagnosis.high.v1.json"
        diagnosis = json.loads(fixture.read_text(encoding="utf-8"))["response"]
        snapshot = {
            "case_id": "VP-PROPOSED", "diagnosis": diagnosis,
            "facts": [{"fact_id": "f-transfer", "field": "transfer_status", "value": "송금함", "status": "PROPOSED"}],
            "verifications": [{"verification_task_id": "v-org", "target": "기관", "claim": "기관 확인",
                                "status": "COMPLETED", "result_summary": "등록된 기관 확인 결과"}],
        }
        adapter = CaseSnapshotAiAdapter()
        result = adapter.build_presentation(snapshot)
        policy = adapter.question_eligibilities(adapter.adapt(snapshot))["transfer_status"]
        self.assertEqual(policy.evaluation.state.value, "UNRESOLVED")
        self.assertFalse(policy.evaluation.is_sufficient)
        self.assertIn("transfer_status", {item.target_field.value for item in result.recommended_questions})

    def test_skipped_and_multiple_values_are_not_sufficient(self) -> None:
        adapter = CaseSnapshotAiAdapter()
        snapshot = {
            "case_id": "VP-MULTIPLE",
            "questions": [{"question_id": "q-auth", "target_field": "authentication_information_exposure",
                           "question_text": "OTP를 제공했나요?", "status": "SKIPPED"}],
            "facts": [{"fact_id": "f1", "field": "transfer_status", "value": "송금함", "status": "CONFIRMED"},
                      {"fact_id": "f2", "field": "transfer_status", "value": "송금하지 않음", "status": "CONFIRMED"}],
        }
        for facts in (snapshot["facts"], list(reversed(snapshot["facts"]))):
            with self.subTest(facts=facts):
                policies = adapter.question_eligibilities(adapter.adapt({**snapshot, "facts": facts}))
                skipped = policies["authentication_information_exposure"]
                self.assertFalse(skipped.evaluation.is_sufficient)
                self.assertFalse(skipped.allow_basic_question)
                self.assertFalse(skipped.allow_follow_up)
                # 관계 정보가 없으므로 conflict를 만들어내거나 마지막 값을 확정하지 않는다.
                self.assertEqual(policies["transfer_status"].evaluation.state.value, "UNRESOLVED")

    def test_builds_brief_and_preserves_diagnosis_warnings(self) -> None:
        fixture = Path(__file__).resolve().parents[2] / "contracts" / "ai_internal" / "fixtures" / "diagnosis.high.v1.json"
        diagnosis = json.loads(fixture.read_text(encoding="utf-8"))["response"]
        diagnosis.update({"warnings": ["diagnosis warning"], "partial_failure": True})

        result = CaseSnapshotAiAdapter().build_presentation({
            "case_id": "VP-SNAPSHOT-001",
            "diagnosis": diagnosis,
            "warnings": ["input warning"],
            "question_context": {"pending_question_fields": ["transfer_status"]},
        })

        self.assertEqual(result.case_id, "VP-SNAPSHOT-001")
        self.assertIsNotNone(result.case_brief)
        self.assertNotIn("transfer_status", [item.target_field.value for item in result.recommended_questions])
        self.assertIn("input warning", result.warnings)
        self.assertIn("diagnosis warning", result.warnings)

    def test_latest_question_answer_and_work_state_update_the_presentation(self) -> None:
        fixture = Path(__file__).resolve().parents[2] / "contracts" / "ai_internal" / "fixtures" / "diagnosis.high.v1.json"
        diagnosis = json.loads(fixture.read_text(encoding="utf-8"))["response"]

        result = CaseSnapshotAiAdapter().build_presentation({
            "case_id": "VP-SNAPSHOT-LIVE",
            "diagnosis": diagnosis,
            "question_context": {"answered_question_fields": ["transfer_status"]},
            "questions": [{
                "question_id": "q-transfer", "target_field": "transfer_status",
                "question_text": "실제 송금하셨나요?", "priority": "P0",
                "status": "ANSWERED", "answer_text": "이미 송금했어요",
            }],
            "facts": [{
                "fact_id": "fact-transfer", "field": "transfer_status",
                "value": "이미 송금했어요", "status": "PROPOSED",
            }],
            "verifications": [{
                "verification_task_id": "verification-1", "target": "서울중앙지검",
                "claim": "검찰 사칭 여부", "status": "IN_PROGRESS",
            }],
            "actions": [{
                "action_id": "action-1", "action_type": "PAYMENT_HOLD_REVIEW",
                "status": "IN_PROGRESS", "note": "지급정지 가능 여부 확인",
            }],
        })

        self.assertIsNotNone(result.case_brief)
        self.assertIn("고객은 송금했다고 답", result.case_brief.summary)
        self.assertNotIn("최신 반영", result.case_brief.summary)
        self.assertNotIn("→", result.case_brief.summary)
        self.assertNotIn("transfer_status", [item.target_field.value for item in result.unresolved_items])
        self.assertIn("기관 확인 진행: 서울중앙지검", result.case_brief.next_checks)
        self.assertIn("대응 업무 진행: 지급정지 가능 여부 확인", result.case_brief.next_checks)

    def test_summary_preserves_answer_sources_and_does_not_promote_legacy_fact_status(self) -> None:
        fixture = Path(__file__).resolve().parents[2] / "contracts" / "ai_internal" / "fixtures" / "diagnosis.high.v1.json"
        diagnosis = json.loads(fixture.read_text(encoding="utf-8"))["response"]

        result = CaseSnapshotAiAdapter().build_presentation({
            "case_id": "VP-SNAPSHOT-SUMMARY",
            "diagnosis": diagnosis,
            "questions": [
                {
                    "question_id": "q-transfer", "target_field": "transfer_status",
                    "question_text": "상대방에게 송금했나요?", "priority": "P0",
                    "status": "ANSWERED", "answer_text": "예",
                },
                {
                    "question_id": "q-personal", "target_field": "personal_information_exposure",
                    "question_text": "개인정보를 제공했나요?", "priority": "P0",
                    "status": "ANSWERED", "answer_text": "제공하지 않았어요",
                },
            ],
            "facts": [{
                "fact_id": "fact-auth", "field": "authentication_information_exposure",
                "value": "제공했어요", "status": "CONFIRMED",
            }],
            "verifications": [{
                "verification_task_id": "verification-1", "target": "서울중앙지검",
                "claim": "검찰 사칭 여부", "status": "COMPLETED",
                "result_summary": "공식 사건번호와 일치하지 않음",
            }],
        })

        summary = result.case_brief.summary
        self.assertIn("고객은 송금했다고 답했고", summary)
        self.assertIn("개인정보를 제공하지 않았다고 답했습니다", summary)
        self.assertNotIn("인증정보를 제공했다고 답했습니다", summary)
        self.assertNotIn("상대방에게 송금했나요?", summary)
        self.assertNotIn("개인정보를 제공했나요?", summary)
        self.assertNotIn("최신 반영", summary)
        self.assertNotIn("고객 상태:", summary)
        self.assertNotIn("진행 업무:", summary)
        self.assertLessEqual(len(summary.split(". ")), 3)
        self.assertLessEqual(len(summary), 600)

    def test_amount_projection_accepts_literal_actor_role_values(self) -> None:
        fixture = Path(__file__).resolve().parents[2] / "contracts" / "ai_internal" / "fixtures" / "diagnosis.high.v1.json"
        diagnosis = json.loads(fixture.read_text(encoding="utf-8"))["response"]
        diagnosis["semantic_atoms"] = [{
            "atom_id": "amount-1", "atom_class": "MONEY_MOVEMENT", "speaker": "SUSPECTED_PARTY",
            "predicate": "TRANSFER_FUNDS", "source_turn_id": 1, "semantic_fingerprint": "fp-amount-1",
            "amount_value_krw": 3_000_000, "amount_role": "REQUESTED_AMOUNT",
            "amount_direction": "REQUEST", "action_state": "REQUESTED",
            "speaker_role": "SUSPECTED_PARTY", "actor_role": "SUSPECTED_PARTY",
        }]

        result = CaseSnapshotAiAdapter().build_presentation({
            "case_id": "VP-AMOUNT-PROJECTION", "diagnosis": diagnosis,
        })

        amount = result.case_context.money_events[0]
        self.assertEqual(amount["amount_krw"], 3_000_000)
        self.assertEqual(amount["speaker_role"], "SUSPECTED_PARTY")
        self.assertEqual(amount["actor_role"], "SUSPECTED_PARTY")

    def test_question_context_without_answer_does_not_prove_sufficiency(self) -> None:
        fixture = Path(__file__).resolve().parents[2] / "contracts" / "ai_internal" / "fixtures" / "diagnosis.high.v1.json"
        diagnosis = json.loads(fixture.read_text(encoding="utf-8"))["response"]

        result = CaseSnapshotAiAdapter().build_presentation({
            "case_id": "VP-SNAPSHOT-CONTEXT",
            "diagnosis": diagnosis,
            "facts": [{"fact_id": "f-transfer", "field": "transfer_status",
                       "value": "송금하지 않음", "status": "CONFIRMED"}],
            "question_context": {
                "confirmed_fields": ["transfer_status"],
                "answered_question_fields": ["personal_information_exposure"],
            },
        })

        unresolved = {item.target_field.value for item in result.unresolved_items}
        self.assertNotIn("transfer_status", unresolved)
        self.assertIn("personal_information_exposure", unresolved)
        self.assertNotIn("personal_information_exposure", {item.target_field.value for item in result.recommended_questions})

    def test_rebuilds_case_context_from_latest_structured_case_state(self) -> None:
        fixture = Path(__file__).resolve().parents[2] / "contracts" / "ai_internal" / "fixtures" / "diagnosis.high.v1.json"
        diagnosis = json.loads(fixture.read_text(encoding="utf-8"))["response"]

        result = CaseSnapshotAiAdapter().build_presentation({
            "case_id": "VP-SNAPSHOT-CONTEXT-PROJECTION",
            "diagnosis": diagnosis,
            "questions": [{
                "question_id": "q-org", "target_field": "claimed_organization",
                "question_text": "어느 기관이라고 했나요?", "priority": "P1",
                "status": "ANSWERED", "answer_text": "경찰청",
            }],
            "facts": [
                {"fact_id": "f-transfer", "field": "transfer_status", "value": "YES", "status": "CONFIRMED"},
                {"fact_id": "f-org", "field": "claimed_organization", "value": "서울중앙지검", "status": "CONFIRMED"},
                {"fact_id": "f-purpose", "field": "transfer_purpose", "value": "안전계좌 검증", "status": "CONFIRMED"},
            ],
            "verifications": [{
                "verification_task_id": "v-org", "target": "서울중앙지검",
                "claim": "사건번호 진위", "status": "COMPLETED",
                "result_summary": "해당 사건번호 없음",
            }],
        })

        context = result.case_context
        self.assertIsNotNone(context)
        self.assertIn("고객의 실제 송금 발생", context.key_signals)
        self.assertIn("서울중앙지검 공식 확인: 해당 사건번호 없음", context.key_signals)
        self.assertIn("서울중앙지검 소속이라고 주장", context.offender_claims)
        self.assertNotIn("경찰청 소속이라고 주장", context.offender_claims)
        self.assertIn("안전계좌 검증 명목의 자금 이동 요구", context.offender_demands)

    def test_partial_personal_information_answer_is_visible_in_customer_exposure(self) -> None:
        fixture = Path(__file__).resolve().parents[2] / "contracts" / "ai_internal" / "fixtures" / "diagnosis.high.v1.json"
        diagnosis = json.loads(fixture.read_text(encoding="utf-8"))["response"]

        result = CaseSnapshotAiAdapter().build_presentation({
            "case_id": "VP-SNAPSHOT-PARTIAL-EXPOSURE",
            "diagnosis": diagnosis,
            "questions": [{
                "question_id": "q-personal", "target_field": "personal_information_exposure",
                "question_text": "주민등록번호나 계좌번호 등 개인정보를 제공하셨나요?",
                "priority": "P0", "status": "ANSWERED",
                "answer_text": "주민등록번호 앞자리만 전달했어요",
            }],
        })

        self.assertIn("개인정보 일부 제공 발생", result.case_context.customer_exposure)
        self.assertIn("고객은 개인정보 일부를 제공했다고 답", result.case_brief.summary)


if __name__ == "__main__":
    unittest.main()
