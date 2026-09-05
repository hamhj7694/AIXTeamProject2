import asyncio
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import general_api.app.main as main
from general_api.app.domains.cases.case_context_v2_repository import InMemoryCaseContextV2Repository
from general_api.app.domains.cases.repository import InMemoryCaseRepository


class CaseContextV2EndpointTest(unittest.TestCase):
    def setUp(self):
        self.permission_patch = patch.dict(os.environ, {"MVP_OPEN_PERMISSIONS": "0"})
        self.permission_patch.start()
        self.addCleanup(self.permission_patch.stop)
        self.repository = InMemoryCaseRepository()
        self.repository._records = [{"case_id": "VP-V2", "context_revision": 1}]
        self.repository._members = [
            {"case_id": "VP-V2", "user_id": "owner", "role": "CASE_OWNER", "status": "ACTIVE"},
            {"case_id": "VP-V2", "user_id": "operator", "role": "CHAT_OPERATOR", "status": "ACTIVE"},
            {"case_id": "VP-V2", "user_id": "viewer", "role": "VIEWER", "status": "ACTIVE"},
        ]
        self.patch = patch.object(main, "repository", self.repository)
        self.patch.start()
        self.client = TestClient(main.app)
        self.base = "/api/cases/VP-V2/context-v2"

    def tearDown(self):
        self.client.close()
        self.patch.stop()

    def create_fact(self):
        return self.client.post(f"{self.base}/facts?actor_user_id=operator", json={
            "client_request_id": "request-fact-001",
            "semantic_key": "transfer.actual.status",
            "display_label": "실제 송금 여부",
            "value": {"status": "YES"},
            "display_value": "고객이 송금했다고 진술함",
            "evidence_refs": [{"type": "MESSAGE", "id": "msg-1"}],
        })

    def test_workspace_read_keeps_legacy_records_separate_and_does_not_write(self):
        self.repository._actions = [
            {"case_id": "VP-V2", "action_id": "old-ai", "action_type": "AI_CHECKLIST:P0:personal_info_shared", "status": "REQUESTED", "note": "personal_info_shared 확인"},
            {"case_id": "VP-V2", "action_id": "old-staff", "action_type": "STAFF_JUDGMENT", "status": "COMPLETED", "note": "기존 판단 또는 업무"},
        ]
        self.repository._case_facts = [{"case_id": "VP-V2", "fact_id": "old-fact", "field": "transfer_status", "value": "고객이 송금했다고 답함", "status": "PROPOSED"}]
        first = self.client.get(f"{self.base}/workspace?actor_user_id=operator")
        second = self.client.get(f"{self.base}/workspace?actor_user_id=operator")
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json(), second.json())
        data = first.json()
        self.assertEqual(data["confirmed_facts"], [])
        self.assertEqual(data["active_tasks"], [])
        self.assertEqual(data["recent_decisions"], [])
        self.assertEqual(data["legacy_facts"][0]["status"], "PROPOSED")
        self.assertEqual(data["legacy_suggestions"][0]["title"], "개인정보 제공 여부 확인")
        self.assertEqual(len(data["legacy_records"]), 1)
        self.assertTrue(data["can_write"])
        self.assertFalse(data["can_review"])
        self.assertEqual(len(self.repository._context_v2_history), 0)

    def test_legacy_suggestion_cannot_create_duplicate_tasks(self):
        self.repository._actions = [{"case_id": "VP-V2", "action_id": "old-ai", "action_type": "AI_CHECKLIST:P0:transfer_status", "status": "REQUESTED", "note": "실제 송금 내역 검토"}]
        url = f"{self.base}/legacy-suggestions/old-ai/review?actor_user_id=owner"
        payload = {"expected_version": 1, "decision": "ACCEPT", "edited_title": "원장 확인"}
        first = self.client.post(url, json=payload)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()["created_task"]["status"], "TODO")
        repeated = self.client.post(url, json=payload)
        self.assertEqual(repeated.status_code, 409, repeated.text)
        workspace = self.client.get(f"{self.base}/workspace?actor_user_id=owner").json()
        self.assertEqual(len(workspace["active_tasks"]), 1)
        self.assertEqual(workspace["legacy_suggestions"], [])
        self.assertEqual(len(workspace["reviewed_suggestions"]), 1)

    def test_workspace_requires_case_membership(self):
        response = self.client.get(f"{self.base}/workspace?actor_user_id=stranger")
        self.assertEqual(response.status_code, 403)

    def test_task_reopening_preserves_old_result_in_audit_history(self):
        created = self.client.post(f"{self.base}/tasks?actor_user_id=operator", json={
            "client_request_id": "reopen-task-test", "task_type": "OTHER", "title": "자료 확인",
            "description": "자료 대조", "priority": "NORMAL",
        }).json()
        completed = self.client.post(f"{self.base}/tasks/{created['task_id']}/complete?actor_user_id=owner", json={"expected_version": 1, "result_summary": "확인한 결과 기록"})
        self.assertEqual(completed.status_code, 200)
        workspace = self.client.get(f"{self.base}/workspace?actor_user_id=owner").json()
        self.assertEqual(len(workspace["archived_tasks"]), 1)
        reopened = self.client.patch(f"{self.base}/tasks/{created['task_id']}?actor_user_id=operator", json={"expected_version": 2, "status": "TODO", "description": "추가 자료 확인"})
        self.assertEqual(reopened.status_code, 200, reopened.text)
        self.assertEqual(reopened.json()["status"], "TODO")
        self.assertIsNone(reopened.json()["completed_at"])
        self.assertEqual(self.repository._context_v2_history[-1]["before"].result_summary, "확인한 결과 기록")

    def test_answered_legacy_gap_remains_review_required(self):
        self.repository._actions = [{"case_id": "VP-V2", "action_id": "old-ai", "action_type": "AI_CHECKLIST:P0:transfer_status", "status": "REQUESTED", "note": "송금 여부 검토"}]
        self.repository._customer_questions = [{"case_id": "VP-V2", "question_id": "q1", "sequence": 1, "target_field": "transfer_status", "status": "ANSWERED"}]
        data = self.client.get(f"{self.base}/workspace?actor_user_id=owner").json()
        self.assertEqual(data["legacy_gaps"][0]["status"], "STAFF_REVIEW_REQUIRED")
        self.assertEqual(data["confirmed_facts"], [])

    def test_staff_fact_is_proposed_until_reviewer_confirms_it(self):
        created = self.create_fact()
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["status"], "PROPOSED")
        self.assertEqual(created.json()["source_kind"], "STAFF_OBSERVATION")

        forbidden = self.client.patch(
            f"{self.base}/facts/{created.json()['fact_id']}/review?actor_user_id=operator",
            json={"expected_version": 1, "decision": "CONFIRM", "reason": "거래 내역 확인"},
        )
        self.assertEqual(forbidden.status_code, 403)

        confirmed = self.client.patch(
            f"{self.base}/facts/{created.json()['fact_id']}/review?actor_user_id=owner",
            json={"expected_version": 1, "decision": "CONFIRM", "reason": "거래 내역 확인"},
        )
        self.assertEqual(confirmed.status_code, 200, confirmed.text)
        self.assertEqual(confirmed.json()["status"], "CONFIRMED")
        self.assertEqual(confirmed.json()["confirmed_by"], "owner")

    def test_idempotency_and_version_conflict_are_enforced(self):
        first = self.create_fact()
        second = self.create_fact()
        self.assertEqual(first.json()["fact_id"], second.json()["fact_id"])
        reviewed = self.client.patch(
            f"{self.base}/facts/{first.json()['fact_id']}/review?actor_user_id=owner",
            json={"expected_version": 1, "decision": "REJECT", "reason": "근거 불충분"},
        )
        self.assertEqual(reviewed.status_code, 200)
        stale = self.client.patch(
            f"{self.base}/facts/{first.json()['fact_id']}/review?actor_user_id=owner",
            json={"expected_version": 1, "decision": "CONFIRM", "reason": "재검토"},
        )
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.json()["detail"]["current_version"], 2)

    def test_gap_resolution_requires_a_confirmed_fact(self):
        fact = self.create_fact().json()
        gap = self.client.post(f"{self.base}/gaps?actor_user_id=operator", json={
            "client_request_id": "request-gap-0001",
            "semantic_key": "transfer.actual.status",
            "title": "실제 송금 여부 확인",
            "reason": "피해 발생 여부 판단에 필요",
            "priority": "URGENT",
        })
        self.assertEqual(gap.status_code, 201, gap.text)
        unresolved = self.client.patch(
            f"{self.base}/gaps/{gap.json()['gap_id']}?actor_user_id=operator",
            json={"expected_version": 1, "status": "RESOLVED", "resolution_fact_id": fact["fact_id"]},
        )
        self.assertEqual(unresolved.status_code, 422)
        self.client.patch(
            f"{self.base}/facts/{fact['fact_id']}/review?actor_user_id=owner",
            json={"expected_version": 1, "decision": "CONFIRM", "reason": "거래 내역 확인"},
        )
        resolved = self.client.patch(
            f"{self.base}/gaps/{gap.json()['gap_id']}?actor_user_id=operator",
            json={"expected_version": 1, "status": "RESOLVED", "resolution_fact_id": fact["fact_id"]},
        )
        self.assertEqual(resolved.status_code, 200, resolved.text)
        self.assertEqual(resolved.json()["status"], "RESOLVED")

    def test_accepting_ai_suggestion_atomically_creates_staff_task(self):
        store = InMemoryCaseContextV2Repository(self.repository)
        suggestion = asyncio.run(store.propose_suggestion("VP-V2", {
            "suggestion_type": "TRANSACTION_REVIEW",
            "title": "송금 내역 확인",
            "rationale": "실제 피해 여부 확인이 필요합니다.",
            "priority": "URGENT",
            "dedupe_key": "transaction-review:transfer.actual.status",
        }))
        accepted = self.client.patch(
            f"{self.base}/suggestions/{suggestion.suggestion_id}/review?actor_user_id=owner",
            json={"expected_version": 1, "decision": "ACCEPT", "edited_title": "거래 원장 확인"},
        )
        self.assertEqual(accepted.status_code, 200, accepted.text)
        body = accepted.json()
        self.assertEqual(body["suggestion"]["status"], "ACCEPTED")
        self.assertEqual(body["created_task"]["source"], "AI_SUGGESTION_ACCEPTED")
        self.assertEqual(body["created_task"]["title"], "거래 원장 확인")
        self.assertEqual(body["suggestion"]["accepted_task_id"], body["created_task"]["task_id"])

        repeated = self.client.patch(
            f"{self.base}/suggestions/{suggestion.suggestion_id}/review?actor_user_id=owner",
            json={"expected_version": 1, "decision": "ACCEPT"},
        )
        self.assertEqual(repeated.status_code, 409)
        resources = self.client.get(f"{self.base}/resources?actor_user_id=owner").json()
        self.assertEqual(len(resources["tasks"]), 1)

    def test_task_completion_requires_result_and_reviewer(self):
        created = self.client.post(f"{self.base}/tasks?actor_user_id=operator", json={
            "client_request_id": "request-task-001",
            "task_type": "CUSTOMER_CONTACT",
            "title": "고객에게 송금 여부 확인",
            "description": "고객 진술을 확인하고 결과를 기록합니다.",
            "priority": "HIGH",
        })
        self.assertEqual(created.status_code, 201, created.text)
        task_id = created.json()["task_id"]
        forbidden = self.client.post(
            f"{self.base}/tasks/{task_id}/complete?actor_user_id=operator",
            json={"expected_version": 1, "result_summary": "고객 확인 완료"},
        )
        self.assertEqual(forbidden.status_code, 403)
        completed = self.client.post(
            f"{self.base}/tasks/{task_id}/complete?actor_user_id=owner",
            json={"expected_version": 1, "result_summary": "고객이 송금 사실을 확인함"},
        )
        self.assertEqual(completed.status_code, 200, completed.text)
        self.assertEqual(completed.json()["status"], "COMPLETED")
        self.assertEqual(completed.json()["completed_by"], "owner")

    def test_viewer_can_read_but_unrelated_user_cannot(self):
        self.assertEqual(self.client.get(f"{self.base}/resources?actor_user_id=outsider").status_code, 403)
        self.assertEqual(self.client.get(f"{self.base}/resources?actor_user_id=viewer").status_code, 200)
        denied_write = self.client.post(f"{self.base}/tasks?actor_user_id=viewer", json={
            "client_request_id": "request-viewer-01",
            "task_type": "OTHER", "title": "읽기 전용", "description": "생성되면 안 됨", "priority": "NORMAL",
        })
        self.assertEqual(denied_write.status_code, 403)


if __name__ == "__main__":
    unittest.main()
