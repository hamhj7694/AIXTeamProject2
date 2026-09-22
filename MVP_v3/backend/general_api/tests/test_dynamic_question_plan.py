from __future__ import annotations

import asyncio
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import BackgroundTasks, HTTPException
import general_api.app.main as main
from contracts.ai_internal.work_card import CaseWorkCardOutput, WorkCardQuestion
from contracts.question_target import encode_follow_up_target
from contracts.public_api.case_workflow import PublicAnswerCustomerQuestionRequest, PublicQueueCustomerQuestionsRequest
from general_api.app.domains.cases.repository import InMemoryCaseRepository
from general_api.app.domains.cases.mysql_repository import MySqlCaseRepository


def draft(target, text="은행 앱이나 거래 알림에서 실제 이체 내역을 확인할 수 있나요?"):
    return dict(question_id="draft", target_field=target, question_text=text,
                reason="거래 기록으로 불확실성을 줄입니다.", priority="P1", options=[],
                answer_mode="TEXT", allow_free_text=True)


class DynamicQuestionFlowTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.repo = InMemoryCaseRepository()
        self.case_id = "CASE-DYNAMIC-GENERAL"
        self.repo._records.append(dict(case_id=self.case_id, context_revision=1, status="TRIAGE", mode="PREVENT", initial_brief="기관 사칭 연락"))
        self.patch = patch.object(main, "repository", self.repo)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        queued = await self.repo.queue_customer_questions(self.case_id, [draft("transfer_status", "송금하셨나요?")], "staff")
        self.parent_id = queued[0]["question_id"]
        await self.repo.dispatch_next_customer_question(self.case_id)
        await self.repo.submit_customer_answer(self.case_id, self.parent_id, "기억이 잘 안 나요", "customer", "고객")
        self.target = encode_follow_up_target("transfer_status", self.parent_id)

    async def test_filter_preserves_validated_target_and_still_blocks_basic(self):
        state = await main._live_question_state(self.case_id, await self.repo.get(self.case_id))
        parents = main.CaseSnapshotAiAdapter.follow_up_parents(state)
        persisted = await self.repo.list_customer_questions(self.case_id)
        result = main.filter_contextual_questions([
            WorkCardQuestion(**draft("transfer_status", "정말 송금하셨나요?")), WorkCardQuestion(**draft(self.target))
        ], [], persisted, [], parents)
        self.assertEqual([q.target_field for q in result], [self.target])
        self.assertEqual(main.filter_contextual_questions([WorkCardQuestion(**draft(self.target))], [], persisted, []), [])

    async def test_generate_returns_staff_draft_without_queue_or_dispatch(self):
        payload = CaseWorkCardOutput(card_type="QUESTION_PLAN", title="질문 검토", summary="거래 기록 확인",
            context_sources=[], rationale=[], next_action="담당자가 검토합니다.",
            questions=[WorkCardQuestion(**draft(self.target))], warnings=[], model_mode="TEST").model_dump()
        generate = AsyncMock(return_value=payload)
        with patch.object(main.service.ai_client, "generate_work_card", generate), \
             patch.object(main, "get_case_support_snapshot", AsyncMock(return_value=main.PublicCaseSupportSnapshotResponse(case_id=self.case_id, available=False))), \
             patch.object(main, "read_staff_context_records", AsyncMock(return_value=[])):
            result = await main.generate_case_work_card(self.case_id, main.PublicWorkCardGenerateRequest(card_type="QUESTION_PLAN"))
        self.assertEqual(result.questions[0].target_field, self.target)
        self.assertEqual(len(await self.repo.list_customer_questions(self.case_id)), 1)
        self.assertEqual(generate.await_args.args[0]["question_state"]["questions"][0]["answer_text"], "기억이 잘 안 나요")

    async def test_staff_queue_allows_same_scope_and_answer_keeps_parent_and_proposed(self):
        original_fact = deepcopy((await self.repo.list_case_facts(self.case_id))[0])
        # Existing staff endpoint performs the only dispatch in this flow.
        queued = await main.queue_customer_questions(self.case_id, PublicQueueCustomerQuestionsRequest(
            questions=[draft(self.target)], requested_by="staff"))
        self.assertEqual(len(queued), 1)
        child_id = queued[0].question_id
        with patch.object(main, "enqueue_context_extraction", AsyncMock()):
            answered = await main.answer_customer_question(self.case_id, child_id,
                PublicAnswerCustomerQuestionRequest(raw_answer="송금했어요", actor_user_id="customer", actor_display_name="고객"), BackgroundTasks())
            await main.answer_customer_question(self.case_id, child_id,
                PublicAnswerCustomerQuestionRequest(raw_answer="송금했어요", actor_user_id="customer", actor_display_name="고객"), BackgroundTasks())
        self.assertEqual(answered.status, "ANSWERED")
        facts = await self.repo.list_case_facts(self.case_id)
        self.assertEqual(facts[0], original_fact)
        self.assertEqual(len(facts), 2)
        self.assertTrue(all(f["field"] == "transfer_status" and f["status"] == "PROPOSED" for f in facts))
        parent = next(q for q in await self.repo.list_customer_questions(self.case_id) if q["question_id"] == self.parent_id)
        self.assertEqual(parent["answer_text"], "기억이 잘 안 나요")
        resources = await main.case_context_v2_repository().list_resources(self.case_id)
        semantic = [f for f in resources.facts if f.semantic_key == "transfer.actual.status"]
        self.assertEqual(len(semantic), 1)
        self.assertEqual(semantic[0].value, {"status": "TRANSFERRED"})
        self.assertEqual((semantic[0].status, semantic[0].source_kind), ("PROPOSED", "CUSTOMER_STATEMENT"))
        with self.assertRaises(HTTPException) as error:
            await main.queue_customer_questions(self.case_id, PublicQueueCustomerQuestionsRequest(questions=[draft(self.target)], requested_by="staff"))
        self.assertEqual(error.exception.status_code, 409)

    async def test_follow_answer_of_check_availability_is_not_transfer_fact(self):
        payload = main._structured_answer_fact_payload(dict(target_field=self.target), "네, 확인할 수 있어요", "msg")
        self.assertIsNone(payload)

    async def test_stale_parent_active_scope_and_wrong_parent_rejected(self):
        for status in ("PENDING", "ASKED", "SKIPPED"):
            with self.subTest(status=status):
                self.repo._customer_questions[0]["status"] = status
                with self.assertRaises(HTTPException) as error:
                    await main.queue_customer_questions(self.case_id, PublicQueueCustomerQuestionsRequest(questions=[draft(self.target)], requested_by="staff"))
                self.assertEqual(error.exception.status_code, 409)
        self.repo._customer_questions[0]["status"] = "ANSWERED"
        with self.assertRaises(HTTPException):
            await main.queue_customer_questions(self.case_id, PublicQueueCustomerQuestionsRequest(
                questions=[draft(encode_follow_up_target("transfer_status", "missing"))], requested_by="staff"))

    async def test_malformed_and_unsafe_staff_edit_rejected(self):
        for item in (draft("qf2:transfer_status:p"), draft(self.target, "거래내역 확인을 위해 OTP를 입력하세요"),
                     draft(self.target, "정말 송금하셨나요?")):
            with self.subTest(item=item), self.assertRaises(HTTPException) as error:
                await main.queue_customer_questions(self.case_id, PublicQueueCustomerQuestionsRequest(questions=[item], requested_by="staff"))
            self.assertEqual(error.exception.status_code, 422)
        self.assertEqual(len(self.repo._customer_questions), 1)

    async def test_repository_basic_text_duplicate_and_concurrent_follow_guards(self):
        self.assertEqual(await self.repo.queue_customer_questions(self.case_id, [draft("transfer_status", "다른 송금 질문")], "staff"), [])
        self.assertEqual(await self.repo.queue_customer_questions(self.case_id, [draft(self.target, "송금하셨나요?")], "staff"), [])
        results = await asyncio.gather(*[self.repo.queue_customer_questions(self.case_id, [draft(self.target)], "staff") for _ in range(2)])
        self.assertEqual(sum(map(len, results)), 1)
        for status in ("PENDING", "ASKED", "ANSWERED", "SKIPPED"):
            self.repo._customer_questions[-1]["status"] = status
            with self.subTest(status=status):
                self.assertEqual(await self.repo.queue_customer_questions(self.case_id, [draft(self.target, "은행 앱의 거래내역을 다시 확인할 수 있나요?")], "staff"), [])

    async def test_repository_same_canonical_active_and_cross_case_parent_guards(self):
        for status in ("PENDING", "ASKED"):
            self.repo._customer_questions[0]["status"] = status
            with self.subTest(status=status):
                self.assertEqual(await self.repo.queue_customer_questions(self.case_id, [draft(self.target)], "staff"), [])
        self.repo._customer_questions[0]["status"] = "ANSWERED"
        self.repo._records.append(dict(case_id="OTHER", context_revision=1))
        self.assertEqual(await self.repo.queue_customer_questions("OTHER", [draft(self.target)], "staff"), [])

    async def test_malformed_batch_does_not_partially_register(self):
        with self.assertRaises(ValueError):
            await self.repo.queue_customer_questions(self.case_id, [draft(self.target), draft("qf2:transfer_status:p")], "staff")
        self.assertEqual(len(self.repo._customer_questions), 1)


class MysqlFollowUpTransactionTest(unittest.IsolatedAsyncioTestCase):
    async def run_queue(self, *, duplicate=False, malformed=False):
        parent = ("transfer_status", "송금하셨나요?", "question-parent", "ANSWERED")
        target = encode_follow_up_target("transfer_status", "question-parent")
        history = [parent] + ([(target, "이미 확인", "question-child", "SKIPPED")] if duplicate else [])
        cursor = AsyncMock()
        cursor.fetchone.side_effect = [("CASE",), (1,)]
        cursor.fetchall.return_value = history
        cursor.__aenter__.return_value = cursor
        connection = SimpleNamespace(cursor=lambda: cursor, commit=AsyncMock(), rollback=AsyncMock())
        acquire = AsyncMock()
        acquire.__aenter__.return_value = connection
        repo = MySqlCaseRepository()
        repo._pool = SimpleNamespace(acquire=lambda: acquire)
        repo.list_customer_questions = AsyncMock(return_value=[])
        if malformed:
            with self.assertRaises(ValueError):
                await repo.queue_customer_questions("CASE", [draft("qf2:transfer_status:p")], "staff")
        else:
            await repo.queue_customer_questions("CASE", [draft(target)], "staff")
        return cursor, connection

    async def test_lock_and_commit_follow_insert(self):
        cursor, connection = await self.run_queue()
        queries = [call.args[0] for call in cursor.execute.await_args_list]
        self.assertIn("FOR UPDATE", queries[0])
        self.assertTrue(any(q.startswith("INSERT INTO customer_questions") for q in queries))
        connection.commit.assert_awaited_once()
        connection.rollback.assert_not_awaited()

    async def test_skipped_child_blocks_second_follow_inside_transaction(self):
        cursor, connection = await self.run_queue(duplicate=True)
        self.assertFalse(any(call.args[0].startswith("INSERT INTO customer_questions") for call in cursor.execute.await_args_list))
        connection.commit.assert_awaited_once()

    async def test_invalid_target_rolls_back(self):
        _, connection = await self.run_queue(malformed=True)
        connection.rollback.assert_awaited_once()
        connection.commit.assert_not_awaited()

    async def test_follow_fact_insert_is_canonical_and_does_not_update_parent(self):
        target = encode_follow_up_target("transfer_status", "question-parent")
        parent_fact = dict(fact_id="parent-fact", case_id="CASE", field_name="transfer_status",
                           value="기억이 잘 안 나요", source_question_id="question-parent", status="PROPOSED")
        cursor = AsyncMock()
        cursor.__aenter__.return_value = cursor
        cursor.fetchone.return_value = {"target_field": target}
        cursor.fetchall.return_value = [parent_fact]
        connection = SimpleNamespace(cursor=lambda *args: cursor, commit=AsyncMock(), rollback=AsyncMock())
        acquire = AsyncMock()
        acquire.__aenter__.return_value = connection
        repo = MySqlCaseRepository()
        repo._pool = SimpleNamespace(acquire=lambda: acquire)
        fact = await repo.propose_case_fact("CASE", "question-child", "송금했어요", "msg-child")
        self.assertEqual((fact["field"], fact["status"]), ("transfer_status", "PROPOSED"))
        self.assertEqual(parent_fact["value"], "기억이 잘 안 나요")
        queries = [call.args[0] for call in cursor.execute.await_args_list]
        self.assertFalse(any(q.startswith("UPDATE case_context_facts_v2") for q in queries))
        self.assertTrue(any(q.startswith("INSERT INTO case_context_facts_v2") for q in queries))
        connection.commit.assert_awaited_once()
