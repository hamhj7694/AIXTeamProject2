from __future__ import annotations

import asyncio
import json
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

import general_api.app.main as general_main


class CaseSupportSnapshotEndpointTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(general_main.app)
        self.original_repository = general_main.repository
        self.original_ai_client = general_main.service.ai_client
        self.repository = AsyncMock()
        fixture = Path(__file__).resolve().parents[2] / "contracts" / "ai_internal" / "fixtures" / "diagnosis.high.v1.json"
        diagnosis = json.loads(fixture.read_text(encoding="utf-8"))["response"]
        # 실제 신규 Case는 송금 여부를 UNKNOWN으로 생성한다. 이 상태에서만
        # 송금 여부 후보가 아직 처리되지 않은 P0 질문으로 남는다.
        self.repository.get.return_value = {
            "case_id": "CASE-AI-1", "diagnosis": diagnosis,
            "victim_transfer_status": "UNKNOWN",
        }
        self.repository.list_case_facts.return_value = []
        self.repository.list_customer_questions.return_value = []
        self.repository.list_verifications.return_value = []
        self.repository.list_actions.return_value = []
        self.repository.list.return_value = []
        self.repository.queue_customer_questions.return_value = []
        self.repository.dispatch_next_customer_question.return_value = None
        general_main._proactive_case_revisions.clear()
        general_main.repository = self.repository
        general_main.service.ai_client.build_case_support_snapshot = AsyncMock(return_value={
            "case_id": "CASE-AI-1",
            "case_brief": {"summary": "AI 요약", "incident_type": "기관 사칭", "risk_level": "HIGH", "risk_score": 92.0, "next_checks": ["송금 여부 확인"]},
            "case_context": {"key_signals": ["송금 요구"], "offender_claims": ["검찰 사칭"], "offender_demands": ["안전계좌 이체 요구"]},
            "recommended_questions": [{"question_id": "q-transfer", "target_field": "transfer_status", "question": "송금하셨나요?", "reason": "피해 여부 확인", "priority": "P0"}],
            "unresolved_items": [{"target_field": "transfer_status", "description": "송금 여부", "priority": "P0"}],
            "warnings": [],
        })

    def tearDown(self) -> None:
        general_main.repository = self.original_repository
        general_main.service.ai_client = self.original_ai_client
        general_main._proactive_case_revisions.clear()
        self.client.close()

    def test_maps_ai_snapshot_to_public_screen_contract(self) -> None:
        response = self.client.get("/api/cases/CASE-AI-1/ai/case-support")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["case_brief"]["summary"], "AI 요약")
        self.assertEqual(response.json()["case_context"]["key_signals"], ["송금 요구"])
        self.assertEqual(response.json()["case_context"]["offender_claims"], ["검찰 사칭"])
        self.assertEqual(response.json()["case_context"]["offender_demands"], ["안전계좌 이체 요구"])
        self.assertEqual(response.json()["recommended_questions"][0]["question_text"], "송금하셨나요?")
        self.assertNotIn("evidence_refs", response.json()["recommended_questions"][0])

    def test_uses_deterministic_candidates_when_ai_is_unavailable(self) -> None:
        general_main.service.ai_client.build_case_support_snapshot = AsyncMock(side_effect=general_main.AiServiceError("AI 서버 연결 실패"))

        response = self.client.get("/api/cases/CASE-AI-1/customer-question-candidates")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json())
        self.assertEqual(response.json()[0]["question_id"], "candidate-victim_transfer_status")

    def test_ai_candidate_is_filtered_when_target_field_was_already_answered(self) -> None:
        self.repository.list_customer_questions.return_value = [{
            "question_id": "old-custom-id", "target_field": "transfer_status",
            "question_text": "송금하셨나요?", "status": "ANSWERED", "answer_text": "아니요",
        }]

        response = self.client.get("/api/cases/CASE-AI-1/customer-question-candidates")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
        sent_context = general_main.service.ai_client.build_case_support_snapshot.await_args.args[0]["question_context"]
        self.assertEqual(sent_context["answered_question_fields"], ["transfer_status"])

    def test_known_case_transfer_status_is_not_recommended_again(self) -> None:
        self.repository.get.return_value["victim_transfer_status"] = "YES"

        response = self.client.get("/api/cases/CASE-AI-1/ai/case-support")

        self.assertEqual(response.status_code, 200)
        sent_context = general_main.service.ai_client.build_case_support_snapshot.await_args.args[0]["question_context"]
        self.assertIn("transfer_status", sent_context["confirmed_fields"])

    def test_sends_latest_case_work_state_to_ai_snapshot(self) -> None:
        self.repository.list_customer_questions.return_value = [{
            "question_id": "q-live", "target_field": "transfer_status",
            "question_text": "실제 송금하셨나요?", "priority": "P0",
            "status": "ANSWERED", "answer_text": "이미 송금했어요",
        }]
        self.repository.list_case_facts.return_value = [{
            "fact_id": "fact-live", "field": "transfer_status", "value": "이미 송금했어요",
            "status": "PROPOSED",
        }]
        self.repository.list_verifications.return_value = [{
            "verification_task_id": "verification-live", "target": "서울중앙지검",
            "claim": "검찰 사칭 여부", "status": "IN_PROGRESS", "result_summary": None,
        }]
        self.repository.list_actions.return_value = [{
            "action_id": "action-live", "action_type": "PAYMENT_HOLD_REVIEW",
            "status": "IN_PROGRESS", "note": "지급정지 가능 여부 확인",
        }]

        response = self.client.get("/api/cases/CASE-AI-1/ai/case-support")

        self.assertEqual(response.status_code, 200)
        sent = general_main.service.ai_client.build_case_support_snapshot.await_args.args[0]
        self.assertEqual(sent["questions"][0]["answer_text"], "이미 송금했어요")
        self.assertEqual(sent["facts"][0]["status"], "PROPOSED")
        self.assertEqual(sent["verifications"][0]["status"], "IN_PROGRESS")
        self.assertEqual(sent["actions"][0]["action_type"], "PAYMENT_HOLD_REVIEW")

    def test_autonomous_agent_queues_only_allowlisted_p0_questions(self) -> None:
        general_main.service.ai_client.build_case_support_snapshot.return_value = {
            "case_id": "CASE-AI-1",
            "case_brief": {"summary": "AI 요약", "incident_type": "기관 사칭", "risk_level": "HIGH", "risk_score": 92.0, "next_checks": []},
            "recommended_questions": [
                {"question_id": "q-transfer", "target_field": "transfer_status", "question": "송금하셨나요?", "reason": "긴급 피해 확인", "priority": "P0"},
                {"question_id": "q-org", "target_field": "claimed_organization", "question": "어느 기관인가요?", "reason": "기관 확인", "priority": "P0"},
                {"question_id": "q-purpose", "target_field": "transfer_purpose", "question": "송금 목적은 무엇인가요?", "reason": "맥락 확인", "priority": "P1"},
            ],
            "unresolved_items": [], "warnings": [],
        }

        response = self.client.post("/api/cases/CASE-AI-1/ai/customer-questions/ensure")

        self.assertEqual(response.status_code, 200)
        queued = self.repository.queue_customer_questions.await_args.args[1]
        self.assertEqual([item["target_field"] for item in queued], ["transfer_status"])
        self.assertEqual(queued[0]["source"], "CUSTOMER_AGENT")

    def test_autonomous_agent_skips_ai_when_all_safety_fields_are_already_handled(self) -> None:
        self.repository.list_customer_questions.return_value = [
            {
                "question_id": f"q-{field}", "target_field": field,
                "question_text": field, "status": "ANSWERED",
            }
            for field in general_main.AUTONOMOUS_P0_QUESTION_FIELDS
        ]

        response = self.client.post("/api/cases/CASE-AI-1/ai/customer-questions/ensure")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
        general_main.service.ai_client.build_case_support_snapshot.assert_not_awaited()
        self.repository.queue_customer_questions.assert_not_awaited()

    def test_autonomous_agent_does_not_queue_a_confirmed_database_fact(self) -> None:
        self.repository.list_case_facts.return_value = [{
            "fact_id": "fact-personal-info", "field": "personal_information_exposure",
            "value": "YES", "status": "CONFIRMED",
        }]
        general_main.service.ai_client.build_case_support_snapshot.return_value["recommended_questions"] = [{
            "question_id": "q-personal-info",
            "target_field": "personal_information_exposure",
            "question": "Was personal information shared?",
            "reason": "Safety check",
            "priority": "P0",
        }]

        response = self.client.post("/api/cases/CASE-AI-1/ai/customer-questions/ensure")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
        self.repository.queue_customer_questions.assert_not_awaited()

    def test_autonomous_agent_does_not_reask_known_case_transfer_status(self) -> None:
        self.repository.get.return_value["victim_transfer_status"] = "YES"

        response = self.client.post("/api/cases/CASE-AI-1/ai/customer-questions/ensure")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
        self.repository.queue_customer_questions.assert_not_awaited()

    def test_revision_scan_runs_without_a_frontend_question_request(self) -> None:
        self.repository.list.return_value = [{
            "case_id": "CASE-AI-1", "status": "TRIAGE", "mode": "PREVENT",
            "updated_at": "2026-09-04T00:00:00+00:00",
        }]

        reconciled = asyncio.run(general_main.reconcile_changed_cases_once())

        self.assertEqual(reconciled, 1)
        self.repository.queue_customer_questions.assert_awaited_once()
        self.assertIn("CASE-AI-1", general_main._proactive_case_revisions)

    def test_ai_checklist_is_persisted_once_even_after_it_is_completed(self) -> None:
        snapshot = general_main.to_public_case_support_snapshot("CASE-AI-1", {
            "case_id": "CASE-AI-1",
            "recommended_questions": [],
            "unresolved_items": [{
                "target_field": "transfer_status",
                "description": "실제 송금 여부를 확인하세요.",
                "priority": "P0",
            }],
            "warnings": [],
        }, available=True)
        self.repository.list_actions.return_value = []

        asyncio.run(general_main.sync_ai_checklist_items("CASE-AI-1", snapshot))

        record = self.repository.create_action.await_args.args[1]
        self.assertEqual(record["action_type"], "AI_CHECKLIST:P0:transfer_status")
        self.repository.create_action.reset_mock()
        self.repository.list_actions.return_value = [{
            "action_id": "act-ai", "action_type": record["action_type"],
            "status": "COMPLETED", "note": record["note"],
        }]

        asyncio.run(general_main.sync_ai_checklist_items("CASE-AI-1", snapshot))

        self.repository.create_action.assert_not_awaited()

    def test_proposed_fact_becomes_staff_checklist_even_when_ai_is_unavailable(self) -> None:
        snapshot = general_main.PublicCaseSupportSnapshotResponse(
            case_id="CASE-AI-1", available=False, warnings=["AI unavailable"],
        )
        self.repository.list_actions.return_value = []
        self.repository.list_case_facts.return_value = [{
            "fact_id": "fact-auth", "field": "authentication_information_exposure",
            "value": "제공했어요", "status": "PROPOSED",
        }]

        asyncio.run(general_main.sync_ai_checklist_items("CASE-AI-1", snapshot))

        record = self.repository.create_action.await_args.args[1]
        self.assertEqual(record["action_type"], "AI_CHECKLIST:P0:authentication_information_exposure")
        self.assertIn("사실로 확정할지", record["note"])


if __name__ == "__main__":
    unittest.main()
