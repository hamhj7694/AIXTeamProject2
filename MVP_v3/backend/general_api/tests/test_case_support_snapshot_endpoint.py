from __future__ import annotations

import asyncio
import json
import unittest
from pathlib import Path
from unittest.mock import AsyncMock
from datetime import datetime, timezone

from fastapi.testclient import TestClient

import general_api.app.main as general_main
from ai_api.app.domains.case_support.case_snapshot_adapter import CaseSnapshotAiAdapter
from contracts.public_api.case_context_v2 import PublicCaseFactV2
from contracts.public_api.case_workflow import PublicQuestionCandidateResponse


class CaseSupportSnapshotEndpointTest(unittest.TestCase):
    def _set_v2_facts(self, facts: list[dict]) -> None:
        semantic_by_field = {
            "authentication_information_exposure": "exposure.authentication_information",
            "personal_information_exposure": "exposure.personal_information",
            "transfer_status": "transfer.actual.status",
            "remote_control_app": "device.remote_control_app",
        }
        self.repository._context_v2_facts.clear()
        for item in facts:
            field = item.get("field", "")
            semantic_key = semantic_by_field.get(field, f"legacy.{field}")
            fact = PublicCaseFactV2(
                fact_id=item["fact_id"], case_id="CASE-AI-1", semantic_key=semantic_key,
                display_label=field, value={"value": item.get("value", "")},
                display_value=item.get("value", ""), source_kind="CUSTOMER_STATEMENT",
                status=item.get("status", "PROPOSED"), confidence=0.8,
                evidence_refs=[], visibility="BANK_INTERNAL", version=1,
                confirmed_by="staff" if item.get("status") == "CONFIRMED" else None,
                confirmed_at=datetime.now(timezone.utc) if item.get("status") == "CONFIRMED" else None,
                created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
            )
            self.repository._context_v2_facts[("CASE-AI-1", fact.fact_id)] = fact

    def setUp(self) -> None:
        self.client = TestClient(general_main.app)
        self.original_repository = general_main.repository
        self.original_ai_client = general_main.service.ai_client
        self.repository = AsyncMock()
        for name in ("facts", "gaps", "suggestions", "tasks", "decisions", "observations", "requests"):
            setattr(self.repository, f"_context_v2_{name}", {})
        fixture = Path(__file__).resolve().parents[2] / "contracts" / "ai_internal" / "fixtures" / "diagnosis.high.v1.json"
        diagnosis = json.loads(fixture.read_text(encoding="utf-8"))["response"]
        # 실제 신규 Case는 송금 여부를 UNKNOWN으로 생성한다. 이 상태에서만
        # 송금 여부 후보가 아직 처리되지 않은 P0 질문으로 남는다.
        self.repository.get.return_value = {
            "case_id": "CASE-AI-1", "input_text": "원문은 지원 AI로 보내면 안 됩니다.", "diagnosis": diagnosis,
            "victim_transfer_status": "UNKNOWN",
        }
        self.repository.list_case_facts.return_value = []
        self.repository.list_customer_questions.return_value = []
        self.repository.list_messages.return_value = []
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
        sent = general_main.service.ai_client.build_case_support_snapshot.await_args.args[0]
        self.assertNotIn("input_text", sent)
        self.assertNotIn("원문은 지원 AI로 보내면 안 됩니다.", json.dumps(sent, ensure_ascii=False))

    def test_uses_deterministic_candidates_when_ai_is_unavailable(self) -> None:
        general_main.service.ai_client.build_case_support_snapshot = AsyncMock(side_effect=general_main.AiServiceError("AI 서버 연결 실패"))

        response = self.client.get("/api/cases/CASE-AI-1/customer-question-candidates")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json())
        self.assertEqual(response.json()[0]["question_id"], "candidate-victim_transfer_status")

    def test_conflicting_customer_transfer_amount_adds_clarification_candidate(self) -> None:
        self.repository.list_messages.return_value = [{
            "message_id": "msg-amount-conflict", "actor_type": "CUSTOMER", "message_kind": "CHAT",
            "content": "아까 300만원 보냈어.", "created_at": "2026-09-22T10:00:00+09:00",
        }]
        self.repository.list_transactions.return_value = [{
            "id": 1, "case_id": "CASE-AI-1", "transaction_type": "TRANSFER_OUT", "amount": 2_000_000,
        }]
        general_main.service.ai_client.build_case_support_snapshot = AsyncMock(side_effect=general_main.AiServiceError("AI 서버 연결 실패"))

        response = self.client.get("/api/cases/CASE-AI-1/customer-question-candidates")

        self.assertEqual(response.status_code, 200)
        conflict = next(item for item in response.json() if item["target_field"] == "transaction_amount_conflict")
        self.assertIn("2000000원", conflict["question_text"].replace(",", ""))
        self.assertIn("3000000원", conflict["question_text"].replace(",", ""))
        self.assertIn("별도로 추가 송금", " ".join(conflict["options"]))

    def test_transaction_conflict_answer_handles_negative_additional_claim(self) -> None:
        self.assertEqual(general_main._classify_transaction_conflict_answer("추가 송금이 아니에요."), "CORRECTION")
        self.assertEqual(general_main._classify_transaction_conflict_answer("아니요, 추가 송금했어요."), "ADDITIONAL")
        self.assertEqual(general_main._classify_transaction_conflict_answer("같은 금액을 한 번 더 보냈어요."), "ADDITIONAL")
        self.assertEqual(general_main._classify_transaction_conflict_answer("잘 모르겠어요."), "UNCERTAIN")

    def test_confirmed_refund_fact_maps_to_internal_return_transaction(self) -> None:
        fact = PublicCaseFactV2(
            fact_id="fact-refund", case_id="CASE-AI-1", semantic_key="transfer.actual.amount",
            display_label="실제 이체 금액", value={"amount_krw": 500_000, "direction": "IN", "amount_role": "REFUND_IN"},
            display_value="500,000원 반환", source_kind="CUSTOMER_STATEMENT", status="CONFIRMED",
            confidence=0.9, evidence_refs=[], visibility="BANK_INTERNAL", confirmed_by="staff",
            confirmed_at=datetime.now(timezone.utc), version=1, created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        record = general_main._confirmed_money_transaction_record(fact, "2026-09-22T10:00:00+00:00")
        self.assertIsNotNone(record)
        self.assertEqual(record["transaction_type"], "RETURN_IN")
        self.assertEqual(record["amount"], 500_000)

    def test_promised_refund_fact_does_not_create_transaction(self) -> None:
        fact = PublicCaseFactV2(
            fact_id="fact-promised-refund", case_id="CASE-AI-1", semantic_key="transfer.promised_return.amount",
            display_label="반환 약속 금액", value={"amount_krw": 500_000, "direction": "IN", "amount_role": "REFUND_IN"},
            display_value="500,000원 반환 약속", source_kind="CUSTOMER_STATEMENT", status="CONFIRMED",
            confidence=0.9, evidence_refs=[], visibility="BANK_INTERNAL", confirmed_by="staff",
            confirmed_at=datetime.now(timezone.utc), version=1, created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.assertIsNone(general_main._confirmed_money_transaction_record(fact, "2026-09-22T10:00:00+00:00"))

    def test_uncertain_answer_keeps_unresolved_need_without_repeating_basic(self) -> None:
        self.repository.list_customer_questions.return_value = [{
            "question_id": "q-auth", "target_field": "authentication_information_exposure",
            "question_text": "OTP를 제공했나요?", "status": "ANSWERED", "answer_text": "기억이 안 나요",
        }]
        general_main.service.ai_client.build_case_support_snapshot = AsyncMock(side_effect=lambda payload:
            CaseSnapshotAiAdapter().build_presentation(payload).model_dump(mode="json"))
        support = self.client.get("/api/cases/CASE-AI-1/ai/case-support")
        self.assertEqual(support.status_code, 200)
        self.assertIn("authentication_information_exposure", {item["target_field"] for item in support.json()["unresolved_items"]})
        response = self.client.get("/api/cases/CASE-AI-1/customer-question-candidates")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("authentication_information_exposure", {item["target_field"] for item in response.json()})
        self.repository.queue_customer_questions.assert_not_awaited()
        self.repository.dispatch_next_customer_question.assert_not_awaited()

    def test_answered_field_alone_is_not_a_final_field_wide_filter(self) -> None:
        question = {"question_id": "q", "target_field": "transfer_status", "question_text": "송금 여부?",
                    "status": "ANSWERED", "answer_text": "기억이 안 나요"}
        candidate = PublicQuestionCandidateResponse(question_id="new", target_field="transfer_status",
            question_text="당시 거래 기록을 가지고 계신가요?", reason="기록 확인", priority="P1")
        self.assertEqual(general_main.exclude_handled_question_candidates([candidate], [question]), [candidate])
        self.assertEqual(general_main.exclude_handled_question_candidates(
            [candidate.model_copy(update={"question_text": question["question_text"]})], [question]), [])

    def test_proposed_v2_fact_and_chat_keywords_do_not_end_question_need(self) -> None:
        now = datetime.now(timezone.utc)
        self.repository._context_v2_facts[("CASE-AI-1", "f-auth")] = PublicCaseFactV2(
            fact_id="f-auth", case_id="CASE-AI-1", semantic_key="exposure.authentication_information",
            display_label="인증정보 제공", value={"status": "EXPOSED"}, display_value="인증정보 제공함",
            source_kind="CUSTOMER_STATEMENT", status="PROPOSED", evidence_refs=[], version=1,
            created_at=now, updated_at=now,
        )
        self.repository.list_messages.return_value = [{"actor_type": "CUSTOMER", "message_kind": "CHAT",
            "content": "OTP를 제공했는지 기억이 안 나요. 송금했는지도 모르겠어요."}]
        for unavailable in (False, True):
            with self.subTest(unavailable=unavailable):
                if unavailable:
                    general_main.service.ai_client.build_case_support_snapshot = AsyncMock(
                        side_effect=general_main.AiServiceError("AI 서버 연결 실패"))
                response = self.client.get("/api/cases/CASE-AI-1/customer-question-candidates")
                self.assertEqual(response.status_code, 200)
                fields = {general_main.normalize_target_field(item["target_field"]) for item in response.json()}
                self.assertIn("authentication_information_exposure", fields)
                self.assertIn("transfer_status", fields)
                self.repository.queue_customer_questions.assert_not_awaited()
                self.repository.dispatch_next_customer_question.assert_not_awaited()

    def test_pending_asked_skipped_clear_and_confirmed_still_suppress_basic(self) -> None:
        for status, answer, facts in (
            ("PENDING", None, []), ("ASKED", None, []), ("SKIPPED", None, []),
            ("ANSWERED", "OTP는 알려주지 않았어요", []),
            ("ANSWERED", "기억이 안 나요", [{"fact_id": "f-auth", "field": "authentication_information_exposure",
                                           "value": "제공하지 않음", "status": "CONFIRMED"}]),
        ):
            with self.subTest(status=status, facts=facts):
                self.repository.list_customer_questions.return_value = [{"question_id": "q-auth",
                    "target_field": "authentication_information_exposure", "question_text": "OTP를 제공했나요?",
                    "status": status, "answer_text": answer}]
                self._set_v2_facts(facts)
                response = self.client.get("/api/cases/CASE-AI-1/customer-question-candidates")
                self.assertEqual(response.status_code, 200)
                self.assertNotIn("authentication_information_exposure", {item["target_field"] for item in response.json()})
                self.repository.queue_customer_questions.assert_not_awaited()
                self.repository.dispatch_next_customer_question.assert_not_awaited()

    def test_ai_candidate_is_filtered_when_target_field_was_already_answered(self) -> None:
        self.repository.list_customer_questions.return_value = [{
            "question_id": "old-custom-id", "target_field": "transfer_status",
            "question_text": "송금하셨나요?", "status": "ANSWERED", "answer_text": "아니요",
        }]

        response = self.client.get("/api/cases/CASE-AI-1/customer-question-candidates")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload)
        self.assertNotIn(
            "transfer_status",
            {item["target_field"] for item in payload},
        )
        sent_context = general_main.service.ai_client.build_case_support_snapshot.await_args.args[0]["question_context"]
        self.assertEqual(sent_context["answered_question_fields"], ["transfer_status"])

    def test_case_transfer_value_alone_does_not_suppress_question(self) -> None:
        self.repository.get.return_value["victim_transfer_status"] = "YES"

        response = self.client.get("/api/cases/CASE-AI-1/customer-question-candidates")

        self.assertEqual(response.status_code, 200)
        sent_context = general_main.service.ai_client.build_case_support_snapshot.await_args.args[0]["question_context"]
        self.assertNotIn("transfer_status", sent_context["confirmed_fields"])
        self.assertIn("transfer_status", {general_main.normalize_target_field(item["target_field"]) for item in response.json()})

    def test_transfer_question_requires_statement_or_confirmed_fact_not_proposal(self) -> None:
        for fact_status, expected in (("PROPOSED", True), ("CONFIRMED", False)):
            with self.subTest(fact_status=fact_status):
                self._set_v2_facts([{
                    "fact_id": "f-transfer", "field": "transfer_status",
                    "value": "송금했어요", "status": fact_status,
                }])
                response = self.client.get("/api/cases/CASE-AI-1/customer-question-candidates")
                fields = {general_main.normalize_target_field(item["target_field"]) for item in response.json()}
                self.assertEqual("transfer_status" in fields, expected)

    def test_remote_question_asks_about_actual_installation(self) -> None:
        response = self.client.get("/api/cases/CASE-AI-1/customer-question-candidates")
        remote = next(item for item in response.json() if item["target_field"] == "remote_control_app")
        self.assertIn("실제로 설치", remote["question_text"])
        self.assertEqual(remote["options"], ["설치했어요", "설치하지 않았어요", "잘 모르겠어요"])
        self.repository.queue_customer_questions.assert_not_awaited()
        self.repository.dispatch_next_customer_question.assert_not_awaited()

    def test_confirmed_installation_request_is_not_confirmed_installation(self) -> None:
        self._set_v2_facts([{
            "fact_id": "f-request", "field": "remote_control_app",
            "value": "원격제어 앱 설치 요구", "status": "CONFIRMED",
        }])
        response = self.client.get("/api/cases/CASE-AI-1/customer-question-candidates")
        self.assertIn("remote_control_app", {item["target_field"] for item in response.json()})

    def test_institution_conceptual_duplicate_keeps_existing_targets_distinct(self) -> None:
        ai_payload = general_main.service.ai_client.build_case_support_snapshot.return_value
        ai_payload["recommended_questions"].append({
            "question_id": "q-claimed", "target_field": "claimed_organization",
            "question": "상대방은 어느 기관이나 회사 소속이라고 말했나요?",
            "reason": "소속 주장 확인", "priority": "P1",
        })
        response = self.client.get("/api/cases/CASE-AI-1/customer-question-candidates")
        fields = {item["target_field"] for item in response.json()}
        self.assertIn("claimed_organization", fields)
        self.assertNotIn("impersonated_institution", fields)
        self.assertNotEqual(general_main.normalize_target_field("claimed_organization"),
                            general_main.normalize_target_field("impersonated_institution"))

    def test_legacy_institution_question_suppresses_matching_new_basic_question(self) -> None:
        self.repository.list_customer_questions.return_value = [{
            "question_id": "legacy-institution", "target_field": "impersonated_institution",
            "question_text": "상대방이 어느 기관이나 은행을 사칭했는지 알려주실 수 있나요?",
            "status": "ASKED", "answer_text": None,
        }]
        response = self.client.get("/api/cases/CASE-AI-1/customer-question-candidates")
        self.assertNotIn("claimed_organization", {item["target_field"] for item in response.json()})

    def test_all_valid_candidates_are_returned_without_filling_or_capping(self) -> None:
        ai_payload = general_main.service.ai_client.build_case_support_snapshot.return_value
        ai_payload["recommended_questions"].extend([
            {"question_id": "q-purpose", "target_field": "transfer_purpose", "question": "송금 명목은 무엇인가요?", "reason": "명목 확인", "priority": "P1"},
            {"question_id": "q-claimed", "target_field": "claimed_organization", "question": "상대방은 어느 기관 소속이라고 말했나요?", "reason": "소속 확인", "priority": "P1"},
            {"question_id": "q-incident", "target_field": "incident_claim", "question": "상대방은 어떤 사건이라고 말했나요?", "reason": "주장 확인", "priority": "P1"},
            {"question_id": "q-unmapped", "target_field": "ongoing_contact", "question": "지금도 통화 중인가요?", "reason": "미매핑", "priority": "P0"},
        ])
        response = self.client.get("/api/cases/CASE-AI-1/customer-question-candidates")
        fields = [general_main.normalize_target_field(item["target_field"]) for item in response.json()]
        self.assertEqual(len(fields), 7)
        self.assertNotIn("ongoing_contact", fields)
        self.assertEqual(fields[:4], ["transfer_status", "authentication_information_exposure",
                                       "personal_information_exposure", "remote_control_app"])
        self.assertEqual(fields[4], "transfer_purpose")

    def test_only_two_needed_candidates_are_returned(self) -> None:
        self.repository.list_customer_questions.return_value = [
            {"question_id": f"q-{field}", "target_field": field,
             "question_text": "상대방은 어느 기관 소속이라고 말했나요?" if field == "impersonated_institution" else f"{field} 확인",
             "status": "PENDING", "answer_text": None}
            for field in ("personal_information_exposure", "authentication_information_exposure",
                          "impersonated_institution")
        ]
        response = self.client.get("/api/cases/CASE-AI-1/customer-question-candidates")
        self.assertEqual(len(response.json()), 2)
        self.repository.queue_customer_questions.assert_not_awaited()

    def test_sends_latest_case_work_state_to_ai_snapshot(self) -> None:
        self.repository.list_customer_questions.return_value = [{
            "question_id": "q-live", "target_field": "transfer_status",
            "question_text": "실제 송금하셨나요?", "priority": "P0",
            "status": "ANSWERED", "answer_text": "이미 송금했어요",
        }]
        self._set_v2_facts([{
            "fact_id": "fact-live", "field": "transfer_status", "value": "이미 송금했어요",
            "status": "PROPOSED",
        }])
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

    def test_legacy_ai_ensure_route_cannot_create_or_send_questions(self) -> None:
        response = self.client.post("/api/cases/CASE-AI-1/ai/customer-questions/ensure")

        self.assertEqual(response.status_code, 404)
        self.repository.queue_customer_questions.assert_not_awaited()
        self.repository.dispatch_next_customer_question.assert_not_awaited()

    def test_staff_approved_customer_question_submit_path_is_preserved(self) -> None:
        response = self.client.post("/api/cases/CASE-AI-1/customer-questions", json={
            "questions": [{
                "question_id": "staff-question",
                "target_field": "ai-context-contact-time",
                "question_text": "상대방이 다시 연락하라고 지정한 시간이 있나요?",
                "reason": "담당자가 사건 맥락을 검토한 뒤 선택했습니다.",
                "priority": "P1",
            }],
            "requested_by": "은행 담당자",
        })

        self.assertEqual(response.status_code, 201)
        queued = self.repository.queue_customer_questions.await_args.args
        self.assertEqual(queued[0], "CASE-AI-1")
        self.assertEqual(queued[1][0]["question_id"], "staff-question")
        self.assertEqual(queued[2], "은행 담당자")
        self.repository.dispatch_next_customer_question.assert_awaited_once_with("CASE-AI-1")

    def test_revision_scan_preserves_checklist_without_creating_customer_questions(self) -> None:
        self.repository.list.return_value = [{
            "case_id": "CASE-AI-1", "status": "TRIAGE", "mode": "PREVENT",
            "updated_at": "2026-09-04T00:00:00+00:00",
        }]

        reconciled = asyncio.run(general_main.reconcile_changed_cases_once())

        self.assertEqual(reconciled, 1)
        self.repository.queue_customer_questions.assert_not_awaited()
        self.repository.create_action.assert_awaited_once()
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
        self._set_v2_facts([{
            "fact_id": "fact-auth", "field": "authentication_information_exposure",
            "value": "제공했어요", "status": "PROPOSED",
        }])

        asyncio.run(general_main.sync_ai_checklist_items("CASE-AI-1", snapshot))

        record = self.repository.create_action.await_args.args[1]
        self.assertEqual(record["action_type"], "AI_CHECKLIST:P0:authentication_information_exposure")
        self.assertIn("사실로 확정할지", record["note"])


if __name__ == "__main__":
    unittest.main()
