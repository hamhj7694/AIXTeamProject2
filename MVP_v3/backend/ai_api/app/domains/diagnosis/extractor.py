from __future__ import annotations

import json
import hashlib
import os
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from openai import APIConnectionError, AsyncOpenAI, AuthenticationError, RateLimitError

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


def _openai_max_retries() -> int:
    """Retry transient provider failures, but never synthesize a diagnosis."""
    try:
        retries = int(os.getenv("OPENAI_MAX_RETRIES", "2"))
    except ValueError:
        retries = 2
    return max(0, min(retries, 5))


def parse_turns(text: str) -> list[str]:
    turns: list[str] = []
    for line in str(text).splitlines():
        parts = re.split(r"(?<=[.!?。！？])\s*", line.strip())
        turns.extend(part.strip() for part in parts if part.strip())
    return turns


def _speaker_hint(turn: str) -> str:
    """Read an optional demo speaker prefix without treating honorifics as speakers.

    The production path receives speaker roles in the Analysis Envelope.  The
    demo adapter may receive a labelled transcript, so pass that label to the
    extraction model as metadata.  An unlabeled turn is marked UNKNOWN here;
    the model receives the surrounding conversation and may infer its speaker
    when the dialogue provides enough evidence.
    """
    match = re.match(r"^\s*(?:\[\s*)?(고객|피해자|소비자|CUSTOMER)\s*(?:\]|:|：)", turn, re.IGNORECASE)
    if match:
        return "CUSTOMER"
    match = re.match(
        r"^\s*(?:\[\s*)?(보이스피싱\s*의심\s*인물|의심\s*인물|상대방|발신자|사칭자|CALLER|SUSPECTED_PARTY)\s*(?:\]|:|：)",
        turn,
        re.IGNORECASE,
    )
    if match:
        return "SUSPECTED_PARTY"
    match = re.match(r"^\s*(?:\[\s*)?(은행\s*담당자|은행직원|BANK_STAFF)\s*(?:\]|:|：)", turn, re.IGNORECASE)
    if match:
        return "BANK_STAFF"
    return "UNKNOWN"


_DEMO_SUSPECTED_CUES = (
    "보내 줘", "보내줘", "이체해 줘", "이체해줘", "말해 줘", "말해줘",
    "불러 주세요", "불러주세요", "따라 주세요", "따라주세요", "묻지 말고",
    "문자로만", "은행에 문의하면", "다른 사람에게", "인증번호", "안전계좌",
    "인증서", "급하게 결제", "결제해야", "환불 전용 계좌", "보안센터", "카드사", "검찰", "경찰",
)
_DEMO_CUSTOMER_CUES = (
    "확인하고 싶", "확인해 보", "확인해보", "알겠습니다", "말하면 결제",
    "어떤 결제인지", "아직 보내지", "송금하지 않았", "설명해 주세요",
)


def _infer_unlabeled_demo_role(turn: str, turns: list[str]) -> tuple[str, float] | None:
    """Infer a low-confidence role for an unlabeled demo turn.

    This is a conservative safety net for the demo adapter only. Explicit
    speaker metadata and model-provided roles always win; the result is marked
    as an inference through its lower confidence rather than presented as fact.
    """
    if _speaker_hint(turn) != "UNKNOWN":
        return None
    compact = re.sub(r"\s+", "", turn)
    conversation = re.sub(r"\s+", "", " ".join(turns))
    scam_context = any(cue.replace(" ", "") in conversation for cue in _DEMO_SUSPECTED_CUES)
    customer_signal = any(cue.replace(" ", "") in compact for cue in _DEMO_CUSTOMER_CUES)
    question_signal = "?" in turn or turn.rstrip().endswith(("까요", "나요", "습니까"))
    suspected_signal = any(cue.replace(" ", "") in compact for cue in _DEMO_SUSPECTED_CUES)
    family_claim_signal = any(token in compact for token in ("엄마", "아빠", "휴대폰이고장", "임시번호"))

    if customer_signal or question_signal:
        return "CUSTOMER", 0.58
    if suspected_signal or (scam_context and family_claim_signal):
        return "SUSPECTED_PARTY", 0.58
    return None


def _apply_demo_speaker_guess(
    atoms: list[SemanticAtom], role: str, confidence: float,
) -> list[SemanticAtom]:
    """Fill only missing role metadata with a clearly low-confidence guess."""
    updated: list[SemanticAtom] = []
    for atom in atoms:
        changes: dict[str, object] = {}
        if atom.speaker_role in {None, "UNKNOWN"}:
            changes["speaker_role"] = role
            changes["speaker_confidence"] = min(atom.speaker_confidence or confidence, confidence)
            changes["attribution_confidence"] = min(atom.attribution_confidence or confidence, confidence)
        if role == "SUSPECTED_PARTY":
            if atom.actor_role in {None, "UNKNOWN"} and (
                atom.claim_status == "CALLER_CLAIM"
                or atom.action_state in {"REQUESTED", "INSTRUCTED"}
                or atom.atom_class in {"IDENTITY_CLAIM", "ORGANIZATION_CLAIM", "ROLE_CLAIM", "ACTION_REQUEST", "ACTION_INSTRUCTION", "PROHIBITION", "SECRECY_REQUEST", "COMMUNICATION_CONTROL", "FINANCIAL_ACTION"}
            ):
                changes["actor_role"] = role
            if atom.target_role in {None, "UNKNOWN"}:
                changes["target_role"] = "CUSTOMER"
            if atom.reported_by_role in {None, "UNKNOWN"}:
                changes["reported_by_role"] = role
        elif role == "CUSTOMER":
            if atom.reported_by_role in {None, "UNKNOWN"}:
                changes["reported_by_role"] = role
            if atom.action_state in {"REPORTED_ACTION", "COMPLETED", "DENIED"} and atom.actor_role in {None, "UNKNOWN"}:
                changes["actor_role"] = role
        updated.append(atom.model_copy(update=changes) if changes else atom)
    return updated


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
        if (
            any(token in compact for token in ("엄마", "아빠", "어머니", "아버지"))
            and any(token in compact for token in ("휴대폰이고장", "스마트폰이고장", "임시번호", "새번호로연락"))
        ):
            add(turn_id, target, "IMPERSONATION", "FAMILY", "FAMILY")
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
    model_name = os.getenv("OPENAI_EVENT_MODEL", "gpt-5.6-luna")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않아 실제 LLM 분석을 시작할 수 없습니다.")

    client = AsyncOpenAI(
        api_key=os.environ["OPENAI_API_KEY"], timeout=_openai_timeout_seconds(),
        max_retries=_openai_max_retries(),
    )
    events: list[ExtractedEvent] = []
    successful: list[int] = []
    semantic_atoms: list[SemanticAtom] = []
    max_output_tokens = int(os.getenv("OPENAI_EVENT_MAX_OUTPUT_TOKENS", "1800"))
    for turn_id, target in enumerate(turns, start=1):
        # Keep attribution context local to the target turn so a long demo
        # input does not multiply the full transcript into every model call.
        context_start = max(0, turn_id - 4)
        context_end = min(len(turns), turn_id + 3)
        conversation_context = "\n".join(
            f"[TURN {index}] {turns[index - 1]}"
            for index in range(context_start + 1, context_end + 1)
        )
        speaker_hint = _speaker_hint(target)
        speaker_marker = "UNLABELED" if speaker_hint == "UNKNOWN" else speaker_hint
        reservation = budget.reserve(
            input_text=(
                f"{SYSTEM_INSTRUCTION}\n[CONVERSATION_CONTEXT]\n"
                f"{conversation_context}\n[TARGET][TURN {turn_id}] {target}"
            ),
            max_output_tokens=max_output_tokens,
        )
        try:
            response = await client.responses.create(
                model=model_name,
                instructions=f"{SYSTEM_INSTRUCTION}\n\n{SEMANTIC_ATOM_INSTRUCTION}",
                input=(
                    "[CONVERSATION_CONTEXT]\n"
                    f"{conversation_context}\n\n"
                    f"[TARGET][TURN {turn_id}][SPEAKER_{speaker_marker}] {target}"
                ),
                max_output_tokens=max_output_tokens,
                text={"format": {"type": "json_schema", "name": "voice_phishing_events_v2_2", "schema": EVENT_OUTPUT_SCHEMA, "strict": True}},
            )
            budget.settle(reservation, response)
            payload = json.loads(response.output_text)
            events.extend(_validate_event(raw, turn_id, target) for raw in payload["events"])
            turn_atoms = _validate_llm_atoms(payload.get("semantic_atoms"), turn_id, target)
            inferred_role = _infer_unlabeled_demo_role(target, turns)
            if inferred_role:
                turn_atoms = _apply_demo_speaker_guess(turn_atoms, *inferred_role)
            semantic_atoms.extend(turn_atoms)
            successful.append(turn_id)
        except Exception as exc:
            if isinstance(exc, RateLimitError):
                raise AiProviderQuotaError("OpenAI API 크레딧 또는 호출 한도가 부족합니다. 결제·사용 한도를 확인한 뒤 다시 시도해 주세요.") from exc
            if isinstance(exc, AuthenticationError):
                raise AiProviderAuthenticationError("OpenAI API 키를 확인해 주세요.") from exc
            if isinstance(exc, APIConnectionError):
                raise
            # A diagnosis with even one unprocessed turn is not complete.
            # Convert malformed provider output to a server-side failure rather
            # than allowing it to become a client-input error or fallback Case.
            raise RuntimeError("AI 이벤트 추출 결과를 완성하지 못했습니다.") from exc
    # Family/device-broken calls are frequently supplied without speaker
    # labels. Keep a deterministic, privacy-safe family impersonation cue when
    # the event model misses the cue, so the downstream narrative has a grounded
    # suspected-party path instead of falling back to a customer report.
    family_safety_events = [
        event for event in _local_safety_events(turns)
        if event.event_family == "IMPERSONATION" and event.impersonation_group == "FAMILY"
    ]
    return EventExtraction(
        turns, _dedupe_events([*events, *family_safety_events]), successful, model_name,
        semantic_atoms=semantic_atoms,
    )


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


def _format_fallback_amount(value: Any) -> str | None:
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return None
    if amount <= 0:
        return None
    if amount.is_integer() and amount >= 10_000:
        value = int(amount)
        man, remainder = divmod(value, 10_000)
        if remainder == 0:
            return f"{man:,}만 원"
    return f"{int(amount):,}원" if amount.is_integer() else f"{amount:,.0f}원"


def _fallback_actor(atom: dict[str, Any]) -> str:
    actor_role = str(atom.get("actor_role") or "").upper()
    reported_by_role = str(atom.get("reported_by_role") or "").upper()
    if actor_role == "CUSTOMER" or reported_by_role == "CUSTOMER":
        return "고객"
    return "보이스피싱 의심 인물"


def _fallback_claim_subject(atom: dict[str, Any]) -> str:
    relationship = str(atom.get("claimed_relationship") or "").upper()
    if relationship in {"CHILD", "FAMILY_MEMBER", "SON", "DAUGHTER"}:
        return "고객의 자녀"
    return str(
        atom.get("claimed_person_name")
        or atom.get("claimed_role_name")
        or atom.get("claimed_role")
        or atom.get("claimed_relationship")
        or "특정 인물·기관"
    )


def _fallback_atom_sentence(atom: dict[str, Any]) -> tuple[str, str]:
    """Render a grounded, privacy-safe sentence for provider-offline fallback.

    This intentionally consumes only normalized semantic atoms. It must not use
    evidence_text, source utterances, or any newly inferred account/person data.
    The returned category is used to populate the same context buckets as the
    context LLM (claim, demand, customer, or tactic).
    """
    predicate = str(atom.get("predicate") or "OTHER").upper()
    actor = _fallback_actor(atom)
    amount = _format_fallback_amount(atom.get("amount_value_krw"))
    destination = str(atom.get("destination") or "").upper()
    action_state = str(atom.get("action_state") or "").upper()
    customer_action = actor == "고객"

    if predicate in {"CLAIMS_IDENTITY", "CLAIMS_ROLE", "CLAIMS_ORGANIZATION", "CLAIMS_ACCOUNT_INVOLVEMENT", "CLAIMS_CRIME_INVOLVEMENT"}:
        subject = _fallback_claim_subject(atom)
        if predicate == "CLAIMS_CRIME_INVOLVEMENT":
            return f"{actor}가 고객 계좌·명의가 범죄에 연루됐다고 주장함.", "claim"
        if predicate == "CLAIMS_ACCOUNT_INVOLVEMENT":
            return f"{actor}가 고객 계좌와 관련된 문제가 있다고 주장함.", "claim"
        particle = "라고" if subject.endswith(("자녀", "아들", "딸")) else "이라고"
        return f"{actor}가 {subject}{particle} 주장함.", "claim"

    if predicate == "TRANSFER_FUNDS":
        if customer_action:
            if action_state in {"COMPLETED", "REPORTED_ACTION"}:
                suffix = " 실제 거래 완료 여부는 은행 내부 채널에서 별도 확인 필요."
                return f"고객이 {amount + '을 ' if amount else ''}송금했다고 진술함.{suffix}", "customer"
            if action_state == "DENIED":
                return f"고객이 {amount + '을 ' if amount else ''}송금하지 않았다고 진술함.", "customer"
            if action_state in {"PLANNED", "ATTEMPTED"}:
                return f"고객이 {amount + '을 ' if amount else ''}송금할 계획이라고 진술함.", "customer"
        destination_text = "외부 계좌로 " if destination in {"EXTERNAL_ACCOUNT", "CLAIMED_SAFE_ACCOUNT"} else ""
        amount_text = f"{amount}을 " if amount else ""
        return f"보이스피싱 의심 인물이 고객에게 {destination_text}{amount_text}이체하라고 요구함.", "demand"

    if predicate == "MAINTAIN_CALL":
        if customer_action:
            return "고객이 통화를 계속 유지했다고 진술함.", "customer"
        return "보이스피싱 의심 인물이 고객에게 통화를 계속 유지하라고 요구함.", "demand"
    if predicate == "KEEP_SECRET":
        return "고객에게 관련 내용을 비밀로 하라고 요구함.", "demand"
    if predicate == "AVOID_EXTERNAL_CONTACT":
        return "고객에게 은행 등 외부 기관에 연락하지 말라고 요구함.", "demand"
    if predicate == "AVOID_REPORTING":
        return "고객에게 관련 내용을 은행이나 관계 기관에 알리지 말라고 요구함.", "demand"
    if predicate in {"THREATEN_ARREST", "THREATEN_ASSET_FREEZE"}:
        return "보이스피싱 의심 인물이 처벌이나 재산상 피해가 발생할 수 있다는 불안을 조성함.", "tactic"
    if predicate == "PROMISE_RETURN":
        return "보이스피싱 의심 인물이 송금하면 돈을 돌려주겠다고 주장함. 해당 반환 약속은 확인되지 않은 주장임.", "claim"

    communication_control = str(atom.get("communication_control") or "").upper()
    if communication_control in {"NO_END_CALL", "NO_EXTERNAL_CONTACT", "NO_BANK_CONTACT", "NO_REPORTING", "KEEP_SECRET"}:
        return "보이스피싱 의심 인물이 고객의 외부 연락이나 사실 확인을 제한한 정황이 확인됨.", "tactic"
    if str(atom.get("urgency") or "").upper() in {"TODAY", "IMMEDIATE", "WITHIN_30_MINUTES", "BEFORE_CALL_END"}:
        return "보이스피싱 의심 인물이 고객에게 즉시 또는 오늘 안에 처리하라고 재촉한 정황이 확인됨.", "demand"
    return "구조화 분석에서 추가 정황이 확인되었으며 세부 사실은 담당자 확인이 필요함.", "tactic"


def _fallback_incident_type(payload: dict[str, Any], labels: list[str]) -> str:
    signals = [item for item in payload.get("signals", []) if isinstance(item, dict)]
    groups = {str(item.get("impersonation_group") or "").upper() for item in signals}
    context_features = payload.get("case_context_features") or {}
    groups.update(str(item).upper() for item in context_features.get("claimed_actor_types", []) if item)
    requested = {str(item).upper() for item in context_features.get("requested_action_codes", []) if item}
    label_text = " ".join(labels)
    has_transfer = any("TRANSFER" in item for item in requested) or "송금" in label_text or "이체" in label_text
    has_auth = any("AUTH" in item for item in requested) or "인증" in label_text
    if "FAMILY" in groups:
        return "가족 사칭 및 송금 유도 의심" if has_transfer else "가족 사칭 의심"
    if "PUBLIC_AGENCY" in groups:
        return "공공기관 사칭 및 송금 요구 의심" if has_transfer else "공공기관 사칭 의심"
    if "FINANCIAL_INSTITUTION" in groups:
        return "금융기관 사칭 및 송금 요구 의심" if has_transfer else "금융기관 사칭 의심"
    if has_auth:
        return "인증정보 요구 의심"
    if has_transfer:
        return "송금·이체 요구 의심"
    if "긴급" in label_text or "압박" in label_text:
        return "긴급 처리 압박 의심"
    return "보이스피싱 의심" if labels else "유형 확인 필요"


def _fallback_context_from_atoms(payload: dict[str, Any], labels: list[str]) -> ContextResult:
    atoms = [item for item in payload.get("semantic_atoms", []) if isinstance(item, dict)]
    narratives: list[ContextNarrative] = []
    claims: list[str] = []
    demands: list[str] = []
    customer_statements: list[str] = []
    tactics: list[str] = []

    for index, atom in enumerate(atoms):
        sentence, category = _fallback_atom_sentence(atom)
        if sentence in {item.sentence for item in narratives}:
            continue
        predicate = str(atom.get("predicate") or "EXTRACTED_CONTEXT").upper()
        code = {
            "CLAIMS_IDENTITY": "CLAIMED_ORGANIZATION",
            "CLAIMS_ORGANIZATION": "CLAIMED_ORGANIZATION",
            "CLAIMS_ROLE": "ROLE_FAMILY" if str(atom.get("claimed_relationship") or "").upper() in {"CHILD", "FAMILY_MEMBER"} else "CLAIMED_ORGANIZATION",
            "TRANSFER_FUNDS": "CUSTOMER_TRANSFERRED" if category == "customer" else "REQUEST_TRANSFER",
            "MAINTAIN_CALL": "REQUEST_KEEP_CALL",
            "KEEP_SECRET": "REQUEST_SECRECY",
            "AVOID_EXTERNAL_CONTACT": "TACTIC_ISOLATION",
            "AVOID_REPORTING": "TACTIC_ISOLATION",
            "THREATEN_ARREST": "TACTIC_FEAR",
            "THREATEN_ASSET_FREEZE": "TACTIC_FEAR",
            "PROMISE_RETURN": "PURPOSE_REFUND",
        }.get(predicate, "EXTRACTED_CONTEXT")
        status = "REPORTED" if category == "customer" else "REQUESTED" if category == "demand" else "CLAIMED"
        narrative = ContextNarrative(
            code=code,
            sentence=sentence,
            status=status,
            source_turns=[int(atom["source_turn_id"])] if atom.get("source_turn_id") else [],
            atom_ids=[str(atom["atom_id"])] if atom.get("atom_id") else [],
            speaker_role=str(atom.get("speaker_role") or "UNKNOWN"),
            actor_role=str(atom.get("actor_role") or "UNKNOWN"),
            target_role=str(atom.get("target_role") or "UNKNOWN"),
            reported_by_role=str(atom.get("reported_by_role") or "UNKNOWN"),
            detail_items=[str(item) for item in atom.get("lexical_cues", []) if item],
            entity_names=[str(item) for item in (
                atom.get("claimed_organization_name"), atom.get("claimed_role_name"),
                atom.get("claimed_relationship"), atom.get("claimed_person_name"),
            ) if item],
            deadline_at=atom.get("deadline_at"),
            relative_deadline_minutes=atom.get("relative_deadline_minutes"),
            occurrence_count=int(atom.get("occurrence_count") or 1),
            confidence=float(atom.get("attribution_confidence") or 0.65),
        )
        narratives.append(narrative)
        if category == "claim":
            claims.append(sentence)
        elif category == "demand":
            demands.append(sentence)
        elif category == "customer":
            customer_statements.append(sentence)
        else:
            tactics.append(sentence)

    if not narratives:
        claims = [label for label in dict.fromkeys(labels) if "사칭" in label]
        demands = [label for label in dict.fromkeys(labels) if any(token in label for token in ("요구", "송금", "정보"))]

    predicates = {str(item.get("predicate") or "").upper() for item in atoms}
    has_transfer = "TRANSFER_FUNDS" in predicates or any("송금" in label or "이체" in label for label in labels)
    has_sensitive = bool(predicates & {"DISCLOSE_OTP", "DISCLOSE_PASSWORD", "PROVIDE_CARD_INFO", "INSTALL_APP", "OPEN_URL", "SHARE_SCREEN"})
    recommended = [
        "고객의 현재 통화를 안전하게 종료하고, 보이스피싱 의심 인물이 제공한 연락처가 아닌 은행 공식 채널로 즉시 거래 및 사고 여부를 확인함.",
    ]
    if has_transfer:
        recommended.append("고객이 송금했다고 진술한 금액의 실제 이체 완료 여부, 처리 시각, 상대 계좌 정보와 지급정지 가능성을 은행 내부 절차로 확인함.")
    if has_sensitive:
        recommended.append("추가 송금, 인증서·비밀번호 제공, 원격제어 앱 설치가 없었는지 확인하고 관련 정보가 노출됐다면 은행의 공식 보안 절차를 진행함.")
    recommended.extend([
        "통화기록, 문자, 계좌 이체 화면 등 관련 자료를 보존하고 필요 시 공식 수사기관 또는 금융기관 신고 절차를 안내함.",
        "확인되지 않은 반환 약속이나 안전계좌라는 취지의 설명은 검증 전 사실로 취급하지 않음.",
    ])
    summary_parts = [item.sentence for item in narratives[:12]]
    summary = " ".join(summary_parts) if summary_parts else (
        "위험 신호가 감지되지 않았습니다." if not labels else f"{', '.join(dict.fromkeys(labels))} 정황이 확인되어 추가 검증이 필요함."
    )
    return ContextResult(
        summary=summary,
        incident_type=_fallback_incident_type(payload, labels) if labels or narratives else "유형 확인 필요",
        claims=list(dict.fromkeys(claims)),
        demands=list(dict.fromkeys(demands)),
        manipulation_tactics=list(dict.fromkeys(tactics)),
        customer_statements=list(dict.fromkeys(customer_statements)),
        recommended_next_steps=list(dict.fromkeys(recommended)),
        feature_narratives=narratives[:40],
        confidence=0.9 if labels or narratives else 0.65,
    )


def build_context_from_signal_payload(payload: dict[str, Any]) -> ContextResult:
    """Build a safe context from real structured signals if the LLM is unavailable."""
    signals = payload.get("signals", [])
    labels = [str(item.get("signal", "")) for item in signals if isinstance(item, dict)]
    atom_context = _fallback_context_from_atoms(payload, labels)
    if atom_context.feature_narratives:
        return atom_context
    incident_type = _fallback_incident_type(payload, labels)
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


_SUSPECTED_FEATURE_PREFIXES = (
    "ROLE_", "CLAIM_", "CLAIMED_", "REQUEST_", "PURPOSE_", "TACTIC_", "DEADLINE_",
)


def _is_suspected_feature_code(code: str) -> bool:
    return code.startswith(_SUSPECTED_FEATURE_PREFIXES)


def _entity_display_name(values: list[str]) -> str:
    labels = {
        "CARD_COMPANY": "카드사",
        "BANK": "은행",
        "PROSECUTION_SERVICE": "검찰·수사기관",
        "POLICE_SERVICE": "경찰기관",
        "FINANCIAL_SUPERVISORY_SERVICE": "금융감독원",
        "COURT": "법원",
    }
    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        if normalized in labels:
            return labels[normalized]
        if normalized not in {"UNKNOWN", "CUSTOMER", "CALLER"}:
            return normalized
    return "금융기관"


def _normalize_suspected_sentence(code: str, sentence: str, entity_names: list[str]) -> str:
    """Prevent legacy/customer-report wording for live-call signals.

    The context model receives role metadata, but older envelopes and partially
    populated narratives may omit atom_ids.  Keep a deterministic, grounded
    display guard so a suspected party's utterance cannot be rendered as a
    customer complaint.
    """
    text = " ".join(sentence.split())
    if not text or not _is_suspected_feature_code(code):
        return text
    customer_wording = text.startswith("고객이 ") or "고객이 " in text[:28] or "요청받" in text
    if not customer_wording:
        return text
    institution = _entity_display_name(entity_names)
    if code == "CLAIM_UNAUTHORIZED_PAYMENT":
        return f"보이스피싱 의심 인물이 {institution} 관계자를 사칭하며 승인되지 않은 결제가 발생했다고 주장함."
    if code == "CLAIM_CRIME_INVOLVEMENT":
        return "보이스피싱 의심 인물이 고객 계좌·명의가 범죄에 연루됐다고 주장함."
    if code == "CLAIM_ACCOUNT_VERIFICATION":
        return f"보이스피싱 의심 인물이 {institution} 명의로 고객 계좌 확인이 필요하다고 주장함."
    if code == "REQUEST_AUTH_INFO":
        return "보이스피싱 의심 인물이 고객에게 인증정보 제공을 요구함."
    if code == "REQUEST_INSTALL_APP":
        return "보이스피싱 의심 인물이 고객에게 특정 앱 설치를 요구함."
    if code in {"REQUEST_TRANSFER", "PURPOSE_SAFE_ACCOUNT", "PURPOSE_REFUND"}:
        return "보이스피싱 의심 인물이 고객에게 자금 이체 또는 송금을 요구함."
    if code == "REQUEST_KEEP_CALL":
        return "보이스피싱 의심 인물이 고객에게 통화를 계속 유지하라고 요구함."
    if code == "REQUEST_SECRECY" or code == "TACTIC_ISOLATION":
        return "보이스피싱 의심 인물이 고객에게 외부 연락이나 사실 공유를 제한함."
    if text.startswith("고객이 "):
        return f"보이스피싱 의심 인물이 {text.removeprefix('고객이 ')}"
    return text


_FEATURE_NARRATIVE_LABELS = {
    "ROLE_PROSECUTION": "수사기관 사칭", "ROLE_POLICE": "경찰 사칭",
    "ROLE_BANK": "금융기관 사칭", "ROLE_FAMILY": "가족·지인 사칭",
    "ROLE_SUPPORT": "지원기관 사칭", "CLAIMED_ORGANIZATION": "기관·소속 사칭",
    "CLAIM_CRIME_INVOLVEMENT": "계좌·명의 범죄 연루 주장",
    "CLAIM_ACCOUNT_VERIFICATION": "계좌 확인 필요 주장",
    "CLAIM_DEVICE_BROKEN": "휴대전화 이상 주장",
    "CLAIM_UNAUTHORIZED_PAYMENT": "승인되지 않은 결제 주장",
    "CLAIM_LOAN_APPROVAL": "대출 승인 주장", "REQUEST_TRANSFER": "송금·이체 요구",
    "REQUEST_INSTALL_APP": "앱 설치 요구", "REQUEST_AUTH_INFO": "인증정보 제공 요구",
    "REQUEST_PERSONAL_INFO": "개인정보 제공 요구", "REQUEST_KEEP_CALL": "통화 유지 요구",
    "REQUEST_SECRECY": "외부 연락 제한 요구", "REQUEST_OPEN_URL": "링크·앱 실행 요구",
    "REQUEST_AMOUNT": "금액 요구", "PURPOSE_SAFE_ACCOUNT": "안전계좌 이체 유도",
    "PURPOSE_LOAN_REPAYMENT": "대출 상환 요구", "PURPOSE_REPAIR": "기기·계정 수리 명분",
    "PURPOSE_REFUND": "환급 명분", "DEADLINE_TODAY": "오늘 안 처리 요구",
    "DEADLINE_IMMEDIATE": "즉시 처리 요구", "TACTIC_FEAR": "불안·공포 조성",
    "TACTIC_URGENCY": "긴급 처리 압박", "TACTIC_ISOLATION": "주변 연락 차단",
}


def _unknown_attribution_sentence(code: str, entity_names: list[str]) -> str:
    label = _FEATURE_NARRATIVE_LABELS.get(code, "추가 분석 정황")
    organization = _entity_display_name(entity_names)
    prefix = f"{organization} 관련 " if entity_names and code.startswith(("ROLE_", "CLAIM")) else ""
    return f"{prefix}{label} 정황이 확인되었으나 발화자·행위자 귀속은 확인 필요."


def _demo_inferred_suspected_sentence(code: str, entity_names: list[str]) -> str:
    """Write a clearly qualified attribution for unlabeled demo calls.

    The demo adapter receives the live-call text before it becomes an
    envelope. When the upstream model leaves a strong scam feature's actor
    unknown, the surrounding call pattern still supports a low-confidence
    suspected-party reading. Keep the wording explicitly inferential and never
    apply this fallback to production envelopes.
    """
    normalized = _normalize_feature_narrative_code(code)
    if normalized == "CLAIM_DEVICE_BROKEN":
        relationship = next((item for item in entity_names if item in {"CHILD", "FAMILY_MEMBER", "자녀", "아들", "딸"}), None)
        if relationship:
            return "보이스피싱 의심 인물로 추정되는 사람이 자녀를 사칭하며 휴대전화가 고장 났다고 주장한 정황"
        return "보이스피싱 의심 인물로 추정되는 사람이 휴대전화가 고장 났다고 주장한 정황"
    label = _FEATURE_NARRATIVE_LABELS.get(normalized, "추가 분석 정황")
    if normalized.startswith(("REQUEST_", "PURPOSE_")):
        return f"보이스피싱 의심 인물로 추정되는 사람이 고객에게 {label}을(를) 요구한 정황"
    return f"보이스피싱 의심 인물로 추정되는 사람이 {label}을(를) 말한 정황"


def _normalize_claim_line(value: str) -> str:
    text = " ".join(value.split())
    if "고객이" not in text:
        return text
    if "카드사" in text and ("불법 결제" in text or "승인되지 않은 결제" in text):
        return "보이스피싱 의심 인물이 카드사 관계자를 사칭하며 승인되지 않은 결제가 발생했다고 주장함."
    if "인증번호" in text or "인증정보" in text:
        return "보이스피싱 의심 인물이 고객에게 인증정보 제공을 요구함."
    if "계좌" in text and "범죄" in text:
        return "보이스피싱 의심 인물이 고객 계좌·명의가 범죄에 연루됐다고 주장함."
    if "계좌" in text and "확인" in text:
        return "보이스피싱 의심 인물이 고객 계좌 확인이 필요하다고 주장함."
    return text.replace("고객이 ", "보이스피싱 의심 인물이 ", 1)


def _normalize_summary_text(value: str) -> str:
    text = " ".join(value.split()).replace("상대방", "보이스피싱 의심 인물")
    match = re.match(r"^고객이 (.+?)라 자칭하는 자(?:에 의해|에게) (.+)$", text)
    if match:
        institution, remainder = match.groups()
        return f"보이스피싱 의심 인물이 {institution} 관계자를 사칭하며 {remainder}"
    if "고객이" in text and "자칭" in text:
        return text.replace("고객이 ", "보이스피싱 의심 인물이 ", 1)
    if text.startswith("고객은 ") and ("요구받" in text or "주장" in text):
        return f"보이스피싱 의심 인물이 고객에게 {text.removeprefix('고객은 ').replace('요구받았습니다', '요구함').replace('요구받았다', '요구함')}"
    return text


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
        if not referenced_atoms and source_turns:
            # Some model responses provide valid turn evidence but omit
            # atom_ids.  Recover role metadata from the same-turn atoms before
            # falling back to the feature code.
            referenced_atoms = [
                atom for atom in atoms_by_id.values()
                if int(atom.get("source_turn_id") or 0) in source_turns
            ]
        def authoritative_role(field: str, fallback: str = "UNKNOWN") -> str:
            allowed_roles = {"SUSPECTED_PARTY", "CUSTOMER", "BANK_STAFF", "SYSTEM", "UNKNOWN"}
            values = [str(atom.get(field) or "").upper() for atom in referenced_atoms]
            values = ["SUSPECTED_PARTY" if value == "CALLER" else value for value in values if value]
            values = [value for value in values if value in allowed_roles]
            return values[0] if values and all(value == values[0] for value in values) else fallback
        speaker_role = authoritative_role("speaker_role", authoritative_role("speaker"))
        actor_role = authoritative_role("actor_role", authoritative_role("actor"))
        target_role = authoritative_role("target_role", authoritative_role("target"))
        reported_by_role = authoritative_role("reported_by_role", speaker_role)

        entity_names = list(dict.fromkeys(
            str(value).strip()
            for atom in referenced_atoms
            for value in (
                atom.get("claimed_organization"),
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
        atom_claim_statuses = {
            str(atom.get("claim_status") or "UNKNOWN").upper() for atom in referenced_atoms
        }
        attribution_conflict = (
            actor_role == "CUSTOMER"
            and _is_suspected_feature_code(code)
            and "CUSTOMER_REPORTED" not in atom_claim_statuses
        )
        inferred_suspected_actor = (
            actor_role == "SUSPECTED_PARTY"
            and bool(confidences)
            and min(confidences) < 0.7
            and "CUSTOMER_REPORTED" not in atom_claim_statuses
        )
        demo_source = str((payload.get("envelope_metadata") or {}).get("source") or "").upper()
        demo_inferred_actor = (
            actor_role == "UNKNOWN"
            and demo_source == "DEMO_ADAPTER"
            and _is_suspected_feature_code(code)
            and "CUSTOMER_REPORTED" not in atom_claim_statuses
        )
        sentence = sentence.replace("상대방", "보이스피싱 의심 인물")
        if demo_inferred_actor:
            actor_role = "SUSPECTED_PARTY"
            if speaker_role == "UNKNOWN":
                speaker_role = "SUSPECTED_PARTY"
            if target_role == "UNKNOWN":
                target_role = "CUSTOMER"
            if reported_by_role == "UNKNOWN":
                reported_by_role = "SUSPECTED_PARTY"
            sentence = _demo_inferred_suspected_sentence(code, entity_names)
        elif actor_role == "UNKNOWN" or attribution_conflict:
            sentence = _unknown_attribution_sentence(code, entity_names)
        elif actor_role == "SUSPECTED_PARTY" and not code.startswith("CUSTOMER_"):
            sentence = _normalize_suspected_sentence(code, sentence, entity_names)
            if inferred_suspected_actor and "보이스피싱 의심 인물" in sentence and "추정" not in sentence:
                sentence = sentence.replace(
                    "보이스피싱 의심 인물",
                    "보이스피싱 의심 인물로 추정되는 발화자",
                    1,
                )
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
            "confidence": min(confidences) if confidences else (0.58 if demo_inferred_actor else None),
        }))
    def suspected_party_lines(items: list[str]) -> list[str]:
        normalized: list[str] = []
        for item in items:
            line = _normalize_claim_line(item.replace("상대방", "보이스피싱 의심 인물"))
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
        "summary": _normalize_summary_text(context.summary),
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
        max_retries=_openai_max_retries(),
    )
    response = await client.responses.create(
        model=os.getenv("OPENAI_CONTEXT_MODEL", os.getenv("OPENAI_EVENT_MODEL", "gpt-5.6-luna")),
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
        max_retries=_openai_max_retries(),
    )
    response = await client.responses.create(
        model=os.getenv("OPENAI_CONTEXT_MODEL", os.getenv("OPENAI_EVENT_MODEL", "gpt-5.6-luna")),
        instructions=(
            "You receive only structured anti-fraud signals, never a call transcript. "
            "Treat speaker_role, actor_role, target_role, reported_by_role and their confidence "
            "as authoritative metadata. Never change a CUSTOMER reporter into the actor of a "
            "claim or request. SUSPECTED_PARTY must be rendered as '보이스피싱 의심 인물'; "
            "The underlying source is a live call between the suspected phishing person and the "
            "customer, not a customer complaint or incident report to the bank. A claim, request, "
            "or pressure signal attributed to SUSPECTED_PARTY must be written as that person's "
            "speech or action toward the customer. Do not write '고객이 ... 주장함' unless the "
            "structured metadata explicitly says speaker_role/actor_role=CUSTOMER and the atom "
            "is a customer report. If a speaker is UNKNOWN, do not invent a customer reporter; "
            "for anti-fraud claim/request codes use the event's suspected-party attribution and "
            "otherwise say '화자 미상 · 확인 필요'. "
            "For a DEMO_ADAPTER envelope, if a strong scam feature has no explicit actor but "
            "the surrounding structured signals form a live-call pattern (for example a family "
            "vocative followed by a broken-phone excuse and money/authentication requests), "
            "attribute it as '보이스피싱 의심 인물로 추정되는 사람' with low confidence rather "
            "than rewriting it as a customer report. "
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
