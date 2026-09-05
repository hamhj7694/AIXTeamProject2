from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from ai_api.app.domains.diagnosis import DiagnosisService
from ai_api.app.domains.diagnosis.extractor import EventExtraction, _local_safety_events, parse_turns
from ai_api.app.domains.diagnosis.features import deterministic_amount
from ai_api.app.domains.diagnosis.model_adapter import EXPECTED_SHA256, metadata
from contracts.diagnosis import CaseContextFeatures, ContextResult


class DiagnosisServiceTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        for target, result in [
            ("extract_case_context_features", CaseContextFeatures()),
            ("FullContextDiagnosisHandler.analyze", ContextResult(summary="테스트 요약", incident_type="test", confidence=0.8)),
        ]:
            mock = patch("ai_api.app.domains.diagnosis.service." + target, new=AsyncMock(return_value=result))
            mock.start()
            self.addCleanup(mock.stop)

    @staticmethod
    def _extraction(text: str) -> EventExtraction:
        turns = parse_turns(text)
        return EventExtraction(turns, _local_safety_events(turns), list(range(1, len(turns) + 1)), "test-extractor")

    async def test_phishing_signals_use_window_model(self) -> None:
        source = "검찰청이라며 계좌가 범죄에 연루됐습니다. 지금 안전계좌로 500만원을 즉시 송금하세요."
        with patch(
            "ai_api.app.domains.diagnosis.window_ai.service.extract_events",
            new=AsyncMock(return_value=self._extraction(source)),
        ):
            result = await DiagnosisService().analyze(source)
        self.assertEqual(result.model_label, "PHISHING")
        self.assertEqual(result.risk_level.value, "HIGH")
        self.assertGreaterEqual(result.risk_score, 95)
        self.assertEqual(result.model_metadata["artifact_sha256"], EXPECTED_SHA256)
        self.assertTrue(result.evidence)

    async def test_normal_input_applies_zero_feature_guardrail(self) -> None:
        source = "예금 만기일은 다음 달 15일입니다."
        with patch(
            "ai_api.app.domains.diagnosis.window_ai.service.extract_events",
            new=AsyncMock(return_value=self._extraction(source)),
        ):
            result = await DiagnosisService().analyze(source)
        self.assertEqual(result.model_label, "NORMAL")
        self.assertTrue(result.windows[0].guardrail_applied)
        self.assertLess(result.risk_score, 95)

    def test_amount_is_recomputed_from_evidence(self) -> None:
        self.assertEqual(deterministic_amount("500만원을 보내세요"), 5_000_000)

    def test_model_is_marked_experimental(self) -> None:
        self.assertEqual(metadata("test-extractor")["model_status"], "EXPERIMENTAL_SAMPLE")


if __name__ == "__main__":
    unittest.main()
