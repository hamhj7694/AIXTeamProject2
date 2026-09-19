from unittest.mock import patch

from pydantic import ValidationError

from contracts.diagnosis import AnalysisEnvelope, ExtractedEvent, SemanticAtom, StructuredTurn
from ai_api.app.domains.diagnosis.envelope import _event_attribution, enrich_atom_roles, window_result_from_envelope
from ai_api.app.domains.diagnosis.extractor import _infer_unlabeled_demo_role


def _atom(**updates: object) -> SemanticAtom:
    payload: dict[str, object] = {
        "atom_id": "ATM-0001",
        "atom_class": "ACTION_INSTRUCTION",
        "speaker": "CALLER",
        "predicate": "TRANSFER_FUNDS",
        "action_state": "INSTRUCTED",
        "claim_status": "CALLER_CLAIM",
        "source_turn_id": 1,
        "semantic_fingerprint": "sha256:test",
    }
    payload.update(updates)
    return SemanticAtom.model_validate(payload)


def test_envelope_rejects_raw_transcript_fields() -> None:
    try:
        AnalysisEnvelope.model_validate({
            "source": "ON_DEVICE",
            "turn_count": 1,
            "turns": [{
                "turn_id": 1,
                "sequence_index": 1,
                "speaker_role": "SUSPECTED_PARTY",
                "speaker_confidence": 0.9,
                "normalized_summary": "자녀 사칭 및 송금 요구",
            }],
            "raw_transcript": "엄마, 원문을 저장하면 안 돼",
        })
    except ValidationError:
        return
    raise AssertionError("AnalysisEnvelope accepted a raw transcript field")


def test_suspected_party_is_actor_and_vocative_is_not_speaker() -> None:
    atom = enrich_atom_roles(_atom(
        claimed_relationship="CHILD",
        vocative_target="엄마",
        target_role="CUSTOMER",
    ))

    assert atom.speaker_role == "SUSPECTED_PARTY"
    assert atom.actor_role == "SUSPECTED_PARTY"
    assert atom.target_role == "CUSTOMER"
    assert atom.vocative_target == "엄마"
    assert atom.claimed_relationship == "CHILD"


def test_event_attribution_comes_from_atom_roles_instead_of_event_family() -> None:
    event = ExtractedEvent(
        event_family="MONEY_MOVEMENT",
        subtype="TRANSFER",
        evidence_turn_id=1,
        detected_at_turn=1,
        evidence_text="안전계좌로 보내세요",
    )
    atom = _atom(
        speaker="CUSTOMER",
        speaker_role="CUSTOMER",
        actor_role="SUSPECTED_PARTY",
        target_role="CUSTOMER",
        reported_by_role="CUSTOMER",
        predicate="TRANSFER_FUNDS",
    )

    assert _event_attribution(event, [enrich_atom_roles(atom)]) == (
        "CUSTOMER", "SUSPECTED_PARTY", "CUSTOMER", "CUSTOMER",
    )


def test_unlabeled_demo_turns_can_be_marked_as_low_confidence_suspected_party() -> None:
    turns = [
        "엄마, 휴대폰이 고장 나서 임시 번호로 연락해.",
        "급하게 결제해야 하는데 내 인증서가 작동하지 않아.",
        "내가 보내는 계좌로 먼저 300만 원만 이체해 줘.",
        "지금 회의 중이라 전화는 받을 수 없으니 문자로만 답해 줘.",
        "오늘 안에 꼭 필요하니까 다른 사람에게 묻지 말고 보내 줘.",
    ]

    assert _infer_unlabeled_demo_role(turns[0], turns) == ("SUSPECTED_PARTY", 0.58)
    assert _infer_unlabeled_demo_role(turns[1], turns) == ("SUSPECTED_PARTY", 0.58)
    assert _infer_unlabeled_demo_role(turns[2], turns) == ("SUSPECTED_PARTY", 0.58)


def test_csr_window_contains_only_normalized_envelope_summary() -> None:
    envelope = AnalysisEnvelope(
        source="ON_DEVICE",
        turn_count=1,
        turns=[StructuredTurn(
            turn_id=1,
            sequence_index=1,
            speaker_role="SUSPECTED_PARTY",
            speaker_confidence=0.92,
            normalized_summary="서울지검 수사관 사칭 및 15시 송금 요구",
        )],
        semantic_atoms=[_atom(
            claimed_organization_name="서울지검",
            claimed_role_name="수사관",
            deadline_at="15:00",
            relative_deadline_minutes=120,
        )],
    )

    prediction = {
        "raw_ml_risk_score": 80.0,
        "final_risk_score": 80.0,
        "threshold_score": 50.0,
        "candidate_signal_count": 1,
        "guardrail_applied": False,
        "label": "PHISHING",
    }
    with patch("ai_api.app.domains.diagnosis.envelope.predict", return_value=prediction):
        result = window_result_from_envelope(envelope)

    assert result.turns == ["서울지검 수사관 사칭 및 15시 송금 요구"]
    assert result.windows[0].text == "서울지검 수사관 사칭 및 15시 송금 요구"
    assert result.semantic_atoms[0].deadline_at == "15:00"
    assert result.semantic_atoms[0].relative_deadline_minutes == 120
