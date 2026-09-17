import asyncio
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from contracts.public_api.case_workflow import (
    PublicCreateActionRequest,
    PublicUpdateActionRequest,
    to_public_action,
)
from general_api.app.domains.cases.repository import (
    CaseVersionConflictError,
    InMemoryCaseRepository,
)


class ActionContractTests(unittest.TestCase):
    def test_create_and_update_contract_accept_expanded_action_fields(self):
        created = PublicCreateActionRequest(
            action_type="CUSTOMER_CALLBACK",
            actor_type="BANK_STAFF",
            title="고객 재확인",
            note="송금 여부를 다시 확인한다.",
            visibility="BANK_INTERNAL",
        )
        updated = PublicUpdateActionRequest(
            expected_version=1,
            status="IN_PROGRESS",
            title="고객 재확인 진행",
            visibility="CUSTOMER_SHARED",
            updated_by="staff-1",
        )
        self.assertEqual(created.title, "고객 재확인")
        self.assertEqual(updated.status, "IN_PROGRESS")
        self.assertEqual(updated.expected_version, 1)

    def test_legacy_update_request_remains_valid_without_expected_version(self):
        request = PublicUpdateActionRequest(status="COMPLETED", updated_by="staff-1")
        self.assertIsNone(request.expected_version)

    def test_in_memory_action_persists_contract_fields_and_rejects_stale_version(self):
        async def exercise():
            repository = InMemoryCaseRepository()
            repository._records = [{"case_id": "VP-ACTION", "context_revision": 1}]

            legacy = await repository.create_action("VP-ACTION", {
                "action_type": "CUSTOMER_CALLBACK", "actor_type": "BANK_STAFF", "note": "기존 기록",
            })
            self.assertIsNone(legacy["title"])
            self.assertEqual(legacy["version"], 1)
            self.assertEqual(legacy["visibility"], "BANK_INTERNAL")
            self.assertEqual(legacy["updated_at"], legacy["created_at"])

            updated = await repository.update_action(
                "VP-ACTION", legacy["action_id"], "IN_PROGRESS", "staff-1",
                title="고객 재확인", visibility="CUSTOMER_SHARED", expected_version=1,
            )
            self.assertEqual(updated["title"], "고객 재확인")
            self.assertEqual(updated["status"], "IN_PROGRESS")
            self.assertEqual(updated["version"], 2)
            self.assertEqual(updated["updated_by"], "staff-1")
            self.assertEqual(updated["visibility"], "CUSTOMER_SHARED")
            self.assertEqual(to_public_action(updated).version, 2)

            with self.assertRaises(CaseVersionConflictError) as conflict:
                await repository.update_action(
                    "VP-ACTION", legacy["action_id"], "COMPLETED", "staff-2", expected_version=1,
                )
            self.assertEqual(conflict.exception.current_version, 2)

        asyncio.run(exercise())

    def test_action_patch_returns_409_for_stale_expected_version(self):
        import general_api.app.main as main

        repository = InMemoryCaseRepository()
        repository._records = [{"case_id": "VP-ACTION-API", "context_revision": 1}]
        action = asyncio.run(repository.create_action("VP-ACTION-API", {
            "action_type": "CUSTOMER_CALLBACK", "actor_type": "BANK_STAFF", "note": "확인 요청",
        }))
        with patch.object(main, "repository", repository), patch.dict(os.environ, {"MVP_OPEN_PERMISSIONS": "1"}):
            with TestClient(main.app) as client:
                first = client.patch(
                    f"/api/cases/VP-ACTION-API/actions/{action['action_id']}?actor_user_id=staff-1",
                    json={"expected_version": 1, "status": "IN_PROGRESS", "updated_by": "staff-1"},
                )
                self.assertEqual(first.status_code, 200, first.text)
                self.assertEqual(first.json()["version"], 2)

                stale = client.patch(
                    f"/api/cases/VP-ACTION-API/actions/{action['action_id']}?actor_user_id=staff-1",
                    json={"expected_version": 1, "status": "COMPLETED", "updated_by": "staff-2"},
                )
                self.assertEqual(stale.status_code, 409, stale.text)
                self.assertEqual(stale.json()["detail"]["code"], "VERSION_CONFLICT")
                self.assertEqual(stale.json()["detail"]["current_version"], 2)


if __name__ == "__main__":
    unittest.main()
