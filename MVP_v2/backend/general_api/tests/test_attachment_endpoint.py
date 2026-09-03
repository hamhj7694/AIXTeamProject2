from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import general_api.app.main as general_main
from general_api.app.domains.cases.repository import InMemoryCaseRepository


class AttachmentEndpointTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(general_main.app)
        self.original_repository = general_main.repository
        self.original_storage_root = general_main.ATTACHMENT_STORAGE_ROOT
        self.temp_directory = tempfile.TemporaryDirectory()
        general_main.ATTACHMENT_STORAGE_ROOT = Path(self.temp_directory.name).resolve()
        repository = InMemoryCaseRepository()
        repository._records = [{"case_id": "VP-FILE", "updated_at": "2026-09-03T00:00:00+00:00"}]
        general_main.repository = repository

    def tearDown(self) -> None:
        general_main.repository = self.original_repository
        general_main.ATTACHMENT_STORAGE_ROOT = self.original_storage_root
        self.client.close()
        self.temp_directory.cleanup()

    def upload(self, visibility: str = "CUSTOMER"):
        return self.client.post(
            f"/api/cases/VP-FILE/attachments?file_name=evidence.png&uploaded_by=tester&visibility={visibility}",
            content=b"\x89PNG\r\n\x1a\nfixture",
            headers={"Content-Type": "image/png"},
        )

    def test_upload_link_and_download_attachment(self) -> None:
        uploaded = self.upload()
        self.assertEqual(uploaded.status_code, 201)
        attachment = uploaded.json()
        self.assertEqual(attachment["original_name"], "evidence.png")
        self.assertEqual(attachment["status"], "UPLOADED")
        self.assertNotIn("storage_path", attachment)

        message = self.client.post("/api/cases/VP-FILE/messages", json={
            "actor_type": "CUSTOMER", "actor_user_id": "customer-1", "actor_display_name": "고객",
            "content": "", "channel": "CUSTOMER", "audience": "CUSTOMER", "visibility": "CUSTOMER",
            "attachment_ids": [attachment["attachment_id"]],
        })
        self.assertEqual(message.status_code, 201)
        self.assertEqual(message.json()["attachments"][0]["status"], "LINKED")

        downloaded = self.client.get(attachment["download_url"])
        self.assertEqual(downloaded.status_code, 200)
        self.assertEqual(downloaded.content, b"\x89PNG\r\n\x1a\nfixture")

        ai_list = self.client.get("/api/internal/cases/VP-FILE/attachments")
        self.assertEqual(ai_list.status_code, 200)
        self.assertTrue(ai_list.json()[0]["ai_readable"])

    def test_customer_cannot_download_internal_attachment(self) -> None:
        uploaded = self.upload("BANK_INTERNAL")
        self.assertEqual(uploaded.status_code, 201)
        downloaded = self.client.get(uploaded.json()["download_url"])
        self.assertEqual(downloaded.status_code, 403)

    def test_rejects_spoofed_image_content(self) -> None:
        response = self.client.post(
            "/api/cases/VP-FILE/attachments?file_name=fake.png&uploaded_by=tester",
            content=b"not-an-image",
            headers={"Content-Type": "image/png"},
        )
        self.assertEqual(response.status_code, 415)


if __name__ == "__main__":
    unittest.main()
