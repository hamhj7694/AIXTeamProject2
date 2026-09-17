from __future__ import annotations

from general_api.app.domains.cases.context_v3.atom_fact_projection import (
    project_semantic_atoms_to_fact_candidates,
)


def test_each_atom_becomes_a_separate_reviewable_fact_without_source_text() -> None:
    atoms = [
        {
            "atom_id": "ATM-1", "predicate": "TRANSFER_FUNDS", "atom_class": "FINANCIAL_ACTION",
            "action_state": "REQUESTED", "amount_value_krw": 3000000,
            "observed_terms": [{"surface_form": "안전계좌", "normalized_code": "TERM.SAFE_ACCOUNT"}],
            "destination": "CLAIMED_SAFE_ACCOUNT", "speech_act": "DIRECTIVE", "modality": "DIRECTIVE", "urgency": "IMMEDIATE",
        },
        {
            "atom_id": "ATM-2", "predicate": "TRANSFER_FUNDS", "atom_class": "FINANCIAL_ACTION",
            "action_state": "REQUESTED", "amount_value_krw": 5000000,
            "observed_terms": [{"surface_form": "당장", "normalized_code": "URGENCY.DANGJANG"}],
        },
    ]

    candidates = project_semantic_atoms_to_fact_candidates(atoms)

    assert [item["value"]["atom_id"] for item in candidates] == ["ATM-1", "ATM-2"]
    assert {item["value"]["amount_krw"] for item in candidates} == {3000000, 5000000}
    assert candidates[0]["evidence_refs"] == [{"type": "STRUCTURED_ATOM", "id": "ATM-1"}]
    assert candidates[0]["value"]["observed_lexical_codes"] == ["TERM.SAFE_ACCOUNT"]
    assert candidates[0]["value"]["destination"] == "CLAIMED_SAFE_ACCOUNT"
    assert candidates[0]["value"]["modality"] == "DIRECTIVE"
    assert candidates[0]["value"]["observed_terms"] == [{"surface_form": "안전계좌", "normalized_code": "TERM.SAFE_ACCOUNT"}]
    assert candidates[1]["value"]["observed_lexical_codes"] == ["URGENCY.DANGJANG"]


def test_atom_projection_does_not_store_sensitive_literals() -> None:
    candidates = project_semantic_atoms_to_fact_candidates([{
        "atom_id": "ATM-OTP", "predicate": "DISCLOSE_OTP", "atom_class": "DISCLOSURE_REQUEST",
        "auth_secret_type": "OTP", "observed_terms": [
            {"surface_form": "OTP", "normalized_code": "AUTH.OTP"},
        ],
    }])
    serialized = str(candidates)
    assert "OTP" in serialized
    assert "583921" not in serialized


def test_atom_semantic_slots_are_carried_into_fact_value() -> None:
    candidate = project_semantic_atoms_to_fact_candidates([{
        "atom_id": "ATM-SLOTS", "atom_class": "ACTION_REQUEST", "predicate": "OTHER",
        "speaker": "CALLER", "subject": "CUSTOMER_ACCOUNT", "actor": "CALLER",
        "target": "CUSTOMER", "object": "ACCOUNT", "action_state": "DENIED",
        "modality": "CONDITIONAL", "polarity": "NEGATIVE", "claim_status": "CALLER_CLAIM",
        "destination": "EXTERNAL_ACCOUNT", "amount_scope": "ALL_FUNDS",
        "claimed_purpose": "PROTECTION", "threat_type": "ACCOUNT_FREEZE", "repetition_pressure": "HIGH",
    }])[0]
    value = candidate["value"]
    for key, expected in {
        "speaker": "CALLER", "subject": "CUSTOMER_ACCOUNT", "actor": "CALLER",
        "target": "CUSTOMER", "object": "ACCOUNT", "action_state": "DENIED",
        "modality": "CONDITIONAL", "polarity": "NEGATIVE", "claim_status": "CALLER_CLAIM",
        "destination": "EXTERNAL_ACCOUNT", "amount_scope": "ALL_FUNDS",
        "claimed_purpose": "PROTECTION", "threat_type": "ACCOUNT_FREEZE",
        "repetition_pressure": "HIGH",
    }.items():
        assert value[key] == expected


def test_actual_money_atom_keeps_event_role_and_projects_as_actual_amount() -> None:
    candidate = project_semantic_atoms_to_fact_candidates([{
        "atom_id": "ATM-REFUND", "atom_class": "STATE_CLAIM", "predicate": "OTHER",
        "action_state": "REPORTED_ACTION", "amount_value_krw": 200000,
        "amount_role": "REFUND_IN", "amount_direction": "IN", "amount_event_id": "AMT-1",
    }])[0]
    assert candidate["semantic_key"] == "transfer.actual.amount"
    assert candidate["value"]["amount_role"] == "REFUND_IN"
    assert candidate["value"]["amount_direction"] == "IN"
    assert candidate["value"]["amount_event_id"] == "AMT-1"
