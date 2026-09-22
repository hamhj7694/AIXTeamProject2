from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

import general_api.app.main as general_main
from general_api.app.domains.cases.repository import InMemoryCaseRepository


class AttachmentEndpointTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(general_main.app)
        self.original_repository = general_main.repository
        repository = InMemoryCaseRepository()
        repository._records = [{"case_id": "VP-FILE", "updated_at": "2026-09-03T00:00:00+00:00"}]
        general_main.repository = repository

    def tearDown(self) -> None:
        general_main.repository = self.original_repository
        self.client.close()

    def test_attachment_api_is_retired(self) -> None:
        upload = self.client.post(
            "/api/cases/VP-FILE/attachments?file_name=evidence.png&uploaded_by=tester",
            content=b"fixture",
            headers={"Content-Type": "image/png"},
        )
        listing = self.client.get("/api/cases/VP-FILE/attachments")
        download = self.client.get("/api/cases/VP-FILE/attachments/att-1/content")
        self.assertEqual([upload.status_code, listing.status_code, download.status_code], [410, 410, 410])
        self.assertEqual(upload.json()["detail"]["code"], "ATTACHMENTS_DISABLED")


if __name__ == "__main__":
    unittest.main()
