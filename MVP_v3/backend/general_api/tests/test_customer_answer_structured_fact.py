from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from fastapi import BackgroundTasks

import general_api.app.main as main
from contracts.ai_internal.context_fact_extraction import ContextFactExtractionOutput, ContextFactProposal
from contracts.public_api.case_workflow import PublicAnswerCustomerQuestionRequest
from general_api.app.domains.cases.repository import InMemoryCaseRepository
from general_api.app.domains.cases.context_v3.panel import build_context_panel_v3


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
        async def provider_stub(request):
            # The production route is provider-only. This test double models
            # the provider's semantic answer, including its evidence ID.
            if "송금했어요" not in request.message.content:
                return ContextFactExtractionOutput(model_version="test-provider", prompt_version="test-prompt")
            proposal = ContextFactProposal(
                semantic_key="transfer.actual.status", display_label="실제 이체 여부",
                value={"status": "TRANSFERRED"}, display_value="송금함", confidence=0.9,
                evidence_message_id=request.message.message_id,
            )
            return ContextFactExtractionOutput(
                proposals=[proposal], model_version="test-provider", prompt_version="test-prompt",
            )

        with patch.object(main, "enqueue_context_extraction", AsyncMock()), patch.object(
            main.service.ai_client, "extract_context_facts", new=AsyncMock(side_effect=provider_stub),
        ):
            answered = await main.answer_customer_question(
                "CASE-ANSWER",
                question_id,
                PublicAnswerCustomerQuestionRequest(
                    raw_answer=raw_answer,
                    actor_user_id="customer-1",
                    actor_display_name="고객",
                ),
                BackgroundTasks(),
            )
            if answered.answer_message_id:
                await self.repository.enqueue_message_extraction("CASE-ANSWER", answered.answer_message_id)
                await main.process_message_context_extraction("CASE-ANSWER", answered.answer_message_id)
            return answered

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
        self.assertEqual(semantic[0].value["status"], "TRANSFERRED")
        self.assertEqual(semantic[0].value["extraction_model"], "test-provider")
        self.assertEqual(semantic[0].status, "PROPOSED")
        self.assertEqual(semantic[0].source_kind, "AI_EXTRACTION")
        panel = build_context_panel_v3(
            self.repository._records[0], resources, view="bank", verifications=[], actions=[], messages=[], progress=[]
        )
        status_item = next(
            item for section in panel.sections for item in section.items
            if item.semantic_key == "transfer.actual.status"
        )
        self.assertIn("송금했다고 진술", status_item.display_value)

    async def test_ambiguous_answer_keeps_raw_legacy_fact_without_semantic_proposal(self) -> None:
        question_id = await self._ask("transfer_status")

        await self._answer(question_id, "기억이 안 나요")

        legacy_facts = await self.repository.list_case_facts("CASE-ANSWER")
        self.assertEqual(legacy_facts[0]["value"], "기억이 안 나요")
        resources = await main.case_context_v2_repository().list_resources("CASE-ANSWER")
        self.assertFalse(any(fact.semantic_key == "transfer.actual.status" for fact in resources.facts))

