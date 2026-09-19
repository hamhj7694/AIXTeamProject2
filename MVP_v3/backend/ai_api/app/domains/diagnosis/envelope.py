"""Privacy-safe Analysis Envelope conversion at the CSR service boundary."""

from __future__ import annotations

from collections import defaultdict
from contracts.diagnosis import (
    AnalysisActorRole,
    AnalysisEnvelope,
    AnalysisSignalEvent,
    CaseContextFeatures,
    ExtractedEvent,
    SemanticAtom,
    SemanticMention,
    StructuredTurn,
    WindowAnalysisResult,
    WindowResult,
)

from .features import features_from_events
from .model_adapter import predict


_EVENT_LABELS: dict[tuple[str, str | None], str] = {
    ("IMPERSONATION", "PROSECUTION"): "검찰·수사기관 사칭 정황",
    ("IMPERSONATION", "POLICE"): "경찰기관 사칭 정황",
    ("IMPERSONATION", "BANK"): "금융기관 사칭 정황",
    ("IMPERSONATION", "FAMILY"): "가족·자녀 사칭 정황",
    ("PSY_STRATEGY", "URGENCY"): "시간제한을 이용한 긴급 처리 압박",
    ("PSY_STRATEGY", "FEAR"): "처벌·금전 피해에 대한 불안 조성",
    ("PSY_STRATEGY", "ISOLATION"): "가족·은행 등 외부 연락 제한",
    ("ACTION_REQUEST", "SENSITIVE_INFO"): "민감 개인정보 제공 요구",
    ("ACTION_REQUEST", "AUTH_INFO"): "인증정보 제공 요구",
    ("ACTION_REQUEST", "DEVICE_CONTROL"): "앱 설치·기기 제어 요구",
    ("ACTION_REQUEST", "CONTACT_RESTRICTION"): "공식 채널 확인 제한",
    ("MONEY_MOVEMENT", "TRANSFER"): "송금·이체 요구",
    ("AMOUNT", None): "구체적인 금액 언급",
}


def normalized_event_label(event: ExtractedEvent) -> str:
    return _EVENT_LABELS.get(
        (event.event_family, event.subtype),
        {
            "IMPERSONATION": "기관·직책·인물 사칭 정황",
            "PSY_STRATEGY": "판단을 압박하거나 통제하려는 정황",
            "ACTION_REQUEST": "특정 행동 요구",
            "MONEY_MOVEMENT": "금전 이동 요구",
            "AMOUNT": "금액 언급",
        }.get(event.event_family, "추가 확인이 필요한 구조화 정황"),
    )


def _role(value: str | None) -> AnalysisActorRole:
    normalized = str(value or "").upper()
    return {
        "CALLER": "SUSPECTED_PARTY",
        "SUSPECTED_PARTY": "SUSPECTED_PARTY",
        "CUSTOMER": "CUSTOMER",
        "BANK_STAFF": "BANK_STAFF",
        "SYSTEM": "SYSTEM",
    }.get(normalized, "UNKNOWN")  # type: ignore[return-value]


def enrich_atom_roles(atom: SemanticAtom) -> SemanticAtom:
    speaker_role = atom.speaker_role or _role(atom.speaker)
    actor_role = atom.actor_role or _role(atom.actor)
    target_role = atom.target_role or _role(atom.target)
    reported_by_role = atom.reported_by_role or (
        "CUSTOMER" if atom.claim_status == "CUSTOMER_REPORTED" else speaker_role
    )
    if speaker_role == "SUSPECTED_PARTY" and (
        atom.claim_status == "CALLER_CLAIM"
        or atom.action_state in {"REQUESTED", "INSTRUCTED"}
        or atom.speech_act in {"REQUEST", "INSTRUCTION", "DIRECTIVE", "ASSERTION"}
    ):
        actor_role = "SUSPECTED_PARTY"
        if target_role == "UNKNOWN":
            target_role = "CUSTOMER"
    if speaker_role == "CUSTOMER" and atom.action_state in {"REPORTED_ACTION", "COMPLETED", "DENIED"}:
        actor_role = "CUSTOMER"
    return atom.model_copy(update={
        "speaker_role": speaker_role,
        "actor_role": actor_role,
        "target_role": target_role,
        "reported_by_role": reported_by_role,
        "speaker_confidence": atom.speaker_confidence if atom.speaker_confidence is not None else 0.85,
        "attribution_confidence": atom.attribution_confidence if atom.attribution_confidence is not None else 0.8,
    })


def _mentions_from_atoms(atoms: list[SemanticAtom]) -> list[SemanticMention]:
    occurrences: dict[tuple[str, str, str], list[tuple[int, float]]] = defaultdict(list)
    mention_types = {
        "INSTITUTION": "INSTITUTION", "ROLE": "ROLE", "ACTION": "ACTION",
        "QUANTITY": "AMOUNT", "URGENCY": "DEADLINE",
    }
    for atom in atoms:
        role = atom.speaker_role or _role(atom.speaker)
        for term in atom.observed_terms:
            value = (term.semantic_value or term.surface_form).strip()
            if value:
                occurrences[(term.normalized_code, value, role)].append((atom.source_turn_id, term.confidence))
        explicit = [
            ("CLAIMED_ORGANIZATION_NAME", atom.claimed_organization_name, "INSTITUTION"),
            ("CLAIMED_BRANCH_NAME", atom.claimed_branch_name, "ORGANIZATION"),
            ("CLAIMED_PERSON_NAME", atom.claimed_person_name, "PERSON_NAME"),
            ("CLAIMED_ROLE", atom.claimed_role_name or atom.claimed_role, "ROLE"),
            ("CLAIMED_RELATIONSHIP", atom.claimed_relationship, "RELATIONSHIP"),
            ("VOCATIVE_TARGET", atom.vocative_target, "VOCATIVE"),
        ]
        for code, value, _ in explicit:
            if value:
                occurrences[(code, value, role)].append((atom.source_turn_id, atom.attribution_confidence or 0.8))

    mentions: list[SemanticMention] = []
    for index, ((code, value, role), found) in enumerate(occurrences.items(), start=1):
        turns = [turn for turn, _ in found]
        term_type = next((
            mention_types.get(term.term_type, "OTHER")
            for atom in atoms for term in atom.observed_terms
            if term.normalized_code == code and (term.semantic_value or term.surface_form).strip() == value
        ), None)
        if term_type is None:
            term_type = {
                "CLAIMED_ORGANIZATION_NAME": "INSTITUTION", "CLAIMED_BRANCH_NAME": "ORGANIZATION",
                "CLAIMED_PERSON_NAME": "PERSON_NAME", "CLAIMED_ROLE": "ROLE",
                "CLAIMED_RELATIONSHIP": "RELATIONSHIP", "VOCATIVE_TARGET": "VOCATIVE",
            }.get(code, "OTHER")
        mentions.append(SemanticMention(
            mention_id=f"MEN-{index:04d}", normalized_code=code,
            normalized_value=value, mention_type=term_type, source_turn_id=min(turns),
            sequence_index=index, speaker_role=role, occurrence_count=len(found),
            first_turn_id=min(turns), last_turn_id=max(turns),
            confidence=min(confidence for _, confidence in found),
        ))
    return mentions


def envelope_from_extraction(
    window_result: WindowAnalysisResult,
    context_features: CaseContextFeatures,
    *,
    source_reference: str | None = None,
) -> AnalysisEnvelope:
    atoms = [enrich_atom_roles(atom) for atom in window_result.semantic_atoms]
    events: list[AnalysisSignalEvent] = []
    events_by_turn: dict[int, list[str]] = defaultdict(list)
    for index, event in enumerate(window_result.events, start=1):
        label = normalized_event_label(event)
        events_by_turn[event.detected_at_turn].append(label)
        suspected_action = event.event_family in {"IMPERSONATION", "PSY_STRATEGY", "ACTION_REQUEST", "MONEY_MOVEMENT"}
        events.append(AnalysisSignalEvent(
            event_id=f"EVT-{event.detected_at_turn:04d}-{index:04d}",
            event_family=event.event_family, subtype=event.subtype,
            impersonation_group=event.impersonation_group,
            source_turn_id=event.detected_at_turn, normalized_label=label,
            speaker_role="SUSPECTED_PARTY" if suspected_action else "UNKNOWN",
            actor_role="SUSPECTED_PARTY" if suspected_action else "UNKNOWN",
            target_role="CUSTOMER" if suspected_action else "UNKNOWN",
            amount_krw=event.amount_krw, is_requested=event.is_requested,
            confidence=0.85,
        ))
    source_turn_count = max(1, len(window_result.turns))
    turns = [
        StructuredTurn(
            turn_id=index, sequence_index=index,
            speaker_role=next((atom.speaker_role for atom in atoms if atom.source_turn_id == index and atom.speaker_role), "UNKNOWN"),
            speaker_confidence=next((atom.speaker_confidence for atom in atoms if atom.source_turn_id == index and atom.speaker_confidence is not None), 0.5),
            normalized_summary=" · ".join(dict.fromkeys(events_by_turn.get(index, []))) or "구조화된 위험 신호 없음",
        )
        for index in range(1, source_turn_count + 1)
    ]
    return AnalysisEnvelope(
        source="DEMO_ADAPTER", source_reference=source_reference,
        extraction_warnings=window_result.warnings,
        turn_count=len(turns), turns=turns, events=events,
        semantic_atoms=atoms, semantic_mentions=_mentions_from_atoms(atoms),
        context_features=context_features,
    )


def window_result_from_envelope(envelope: AnalysisEnvelope) -> WindowAnalysisResult:
    events = [
        ExtractedEvent(
            event_family=event.event_family, subtype=event.subtype,
            impersonation_group=event.impersonation_group,
            evidence_turn_id=event.source_turn_id,
            evidence_text=event.normalized_label,
            amount_krw=event.amount_krw, amount_context=None,
            is_requested=event.is_requested, detected_at_turn=event.source_turn_id,
        )
        for event in envelope.events
    ]
    windows: list[WindowResult] = []
    window_size = 10
    for turn in envelope.turns:
        start_turn = max(1, turn.turn_id - window_size + 1)
        window_events = [event for event in events if start_turn <= event.detected_at_turn <= turn.turn_id]
        features = features_from_events(window_events)
        windows.append(WindowResult(
            segment_id=f"seg-{start_turn:04d}-{turn.turn_id:04d}",
            start_turn=start_turn, end_turn=turn.turn_id,
            text=" · ".join(item.normalized_summary for item in envelope.turns if start_turn <= item.turn_id <= turn.turn_id),
            features=features, **predict(features),
        ))
    return WindowAnalysisResult(
        turns=[turn.normalized_summary for turn in envelope.turns],
        events=events, windows=windows, extractor_model=f"{envelope.source.lower()}-analysis-envelope-v1",
        warnings=envelope.extraction_warnings,
        semantic_atoms=[enrich_atom_roles(atom) for atom in envelope.semantic_atoms],
    )
