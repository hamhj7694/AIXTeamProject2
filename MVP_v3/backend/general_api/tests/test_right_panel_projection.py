from __future__ import annotations

import unittest

from general_api.app.domains.cases.right_panel_projection import build_right_panel_projection


class RightPanelProjectionTest(unittest.TestCase):
    def test_sources_are_attributed_and_transfer_request_is_not_a_transaction(self):
        case = {
            "case_id": "VP-25",
            "victim_transfer_status": "UNKNOWN",
            "diagnosis": {
                "context": {
                    "summary": "수사기관 사칭 및 송금 유도 정황이 있는 사건입니다.",
                    "feature_narratives": [
                        {"code": "INCIDENT_CLAIM", "sentence": "계좌가 범죄에 연루됐다고 주장함", "status": "CLAIMED",
                         "speaker_role": "SUSPECTED_PARTY", "source_turns": [3], "atom_ids": ["claim-1"]},
                        {"code": "ACTION_TRANSFER_REQUEST", "sentence": "300만원 송금을 요구함", "status": "REQUESTED",
                         "speaker_role": "SUSPECTED_PARTY", "source_turns": [5], "atom_ids": ["demand-1"]},
                    ],
                },
                "semantic_mentions": [
                    {"mention_id": "entity-1", "mention_type": "INSTITUTION", "normalized_value": "서울중앙지검",
                     "speaker_role": "SUSPECTED_PARTY", "sequence_index": 3},
                ],
            },
        }
        context = {
            "situation_summary": "수사기관 사칭 및 송금 유도 정황이 있는 사건입니다.",
            "money_events": [
                {"event_id": "amount-1", "atom_id": "a-1", "amount_krw": 3_000_000,
                 "amount_role": "REQUESTED_AMOUNT", "action_state": "REQUESTED",
                 "speaker_role": "SUSPECTED_PARTY", "predicate": "안전계좌 송금 요구"},
                {"event_id": "amount-2", "atom_id": "a-2", "amount_krw": 3_000_000,
                 "amount_role": "TRANSFER_OUT", "action_state": "COMPLETED", "claim_status": "REPORTED",
                 "speaker_role": "CUSTOMER", "predicate": "송금했다고 답변"},
                {"event_id": "amount-3", "atom_id": "a-3", "amount_krw": 3_000_000,
                 "amount_role": "REQUESTED_AMOUNT", "action_state": "REQUESTED",
                 "speaker_role": "SUSPECTED_PARTY", "predicate": "환급을 위한 다른 계좌 이체 요구"},
            ],
        }
        result = build_right_panel_projection(
            case=case, case_context=context,
            questions=[{"question_id": "q-transfer", "target_field": "transfer_status", "status": "ANSWERED", "answer_text": "송금했어요"}],
            verifications=[
                {"verification_task_id": "v-1", "target": "기관 소속", "status": "COMPLETED", "result_summary": "회신 내용을 기록함"},
                {"verification_task_id": "v-2", "target": "사건번호", "status": "COMPLETED", "result_summary": "공식 조회 결과 불일치", "evidence_url": "https://www.police.go.kr/check"},
            ],
        )

        money = [item for item in result["exposure"] if "300만원" in item["title"]]
        self.assertEqual(len(money), 1)
        self.assertEqual(money[0]["title"], "300만원 송금 요구")
        self.assertEqual(money[0]["source_badge"], "상대방 요구")
        self.assertFalse(any("금액 관련 언급" in item["title"] for item in result["exposure"]))
        self.assertTrue(any(item["title"] == "실제 송금" and item["source_badge"] == "고객 진술" for item in result["exposure"]))
        self.assertEqual(result["contact_information"][0]["title"], "서울중앙지검")
        self.assertEqual(result["contact_information"][0]["source_badge"], "상대방 주장")
        verification_badges = {item["title"]: item["source_badge"] for item in result["verification"]}
        self.assertEqual(verification_badges["기관 소속"], "직원 기록")
        self.assertEqual(verification_badges["사건번호"], "공식 확인")

    def test_vp25_categories_entities_and_test_verification_are_human_readable(self):
        case = {"diagnosis": {"context": {"feature_narratives": [
            {"code": "ROLE_PROSECUTION", "sentence": "보이스피싱 의심 인물이 수사관 역할로 제시됨.",
             "status": "CLAIMED", "speaker_role": "SUSPECTED_PARTY", "source_turns": [6],
             "entity_names": ["김인수", "용의자", "INVESTIGATOR"], "atom_ids": ["role-1"]},
            {"code": "CLAIM_ACCOUNT_VERIFICATION", "sentence": "보이스피싱 의심 인물이 고객 계좌가 범죄에 연루됐다고 주장함.",
             "status": "CLAIMED", "speaker_role": "SUSPECTED_PARTY", "source_turns": [7],
             "entity_names": ["김인수"], "atom_ids": ["claim-1"]},
            {"code": "REQUEST_PERSONAL_INFO", "sentence": "보이스피싱 의심 인물이 고객에게 개인 정보 제공을 요구함.",
             "status": "REQUESTED", "speaker_role": "SUSPECTED_PARTY", "source_turns": [8],
             "entity_names": ["김민수", "BANK_EMPLOYEE"], "atom_ids": ["request-1"]},
            {"code": "TACTIC_FEAR", "sentence": "보이스피싱 의심 인물이 처벌 불안을 조성함.",
             "status": "CLAIMED", "speaker_role": "SUSPECTED_PARTY", "source_turns": [9],
             "entity_names": [], "atom_ids": ["pressure-1"]},
        ]}, "semantic_mentions": [
            {"mention_id": "name-1", "mention_type": "PERSON_NAME", "normalized_value": "김인수",
             "speaker_role": "SUSPECTED_PARTY", "sequence_index": 1, "source_turn_id": 6},
            {"mention_id": "role-1", "mention_type": "ROLE", "normalized_value": "용의자",
             "speaker_role": "SUSPECTED_PARTY", "sequence_index": 2, "source_turn_id": 6},
            {"mention_id": "code-1", "mention_type": "INSTITUTION", "normalized_value": "BANK",
             "speaker_role": "SUSPECTED_PARTY", "sequence_index": 3, "source_turn_id": 6},
            {"mention_id": "name-2", "mention_type": "PERSON_NAME", "normalized_value": "김민수",
             "speaker_role": "SUSPECTED_PARTY", "sequence_index": 4, "source_turn_id": 8},
            {"mention_id": "role-2", "mention_type": "ROLE", "normalized_value": "BANK_EMPLOYEE",
             "speaker_role": "SUSPECTED_PARTY", "sequence_index": 5, "source_turn_id": 8},
            {"mention_id": "court-1", "mention_type": "INSTITUTION", "normalized_value": "서울중앙지검",
             "speaker_role": "SUSPECTED_PARTY", "sequence_index": 6, "source_turn_id": 8},
        ]}}
        result = build_right_panel_projection(
            case=case, case_context={},
            verifications=[
                {"verification_task_id": "test-1", "target": "테스트 담당자", "claim": "테스트 내용", "status": "PENDING"},
                {"verification_task_id": "real-1", "target": "서울중앙지검 소속", "claim": "소속 확인", "status": "PENDING"},
            ],
        )

        groups = {group["key"]: group["items"] for group in result["fraud_signals"]}
        self.assertTrue(any("범죄에 연루됐다고 주장함" in item["title"] for item in groups["claim"]))
        self.assertEqual(groups["demand"][0]["title"], "개인정보·민감정보 제공 요구")
        self.assertTrue(groups["pressure"])
        contacts = {item["title"]: item for item in result["contact_information"]}
        self.assertEqual(contacts["김인수"]["detail"], "용의자로 지목")
        self.assertEqual(contacts["김민수"]["detail"], "은행 직원으로 언급")
        self.assertNotIn("BANK", contacts)
        self.assertNotIn("INVESTIGATOR", contacts)
        self.assertNotIn("테스트 담당자", {item["title"] for item in result["verification"]})
        self.assertEqual([item["title"] for item in result["verification"]], ["서울중앙지검 소속"])

    def test_checklist_recommendations_are_work_not_activity(self):
        action = {"action_id": "check-1", "action_type": "AI_CHECKLIST:P0:transfer_status",
                  "status": "REQUESTED", "note": "실제 송금 진행 여부 확인 필요",
                  "created_at": "2026-09-28T08:00:00Z"}
        result = build_right_panel_projection(case={}, case_context={}, actions=[action])
        self.assertEqual([item["title"] for item in result["incomplete_work"]], ["실제 송금 여부 확인"])
        self.assertEqual(result["activity"], [])

        completed = {**action, "status": "COMPLETED", "updated_at": "2026-09-28T08:15:00Z"}
        result = build_right_panel_projection(case={}, case_context={}, actions=[completed])
        self.assertEqual([item["title"] for item in result["completed_work"]], ["실제 송금 여부 확인"])
        self.assertEqual([item["title"] for item in result["activity"]], ["업무 완료: 실제 송금 여부 확인"])

    def test_absent_answers_are_unknown_not_no_harm(self):
        result = build_right_panel_projection(case={"diagnosis": {}}, case_context={})
        self.assertEqual(len(result["exposure"]), 4)
        self.assertTrue(all(item["source_badge"] == "미확인" for item in result["exposure"]))
        self.assertTrue(all("추가 확인 필요" in item["detail"] for item in result["exposure"]))


if __name__ == "__main__":
    unittest.main()
