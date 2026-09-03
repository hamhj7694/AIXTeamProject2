from __future__ import annotations

import unittest
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

import general_api.app.main as general_main
from contracts.public_api.case_workflow import to_public_customer_question_view


CASE = {"case_id": "VP-ACTIVITY", "input_text": "test"}
BUNDLE_CASE = {
    "case_id": "VP-ACTIVITY", "client_request_id": None, "input_text": "test", "risk": "HIGH", "risk_score": 0.9,
    "mode": "PREVENT", "status": "TRIAGE", "initial_brief": "brief", "diagnosis": {},
    "initial_report": {"report_id": "live-1", "case_id": "VP-ACTIVITY", "report_version": 1},
    "created_at": "2026-09-02T01:00:00+00:00", "updated_at": "2026-09-02T01:00:00+00:00",
}


class CaseActivityEndpointTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(general_main.app)
        self.original_repository = general_main.repository
        self.repository = AsyncMock()
        self.repository.get.return_value = CASE
        self.repository.get_voice_session.return_value = None
        general_main.repository = self.repository

    def tearDown(self) -> None:
        general_main.repository = self.original_repository
        self.client.close()

    def test_create_message_returns_public_message(self) -> None:
        self.repository.append_message.return_value = {
            "message_id": "msg-1", "case_id": "VP-ACTIVITY", "actor_type": "CUSTOMER",
            "content": "송금하지 않았습니다.", "client_request_id": "web-1", "created_at": "2026-09-02T01:00:00+00:00",
        }

        response = self.client.post("/api/cases/VP-ACTIVITY/messages", json={
            "actor_type": "CUSTOMER", "actor_user_id": "customer-1", "actor_display_name": "고객",
            "content": "송금하지 않았습니다.", "client_request_id": "web-1",
        })

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["channel"], "CUSTOMER")
        self.assertEqual(response.json()["audience"], "CUSTOMER")
        self.assertEqual(response.json()["mentions"], [])
        self.assertIsNone(response.json()["reply_to_message_id"])
        self.assertEqual({key: response.json()[key] for key in ("message_id", "case_id", "actor_type", "content", "created_at")}, {
            "message_id": "msg-1", "case_id": "VP-ACTIVITY", "actor_type": "CUSTOMER",
            "content": "송금하지 않았습니다.", "created_at": "2026-09-02T01:00:00+00:00",
        })

    def test_list_events_applies_cursor(self) -> None:
        self.repository.list_events.return_value = [{
            "event_id": 3, "case_id": "VP-ACTIVITY", "event_type": "MESSAGE_ADDED", "actor_type": "CUSTOMER",
            "payload": {"message_id": "msg-1"}, "occurred_at": "2026-09-02T01:00:00+00:00",
        }]

        response = self.client.get("/api/cases/VP-ACTIVITY/events?after=2")

        self.assertEqual(response.status_code, 200)
        self.repository.list_events.assert_awaited_once_with("VP-ACTIVITY", 2)
        self.assertEqual(response.json()[0]["event_id"], 3)

    def test_activity_endpoints_return_404_for_unknown_case(self) -> None:
        self.repository.get.return_value = None

        response = self.client.get("/api/cases/VP-UNKNOWN/messages")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"]["code"], "CASE_NOT_FOUND")

    def test_verification_and_action_use_case_scoped_contracts(self) -> None:
        self.repository.create_verification.return_value = {
            "verification_task_id": "ver-1", "case_id": "VP-ACTIVITY", "claim": "기관 사칭", "target": "검찰청",
            "status": "PENDING", "version": 1, "created_at": "2026-09-02T01:00:00+00:00", "updated_at": "2026-09-02T01:00:00+00:00",
        }
        self.repository.create_action.return_value = {
            "action_id": "act-1", "case_id": "VP-ACTIVITY", "action_type": "HUMAN_TAKEOVER", "status": "REQUESTED",
            "actor_type": "BANK_STAFF", "note": "담당자 검토 요청", "created_at": "2026-09-02T01:00:00+00:00",
        }
        verification = self.client.post("/api/cases/VP-ACTIVITY/verifications", json={"claim": "기관 사칭", "target": "검찰청"})
        action = self.client.post("/api/cases/VP-ACTIVITY/actions", json={"action_type": "HUMAN_TAKEOVER", "actor_type": "BANK_STAFF", "note": "담당자 검토 요청"})

        self.assertEqual(verification.status_code, 201)
        self.assertEqual(action.status_code, 201)
        self.repository.create_verification.assert_awaited_once()
        self.repository.create_action.assert_awaited_once()

    def test_verification_update_and_takeover_commands_are_persisted(self) -> None:
        self.repository.update_verification.return_value = {
            "verification_task_id": "ver-1", "case_id": "VP-ACTIVITY", "claim": "기관 직원 주장", "target": "기관",
            "status": "COMPLETED", "version": 2, "created_at": "2026-09-02T01:00:00+00:00", "updated_at": "2026-09-02T01:01:00+00:00",
        }
        self.repository.create_action.return_value = {
            "action_id": "act-2", "case_id": "VP-ACTIVITY", "action_type": "HUMAN_TAKEOVER", "status": "REQUESTED",
            "actor_type": "BANK_STAFF", "note": "담당자 인계", "created_at": "2026-09-02T01:00:00+00:00",
        }
        verification = self.client.patch("/api/cases/VP-ACTIVITY/verifications/ver-1", json={"expected_version": 1, "status": "COMPLETED"})
        takeover = self.client.post("/api/cases/VP-ACTIVITY/takeover", json={"note": "담당자 인계"})
        self.assertEqual(verification.status_code, 200)
        self.assertEqual(verification.json()["status"], "COMPLETED")
        self.assertEqual(takeover.status_code, 201)
        self.assertEqual(takeover.json()["action_type"], "HUMAN_TAKEOVER")
        self.assertTrue(takeover.headers.get("x-request-id"))

    def test_voice_session_transcript_and_final_report_contracts(self) -> None:
        self.repository.create_voice_session.return_value = {
            "session_id": "voice-1", "case_id": "VP-ACTIVITY", "status": "REQUESTED", "participants": ["CUSTOMER", "BANK_STAFF"],
            "started_at": None, "ended_at": None, "created_at": "2026-09-02T01:00:00+00:00",
        }
        self.repository.update_voice_session.return_value = {**self.repository.create_voice_session.return_value, "status": "ACTIVE", "started_at": "2026-09-02T01:01:00+00:00"}
        self.repository.append_transcript.return_value = {"segment_id": "seg-1", "session_id": "voice-1", "case_id": "VP-ACTIVITY", "speaker": "CUSTOMER", "content": "상담 내용", "started_at": None, "created_at": "2026-09-02T01:01:00+00:00"}
        self.repository.finalize_report.return_value = {"report_id": "final-VP-ACTIVITY", "case_id": "VP-ACTIVITY", "report_version": 1, "status": "FINAL", "sections": [], "created_at": "2026-09-02T01:02:00+00:00"}
        voice = self.client.post("/api/cases/VP-ACTIVITY/voice-sessions", json={"participants": ["CUSTOMER", "BANK_STAFF"]})
        active = self.client.patch("/api/cases/VP-ACTIVITY/voice-sessions/voice-1", json={"status": "ACTIVE"})
        transcript = self.client.post("/api/cases/VP-ACTIVITY/voice-sessions/voice-1/transcript", json={"speaker": "CUSTOMER", "content": "상담 내용"})
        final = self.client.post("/api/cases/VP-ACTIVITY/reports/finalize", json={"expected_version": 1, "note": "종료"})
        self.assertEqual([voice.status_code, active.status_code, transcript.status_code, final.status_code], [201, 200, 201, 200])
        self.assertEqual(final.json()["status"], "FINAL")

    def test_bundle_contains_only_case_scoped_resources_and_cursor(self) -> None:
        self.repository.get.return_value = BUNDLE_CASE
        self.repository.list_messages.return_value = [{
            "message_id": "msg-1", "case_id": "VP-ACTIVITY", "actor_type": "CUSTOMER", "content": "test", "created_at": "2026-09-02T01:00:00+00:00",
        }]
        self.repository.list_actions.return_value = []
        self.repository.list_verifications.return_value = [
            {
                "verification_task_id": "ver-public", "case_id": "VP-ACTIVITY", "claim": "검찰청 사칭 주장", "target": "서울지검",
                "status": "COMPLETED", "version": 2, "result_summary": "공식 확인 결과 해당 연락은 기관 발신이 아닙니다.",
                "evidence_url": "https://internal.example/evidence", "verified_by": "검증 담당자", "rag_source": "내부 문서",
                "customer_visible": True, "created_at": "2026-09-02T01:00:00+00:00", "updated_at": "2026-09-02T01:03:00+00:00",
            },
            {
                "verification_task_id": "ver-private", "case_id": "VP-ACTIVITY", "claim": "내부 확인", "target": "내부 대상",
                "status": "COMPLETED", "version": 2, "result_summary": "내부 전용 결과", "customer_visible": False,
                "created_at": "2026-09-02T01:00:00+00:00", "updated_at": "2026-09-02T01:04:00+00:00",
            },
        ]
        self.repository.list_events.return_value = [{
            "event_id": 7, "case_id": "VP-ACTIVITY", "event_type": "MESSAGE_ADDED", "actor_type": "CUSTOMER",
            "payload": {"message_id": "msg-1"}, "occurred_at": "2026-09-02T01:00:00+00:00",
        }]

        response = self.client.get("/api/cases/VP-ACTIVITY/bundle?view=customer")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["case"]["case_id"], "VP-ACTIVITY")
        self.assertEqual(response.json()["recent_messages"][0]["message_id"], "msg-1")
        self.assertIsNone(response.json()["cursor"])
        self.assertEqual(response.json()["questions"], [])
        self.assertEqual(response.json()["verification_tasks"], [])
        self.assertEqual(response.json()["customer_verification_results"], [{
            "verification_task_id": "ver-public", "target": "서울지검",
            "result_summary": "공식 확인 결과 해당 연락은 기관 발신이 아닙니다.",
            "published_at": "2026-09-02T01:03:00+00:00",
        }])
        self.assertNotIn("evidence_url", response.json()["customer_verification_results"][0])
        self.assertNotIn("rag_source", response.json()["customer_verification_results"][0])

    def test_customer_question_card_projection_keeps_only_safe_fields(self) -> None:
        projection = to_public_customer_question_view({
            "question_id": "cq-1", "case_id": "VP-ACTIVITY",
            "question_text": "이미 송금한 금액이 있나요?", "priority": "P0", "status": "ASKED", "sequence": 1,
            "options": ["없음", "있음", "잘 모르겠어요"],
            "customer_explanation": "안전을 위해 피해 발생 여부를 먼저 확인합니다.",
            "answer_mode": "CHOICE_OR_TEXT", "allow_free_text": True,
            "answered_at": "2026-09-02T01:05:00+00:00", "answer_text": "있음",
            "source": "BANK_SELECTED", "reason": "내부 판단 사유", "requested_by": "은행 직원",
        }).model_dump(mode="json")

        self.assertEqual(projection["customer_explanation"], "안전을 위해 피해 발생 여부를 먼저 확인합니다.")
        self.assertEqual(projection["options"], ["없음", "있음", "잘 모르겠어요"])
        self.assertTrue(projection["allow_free_text"])
        self.assertEqual(projection["answer_text"], "있음")
        self.assertNotIn("reason", projection)
        self.assertNotIn("requested_by", projection)

    def test_customer_answer_is_persisted_for_receipt_card_restoration(self) -> None:
        self.repository.append_message.return_value = {
            "message_id": "msg-answer", "case_id": "VP-ACTIVITY", "actor_type": "CUSTOMER",
            "content": "있음", "created_at": "2026-09-02T01:05:00+00:00",
        }
        self.repository.answer_customer_question.return_value = {
            "question_id": "cq-1", "case_id": "VP-ACTIVITY", "source": "BANK_SELECTED",
            "target_field": "victim_transfer_status", "question_text": "이미 송금한 금액이 있나요?",
            "reason": "피해 여부 확인", "priority": "P0", "status": "ANSWERED", "sequence": 1,
            "requested_by": "은행 직원", "asked_at": "2026-09-02T01:04:00+00:00",
            "answered_at": "2026-09-02T01:05:00+00:00", "answer_text": "있음",
        }
        self.repository.propose_case_fact.return_value = {}
        self.repository.dispatch_next_customer_question.return_value = None

        response = self.client.post("/api/cases/VP-ACTIVITY/customer-questions/cq-1/answer", json={
            "raw_answer": "있음", "actor_user_id": "customer-1", "actor_display_name": "고객",
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["answer_text"], "있음")
        self.repository.answer_customer_question.assert_awaited_once_with(
            "VP-ACTIVITY", "cq-1", "msg-answer", "있음"
        )

    def test_customer_emergency_updates_case_and_alerts_ai_private_only(self) -> None:
        self.repository.get.return_value = {**CASE, "version": 3}
        self.repository.list_messages.return_value = []
        self.repository.update_case.return_value = {**CASE, "version": 4, "mode": "RECOVERY", "victim_transfer_status": "YES"}
        acknowledgement = {
            "message_id": "msg-customer-emergency", "case_id": "VP-ACTIVITY", "actor_type": "CUSTOMER",
            "actor_user_id": "customer-1", "actor_display_name": "고객", "actor_role": "CUSTOMER",
            "content": "이미 사기 피해를 입었습니다. 피해구제 안내를 확인합니다.", "channel": "CUSTOMER",
            "audience": "CUSTOMER", "visibility": "CUSTOMER", "message_kind": "CHAT",
            "private_owner_user_id": None, "mentions": [], "created_at": "2026-09-03T10:00:00+09:00",
        }
        alert = {
            "message_id": "msg-emergency", "case_id": "VP-ACTIVITY", "actor_type": "BANK_AGENT",
            "actor_user_id": "case-copilot", "actor_display_name": "CaseCopilot 긴급 알림", "actor_role": "BANK_AGENT",
            "content": "고객이 직접 사기 피해 발생을 신고했습니다.", "channel": "AI_INTERNAL",
            "audience": "BANK_INTERNAL", "visibility": "AI_PRIVATE", "message_kind": "SYSTEM_EVENT",
            "private_owner_user_id": None, "mentions": ["CaseCopilot"],
            "created_at": "2026-09-03T10:00:00+09:00",
        }
        self.repository.append_message.side_effect = [acknowledgement, alert]

        response = self.client.post("/api/cases/VP-ACTIVITY/customer-emergency", json={
            "actor_user_id": "customer-1", "actor_display_name": "고객",
        })

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["channel"], "AI_INTERNAL")
        self.assertEqual(response.json()["visibility"], "AI_PRIVATE")
        self.repository.update_case.assert_awaited_once_with("VP-ACTIVITY", 3, {
            "victim_transfer_status": "YES", "mode": "RECOVERY",
        })
        self.assertEqual(self.repository.append_message.await_count, 2)
        acknowledgement_record = self.repository.append_message.await_args_list[0].args[1]
        alert_record = self.repository.append_message.await_args_list[1].args[1]
        self.assertEqual(acknowledgement_record["channel"], "CUSTOMER")
        self.assertEqual(alert_record["channel"], "AI_INTERNAL")
        self.assertIsNone(alert_record["private_owner_user_id"])
        self.assertNotEqual(alert_record["channel"], "TEAM")

    def test_customer_emergency_reuses_existing_alert_without_duplicates(self) -> None:
        acknowledgement = {
            "message_id": "msg-customer-emergency", "case_id": "VP-ACTIVITY", "actor_type": "CUSTOMER",
            "actor_user_id": "customer-1", "actor_display_name": "고객", "actor_role": "CUSTOMER",
            "content": "이미 사기 피해를 입었습니다. 피해구제 안내를 확인합니다.", "channel": "CUSTOMER",
            "audience": "CUSTOMER", "visibility": "CUSTOMER", "message_kind": "CHAT",
            "private_owner_user_id": None, "mentions": [], "created_at": "2026-09-03T10:00:00+09:00",
        }
        alert = {
            "message_id": "msg-emergency", "case_id": "VP-ACTIVITY", "actor_type": "BANK_AGENT",
            "actor_user_id": "case-copilot", "actor_display_name": "CaseCopilot 긴급 알림", "actor_role": "BANK_AGENT",
            "content": "고객이 직접 사기 피해 발생을 신고했습니다.", "channel": "AI_INTERNAL",
            "audience": "BANK_INTERNAL", "visibility": "AI_PRIVATE", "message_kind": "SYSTEM_EVENT",
            "private_owner_user_id": None, "mentions": ["CaseCopilot"], "created_at": "2026-09-03T10:00:00+09:00",
        }
        self.repository.get.return_value = {**CASE, "version": 4, "mode": "RECOVERY", "victim_transfer_status": "YES"}
        self.repository.list_messages.return_value = [acknowledgement, alert]

        response = self.client.post("/api/cases/VP-ACTIVITY/customer-emergency", json={
            "actor_user_id": "customer-1", "actor_display_name": "고객",
        })

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["message_id"], "msg-emergency")
        self.repository.append_message.assert_not_awaited()
        self.repository.update_case.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
