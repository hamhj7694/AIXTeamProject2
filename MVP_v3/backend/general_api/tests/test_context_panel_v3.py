from __future__ import annotations

import unittest
from datetime import datetime, timezone

from contracts.public_api.case_context_v2 import PublicCaseContextResourcesV2, PublicCaseFactV2
from contracts.public_api.customer_progress import CustomerProgressItem
from general_api.app.domains.cases.context_v3.panel import build_context_panel_v3
from general_api.app.domains.cases.context_items import ContextItem


class ContextPanelV3Tests(unittest.TestCase):
    def test_exact_sections_masking_and_customer_allowlist(self):
        now = datetime.now(timezone.utc)
        facts = [
            PublicCaseFactV2(fact_id="fact-private", case_id="VP-1", semantic_key="offender.contact", display_label="연락처",
                             value={"phone": "01012345678"}, display_value="010-1234-5678", source_kind="CUSTOMER_STATEMENT",
                             status="PROPOSED", evidence_refs=[], version=1, created_at=now, updated_at=now),
            PublicCaseFactV2(fact_id="fact-shared", case_id="VP-1", semantic_key="offender.claimed_organization", display_label="사칭 기관",
                             value={"name": "검찰"}, display_value="검찰", source_kind="CUSTOMER_STATEMENT", status="CONFIRMED",
                             visibility="CUSTOMER_SHARED", confirmed_by="reviewer", confirmed_at=now, version=2, created_at=now, updated_at=now),
        ]
        resources = PublicCaseContextResourcesV2(case_id="VP-1", context_revision=3, facts=facts)
        bank = build_context_panel_v3({"case_id": "VP-1", "initial_brief": "검찰 사칭 의심", "context_revision": 3}, resources, view="bank", verifications=[], actions=[], messages=[], progress=[])
        self.assertEqual(len(bank.sections), 7)
        contact = next(item for section in bank.sections for item in section.items if item.item_id == "fact-private")
        self.assertTrue(contact.masked)
        self.assertNotIn("010-1234-5678", contact.display_value)
        customer = build_context_panel_v3(
            {"case_id": "VP-1", "context_revision": 3}, resources, view="customer", verifications=[], actions=[],
            messages=[
                {"message_id": "public-message", "actor_type": "BANK_STAFF", "visibility": "CUSTOMER", "content": "공개 안내"},
                {"message_id": "private-message", "actor_type": "BANK_STAFF", "visibility": "BANK_INTERNAL", "content": "내부 판단"},
            ],
            progress=[CustomerProgressItem(step="REPORT", label="기관 신고 접수", status="IN_PROGRESS", summary="접수 확인 중", revision=2)],
        )
        visible = [item.item_id for section in customer.sections for item in section.items]
        self.assertEqual(visible, ["fact-shared", "progress-REPORT", "public-message"])
        customer_text = " ".join(item.display_value for section in customer.sections for item in section.items)
        self.assertNotIn("내부 판단", customer_text)

    def test_stale_summary_override_is_preserved_but_not_projected_over_new_revision(self):
        resources = PublicCaseContextResourcesV2(case_id="VP-1", context_revision=4)
        stale = ContextItem(item_id="ctx-summary", case_id="VP-1", section="SUMMARY", semantic_key="display", item_version=2,
                            staff_text="오래된 직원 요약", edited_by="staff", override_scope="SECTION_DISPLAY", base_projection_revision=3)
        panel = build_context_panel_v3({"case_id": "VP-1", "initial_brief": "최신 사건 요약", "context_revision": 4}, resources,
                                       view="bank", verifications=[], actions=[], messages=[], progress=[], display_items=[stale])
        summary = panel.sections[0]
        self.assertNotIn("오래된 직원 요약", [item.display_value for item in summary.items])
        self.assertIn("최신 사건 요약", [item.display_value for item in summary.items])


if __name__ == "__main__":
    unittest.main()
