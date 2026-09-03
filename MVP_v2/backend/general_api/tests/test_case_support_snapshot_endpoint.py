from __future__ import annotations

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
        general_main.repository = self.repository
        general_main.service.ai_client.build_case_support_snapshot = AsyncMock(return_value={
            "case_id": "CASE-AI-1",
            "case_brief": {"summary": "AI 요약", "incident_type": "기관 사칭", "risk_level": "HIGH", "risk_score": 92.0, "next_checks": ["송금 여부 확인"]},
            "recommended_questions": [{"question_id": "q-transfer", "target_field": "transfer_status", "question": "송금하셨나요?", "reason": "피해 여부 확인", "priority": "P0"}],
            "unresolved_items": [{"target_field": "transfer_status", "description": "송금 여부", "priority": "P0"}],
            "warnings": [],
        })

    def tearDown(self) -> None:
        general_main.repository = self.original_repository
        general_main.service.ai_client = self.original_ai_client
        self.client.close()

    def test_maps_ai_snapshot_to_public_screen_contract(self) -> None:
        response = self.client.get("/api/cases/CASE-AI-1/ai/case-support")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["case_brief"]["summary"], "AI 요약")
        self.assertEqual(response.json()["recommended_questions"][0]["question_text"], "송금하셨나요?")
        self.assertNotIn("evidence_refs", response.json()["recommended_questions"][0])

    def test_uses_deterministic_candidates_when_ai_is_unavailable(self) -> None:
        general_main.service.ai_client.build_case_support_snapshot = AsyncMock(side_effect=general_main.AiServiceError("AI 서버 연결 실패"))

        response = self.client.get("/api/cases/CASE-AI-1/customer-question-candidates")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json())
        self.assertEqual(response.json()[0]["question_id"], "candidate-victim_transfer_status")


if __name__ == "__main__":
    unittest.main()
