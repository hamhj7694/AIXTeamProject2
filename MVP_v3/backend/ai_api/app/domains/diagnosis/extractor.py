from __future__ import annotations

import json
import os
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from openai import AsyncOpenAI, AuthenticationError, RateLimitError

from contracts.diagnosis import ContextResult, ExtractedEvent

from .constants import EVENT_OUTPUT_SCHEMA, SYSTEM_INSTRUCTION
from .budget import active_diagnosis_budget


@dataclass
class EventExtraction:
    turns: list[str]
    events: list[ExtractedEvent]
    successful_turn_ids: list[int]
    extractor_model: str
    warnings: list[str] = field(default_factory=list)


class AiProviderQuotaError(RuntimeError):
    """The configured provider rejected analysis because its quota is exhausted."""


class AiProviderAuthenticationError(RuntimeError):
    """The configured provider rejected the configured API key."""


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


def signal_label(event: ExtractedEvent) -> str:
    """Return a human-readable signal label without retaining source utterances."""
    return _SIGNAL_LABELS.get(
        (event.event_family, event.subtype),
        f"{event.event_family.replace('_', ' ').title()} 신호",
    )


def signal_context_payload(events: list[ExtractedEvent]) -> dict[str, Any]:
    """Project transient event extraction into the only payload context LLM may see.

    `evidence_text` and `amount_context` can contain a caller's exact words. They
    intentionally never cross this boundary. Production deployments can feed
    the same shape directly from an on-device or telephony feature extractor.
    """
    signals: list[dict[str, Any]] = []
    for event in events:
        item: dict[str, Any] = {
            "signal": signal_label(event),
            "event_family": event.event_family,
            "subtype": event.subtype,
            "impersonation_group": event.impersonation_group,
            "turn": event.detected_at_turn,
        }
        if event.amount_krw is not None:
            item["amount_krw"] = event.amount_krw
        if event.is_requested is not None:
            item["is_requested"] = event.is_requested
        signals.append(item)
    return {
        "source": "STRUCTURED_RISK_SIGNALS_ONLY",
        "signal_count": len(signals),
        "signals": signals,
    }


def _openai_timeout_seconds() -> float:
    """OpenAI 호출이 데모 흐름 전체를 대기시키지 않도록 유효한 timeout만 사용한다."""
    try:
        timeout = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "20"))
    except ValueError:
        return 20.0
    return timeout if timeout > 0 else 20.0


def parse_turns(text: str) -> list[str]:
    turns: list[str] = []
    for line in str(text).splitlines():
        parts = re.split(r"(?<=[.!?。！？])\s*", line.strip())
        turns.extend(part.strip() for part in parts if part.strip())
    return turns


def _validate_event(raw: dict[str, Any], turn_id: int, target: str) -> ExtractedEvent:
    if int(raw["evidence_turn_id"]) != turn_id:
        raise ValueError("evidence_turn_id가 TARGET Turn과 다릅니다.")
    evidence = unicodedata.normalize("NFKC", str(raw["evidence_text"]).strip())
    if not evidence or evidence not in unicodedata.normalize("NFKC", target):
        raise ValueError("evidence_text가 TARGET 원문에 존재하지 않습니다.")
    payload = {**raw, "evidence_text": evidence, "detected_at_turn": turn_id}
    return ExtractedEvent.model_validate(payload)


def _local_safety_events(
    turns: list[str], *, only_turn_ids: set[int] | None = None,
) -> list[ExtractedEvent]:
    """Extract a small, deterministic safety net from strong Korean scam signals.

    This is deliberately used only when the remote event extractor is unavailable
    for a turn. It keeps case creation safe and usable without storing a raw
    transcript: downstream code projects these events into structured features
    before it writes a Case or calls the context LLM.
    """
    events: list[ExtractedEvent] = []

    def add(
        turn_id: int,
        target: str,
        family: str,
        subtype: str | None,
        group: str | None = None,
    ) -> None:
        events.append(ExtractedEvent(
            event_family=family,
            subtype=subtype,
            impersonation_group=group,
            evidence_turn_id=turn_id,
            evidence_text=target,
            detected_at_turn=turn_id,
        ))

    for turn_id, target in enumerate(turns, start=1):
        if only_turn_ids is not None and turn_id not in only_turn_ids:
            continue
        compact = re.sub(r"\s+", "", target)
        if any(token in compact for token in ("검찰", "지검", "수사관", "검사")):
            add(turn_id, target, "IMPERSONATION", "PROSECUTION", "PUBLIC_AGENCY")
        elif any(token in compact for token in ("경찰", "경찰청", "형사")):
            add(turn_id, target, "IMPERSONATION", "POLICE", "PUBLIC_AGENCY")
        elif any(token in compact for token in ("은행직원", "금융감독원", "금감원")):
            add(turn_id, target, "IMPERSONATION", "BANK", "FINANCIAL_INSTITUTION")

        if any(token in compact for token in ("안전계좌", "송금", "이체", "입금")):
            add(turn_id, target, "MONEY_MOVEMENT", "TRANSFER")
        if any(token in compact for token in ("지금", "즉시", "바로", "오늘안에", "긴급")):
            add(turn_id, target, "PSY_STRATEGY", "URGENCY")
        if any(token in compact for token in ("범죄", "연루", "체포", "구속", "처벌", "압류")):
            add(turn_id, target, "PSY_STRATEGY", "FEAR")
        if any(token in compact for token in ("알리지마", "말하지마", "통화를끊지말")):
            add(turn_id, target, "ACTION_REQUEST", "CONTACT_RESTRICTION")

        denies_information_request = any(token in compact for token in ("요청하지않", "요구하지않", "제공하지않"))
        if not denies_information_request and any(token in compact for token in ("주민등록번호", "개인정보", "계좌번호")):
            add(turn_id, target, "ACTION_REQUEST", "SENSITIVE_INFO")
        if not denies_information_request and any(token in compact for token in ("인증번호", "비밀번호", "OTP")):
            add(turn_id, target, "ACTION_REQUEST", "AUTH_INFO")
    return events


def _dedupe_events(events: list[ExtractedEvent]) -> list[ExtractedEvent]:
    """Keep one feature event for each signal kind in a turn."""
    unique: list[ExtractedEvent] = []
    seen: set[tuple[int, str, str | None, str | None]] = set()
    for event in events:
        key = (
            event.detected_at_turn,
            event.event_family,
            event.subtype,
            event.impersonation_group,
        )
        if key not in seen:
            unique.append(event)
            seen.add(key)
    return unique


async def extract_events(text: str) -> EventExtraction:
    turns = parse_turns(text)
    if not turns:
        raise ValueError("분석할 발화가 비어 있습니다.")

    budget = active_diagnosis_budget()
    budget.validate_input(text=text, turn_count=len(turns))
    model_name = os.getenv("OPENAI_EVENT_MODEL", "gpt-4o-mini")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않아 실제 LLM 분석을 시작할 수 없습니다.")

    client = AsyncOpenAI(
        api_key=os.environ["OPENAI_API_KEY"], timeout=_openai_timeout_seconds(),
    )
    events: list[ExtractedEvent] = []
    successful: list[int] = []
    warnings: list[str] = []
    failures: list[Exception] = []
    failed_turn_ids: set[int] = set()
    max_output_tokens = int(os.getenv("OPENAI_EVENT_MAX_OUTPUT_TOKENS", "350"))
    for turn_id, target in enumerate(turns, start=1):
        reservation = budget.reserve(
            input_text=f"{SYSTEM_INSTRUCTION}\n[TARGET][TURN {turn_id}] {target}",
            max_output_tokens=max_output_tokens,
        )
        try:
            response = await client.responses.create(
                model=model_name,
                instructions=SYSTEM_INSTRUCTION,
                input=f"[TARGET][TURN {turn_id}][SPEAKER_UNKNOWN] {target}",
                max_output_tokens=max_output_tokens,
                text={"format": {"type": "json_schema", "name": "voice_phishing_events_v2_2", "schema": EVENT_OUTPUT_SCHEMA, "strict": True}},
            )
            budget.settle(reservation, response)
            payload = json.loads(response.output_text)
            events.extend(_validate_event(raw, turn_id, target) for raw in payload["events"])
            successful.append(turn_id)
        except Exception as exc:
            failures.append(exc)
            failed_turn_ids.add(turn_id)
            warnings.append(f"Turn {turn_id} 이벤트 추출 실패: {type(exc).__name__}")
    if not successful:
        fallback_events = _local_safety_events(turns)
        if fallback_events:
            warnings.append("외부 AI 이벤트 추출이 실패하여 강한 위험 신호를 로컬 안전 추출로 이어서 분석했습니다.")
            return EventExtraction(
                turns,
                _dedupe_events(fallback_events),
                list(range(1, len(turns) + 1)),
                "local-safety-fallback-v1",
                warnings,
            )
        if any(isinstance(error, RateLimitError) for error in failures):
            raise AiProviderQuotaError("OpenAI API 크레딧 또는 호출 한도가 부족합니다. 결제·사용 한도를 확인한 뒤 다시 시도해 주세요.")
        if any(isinstance(error, AuthenticationError) for error in failures):
            raise AiProviderAuthenticationError("OpenAI API 키를 확인해 주세요.")
        raise RuntimeError("모든 문장의 이벤트 추출에 실패했습니다.")

    if failed_turn_ids:
        fallback_events = _local_safety_events(turns, only_turn_ids=failed_turn_ids)
        if fallback_events:
            events.extend(fallback_events)
            warnings.append("일부 문장은 외부 AI 대신 로컬 안전 신호로 보완했습니다.")
    return EventExtraction(turns, _dedupe_events(events), successful, model_name, warnings)


def build_context_from_events(events: list[ExtractedEvent]) -> ContextResult:
    subtypes = {event.subtype for event in events if event.subtype}
    groups = {event.impersonation_group for event in events if event.impersonation_group}
    claims = [signal_label(event) for event in events if event.event_family == "IMPERSONATION"]
    if "PUBLIC_AGENCY" in groups:
        incident_type = "공공기관 사칭 의심"
    elif "FINANCIAL_INSTITUTION" in groups:
        incident_type = "금융기관 사칭 의심"
    else:
        incident_type = "유형 확인 필요"
    signals: list[str] = []
    if groups:
        signals.append("기관 또는 신분 사칭")
    if "URGENCY" in subtypes:
        signals.append("긴급성 압박")
    if any(event.event_family == "MONEY_MOVEMENT" for event in events):
        signals.append("금전 이동 요구")
    if any(event.event_family == "ACTION_REQUEST" for event in events):
        signals.append("민감 행동 요구")
    summary = "위험 이벤트가 추출되지 않았습니다." if not signals else f"{', '.join(signals)} 정황이 확인되어 추가 검증이 필요합니다."
    return ContextResult(
        summary=summary, incident_type=incident_type, claims=list(dict.fromkeys(claims)),
        recommended_next_steps=["송금과 정보 제공을 중단하고 공식 채널로 사실관계를 확인하세요."],
        confidence=0.9 if signals else 0.65,
    )


def build_context_from_signal_payload(payload: dict[str, Any]) -> ContextResult:
    """Build a safe context from real structured signals if the LLM is unavailable."""
    signals = payload.get("signals", [])
    labels = [str(item.get("signal", "")) for item in signals if isinstance(item, dict)]
    groups = {item.get("impersonation_group") for item in signals if isinstance(item, dict)}
    if "PUBLIC_AGENCY" in groups:
        incident_type = "공공기관 사칭 의심"
    elif "FINANCIAL_INSTITUTION" in groups:
        incident_type = "금융기관 사칭 의심"
    else:
        incident_type = "유형 확인 필요"
    summary = "위험 신호가 감지되지 않았습니다." if not labels else f"{', '.join(dict.fromkeys(labels))} 신호가 확인되어 추가 검증이 필요합니다."
    claims = [label for label in dict.fromkeys(labels) if "사칭" in label]
    return ContextResult(
        summary=summary,
        incident_type=incident_type,
        claims=claims,
        recommended_next_steps=["송금과 정보 제공을 중단하고 공식 채널로 사실관계를 확인하세요."],
        confidence=0.9 if labels else 0.65,
    )


CONTEXT_OUTPUT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "summary": {"type": "string"}, "incident_type": {"type": "string"},
        "claims": {"type": "array", "items": {"type": "string"}},
        "recommended_next_steps": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["summary", "incident_type", "claims", "recommended_next_steps", "confidence"],
}


async def extract_full_context(text: str) -> ContextResult:
    """전체 맥락을 구조화하되 보이스피싱 최종 판정이나 금융조치를 확정하지 않는다."""
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY가 없습니다.")
    budget = active_diagnosis_budget()
    budget.validate_input(text=text, turn_count=len(parse_turns(text)))
    max_output_tokens = int(os.getenv("OPENAI_CONTEXT_MAX_OUTPUT_TOKENS", "500"))
    reservation = budget.reserve(input_text=text, max_output_tokens=max_output_tokens)
    client = AsyncOpenAI(
        api_key=os.environ["OPENAI_API_KEY"], timeout=_openai_timeout_seconds(),
    )
    response = await client.responses.create(
        model=os.getenv("OPENAI_CONTEXT_MODEL", os.getenv("OPENAI_EVENT_MODEL", "gpt-4o-mini")),
        instructions=(
            "전체 금융 통화 맥락을 구조화한다. 확인된 주장과 권고를 구분하고, "
            "보이스피싱 여부나 금융조치를 최종 확정하지 않는다. 입력에 없는 사실을 추가하지 않는다."
        ),
        input=text,
        max_output_tokens=max_output_tokens,
        text={"format": {"type": "json_schema", "name": "diagnosis_context_v1", "schema": CONTEXT_OUTPUT_SCHEMA, "strict": True}},
    )
    budget.settle(reservation, response)
    return ContextResult.model_validate_json(response.output_text)


async def extract_context_from_signals(events: list[ExtractedEvent]) -> ContextResult:
    """Ask the context LLM to interpret structured signals, not call text.

    This is the production path. The legacy ``extract_full_context`` remains for
    backwards-compatible isolated tests only and must not be called by the Case
    workflow.
    """
    return await extract_context_from_signal_payload(signal_context_payload(events), events=events)


async def extract_context_from_signal_payload(
    payload: dict[str, Any], *, events: list[ExtractedEvent] | None = None,
) -> ContextResult:
    """Context LLM boundary: accepts only a pre-sanitized signal payload."""
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    input_text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    budget = active_diagnosis_budget()
    budget.validate_input(text=input_text, turn_count=max(1, int(payload.get("signal_count", 0))))
    max_output_tokens = int(os.getenv("OPENAI_CONTEXT_MAX_OUTPUT_TOKENS", "500"))
    reservation = budget.reserve(input_text=input_text, max_output_tokens=max_output_tokens)
    client = AsyncOpenAI(
        api_key=os.environ["OPENAI_API_KEY"], timeout=_openai_timeout_seconds(),
    )
    response = await client.responses.create(
        model=os.getenv("OPENAI_CONTEXT_MODEL", os.getenv("OPENAI_EVENT_MODEL", "gpt-4o-mini")),
        instructions=(
            "You receive only structured anti-fraud signals, never a call transcript. "
            "Write a concise Korean case summary, distinguish claims from verified facts, "
            "and recommend safe next checks. Do not invent names, account numbers, quoted "
            "utterances, or a final financial decision."
        ),
        input=input_text,
        max_output_tokens=max_output_tokens,
        text={"format": {"type": "json_schema", "name": "diagnosis_signal_context_v1", "schema": CONTEXT_OUTPUT_SCHEMA, "strict": True}},
    )
    budget.settle(reservation, response)
    return ContextResult.model_validate_json(response.output_text)
