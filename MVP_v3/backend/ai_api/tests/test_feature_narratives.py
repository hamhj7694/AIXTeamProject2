from contracts.diagnosis import ContextNarrative, ContextResult
from ai_api.app.domains.diagnosis.extractor import _speaker_hint, _validated_feature_narratives


def test_demo_speaker_prefix_is_metadata_not_customer_report_wording() -> None:
    assert _speaker_hint("보이스피싱 의심 인물: 카드사 보안센터입니다.") == "SUSPECTED_PARTY"
    assert _speaker_hint("고객: 어떤 결제인지 확인하고 싶습니다.") == "CUSTOMER"
    assert _speaker_hint("고객님 계좌가 범죄에 연루됐습니다.") == "UNKNOWN"


def test_feature_narratives_keep_grounded_references_and_drop_unknown_items() -> None:
    context = ContextResult(
        summary="요약",
        incident_type="사칭 의심",
        confidence=0.9,
        feature_narratives=[
            ContextNarrative(
                code="REQUEST_TRANSFER",
                sentence="상대방이 안전계좌로 이체하라고 요구했습니다.",
                status="REQUESTED",
                source_turns=[2, 99],
                atom_ids=["atom-1", "atom-missing"],
            ),
            ContextNarrative(
                code="UNKNOWN_CODE",
                sentence="입력에 없는 정황입니다.",
                status="CLAIMED",
                source_turns=[2],
                atom_ids=[],
            ),
        ],
    )
    payload = {
        "signals": [{"turn": 2}],
        "case_context_features": {
            "observations": [{"code": "REQUEST_TRANSFER", "turn": 2, "status": "REQUESTED"}],
        },
        "semantic_atoms": [{"atom_id": "atom-1", "source_turn_id": 2}],
    }

    result = _validated_feature_narratives(context, payload)

    assert len(result.feature_narratives) == 1
    assert result.feature_narratives[0].source_turns == [2]
    assert result.feature_narratives[0].atom_ids == ["atom-1"]
    assert result.feature_narratives[0].sentence.startswith("보이스피싱 의심 인물이")


def test_context_result_without_narratives_remains_backward_compatible() -> None:
    context = ContextResult(summary="기존 사건", incident_type="유형 확인 필요", confidence=0.6)

    assert context.feature_narratives == []


def test_customer_completed_action_requires_internal_verification_copy() -> None:
    context = ContextResult(
        summary="송금 여부 확인 필요",
        incident_type="송금 요구 의심",
        customer_statements=["고객이 송금했다고 진술함"],
        confidence=0.8,
        feature_narratives=[ContextNarrative(
            code="CUSTOMER_TRANSFERRED",
            sentence="고객이 송금했다고 진술함",
            status="REPORTED",
            source_turns=[3],
            atom_ids=["customer-action"],
        )],
    )
    payload = {
        "signals": [{"turn": 3}],
        "case_context_features": {"observations": [{"code": "CUSTOMER_TRANSFERRED", "turn": 3}]},
        "semantic_atoms": [{
            "atom_id": "customer-action", "source_turn_id": 3,
            "speaker_role": "CUSTOMER", "actor_role": "CUSTOMER",
            "target_role": "UNKNOWN", "reported_by_role": "CUSTOMER",
        }],
    }

    result = _validated_feature_narratives(context, payload)

    assert "은행 내부 채널에서 별도 확인 필요" in result.customer_statements[0]
    assert "은행 내부 채널에서 별도 확인 필요" in result.feature_narratives[0].sentence


def test_live_call_claim_is_not_rendered_as_customer_report_when_atom_ids_are_missing() -> None:
    context = ContextResult(
        summary="고객이 카드사라 자칭하는 자에 의해 불법 결제가 발생했다고 주장함.",
        incident_type="카드사 사칭 의심",
        claims=["고객이 카드사라 자칭하는 자에게 불법 결제가 발생했다고 주장함."],
        confidence=0.9,
        feature_narratives=[ContextNarrative(
            code="CLAIM_UNAUTHORIZED_PAYMENT",
            sentence="고객이 카드사라 자칭하는 자에게 불법 결제가 발생했다고 주장함.",
            status="CLAIMED",
            source_turns=[1],
            atom_ids=[],
        )],
    )
    payload = {
        "signals": [{"turn": 1}],
        "case_context_features": {
            "observations": [{"code": "CLAIM_UNAUTHORIZED_PAYMENT", "turn": 1, "status": "CLAIMED"}],
        },
        "semantic_atoms": [{
            "atom_id": "claim-1", "source_turn_id": 1,
            "speaker_role": "SUSPECTED_PARTY", "actor_role": "SUSPECTED_PARTY",
            "target_role": "CUSTOMER", "reported_by_role": "SUSPECTED_PARTY",
            "claimed_organization": "CARD_COMPANY",
            "observed_terms": [{"semantic_value": "CARD_COMPANY", "surface_form": "카드사"}],
        }],
    }

    result = _validated_feature_narratives(context, payload)

    narrative = result.feature_narratives[0]
    assert narrative.actor_role == "SUSPECTED_PARTY"
    assert narrative.target_role == "CUSTOMER"
    assert narrative.sentence == "보이스피싱 의심 인물이 카드사 관계자를 사칭하며 승인되지 않은 결제가 발생했다고 주장함."
    assert result.summary == "보이스피싱 의심 인물이 카드사 관계자를 사칭하며 불법 결제가 발생했다고 주장함."
    assert result.claims == ["보이스피싱 의심 인물이 카드사 관계자를 사칭하며 승인되지 않은 결제가 발생했다고 주장함."]
