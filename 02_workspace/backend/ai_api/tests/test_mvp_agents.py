from __future__ import annotations

import json
import unittest
from pathlib import Path

from ai_api.app.domains.case_support.agents import (
    CaseSupportAgent,
    CaseUpdateAgent,
    CustomerVerificationAgent,
)
from ai_api.app.domains.case_support.workflow import MvpWorkflowService
from contracts.ai_internal.mvp_workflow import ExecutionMode, TargetField
from contracts.diagnosis import DiagnosisResult


class MvpAgentsTest(unittest.TestCase):
    @staticmethod
    def _diagnosis() -> DiagnosisResult:
        fixture = (
            Path(__file__).resolve().parents[2]
            / "contracts"
            / "ai_internal"
            / "fixtures"
            / "diagnosis.high.v1.json"
        )
        return DiagnosisResult.model_validate(json.loads(fixture.read_text(encoding="utf-8"))["response"])

    def test_agents_preserve_the_existing_workflow_outputs(self) -> None:
        diagnosis = self._diagnosis()
        workflow = MvpWorkflowService()
        case_support = CaseSupportAgent(workflow)
        verification = CustomerVerificationAgent(workflow)
        case_update = CaseUpdateAgent(workflow)

        brief = case_support.build_brief(diagnosis)
        self.assertEqual(brief, workflow.build_brief(diagnosis))

        questions = verification.recommend_questions(brief)
        self.assertEqual(questions, workflow.recommend_questions(brief))
        self.assertTrue(all(item.execution_mode is ExecutionMode.HUMAN_REVIEW_REQUIRED for item in questions))

        answer = verification.structure_answer(TargetField.TRANSFER_STATUS, "아직 송금 안 했어요.")
        self.assertEqual(answer.structured_value, "NOT_TRANSFERRED")
        self.assertEqual(answer, workflow.structure_answer(TargetField.TRANSFER_STATUS, "아직 송금 안 했어요."))

        update = case_update.update_brief(brief, answer)
        self.assertEqual(update, workflow.update_brief(brief, answer))
        self.assertEqual(update.risk_evidence, brief.risk_evidence)

    def test_ambiguous_answer_is_preserved_as_unresolved(self) -> None:
        result = CustomerVerificationAgent().structure_answer(
            TargetField.TRANSFER_STATUS, "잘 모르겠습니다."
        )
        self.assertTrue(result.unresolved)
        self.assertIsNone(result.structured_value)
        self.assertTrue(result.warnings)

    def test_customer_verification_agent_can_process_answer_and_update_brief(self) -> None:
        workflow = MvpWorkflowService()
        verification = CustomerVerificationAgent(workflow)
        brief = CaseSupportAgent(workflow).build_brief(self._diagnosis())
        question = next(
            item
            for item in verification.recommend_questions(brief)
            if item.target_field is TargetField.TRANSFER_STATUS
        )

        result = verification.process_answer_and_update_brief(
            brief,
            question,
            "\uc1a1\uae08\ud588\uc5b4\uc694.",
        )

        self.assertEqual(result.structured_answer.structured_value, "TRANSFERRED")
        self.assertEqual(result.brief_update.resolved_items[0].target_field, TargetField.TRANSFER_STATUS)
