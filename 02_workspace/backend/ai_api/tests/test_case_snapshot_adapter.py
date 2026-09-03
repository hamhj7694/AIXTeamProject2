from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import Mock

from ai_api.app.domains.case_support.case_snapshot_adapter import CaseSnapshotAiAdapter
from ai_api.app.domains.case_support.workflow import MvpWorkflowService
from contracts.diagnosis import DiagnosisResult


FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "contracts"
    / "ai_internal"
    / "fixtures"
    / "diagnosis.high.v1.json"
)


class CaseSnapshotAiAdapterTest(unittest.TestCase):
    @staticmethod
    def _diagnosis() -> DiagnosisResult:
        payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        return DiagnosisResult.model_validate(payload["response"])

    def test_snapshot_reuses_existing_workflow_and_makes_presentation_fixture(self) -> None:
        diagnosis = self._diagnosis().model_copy(update={
            "warnings": ["원본 분석 일부 확인 필요"],
            "partial_failure": True,
        })
        workflow = Mock(wraps=MvpWorkflowService())
        snapshot = {
            "case_id": "VP-ADAPTER-001",
            "diagnosis": diagnosis.model_dump(mode="json"),
            "input_text": "검찰청을 사칭해 송금을 요구했습니다.",
            "version": 9,
            "ui_state": "expanded",
            "db_internal_id": 42,
            "assignee_presence": "online",
        }

        result = CaseSnapshotAiAdapter(workflow).build_presentation(snapshot)

        workflow.build_brief.assert_called_once()
        workflow.recommend_questions.assert_called_once_with(result.case_brief)
        self.assertEqual(result.case_id, "VP-ADAPTER-001")
        self.assertIsNotNone(result.case_brief)
        self.assertTrue(result.recommended_questions)
        self.assertTrue(result.unresolved_items)
        self.assertIn("원본 분석 일부 확인 필요", result.warnings)
        self.assertIn("Diagnosis 결과가 부분 실패 상태입니다.", result.warnings)
        # DB/UI 전용 값은 AI 입력과 fixture 어디에도 복사되지 않는다.
        serialized = json.dumps(result.model_dump(mode="json"))
        self.assertNotIn("ui_state", serialized)
        self.assertNotIn("db_internal_id", serialized)
        self.assertNotIn("assignee_presence", serialized)

    def test_missing_diagnosis_preserves_uncertainty_without_inventing_brief(self) -> None:
        result = CaseSnapshotAiAdapter().build_presentation({"case_id": "VP-MISSING"})

        self.assertIsNone(result.case_brief)
        self.assertEqual(result.recommended_questions, [])
        self.assertEqual(result.unresolved_items, [])
        self.assertTrue(any("diagnosis" in warning for warning in result.warnings))

    def test_transfer_request_does_not_become_transfer_completed(self) -> None:
        diagnosis = self._diagnosis().model_copy(update={"case_id": "OTHER-CASE"})
        result = CaseSnapshotAiAdapter().build_presentation({
            "case_id": "VP-REQUEST-ONLY",
            "diagnosis": diagnosis.model_dump(mode="json"),
            "actual_transfer_status": "UNCONFIRMED",
        })

        self.assertIsNotNone(result.case_brief)
        self.assertTrue(any(
            item.target_field.value == "transfer_status"
            for item in result.unresolved_items
        ))
        self.assertIn("Case snapshot과 diagnosis의 case_id가 달라 snapshot 값을 사용했습니다.", result.warnings)
        self.assertNotIn("TRANSFER_COMPLETED", json.dumps(result.model_dump(mode="json")))


if __name__ == "__main__":
    unittest.main()
