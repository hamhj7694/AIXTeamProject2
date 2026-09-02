from __future__ import annotations

import json
import unittest
from pathlib import Path

from ai_api.app.domains.case_support.brief_update_service import BriefUpdateService
from ai_api.app.domains.case_support.brief_service import CaseBriefService
from contracts.ai_internal.mvp_workflow import (
    BriefUpdateResult,
    CaseBrief,
    CustomerAnswerResult,
    QuestionPriority,
    TargetField,
    UnresolvedItem,
)
from contracts.diagnosis import Evidence, RiskLevel


class BriefUpdateServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.service = BriefUpdateService()
        self.risk_evidence = [
            Evidence(turn=1, event_family="MONEY_MOVEMENT", subtype="TRANSFER", text="Send money now")
        ]
        self.counter_evidence = [
            Evidence(turn=2, event_family="CUSTOMER_REPLY", text="No transfer yet")
        ]
        self.brief = CaseBrief(
            summary="Caller requested a transfer.",
            incident_type="VOICE_PHISHING",
            risk_level=RiskLevel.HIGH,
            risk_score=88.0,
            risk_evidence=self.risk_evidence,
            counter_evidence=self.counter_evidence,
            unresolved_items=[
                UnresolvedItem(
                    target_field=TargetField.TRANSFER_STATUS,
                    description="Confirm whether a transfer occurred.",
                    priority=QuestionPriority.P0,
                ),
                UnresolvedItem(
                    target_field=TargetField.PERSONAL_INFORMATION_EXPOSURE,
                    description="Confirm personal information exposure.",
                    priority=QuestionPriority.P0,
                ),
            ],
            next_checks=["Confirm transfer status", "Confirm personal information exposure"],
        )

    def test_confirmed_transfer_resolves_only_its_pending_item(self) -> None:
        answer = CustomerAnswerResult(
            target_field=TargetField.TRANSFER_STATUS,
            raw_answer="I have not transferred any money.",
            structured_value="NOT_TRANSFERRED",
            confidence=0.95,
            unresolved=False,
            evidence_text="I have not transferred any money.",
        )

        result = self.service.update(self.brief, answer)

        self.assertEqual(result.resolved_items[0].target_field, TargetField.TRANSFER_STATUS)
        self.assertEqual(result.resolved_items[0].structured_value, "NOT_TRANSFERRED")
        self.assertEqual(result.resolved_items[0].evidence_text, answer.evidence_text)
        self.assertEqual(
            [item.target_field for item in result.unresolved_items],
            [TargetField.PERSONAL_INFORMATION_EXPOSURE],
        )
        self.assertEqual(result.next_checks, ["Confirm personal information exposure"])
        self.assertIn("transfer_status", result.updated_summary)
        self.assertIn("NOT_TRANSFERRED", result.updated_summary)

    def test_unresolved_answer_preserves_brief_and_answer_is_not_promoted(self) -> None:
        answer = CustomerAnswerResult(
            target_field=TargetField.TRANSFER_STATUS,
            raw_answer="I am not sure.",
            structured_value=None,
            confidence=0.2,
            unresolved=True,
            evidence_text="I am not sure.",
            warnings=["Ambiguous answer"],
        )

        result = self.service.update(self.brief, answer)

        self.assertEqual(result.resolved_items, [])
        self.assertEqual(result.unresolved_items, self.brief.unresolved_items)
        self.assertEqual(result.next_checks, self.brief.next_checks)
        self.assertEqual(result.updated_summary, self.brief.summary)

    def test_confirmed_personal_information_answer_is_resolved(self) -> None:
        answer = CustomerAnswerResult(
            target_field=TargetField.PERSONAL_INFORMATION_EXPOSURE,
            raw_answer="I did not provide personal information.",
            structured_value="NOT_EXPOSED",
            confidence=0.95,
            unresolved=False,
        )

        result = self.service.update_brief(self.brief, answer)

        self.assertEqual(result.resolved_items[0].target_field, TargetField.PERSONAL_INFORMATION_EXPOSURE)
        self.assertEqual(result.resolved_items[0].evidence_text, answer.raw_answer)
        self.assertNotIn(TargetField.PERSONAL_INFORMATION_EXPOSURE, [item.target_field for item in result.unresolved_items])

    def test_existing_risk_and_counter_evidence_are_preserved(self) -> None:
        answer = CustomerAnswerResult(
            target_field=TargetField.TRANSFER_STATUS,
            raw_answer="No transfer.",
            structured_value="NOT_TRANSFERRED",
            confidence=0.95,
            unresolved=False,
        )

        result = self.service.update(self.brief, answer)

        self.assertEqual(result.risk_evidence, self.risk_evidence)
        self.assertEqual(result.counter_evidence, self.counter_evidence)
        self.assertEqual(self.brief.risk_level, RiskLevel.HIGH)
        self.assertEqual(self.brief.risk_score, 88.0)

    def test_answer_for_non_pending_field_does_not_add_a_fact(self) -> None:
        answer = CustomerAnswerResult(
            target_field=TargetField.AUTHENTICATION_INFORMATION_EXPOSURE,
            raw_answer="I did not share an OTP.",
            structured_value="NOT_EXPOSED",
            confidence=0.95,
            unresolved=False,
        )

        result = self.service.update(self.brief, answer)

        self.assertEqual(result.resolved_items, [])
        self.assertEqual(result.unresolved_items, self.brief.unresolved_items)

    def test_result_is_validated_by_the_existing_contract(self) -> None:
        answer = CustomerAnswerResult(
            target_field=TargetField.TRANSFER_STATUS,
            raw_answer="No transfer.",
            structured_value="NOT_TRANSFERRED",
            confidence=0.95,
            unresolved=False,
        )
        result = self.service.update(self.brief, answer)

        validated = BriefUpdateResult.model_validate(result.model_dump())
        self.assertEqual(validated, result)

    def test_existing_diagnosis_fixture_can_be_updated_without_reanalysis(self) -> None:
        fixture = Path(__file__).resolve().parents[2] / "contracts" / "ai_internal" / "fixtures" / "diagnosis.high.v1.json"
        from contracts.diagnosis import DiagnosisResult

        diagnosis = DiagnosisResult.model_validate(json.loads(fixture.read_text(encoding="utf-8"))["response"])
        brief = CaseBriefService().build_brief(diagnosis)
        answer = CustomerAnswerResult(
            target_field=TargetField.TRANSFER_STATUS,
            raw_answer="No transfer was made.",
            structured_value="NOT_TRANSFERRED",
            confidence=0.95,
            unresolved=False,
        )

        result = self.service.update(brief, answer)

        self.assertEqual(result.resolved_items[0].target_field, TargetField.TRANSFER_STATUS)
        self.assertEqual(result.risk_evidence, brief.risk_evidence)
