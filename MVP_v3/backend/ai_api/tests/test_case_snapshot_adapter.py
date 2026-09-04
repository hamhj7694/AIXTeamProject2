from __future__ import annotations

import json
import unittest
from pathlib import Path

from ai_api.app.domains.case_support import CaseSnapshotAiAdapter


class CaseSnapshotAiAdapterTest(unittest.TestCase):
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
        self.assertIn("고객 답변상 이미 송금한 상태입니다", result.case_brief.summary)
        self.assertNotIn("최신 반영", result.case_brief.summary)
        self.assertNotIn("→", result.case_brief.summary)
        self.assertNotIn("transfer_status", [item.target_field.value for item in result.unresolved_items])
        self.assertIn("기관 확인 진행: 서울중앙지검", result.case_brief.next_checks)
        self.assertIn("대응 업무 진행: 지급정지 가능 여부 확인", result.case_brief.next_checks)

    def test_synthesizes_answers_and_confirmed_facts_instead_of_appending_a_log(self) -> None:
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
        self.assertIn("고객 답변상 이미 송금한 상태입니다", summary)
        self.assertIn("고객 답변상 개인정보를 제공하지 않은 상태입니다", summary)
        self.assertIn("확인 결과 비밀번호·인증번호 등 인증정보를 제공한 상태입니다", summary)
        self.assertIn("서울중앙지검 확인 결과 공식 사건번호와 일치하지 않음", summary)
        self.assertNotIn("상대방에게 송금했나요?", summary)
        self.assertNotIn("개인정보를 제공했나요?", summary)
        self.assertNotIn("최신 반영", summary)
        self.assertLessEqual(len(summary), 600)

    def test_question_context_alone_removes_already_handled_items(self) -> None:
        fixture = Path(__file__).resolve().parents[2] / "contracts" / "ai_internal" / "fixtures" / "diagnosis.high.v1.json"
        diagnosis = json.loads(fixture.read_text(encoding="utf-8"))["response"]

        result = CaseSnapshotAiAdapter().build_presentation({
            "case_id": "VP-SNAPSHOT-CONTEXT",
            "diagnosis": diagnosis,
            "question_context": {
                "confirmed_fields": ["transfer_status"],
                "answered_question_fields": ["personal_information_exposure"],
            },
        })

        unresolved = {item.target_field.value for item in result.unresolved_items}
        self.assertNotIn("transfer_status", unresolved)
        self.assertNotIn("personal_information_exposure", unresolved)

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


if __name__ == "__main__":
    unittest.main()
