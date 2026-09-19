from contracts.diagnosis import ContextNarrative, ContextResult
from ai_api.app.domains.diagnosis.extractor import _validated_feature_narratives


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
