from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_api.app.domains.case_support import MvpWorkflowService
from contracts.ai_internal.mvp_workflow import (
    BriefUpdateResult,
    CaseBrief,
    CustomerAnswerResult,
    ExecutionMode,
    QuestionCandidate,
    QuestionPriority,
    TargetField,
)
from contracts.diagnosis import DiagnosisResult, Evidence, RiskLevel


FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "contracts"
    / "ai_internal"
    / "fixtures"
    / "diagnosis.high.v1.json"
)
RAW_ANSWER = "아직 송금 안 했어요"


class MvpVerticalSliceTest(unittest.TestCase):
    """HIGH 진단부터 담당자 검토용 brief 갱신까지의 결정론적 MVP 흐름."""

    @staticmethod
    def _high_diagnosis_with_local_evidence() -> DiagnosisResult:
        """공용 fixture의 실제 문구만으로 테스트에 필요한 evidence를 보강한다."""
        payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        diagnosis = DiagnosisResult.model_validate(payload["response"])
        fixture_text = payload["request"]["text"]

        evidence = [
            Evidence(
                turn=1,
                event_family="IMPERSONATION",
                subtype="검찰청",
                text="검찰청이라며",
            ),
            Evidence(
                turn=1,
                event_family="MONEY_MOVEMENT",
                subtype="TRANSFER_REQUEST",
                text=fixture_text,
            ),
            Evidence(
                turn=1,
                event_family="AMOUNT",
                subtype="REQUESTED_AMOUNT",
                text="500만원을 즉시 송금하세요.",
            ),
        ]
        return diagnosis.model_copy(
            update={
                "evidence": evidence,
                "features": {**diagnosis.features, "requested_amount_max": 5_000_000},
            }
        )

    def test_high_case_flows_from_diagnosis_to_safe_brief_update(self) -> None:
        diagnosis = self._high_diagnosis_with_local_evidence()

        self.assertEqual(diagnosis.risk_level, RiskLevel.HIGH)
        self.assertEqual(diagnosis.model_label, "PHISHING")
        self.assertGreaterEqual(diagnosis.risk_score, 95)

        # workflow.build_brief()는 fixture 경로만 사용하도록 명시해 실제 API 호출을 막는다.
        with patch.dict(os.environ, {"CASE_BRIEF_MODE": "fixture"}, clear=False):
            workflow = MvpWorkflowService()
            brief = workflow.build_brief(diagnosis)

        self.assertEqual(CaseBrief.model_validate(brief.model_dump()), brief)
        self.assertTrue(brief.summary)
        self.assertEqual(brief.risk_level, diagnosis.risk_level)
        self.assertEqual(brief.risk_score, diagnosis.risk_score)
        self.assertEqual(brief.mentioned_amount_krw, 5_000_000)
        self.assertEqual(brief.risk_evidence, diagnosis.evidence)
        self.assertEqual(brief.counter_evidence, [])
        self.assertTrue(brief.unresolved_items)
        self.assertEqual(
            {item.text for item in brief.risk_evidence},
            {"검찰청이라며", diagnosis.evidence[1].text, "500만원을 즉시 송금하세요."},
        )

        questions = workflow.recommend_questions(brief)
        self.assertGreaterEqual(len(questions), 1)
        self.assertTrue(all(QuestionCandidate.model_validate(item.model_dump()) == item for item in questions))
        transfer_question = next(
            item for item in questions if item.target_field is TargetField.TRANSFER_STATUS
        )
        self.assertEqual(transfer_question.priority, QuestionPriority.P0)
        self.assertEqual(transfer_question.execution_mode, ExecutionMode.HUMAN_REVIEW_REQUIRED)
        self.assertTrue(transfer_question.question.strip())
        self.assertTrue(transfer_question.reason.strip())

        answer = workflow.structure_answer(TargetField.TRANSFER_STATUS, RAW_ANSWER)
        self.assertEqual(CustomerAnswerResult.model_validate(answer.model_dump()), answer)
        self.assertEqual(answer.target_field, TargetField.TRANSFER_STATUS)
        self.assertEqual(answer.raw_answer, RAW_ANSWER)
        self.assertEqual(answer.structured_value, "NOT_TRANSFERRED")
        self.assertGreaterEqual(answer.confidence, 0)
        self.assertLessEqual(answer.confidence, 1)
        self.assertFalse(answer.unresolved)
        self.assertEqual(answer.warnings, [])
        self.assertEqual(answer.evidence_text, RAW_ANSWER)

        update = workflow.update_brief(brief, answer)
        self.assertEqual(BriefUpdateResult.model_validate(update.model_dump()), update)
        self.assertTrue(update.updated_summary)
        self.assertEqual(len(update.resolved_items), 1)
        self.assertEqual(update.resolved_items[0].target_field, TargetField.TRANSFER_STATUS)
        self.assertEqual(update.resolved_items[0].structured_value, "NOT_TRANSFERRED")
        self.assertEqual(update.resolved_items[0].evidence_text, RAW_ANSWER)
        self.assertNotIn(
            TargetField.TRANSFER_STATUS,
            [item.target_field for item in update.unresolved_items],
        )
        self.assertEqual(
            [item for item in update.unresolved_items],
            [
                item
                for item in brief.unresolved_items
                if item.target_field is not TargetField.TRANSFER_STATUS
            ],
        )
        self.assertEqual(update.risk_evidence, brief.risk_evidence)
        self.assertEqual(update.counter_evidence, brief.counter_evidence)

    def test_ambiguous_transfer_answer_remains_unresolved(self) -> None:
        diagnosis = self._high_diagnosis_with_local_evidence()
        workflow = MvpWorkflowService()
        brief = workflow.build_brief(diagnosis)

        answer = workflow.structure_answer(TargetField.TRANSFER_STATUS, "잘 모르겠습니다.")
        self.assertIsNone(answer.structured_value)
        self.assertTrue(answer.unresolved)

        update = workflow.update_brief(brief, answer)
        self.assertEqual(update.resolved_items, [])
        self.assertEqual(update.unresolved_items, brief.unresolved_items)
        self.assertEqual(update.risk_evidence, brief.risk_evidence)


if __name__ == "__main__":
    unittest.main()
