from __future__ import annotations

import json
import unittest
from pathlib import Path

from pydantic import ValidationError

from contracts.diagnosis import AnalyzeTextRequest, DiagnosisResult


FIXTURE_DIRECTORY = Path(__file__).resolve().parents[2] / "contracts" / "ai_internal" / "fixtures"
CONTRACT_DIRECTORY = FIXTURE_DIRECTORY.parent


class DiagnosisInternalContractTest(unittest.TestCase):
    def _load_fixture(self, name: str) -> dict:
        return json.loads((FIXTURE_DIRECTORY / name).read_text(encoding="utf-8"))

    @staticmethod
    def _load_json(path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def test_normal_and_high_fixtures_match_runtime_models(self) -> None:
        for name, expected_level, expected_label in [
            ("diagnosis.normal.v1.json", "NORMAL", "NORMAL"),
            ("diagnosis.high.v1.json", "HIGH", "PHISHING"),
        ]:
            fixture = self._load_fixture(name)
            AnalyzeTextRequest.model_validate(fixture["request"])
            result = DiagnosisResult.model_validate(fixture["response"])
            self.assertEqual(result.risk_level.value, expected_level)
            self.assertEqual(result.model_label, expected_label)

        example = self._load_json(CONTRACT_DIRECTORY / "diagnosis.v1.example.json")
        AnalyzeTextRequest.model_validate(example["request"])
        self.assertEqual(DiagnosisResult.model_validate(example["response"]).risk_level.value, "HIGH")

    def test_high_fixture_preserves_distinct_money_features(self) -> None:
        fixture = self._load_fixture("diagnosis.high.v1.json")
        features = fixture["response"]["features"]
        self.assertEqual(features["money_movement_present"], 1.0)
        self.assertEqual(features["money_transfer_present"], 1.0)

    def test_generated_json_schema_describes_runtime_response(self) -> None:
        schema = DiagnosisResult.model_json_schema()
        self.assertEqual(schema["title"], "DiagnosisResult")
        self.assertEqual(schema["type"], "object")
        self.assertTrue(set(DiagnosisResult.model_fields).issubset(schema["properties"]))
        self.assertIn("WindowResult", schema["$defs"])

    def test_runtime_contract_rejects_extra_or_invalid_fields(self) -> None:
        response = self._load_fixture("diagnosis.normal.v1.json")["response"]
        with self.assertRaises(ValidationError):
            DiagnosisResult.model_validate({**response, "unexpected": True})
        with self.assertRaises(ValidationError):
            DiagnosisResult.model_validate({**response, "risk_score": "not-a-score"})


if __name__ == "__main__":
    unittest.main()
