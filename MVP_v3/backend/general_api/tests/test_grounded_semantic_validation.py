from __future__ import annotations

from datetime import datetime, timezone

import pytest
from contracts.public_api.case_context_v2 import PublicCaseFactV2
from general_api.app.domains.cases.context_v3.grounded import (
    grounded_fact_item,
    grounded_fact_text,
    validate_fact_atom_alignment,
    validate_no_unlinked_fact_join,
    validate_grounded_fact,
    validate_grounded_statement_scope,
    validate_unknown_not_upgraded,
    validate_semantic_slot_preservation,
)


def _fact(value: dict) -> PublicCaseFactV2:
    now = datetime.now(timezone.utc)
    return PublicCaseFactV2(
        fact_id="fact-state", case_id="VP-STATE", semantic_key="circumstance.demand",
        display_label="상대방 요구", value=value, display_value="송금 요구",
        source_kind="AI_EXTRACTION", status="PROPOSED",
        evidence_refs=[{"type": "STRUCTURED_ATOM", "id": "atom-state"}], version=1,
        created_at=now, updated_at=now,
    )


def _context(state: str = "REQUESTED", polarity: str = "POSITIVE") -> dict:
    return {"diagnosis": {"semantic_atoms": [{
        "atom_id": "atom-state", "predicate": "TRANSFER_FUNDS", "atom_class": "ACTION_REQUEST",
        "action_state": state, "polarity": polarity, "modality": "DIRECTIVE",
        "claim_status": "UNVERIFIED", "source_turn_id": 1,
    }]}}


def test_grounded_plan_preserves_requested_vs_instructed_and_polarity() -> None:
    plan = grounded_fact_item(_fact({"action_state": "INSTRUCTED", "polarity": "POSITIVE", "modality": "DIRECTIVE"}), _context("INSTRUCTED"))
    assert plan["semantic_state"] == "INSTRUCTED"
    assert plan["polarity"] == "POSITIVE"
    assert plan["modality"] == "DIRECTIVE"
    assert "지시한" in plan["text"]


def test_negative_or_conditional_atom_cannot_be_projected_without_polarity() -> None:
    fact = _fact({"action_state": "UNKNOWN"})
    with pytest.raises(ValueError, match="polarity"):
        validate_fact_atom_alignment(fact, _context("UNKNOWN", "NEGATIVE"))


def test_mismatched_atom_state_is_rejected() -> None:
    fact = _fact({"action_state": "COMPLETED", "polarity": "POSITIVE"})
    with pytest.raises(ValueError, match="action_state"):
        validate_fact_atom_alignment(fact, _context("REQUESTED"))


def test_unknown_and_conditional_states_are_visible_in_staff_sentence() -> None:
    unknown = _fact({"action_state": "UNKNOWN", "polarity": "POSITIVE"})
    unknown_plan = grounded_fact_item(unknown, _context("UNKNOWN"))
    assert "확인되지 않은" in unknown_plan["text"]

    conditional = _fact({"action_state": "REQUESTED", "polarity": "CONDITIONAL"})
    conditional_plan = grounded_fact_item(conditional, _context("REQUESTED", "CONDITIONAL"))
    assert "조건부" in conditional_plan["text"]

    denied = _fact({"action_state": "DENIED", "polarity": "POSITIVE"})
    denied_plan = grounded_fact_item(denied, _context("DENIED"))
    assert "부인되었거나 실행되지 않은" in denied_plan["text"]


def test_unknown_state_cannot_be_rendered_as_a_concrete_fact() -> None:
    fact = _fact({"action_state": "UNKNOWN", "polarity": "POSITIVE"})
    with pytest.raises(ValueError, match="cannot be upgraded"):
        validate_unknown_not_upgraded(fact, "The customer transferred the funds.", _context("UNKNOWN"))


def test_amount_slot_cannot_be_broadened_to_generic_money_statement() -> None:
    fact = _fact({"action_state": "REQUESTED", "polarity": "POSITIVE", "amount_krw": 3000000})
    context = _context("REQUESTED")
    context["diagnosis"]["semantic_atoms"][0]["amount_krw"] = 3000000
    with pytest.raises(ValueError, match="amount semantic slot"):
        validate_semantic_slot_preservation(fact, "상대방이 금전을 요구한 정황입니다.", context)


def test_statement_scope_rejects_an_unobserved_institution() -> None:
    fact = _fact({"action_state": "REQUESTED", "polarity": "POSITIVE"})
    context = {"diagnosis": {"semantic_atoms": [{
        "atom_id": "atom-state", "predicate": "CLAIMS_ORGANIZATION", "atom_class": "ORGANIZATION_CLAIM",
        "claimed_organization": "PROSECUTION_SERVICE", "source_turn_id": 1,
    }]}}
    fact.semantic_key = "offender.claimed_organization"
    with pytest.raises(ValueError, match="기관"):
        validate_grounded_statement_scope(fact, "상대방이 경찰을 사칭한 정황입니다.", context)


def test_customer_reported_completion_is_not_rendered_as_verified() -> None:
    fact = _fact({"action_state": "CUSTOMER_REPORTED_COMPLETED", "polarity": "POSITIVE"})
    context = _context("CUSTOMER_REPORTED_COMPLETED")
    context["diagnosis"]["semantic_atoms"][0]["claim_status"] = "CUSTOMER_REPORTED"
    text = grounded_fact_text(fact.semantic_key, fact.display_value, fact.value, context=context, fact=fact)
    assert "확인된" not in text
    with pytest.raises(ValueError, match="승격"):
        validate_grounded_fact(fact, "공식 확인된 송금 결과입니다.", context)


def test_missing_observed_terms_does_not_invent_a_specific_surface_term() -> None:
    fact = _fact({"action_state": "REQUESTED", "polarity": "POSITIVE"})
    context = _context("REQUESTED")
    text = grounded_fact_text("exposure.authentication_information", "인증정보 제공 요청", fact.value, context=context, fact=fact)
    assert "OTP" not in text
    assert "인증정보" in text


def test_unlinked_facts_cannot_be_joined_as_causal_statement() -> None:
    first = _fact({"action_state": "REQUESTED", "polarity": "POSITIVE"})
    second = _fact({"action_state": "REQUESTED", "polarity": "POSITIVE"})
    second.fact_id = "fact-state-2"
    second.evidence_refs = [{"type": "STRUCTURED_ATOM", "id": "atom-state-2"}]
    context = _context("REQUESTED")
    context["diagnosis"]["semantic_atoms"].append({
        "atom_id": "atom-state-2", "predicate": "DISCLOSE_AUTH_SECRET",
        "atom_class": "AUTH_REQUEST", "action_state": "REQUESTED",
    })
    with pytest.raises(ValueError, match="Relation"):
        validate_no_unlinked_fact_join([first, second], "because the transfer caused the disclosure", context)


def test_explicit_atom_is_used_even_when_a_signal_exists() -> None:
    fact = _fact({"action_state": "REQUESTED", "polarity": "POSITIVE"})
    context = _context("REQUESTED")
    context["diagnosis"]["context_signals"] = [{"signal_id": "signal-1", "signal_code": "TACTIC_FEAR", "atom_ids": ["atom-state"]}]
    text = grounded_fact_text(fact.semantic_key, fact.display_value, fact.value, context=context, fact=fact)
    assert "송금·이체" in text
    assert "공포" not in text
