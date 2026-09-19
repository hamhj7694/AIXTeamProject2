import asyncio
import json
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from contracts.diagnosis import ExtractedEvent
from ai_api.app.domains.diagnosis.constants import (
    EVENT_OUTPUT_SCHEMA,
    SEMANTIC_ATOM_OUTPUT_PROPERTIES,
)
from ai_api.app.domains.diagnosis.extractor import _validate_llm_atoms, extract_events
from ai_api.app.domains.diagnosis.semantic_atoms import (
    build_semantic_atoms,
    build_structure_coverage_report,
    merge_semantic_atoms,
)
from ai_api.app.domains.diagnosis.relations import build_context_signals, build_semantic_relations
from ai_api.app.domains.diagnosis.grouping import (
    build_action_groups, build_conversation_episodes, build_entity_registry,
)


def test_semantic_atoms_are_deterministic_and_do_not_copy_source_text() -> None:
    event = ExtractedEvent(
        event_family="MONEY_MOVEMENT",
        subtype="TRANSFER",
        evidence_turn_id=2,
        evidence_text="민감한 원문은 Atom에 들어가면 안 됩니다",
        detected_at_turn=2,
        is_requested=True,
    )

    first = build_semantic_atoms([event])
    second = build_semantic_atoms([event])

    assert first == second
    assert first[0].predicate == "TRANSFER_FUNDS"
    assert first[0].action_state == "REQUESTED"
    assert first[0].speech_act == "DIRECTIVE"
    assert first[0].actor == "CALLER"
    assert first[0].target == "CUSTOMER"
    assert first[0].financial_pressure == "HIGH"
    assert first[0].amount_scope is None
    assert "민감한 원문" not in first[0].model_dump_json()
    assert first[0].source_turn_id == 2


def test_llm_event_can_return_multiple_privacy_safe_atoms() -> None:
    source = "검찰 수사관이라며 안전계좌로 즉시 송금하라고 했습니다."
    nullable_fields = {
        "actor": None, "target": "CUSTOMER", "object": None,
        "destination": None, "action_state": None, "modality": "ASSERTION",
        "speech_act": "ASSERTION", "directive_strength": None,
        "obligation": None, "urgency": None, "authority_pressure": "HIGH",
        "fear_pressure": None, "secrecy_pressure": None,
        "isolation_pressure": None, "financial_pressure": None,
        "repetition_pressure": None, "threat_type": None,
        "communication_control": None, "auth_secret_type": None,
        "amount_scope": None, "claimed_purpose": None,
    }
    organization_atom = {
        "atom_class": "ORGANIZATION_CLAIM", "speaker": "CALLER",
        "subject": "CALLER", "predicate": "CLAIMS_ORGANIZATION",
        "polarity": "POSITIVE", "claim_status": "CALLER_CLAIM",
        "lexical_cues": ["PROSECUTION"], **nullable_fields,
    }
    transfer_atom = {
        **organization_atom,
        "atom_class": "ACTION_INSTRUCTION", "subject": "CUSTOMER",
        "predicate": "TRANSFER_FUNDS", "destination": "CLAIMED_SAFE_ACCOUNT",
        "action_state": "INSTRUCTED", "modality": "DIRECTIVE",
        "speech_act": "DIRECTIVE", "urgency": "IMMEDIATE",
        "financial_pressure": "HIGH", "lexical_cues": ["SAFE_ACCOUNT", "IMMEDIATE"],
    }
    payload = {"events": [{
        "event_family": "IMPERSONATION", "subtype": "PROSECUTION",
        "impersonation_group": "PUBLIC_AGENCY", "evidence_turn_id": 1,
        "evidence_text": source, "amount_krw": None, "amount_context": None,
        "is_requested": None,
    }], "semantic_atoms": [organization_atom, transfer_atom]}
    client = Mock()
    client.responses.create = AsyncMock(
        return_value=SimpleNamespace(output_text=json.dumps(payload, ensure_ascii=False))
    )
    with patch(
        "ai_api.app.domains.diagnosis.extractor.AsyncOpenAI", return_value=client,
    ), patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False):
        extraction = asyncio.run(extract_events(source))

    assert len(extraction.semantic_atoms) == 2
    assert {atom.atom_class for atom in extraction.semantic_atoms} == {
        "ORGANIZATION_CLAIM", "ACTION_INSTRUCTION",
    }
    serialized = json.dumps(
        [atom.model_dump(mode="json") for atom in extraction.semantic_atoms],
        ensure_ascii=False,
    )
    assert source not in serialized
    assert extraction.semantic_atoms[1].action_state == "INSTRUCTED"


def test_strict_atom_schema_requires_every_field_and_has_no_raw_text_field() -> None:
    atom_schema = EVENT_OUTPUT_SCHEMA["properties"]["semantic_atoms"]["items"]

    assert set(atom_schema["required"]) == set(SEMANTIC_ATOM_OUTPUT_PROPERTIES)
    assert atom_schema["additionalProperties"] is False
    assert not {
        "raw_text", "source_text", "evidence_text", "quote", "utterance",
    }.intersection(SEMANTIC_ATOM_OUTPUT_PROPERTIES)
    assert SEMANTIC_ATOM_OUTPUT_PROPERTIES["lexical_cues"]["items"]["enum"]


def test_llm_atom_validation_normalizes_claim_state_and_preserves_distinct_controls() -> None:
    base = {
        "speaker": "CALLER", "subject": "CUSTOMER", "actor": "CALLER",
        "target": "CUSTOMER", "object": None, "destination": None,
        "modality": "DIRECTIVE", "polarity": "POSITIVE",
        "claim_status": "CALLER_CLAIM", "lexical_cues": [],
        "speech_act": "INSTRUCTION", "directive_strength": "STRONG",
        "obligation": "REQUIRED", "urgency": None,
        "authority_pressure": None, "fear_pressure": None,
        "secrecy_pressure": None, "isolation_pressure": "HIGH",
        "financial_pressure": None, "repetition_pressure": None,
        "threat_type": None, "auth_secret_type": None, "amount_scope": None,
        "amount_value_krw": None, "claimed_organization": None,
        "claimed_role": None, "claimed_purpose": None,
    }
    raw_atoms = [
        {
            **base, "atom_class": "ORGANIZATION_CLAIM",
            "predicate": "CLAIMS_ORGANIZATION", "action_state": "REQUESTED",
            "claimed_organization": "PROSECUTION_SERVICE",
            "communication_control": None,
        },
        {
            **base, "atom_class": "COMMUNICATION_CONTROL",
            "predicate": "AVOID_EXTERNAL_CONTACT", "action_state": "INSTRUCTED",
            "communication_control": "NO_END_CALL",
        },
        {
            **base, "atom_class": "COMMUNICATION_CONTROL",
            "predicate": "AVOID_EXTERNAL_CONTACT", "action_state": "INSTRUCTED",
            "communication_control": "NO_FAMILY_DISCLOSURE",
        },
    ]

    atoms = _validate_llm_atoms(raw_atoms, turn_id=4)

    assert atoms[0].action_state is None
    assert atoms[1].semantic_fingerprint != atoms[2].semantic_fingerprint
    assert {atom.communication_control for atom in atoms[1:]} == {
        "NO_END_CALL", "NO_FAMILY_DISCLOSURE",
    }


def test_merge_adds_event_derived_atom_when_llm_omits_critical_transfer() -> None:
    event = ExtractedEvent(
        event_family="MONEY_MOVEMENT", subtype="TRANSFER",
        evidence_turn_id=1, evidence_text="transient", detected_at_turn=1,
        is_requested=True,
    )
    claim_raw = {
        "atom_class": "ORGANIZATION_CLAIM", "speaker": "CALLER",
        "subject": "CALLER", "predicate": "CLAIMS_ORGANIZATION",
        "actor": None, "target": "CUSTOMER", "object": None,
        "destination": None, "action_state": None, "modality": "ASSERTION",
        "polarity": "POSITIVE", "claim_status": "CALLER_CLAIM",
        "lexical_cues": ["PROSECUTION"], "speech_act": "ASSERTION",
        "directive_strength": None, "obligation": None, "urgency": None,
        "authority_pressure": "HIGH", "fear_pressure": None,
        "secrecy_pressure": None, "isolation_pressure": None,
        "financial_pressure": None, "repetition_pressure": None,
        "threat_type": None, "communication_control": None,
        "auth_secret_type": None, "amount_scope": None,
        "amount_value_krw": None,
        "claimed_organization": "PROSECUTION_SERVICE", "claimed_role": None,
        "claimed_purpose": None,
    }
    claim_atom = _validate_llm_atoms([claim_raw], turn_id=1)[0]

    merged = merge_semantic_atoms([claim_atom], [event])

    assert merged[0] == claim_atom
    assert any(atom.predicate == "TRANSFER_FUNDS" for atom in merged)
    assert all("transient" not in atom.model_dump_json() for atom in merged)


@pytest.mark.parametrize(
    ("atom_class", "action_state", "modality", "polarity", "expected_state"),
    [
        ("ACTION_REQUEST", "REQUESTED", "REQUEST", "POSITIVE", "REQUESTED"),
        ("ACTION_INSTRUCTION", "REQUESTED", "DIRECTIVE", "POSITIVE", "INSTRUCTED"),
        ("OBSERVED_ACTION", "ATTEMPTED", "ASSERTION", "POSITIVE", "ATTEMPTED"),
        ("REPORTED_ACTION", "COMPLETED", "ASSERTION", "POSITIVE", "COMPLETED"),
        ("CUSTOMER_RESPONSE", "DENIED", "ASSERTION", "NEGATIVE", "DENIED"),
        ("CONDITION", "PLANNED", "CONDITIONAL", "POSITIVE", "PLANNED"),
    ],
)
def test_action_state_minimal_pairs_are_not_conflated(
    atom_class: str,
    action_state: str,
    modality: str,
    polarity: str,
    expected_state: str,
) -> None:
    raw = {
        "atom_class": atom_class, "speaker": "CUSTOMER", "subject": "CUSTOMER",
        "predicate": "TRANSFER_FUNDS", "actor": "CUSTOMER", "target": None,
        "object": None, "destination": "EXTERNAL_ACCOUNT",
        "action_state": action_state, "modality": modality, "polarity": polarity,
        "claim_status": "CUSTOMER_REPORTED", "lexical_cues": ["TRANSFER"],
        "speech_act": "ASSERTION", "directive_strength": None,
        "obligation": None, "urgency": None, "authority_pressure": None,
        "fear_pressure": None, "secrecy_pressure": None,
        "isolation_pressure": None, "financial_pressure": None,
        "repetition_pressure": None, "threat_type": None,
        "communication_control": None, "auth_secret_type": None,
        "amount_scope": None, "amount_value_krw": None,
        "claimed_organization": None, "claimed_role": None,
        "claimed_purpose": None,
    }

    atom = _validate_llm_atoms([raw], turn_id=7)[0]

    assert atom.action_state == expected_state
    assert atom.modality == modality
    assert atom.polarity == polarity


def test_unknown_fields_remain_unknown_instead_of_being_invented() -> None:
    raw = {
        "atom_class": "ACTION_REQUEST", "speaker": "CALLER",
        "subject": "CUSTOMER", "predicate": "DISCLOSE_OTP", "actor": "CALLER",
        "target": "CUSTOMER", "object": None, "destination": None,
        "action_state": "REQUESTED", "modality": "REQUEST",
        "polarity": "POSITIVE", "claim_status": "CALLER_CLAIM",
        "lexical_cues": ["OTP"], "speech_act": "REQUEST",
        "directive_strength": "UNKNOWN", "obligation": "UNKNOWN",
        "urgency": None, "authority_pressure": None, "fear_pressure": None,
        "secrecy_pressure": None, "isolation_pressure": None,
        "financial_pressure": None, "repetition_pressure": None,
        "threat_type": None, "communication_control": None,
        "auth_secret_type": "OTP", "amount_scope": None,
        "amount_value_krw": None, "claimed_organization": None,
        "claimed_role": None, "claimed_purpose": None,
    }

    atom = _validate_llm_atoms([raw], turn_id=8)[0]

    assert atom.auth_secret_type == "OTP"
    assert atom.urgency is None
    assert atom.amount_scope is None
    assert atom.amount_value_krw is None


@pytest.mark.parametrize("secret_type", ["OTP", "PASSWORD", "PIN", "CARD_CVC"])
def test_authentication_secret_types_are_preserved_individually(secret_type: str) -> None:
    raw = {
        "atom_class": "DISCLOSURE_REQUEST", "speaker": "CALLER",
        "subject": "CUSTOMER", "predicate": "DISCLOSE_OTP", "actor": "CALLER",
        "target": "CUSTOMER", "object": None, "destination": None,
        "action_state": "REQUESTED", "modality": "REQUEST", "polarity": "POSITIVE",
        "claim_status": "CALLER_CLAIM", "lexical_cues": [secret_type],
        "speech_act": "REQUEST", "directive_strength": "STRONG",
        "obligation": "REQUIRED", "urgency": "IMMEDIATE",
        "authority_pressure": None, "fear_pressure": None, "secrecy_pressure": None,
        "isolation_pressure": None, "financial_pressure": None,
        "repetition_pressure": None, "threat_type": None,
        "communication_control": None, "auth_secret_type": secret_type,
        "amount_scope": None, "amount_value_krw": None,
        "claimed_organization": None, "claimed_role": None, "claimed_purpose": None,
    }

    atom = _validate_llm_atoms([raw], turn_id=9)[0]

    assert atom.auth_secret_type == secret_type
    assert atom.urgency == "IMMEDIATE"
    assert atom.obligation == "REQUIRED"


def test_pressure_dimensions_and_euphemistic_purpose_stay_separate() -> None:
    raw = {
        "atom_class": "ACTION_INSTRUCTION", "speaker": "CALLER",
        "subject": "CUSTOMER", "predicate": "TRANSFER_FUNDS", "actor": "CALLER",
        "target": "CUSTOMER", "object": None, "destination": "CLAIMED_SAFE_ACCOUNT",
        "action_state": "INSTRUCTED", "modality": "DIRECTIVE", "polarity": "POSITIVE",
        "claim_status": "CALLER_CLAIM", "lexical_cues": ["SAFE_ACCOUNT", "IMMEDIATE"],
        "speech_act": "INSTRUCTION", "directive_strength": "STRONG",
        "obligation": "REQUIRED", "urgency": "IMMEDIATE",
        "authority_pressure": "HIGH", "fear_pressure": "HIGH",
        "secrecy_pressure": "HIGH", "isolation_pressure": "HIGH",
        "financial_pressure": "HIGH", "repetition_pressure": "HIGH",
        "threat_type": "ASSET_FREEZE_THREAT", "communication_control": None,
        "auth_secret_type": None, "amount_scope": "ALL_FUNDS", "amount_value_krw": None,
        "claimed_organization": None, "claimed_role": None,
        "claimed_purpose": "ASSET_PROTECTION",
    }

    control = {
        **raw,
        "atom_class": "COMMUNICATION_CONTROL",
        "predicate": "AVOID_EXTERNAL_CONTACT",
        "destination": None,
        "action_state": "INSTRUCTED",
        "modality": "PROHIBITION",
        "speech_act": "PROHIBITION",
        "directive_strength": "STRONG",
        "obligation": "REQUIRED",
        "urgency": None,
        "threat_type": None,
        "communication_control": "NO_BANK_CONTACT",
        "amount_scope": None,
        "claimed_purpose": None,
    }
    atoms = _validate_llm_atoms([raw, control], turn_id=10)
    atom, control_atom = atoms

    assert atom.action_state == "INSTRUCTED"
    assert atom.urgency == "IMMEDIATE"
    assert atom.obligation == "REQUIRED"
    assert atom.authority_pressure == "HIGH"
    assert atom.fear_pressure == "HIGH"
    assert atom.repetition_pressure == "HIGH"
    assert atom.threat_type == "ASSET_FREEZE_THREAT"
    assert atom.communication_control is None
    assert control_atom.communication_control == "NO_BANK_CONTACT"
    assert atom.amount_scope == "ALL_FUNDS"
    assert atom.claimed_purpose == "ASSET_PROTECTION"


def test_multiple_amounts_and_actions_in_one_call_remain_individual_atoms() -> None:
    events = [
        ExtractedEvent(
            event_family="MONEY_MOVEMENT", subtype="TRANSFER", evidence_turn_id=4,
            evidence_text="transient", detected_at_turn=4, is_requested=True,
            amount_krw=3000000,
        ),
        ExtractedEvent(
            event_family="MONEY_MOVEMENT", subtype="TRANSFER", evidence_turn_id=4,
            evidence_text="transient", detected_at_turn=4, is_requested=True,
            amount_krw=500000,
        ),
        ExtractedEvent(
            event_family="ACTION_REQUEST", subtype="AUTH_INFO", evidence_turn_id=4,
            evidence_text="transient", detected_at_turn=4, is_requested=True,
        ),
    ]
    atoms = build_semantic_atoms(events)

    assert [atom.amount_value_krw for atom in atoms if atom.amount_value_krw is not None] == [3000000, 500000]
    assert len(atoms) == 3


def test_structure_coverage_report_counts_atoms_and_observed_terms() -> None:
    event = ExtractedEvent(
        event_family="MONEY_MOVEMENT", subtype="TRANSFER", evidence_turn_id=1,
        evidence_text="안전계좌로 당장 이체", detected_at_turn=1, is_requested=True,
    )
    atoms = build_semantic_atoms([event])
    report = build_structure_coverage_report([event], atoms)

    assert report["schema_version"] == "semantic-coverage.v1"
    assert report["event_coverage"] == 1.0
    assert report["semantic_atom_count"] == 1
    assert report["observed_term_count"] >= 2


def test_relations_and_signals_are_grounded_only_in_existing_atom_ids() -> None:
    event = ExtractedEvent(
        event_family="MONEY_MOVEMENT", subtype="TRANSFER",
        evidence_turn_id=1, evidence_text="transient", detected_at_turn=1,
        is_requested=True,
    )
    atoms = build_semantic_atoms([event])
    organization = atoms[0].model_copy(update={
        "atom_id": "ATM-ORG", "predicate": "CLAIMS_ORGANIZATION",
        "claimed_organization": "PROSECUTION_SERVICE",
    })
    role = organization.model_copy(update={
        "atom_id": "ATM-ROLE", "atom_class": "ROLE_CLAIM",
        "predicate": "CLAIMS_ROLE", "claimed_organization": None,
        "claimed_role": "INVESTIGATOR",
    })
    transfer = atoms[0].model_copy(update={"atom_id": "ATM-TRANSFER"})
    control = organization.model_copy(update={
        "atom_id": "ATM-CONTROL", "atom_class": "COMMUNICATION_CONTROL",
        "predicate": "KEEP_SECRET", "claimed_organization": None,
        "communication_control": "NO_END_CALL",
    })

    relations = build_semantic_relations([organization, role, transfer, control])
    signals = build_context_signals([organization, role, transfer, control])

    assert any(relation.relation_type == "SUPPORTS" for relation in relations)
    assert len(signals) == 1
    signal = signals[0]
    assert set(signal.atom_ids) == {"ATM-ORG", "ATM-ROLE", "ATM-TRANSFER", "ATM-CONTROL"}
    assert "transient" not in signal.model_dump_json()


def test_relation_builder_does_not_hallucinate_cross_turn_links() -> None:
    event = ExtractedEvent(
        event_family="MONEY_MOVEMENT", subtype="TRANSFER",
        evidence_turn_id=2, evidence_text="transient", detected_at_turn=2,
        is_requested=True,
    )
    transfer = build_semantic_atoms([event])[0]
    organization = transfer.model_copy(update={
        "atom_id": "ATM-ORG", "source_turn_id": 1,
        "predicate": "CLAIMS_ORGANIZATION",
        "claimed_organization": "PROSECUTION_SERVICE",
    })
    assert build_semantic_relations([organization, transfer]) == []
    assert build_context_signals([organization, transfer]) == []


def test_episode_action_group_and_entity_registry_use_only_explicit_atom_lineage() -> None:
    source = ExtractedEvent(
        event_family="MONEY_MOVEMENT", subtype="TRANSFER",
        evidence_turn_id=3, evidence_text="transient", detected_at_turn=3,
        is_requested=True,
    )
    transfer = build_semantic_atoms([source])[0].model_copy(update={"atom_id": "ATM-TRANSFER"})
    control = transfer.model_copy(update={
        "atom_id": "ATM-CONTROL", "predicate": "KEEP_SECRET",
        "atom_class": "COMMUNICATION_CONTROL", "communication_control": "NO_END_CALL",
        "subject": None, "actor": None, "target": None,
    })
    organization = transfer.model_copy(update={
        "atom_id": "ATM-ORG", "predicate": "CLAIMS_ORGANIZATION",
        "action_state": None, "claimed_organization": "PROSECUTION_SERVICE",
        "subject": None, "actor": None, "target": None,
    })

    episodes = build_conversation_episodes([transfer, control, organization])
    groups = build_action_groups([transfer, control, organization])
    entities = build_entity_registry([transfer, control, organization])

    assert len(episodes) == 1
    assert episodes[0].episode_type == "IDENTITY_CLAIM"
    assert set(episodes[0].atom_ids) == {"ATM-TRANSFER", "ATM-CONTROL", "ATM-ORG"}
    assert {group.action_predicate for group in groups} == {"KEEP_SECRET", "TRANSFER_FUNDS"}
    customer_account = next(item for item in entities if item.entity_code == "CUSTOMER_ACCOUNT")
    assert customer_account.atom_ids == ["ATM-TRANSFER"]
    assert customer_account.source_turn_ids == [3]
    assert "transient" not in (episodes + groups + entities)[0].model_dump_json()


def test_grouping_does_not_merge_atoms_across_turns_into_one_episode() -> None:
    first = build_semantic_atoms([ExtractedEvent(
        event_family="IMPERSONATION", subtype="PROSECUTION",
        evidence_turn_id=1, evidence_text="transient", detected_at_turn=1,
    )])[0]
    second = build_semantic_atoms([ExtractedEvent(
        event_family="MONEY_MOVEMENT", subtype="TRANSFER",
        evidence_turn_id=2, evidence_text="transient", detected_at_turn=2,
        is_requested=True,
    )])[0]

    episodes = build_conversation_episodes([first, second])

    assert [(episode.start_turn, episode.end_turn) for episode in episodes] == [(1, 1), (2, 2)]


def test_relation_rules_cover_justifies_requires_and_causes_without_free_text() -> None:
    base = build_semantic_atoms([ExtractedEvent(
        event_family="MONEY_MOVEMENT", subtype="TRANSFER",
        evidence_turn_id=1, evidence_text="transient", detected_at_turn=1,
        is_requested=True,
    )])[0]
    threat = base.model_copy(update={
        "atom_id": "ATM-THREAT", "atom_class": "THREAT",
        "predicate": "THREATEN_ASSET_FREEZE", "action_state": None,
        "threat_type": "ASSET_FREEZE_THREAT",
    })
    action = base.model_copy(update={"atom_id": "ATM-ACTION"})
    disclosure = base.model_copy(update={
        "atom_id": "ATM-DISCLOSURE", "atom_class": "DISCLOSURE_REQUEST",
        "predicate": "DISCLOSE_OTP", "auth_secret_type": None,
    })
    auth = base.model_copy(update={
        "atom_id": "ATM-AUTH", "atom_class": "ACTION_REQUEST",
        "predicate": "DISCLOSE_OTP", "auth_secret_type": "OTP",
    })
    urgency = base.model_copy(update={
        "atom_id": "ATM-URGENCY", "atom_class": "WARNING",
        "predicate": "OTHER", "action_state": None, "urgency": "IMMEDIATE",
    })

    relations = build_semantic_relations([threat, action, disclosure, auth, urgency])
    relation_types = {relation.relation_type for relation in relations}

    assert {"JUSTIFIES", "REQUIRES", "CAUSES"}.issubset(relation_types)
    assert all("transient" not in relation.model_dump_json() for relation in relations)
