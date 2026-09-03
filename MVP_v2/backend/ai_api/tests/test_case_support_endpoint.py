from __future__ import annotations

import json
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import ai_api.app.main as ai_main


class CaseSupportEndpointTest(unittest.TestCase):
    @staticmethod
    def _diagnosis_payload() -> dict:
        fixture = Path(__file__).resolve().parents[2] / "contracts" / "ai_internal" / "fixtures" / "diagnosis.high.v1.json"
        return json.loads(fixture.read_text(encoding="utf-8"))["response"]

    def setUp(self) -> None:
        self.client = TestClient(ai_main.app)

    def tearDown(self) -> None:
        self.client.close()

    def test_snapshot_returns_brief_questions_and_warnings(self) -> None:
        response = self.client.post("/ai/case-support/snapshot", json={
            "case_id": "VP-HTTP-001",
            "diagnosis": self._diagnosis_payload(),
            "warnings": ["호출자 경고"],
        })

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["case_id"], "VP-HTTP-001")
        self.assertTrue(payload["case_brief"]["summary"])
        self.assertTrue(payload["recommended_questions"])
        self.assertIn("호출자 경고", payload["warnings"])
        self.assertNotIn("message_id", payload)
        self.assertNotIn("queue_id", payload)

    def test_missing_diagnosis_returns_safe_partial_result(self) -> None:
        response = self.client.post("/ai/case-support/snapshot", json={"case_id": "VP-HTTP-MISSING"})

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["case_brief"])
        self.assertTrue(response.json()["warnings"])


if __name__ == "__main__":
    unittest.main()
