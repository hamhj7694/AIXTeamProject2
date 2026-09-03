from __future__ import annotations

import unittest
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

import general_api.app.main as general_main


class CollaborationEndpointTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(general_main.app)
        self.original_repository = general_main.repository
        self.repository = AsyncMock()
        self.repository.get.return_value = {
            "case_id": "CASE-1", "status": "TRIAGE", "initial_brief": "brief",
        }
        self.repository.list_verifications.return_value = []
        self.repository.upsert_member.return_value = {
            "case_id": "CASE-1", "user_id": "staff-1", "display_name": "Operator",
            "role": "CHAT_OPERATOR", "status": "ACTIVE",
            "assigned_at": "2026-09-02T01:00:00+00:00", "updated_at": "2026-09-02T01:00:00+00:00",
        }
        self.repository.heartbeat_presence.return_value = {
            "case_id": "CASE-1", "user_id": "staff-1", "display_name": "Operator",
            "presence": "VIEWING", "channel": "TEAM", "last_seen_at": "2026-09-02T01:00:00+00:00",
            "expires_at": "2026-09-02T01:00:45+00:00",
        }
        self.repository.append_message.return_value = {
            "message_id": "msg-ai-1", "case_id": "CASE-1", "actor_type": "BANK_AGENT",
            "content": "reply", "channel": "AI_INTERNAL", "audience": "BANK_INTERNAL",
            "mentions": ["CaseCopilot"], "created_at": "2026-09-02T01:00:00+00:00",
        }
        general_main.repository = self.repository

    def tearDown(self) -> None:
        general_main.repository = self.original_repository
        self.client.close()

    def test_member_presence_and_explicit_copilot_contract(self) -> None:
        member = self.client.post("/api/cases/CASE-1/members", json={
            "user_id": "staff-1", "display_name": "Operator", "role": "CHAT_OPERATOR",
        })
        presence = self.client.post("/api/cases/CASE-1/presence/heartbeat", json={
            "user_id": "staff-1", "display_name": "Operator", "channel": "TEAM",
        })
        copilot = self.client.post("/api/cases/CASE-1/ai/invocations", json={
            "prompt": "@CaseCopilot summarize", "channel": "TEAM", "requester_user_id": "staff-1", "requester_display_name": "Operator",
        })

        self.assertEqual([member.status_code, presence.status_code, copilot.status_code], [201, 200, 201])
        self.assertEqual(member.json()["role"], "CHAT_OPERATOR")
        self.assertEqual(presence.json()["channel"], "TEAM")
        self.assertEqual(copilot.json()["channel"], "TEAM")
        self.assertEqual(copilot.json()["model_mode"], "MVP_DETERMINISTIC")


if __name__ == "__main__":
    unittest.main()
