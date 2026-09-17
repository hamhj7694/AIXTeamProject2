from __future__ import annotations

from datetime import datetime, timezone

from contracts.public_api.case_context_v2 import PublicCaseFactV2
from general_api.app.domains.cases.context_v3.quality_metrics import (
    build_projection_quality_metrics,
    find_slot_preservation_violations,
)


def test_projection_quality_metrics_detect_atom_loss_and_preserved_slots() -> None:
    now = datetime.now(timezone.utc)
    facts = [PublicCaseFactV2(
        fact_id="fact-1", case_id="VP-METRIC", semantic_key="circumstance.demand",
        display_label="상대방 요구", display_value="송금 요구",
        value={"atom_id": "atom-1", "predicate": "TRANSFER_FUNDS", "action_state": "REQUESTED",
               "polarity": "POSITIVE", "observed_lexical_codes": ["ACTION.TRANSFER"]},
        source_kind="AI_EXTRACTION", status="PROPOSED",
        evidence_refs=[{"type": "STRUCTURED_ATOM", "id": "atom-1"}], version=1,
        created_at=now, updated_at=now,
    )]
    metrics = build_projection_quality_metrics([
        {"atom_id": "atom-1", "predicate": "TRANSFER_FUNDS", "action_state": "REQUESTED",
         "polarity": "POSITIVE", "observed_terms": [{"normalized_code": "ACTION.TRANSFER"}]},
        {"atom_id": "atom-2", "predicate": "CLAIMS_ORGANIZATION", "polarity": "POSITIVE"},
    ], facts)
    assert metrics["semantic_slot_preservation_rate"] == 1.0
    assert metrics["aggregation_loss_rate"] == 0.5
    assert metrics["semantic_broadening_rate"] == 0.0


def test_projection_quality_metrics_detect_unsupported_lexical_code() -> None:
    now = datetime.now(timezone.utc)
    fact = PublicCaseFactV2(
        fact_id="fact-1", case_id="VP-METRIC", semantic_key="circumstance.demand",
        display_label="상대방 요구", display_value="송금 요구",
        value={"atom_id": "atom-1", "observed_lexical_codes": ["TERM.UNSUPPORTED"]},
        source_kind="AI_EXTRACTION", status="PROPOSED",
        evidence_refs=[{"type": "STRUCTURED_ATOM", "id": "atom-1"}], version=1,
        created_at=now, updated_at=now,
    )
    metrics = build_projection_quality_metrics(
        [{"atom_id": "atom-1", "observed_terms": [{"normalized_code": "ACTION.TRANSFER"}]}], [fact]
    )
    assert metrics["unsupported_lexicalization_rate"] == 1.0


def test_slot_validator_reports_only_missing_structured_slots() -> None:
    now = datetime.now(timezone.utc)
    fact = PublicCaseFactV2(
        fact_id="fact-1", case_id="VP-METRIC", semantic_key="circumstance.tactic",
        display_label="압박", display_value="긴급 처리 압박",
        value={"atom_id": "atom-1", "expression_features": {"urgency": "IMMEDIATE"}},
        source_kind="AI_EXTRACTION", status="PROPOSED",
        evidence_refs=[{"type": "STRUCTURED_ATOM", "id": "atom-1"}], version=1,
        created_at=now, updated_at=now,
    )
    violations = find_slot_preservation_violations([{
        "atom_id": "atom-1", "urgency": "IMMEDIATE", "polarity": "NEGATIVE",
    }], [fact])
    assert violations == ["atom-1:polarity"]
