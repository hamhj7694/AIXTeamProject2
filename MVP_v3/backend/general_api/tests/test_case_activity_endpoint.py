from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

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

FINAL_AI_REPORT = {
    "title": "보이스피싱 대응 최종 결과 보고서",
    "executive_summary": "기관 사칭 의심 사건의 확인 및 대응 결과를 정리했습니다.",
    "incident_summary": "고객에게 기관을 사칭한 연락과 송금 요구가 있었습니다.",
    "customer_impact_summary": "송금 여부는 확인되지 않았고 개인정보 노출 여부를 검토 중입니다.",
    "verified_facts": ["고객 진술을 접수했습니다."],
    "verification_results": ["등록된 기관 확인 결과가 없습니다."],
    "actions_taken": ["추가 송금 중단을 안내했습니다."],
    "unresolved_items": ["실제 송금 여부 확인"],
    "decision_basis": ["담당자의 종결 메모"],
    "resolution": "담당자 검토를 거쳐 사건 대응을 종결했습니다.",
    "follow_up": ["추가 연락이 오면 공식 채널로 재확인합니다."],
    "cautions": ["실제 금융 조치 완료 여부는 별도로 확인해야 합니다."],
    "model_mode": "test-model",
}


class CaseActivityEndpointTest(unittest.TestCase):
    def setUp(self) -> None:
        self.admin_env = patch.dict("os.environ", {"CASE_ADMIN_DELETE_PASSWORD": "test-admin"})
        self.admin_env.start()
        self.client = TestClient(general_main.app)
        self.original_repository = general_main.repository
        self.repository = AsyncMock()
        for name in ("facts", "gaps", "suggestions", "tasks", "decisions", "requests"):
            setattr(self.repository, f"_context_v2_{name}", {})
        self.repository.get.return_value = CASE
        self.repository.get_voice_session.return_value = None
        self.repository.list_case_facts.return_value = []
        self.repository.list_verifications.return_value = []
        self.repository.list_actions.return_value = []
        self.repository.list_messages.return_value = []
        self.repository.list_customer_questions.return_value = []
        general_main.repository = self.repository
        self.ai_report_patch = patch.object(
            general_main.service.ai_client,
            "generate_final_report",
            new=AsyncMock(return_value=FINAL_AI_REPORT),
        )
        self.generate_final_report = self.ai_report_patch.start()

    def tearDown(self) -> None:
        general_main.repository = self.original_repository
        self.ai_report_patch.stop()
        self.client.close()
        self.admin_env.stop()

    def test_create_message_returns_public_message(self) -> None:
        self.repository.append_message.return_value = {
            "message_id": "msg-1", "case_id": "VP-ACTIVITY", "actor_type": "CUSTOMER",
            "actor_user_id": "customer-1", "actor_display_name": "고객",
            "content": "송금하지 않았습니다.", "client_request_id": "web-1", "created_at": "2026-09-02T01:00:00+00:00",
        }

        response = self.client.post("/api/cases/VP-ACTIVITY/messages", json={
            "actor_type": "CUSTOMER", "actor_user_id": "customer-1", "actor_display_name": "고객",
            "content": "송금하지 않았습니다.", "client_request_id": "web-1",
        })

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["actor_user_id"], "customer-1")
        self.assertEqual(response.json()["actor_display_name"], "고객")
        self.assertEqual(response.json()["channel"], "CUSTOMER")
        self.assertEqual(response.json()["audience"], "CUSTOMER")
        self.assertEqual(response.json()["mentions"], [])
        self.assertIsNone(response.json()["reply_to_message_id"])
        self.assertEqual(response.json()["client_request_id"], "web-1")
        self.assertEqual({key: response.json()[key] for key in ("message_id", "case_id", "actor_type", "content", "created_at")}, {
            "message_id": "msg-1", "case_id": "VP-ACTIVITY", "actor_type": "CUSTOMER",
            "content": "송금하지 않았습니다.", "created_at": "2026-09-02T01:00:00+00:00",
        })

    def test_create_message_reuses_same_client_request(self) -> None:
        existing = {
            "message_id": "msg-existing", "case_id": "VP-ACTIVITY", "actor_type": "CUSTOMER",
            "actor_user_id": "customer-1", "actor_display_name": "고객", "content": "중복 방지",
            "client_request_id": "same-request", "created_at": "2026-09-02T01:00:00+00:00",
        }
        self.repository.find_message_by_client_request_id.return_value = existing

        response = self.client.post("/api/cases/VP-ACTIVITY/messages", json={
            "actor_type": "CUSTOMER", "actor_user_id": "customer-1", "actor_display_name": "고객",
            "content": "중복 방지", "client_request_id": "same-request",
        })

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["message_id"], "msg-existing")
        self.repository.append_message.assert_not_awaited()

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

    def test_checklist_action_can_be_completed_and_reopened(self) -> None:
        self.repository.update_action.side_effect = [
            {
                "action_id": "act-check", "case_id": "VP-ACTIVITY",
                "action_type": "STAFF_JUDGMENT", "status": "COMPLETED",
                "actor_type": "BANK_STAFF", "note": "지급정지 가능 여부 확인",
                "created_at": "2026-09-02T01:00:00+00:00",
                "updated_at": "2026-09-02T01:01:00+00:00", "updated_by": "은행 담당자",
            },
            {
                "action_id": "act-check", "case_id": "VP-ACTIVITY",
                "action_type": "STAFF_JUDGMENT", "status": "REQUESTED",
                "actor_type": "BANK_STAFF", "note": "지급정지 가능 여부 확인",
                "created_at": "2026-09-02T01:00:00+00:00",
                "updated_at": "2026-09-02T01:02:00+00:00", "updated_by": "은행 담당자",
            },
        ]

        completed = self.client.patch("/api/cases/VP-ACTIVITY/actions/act-check", json={
            "status": "COMPLETED", "updated_by": "은행 담당자",
        })
        reopened = self.client.patch("/api/cases/VP-ACTIVITY/actions/act-check", json={
            "status": "REQUESTED", "updated_by": "은행 담당자",
        })

        self.assertEqual(completed.status_code, 200)
        self.assertEqual(completed.json()["status"], "COMPLETED")
        self.assertEqual(completed.json()["updated_by"], "은행 담당자")
        self.assertEqual(reopened.status_code, 200)
        self.assertEqual(reopened.json()["status"], "REQUESTED")

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
        final = self.client.post("/api/cases/VP-ACTIVITY/reports/finalize", json={"expected_version": 1, "password": "test-admin", "note": "종료"})
        self.assertEqual([voice.status_code, active.status_code, transcript.status_code, final.status_code], [201, 200, 201, 200])
        self.assertEqual(final.json()["status"], "FINAL")
        self.generate_final_report.assert_awaited_once()
        finalize_args = self.repository.finalize_report.await_args.args
        self.assertEqual(finalize_args[:3], ("VP-ACTIVITY", 1, "종료"))
        self.assertEqual(finalize_args[4]["title"], FINAL_AI_REPORT["title"])
        self.assertEqual(
            [item["section_key"] for item in finalize_args[3]],
            [
                "title", "executive_summary", "incident_summary", "customer_impact_summary",
                "verified_facts", "verification_results", "actions_taken", "unresolved_items",
                "decision_basis", "resolution", "follow_up", "cautions",
            ],
        )

    def test_closed_bank_bundle_includes_canonical_final_report(self) -> None:
        self.repository.get.return_value = {**BUNDLE_CASE, "status": "CLOSED", "mode": "CLOSED"}
        self.repository.list_messages.return_value = []
        self.repository.list_actions.return_value = []
        self.repository.list_verifications.return_value = []
        self.repository.list_customer_questions.return_value = []
        self.repository.list_events.return_value = []
        self.repository.get_voice_session.return_value = None
        self.repository.get_final_report.return_value = {
            "report_id": "final-VP-ACTIVITY", "case_id": "VP-ACTIVITY", "report_version": 1,
            "status": "FINAL", "created_at": "2026-09-02T01:02:00+00:00", "sections": [
                {"section_key": "executive_summary", "content": {"text": "종결 보고서 요약"}, "version": 1},
            ],
        }

        bank = self.client.get("/api/cases/VP-ACTIVITY/bundle?view=bank")
        customer = self.client.get("/api/cases/VP-ACTIVITY/bundle?view=customer")

        self.assertEqual(bank.status_code, 200, bank.text)
        self.assertEqual(bank.json()["final_report"]["report_id"], "final-VP-ACTIVITY")
        self.assertIsNone(customer.json()["final_report"])

    def test_closed_case_can_be_reopened_with_admin_password(self) -> None:
        self.repository.reopen_case.return_value = {
            **BUNDLE_CASE, "version": 3, "mode": "RECOVERY", "status": "IN_PROGRESS",
        }

        denied = self.client.post("/api/cases/VP-ACTIVITY/reopen", json={"expected_version": 2, "password": "wrong"})
        reopened = self.client.post("/api/cases/VP-ACTIVITY/reopen", json={"expected_version": 2, "password": "test-admin"})

        self.assertEqual(denied.status_code, 403)
        self.assertEqual(reopened.status_code, 200)
        self.assertEqual(reopened.json()["mode"], "RECOVERY")
        self.assertEqual(reopened.json()["status"], "IN_PROGRESS")
        self.repository.reopen_case.assert_awaited_once_with("VP-ACTIVITY", 2)

    def test_final_report_can_be_downloaded_as_pdf_and_word(self) -> None:
        self.repository.get_final_report.return_value = {
            "report_id": "final-VP-ACTIVITY", "case_id": "VP-ACTIVITY", "report_version": 1,
            "status": "FINAL", "created_at": "2026-09-02T01:02:00+00:00",
            "sections": [
                {"section_key": "executive_summary", "content": {"text": "최종 요약"}, "version": 1},
                {"section_key": "follow_up", "content": {"items": ["공식 채널로 재확인"]}, "version": 1},
            ],
        }

        pdf = self.client.get("/api/cases/VP-ACTIVITY/reports/final/export?format=pdf")
        word = self.client.get("/api/cases/VP-ACTIVITY/reports/final/export?format=docx")

        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf.headers["content-type"], "application/pdf")
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        self.assertEqual(word.status_code, 200)
        self.assertIn("wordprocessingml.document", word.headers["content-type"])
        self.assertTrue(word.content.startswith(b"PK"))

    def test_case_trash_restore_and_permanent_delete_require_admin_password(self) -> None:
        self.repository.list_attachments.return_value = []

        denied = self.client.post("/api/cases/VP-ACTIVITY/trash", json={"password": "wrong"})
        moved = self.client.post("/api/cases/VP-ACTIVITY/trash", json={"password": "test-admin"})
        restored = self.client.post("/api/cases/VP-ACTIVITY/restore", json={"password": "test-admin"})
        purged = self.client.request("DELETE", "/api/cases/trash/VP-ACTIVITY", json={"password": "test-admin"})

        self.assertEqual([denied.status_code, moved.status_code, restored.status_code, purged.status_code], [403, 204, 204, 204])
        self.repository.delete_case.assert_awaited_once_with("VP-ACTIVITY")
        self.repository.restore_case.assert_awaited_once_with("VP-ACTIVITY")
        self.repository.purge_case.assert_awaited_once_with("VP-ACTIVITY")

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
        # Customer payload hides event details but keeps the latest cursor so the
        # client can detect that the Case changed and safely refetch its projection.
        self.assertEqual(response.json()["cursor"], "7")
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
        customer_message = {
            "message_id": "msg-answer", "case_id": "VP-ACTIVITY", "actor_type": "CUSTOMER",
            "content": "있음", "created_at": "2026-09-02T01:05:00+00:00",
        }
        ai_receipt = {
            "message_id": "msg-ai-receipt", "case_id": "VP-ACTIVITY", "actor_type": "BANK_AGENT",
            "actor_user_id": "case-copilot", "actor_display_name": "CaseCopilot", "actor_role": "BANK_AGENT",
            "content": "고객 답변 접수\n질문: 이미 송금한 금액이 있나요?\n답변: 있음\n상태: 담당자 확인 전 정보 후보",
            "channel": "AI_INTERNAL", "audience": "BANK_INTERNAL", "visibility": "AI_PRIVATE",
            "message_kind": "SYSTEM_EVENT", "private_owner_user_id": None, "mentions": [],
            "created_at": "2026-09-02T01:05:01+00:00",
        }
        recovery_alert = {
            "message_id": "msg-emergency", "case_id": "VP-ACTIVITY", "actor_type": "BANK_AGENT",
            "actor_user_id": "case-copilot", "actor_display_name": "CaseCopilot 긴급 알림", "actor_role": "BANK_AGENT",
            "content": "고객이 직접 사기 피해 발생을 신고했습니다.", "channel": "AI_INTERNAL",
            "audience": "BANK_INTERNAL", "visibility": "AI_PRIVATE", "message_kind": "SYSTEM_EVENT",
            "private_owner_user_id": None, "mentions": ["CaseCopilot"],
            "created_at": "2026-09-02T01:05:02+00:00",
        }
        self.repository.append_message.side_effect = [recovery_alert]
        self.repository.list_messages.return_value = []
        self.repository.get.return_value = {**CASE, "version": 2, "mode": "PREVENT", "victim_transfer_status": "UNKNOWN"}
        self.repository.submit_customer_answer.return_value = {
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
        self.repository.submit_customer_answer.assert_awaited_once_with(
            "VP-ACTIVITY", "cq-1", "있음", "customer-1", "고객"
        )
        self.assertEqual(self.repository.append_message.await_count, 1)  # recovery alert only
        self.repository.propose_case_fact.assert_not_awaited()  # included in the atomic repository operation
        self.repository.update_case.assert_awaited_once_with("VP-ACTIVITY", 2, {
            "victim_transfer_status": "YES", "mode": "RECOVERY",
        })

    def test_customer_chat_loss_statement_activates_recovery_without_duplicate_ack(self) -> None:
        customer_message = {
            "message_id": "msg-customer-loss", "case_id": "VP-ACTIVITY", "actor_type": "CUSTOMER",
            "actor_user_id": "customer-1", "actor_display_name": "고객", "actor_role": "CUSTOMER",
            "content": "이미 송금했어", "channel": "CUSTOMER", "audience": "CUSTOMER",
            "visibility": "CUSTOMER", "message_kind": "CHAT", "private_owner_user_id": None,
            "mentions": [], "created_at": "2026-09-03T10:00:00+09:00",
        }
        alert = {
            "message_id": "msg-emergency", "case_id": "VP-ACTIVITY", "actor_type": "BANK_AGENT",
            "actor_user_id": "case-copilot", "actor_display_name": "CaseCopilot 긴급 알림", "actor_role": "BANK_AGENT",
            "content": "고객이 직접 사기 피해 발생을 신고했습니다.", "channel": "AI_INTERNAL",
            "audience": "BANK_INTERNAL", "visibility": "AI_PRIVATE", "message_kind": "SYSTEM_EVENT",
            "private_owner_user_id": None, "mentions": ["CaseCopilot"],
            "created_at": "2026-09-03T10:00:01+09:00",
        }
        self.repository.get.return_value = {**CASE, "version": 3, "mode": "PREVENT", "victim_transfer_status": "UNKNOWN"}
        self.repository.list_messages.return_value = [customer_message]
        self.repository.append_message.side_effect = [customer_message, alert]

        response = self.client.post("/api/cases/VP-ACTIVITY/messages", json={
            "actor_type": "CUSTOMER", "actor_user_id": "customer-1", "actor_display_name": "고객",
            "content": "이미 송금했어", "channel": "CUSTOMER", "audience": "CUSTOMER", "visibility": "CUSTOMER",
        })

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["message_id"], "msg-customer-loss")
        self.assertEqual(self.repository.append_message.await_count, 2)
        self.repository.update_case.assert_awaited_once_with("VP-ACTIVITY", 3, {
            "victim_transfer_status": "YES", "mode": "RECOVERY",
        })

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
