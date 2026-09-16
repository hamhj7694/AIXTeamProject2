from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from fastapi import BackgroundTasks

import general_api.app.main as main
from contracts.public_api.case_workflow import PublicAnswerCustomerQuestionRequest
from general_api.app.domains.cases.repository import InMemoryCaseRepository


class CustomerAnswerStructuredFactTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.repository = InMemoryCaseRepository()
        self.repository._records.append({"case_id": "CASE-ANSWER", "context_revision": 1})
        self.original_repository = main.repository
        main.repository = self.repository

    def tearDown(self) -> None:
        main.repository = self.original_repository

    async def _ask(self, target_field: str) -> str:
        queued = await self.repository.queue_customer_questions("CASE-ANSWER", [{
            "question_id": f"candidate-{target_field}",
            "target_field": target_field,
            "question_text": "확인 질문",
            "reason": "확인 필요",
            "priority": "P0",
        }], "staff")
        await self.repository.dispatch_next_customer_question("CASE-ANSWER")
        return queued[0]["question_id"]

    async def _answer(self, question_id: str, raw_answer: str):
        with patch.object(main, "enqueue_context_extraction", AsyncMock()):
            return await main.answer_customer_question(
                "CASE-ANSWER",
                question_id,
                PublicAnswerCustomerQuestionRequest(
                    raw_answer=raw_answer,
                    actor_user_id="customer-1",
                    actor_display_name="고객",
                ),
                BackgroundTasks(),
            )

    async def test_clear_answer_keeps_raw_legacy_fact_and_adds_one_semantic_proposal(self) -> None:
        question_id = await self._ask("transfer_status")

        answered = await self._answer(question_id, "송금했어요")
        await self._answer(question_id, "송금했어요")  # Idempotent retry must not duplicate the proposal.

        self.assertEqual(answered.status, "ANSWERED")
        legacy_facts = await self.repository.list_case_facts("CASE-ANSWER")
        self.assertEqual(legacy_facts[0]["value"], "송금했어요")
        resources = await main.case_context_v2_repository().list_resources("CASE-ANSWER")
        semantic = [fact for fact in resources.facts if fact.semantic_key == "transfer.actual.status"]
        self.assertEqual(len(semantic), 1)
        self.assertEqual(semantic[0].value, {"status": "TRANSFERRED"})
        self.assertEqual(semantic[0].status, "PROPOSED")
        self.assertEqual(semantic[0].source_kind, "CUSTOMER_STATEMENT")

    async def test_ambiguous_answer_keeps_raw_legacy_fact_without_semantic_proposal(self) -> None:
        question_id = await self._ask("transfer_status")

        await self._answer(question_id, "기억이 안 나요")

        legacy_facts = await self.repository.list_case_facts("CASE-ANSWER")
        self.assertEqual(legacy_facts[0]["value"], "기억이 안 나요")
        resources = await main.case_context_v2_repository().list_resources("CASE-ANSWER")
        self.assertFalse(any(fact.semantic_key == "transfer.actual.status" for fact in resources.facts))

