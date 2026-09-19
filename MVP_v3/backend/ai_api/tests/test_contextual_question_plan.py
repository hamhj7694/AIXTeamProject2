from __future__ import annotations

import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from contracts.ai_internal.work_card import CaseWorkCardInput
from ai_api.app.domains.case_support.work_card_service import CaseWorkCardService, WORK_CARD_SCHEMA
from ai_api.app.domains.case_support.copilot_service import CaseCopilotProviderError


def payload(questions: list[dict]) -> dict:
    return {
        "card_type": "QUESTION_PLAN",
        "title": "고객 확인 질문 추천",
        "summary": "사건별 추가 확인 질문",
        "context_sources": ["통화·신고 맥락"],
        "rationale": ["입력된 사건 맥락에 근거"],
        "next_action": "담당자가 검토합니다.",
        "questions": questions,
        "suggested_claim": None,
        "suggested_target": None,
        "suggested_action_type": None,
        "suggested_action_note": None,
        "suggested_notice": None,
        "suggested_transition": None,
        "warnings": [],
    }


def question(index: int) -> dict:
    return {
        "question_id": f"contextual-{index}",
        "target_field": f"contextual_topic_{index}",
        "question_text": f"상대방이 다시 연락하라고 지정한 시간 {index}을 기억하시나요?",
        "reason": "상대방의 후속 접촉 계획을 확인하기 위해 필요합니다.",
        "priority": "P1",
        "options": [],
        "customer_explanation": "기억나는 범위에서 답해 주세요.",
        "answer_mode": "TEXT",
        "allow_free_text": True,
    }


class ContextualQuestionPlanTest(unittest.IsolatedAsyncioTestCase):
    async def _generate(self, questions: list[dict]):
        create = AsyncMock(return_value=SimpleNamespace(output_text=json.dumps(payload(questions), ensure_ascii=False)))
        client = SimpleNamespace(responses=SimpleNamespace(create=create))
        request = CaseWorkCardInput(
            case_id="CASE-AI", card_type="QUESTION_PLAN",
            case_summary="수사기관을 사칭한 상대방이 통화를 이어감",
            question_candidates=[],
        )
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False), \
             patch("ai_api.app.domains.case_support.work_card_service.AsyncOpenAI", return_value=client):
            result = await CaseWorkCardService().generate(request)
        return result, create

    async def test_novel_contextual_shape_is_accepted_and_capped_at_three(self) -> None:
        result, create = await self._generate([question(index) for index in range(4)])

        self.assertEqual(len(result.questions), 3)
        self.assertEqual(result.questions[0].target_field, "contextual_topic_0")
        self.assertEqual(WORK_CARD_SCHEMA["properties"]["questions"]["maxItems"], 10)
        instructions = create.await_args.kwargs["instructions"]
        self.assertIn("question_candidates에 없는 내용", instructions)
        self.assertIn("최대 3개", instructions)
        self.assertIn("실제 비밀번호", instructions)
        self.assertIn("입력에 없는 기관", instructions)
        self.assertNotIn("질문은 question_candidates에 있는 항목만 사용", instructions)

    async def test_contract_validation_logs_only_stage_and_error_type(self) -> None:
        invalid = {"question_id": "invalid"}
        with self.assertLogs("ai_api.app.domains.case_support.work_card_service", level="WARNING") as captured:
            with self.assertRaises(CaseCopilotProviderError):
                await self._generate([invalid])
        message = "\n".join(captured.output)
        self.assertIn("stage=contract_validation", message)
        self.assertIn("error_type=ValidationError", message)
        self.assertNotIn("CASE-AI", message)

    async def test_empty_contextual_result_is_not_replaced_with_baseline_candidates(self) -> None:
        result, _ = await self._generate([])

        self.assertEqual(result.questions, [])

    async def test_llm_options_are_normalized_before_delivery(self) -> None:
        item = question(1)
        item.update({
            "options": [" 오전 ", "", "오전", "오후"],
            "answer_mode": "SINGLE_CHOICE",
            "allow_free_text": False,
        })

        result, _ = await self._generate([item])

        self.assertEqual(result.questions[0].options, ["오전", "오후"])
        self.assertEqual(result.questions[0].answer_mode, "SINGLE_CHOICE")
        self.assertFalse(result.questions[0].allow_free_text)


if __name__ == "__main__":
    unittest.main()
