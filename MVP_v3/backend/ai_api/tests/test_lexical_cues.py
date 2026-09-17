import json

import pytest

from contracts.diagnosis import CaseContextFeatures, ExtractedEvent
from ai_api.app.domains.diagnosis.extractor import _validate_llm_atoms
from ai_api.app.domains.diagnosis.lexical_cues import (
    attach_context_observation_lineage,
    enrich_atom_payload,
    extract_observed_terms,
)
from ai_api.app.domains.diagnosis.semantic_atoms import build_semantic_atoms


def _codes(source: str, atom: dict | None = None) -> set[str]:
    return {term.normalized_code for term in extract_observed_terms(source, atom)}


def test_institutions_and_roles_are_preserved_only_when_observed() -> None:
    codes = _codes("\uac80\ucc30 \uc218\uc0ac\uad00\uc785\ub2c8\ub2e4.")
    assert {"TERM.PROSECUTION", "ROLE.INVESTIGATOR"}.issubset(codes)
    assert "ROLE.COUNSELOR" not in codes


def test_urgency_keeps_lexical_distinction_and_shared_semantic_value() -> None:
    immediate = extract_observed_terms("\ub2f9\uc7a5 \ubcf4\ub0b4\uc138\uc694.")
    now = extract_observed_terms("\uc989\uc2dc \ubcf4\ub0b4\uc138\uc694.")
    assert immediate[0].normalized_code == "URGENCY.DANGJANG"
    assert now[0].normalized_code == "URGENCY.JEUKSI"
    assert immediate[0].semantic_value == now[0].semantic_value == "IMMEDIATE"


def test_safe_account_and_transfer_meaning_are_both_kept() -> None:
    payload = enrich_atom_payload(
        "\uc548\uc804\uacc4\uc88c\ub85c \ubcf4\ub0b4\uc138\uc694.",
        {"atom_class": "ACTION_INSTRUCTION", "predicate": "TRANSFER_FUNDS"},
    )
    codes = {item["normalized_code"] for item in payload["observed_terms"]}
    assert "TERM.SAFE_ACCOUNT" in codes
    assert payload["destination"] == "CLAIMED_SAFE_ACCOUNT"


def test_otp_type_survives_without_an_otp_value() -> None:
    payload = enrich_atom_payload(
        "OTP \ubc88\ud638\ub97c \ubd88\ub7ec\uc8fc\uc138\uc694.",
        {"atom_class": "DISCLOSURE_REQUEST", "predicate": "DISCLOSE_OTP"},
    )
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "AUTH.OTP" in serialized
    assert "583921" not in serialized


def test_sensitive_literals_account_literals_and_raw_phrases_never_persist() -> None:
    source = "\uc9c0\uae08 \ub2f9\uc7a5 \uc548\uc804\uacc4\uc88c\ub85c \uc794\uc561\uc744 \uc804\ubd80 \ubcf4\ub0b4\uc154\uc57c \ud569\ub2c8\ub2e4."
    payload = enrich_atom_payload(
        source,
        {"atom_class": "ACTION_INSTRUCTION", "predicate": "TRANSFER_FUNDS"},
    )
    serialized = json.dumps(payload, ensure_ascii=False)
    assert source not in serialized
    assert payload["speech_form_codes"]
    assert {"URGENCY.DANGJANG", "TERM.SAFE_ACCOUNT", "QUANTITY.REMAINING_BALANCE", "QUANTITY.ALL"}.issubset(
        {item["normalized_code"] for item in payload["observed_terms"]}
    )

    sensitive = enrich_atom_payload(
        "OTP 583921\uc744 \uc54c\ub824\uc8fc\uc138\uc694.",
        {"atom_class": "DISCLOSURE_REQUEST", "predicate": "DISCLOSE_OTP"},
    )
    account = enrich_atom_payload(
        "123-456-789 \uacc4\uc88c\ub85c \ubcf4\ub0b4\uc138\uc694.",
        {"atom_class": "ACTION_INSTRUCTION", "predicate": "TRANSFER_FUNDS"},
    )
    assert "583921" not in json.dumps(sensitive, ensure_ascii=False)
    assert "123-456-789" not in json.dumps(account, ensure_ascii=False)


def test_allowlist_prevents_token_dump_and_hallucinated_terms() -> None:
    terms = extract_observed_terms("\uac80\ucc30 \uad00\uacc4\uc790\uc785\ub2c8\ub2e4.")
    assert {term.surface_form for term in terms} == {"\uac80\ucc30"}
    assert all(len(term.surface_form) <= 16 for term in terms)


def test_legacy_normalized_cues_and_new_observed_terms_coexist() -> None:
    event = ExtractedEvent(
        event_family="MONEY_MOVEMENT", subtype="TRANSFER",
        evidence_turn_id=1,
        evidence_text="\uc548\uc804\uacc4\uc88c\ub85c \ub2f9\uc7a5 \uc774\uccb4\ud558\uc138\uc694.",
        detected_at_turn=1, is_requested=True,
    )
    atom = build_semantic_atoms([event])[0]
    assert atom.lexical_cues == ["TRANSFER"]
    assert {term.normalized_code for term in atom.observed_terms} >= {
        "TERM.SAFE_ACCOUNT", "URGENCY.DANGJANG", "ACTION.TRANSFER",
    }


def test_context_observation_points_to_atoms_without_copying_surface_text() -> None:
    event = ExtractedEvent(
        event_family="MONEY_MOVEMENT", subtype="TRANSFER",
        evidence_turn_id=2,
        evidence_text="\uc548\uc804\uacc4\uc88c\ub85c \ub2f9\uc7a5 \uc774\uccb4\ud558\uc138\uc694.",
        detected_at_turn=2, is_requested=True,
    )
    atom = build_semantic_atoms([event])[0]
    features = CaseContextFeatures(observations=[{
        "code": "PURPOSE_SAFE_ACCOUNT", "turn": 2, "status": "REQUESTED",
    }])
    enriched = attach_context_observation_lineage(features, [atom])
    observation = enriched.observations[0]
    assert observation["source_atom_ids"] == [atom.atom_id]
    assert "TERM.SAFE_ACCOUNT" in observation["observed_lexical_codes"]
    assert "surface_form" not in json.dumps(observation, ensure_ascii=False)


def test_llm_atom_validation_enriches_from_target_without_changing_legacy_contract() -> None:
    raw = {
        "atom_class": "ACTION_INSTRUCTION", "speaker": "CALLER", "subject": "CUSTOMER",
        "predicate": "TRANSFER_FUNDS", "actor": "CALLER", "target": "CUSTOMER",
        "object": None, "destination": None, "action_state": "REQUESTED", "modality": "DIRECTIVE",
        "polarity": "POSITIVE", "claim_status": "CALLER_CLAIM", "lexical_cues": ["TRANSFER"],
        "speech_act": "DIRECTIVE", "directive_strength": None, "obligation": None, "urgency": None,
        "authority_pressure": None, "fear_pressure": None, "secrecy_pressure": None,
        "isolation_pressure": None, "financial_pressure": None, "repetition_pressure": None,
        "threat_type": None, "communication_control": None, "auth_secret_type": None,
        "amount_scope": None, "amount_value_krw": None, "claimed_organization": None,
        "claimed_role": None, "claimed_purpose": None,
    }
    atom = _validate_llm_atoms([raw], turn_id=3, target="\uc548\uc804\uacc4\uc88c\ub85c \ub2f9\uc7a5 \ubcf4\ub0b4\uc138\uc694.")[0]
    assert atom.lexical_cues == ["TRANSFER"]
    assert atom.destination == "CLAIMED_SAFE_ACCOUNT"
    assert atom.urgency == "IMMEDIATE"


@pytest.mark.parametrize(
    "state", ["REQUESTED", "INSTRUCTED", "PLANNED", "ATTEMPTED", "REPORTED_ACTION", "VERIFIED", "UNKNOWN"]
)
def test_action_state_vocabulary_is_preserved(state: str) -> None:
    raw = {
        "atom_class": "ACTION_REQUEST" if state == "REQUESTED" else "ACTION_INSTRUCTION",
        "speaker": "CALLER", "subject": "CUSTOMER",
        "predicate": "TRANSFER_FUNDS", "actor": "CALLER", "target": "CUSTOMER",
        "object": None, "destination": None, "action_state": state, "modality": "DIRECTIVE",
        "polarity": "POSITIVE", "claim_status": "CALLER_CLAIM", "lexical_cues": ["TRANSFER"],
        "speech_act": "DIRECTIVE", "directive_strength": None, "obligation": None, "urgency": None,
        "authority_pressure": None, "fear_pressure": None, "secrecy_pressure": None,
        "isolation_pressure": None, "financial_pressure": None, "repetition_pressure": None,
        "threat_type": None, "communication_control": None, "auth_secret_type": None,
        "amount_scope": None, "amount_value_krw": None, "claimed_organization": None,
        "claimed_role": None, "claimed_purpose": None,
    }
    atom = _validate_llm_atoms([raw], turn_id=3)[0]
    assert atom.action_state == state


def test_invalid_entity_slot_is_rejected_instead_of_being_persisted() -> None:
    raw = {
        "atom_class": "ACTION_INSTRUCTION", "speaker": "CALLER", "subject": "FREE_TEXT",
        "predicate": "TRANSFER_FUNDS", "actor": "CALLER", "target": "CUSTOMER",
        "object": None, "destination": None, "action_state": "REQUESTED", "modality": "DIRECTIVE",
        "polarity": "POSITIVE", "claim_status": "CALLER_CLAIM", "lexical_cues": [],
        "speech_act": "DIRECTIVE", "directive_strength": None, "obligation": None, "urgency": None,
        "authority_pressure": None, "fear_pressure": None, "secrecy_pressure": None,
        "isolation_pressure": None, "financial_pressure": None, "repetition_pressure": None,
        "threat_type": None, "communication_control": None, "auth_secret_type": None,
        "amount_scope": None, "amount_value_krw": None, "claimed_organization": None,
        "claimed_role": None, "claimed_purpose": None,
    }
    assert _validate_llm_atoms([raw], turn_id=3) == []


def test_llm_observed_terms_are_replaced_by_source_verified_terms() -> None:
    raw = {
        "atom_class": "ACTION_INSTRUCTION", "speaker": "CALLER", "subject": "CUSTOMER",
        "predicate": "TRANSFER_FUNDS", "actor": "CALLER", "target": "CUSTOMER",
        "object": None, "destination": None, "action_state": "REQUESTED", "modality": "DIRECTIVE",
        "polarity": "POSITIVE", "claim_status": "CALLER_CLAIM", "lexical_cues": ["TRANSFER"],
        "observed_terms": [{"surface_form": "검찰", "lemma": "검찰", "normalized_code": "TERM.PROSECUTION", "term_type": "INSTITUTION", "confidence": 0.99}],
        "speech_act": "DIRECTIVE", "directive_strength": None, "obligation": None, "urgency": None,
        "authority_pressure": None, "fear_pressure": None, "secrecy_pressure": None,
        "isolation_pressure": None, "financial_pressure": None, "repetition_pressure": None,
        "threat_type": None, "communication_control": None, "auth_secret_type": None,
        "amount_scope": None, "amount_value_krw": None, "claimed_organization": None,
        "claimed_role": None, "claimed_purpose": None,
    }
    atom = _validate_llm_atoms([raw], turn_id=3, target="안전계좌로 당장 보내세요.")[0]
    assert "검찰" not in atom.model_dump_json(ensure_ascii=False)
    assert {term.normalized_code for term in atom.observed_terms} >= {
        "TERM.SAFE_ACCOUNT", "URGENCY.DANGJANG",
    }


def test_mixed_predicate_atom_is_rejected_instead_of_merging_meanings() -> None:
    event = ExtractedEvent(
        event_family="MONEY_MOVEMENT", subtype="TRANSFER", evidence_turn_id=1,
        evidence_text="송금", detected_at_turn=1, is_requested=True,
    )
    mixed = build_semantic_atoms([event])[0].model_dump(mode="json")
    mixed.update({"predicate": "TRANSFER_FUNDS", "communication_control": "NO_END_CALL"})
    assert _validate_llm_atoms([mixed], turn_id=1) == []
