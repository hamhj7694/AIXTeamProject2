from __future__ import annotations

import unittest
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

import general_api.app.main as general_main


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
            "actor_type": "CUSTOMER", "content": "송금하지 않았습니다.", "client_request_id": "web-1",
        })

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {
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
        self.repository.list_verifications.return_value = []
        self.repository.list_events.return_value = [{
            "event_id": 7, "case_id": "VP-ACTIVITY", "event_type": "MESSAGE_ADDED", "actor_type": "CUSTOMER",
            "payload": {"message_id": "msg-1"}, "occurred_at": "2026-09-02T01:00:00+00:00",
        }]

        response = self.client.get("/api/cases/VP-ACTIVITY/bundle?view=customer")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["case"]["case_id"], "VP-ACTIVITY")
        self.assertEqual(response.json()["recent_messages"][0]["message_id"], "msg-1")
        self.assertEqual(response.json()["cursor"], "7")
        self.assertEqual(response.json()["questions"], [])


if __name__ == "__main__":
    unittest.main()
