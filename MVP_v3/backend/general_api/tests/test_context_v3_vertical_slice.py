from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

import general_api.app.main as main
from ai_api.app.domains.case_support.context_fact_extraction_service import ContextFactExtractionService
from general_api.app.domains.cases.context_v3.panel import build_context_panel_v3
from general_api.app.domains.cases.repository import InMemoryCaseRepository


class ContextV3VerticalSliceTest(unittest.IsolatedAsyncioTestCase):
    async def test_committed_customer_message_flows_to_proposals_and_three_sections(self) -> None:
        repository = InMemoryCaseRepository()
        repository._records = [{"case_id": "VP-V3-E2E", "context_revision": 1, "initial_brief": "전화 사칭 의심", "status": "TRIAGE"}]
        message = await repository.append_message("VP-V3-E2E", {
            "actor_type": "CUSTOMER", "actor_user_id": "customer", "actor_display_name": "고객",
            "content": "검찰이라고 전화가 왔고 계좌가 범죄에 연루됐다고 했어요. OTP를 알려줬어요.",
            "channel": "CUSTOMER", "audience": "CUSTOMER", "visibility": "CUSTOMER", "message_kind": "CHAT",
        })
        extractor = ContextFactExtractionService()
        with patch.object(main, "repository", repository), patch.object(
            main.service.ai_client, "extract_context_facts", new=AsyncMock(side_effect=extractor.extract),
        ):
            await main.enqueue_context_extraction(message)
            await main.process_message_context_extraction("VP-V3-E2E", message["message_id"])
            resources = await main.case_context_v2_repository().list_resources("VP-V3-E2E")

        keys = {item.semantic_key for item in resources.facts}
        self.assertIn("exposure.authentication_information", keys)
        self.assertIn("offender.claimed_organization", keys)
        self.assertIn("offender.incident_claim", keys)
        self.assertTrue(all(item.status == "PROPOSED" for item in resources.facts))
        self.assertEqual((await repository.list_messages("VP-V3-E2E"))[0]["message_id"], message["message_id"])
        panel = build_context_panel_v3(repository._records[0], resources, view="bank", verifications=[], actions=[], messages=[], progress=[])
        populated = {section.section_id for section in panel.sections if section.items or any(section.groups.values())}
        self.assertTrue({"EXPOSURE", "IMPERSONATION_CONTACT", "FRAUD_CIRCUMSTANCES"}.issubset(populated))


if __name__ == "__main__":
    unittest.main()
