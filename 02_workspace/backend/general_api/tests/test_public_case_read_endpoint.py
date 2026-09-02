from __future__ import annotations

import unittest
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

import general_api.app.main as general_main


RECORD = {
    "case_id": "VP-READ001",
    "client_request_id": "read-contract-001",
    "input_text": "검찰청이라며 송금을 요구했습니다.",
    "risk": "HIGH",
    "risk_score": 98.5,
    "mode": "PREVENT",
    "status": "TRIAGE",
    "initial_brief": "기관 사칭과 송금 요구 정황이 확인되었습니다.",
    "diagnosis": {
        "context": {"summary": "기관 사칭 의심", "incident_type": "보이스피싱", "claims": []},
        "evidence": [],
        "features": {"requested_amount_max": 5_000_000},
    },
    "initial_report": {"report_id": "live-VP-READ001", "case_id": "VP-READ001", "report_version": 1},
    "created_at": "2026-09-02T01:00:00+00:00",
    "updated_at": "2026-09-02T01:01:00+00:00",
    "internal_only": "must not be exposed",
}


class PublicCaseReadEndpointTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(general_main.app)
        self.original_repository = general_main.repository
        self.repository = AsyncMock()
        general_main.repository = self.repository

    def tearDown(self) -> None:
        general_main.repository = self.original_repository
        self.client.close()

    def test_list_returns_existing_public_fields_only(self) -> None:
        self.repository.list.return_value = [RECORD]

        response = self.client.get("/api/cases")

        self.assertEqual(response.status_code, 200)
        item = response.json()[0]
        self.assertEqual(item["case_id"], "VP-READ001")
        self.assertEqual(item["risk"], "HIGH")
        self.assertEqual(item["initial_brief"], RECORD["initial_brief"])
        self.assertNotIn("internal_only", item)
        self.assertEqual(set(item), {
            "case_id", "version", "client_request_id", "input_text", "risk", "risk_score", "mode", "status",
            "initial_brief", "diagnosis", "initial_report", "created_at", "updated_at",
        })

    def test_detail_returns_same_public_shape(self) -> None:
        self.repository.get.return_value = RECORD

        response = self.client.get("/api/cases/VP-READ001")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["case_id"], "VP-READ001")
        self.assertEqual(response.json()["diagnosis"], RECORD["diagnosis"])

    def test_detail_not_found_keeps_existing_error_response(self) -> None:
        self.repository.get.return_value = None

        response = self.client.get("/api/cases/VP-NOTFOUND")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"]["code"], "CASE_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
