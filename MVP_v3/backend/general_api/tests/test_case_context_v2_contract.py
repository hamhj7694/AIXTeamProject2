import unittest
from datetime import datetime, timezone

from pydantic import ValidationError

from contracts.public_api.case_context_v2 import (
    PublicAiSuggestionV2,
    PublicCaseFactV2,
    PublicCaseGapV2,
    PublicCaseTaskV2,
    PublicContextBulletV2,
    PublicCaseContextViewV2,
    PublicCreateFactV2Request,
    PublicCreateGapV2Request,
    PublicUpdateGapV2Request,
)


NOW = datetime(2026, 9, 5, tzinfo=timezone.utc)


class CaseContextV2PublicContractTest(unittest.TestCase):
    def fact(self, **changes):
        value = {
            "fact_id": "FACT-1", "case_id": "VP-1",
            "semantic_key": "transfer.actual.status", "display_label": "실제 송금 여부",
            "value": {"status": "UNKNOWN"}, "display_value": "아직 확인되지 않음",
            "source_kind": "CUSTOMER_STATEMENT", "status": "PROPOSED",
            "version": 1, "created_at": NOW, "updated_at": NOW,
        }
        value.update(changes)
        return PublicCaseFactV2.model_validate(value)

    def test_customer_statement_remains_proposed_without_reviewer(self):
        fact = self.fact()
        self.assertEqual(fact.status, "PROPOSED")
        self.assertIsNone(fact.confirmed_by)

    def test_confirmed_fact_requires_reviewer_and_time(self):
        with self.assertRaises(ValidationError):
            self.fact(status="CONFIRMED")
        confirmed = self.fact(status="CONFIRMED", confirmed_by="USER-1", confirmed_at=NOW)
        self.assertEqual(confirmed.status, "CONFIRMED")

    def test_gap_terminal_states_require_reason_or_fact(self):
        base = {
            "gap_id": "GAP-1", "case_id": "VP-1", "semantic_key": "transfer.actual.status",
            "title": "실제 송금 여부", "reason": "피해 상태 판단에 필요", "priority": "URGENT",
            "source": "AI", "source_revision": 2, "version": 1,
            "created_at": NOW, "updated_at": NOW,
        }
        with self.assertRaises(ValidationError):
            PublicCaseGapV2.model_validate({**base, "status": "RESOLVED"})
        with self.assertRaises(ValidationError):
            PublicCaseGapV2.model_validate({**base, "status": "DISMISSED"})
        resolved = PublicCaseGapV2.model_validate({**base, "status": "RESOLVED", "resolution_fact_id": "FACT-1"})
        self.assertEqual(resolved.resolution_fact_id, "FACT-1")

    def test_gap_update_request_preserves_resolved_reason_compatibility(self):
        with self.assertRaises(ValidationError):
            PublicUpdateGapV2Request(expected_version=1, status="DISMISSED")
        with self.assertRaises(ValidationError):
            PublicUpdateGapV2Request(expected_version=1, status="RESOLVED")

        request = PublicUpdateGapV2Request(
            expected_version=1,
            status="RESOLVED",
            resolution_fact_id="FACT-1",
            reason="확정 사실 연결",
        )
        self.assertEqual(request.reason, "확정 사실 연결")
        self.assertIsNone(request.edited_reason)

    def test_create_requests_accept_canonical_semantic_keys(self):
        semantic_keys = (
            "exposure.personal_information",
            "exposure.authentication_information",
            "device.remote_control_app",
            "offender.claimed_organization",
            "offender.incident_claim",
            "transfer.actual.status",
        )
        for request_model in (PublicCreateFactV2Request, PublicCreateGapV2Request):
            for semantic_key in semantic_keys:
                with self.subTest(request_model=request_model.__name__, semantic_key=semantic_key):
                    payload = {
                        "client_request_id": "canonical-key-test",
                        "semantic_key": semantic_key,
                    }
                    if request_model is PublicCreateFactV2Request:
                        payload.update({
                            "display_label": "확인 항목",
                            "value": {"status": "UNKNOWN"},
                            "display_value": "확인 필요",
                        })
                    else:
                        payload.update({
                            "title": "확인 항목",
                            "reason": "사건 확인에 필요",
                            "priority": "HIGH",
                        })
                    self.assertEqual(request_model.model_validate(payload).semantic_key, semantic_key)

    def test_create_requests_reject_invalid_semantic_keys(self):
        semantic_keys = (
            "Exposure.personal_information",
            "exposure.personal information",
            "exposure..personal_information",
            ".exposure.personal_information",
            "exposure.personal_information.",
            "exposure/personal_information",
        )
        for request_model in (PublicCreateFactV2Request, PublicCreateGapV2Request):
            for semantic_key in semantic_keys:
                with self.subTest(request_model=request_model.__name__, semantic_key=semantic_key):
                    payload = {
                        "client_request_id": "invalid-key-test",
                        "semantic_key": semantic_key,
                    }
                    if request_model is PublicCreateFactV2Request:
                        payload.update({
                            "display_label": "확인 항목",
                            "value": {"status": "UNKNOWN"},
                            "display_value": "확인 필요",
                        })
                    else:
                        payload.update({
                            "title": "확인 항목",
                            "reason": "사건 확인에 필요",
                            "priority": "HIGH",
                        })
                    with self.assertRaises(ValidationError):
                        request_model.model_validate(payload)

    def test_reviewed_ai_suggestion_requires_human_review_metadata(self):
        base = {
            "suggestion_id": "SUG-1", "case_id": "VP-1", "suggestion_type": "TRANSACTION_REVIEW",
            "title": "거래내역 확인", "rationale": "송금 답변 검토 필요", "priority": "URGENT",
            "related_gap_ids": ["GAP-1"], "dedupe_key": "transaction-review:transfer.actual.status",
            "execution_mode": "HUMAN_REVIEW_REQUIRED", "source_revision": 2,
            "version": 1, "created_at": NOW, "updated_at": NOW,
        }
        with self.assertRaises(ValidationError):
            PublicAiSuggestionV2.model_validate({**base, "status": "ACCEPTED"})
        accepted = PublicAiSuggestionV2.model_validate({
            **base, "status": "ACCEPTED", "accepted_task_id": "TASK-1",
            "reviewed_by": "USER-1", "reviewed_at": NOW,
        })
        self.assertEqual(accepted.accepted_task_id, "TASK-1")

    def test_completed_task_requires_result_and_completer(self):
        base = {
            "task_id": "TASK-1", "case_id": "VP-1", "source": "STAFF_CREATED",
            "task_type": "TRANSACTION_REVIEW", "title": "거래 확인", "description": "거래내역 검토",
            "priority": "URGENT", "status": "COMPLETED", "version": 1,
            "created_by": "USER-1", "created_at": NOW, "updated_at": NOW,
        }
        with self.assertRaises(ValidationError):
            PublicCaseTaskV2.model_validate(base)
        completed = PublicCaseTaskV2.model_validate({
            **base, "result_summary": "300만 원 송금 확인", "completed_by": "USER-1", "completed_at": NOW,
        })
        self.assertEqual(completed.status, "COMPLETED")

    def test_projection_limits_summary_and_rejects_unknown_fields(self):
        bullets = [PublicContextBulletV2(bullet_id=f"B-{index}", text="요약") for index in range(4)]
        view = PublicCaseContextViewV2(
            case_id="VP-1", source_revision=2, projection_revision=2,
            projection_status="CURRENT", generated_by="DETERMINISTIC_FALLBACK",
            summary_bullets=bullets,
        )
        self.assertEqual(len(view.summary_bullets), 4)
        with self.assertRaises(ValidationError):
            PublicCaseContextViewV2.model_validate({**view.model_dump(), "internal_debug": "secret"})


if __name__ == "__main__":
    unittest.main()
