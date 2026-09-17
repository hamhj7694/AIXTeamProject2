from contracts.diagnosis import ContextSignal, ExtractedEvent, SemanticRelation

from ai_api.app.domains.diagnosis.audit import audit_semantic_result
from ai_api.app.domains.diagnosis.semantic_atoms import build_semantic_atoms


def _transfer_event(amount: float | None = None) -> ExtractedEvent:
    return ExtractedEvent(
        event_family="MONEY_MOVEMENT", subtype="TRANSFER", evidence_turn_id=1,
        evidence_text="안전계좌로 당장 이체", detected_at_turn=1,
        is_requested=True, amount_krw=amount,
    )


def test_audit_passes_privacy_safe_grounded_atoms() -> None:
    event = _transfer_event(3000000)
    atom = build_semantic_atoms([event])[0]

    result = audit_semantic_result([event], [atom], source_by_turn={1: event.evidence_text})

    assert result.audit_status == "PASS"
    assert result.recommended_action == "NONE"
    assert result.privacy_violations == []
    assert result.metrics["event_coverage"] == 1.0


def test_audit_requires_reextraction_for_mixed_atom_or_orphan_lineage() -> None:
    event = _transfer_event()
    atom = build_semantic_atoms([event])[0]
    mixed = atom.model_copy(update={"communication_control": "NO_END_CALL"})
    relation = SemanticRelation(
        relation_id="REL-ORPHAN", relation_type="CAUSES",
        source_atom_id="ATM-MISSING", target_atom_id=atom.atom_id, confidence=0.8,
    )

    result = audit_semantic_result([event], [mixed], [relation], source_by_turn={1: event.evidence_text})

    assert result.audit_status == "REEXTRACTION_REQUIRED"
    assert result.recommended_action == "TARGETED_REEXTRACTION"
    assert mixed.atom_id in result.mixed_atoms
    assert "REL-ORPHAN" in result.orphan_references


def test_audit_detects_observed_term_not_present_in_transient_source() -> None:
    event = _transfer_event()
    atom = build_semantic_atoms([event])[0].model_copy(update={
        "observed_terms": [atom_term for atom_term in build_semantic_atoms([event])[0].observed_terms]
    })
    forged = atom.observed_terms[0].model_copy(update={"surface_form": "검찰"})
    atom = atom.model_copy(update={"observed_terms": [forged]})

    result = audit_semantic_result([event], [atom], source_by_turn={1: event.evidence_text})

    assert result.audit_status == "NEEDS_REVIEW"
    assert result.unsupported_terms


def test_audit_result_does_not_contain_source_text() -> None:
    event = _transfer_event()
    atom = build_semantic_atoms([event])[0]
    result = audit_semantic_result([event], [atom], source_by_turn={1: event.evidence_text})

    assert event.evidence_text not in result.model_dump_json(ensure_ascii=False)
