from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock

from fastapi.testclient import TestClient

import ai_api.app.main as ai_main
from ai_api.app.domains.case_support import CaseSnapshotAiAdapter
from contracts.diagnosis import DiagnosisResult


FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "contracts"
    / "ai_internal"
    / "fixtures"
    / "diagnosis.high.v1.json"
)


class CaseSupportEndpointTest(unittest.TestCase):
    @staticmethod
    def _diagnosis_payload() -> dict:
        return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["response"]

    def setUp(self) -> None:
        self.client = TestClient(ai_main.app)
        self.original_adapter = ai_main.case_snapshot_adapter
        self.adapter = Mock(wraps=CaseSnapshotAiAdapter())
        ai_main.case_snapshot_adapter = self.adapter

    def tearDown(self) -> None:
        ai_main.case_snapshot_adapter = self.original_adapter
        self.client.close()

    def test_snapshot_returns_case_brief_questions_and_preserved_warnings(self) -> None:
        diagnosis = self._diagnosis_payload()
        diagnosis.update({
            "warnings": ["분석 원본의 경고"],
            "partial_failure": True,
        })

        response = self.client.post("/ai/case-support/snapshot", json={
            "case_id": "VP-HTTP-001",
            "diagnosis": diagnosis,
            "warnings": ["호출자가 전달한 경고"],
        })

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.adapter.build_presentation.assert_called_once()
        self.assertEqual(payload["case_id"], "VP-HTTP-001")
        self.assertTrue(payload["case_brief"]["summary"])
        self.assertTrue(payload["recommended_questions"])
        self.assertTrue({"question", "target_field", "priority"}.issubset(
            payload["recommended_questions"][0],
        ))
        self.assertTrue(payload["unresolved_items"])
        self.assertIn("호출자가 전달한 경고", payload["warnings"])
        self.assertIn("분석 원본의 경고", payload["warnings"])
        self.assertIn("Diagnosis 결과가 부분 실패 상태입니다.", payload["warnings"])

    def test_missing_diagnosis_keeps_safe_partial_result(self) -> None:
        response = self.client.post("/ai/case-support/snapshot", json={"case_id": "VP-HTTP-MISSING"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIsNone(payload["case_brief"])
        self.assertEqual(payload["recommended_questions"], [])
        self.assertTrue(any("diagnosis" in warning for warning in payload["warnings"]))

    def test_snapshot_context_removes_pending_question_without_sending_message(self) -> None:
        response = self.client.post("/ai/case-support/snapshot", json={
            "case_id": "VP-HTTP-PENDING",
            "diagnosis": self._diagnosis_payload(),
            "question_context": {
                "pending_question_fields": ["transfer_status"],
            },
        })

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(any(
            item["target_field"] == "transfer_status"
            for item in payload["recommended_questions"]
        ))
        # 이 endpoint는 추천 데이터만 반환하며 Message/Queue 식별자를 만들지 않는다.
        self.assertNotIn("message_id", payload)
        self.assertNotIn("queue_id", payload)

    def test_invalid_diagnosis_uses_fastapi_validation_error(self) -> None:
        response = self.client.post("/ai/case-support/snapshot", json={
            "case_id": "VP-HTTP-INVALID",
            "diagnosis": {},
        })

        self.assertEqual(response.status_code, 422)

    def test_existing_analyze_text_route_is_unchanged(self) -> None:
        original_service = ai_main.service
        diagnosis = DiagnosisResult.model_validate(self._diagnosis_payload())
        ai_main.service = Mock()
        ai_main.service.analyze = AsyncMock(return_value=diagnosis)
        try:
            response = self.client.post("/ai/analyze/text", json={"text": "기존 분석 요청"})
        finally:
            ai_main.service = original_service

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["risk_level"], "HIGH")


if __name__ == "__main__":
    unittest.main()
