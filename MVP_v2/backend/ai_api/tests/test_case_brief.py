from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_api.app.domains.case_support.brief_service import CaseBriefService
from contracts.diagnosis import DiagnosisResult, Evidence


FIXTURE_DIRECTORY = Path(__file__).resolve().parents[2] / "contracts" / "ai_internal" / "fixtures"


class CaseBriefServiceTest(unittest.IsolatedAsyncioTestCase):
    def _diagnosis(self, name: str) -> DiagnosisResult:
        payload = json.loads((FIXTURE_DIRECTORY / name).read_text(encoding="utf-8"))
        return DiagnosisResult.model_validate(payload["response"])

    def test_high_diagnosis_preserves_risk_evidence_and_requested_amount(self) -> None:
        diagnosis = self._diagnosis("diagnosis.high.v1.json")
        evidence = [Evidence(turn=1, event_family="MONEY_MOVEMENT", subtype="TRANSFER", text="500만원을 송금하라고 요구함")]
        diagnosis = diagnosis.model_copy(update={
            "evidence": evidence,
            "features": {**diagnosis.features, "requested_amount_max": 5_000_000},
        })
        brief = CaseBriefService().build_brief(diagnosis)
        self.assertEqual(brief.risk_level, diagnosis.risk_level)
        self.assertEqual(brief.risk_score, diagnosis.risk_score)
        self.assertEqual(brief.mentioned_amount_krw, 5_000_000)
        self.assertEqual(brief.transfer_context, evidence[0].text)
        self.assertEqual(brief.risk_evidence, diagnosis.evidence)
        self.assertTrue(brief.unresolved_items)
        self.assertEqual(brief.model_dump()["schema_version"], "case_brief.v1")

    def test_normal_diagnosis_keeps_absent_evidence_empty(self) -> None:
        brief = CaseBriefService().build_brief(self._diagnosis("diagnosis.normal.v1.json"))
        self.assertEqual(brief.risk_evidence, [])
        self.assertEqual(brief.counter_evidence, [])
        self.assertIsNone(brief.transfer_context)
        self.assertIsNone(brief.mentioned_amount_krw)

    async def test_fixture_mode_is_repeatable_without_openai(self) -> None:
        diagnosis = self._diagnosis("diagnosis.high.v1.json")
        with patch.dict(os.environ, {"CASE_BRIEF_MODE": "fixture"}, clear=False):
            first = await CaseBriefService().build(diagnosis)
            second = await CaseBriefService().build(diagnosis)
        self.assertFalse(first.used_fallback)
        self.assertEqual(first.brief, second.brief)

    async def test_openai_failure_returns_deterministic_fallback(self) -> None:
        diagnosis = self._diagnosis("diagnosis.normal.v1.json")
        with patch.dict(os.environ, {"CASE_BRIEF_MODE": "openai"}, clear=True):
            outcome = await CaseBriefService().build(diagnosis)
        self.assertTrue(outcome.used_fallback)
        self.assertIsNotNone(outcome.warning)
        self.assertEqual(outcome.brief, CaseBriefService().build_brief(diagnosis))
