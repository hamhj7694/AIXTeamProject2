from __future__ import annotations

import json
import os
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from openai import AsyncOpenAI

from contracts.diagnosis import ContextResult, ExtractedEvent

from .constants import EVENT_OUTPUT_SCHEMA, SYSTEM_INSTRUCTION


@dataclass
class EventExtraction:
    turns: list[str]
    events: list[ExtractedEvent]
    successful_turn_ids: list[int]
    extractor_model: str
    warnings: list[str] = field(default_factory=list)


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


def _fixture_events(turns: list[str]) -> list[ExtractedEvent]:
    """API key가 없는 로컬/테스트용 결정론적 extractor. 운영 기본값은 openai다."""
    events: list[ExtractedEvent] = []
    # Korean demo inputs must remain usable even when the legacy fixture
    # patterns were authored under a different terminal encoding.
    for turn_id, target in enumerate(turns, start=1):
        has_agency = any(token in target for token in ("검찰", "경찰", "금융감독", "은행 직원"))
        has_transfer = any(token in target for token in ("안전계좌", "이체", "송금", "입금"))
        has_urgency = any(token in target for token in ("지금", "즉시", "바로", "긴급"))
        if has_agency:
            events.append(ExtractedEvent(event_family="IMPERSONATION", subtype="PROSECUTION", impersonation_group="PUBLIC_AGENCY", evidence_turn_id=turn_id, evidence_text=target, detected_at_turn=turn_id))
        if has_transfer:
            events.append(ExtractedEvent(event_family="MONEY_MOVEMENT", subtype="TRANSFER", impersonation_group=None, evidence_turn_id=turn_id, evidence_text=target, detected_at_turn=turn_id))
        if has_urgency:
            events.append(ExtractedEvent(event_family="PSY_STRATEGY", subtype="URGENCY", impersonation_group=None, evidence_turn_id=turn_id, evidence_text=target, detected_at_turn=turn_id))
    rules = [
        ("IMPERSONATION", "PROSECUTION", "PUBLIC_AGENCY", r"검찰(?:청|관|입니다)?"),
        ("IMPERSONATION", "POLICE", "PUBLIC_AGENCY", r"경찰(?:청|관|입니다)?"),
        ("IMPERSONATION", "BANK", "FINANCIAL_INSTITUTION", r"은행(?:원| 직원|입니다)?"),
        ("PSY_STRATEGY", "URGENCY", None, r"(?:지금|즉시|바로|긴급)[^.!?。！？]*"),
        ("PSY_STRATEGY", "FEAR", None, r"(?:범죄|체포|구속|처벌|압류)[^.!?。！？]*"),
        ("ACTION_REQUEST", "SENSITIVE_INFO", None, r"(?:주민등록번호|개인정보|계좌번호)[^.!?。！？]*"),
        ("ACTION_REQUEST", "AUTH_INFO", None, r"(?:인증번호|비밀번호|OTP)[^.!?。！？]*"),
        ("ACTION_REQUEST", "CONTACT_RESTRICTION", None, r"(?:누구에게도 말하지|연락하지)[^.!?。！？]*"),
        ("MONEY_MOVEMENT", "TRANSFER", None, r"[^.!?。！？]*(?:송금|이체)[^.!?。！？]*"),
    ]
    for turn_id, target in enumerate(turns, start=1):
        for family, subtype, group, pattern in rules:
            match = re.search(pattern, target, re.IGNORECASE)
            if match:
                evidence = match.group(0).strip()
                events.append(ExtractedEvent(
                    event_family=family, subtype=subtype, impersonation_group=group,
                    evidence_turn_id=turn_id, evidence_text=evidence,
                    detected_at_turn=turn_id,
                ))
        amount = re.search(r"\d[\d,]*(?:\.\d+)?\s*(?:억|천만|백만|만|천)?\s*원", target)
        if amount:
            evidence = amount.group(0)
            events.append(ExtractedEvent(
                event_family="AMOUNT", subtype=None, impersonation_group=None,
                evidence_turn_id=turn_id, evidence_text=evidence, amount_context=target,
                is_requested=bool(re.search(r"송금|이체|납부|보내", target)), detected_at_turn=turn_id,
            ))
    return events


async def extract_events(text: str) -> EventExtraction:
    turns = parse_turns(text)
    if not turns:
        raise ValueError("분석할 발화가 비어 있습니다.")

    mode = os.getenv("DIAGNOSIS_EXTRACTOR_MODE", "openai").lower()
    model_name = os.getenv("OPENAI_EVENT_MODEL", "gpt-4o-mini")
    if mode == "fixture":
        return EventExtraction(turns, _fixture_events(turns), list(range(1, len(turns) + 1)), "fixture-v1")

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않아 실제 LLM 분석을 시작할 수 없습니다.")

    client = AsyncOpenAI(
        api_key=os.environ["OPENAI_API_KEY"], timeout=_openai_timeout_seconds(),
    )
    events: list[ExtractedEvent] = []
    successful: list[int] = []
    warnings: list[str] = []
    for turn_id, target in enumerate(turns, start=1):
        try:
            response = await client.responses.create(
                model=model_name,
                instructions=SYSTEM_INSTRUCTION,
                input=f"[TARGET][TURN {turn_id}][SPEAKER_UNKNOWN] {target}",
                text={"format": {"type": "json_schema", "name": "voice_phishing_events_v2_2", "schema": EVENT_OUTPUT_SCHEMA, "strict": True}},
            )
            payload = json.loads(response.output_text)
            events.extend(_validate_event(raw, turn_id, target) for raw in payload["events"])
            successful.append(turn_id)
        except Exception as exc:
            warnings.append(f"Turn {turn_id} 이벤트 추출 실패: {type(exc).__name__}")
    if not successful:
        raise RuntimeError("모든 문장의 이벤트 추출에 실패했습니다.")
    return EventExtraction(turns, events, successful, model_name, warnings)


def build_context_from_events(events: list[ExtractedEvent]) -> ContextResult:
    subtypes = {event.subtype for event in events if event.subtype}
    groups = {event.impersonation_group for event in events if event.impersonation_group}
    claims = [event.evidence_text for event in events if event.event_family == "IMPERSONATION"]
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
    mode = os.getenv("DIAGNOSIS_EXTRACTOR_MODE", "openai").lower()
    if mode == "fixture":
        return build_context_from_events(_fixture_events(parse_turns(text)))
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY가 없습니다.")
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
        text={"format": {"type": "json_schema", "name": "diagnosis_context_v1", "schema": CONTEXT_OUTPUT_SCHEMA, "strict": True}},
    )
    return ContextResult.model_validate_json(response.output_text)
