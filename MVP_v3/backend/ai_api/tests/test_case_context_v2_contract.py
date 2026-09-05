import unittest

from pydantic import ValidationError

from contracts.ai_internal.case_context_v2 import (
    CaseContextAiInputV2,
    CaseContextAiProposalV2,
    ProposedContextBulletV2,
    ProposedSuggestionV2,
)


class CaseContextV2AiContractTest(unittest.TestCase):
    def test_ai_output_is_proposal_only(self):
        proposal = CaseContextAiProposalV2(
            source_revision=3,
            summary_bullets=[ProposedContextBulletV2(semantic_key="summary.loss", text="송금 여부 확인 필요")],
            proposed_suggestions=[ProposedSuggestionV2(
                suggestion_type="TRANSACTION_REVIEW", title="거래내역 확인",
                rationale="고객 답변 검토 필요", priority="URGENT",
                related_gap_keys=["transfer.actual.status"],
                dedupe_key="transaction-review:transfer.actual.status",
            )],
            model_version="test-model", prompt_version="case-context-v2-test",
        )
        self.assertEqual(proposal.proposed_suggestions[0].execution_mode, "HUMAN_REVIEW_REQUIRED")

        with self.assertRaises(ValidationError):
            CaseContextAiProposalV2.model_validate({
                **proposal.model_dump(),
                "confirmed_facts": [{"semantic_key": "transfer.actual.status"}],
            })

    def test_ai_input_rejects_raw_transcript_field(self):
        valid = CaseContextAiInputV2(case_id="VP-1", source_revision=1)
        self.assertEqual(valid.privacy_safe_signals, [])
        with self.assertRaises(ValidationError):
            CaseContextAiInputV2.model_validate({
                "case_id": "VP-1", "source_revision": 1,
                "raw_transcript": "저장하거나 전달하면 안 되는 원문",
            })


if __name__ == "__main__":
    unittest.main()
