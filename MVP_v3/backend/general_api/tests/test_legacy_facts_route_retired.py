import unittest

from fastapi.testclient import TestClient

from general_api.app.main import app


class LegacyFactsRouteRetiredTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()

    def test_legacy_fact_list_is_gone(self) -> None:
        response = self.client.get("/api/cases/VP-1/facts")
        self.assertEqual(response.status_code, 410)
        self.assertEqual(response.json()["detail"]["code"], "LEGACY_FACTS_DISABLED")

    def test_legacy_fact_confirmation_is_gone(self) -> None:
        response = self.client.post(
            "/api/cases/VP-1/facts/fact-1/confirm",
            json={"confirmed_by": "operator"},
        )
        self.assertEqual(response.status_code, 410)
        self.assertEqual(response.json()["detail"]["code"], "LEGACY_FACTS_DISABLED")
