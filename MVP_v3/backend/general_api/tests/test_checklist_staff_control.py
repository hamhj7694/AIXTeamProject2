import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import general_api.app.main as main
from general_api.app.domains.cases.repository import InMemoryCaseRepository


class ChecklistStaffControlTest(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryCaseRepository()
        self.repository._records = [{"case_id": "VP-CHECKLIST"}]
        self.patch = patch.object(main, "repository", self.repository)
        self.patch.start()
        self.client = TestClient(main.app)
        created = self.client.post("/api/cases/VP-CHECKLIST/actions", json={
            "action_type": "AI_CHECKLIST:P0:transfer_status",
            "actor_type": "SYSTEM",
            "note": "실제 송금 여부 확인 필요",
        })
        self.assertEqual(created.status_code, 201, created.text)
        self.action_id = created.json()["action_id"]
        self.url = f"/api/cases/VP-CHECKLIST/actions/{self.action_id}"

    def tearDown(self):
        self.client.close()
        self.patch.stop()

    def change(self, **values):
        return self.client.patch(self.url, json={"updated_by": "은행 담당자", **values})

    def test_staff_can_edit_exclude_restore_and_complete_ai_suggestion(self):
        edited = self.change(note="송금 시각과 금액을 고객에게 확인")
        self.assertEqual(edited.status_code, 200, edited.text)
        self.assertEqual(edited.json()["note"], "송금 시각과 금액을 고객에게 확인")
        self.assertEqual(edited.json()["status"], "REQUESTED")

        excluded = self.change(status="CANCELLED")
        self.assertEqual(excluded.status_code, 200, excluded.text)
        self.assertEqual(excluded.json()["status"], "CANCELLED")

        restored = self.change(status="REQUESTED")
        self.assertEqual(restored.json()["status"], "REQUESTED")
        completed = self.change(status="COMPLETED")
        self.assertEqual(completed.json()["status"], "COMPLETED")

        events = [item for item in self.repository._events if item["event_type"] == "CASE_CHECKLIST_UPDATED"]
        self.assertEqual(len(events), 4)
        self.assertTrue(events[0]["payload"]["note_changed"])

    def test_empty_or_missing_change_is_rejected(self):
        self.assertEqual(self.change().status_code, 422)
        self.assertEqual(self.change(note="   ").status_code, 422)


if __name__ == "__main__":
    unittest.main()
