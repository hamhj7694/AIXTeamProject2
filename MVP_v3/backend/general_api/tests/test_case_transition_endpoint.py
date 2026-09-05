from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
import unittest

import general_api.app.main as general_main


class CaseTransitionEndpointTest(unittest.TestCase):
    def setUp(self) -> None:
        self.original_repository = general_main.repository
        self.repository = AsyncMock()
        self.repository.get.return_value = {
            "case_id": "VP-TRANSITION", "version": 1, "client_request_id": None,
            "input_text": "test", "risk": "HIGH", "risk_score": 0.9,
            "mode": "PREVENT", "status": "TRIAGE", "initial_brief": "brief",
            "diagnosis": {}, "initial_report": None,
            "created_at": "2026-09-02T01:00:00+00:00", "updated_at": "2026-09-02T01:00:00+00:00",
        }
        self.repository.update_case.return_value = {**self.repository.get.return_value, "version": 2, "status": "VERIFYING"}
        general_main.repository = self.repository
        self.client = TestClient(general_main.app)

    def tearDown(self) -> None:
        general_main.repository = self.original_repository
        self.client.close()

    def test_patch_case_returns_updated_version(self) -> None:
        response = self.client.patch("/api/cases/VP-TRANSITION", json={"expected_version": 1, "status": "VERIFYING"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["version"], 2)
        self.repository.update_case.assert_awaited_once_with("VP-TRANSITION", 1, {"status": "VERIFYING"})

    def test_invalid_transition_returns_conflict(self) -> None:
        response = self.client.patch("/api/cases/VP-TRANSITION", json={"expected_version": 1, "status": "NEW"})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"]["code"], "INVALID_STATE_TRANSITION")
        self.repository.update_case.assert_not_awaited()

    def test_generic_patch_cannot_bypass_finalize(self) -> None:
        for changes in ({'status': 'CLOSED'}, {'mode': 'CLOSED'}, {'status': 'CLOSED', 'mode': 'CLOSED'}):
            with self.subTest(changes=changes):
                response = self.client.patch('/api/cases/VP-TRANSITION', json={'expected_version': 1, **changes})
                self.assertEqual(response.status_code, 409)
                self.assertEqual(response.json()['detail']['code'], 'INVALID_STATE_TRANSITION')
        self.repository.update_case.assert_not_awaited()

    def test_stale_version_returns_conflict(self) -> None:
        from general_api.app.domains.cases.repository import CaseVersionConflictError
        self.repository.update_case.side_effect = CaseVersionConflictError(3)
        response = self.client.patch("/api/cases/VP-TRANSITION", json={"expected_version": 1, "status": "VERIFYING"})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"]["current_version"], 3)

