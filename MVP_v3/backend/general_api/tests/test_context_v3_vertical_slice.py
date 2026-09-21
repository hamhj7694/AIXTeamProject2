from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import general_api.app.main as main
from ai_api.app.domains.case_support.context_fact_extraction_service import ContextFactExtractionService
from contracts.public_api.case_context_v2 import PublicCaseContextResourcesV2
from general_api.app.domains.cases.context_v3.panel import build_context_panel_v3
from general_api.app.domains.cases.repository import InMemoryCaseRepository


class ContextV3VerticalSliceTest(unittest.IsolatedAsyncioTestCase):
    async def test_free_staff_and_customer_messages_only_create_proposals(self) -> None:
        repository = InMemoryCaseRepository()
        repository._records = [{"case_id": "VP-V3-MESSAGE", "context_revision": 1, "status": "TRIAGE"}]
        extractor = ContextFactExtractionService()
        with patch.object(main, "repository", repository), patch.object(
            main.service.ai_client, "extract_context_facts", new=AsyncMock(side_effect=extractor.extract),
        ):
            for actor_type in ("BANK_STAFF", "CUSTOMER"):
                message = await repository.append_message("VP-V3-MESSAGE", {
                    "actor_type": actor_type, "actor_user_id": actor_type.lower(),
                    "actor_display_name": actor_type, "content": "100만원 송금했습니다.",
                    "channel": "TEAM" if actor_type == "BANK_STAFF" else "CUSTOMER",
                    "audience": "BANK_INTERNAL" if actor_type == "BANK_STAFF" else "CUSTOMER",
                    "visibility": "BANK_INTERNAL" if actor_type == "BANK_STAFF" else "CUSTOMER",
                    "message_kind": "CHAT",
                })
                await main.enqueue_context_extraction(message)
                await main.process_message_context_extraction("VP-V3-MESSAGE", message["message_id"])
            facts = (await main.case_context_v2_repository().list_resources("VP-V3-MESSAGE")).facts

        self.assertTrue(facts)
        self.assertEqual({fact.source_kind for fact in facts}, {"STAFF_OBSERVATION", "CUSTOMER_STATEMENT"})
        self.assertTrue(all(fact.status == "PROPOSED" for fact in facts))
        self.assertTrue(all(fact.confirmed_by is None for fact in facts))

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

    async def test_structured_a_result_is_projected_for_bank_only(self) -> None:
        case = {
            "case_id": "VP-STRUCTURED", "context_revision": 4,
            "initial_brief": "구조화 분석", "status": "TRIAGE",
            "diagnosis": {
                "semantic_atoms": [{
                    "atom_id": "ATM-1", "atom_class": "ACTION_REQUEST", "predicate": "DISCLOSE_OTP",
                    "action_state": "REQUESTED", "modality": None, "claim_status": "UNVERIFIED", "source_turn_id": 1,
                }],
                "semantic_relations": [],
                "context_signals": [{
                    "signal_id": "SIG-1", "signal_code": "AUTH_INFO_REQUEST", "severity": "HIGH",
                    "confidence": 0.9, "claim_status": "CALLER_CLAIM", "atom_ids": ["ATM-1"],
                }],
                "case_context_features": {"requested_action_codes": ["REQUEST_AUTH_INFO"]},
            },
        }
        resources = PublicCaseContextResourcesV2(case_id="VP-STRUCTURED", context_revision=4)
        bank_panel = build_context_panel_v3(case, resources, view="bank", verifications=[], actions=[], messages=[], progress=[])
        customer_panel = build_context_panel_v3(case, resources, view="customer", verifications=[], actions=[], messages=[], progress=[])

        self.assertIsNotNone(bank_panel.structured_context)
        self.assertEqual(len(bank_panel.structured_context.signals), 1)
        self.assertEqual(bank_panel.structured_context.signals[0].atom_ids, ["ATM-1"])
        self.assertIsNone(customer_panel.structured_context)

    def test_bank_evidence_ref_has_lineage_summary(self) -> None:
        now = datetime.now(timezone.utc)
        case = {
            "case_id": "VP-EVIDENCE", "context_revision": 1,
            "initial_brief": "근거 연결", "status": "TRIAGE",
            "diagnosis": {
                "semantic_atoms": [{"atom_id": "ATM-1", "atom_class": "ACTION_REQUEST", "predicate": "DISCLOSE_OTP", "source_turn_id": 1}],
                "context_signals": [{"signal_id": "SIG-1", "signal_code": "AUTH_INFO_REQUEST", "severity": "HIGH", "confidence": 0.9, "claim_status": "CALLER_CLAIM", "atom_ids": ["ATM-1"]}],
            },
        }
        resources = PublicCaseContextResourcesV2.model_validate({
            "case_id": "VP-EVIDENCE", "context_revision": 1, "facts": [{
                "fact_id": "FACT-1", "case_id": "VP-EVIDENCE", "semantic_key": "exposure.authentication_information",
                "display_label": "인증정보 노출", "value": {"status": "REQUESTED"}, "display_value": "인증정보 제공 요구",
                "source_kind": "AI_EXTRACTION", "status": "PROPOSED",
                "evidence_refs": [{"type": "STRUCTURED_SIGNAL", "id": "SIG-1"}],
                "visibility": "BANK_INTERNAL", "version": 1, "created_at": now, "updated_at": now,
            }],
        })
        panel = build_context_panel_v3(case, resources, view="bank", verifications=[], actions=[], messages=[], progress=[])
        item = panel.sections[1].items[0]
        self.assertEqual(item.evidence_refs[0].summary, "분석 근거 · 인증정보 제공 요구")


if __name__ == "__main__":
    unittest.main()
