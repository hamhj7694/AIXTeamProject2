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

    def test_missing_provider_returns_explicit_connection_error(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
            response = self.client.post("/ai/case-copilot/replies", json={
                "case_id": "VP-1", "prompt": "미확인 사실을 정리해 주세요.",
                "case_summary": "기관 사칭 가능성", "unresolved_verifications": ["기관 연락처 확인"],
            })
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"]["code"], "OPENAI_AUTHENTICATION_FAILED")
        self.assertIn("실제 AI 서버에 연결할 수 없습니다", response.json()["detail"]["message"])

    def test_rejects_oversized_prompt_before_provider_call(self) -> None:
        with patch.dict(os.environ, {"CASE_COPILOT_MAX_INPUT_CHARS": "5"}, clear=False):
            response = self.client.post("/ai/case-copilot/replies", json={"case_id": "VP-1", "prompt": "너무 긴 요청입니다"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"]["code"], "INVALID_INPUT")

    def test_work_card_missing_provider_returns_explicit_connection_error(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
            response = self.client.post("/ai/work-cards/generate", json={
                "case_id": "VP-1", "card_type": "QUESTION_PLAN",
                "case_summary": "기관 사칭 의심", "unresolved_items": ["P0: 실제 송금 여부"],
            })
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"]["code"], "OPENAI_AUTHENTICATION_FAILED")

    def test_final_report_missing_provider_does_not_create_fake_report(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
            response = self.client.post("/ai/final-reports/generate", json={
                "case_id": "VP-1",
                "case_summary": "기관 사칭 가능성",
                "workflow_status": "IN_PROGRESS",
                "case_mode": "PREVENT",
                "known_facts": ["고객 진술 접수"],
                "closure_note": "담당자 확인 후 종결",
            })

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"]["code"], "OPENAI_AUTHENTICATION_FAILED")
        self.assertIn("최종 결과 보고서", response.json()["detail"]["message"])

    def test_every_work_card_type_refuses_to_make_fake_content_without_provider(self) -> None:
        card_types = (
            "FACT_REVIEW", "QUESTION_PLAN", "VERIFICATION_REQUEST",
            "BANK_ACTION", "CUSTOMER_NOTICE", "CASE_TRANSITION",
        )
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
            for card_type in card_types:
                with self.subTest(card_type=card_type):
                    response = self.client.post("/ai/work-cards/generate", json={
                        "case_id": "VP-1", "card_type": card_type,
                        "case_summary": "서울지검을 사칭해 안전계좌 송금을 요구한 정황",
                        "workflow_status": "TRIAGE", "case_mode": "PREVENT",
                        "unresolved_items": ["P0: 실제 송금 여부"],
                    })
                    self.assertEqual(response.status_code, 401)
                    self.assertEqual(response.json()["detail"]["code"], "OPENAI_AUTHENTICATION_FAILED")

    def test_customer_support_reports_provider_unavailable_without_fake_reply(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
            response = self.client.post("/ai/case-copilot/replies", json={
                "case_id": "VP-1",
                "prompt": "이미 송금했어요. 어떻게 해야 하나요?",
                "transfer_status": "YES",
                "assistant_mode": "CUSTOMER_SUPPORT",
            })

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"]["code"], "OPENAI_AUTHENTICATION_FAILED")

    def test_bank_case_summary_reports_provider_unavailable_without_fake_reply(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
            response = self.client.post("/ai/case-copilot/replies", json={
                "case_id": "VP-1",
                "prompt": "사건을 정리해 주세요.",
                "case_summary": "검찰 사칭과 안전계좌 송금 요구 정황",
                "known_facts": ["송금 여부: 미확인"],
                "unresolved_verifications": ["서울지검 공식 발신 여부"],
                "assistant_mode": "BANK_INTERNAL",
                "response_style": "BRIEF",
            })

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"]["code"], "OPENAI_AUTHENTICATION_FAILED")

    def test_primary_assignee_question_uses_latest_shared_case_assignment(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
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
