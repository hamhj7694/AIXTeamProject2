from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from contracts.diagnosis import CaseContextFeatures, ExtractedEvent, WindowAnalysisResult
from ai_api.app.domains.diagnosis.extractor import build_case_context_features
from ai_api.app.domains.diagnosis.service import DiagnosisService


class ContextFeatureSafetyTest(unittest.TestCase):
    def test_non_requested_action_does_not_become_a_demand(self):
        event = ExtractedEvent(
            event_family="ACTION_REQUEST", subtype="AUTH_INFO", is_requested=False,
            evidence_turn_id=1, detected_at_turn=1,
            evidence_text="인증번호는 요청하지 않습니다.",
        )
        features = build_case_context_features([event])
        self.assertEqual(features.requested_action_codes, [])
        self.assertEqual(features.exposure_risk_codes, [])
        self.assertNotIn(event.evidence_text, features.model_dump_json())

    def test_features_preserve_multiple_turns_without_source_text(self):
        events = [ExtractedEvent(
            event_family="MONEY_MOVEMENT", subtype="TRANSFER", is_requested=True,
            evidence_turn_id=turn, detected_at_turn=turn, amount_krw=amount,
            evidence_text="원문으로만 존재하는 문장",
        ) for turn, amount in [(8, 30000), (2, 10000)]]
        features = build_case_context_features(events)
        self.assertEqual(features.amount_values_krw, [10000, 30000])
        self.assertEqual(features.chronology, ["T2:MONEY_MOVEMENT:TRANSFER", "T8:MONEY_MOVEMENT:TRANSFER"])
        self.assertNotIn("원문으로만", features.model_dump_json())


class ContextCancellationTest(unittest.IsolatedAsyncioTestCase):
    async def test_cancelled_context_request_is_not_turned_into_a_fallback(self):
        window_ai = AsyncMock()
        window_ai.analyze.return_value = WindowAnalysisResult(
            turns=[], events=[], windows=[], extractor_model="test",
        )
        handler = AsyncMock()
        handler.analyze.side_effect = asyncio.CancelledError()
        fusion = AsyncMock()
        with patch("ai_api.app.domains.diagnosis.service.extract_case_context_features", new=AsyncMock(return_value=CaseContextFeatures())), self.assertRaises(asyncio.CancelledError):
            await DiagnosisService(window_ai=window_ai, full_context_llm=handler, fusion=fusion).analyze("test")
        fusion.merge.assert_not_called()
