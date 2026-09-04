"""Privacy-safe diagnosis projection used at the Case persistence boundary.

Raw utterances are useful only while a feature extractor is running. A Shared
Case stores reproducible signal codes, numeric features, and a safe Case
summary—not the original transcript or extracted verbatim spans.
"""

from __future__ import annotations

from collections.abc import Iterable

from contracts.diagnosis import DiagnosisResult, Evidence, ExtractedEvent, WindowResult


_SIGNAL_LABELS: dict[tuple[str, str | None], str] = {
    ("IMPERSONATION", "PROSECUTION"): "검찰·수사기관 사칭",
    ("IMPERSONATION", "POLICE"): "경찰기관 사칭",
    ("IMPERSONATION", "BANK"): "금융기관 사칭",
    ("PSY_STRATEGY", "URGENCY"): "긴급 처리 압박",
    ("PSY_STRATEGY", "FEAR"): "처벌·피해 불안 조성",
    ("PSY_STRATEGY", "ISOLATION"): "주변 알림 제한",
    ("ACTION_REQUEST", "SENSITIVE_INFO"): "민감 개인정보 요구",
    ("ACTION_REQUEST", "AUTH_INFO"): "인증정보 요구",
    ("ACTION_REQUEST", "CONTACT_RESTRICTION"): "공식 채널 확인 제한",
    ("MONEY_MOVEMENT", "TRANSFER"): "송금·이체 요구",
    ("AMOUNT", None): "금액 언급",
}


def _label(event: ExtractedEvent) -> str:
    return _SIGNAL_LABELS.get(
        (event.event_family, event.subtype),
        f"{event.event_family.replace('_', ' ').title()} 신호",
    )


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _safe_window(window: WindowResult, events: list[ExtractedEvent]) -> WindowResult:
    labels = _unique(
        _label(event) for event in events
        if window.start_turn <= event.detected_at_turn <= window.end_turn
    )
    return window.model_copy(update={
        "text": " · ".join(labels) if labels else "위험 피처 미감지",
    })


def project_diagnosis_for_case(diagnosis: DiagnosisResult) -> DiagnosisResult:
    """Remove every field that can reproduce the submitted source utterance."""
    safe_events = [
        event.model_copy(update={"evidence_text": _label(event), "amount_context": None})
        for event in diagnosis.events
    ]
    safe_evidence = [
        Evidence(
            turn=event.evidence_turn_id,
            event_family=event.event_family,
            subtype=event.subtype,
            text=_label(event),
        )
        for event in safe_events
    ]
    safe_windows = [_safe_window(window, safe_events) for window in diagnosis.windows]
    safe_claims = _unique(_label(event) for event in safe_events if event.event_family == "IMPERSONATION")
    safe_context = diagnosis.context.model_copy(update={"claims": safe_claims})
    metadata = {**diagnosis.model_metadata, "source_text_retention": "NONE", "context_input": "STRUCTURED_RISK_SIGNALS_ONLY"}
    return diagnosis.model_copy(update={
        "context": safe_context,
        "events": safe_events,
        "evidence": safe_evidence,
        "windows": safe_windows,
        "model_metadata": metadata,
    })
