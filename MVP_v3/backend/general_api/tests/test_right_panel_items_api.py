from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import general_api.app.main as main
from general_api.app.domains.cases.repository import InMemoryCaseRepository


class RightPanelItemsApiTest(unittest.TestCase):
    def setUp(self):
        permissions = patch.dict(os.environ, {"MVP_OPEN_PERMISSIONS": "0"})
        permissions.start()
        self.addCleanup(permissions.stop)
        self.repo = InMemoryCaseRepository()
        self.repo._records = [{"case_id": "VP-RP"}]
        self.repo._members = [{"case_id": "VP-RP", "user_id": "staff", "role": "CHAT_OPERATOR", "status": "ACTIVE"}]
        self.repo_patch = patch.object(main, "repository", self.repo)
        self.repo_patch.start()
        self.addCleanup(self.repo_patch.stop)
        self.client = TestClient(main.app)
        self.addCleanup(self.client.close)
        self.base = "/api/cases/VP-RP/right-panel/items"

    def mutate(self, section: str, key: str, **values):
        return self.client.put(
            f"{self.base}/{section}/{key}?actor_user_id=staff",
            json=values,
        )

    def test_shared_add_edit_archive_restore_and_permanent_hide(self):
        self.assertEqual(self.client.get(self.base + "?actor_user_id=staff").json(), [])
        created = self.mutate("RP_SIGNAL", "staff:test-item", expected_version=0, operation="ADD", text="직원이 추가한 정황")
        self.assertEqual(created.status_code, 200, created.text)
        self.assertTrue(created.json()["staff_authored"])
        self.assertEqual(created.json()["ai_text"], "직원이 추가한 정황")

        edited = self.mutate("RP_SIGNAL", "staff:test-item", expected_version=1, operation="EDIT",
                             text="직원이 수정한 정황", source_text="직원이 추가한 정황")
        self.assertEqual(edited.status_code, 200, edited.text)
        self.assertEqual(edited.json()["staff_text"], "직원이 수정한 정황")
        self.assertEqual(self.mutate("RP_SIGNAL", "staff:test-item", expected_version=1, operation="ARCHIVE").status_code, 409)

        archived = self.mutate("RP_SIGNAL", "staff:test-item", expected_version=2, operation="ARCHIVE")
        self.assertEqual(archived.status_code, 200, archived.text)
        self.assertEqual(archived.json()["deleted_by"], "staff")
        restored = self.mutate("RP_SIGNAL", "staff:test-item", expected_version=3, operation="RESTORE")
        self.assertEqual(restored.status_code, 200, restored.text)
        archived_again = self.mutate("RP_SIGNAL", "staff:test-item", expected_version=4, operation="ARCHIVE")
        self.assertEqual(archived_again.status_code, 200, archived_again.text)
        hidden = self.mutate("RP_SIGNAL", "staff:test-item", expected_version=5, operation="PERMANENT_HIDE")
        self.assertEqual(hidden.status_code, 200, hidden.text)
        self.assertTrue(hidden.json()["permanently_hidden"])
        self.assertEqual(self.mutate("RP_SIGNAL", "staff:test-item", expected_version=6, operation="RESTORE").status_code, 409)

        persisted = self.client.get(self.base + "?actor_user_id=staff").json()
        self.assertEqual(len(persisted), 1)
        self.assertTrue(persisted[0]["permanently_hidden"])
        self.assertEqual(self.client.get(self.base + "?actor_user_id=outsider").status_code, 403)

    def test_work_status_is_only_incomplete_or_completed(self):
        added = self.mutate("RP_WORK", "staff:task", expected_version=0, operation="ADD", text="고객 답변 확인")
        self.assertEqual(added.status_code, 200, added.text)
        completed = self.mutate("RP_WORK", "staff:task", expected_version=1, operation="SET_STATUS", display_status="COMPLETED")
        self.assertEqual(completed.status_code, 200, completed.text)
        self.assertEqual(completed.json()["display_status"], "COMPLETED")
        self.assertEqual(self.mutate("RP_WORK", "staff:task", expected_version=2, operation="SET_STATUS", display_status="IN_PROGRESS").status_code, 422)


if __name__ == "__main__":
    unittest.main()
