from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

import general_api.app.main as main
from contracts.ai_internal.work_card import CaseWorkCardOutput, WorkCardQuestion
from contracts.public_api.case_workflow import PublicQuestionCandidateResponse
from general_api.app.domains.cases.repository import InMemoryCaseRepository


def question(target: str, text: str, *, question_id: str = "generated") -> WorkCardQuestion:
    return WorkCardQuestion(
        question_id=question_id,
        target_field=target,
        question_text=text,
        reason="사건의 불확실성을 줄이기 위해 확인이 필요합니다.",
        priority="P1",
    )


def candidate(target: str, text: str, *, question_id: str = "candidate") -> PublicQuestionCandidateResponse:
    return PublicQuestionCandidateResponse(
        question_id=question_id,
        target_field=target,
        question_text=text,
        reason="기준 안전 확인",
        priority="P0",
    )


class ContextualQuestionFilterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.baseline = [candidate("transfer_status", "현재 송금하거나 이체한 금액이 있나요?")]

    def test_novel_question_gets_safe_custom_target_and_baseline_duplicate_is_removed(self) -> None:
        result = main.filter_contextual_questions([
            question("contextual_contact", "상대방이 다시 연락하라고 지정한 시간대가 있나요?"),
            question("transfer_status", "현재 송금하거나 이체한 금액이 있나요?"),
        ], self.baseline, [], [])

        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].target_field.startswith("ai-context-"))
        self.assertEqual(result[0].question_id, result[0].target_field)

    def test_asked_pending_answered_drafts_and_duplicate_ai_outputs_are_removed(self) -> None:
        persisted = [
            {"question_id": "asked", "target_field": "staff-contact", "question_text": "상대방이 다시 연락할 시간을 정했나요?", "status": "ASKED", "priority": "P1"},
            {"question_id": "pending", "target_field": "staff-secrecy", "question_text": "통화 내용을 다른 사람에게 말하지 말라고 했나요?", "status": "PENDING", "priority": "P1"},
            {"question_id": "answered", "target_field": "staff-number", "question_text": "다시 연락하라고 알려준 번호가 있나요?", "status": "ANSWERED", "priority": "P1"},
        ]
        drafts = [candidate("staff-app", "화면 공유를 요구한 구체적인 앱 이름을 기억하시나요?", question_id="staff-app")]
        novel = "상대방이 특정 장소로 이동하라고 요구했나요?"
        result = main.filter_contextual_questions([
            question("staff-contact", persisted[0]["question_text"]),
            question("staff-secrecy", persisted[1]["question_text"]),
            question("staff-number", persisted[2]["question_text"]),
            question("staff-app", drafts[0].question_text),
            question("contextual-place", novel),
            question("contextual-place-copy", novel),
        ], self.baseline, persisted, drafts)

        self.assertEqual([item.question_text for item in result], [novel])

    def test_unsafe_secret_value_and_payment_instruction_are_removed_and_result_is_capped(self) -> None:
        result = main.filter_contextual_questions([
            question("contextual-otp", "제공한 OTP 번호가 무엇인가요?"),
            question("contextual-payment", "안전계좌로 지금 송금해 주세요."),
            *[question(f"contextual-{index}", f"상대방이 사용한 연락 수단 {index}을 기억하시나요?") for index in range(5)],
        ], self.baseline, [], [])

        self.assertEqual(len(result), 3)
        self.assertNotIn("OTP 번호", " ".join(item.question_text for item in result))


class ContextualQuestionEndpointTest(unittest.IsolatedAsyncioTestCase):
    async def test_general_api_returns_novel_draft_and_sends_existing_state_to_ai(self) -> None:
        repository = AsyncMock()
        repository.get.return_value = {
            "case_id": "CASE-CONTEXT", "initial_brief": "기관을 사칭한 연락을 받음",
            "status": "TRIAGE", "mode": "PREVENT", "fraud_type": "IMPERSONATION",
        }
        repository.list_case_facts.return_value = []
        repository.list_verifications.return_value = []
        repository.list_actions.return_value = []
        repository.list_messages.return_value = []
        repository.list_attachments.return_value = []
        repository.list_customer_questions.return_value = [{
            "question_id": "answered", "target_field": "transfer_status",
            "question_text": "송금하셨나요?", "status": "ANSWERED", "answer_text": "아니요", "priority": "P0",
        }]
        support = main.PublicCaseSupportSnapshotResponse(
            case_id="CASE-CONTEXT", available=True,
            case_context=main.PublicCaseContextProjection(offender_claims=["수사기관 소속 주장"]),
        )
        baseline = [candidate("personal_information_exposure", "개인정보를 제공하셨나요?")]
        ai_payload = CaseWorkCardOutput(
            card_type="QUESTION_PLAN", title="추가 질문", summary="추가 확인", context_sources=[],
            rationale=[], next_action="담당자 검토", questions=[
                question("contextual-affiliation", "상대방이 어느 부서 소속이라고 소개했는지 기억하시나요?")
            ], warnings=[], model_mode="TEST",
        ).model_dump(mode="python")
        original_repository = main.repository
        original_generate = main.service.ai_client.generate_work_card
        generate_work_card = AsyncMock(return_value=ai_payload)
        main.repository = repository
        main.service.ai_client.generate_work_card = generate_work_card
        try:
            with patch.object(main, "get_case_support_snapshot", AsyncMock(return_value=support)), \
                 patch.object(main, "list_customer_question_candidates", AsyncMock(return_value=baseline)), \
                 patch.object(main, "read_staff_context_records", AsyncMock(return_value=[])):
                result = await main.generate_case_work_card(
                    "CASE-CONTEXT",
                    main.PublicWorkCardGenerateRequest(
                        card_type="QUESTION_PLAN",
                        question_drafts=[candidate("staff-draft", "상대방의 직급을 기억하시나요?", question_id="staff-draft")],
                    ),
                )
        finally:
            main.repository = original_repository
            main.service.ai_client.generate_work_card = original_generate

        self.assertEqual(len(result.questions), 1)
        self.assertTrue(result.questions[0].target_field.startswith("ai-context-"))
        sent = generate_work_card.await_args.args[0]
        self.assertTrue(any("ANSWERED" in item and "답변: 아니요" in item for item in sent["known_facts"]))
        self.assertTrue(any("현재 미발송 직원 검토 초안" in item for item in sent["known_facts"]))

    async def test_non_question_plan_keeps_original_first_thirty_known_facts(self) -> None:
        repository = AsyncMock()
        repository.get.return_value = {
            "case_id": "CASE-FACTS", "initial_brief": "기관을 사칭한 연락을 받음",
            "status": "TRIAGE", "mode": "PREVENT", "fraud_type": "IMPERSONATION",
        }
        facts = [
            {"field": f"field_{index}", "value": f"value_{index}", "status": "CONFIRMED"}
            for index in range(35)
        ]
        repository.list_case_facts.return_value = facts
        repository.list_verifications.return_value = []
        repository.list_actions.return_value = []
        repository.list_messages.return_value = []
        repository.list_attachments.return_value = []
        repository.list_customer_questions.return_value = []
        support = main.PublicCaseSupportSnapshotResponse(
            case_id="CASE-FACTS", available=True,
            case_context=main.PublicCaseContextProjection(offender_claims=["수사기관 소속 주장"]),
        )
        ai_payload = CaseWorkCardOutput(
            card_type="FACT_REVIEW", title="사실 검토", summary="사실 확인", context_sources=[],
            rationale=[], next_action="담당자 검토", questions=[], warnings=[], model_mode="TEST",
        ).model_dump(mode="python")
        original_repository = main.repository
        original_generate = main.service.ai_client.generate_work_card
        generate_work_card = AsyncMock(return_value=ai_payload)
        main.repository = repository
        main.service.ai_client.generate_work_card = generate_work_card
        try:
            with patch.object(main, "get_case_support_snapshot", AsyncMock(return_value=support)), \
                 patch.object(main, "list_customer_question_candidates", AsyncMock(return_value=[])), \
                 patch.object(main, "read_staff_context_records", AsyncMock(return_value=[])):
                await main.generate_case_work_card(
                    "CASE-FACTS", main.PublicWorkCardGenerateRequest(card_type="FACT_REVIEW")
                )
        finally:
            main.repository = original_repository
            main.service.ai_client.generate_work_card = original_generate

        sent = generate_work_card.await_args.args[0]
        self.assertEqual(sent["known_facts"], [
            f"field_{index}: value_{index} (CONFIRMED)" for index in range(30)
        ])


class CustomQuestionQueueTest(unittest.IsolatedAsyncioTestCase):
    async def test_explicit_submit_and_answer_reuse_existing_queue_for_custom_target(self) -> None:
        repo = InMemoryCaseRepository()
        repo._records.append({"case_id": "CASE-QUEUE", "context_revision": 1})
        custom = candidate("ai-context-abc", "상대방이 다시 연락할 시간을 정했나요?", question_id="ai-context-abc")
        second = candidate("staff-second", "통화 내용을 비밀로 하라고 했나요?", question_id="staff-second")

        created = await repo.queue_customer_questions(
            "CASE-QUEUE", [custom.model_dump(), second.model_dump()], "은행 담당자"
        )
        first = await repo.dispatch_next_customer_question("CASE-QUEUE")

        self.assertEqual(len(created), 2)
        self.assertEqual(first["status"], "ASKED")
        self.assertEqual((await repo.list_customer_questions("CASE-QUEUE"))[1]["status"], "PENDING")

        answered = await repo.submit_customer_answer(
            "CASE-QUEUE", first["question_id"], "오후 3시라고 했어요", "customer", "고객"
        )
        next_question = await repo.dispatch_next_customer_question("CASE-QUEUE")

        self.assertEqual(answered["status"], "ANSWERED")
        self.assertEqual(next_question["status"], "ASKED")
        self.assertEqual(repo._case_facts[0]["field"], "ai-context-abc")


if __name__ == "__main__":
    unittest.main()
