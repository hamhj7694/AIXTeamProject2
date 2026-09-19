from __future__ import annotations

import json
import hashlib
import os
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from openai import AsyncOpenAI, AuthenticationError, RateLimitError

from contracts.diagnosis import CaseContextFeatures, ContextNarrative, ContextResult, ExtractedEvent, SemanticAtom

from .constants import (
    ATOM_CLASSES,
    CLAIMED_ORGANIZATION_CODES,
    CLAIMED_ROLE_CODES,
    ENTITY_CODES,
    EVENT_OUTPUT_SCHEMA,
    PREDICATE_CODES,
    SEMANTIC_ATOM_INSTRUCTION,
    SYSTEM_INSTRUCTION,
)
from .budget import active_diagnosis_budget
from .lexical_cues import enrich_atom_payload


@dataclass
class EventExtraction:
    turns: list[str]
    events: list[ExtractedEvent]
    successful_turn_ids: list[int]
    extractor_model: str
    warnings: list[str] = field(default_factory=list)
    semantic_atoms: list[SemanticAtom] = field(default_factory=list)


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

# Codes rendered by the staff-facing analysis result. The context LLM may only
# narrate one of these known signals; unknown labels are discarded before the
# result reaches the API and frontend.
_FEATURE_NARRATIVE_CODES = frozenset({
    "ROLE_PROSECUTION", "ROLE_POLICE", "ROLE_BANK", "ROLE_FAMILY", "ROLE_SUPPORT",
    "CLAIMED_ORGANIZATION", "CLAIM_CRIME_INVOLVEMENT", "CLAIM_ACCOUNT_VERIFICATION",
    "CLAIM_DEVICE_BROKEN", "CLAIM_UNAUTHORIZED_PAYMENT", "CLAIM_LOAN_APPROVAL",
    "REQUEST_TRANSFER", "REQUEST_INSTALL_APP", "REQUEST_AUTH_INFO", "REQUEST_PERSONAL_INFO",
    "REQUEST_KEEP_CALL", "REQUEST_SECRECY", "REQUEST_OPEN_URL", "REQUEST_AMOUNT",
    "PURPOSE_SAFE_ACCOUNT", "PURPOSE_LOAN_REPAYMENT", "PURPOSE_REPAIR", "PURPOSE_REFUND",
    "DEADLINE_TODAY", "DEADLINE_IMMEDIATE", "TACTIC_FEAR", "TACTIC_URGENCY",
    "TACTIC_ISOLATION", "CUSTOMER_TRANSFERRED", "CUSTOMER_NOT_TRANSFERRED",
    "CUSTOMER_PROVIDED_AUTH", "CUSTOMER_PROVIDED_PERSONAL_INFO", "CUSTOMER_INSTALLED_APP",
    "NORMAL_DEPOSIT_CONSULTATION", "NORMAL_CARD_CONSULTATION", "NORMAL_DAILY_CALL",
    "EXTRACTED_CONTEXT",
})


def signal_label(event: ExtractedEvent) -> str:
    """Return a human-readable signal label without retaining source utterances."""
    return _SIGNAL_LABELS.get(
        (event.event_family, event.subtype),
        f"{event.event_family.replace('_', ' ').title()} 신호",
    )


def build_case_context_features(events: list[ExtractedEvent]) -> CaseContextFeatures:
    """위험 모델의 숫자 벡터와 별개인 privacy-safe 사건 맥락 피처를 만든다."""
    actor_types: list[str] = []
    claims: list[str] = []
    actions: list[str] = []
    tactics: list[str] = []
    exposures: list[str] = []
    amounts: list[float] = []
    requested_amounts: list[float] = []
    chronology: list[str] = []
    for event in sorted(events, key=lambda item: item.detected_at_turn):
        code = event.subtype or event.event_family
        if event.event_family == "IMPERSONATION":
            actor_types.append(event.impersonation_group or code)
            claims.append(f"CLAIMED_ROLE:{code}")
        elif event.event_family == "MONEY_MOVEMENT" and event.is_requested is not False:
            actions.append(f"REQUEST:{code}")
        elif event.event_family == "ACTION_REQUEST" and event.is_requested is not False:
            actions.append(f"REQUEST:{code}")
            if code in {"SENSITIVE_INFO", "AUTH_INFO"}:
                exposures.append(code)
        elif event.event_family == "PSY_STRATEGY":
            tactics.append(code)
        if event.amount_krw is not None:
            amounts.append(event.amount_krw)
            if event.is_requested:
                requested_amounts.append(event.amount_krw)
        chronology.append(f"T{event.detected_at_turn}:{event.event_family}:{code}")
    unique = lambda values: list(dict.fromkeys(values))
    return CaseContextFeatures(
        claimed_actor_types=unique(actor_types), claim_codes=unique(claims),
        requested_action_codes=unique(actions), manipulation_tactic_codes=unique(tactics),
        exposure_risk_codes=unique(exposures), amount_values_krw=unique(amounts),
        requested_amount_values_krw=unique(requested_amounts),
        chronology=unique(chronology),
        unknown_fields=["transfer_status", "personal_information_exposure", "authentication_information_exposure"],
    )


def signal_context_payload(
    events: list[ExtractedEvent],
    *,
    semantic_atoms: list[SemanticAtom] | None = None,
) -> dict[str, Any]:
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
    payload: dict[str, Any] = {
        "source": "STRUCTURED_CONTEXT_FEATURES_ONLY",
        "signal_count": len(signals),
        "signals": signals,
        "case_context_features": build_case_context_features(events).model_dump(mode="json"),
    }
    if semantic_atoms:
        # Atoms are the privacy-safe detail layer. They carry short, source-
        # verified lexical cues (for example `서울지검` or `수사관`) and
        # normalized meaning, but never evidence_text or the call transcript.
        payload["semantic_atoms"] = [
            {
                "atom_id": atom.atom_id,
                "source_turn_id": atom.source_turn_id,
                "atom_class": atom.atom_class,
                "speaker": atom.speaker,
                "speaker_role": atom.speaker_role,
                "actor_role": atom.actor_role,
                "target_role": atom.target_role,
                "reported_by_role": atom.reported_by_role,
                "speaker_confidence": atom.speaker_confidence,
                "attribution_confidence": atom.attribution_confidence,
                "predicate": atom.predicate,
                "subject": atom.subject,
                "actor": atom.actor,
                "target": atom.target,
                "object": atom.object,
                "destination": atom.destination,
                "action_state": atom.action_state,
                "modality": atom.modality,
                "polarity": atom.polarity,
                "claim_status": atom.claim_status,
                "speech_act": atom.speech_act,
                "obligation": atom.obligation,
                "urgency": atom.urgency,
                "authority_pressure": atom.authority_pressure,
                "fear_pressure": atom.fear_pressure,
                "secrecy_pressure": atom.secrecy_pressure,
                "isolation_pressure": atom.isolation_pressure,
                "financial_pressure": atom.financial_pressure,
                "communication_control": atom.communication_control,
                "auth_secret_type": atom.auth_secret_type,
                "amount_scope": atom.amount_scope,
                "amount_value_krw": atom.amount_value_krw,
                "amount_role": atom.amount_role,
                "amount_direction": atom.amount_direction,
                "claimed_organization": atom.claimed_organization,
                "claimed_organization_name": atom.claimed_organization_name,
                "claimed_branch_name": atom.claimed_branch_name,
                "claimed_person_name": atom.claimed_person_name,
                "claimed_role": atom.claimed_role,
                "claimed_role_name": atom.claimed_role_name,
                "claimed_relationship": atom.claimed_relationship,
                "claimed_purpose": atom.claimed_purpose,
                "vocative_target": atom.vocative_target,
                "deadline_at": atom.deadline_at,
                "relative_deadline_minutes": atom.relative_deadline_minutes,
                "mention_order": atom.mention_order,
                "occurrence_count": atom.occurrence_count,
                "lexical_cues": atom.lexical_cues,
                "observed_terms": [term.model_dump(mode="json") for term in atom.observed_terms],
            }
            for atom in semantic_atoms
        ]
    return payload


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
    payload = {
        key: value for key, value in raw.items()
        if key != "semantic_atoms"
    }
    payload.update({"evidence_text": evidence, "detected_at_turn": turn_id})
    return ExtractedEvent.model_validate(payload)


def _validate_llm_atoms(raw_atoms: Any, turn_id: int, target: str = "") -> list[SemanticAtom]:
    """Validate LLM atoms and attach deterministic non-text lineage."""
    if not isinstance(raw_atoms, list):
        return []
    result: list[SemanticAtom] = []
    for index, raw in enumerate(raw_atoms, start=1):
        if not isinstance(raw, dict):
            continue
        payload = dict(raw)
        predicate = str(payload.get("predicate") or "UNKNOWN")
        if not _is_single_primary_predicate(payload, predicate):
            continue
        if predicate.startswith("CLAIMS_"):
            payload["action_state"] = None
        elif payload.get("atom_class") == "ACTION_INSTRUCTION" and payload.get("action_state") in {None, "REQUESTED"}:
            payload["action_state"] = "INSTRUCTED"
        fingerprint_payload = {
            key: payload.get(key)
            for key in sorted(payload)
            if key not in {"atom_id", "source_event_id", "source_turn_id", "semantic_fingerprint"}
        }
        fingerprint = hashlib.sha256(
            json.dumps(
                {"turn_id": turn_id, **fingerprint_payload},
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        payload.update({
            "atom_id": f"ATM-{turn_id:04d}-LLM-{index:04d}",
            "source_event_id": f"EVT-{turn_id:04d}-LLM-{index:04d}",
            "source_turn_id": turn_id,
            "semantic_fingerprint": f"sha256:{fingerprint}",
        })
        try:
            result.append(SemanticAtom.model_validate(enrich_atom_payload(target, payload)))
        except Exception:
            continue
    return result


def _is_single_primary_predicate(payload: dict[str, Any], predicate: str) -> bool:
    """Reject one Atom that mixes independently reviewable meanings."""
    if predicate not in PREDICATE_CODES:
        return False
    if payload.get("atom_class") not in ATOM_CLASSES:
        return False
    for field in ("subject", "actor", "target", "object", "destination"):
        value = payload.get(field)
        if value is not None:
            allowed = {"destination": {"CLAIMED_SAFE_ACCOUNT", "EXTERNAL_ACCOUNT", "CUSTOMER_ACCOUNT", "UNKNOWN"}}.get(field, set(ENTITY_CODES))
            if value not in allowed:
                return False
    if payload.get("claimed_organization") not in {None, *CLAIMED_ORGANIZATION_CODES}:
        return False
    if payload.get("claimed_role") not in {None, *CLAIMED_ROLE_CODES}:
        return False
    if predicate == "CLAIMS_ORGANIZATION" and payload.get("claimed_role") is not None:
        return False
    if predicate == "CLAIMS_ROLE" and payload.get("claimed_organization") is not None:
        return False
    if predicate in {"TRANSFER_FUNDS", "WITHDRAW_CASH", "INSTALL_APP", "OPEN_URL", "SHARE_SCREEN"}:
        if payload.get("communication_control") is not None or payload.get("auth_secret_type") is not None:
            return False
    if predicate in {"DISCLOSE_OTP", "DISCLOSE_PASSWORD", "PROVIDE_CARD_INFO"}:
        if payload.get("destination") is not None or payload.get("amount_value_krw") is not None:
            return False
    if payload.get("atom_class") == "COMMUNICATION_CONTROL" and predicate not in {
        "MAINTAIN_CALL", "END_CALL", "KEEP_SECRET", "AVOID_REPORTING", "AVOID_EXTERNAL_CONTACT",
    }:
        return False
    return True


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
    semantic_atoms: list[SemanticAtom] = []
    failures: list[Exception] = []
    failed_turn_ids: set[int] = set()
    max_output_tokens = int(os.getenv("OPENAI_EVENT_MAX_OUTPUT_TOKENS", "1800"))
    for turn_id, target in enumerate(turns, start=1):
        reservation = budget.reserve(
            input_text=f"{SYSTEM_INSTRUCTION}\n[TARGET][TURN {turn_id}] {target}",
            max_output_tokens=max_output_tokens,
        )
        try:
            response = await client.responses.create(
                model=model_name,
                instructions=f"{SYSTEM_INSTRUCTION}\n\n{SEMANTIC_ATOM_INSTRUCTION}",
                input=f"[TARGET][TURN {turn_id}][SPEAKER_UNKNOWN] {target}",
                max_output_tokens=max_output_tokens,
                text={"format": {"type": "json_schema", "name": "voice_phishing_events_v2_2", "schema": EVENT_OUTPUT_SCHEMA, "strict": True}},
            )
            budget.settle(reservation, response)
            payload = json.loads(response.output_text)
            events.extend(_validate_event(raw, turn_id, target) for raw in payload["events"])
            semantic_atoms.extend(_validate_llm_atoms(payload.get("semantic_atoms"), turn_id, target))
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
                [],
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
    return EventExtraction(turns, _dedupe_events(events), successful, model_name, warnings, semantic_atoms)


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
        demands=[signal_label(event) for event in events if event.event_family in {"ACTION_REQUEST", "MONEY_MOVEMENT"}],
        manipulation_tactics=[signal_label(event) for event in events if event.event_family == "PSY_STRATEGY"],
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
        demands=[label for label in dict.fromkeys(labels) if any(token in label for token in ("요구", "송금", "정보"))],
        manipulation_tactics=[label for label in dict.fromkeys(labels) if any(token in label for token in ("압박", "불안", "알림 제한"))],
        recommended_next_steps=["송금과 정보 제공을 중단하고 공식 채널로 사실관계를 확인하세요."],
        confidence=0.9 if labels else 0.65,
    )


def _normalize_feature_narrative_code(value: str) -> str:
    normalized = value.strip().upper()
    if normalized.startswith("CLAIMED_ROLE:"):
        return f"ROLE_{normalized.split(':', 1)[1]}"
    if normalized.startswith("REQUEST:"):
        return f"REQUEST_{normalized.split(':', 1)[1]}"
    if normalized in {"URGENCY", "FEAR", "ISOLATION"}:
        return f"TACTIC_{normalized}"
    if normalized == "AUTH_INFO" or normalized == "SENSITIVE_INFO":
        return "REQUEST_AUTH_INFO"
    if normalized == "TRANSFER":
        return "REQUEST_TRANSFER"
    if normalized == "CLAIMS_ORGANIZATION":
        return "CLAIMED_ORGANIZATION"
    if normalized == "OPEN_URL":
        return "REQUEST_OPEN_URL"
    if normalized == "INSTALL_APP":
        return "REQUEST_INSTALL_APP"
    return normalized


def _validated_feature_narratives(context: ContextResult, payload: dict[str, Any]) -> ContextResult:
    """Keep only grounded, known narrative references from the LLM response."""
    valid_turns: set[int] = set()
    valid_atom_ids: set[str] = set()
    atoms_by_id: dict[str, dict[str, Any]] = {}
    observed_codes: set[str] = set()
    feature_payload = payload.get("case_context_features") or {}
    for observation in feature_payload.get("observations", []):
        if not isinstance(observation, dict):
            continue
        code = _normalize_feature_narrative_code(str(observation.get("code") or ""))
        if code:
            observed_codes.add(code)
        try:
            valid_turns.add(int(observation.get("turn")))
        except (TypeError, ValueError):
            pass
    for key in (
        "claimed_actor_types", "claim_codes", "requested_action_codes",
        "manipulation_tactic_codes", "exposure_risk_codes",
    ):
        observed_codes.update(
            code for code in (_normalize_feature_narrative_code(str(item)) for item in feature_payload.get(key, []))
            if code
        )
    for signal in payload.get("signals", []):
        if isinstance(signal, dict):
            try:
                valid_turns.add(int(signal.get("turn")))
            except (TypeError, ValueError):
                pass
    for atom in payload.get("semantic_atoms", []):
        if isinstance(atom, dict):
            atom_id = str(atom.get("atom_id") or "").strip()
            if atom_id:
                valid_atom_ids.add(atom_id)
                atoms_by_id[atom_id] = atom
            try:
                valid_turns.add(int(atom.get("source_turn_id")))
            except (TypeError, ValueError):
                pass

    validated: list[ContextNarrative] = []
    seen: set[tuple[str, str, tuple[int, ...], tuple[str, ...]]] = set()
    for narrative in context.feature_narratives[:40]:
        code = _normalize_feature_narrative_code(narrative.code)
        sentence = " ".join(narrative.sentence.split())[:320]
        if code not in _FEATURE_NARRATIVE_CODES or not sentence:
            continue
        source_turns = sorted({turn for turn in narrative.source_turns if turn in valid_turns})
        atom_ids = list(dict.fromkeys(atom_id for atom_id in narrative.atom_ids if atom_id in valid_atom_ids))
        if not source_turns and not atom_ids and observed_codes and code not in observed_codes:
            continue
        referenced_atoms = [atoms_by_id[atom_id] for atom_id in atom_ids]
        def authoritative_role(field: str, fallback: str = "UNKNOWN") -> str:
            values = [str(atom.get(field) or "").upper() for atom in referenced_atoms]
            values = ["SUSPECTED_PARTY" if value == "CALLER" else value for value in values if value]
            return values[0] if values and all(value == values[0] for value in values) else fallback
        speaker_role = authoritative_role("speaker_role", authoritative_role("speaker"))
        actor_role = authoritative_role("actor_role")
        target_role = authoritative_role("target_role")
        reported_by_role = authoritative_role("reported_by_role", speaker_role)
        if actor_role == "UNKNOWN" and code.startswith(("ROLE_", "CLAIM_", "CLAIMED_", "REQUEST_", "PURPOSE_", "TACTIC_", "DEADLINE_")):
            actor_role = "SUSPECTED_PARTY"
        if target_role == "UNKNOWN" and actor_role == "SUSPECTED_PARTY":
            target_role = "CUSTOMER"
        if code.startswith("CUSTOMER_"):
            actor_role = "CUSTOMER"
            reported_by_role = "CUSTOMER"

        entity_names = list(dict.fromkeys(
            str(value).strip()
            for atom in referenced_atoms
            for value in (
                atom.get("claimed_organization_name"), atom.get("claimed_branch_name"),
                atom.get("claimed_person_name"), atom.get("claimed_role_name"), atom.get("claimed_role"),
                atom.get("claimed_relationship"), atom.get("vocative_target"),
            )
            if value and str(value).strip()
        ))[:20]
        detail_items = list(dict.fromkeys(
            str(term.get("semantic_value") or term.get("surface_form") or "").strip()
            for atom in referenced_atoms for term in atom.get("observed_terms", [])
            if isinstance(term, dict) and str(term.get("semantic_value") or term.get("surface_form") or "").strip()
        ))[:20]
        deadlines = [str(atom.get("deadline_at")) for atom in referenced_atoms if atom.get("deadline_at")]
        relative_deadlines = [int(atom["relative_deadline_minutes"]) for atom in referenced_atoms if atom.get("relative_deadline_minutes") is not None]
        occurrence_count = max([int(atom.get("occurrence_count") or 1) for atom in referenced_atoms] or [1])
        confidences = [float(atom["attribution_confidence"]) for atom in referenced_atoms if atom.get("attribution_confidence") is not None]
        sentence = sentence.replace("상대방", "보이스피싱 의심 인물")
        if actor_role == "SUSPECTED_PARTY" and sentence.startswith("고객이 ") and not code.startswith("CUSTOMER_"):
            sentence = "보이스피싱 의심 인물이 " + sentence.removeprefix("고객이 ")
        if code.startswith("CUSTOMER_") and any(
            token in sentence for token in ("송금했다고", "이체했다고", "설치했다고", "제공했다고")
        ) and "은행 내부 채널" not in sentence:
            sentence = sentence.rstrip(". ") + ". 실제 완료 여부는 은행 내부 채널에서 별도 확인 필요"
        key = (code, sentence.casefold(), tuple(source_turns), tuple(atom_ids))
        if key in seen:
            continue
        seen.add(key)
        validated.append(narrative.model_copy(update={
            "code": code,
            "sentence": sentence,
            "source_turns": source_turns,
            "atom_ids": atom_ids,
            "speaker_role": speaker_role,
            "actor_role": actor_role,
            "target_role": target_role,
            "reported_by_role": reported_by_role,
            "detail_items": detail_items,
            "entity_names": entity_names,
            "deadline_at": deadlines[0] if deadlines else None,
            "relative_deadline_minutes": min(relative_deadlines) if relative_deadlines else None,
            "occurrence_count": occurrence_count,
            "confidence": min(confidences) if confidences else None,
        }))
    def suspected_party_lines(items: list[str]) -> list[str]:
        normalized: list[str] = []
        for item in items:
            line = " ".join(item.split()).replace("상대방", "보이스피싱 의심 인물")
            if line.startswith("고객이 "):
                line = "보이스피싱 의심 인물이 " + line.removeprefix("고객이 ")
            if line and line not in normalized:
                normalized.append(line)
        return normalized

    customer_statements: list[str] = []
    for item in context.customer_statements:
        line = " ".join(item.split()).replace("상대방", "보이스피싱 의심 인물")
        if line.startswith("고객이 ") and "주장을 전달" in line:
            continue
        if any(token in line for token in ("송금했다고", "이체했다고", "설치했다고", "제공했다고")) \
                and "은행 내부 채널" not in line:
            line = line.rstrip(". ") + ". 실제 완료 여부는 은행 내부 채널에서 별도 확인 필요"
        if line and line not in customer_statements:
            customer_statements.append(line)

    return context.model_copy(update={
        "summary": context.summary.replace("상대방", "보이스피싱 의심 인물"),
        "claims": suspected_party_lines(context.claims),
        "demands": suspected_party_lines(context.demands),
        "manipulation_tactics": suspected_party_lines(context.manipulation_tactics),
        "customer_statements": customer_statements,
        "feature_narratives": validated,
    })


CONTEXT_OUTPUT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "summary": {"type": "string"}, "incident_type": {"type": "string"},
        "claims": {"type": "array", "items": {"type": "string"}},
        "demands": {"type": "array", "items": {"type": "string"}},
        "manipulation_tactics": {"type": "array", "items": {"type": "string"}},
        "customer_statements": {"type": "array", "items": {"type": "string"}},
        "recommended_next_steps": {"type": "array", "items": {"type": "string"}},
        "feature_narratives": {
            "type": "array", "maxItems": 40,
            "items": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "code": {"type": "string", "maxLength": 80},
                    "sentence": {"type": "string", "minLength": 1, "maxLength": 320},
                    "status": {"type": "string", "enum": ["CLAIMED", "REQUESTED", "REPORTED", "DENIED"]},
                    "source_turns": {"type": "array", "maxItems": 12, "items": {"type": "integer", "minimum": 1}},
                    "atom_ids": {"type": "array", "maxItems": 20, "items": {"type": "string", "maxLength": 100}},
                    "speaker_role": {"type": "string", "enum": ["SUSPECTED_PARTY", "CUSTOMER", "BANK_STAFF", "SYSTEM", "UNKNOWN"]},
                    "actor_role": {"type": "string", "enum": ["SUSPECTED_PARTY", "CUSTOMER", "BANK_STAFF", "SYSTEM", "UNKNOWN"]},
                    "target_role": {"type": "string", "enum": ["SUSPECTED_PARTY", "CUSTOMER", "BANK_STAFF", "SYSTEM", "UNKNOWN"]},
                    "reported_by_role": {"type": "string", "enum": ["SUSPECTED_PARTY", "CUSTOMER", "BANK_STAFF", "SYSTEM", "UNKNOWN"]},
                    "detail_items": {"type": "array", "maxItems": 20, "items": {"type": "string", "maxLength": 160}},
                    "entity_names": {"type": "array", "maxItems": 20, "items": {"type": "string", "maxLength": 160}},
                    "deadline_at": {"type": ["string", "null"], "maxLength": 64},
                    "relative_deadline_minutes": {"type": ["integer", "null"], "minimum": 0},
                    "occurrence_count": {"type": "integer", "minimum": 1},
                    "confidence": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
                },
                "required": ["code", "sentence", "status", "source_turns", "atom_ids", "speaker_role", "actor_role", "target_role", "reported_by_role", "detail_items", "entity_names", "deadline_at", "relative_deadline_minutes", "occurrence_count", "confidence"],
            },
        },
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["summary", "incident_type", "claims", "demands", "manipulation_tactics", "customer_statements", "recommended_next_steps", "feature_narratives", "confidence"],
}


async def extract_full_context(text: str) -> ContextResult:
    """전체 맥락을 구조화하되 보이스피싱 최종 판정이나 금융조치를 확정하지 않는다."""
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY가 없습니다.")
    budget = active_diagnosis_budget()
    budget.validate_input(text=text, turn_count=len(parse_turns(text)))
    max_output_tokens = int(os.getenv("OPENAI_CONTEXT_MAX_OUTPUT_TOKENS", "2400"))
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
    max_output_tokens = int(os.getenv("OPENAI_CONTEXT_MAX_OUTPUT_TOKENS", "2400"))
    reservation = budget.reserve(input_text=input_text, max_output_tokens=max_output_tokens)
    client = AsyncOpenAI(
        api_key=os.environ["OPENAI_API_KEY"], timeout=_openai_timeout_seconds(),
    )
    response = await client.responses.create(
        model=os.getenv("OPENAI_CONTEXT_MODEL", os.getenv("OPENAI_EVENT_MODEL", "gpt-4o-mini")),
        instructions=(
            "You receive only structured anti-fraud signals, never a call transcript. "
            "Treat speaker_role, actor_role, target_role, reported_by_role and their confidence "
            "as authoritative metadata. Never change a CUSTOMER reporter into the actor of a "
            "claim or request. SUSPECTED_PARTY must be rendered as '보이스피싱 의심 인물'; "
            "do not use the vague label '상대방' and do not call anyone a confirmed criminal. "
            "A vocative such as '엄마' is the addressee, not the speaker. When claimed_relationship "
            "is CHILD, describe that the suspected person impersonated the customer's child. "
            "Write a grounded Korean case summary using every useful structured detail available. "
            "Preserve exact organization, branch, institution, person, role, relationship, amount, "
            "deadline, remaining-time, order and frequency values; never replace a concrete name "
            "such as 서울지검 or an exact bank/police-station name with a generic institution label. "
            "For impersonation use wording like '보이스피싱 의심 인물이 서울지검 수사관을 "
            "사칭한 정황이 확인됨'. For unverified claims use '...라고 주장함'; for directives "
            "use '...을 요구함'. For a customer-reported completed action use wording like "
            "'고객이 송금했다고 진술함. 실제 거래 완료 여부는 은행 내부 채널에서 별도 "
            "확인 필요'. Never emit the unhelpful sentence '고객이 상대방의 주장을 전달함'. "
            "If deadline_at is 15:00 and relative_deadline_minutes is 120, state both the deadline "
            "and that about two hours remained. Distinguish claims from verified facts and "
            "separately describe claims, requested actions, pressure tactics, and customer actions. "
            "Use plain Korean for every user-facing string including incident_type; keep schema "
            "keys unchanged. Recommend safe next checks without inventing names, account numbers, "
            "quoted utterances, missing actors, or a final financial decision. "
            "Also create feature_narratives for as many distinct observed signals as possible, "
            "up to 40 items. Keep different actions, claims, pressure tactics, customer actions, "
            "amounts, roles, and time references as separate items rather than collapsing them. "
            "Each sentence must be detailed but no longer than 320 Korean characters, and must "
            "clearly distinguish a claim, request, or customer report from a verified fact. "
            "The code must be one of the known feature codes represented in the payload. "
            "source_turns may contain only payload turn numbers and atom_ids may contain only "
            "payload atom IDs. If a signal is not grounded in the payload, omit it. "
            "Populate role metadata, detail_items, entity_names, deadline fields, occurrence_count "
            "and confidence from the referenced atoms only. Do not repeat the same sentence for "
            "the same evidence."
        ),
        input=input_text,
        max_output_tokens=max_output_tokens,
        text={"format": {"type": "json_schema", "name": "diagnosis_signal_context_v1", "schema": CONTEXT_OUTPUT_SCHEMA, "strict": True}},
    )
    budget.settle(reservation, response)
    context = ContextResult.model_validate_json(response.output_text)
    return _validated_feature_narratives(context, payload)
