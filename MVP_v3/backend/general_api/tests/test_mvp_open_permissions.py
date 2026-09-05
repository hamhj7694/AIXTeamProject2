import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
import general_api.app.main as main
from general_api.app.domains.cases.repository import InMemoryCaseRepository


class MvpOpenPermissionsTest(unittest.TestCase):
    def setUp(self):
        self.repo = InMemoryCaseRepository()
        self.repo._records = [{"case_id": "VP-OPEN", "context_revision": 1}]
        self.repo._members = [
            {"case_id": "VP-OPEN", "user_id": "operator", "role": "CHAT_OPERATOR", "status": "ACTIVE"},
            {"case_id": "VP-OPEN", "user_id": "viewer", "role": "VIEWER", "status": "ACTIVE"},
        ]
        self.repo_patch = patch.object(main, "repository", self.repo)
        self.env_patch = patch.dict(os.environ, {"MVP_OPEN_PERMISSIONS": "1", "CASE_ADMIN_DELETE_PASSWORD": "test-admin-password"})
        self.repo_patch.start()
        self.env_patch.start()
        self.client = TestClient(main.app)
        self.base = "/api/cases/VP-OPEN/context-v2"

    def tearDown(self):
        self.client.close()
        self.env_patch.stop()
        self.repo_patch.stop()

    def test_all_human_workspace_roles_get_same_capabilities_without_member_mutation(self):
        before = [dict(m) for m in self.repo._members]
        for actor in ("operator", "viewer", "new-bank-user"):
            with self.subTest(actor=actor):
                response = self.client.get(f"{self.base}/workspace?actor_user_id={actor}")
                self.assertEqual(response.status_code, 200, response.text)
                self.assertTrue(response.json()["can_write"])
                self.assertTrue(response.json()["can_review"])
                self.assertEqual(response.json()["permissions_mode"], "MVP_OPEN")
        self.assertEqual(self.repo._members, before)

    def test_unregistered_staff_can_create_review_and_record_task_result(self):
        fact = self.client.post(f"{self.base}/facts?actor_user_id=new-bank-user", json={
            "client_request_id": "open-fact-0001", "semantic_key": "transfer.actual.status",
            "display_label": "실제 송금 여부", "value": {"status": "NO"}, "display_value": "송금하지 않음",
        })
        self.assertEqual(fact.status_code, 201, fact.text)
        url = f"{self.base}/facts/{fact.json()['fact_id']}/review?actor_user_id=viewer"
        result = self.client.patch(url, json={"expected_version": 1, "decision": "CONFIRM", "reason": "담당자 확인"})
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()["confirmed_by"], "viewer")
        self.assertEqual(self.client.patch(url, json={"expected_version": 1, "decision": "CONFIRM", "reason": "중복"}).status_code, 409)
        task = self.client.post(f"{self.base}/tasks?actor_user_id=viewer", json={
            "client_request_id": "open-task-0001", "task_type": "OTHER", "title": "자료 확인", "description": "내역 확인", "priority": "NORMAL",
        })
        self.assertEqual(task.status_code, 201, task.text)
        complete_url = f"{self.base}/tasks/{task.json()['task_id']}/complete?actor_user_id=operator"
        self.assertEqual(self.client.post(complete_url, json={"expected_version": 1}).status_code, 422)
        self.assertEqual(self.client.post(complete_url, json={"expected_version": 1, "result_summary": "자료 확인함"}).status_code, 200)

    def test_legacy_suggestion_buttons_work_without_review_role(self):
        self.repo._actions = [{"case_id": "VP-OPEN", "action_id": "legacy-ai", "action_type": "AI_CHECKLIST:P0:transfer_status", "status": "REQUESTED", "note": "실제 송금 확인"}]
        response = self.client.post(f"{self.base}/legacy-suggestions/legacy-ai/review?actor_user_id=operator", json={
            "expected_version": 1, "decision": "ACCEPT", "edited_title": "이체 기록 검토", "edited_description": "기록 확인",
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["created_task"]["title"], "이체 기록 검토")
        self.assertEqual(response.json()["created_task"]["status"], "TODO")

    def test_display_edit_persists_for_unregistered_user(self):
        url = "/api/cases/VP-OPEN/context-display"
        response = self.client.patch(url + "/SUMMARY?actor_user_id=new-bank-user", json={
            "expected_version": 0, "operation": "EDIT", "text": "직원 수정 내용",
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.client.get(url + "?actor_user_id=viewer").json()[0]["staff_text"], "직원 수정 내용")
        self.assertEqual(self.client.get(url + "?actor_user_id=mvp-v3-customer").json(), [])

    def test_customer_ai_identity_and_admin_secret_boundaries_remain(self):
        for actor in ("mvp-v3-customer", "customer-agent", "case-copilot", "system:context-ai"):
            with self.subTest(actor=actor):
                self.assertEqual(self.client.get(f"{self.base}/workspace?actor_user_id={actor}").status_code, 403)
        response = self.client.post('/api/cases/VP-OPEN/reports/finalize', json={"expected_version": 1, "password": "wrong", "note": ""})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"]["code"], "ADMIN_AUTH_FAILED")

    def test_runtime_config_is_minimal_and_flag_off_restores_role_checks(self):
        self.assertEqual(self.client.get('/api/runtime-config').json(), {"permissions_mode": "MVP_OPEN"})
        with patch.dict(os.environ, {"MVP_OPEN_PERMISSIONS": "0"}):
            self.assertEqual(self.client.get('/api/runtime-config').json(), {"permissions_mode": "ROLE_BASED"})
            self.assertFalse(self.client.get(f"{self.base}/workspace?actor_user_id=operator").json()["can_review"])
            self.assertEqual(self.client.get(f"{self.base}/workspace?actor_user_id=new-bank-user").status_code, 403)
        self.assertEqual(self.client.get('/api/cases/missing/context-v2/workspace?actor_user_id=new-bank-user').status_code, 404)
