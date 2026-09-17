from __future__ import annotations

import unittest
from datetime import datetime, timezone

from contracts.public_api.case_context_v2 import PublicCaseContextResourcesV2, PublicCaseFactV2
from contracts.public_api.customer_progress import CustomerProgressItem
from general_api.app.domains.cases.context_v3.panel import build_context_panel_v3
from general_api.app.domains.cases.context_v3.grounded import grounded_fact_item, validate_grounded_fact
from general_api.app.domains.cases.context_items import ContextItem


class ContextPanelV3Tests(unittest.TestCase):
    def test_grounded_plan_keeps_status_and_lineage(self):
        now = datetime.now(timezone.utc)
        fact = PublicCaseFactV2(
            fact_id="fact-request", case_id="VP-GROUNDED", semantic_key="circumstance.demand",
            value={"kind": "TRANSFER"}, display_value="송금·이체 요구", display_label="상대방 요구",
            source_kind="AI_EXTRACTION", status="PROPOSED",
            evidence_refs=[{"type": "STRUCTURED_ATOM", "id": "atom-transfer"}], version=1,
            created_at=now, updated_at=now,
        )
        plan = grounded_fact_item(fact)
        self.assertEqual(plan["text"], "상대방이 송금·이체를 요구한 정황입니다.")
        self.assertEqual(plan["status_label"], "담당자 확인 필요")
        self.assertEqual(plan["supporting_refs"][0]["id"], "atom-transfer")
        validate_grounded_fact(fact, plan["text"])
        with self.assertRaises(ValueError):
            validate_grounded_fact(fact, "확정된 송금이 완료됨")

    def test_grounded_projection_deduplicates_same_staff_sentence(self):
        now = datetime.now(timezone.utc)
        facts = [
            PublicCaseFactV2(fact_id="fact-tactic-1", case_id="VP-DEDUP", semantic_key="circumstance.tactic",
                             display_label="압박·조작 수법", value={"text": "가족·은행 직원과의 상의를 막은 정황"},
                             display_value="가족·은행 직원과의 상의를 막은 정황", source_kind="AI_EXTRACTION",
                             status="PROPOSED", evidence_refs=[], version=1, created_at=now, updated_at=now),
            PublicCaseFactV2(fact_id="fact-tactic-2", case_id="VP-DEDUP", semantic_key="circumstance.tactic",
                             display_label="압박·조작 수법", value={"kind": "ISOLATION"}, display_value="외부 연락 제한",
                             source_kind="AI_EXTRACTION", status="PROPOSED", evidence_refs=[], version=1,
                             created_at=now, updated_at=now),
        ]
        resources = PublicCaseContextResourcesV2(case_id="VP-DEDUP", context_revision=1, facts=facts)
        panel = build_context_panel_v3({"case_id": "VP-DEDUP", "initial_brief": "고립 정황", "context_revision": 1}, resources,
                                       view="bank", verifications=[], actions=[], messages=[], progress=[])
        tactics = next(section for section in panel.sections if section.section_id == "FRAUD_CIRCUMSTANCES").groups["tactics"]
        self.assertEqual(len(tactics), 1)
        self.assertEqual(tactics[0].display_value, "외부 연락이나 주변 상의를 제한한 정황입니다.")
        self.assertIn("확정 사실 0건 · 검토 대기 1건", panel.sections[0].items[-1].display_value)

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

    def test_grounded_statement_uses_supporting_atom_specificity(self):
        now = datetime.now(timezone.utc)
        fact = PublicCaseFactV2(
            fact_id="fact-otp", case_id="VP-FINE", semantic_key="exposure.authentication_information",
            value={"status": "REQUESTED"}, display_value="인증정보 제공 요구", display_label="인증정보 노출",
            source_kind="AI_EXTRACTION", status="PROPOSED",
            evidence_refs=[{"type": "STRUCTURED_ATOM", "id": "atom-otp"}], version=1,
            created_at=now, updated_at=now,
        )
        panel = build_context_panel_v3(
            {"case_id": "VP-FINE", "initial_brief": "인증정보 요구", "context_revision": 1,
             "diagnosis": {"semantic_atoms": [{
                 "atom_id": "atom-otp", "predicate": "DISCLOSE_OTP", "atom_class": "DISCLOSURE_REQUEST",
                 "auth_secret_type": "OTP", "action_state": "REQUESTED", "source_turn_id": 1,
                 "observed_terms": [{"normalized_code": "AUTH.OTP", "surface_form": "OTP"}],
             }]}},
            PublicCaseContextResourcesV2(case_id="VP-FINE", context_revision=1, facts=[fact]),
            view="bank", verifications=[], actions=[], messages=[], progress=[],
        )
        item = next(item for section in panel.sections for item in section.items if item.item_id == "fact-otp")
        self.assertEqual(item.display_value, "상대방이 OTP 제공을 요구한 정황입니다.")

    def test_grounded_statement_keeps_distinct_communication_controls(self):
        now = datetime.now(timezone.utc)
        facts = [
            PublicCaseFactV2(
                fact_id="fact-family", case_id="VP-CONTROL", semantic_key="circumstance.tactic",
                value={"kind": "ISOLATION"}, display_value="외부 연락 제한", display_label="압박·조작 수법",
                source_kind="AI_EXTRACTION", status="PROPOSED",
                evidence_refs=[{"type": "STRUCTURED_ATOM", "id": "atom-family"}], version=1,
                created_at=now, updated_at=now,
            ),
            PublicCaseFactV2(
                fact_id="fact-bank", case_id="VP-CONTROL", semantic_key="circumstance.tactic",
                value={"kind": "ISOLATION"}, display_value="외부 연락 제한", display_label="압박·조작 수법",
                source_kind="AI_EXTRACTION", status="PROPOSED",
                evidence_refs=[{"type": "STRUCTURED_ATOM", "id": "atom-bank"}], version=1,
                created_at=now, updated_at=now,
            ),
        ]
        case = {"case_id": "VP-CONTROL", "initial_brief": "연락 통제", "context_revision": 1, "diagnosis": {"semantic_atoms": [
            {"atom_id": "atom-family", "predicate": "KEEP_SECRET", "atom_class": "COMMUNICATION_CONTROL", "communication_control": "NO_FAMILY_DISCLOSURE", "source_turn_id": 1},
            {"atom_id": "atom-bank", "predicate": "AVOID_EXTERNAL_CONTACT", "atom_class": "COMMUNICATION_CONTROL", "communication_control": "NO_BANK_CONTACT", "source_turn_id": 2},
        ]}}
        panel = build_context_panel_v3(case, PublicCaseContextResourcesV2(case_id="VP-CONTROL", context_revision=1, facts=facts),
                                       view="bank", verifications=[], actions=[], messages=[], progress=[])
        tactics = next(section for section in panel.sections if section.section_id == "FRAUD_CIRCUMSTANCES").groups["tactics"]
        texts = {item.display_value for item in tactics}
        self.assertIn("상대방이 가족에게 알리지 말라고 요구한 정황입니다.", texts)
        self.assertIn("상대방이 은행에 연락하지 말라고 요구한 정황입니다.", texts)


if __name__ == "__main__":
    unittest.main()
