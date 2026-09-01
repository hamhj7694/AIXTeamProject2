from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from ai_api.app.domains.diagnosis import DiagnosisService
from ai_api.app.domains.diagnosis.features import deterministic_amount
from ai_api.app.domains.diagnosis.model_adapter import EXPECTED_SHA256, metadata


class DiagnosisServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_phishing_fixture_uses_window_model(self) -> None:
        with patch.dict(os.environ, {"DIAGNOSIS_EXTRACTOR_MODE": "fixture"}):
            result = await DiagnosisService().analyze(
                "검찰청이라며 계좌가 범죄에 연루됐습니다. 지금 안전계좌로 500만원을 즉시 송금하세요."
            )
        self.assertEqual(result.model_label, "PHISHING")
        self.assertEqual(result.risk_level.value, "HIGH")
        self.assertGreaterEqual(result.risk_score, 95)
        self.assertEqual(result.model_metadata["artifact_sha256"], EXPECTED_SHA256)
        self.assertTrue(result.evidence)

    async def test_normal_fixture_applies_zero_feature_guardrail(self) -> None:
        with patch.dict(os.environ, {"DIAGNOSIS_EXTRACTOR_MODE": "fixture"}):
            result = await DiagnosisService().analyze("예금 만기일은 다음 달 15일입니다.")
        self.assertEqual(result.model_label, "NORMAL")
        self.assertTrue(result.windows[0].guardrail_applied)
        self.assertLess(result.risk_score, 95)

    def test_amount_is_recomputed_from_evidence(self) -> None:
        self.assertEqual(deterministic_amount("500만원을 보내세요"), 5_000_000)

    def test_model_is_marked_experimental(self) -> None:
        self.assertEqual(metadata("fixture-v1")["model_status"], "EXPERIMENTAL_SAMPLE")


if __name__ == "__main__":
    unittest.main()
