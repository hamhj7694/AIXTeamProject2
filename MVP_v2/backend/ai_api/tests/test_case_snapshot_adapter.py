from __future__ import annotations

import json
import unittest
from pathlib import Path

from ai_api.app.domains.case_support import CaseSnapshotAiAdapter


class CaseSnapshotAiAdapterTest(unittest.TestCase):
    def test_builds_brief_and_preserves_diagnosis_warnings(self) -> None:
        fixture = Path(__file__).resolve().parents[2] / "contracts" / "ai_internal" / "fixtures" / "diagnosis.high.v1.json"
        diagnosis = json.loads(fixture.read_text(encoding="utf-8"))["response"]
        diagnosis.update({"warnings": ["diagnosis warning"], "partial_failure": True})

        result = CaseSnapshotAiAdapter().build_presentation({
            "case_id": "VP-SNAPSHOT-001",
            "diagnosis": diagnosis,
            "warnings": ["input warning"],
            "question_context": {"pending_question_fields": ["transfer_status"]},
        })

        self.assertEqual(result.case_id, "VP-SNAPSHOT-001")
        self.assertIsNotNone(result.case_brief)
        self.assertNotIn("transfer_status", [item.target_field.value for item in result.recommended_questions])
        self.assertIn("input warning", result.warnings)
        self.assertIn("diagnosis warning", result.warnings)


if __name__ == "__main__":
    unittest.main()
