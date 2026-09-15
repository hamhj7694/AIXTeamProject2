from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from contracts.public_api.case_context_v2 import PublicCaseContextResourcesV2
import general_api.app.main as main
from general_api.app.domains.cases.context_v3.panel import build_context_panel_v3
from general_api.app.domains.cases.repository import InMemoryCaseRepository


class ContextTimelinePanelSyncTests(unittest.TestCase):
    def test_action_journal_projects_to_staff_panel_with_stable_id(self):
        action_id = "action-sync-1"
        panel = build_context_panel_v3(
            {"case_id": "VP-1", "initial_brief": "brief", "context_revision": 7},
            PublicCaseContextResourcesV2(case_id="VP-1", context_revision=7),
            view="bank", verifications=[],
            actions=[{"action_id": action_id, "action_type": "CUSTOMER_CALLBACK", "actor_type": "BANK_STAFF", "status": "COMPLETED", "note": "확인 완료"}],
            messages=[], progress=[],
        )
        items = [item for section in panel.sections for group in section.groups.values() for item in group]
        projected = next(item for item in items if item.item_id == action_id)
        self.assertEqual(projected.source_kind, "ACTION_RECORD")
        self.assertEqual(projected.visibility, "BANK_INTERNAL")
        self.assertEqual(panel.source_revision, 7)

    def test_customer_projection_excludes_staff_action_journal(self):
        panel = build_context_panel_v3(
            {"case_id": "VP-1", "context_revision": 2},
            PublicCaseContextResourcesV2(case_id="VP-1", context_revision=2),
            view="customer", verifications=[],
            actions=[{"action_id": "internal-1", "action_type": "CUSTOMER_CALLBACK", "actor_type": "BANK_STAFF", "status": "COMPLETED", "note": "internal"}],
            messages=[], progress=[],
        )
        ids = [item.item_id for section in panel.sections for item in section.items]
        ids.extend(item.item_id for section in panel.sections for group in section.groups.values() for item in group)
        self.assertNotIn("internal-1", ids)

    async def _action_round_trip(self):
        repository = InMemoryCaseRepository()
        repository._records = [{"case_id": "VP-1", "initial_brief": "brief", "context_revision": 1}]
        action = await repository.create_action("VP-1", {
            "action_type": "CUSTOMER_CALLBACK", "actor_type": "BANK_STAFF", "note": "고객 재확인",
        })
        created_event = (await repository.list_events("VP-1"))[-1]
        self.assertEqual(created_event["payload"]["action_id"], action["action_id"])

        await repository.update_action("VP-1", action["action_id"], "COMPLETED", "staff-1", "확인 완료")
        updated = (await repository.list_actions("VP-1"))[0]
        updated_event = (await repository.list_events("VP-1"))[-1]
        panel = build_context_panel_v3(
            repository._records[0], PublicCaseContextResourcesV2(case_id="VP-1", context_revision=1),
            view="bank", verifications=[], actions=[updated], messages=[], progress=[],
        )
        projected = next(
            item for section in panel.sections for group in section.groups.values() for item in group
            if item.source_kind == "ACTION_RECORD"
        )
        self.assertEqual(updated["action_id"], action["action_id"])
        self.assertEqual(updated_event["payload"]["action_id"], action["action_id"])
        self.assertEqual(projected.item_id, action["action_id"])
        self.assertEqual(projected.visibility, "BANK_INTERNAL")

    def test_action_create_update_timeline_and_panel_keep_one_resource_id(self):
        import asyncio
        asyncio.run(self._action_round_trip())


class ContextPanelOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryCaseRepository()
        self.repository._records = [{"case_id": "CASE-A", "context_revision": 1, "initial_brief": "brief"}]
        self.repository._members = [
            {"case_id": "CASE-A", "user_id": "customer-a", "role": "CUSTOMER", "status": "ACTIVE"},
            {"case_id": "CASE-A", "user_id": "inactive-customer", "role": "CUSTOMER", "status": "INACTIVE"},
            {"case_id": "CASE-A", "user_id": "bank-owner", "role": "CASE_OWNER", "status": "ACTIVE"},
        ]
        self.repository_patch = patch.object(main, "repository", self.repository)
        self.env_patch = patch.dict(os.environ, {"MVP_OPEN_PERMISSIONS": "1"})
        self.repository_patch.start()
        self.env_patch.start()
        self.client = TestClient(main.app)

    def tearDown(self):
        self.client.close()
        self.env_patch.stop()
        self.repository_patch.stop()

    def test_customer_can_read_only_its_own_customer_projection(self):
        response = self.client.get("/api/cases/CASE-A/context-v2/panel?view=customer&actor_user_id=customer-a")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["view"], "customer")

    def test_other_and_inactive_customers_are_forbidden(self):
        for actor in ("customer-b", "inactive-customer"):
            with self.subTest(actor=actor):
                response = self.client.get(f"/api/cases/CASE-A/context-v2/panel?view=customer&actor_user_id={actor}")
                self.assertEqual(response.status_code, 403, response.text)

    def test_customer_member_cannot_use_bank_projection_even_in_demo_mode(self):
        response = self.client.get("/api/cases/CASE-A/context-v2/panel?view=bank&actor_user_id=customer-a")
        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(
            self.client.get("/api/cases/CASE-A/context-display?actor_user_id=customer-a").json(),
            [],
        )
        edit = self.client.patch(
            "/api/cases/CASE-A/context-display/SUMMARY?actor_user_id=customer-a",
            json={"expected_version": 0, "operation": "EDIT", "text": "internal"},
        )
        self.assertEqual(edit.status_code, 403, edit.text)

    def test_bank_member_can_read_bank_projection(self):
        response = self.client.get("/api/cases/CASE-A/context-v2/panel?view=bank&actor_user_id=bank-owner")
        self.assertEqual(response.status_code, 200, response.text)
