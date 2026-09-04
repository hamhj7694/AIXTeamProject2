from __future__ import annotations

import unittest
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

import general_api.app.main as general_main
from contracts.diagnosis import AnalyzeCaseResponse, InitialReport, RiskLevel
from general_api.app.clients.diagnosis_ai import AiServiceError


class PublicAnalyzeEndpointTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(general_main.app)
        self.original_service = general_main.service
        self.service = AsyncMock()
        general_main.service = self.service

    def tearDown(self) -> None:
        general_main.service = self.original_service
        self.client.close()

    def test_case_created_returns_only_public_fields(self) -> None:
        self.service.analyze.return_value = AnalyzeCaseResponse(
            disposition="CASE_CREATED",
            case_id="VP-PUBLIC01",
            risk=RiskLevel.HIGH,
            mode="PREVENT",
            status="TRIAGE",
            initial_brief="기관 사칭과 송금 요구 정황이 확인되었습니다.",
            initial_report=InitialReport(
                report_id="RPT-PUBLIC01",
                case_id="VP-PUBLIC01",
                sections=[],
                created_at="2026-09-01T00:00:00+00:00",
            ),
        )

        response = self.client.post("/api/cases/analyze", json={
            "text": "검찰청이라며 안전계좌 송금을 요구했습니다.",
            "client_request_id": "public-contract-001",
        })

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {
            "schema_version": "case_analyze.v1",
            "disposition": "CASE_CREATED",
            "case_id": "VP-PUBLIC01",
            "risk": "HIGH",
            "mode": "PREVENT",
            "status": "TRIAGE",
            "initial_brief": "기관 사칭과 송금 요구 정황이 확인되었습니다.",
            "initial_report": {
                "report_id": "RPT-PUBLIC01",
                "case_id": "VP-PUBLIC01",
                "report_version": 1,
            },
            "error": None,
        })
        forwarded = self.service.analyze.await_args.args[0]
        self.assertEqual(forwarded.client_request_id, "public-contract-001")

    def test_no_case_uses_same_public_envelope(self) -> None:
        self.service.analyze.return_value = AnalyzeCaseResponse(
            disposition="NO_CASE",
            risk=RiskLevel.NORMAL,
            initial_brief="현재 모델 판정 기준 미만입니다.",
        )

        response = self.client.post("/api/cases/analyze", json={"text": "예금 만기일은 다음 달입니다."})

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["disposition"], "NO_CASE")
        self.assertEqual(response.json()["risk"], "NORMAL")
        self.assertNotIn("diagnosis", response.json())
        self.assertIsNone(response.json()["initial_report"])

    def test_invalid_input_uses_public_failed_error(self) -> None:
        response = self.client.post("/api/cases/analyze", json={"text": ""})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {
            "schema_version": "case_analyze.v1",
            "disposition": "FAILED",
            "case_id": None,
            "risk": None,
            "mode": None,
            "status": None,
            "initial_brief": None,
            "initial_report": None,
            "error": {
                "code": "INVALID_INPUT",
                "message": "요청 형식을 확인해 주세요.",
                "retryable": False,
            },
        })

    def test_upstream_failure_hides_internal_error_details(self) -> None:
        self.service.analyze.side_effect = AiServiceError("AI API 연결에 실패했습니다.")

        response = self.client.post("/api/cases/analyze", json={"text": "분석할 통화"})

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["disposition"], "FAILED")
        self.assertEqual(response.json()["error"], {
            "code": "AI_ANALYSIS_FAILED",
            "message": "AI API 연결에 실패했습니다.",
            "retryable": True,
        })


if __name__ == "__main__":
    unittest.main()
