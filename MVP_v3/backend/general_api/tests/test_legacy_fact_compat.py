from __future__ import annotations

import unittest

from general_api.app.domains.cases.legacy_fact_compat import (
    legacy_row_from_v2,
    v2_payload_from_legacy,
)


class LegacyFactCompatibilityTest(unittest.TestCase):
    def test_legacy_payload_maps_to_explicit_v2_semantic_key(self) -> None:
        payload = v2_payload_from_legacy(
            field="authentication_information_exposure",
            value="고객 진술",
            source="AI_EXTRACTED",
            evidence_message_id="msg-1",
            source_question_id="question-1",
            fact_id="fact-1",
        )
        self.assertEqual(payload["semantic_key"], "exposure.authentication_information")
        self.assertEqual(payload["source_kind"], "AI_EXTRACTION")
        self.assertEqual(payload["evidence_refs"], [
            {"type": "MESSAGE", "id": "msg-1"},
            {"type": "QUESTION_ANSWER", "id": "question-1"},
        ])

    def test_v2_row_is_exposed_as_legacy_shape_without_using_legacy_storage(self) -> None:
        row = legacy_row_from_v2({
            "fact_id": "legacy-1", "case_id": "VP-1",
            "semantic_key": "exposure.personal_information",
            "display_value": "고객 진술", "source_kind": "CUSTOMER_STATEMENT",
            "status": "PROPOSED", "confidence": None,
            "evidence_refs_json": [{"type": "MESSAGE", "id": "msg-2"}],
            "created_at": "2026-09-22T00:00:00+00:00",
        })
        self.assertEqual(row["field"], "personal_information_exposure")
        self.assertEqual(row["source"], "UNRESOLVED")
        self.assertEqual(row["evidence_message_id"], "msg-2")


if __name__ == "__main__":
    unittest.main()
