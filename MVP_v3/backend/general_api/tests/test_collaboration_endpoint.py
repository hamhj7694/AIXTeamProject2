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
        for name in ("facts", "gaps", "suggestions", "tasks", "decisions", "requests"):
            setattr(self.repository, f"_context_v2_{name}", {})
        self.repository.get.return_value = {
            "case_id": "CASE-1", "status": "TRIAGE", "initial_brief": "brief",
        }
        self.repository.list_members.return_value = [
            {
                "case_id": "CASE-1", "user_id": "staff-owner", "display_name": "김태환",
                "role": "CASE_OWNER", "status": "ACTIVE",
            },
            {
                "case_id": "CASE-1", "user_id": "staff-reviewer", "display_name": "은행 담당자",
                "role": "REVIEWER", "status": "ACTIVE",
            },
        ]
        self.repository.list_verifications.return_value = []
        self.repository.list_case_facts.return_value = []
        self.repository.list_actions.return_value = []
        self.repository.list_attachments.return_value = []
        self.repository.list_messages.return_value = []
        self.repository.list_customer_questions.return_value = []
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
        general_main.service.ai_client.generate_case_copilot_reply = AsyncMock(return_value={
            "content": "reply", "model_mode": "gpt-4o-mini",
        })

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
        self.assertEqual(copilot.json()["model_mode"], "gpt-4o-mini")
        payload = general_main.service.ai_client.generate_case_copilot_reply.await_args.args[0]
        self.assertEqual(payload["primary_assignee"], "김태환")
        self.assertEqual(payload["participants"], ["김태환 (메인 담당자)", "은행 담당자 (검토자)"])

    def test_customer_ai_reply_uses_customer_safe_mode_and_public_channel(self) -> None:
        self.repository.list_messages.return_value = [{
            "actor_display_name": "고객", "content": "이미 개인정보를 제공했어요.",
            "visibility": "CUSTOMER", "channel": "CUSTOMER",
        }]
        self.repository.list_customer_questions.return_value = [{
            "question_text": "개인정보를 제공했나요?", "answer_text": "예", "status": "ANSWERED",
        }, {
            'case_id': 'CASE-1', 'question_text': '인증번호를 제공하셨나요?', 'status': 'ASKED',
            'customer_explanation': '인증정보 제공 여부만 확인합니다.', 'options': ['제공함', '제공하지 않음'],
            'reason': '비공개 내부 판단', 'requested_by': '비공개 직원 식별자',
        }, {
            'case_id': 'CASE-1', 'question_text': '아직 공개하지 않은 질문', 'status': 'PENDING',
        }, {
            'case_id': 'OTHER-CASE', 'question_text': '다른 사건 질문', 'status': 'ASKED',
        }]
        self.repository.append_message.return_value = {
            "message_id": "msg-customer-ai-1", "case_id": "CASE-1", "actor_type": "CUSTOMER_AGENT",
            "actor_user_id": "customer-agent", "actor_display_name": "안전 상담 AI", "actor_role": "CUSTOMER_AGENT",
            "content": "추가 정보 제공을 멈추고 공식 은행 고객센터에 연락해 주세요.",
            "channel": "CUSTOMER", "audience": "CUSTOMER", "visibility": "CUSTOMER",
            "message_kind": "AI_RESPONSE", "mentions": [], "attachments": [],
            "created_at": "2026-09-02T01:00:00+00:00",
        }

        response = self.client.post("/api/cases/CASE-1/ai/customer-replies", json={
            "prompt": "이제 어떻게 해야 하나요?", "requester_user_id": "customer-1", "requester_display_name": "고객",
            "reply_to_message_id": "msg-customer-1",
        })

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["channel"], "CUSTOMER")
        payload = general_main.service.ai_client.generate_case_copilot_reply.await_args.args[0]
        self.assertEqual(payload["assistant_mode"], "CUSTOMER_SUPPORT")
        self.assertEqual(payload["pending_actions"], [])
        self.assertEqual(payload["unresolved_verifications"], [])
        self.assertEqual(payload['customer_service_questions'], [{
            'source': 'CSR_QUESTION_CARD', 'status': 'ASKED', 'question_text': '인증번호를 제공하셨나요?',
            'customer_explanation': '인증정보 제공 여부만 확인합니다.', 'options': ['제공함', '제공하지 않음'],
        }])
        saved = self.repository.append_message.await_args.args[1]
        self.assertEqual(saved["reply_to_message_id"], "msg-customer-1")


if __name__ == "__main__":
    unittest.main()
