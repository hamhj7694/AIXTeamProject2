from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from ai_api.app.main import app
from ai_api.app.domains.case_support.copilot_service import CaseCopilotQuotaError, CustomerSupportCallBudget


class CaseCopilotEndpointTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()

    def test_fixture_mode_is_explicitly_labelled_and_bounded(self) -> None:
        with patch.dict(os.environ, {"CASE_COPILOT_MODE": "fixture"}, clear=False):
            response = self.client.post("/ai/case-copilot/replies", json={
                "case_id": "VP-1", "prompt": "미확인 사실을 정리해 주세요.",
                "case_summary": "기관 사칭 가능성", "unresolved_verifications": ["기관 연락처 확인"],
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["model_mode"], "FIXTURE")

    def test_rejects_oversized_prompt_before_provider_call(self) -> None:
        with patch.dict(os.environ, {"CASE_COPILOT_MODE": "fixture", "CASE_COPILOT_MAX_INPUT_CHARS": "5"}, clear=False):
            response = self.client.post("/ai/case-copilot/replies", json={"case_id": "VP-1", "prompt": "너무 긴 요청입니다"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"]["code"], "INVALID_INPUT")

    def test_work_card_fixture_is_structured_and_explicitly_labelled(self) -> None:
        with patch.dict(os.environ, {"CASE_WORK_CARD_MODE": "fixture"}, clear=False):
            response = self.client.post("/ai/work-cards/generate", json={
                "case_id": "VP-1", "card_type": "QUESTION_PLAN",
                "case_summary": "기관 사칭 의심", "unresolved_items": ["P0: 실제 송금 여부"],
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["card_type"], "QUESTION_PLAN")
        self.assertEqual(response.json()["model_mode"], "FIXTURE")
        self.assertTrue(response.json()["title"])
        self.assertTrue(response.json()["summary"])
        self.assertGreaterEqual(len(response.json()["questions"]), 1)

    def test_every_work_card_fixture_contains_its_executable_content(self) -> None:
        expected_fields = {
            "FACT_REVIEW": [],
            "QUESTION_PLAN": ["questions"],
            "VERIFICATION_REQUEST": ["suggested_claim", "suggested_target"],
            "BANK_ACTION": ["suggested_action_type", "suggested_action_note"],
            "CUSTOMER_NOTICE": ["suggested_notice"],
            "CASE_TRANSITION": ["suggested_transition"],
        }
        with patch.dict(os.environ, {"CASE_WORK_CARD_MODE": "fixture"}, clear=False):
            for card_type, fields in expected_fields.items():
                with self.subTest(card_type=card_type):
                    response = self.client.post("/ai/work-cards/generate", json={
                        "case_id": "VP-1", "card_type": card_type,
                        "case_summary": "서울지검을 사칭해 안전계좌 송금을 요구한 정황",
                        "workflow_status": "TRIAGE", "case_mode": "PREVENT",
                        "unresolved_items": ["P0: 실제 송금 여부"],
                    })
                    self.assertEqual(response.status_code, 200)
                    payload = response.json()
                    self.assertTrue(payload["title"])
                    self.assertTrue(payload["summary"])
                    self.assertTrue(payload["context_sources"])
                    self.assertTrue(payload["rationale"])
                    self.assertTrue(payload["next_action"])
                    self.assertTrue(payload["warnings"])
                    for field in fields:
                        self.assertTrue(payload[field])
                    if card_type == "VERIFICATION_REQUEST":
                        self.assertIn("서울지검", payload["suggested_claim"])
                        self.assertIn("공식 대표번호", payload["suggested_target"])

    def test_customer_support_has_safe_fallback_when_provider_is_unavailable(self) -> None:
        with patch.dict(os.environ, {"CASE_COPILOT_MODE": "openai", "OPENAI_API_KEY": ""}, clear=False):
            response = self.client.post("/ai/case-copilot/replies", json={
                "case_id": "VP-1",
                "prompt": "이미 송금했어요. 어떻게 해야 하나요?",
                "transfer_status": "YES",
                "assistant_mode": "CUSTOMER_SUPPORT",
            })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["model_mode"], "CUSTOMER_SAFETY_FALLBACK")
        self.assertIn("추가 송금", response.json()["content"])
        self.assertIn("112", response.json()["content"])

    def test_bank_case_summary_has_context_fallback_when_provider_is_unavailable(self) -> None:
        with patch.dict(os.environ, {"CASE_COPILOT_MODE": "openai", "OPENAI_API_KEY": ""}, clear=False):
            response = self.client.post("/ai/case-copilot/replies", json={
                "case_id": "VP-1",
                "prompt": "사건을 정리해 주세요.",
                "case_summary": "검찰 사칭과 안전계좌 송금 요구 정황",
                "known_facts": ["송금 여부: 미확인"],
                "unresolved_verifications": ["서울지검 공식 발신 여부"],
                "assistant_mode": "BANK_INTERNAL",
                "response_style": "BRIEF",
            })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["model_mode"], "BANK_CONTEXT_FALLBACK")
        self.assertIn("## 상황 판단", response.json()["content"])
        self.assertIn("서울지검 공식 발신 여부", response.json()["content"])

    def test_primary_assignee_question_uses_latest_shared_case_assignment(self) -> None:
        with patch.dict(os.environ, {"CASE_COPILOT_MODE": "openai", "OPENAI_API_KEY": ""}, clear=False):
            response = self.client.post("/ai/case-copilot/replies", json={
                "case_id": "VP-1",
                "prompt": "이 사건 메인 담당자가 누구야?",
                "primary_assignee": "김태환",
                "participants": ["김태환 (메인 담당자)", "은행 담당자 (검토자)"],
                "assistant_mode": "BANK_INTERNAL",
            })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["model_mode"], "SHARED_CASE_LOOKUP")
        self.assertIn("김태환", response.json()["content"])
        self.assertIn("은행 담당자 (검토자)", response.json()["content"])


class CustomerSupportCallBudgetTest(unittest.IsolatedAsyncioTestCase):
    async def test_per_minute_limit_stops_before_provider_call(self) -> None:
        budget = CustomerSupportCallBudget()
        with patch.dict(os.environ, {
            "CUSTOMER_AI_MAX_CALLS_PER_MINUTE": "1",
            "CUSTOMER_AI_MAX_CALLS_PER_DAY": "2",
        }, clear=False):
            await budget.reserve("VP-BUDGET")
            with self.assertRaises(CaseCopilotQuotaError):
                await budget.reserve("VP-BUDGET")


if __name__ == "__main__":
    unittest.main()
