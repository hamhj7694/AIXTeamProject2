"""Grounded staff-facing sentences for Context V3.

This layer deliberately consumes persisted Facts and their structured values only.
It never reconstructs a call transcript and it does not upgrade a claim, request,
or unknown value into a confirmed event.
"""
from __future__ import annotations

from typing import Any


def _text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _object_phrase(noun: str) -> str:
    """Attach the correct Korean object particle for a concrete label."""
    noun = _text(noun)
    if not noun:
        return noun
    last = ord(noun[-1])
    has_batchim = 0xAC00 <= last <= 0xD7A3 and (last - 0xAC00) % 28 != 0
    return f"{noun}{'을' if has_batchim else '를'}"


_ORGANIZATION_LABELS = {
    "PROSECUTION_SERVICE": "수사기관",
    "POLICE_SERVICE": "경찰",
    "FINANCIAL_SUPERVISORY_SERVICE": "금융감독원",
    "BANK": "은행",
    "COURT": "법원",
    "CARD_COMPANY": "카드사",
}


def _organization_label(value: dict[str, Any], atom: dict[str, Any]) -> str:
    """Resolve either a concrete name or the normalized A-part code.

    Provider responses may use ``name``/``organization`` while initial
    structured context uses ``organization_code``.  Both represent the same
    AI-extracted slot and must not collapse to ``특정 기관``.
    """
    raw = _text(
        value.get("organization")
        or value.get("name")
        or value.get("claimed_organization")
        or value.get("organization_code")
        or atom.get("claimed_organization")
    )
    return _ORGANIZATION_LABELS.get(raw.upper(), raw) or "특정 기관"


def _amount(value: dict[str, Any], display_value: str) -> str:
    raw = value.get("amount_krw")
    try:
        if raw is not None:
            return f"{int(float(raw)):,}원"
    except (TypeError, ValueError):
        pass
    return _text(display_value).replace(" 요구", "").strip()


def _state_phrase(atom: dict[str, Any] | None, *, requested: str, reported: str) -> str:
    state = str((atom or {}).get("action_state") or "").upper()
    if state in {"CUSTOMER_REPORTED_COMPLETED", "REPORTED_ACTION", "COMPLETED"}:
        return reported
    if state == "VERIFIED":
        return "확인된"
    if state in {"INSTRUCTED", "REQUESTED"}:
        return requested
    if state in {"UNKNOWN", "MISSING"}:
        return "확인되지 않은"
    return requested


def _supporting_atom(fact: Any, context: dict[str, Any] | None) -> dict[str, Any]:
    """Resolve only the Atom explicitly referenced by a persisted Fact."""
    if not context:
        return {}
    diagnosis = context.get("diagnosis") if isinstance(context.get("diagnosis"), dict) else context
    atoms = {
        str(atom.get("atom_id")): atom
        for atom in diagnosis.get("semantic_atoms", [])
        if isinstance(atom, dict)
    }
    for ref in getattr(fact, "evidence_refs", []) or []:
        ref_type = ref.get("type") if isinstance(ref, dict) else getattr(ref, "type", None)
        ref_id = ref.get("id") if isinstance(ref, dict) else getattr(ref, "id", None)
        if str(ref_type) == "STRUCTURED_ATOM" and str(ref_id) in atoms:
            return atoms[str(ref_id)]
    return {}


def _observed_term(
    atom: dict[str, Any], prefixes: tuple[str, ...], value: dict[str, Any] | None = None,
) -> str | None:
    """Return a concrete lexical cue from an Atom or a chat-extracted Fact."""
    terms = list(atom.get("observed_terms", []) or [])
    if value:
        terms.extend(value.get("observed_terms", []) or [])
    for term in terms:
        if not isinstance(term, dict):
            continue
        code = str(term.get("normalized_code") or "")
        surface = _text(term.get("surface_form"))
        if surface and any(code.startswith(prefix) for prefix in prefixes):
            return surface
    return None


def _communication_sentence(
    atom: dict[str, Any], *, requested: str, value: dict[str, Any] | None = None,
) -> str | None:
    control = str(atom.get("communication_control") or (value or {}).get("communication_control") or "").upper()
    control_text = {
        "NO_FAMILY_DISCLOSURE": "가족에게 알리지 말라고",
        "NO_BANK_CONTACT": "은행에 연락하지 말라고",
        "NO_REPORTING": "신고하지 말라고",
        "NO_END_CALL": "통화를 끝내지 말라고",
        "KEEP_CALL": "통화를 계속 유지하라고",
    }.get(control)
    if control_text:
        return f"상대방이 {control_text} 요구한 정황입니다."
    return None


def validate_fact_atom_alignment(fact: Any, context: dict[str, Any] | None = None) -> None:
    """Ensure sentence inputs do not silently lose Atom state or modality."""
    atom = _supporting_atom(fact, context)
    if not atom:
        return
    value = getattr(fact, "value", {}) or {}
    for field in (
        "atom_class", "predicate", "speaker", "subject", "actor", "target", "object",
        "action_state", "polarity", "modality", "claim_status", "destination", "amount_scope",
        "claimed_purpose", "threat_type", "repetition_pressure",
    ):
        atom_value = atom.get(field)
        if atom_value is None:
            continue
        stored_value = value.get(field)
        if stored_value is not None and str(stored_value).upper() != str(atom_value).upper():
            raise ValueError(f"Fact와 supporting Atom의 {field} 상태가 일치하지 않습니다.")
    if atom.get("polarity") in {"NEGATIVE", "CONDITIONAL"} and value.get("polarity") is None:
        raise ValueError("부정·조건부 Atom의 polarity를 보존하지 않은 Fact입니다.")


def status_label(status: str) -> str:
    return {
        "PROPOSED": "담당자 확인 필요",
        "CONFIRMED": "담당자 확인 완료",
        "REJECTED": "검토에서 제외됨",
        "SUPERSEDED": "새 내용으로 대체됨",
    }.get(status, "담당자 확인 필요")


def _grounded_fact_text_base(
    semantic_key: str, display_value: str, value: dict[str, Any] | None = None,
    *, context: dict[str, Any] | None = None, fact: Any | None = None,
) -> str:
    """Render one Fact without changing its epistemic meaning."""
    value = value or {}
    display = _text(display_value)
    atom = _supporting_atom(fact, context) if fact is not None else {}
    effective = {**value, **{key: atom[key] for key in (
        "action_state", "communication_control", "auth_secret_type", "destination",
        "urgency", "obligation", "claimed_organization", "claimed_role", "claimed_purpose",
        "polarity", "modality", "claim_status",
    ) if atom.get(key) is not None}}
    action_word = "지시한" if str(effective.get("action_state") or "").upper() == "INSTRUCTED" else "요구한"
    if semantic_key == "offender.claimed_organization":
        # Chat extraction uses ``name`` while initial Atoms use a normalized
        # code. Preserve the concrete surface term whenever it is persisted.
        organization = _organization_label(value, atom)
        return f"상대방이 {_object_phrase(organization)} 사칭한 정황입니다."
    if semantic_key == "offender.claimed_person_or_role":
        role = _text(value.get("role") or value.get("claimed_role") or effective.get("claimed_role"))
        if role:
            return f"상대방이 {_object_phrase(role)} 내세운 정황입니다."
        role = _observed_term(atom, ("ROLE.", "PERSON."), value)
        return f"상대방이 {_object_phrase(role or '특정 인물·역할')} 내세운 정황입니다."
    if semantic_key == "offender.incident_claim":
        if "범죄" in display or "연루" in display:
            return "상대방이 계좌·명의가 범죄에 연루됐다고 주장한 내용입니다."
        return f"상대방이 {display or '사건 관련 내용을'} 주장한 내용입니다."
    if semantic_key == "exposure.authentication_information":
        secret = _text(effective.get("auth_secret_type"))
        if not secret:
            secret = _observed_term(atom, ("AUTH.",), value)
        subject = secret or "인증정보"
        state = str(effective.get("action_state") or value.get("status") or "").upper()
        if state in {"CUSTOMER_REPORTED_COMPLETED", "REPORTED_ACTION", "COMPLETED", "EXPOSED", "SUPPLIED", "DISCLOSED"}:
            return f"고객이 {subject}를 제공했다고 진술했습니다."
        if state in {"UNKNOWN", "MISSING"}:
            return f"{subject} 제공 여부는 아직 확인되지 않았습니다."
        return f"상대방이 {subject} 제공을 요구한 정황입니다."
    if semantic_key == "exposure.personal_information":
        return "상대방이 개인정보 제공을 요구한 정황입니다."
    if semantic_key == "device.remote_control_app":
        if str(value.get("status") or "").upper() in {"INSTALLED", "EXECUTED", "COMPLETED"}:
            return "고객이 원격제어 앱 또는 링크를 실행했다고 진술한 정황입니다."
        return "상대방이 원격제어 앱 또는 링크 실행을 요구한 정황입니다."
    if semantic_key == "transfer.requested.amount":
        amount = _amount(value, display)
        destination = ""
        if effective.get("destination") == "CLAIMED_SAFE_ACCOUNT":
            destination = " 안전계좌로"
        return f"상대방이 {amount}{destination} 송금하도록 {action_word} 정황입니다."
    if semantic_key == "transfer.actual.amount":
        return f"실제 이체 금액은 {_amount(value, display)}입니다."
    if semantic_key == "transfer.actual.status":
        state = str(value.get("status") or "").upper()
        if state == "TRANSFERRED":
            return "고객이 실제로 송금했다고 진술한 상태입니다."
        if state in {"NOT_TRANSFERRED", "NOT_SENT"}:
            return "고객이 송금하지 않았다고 진술한 상태입니다."
        return "송금 여부는 아직 확인되지 않았습니다."
    if semantic_key == "circumstance.demand":
        communication = _communication_sentence(atom, requested="알리지", value=value)
        if communication:
            return communication
        if effective.get("destination") == "CLAIMED_SAFE_ACCOUNT" or value.get("kind") == "SAFE_ACCOUNT":
            term = _observed_term(atom, ("TERM.SAFE_ACCOUNT", "TERM.PROTECTIVE_ACCOUNT", "TERM.SECURE_ACCOUNT"))
            destination = term or "안전계좌"
            return f"상대방이 {destination}로 송금하도록 {action_word} 정황입니다."
        if value.get("kind") == "LINK_OR_APP":
            return "상대방이 링크 또는 앱 실행을 요구한 정황입니다."
        lowered = display.casefold()
        if "송금" in lowered or "이체" in lowered:
            return f"상대방이 송금·이체를 {action_word} 정황입니다."
        if "앱" in lowered or "링크" in lowered:
            return f"상대방이 앱 또는 링크 실행을 {action_word} 정황입니다."
        if "통화" in lowered:
            return "상대방이 통화를 계속 유지하도록 요구한 정황입니다."
        if "외부" in lowered or "알리" in lowered:
            return "상대방이 가족·은행 등 외부에 알리지 않도록 요구한 정황입니다."
        if "안전계좌" in lowered:
            return "상대방이 안전계좌로 자금 이동을 유도한 정황입니다."
        return f"상대방이 {display or '특정 행동'}을(를) {action_word} 정황입니다.".replace("을(를)", "을")
    if semantic_key == "circumstance.tactic":
        communication = _communication_sentence(atom, requested="알리지", value=value)
        if communication:
            return communication
        if effective.get("urgency") not in {None, "NONE", "UNKNOWN", "UNKNOWN_DEADLINE"} or value.get("kind") in {"URGENCY", "DEADLINE_TODAY", "DEADLINE_IMMEDIATE"}:
            term = _observed_term(atom, ("URGENCY.",), value)
            if term:
                return f"상대방이 ‘{term}’ 처리하라고 요구하며 긴급한 행동을 재촉한 정황입니다."
            return "상대방이 즉시 행동하도록 긴급성을 강조한 정황입니다."
        lowered = display.casefold()
        threat_type = str(value.get("threat_type") or "").upper()
        if any(term in lowered for term in ("협박", "위협", "체포", "구속", "처벌", "불이익")) or threat_type:
            if threat_type in {"ARREST", "DETENTION"} or any(term in lowered for term in ("체포", "구속")):
                return "상대방이 체포·구속을 언급하며 압박한 정황입니다."
            if threat_type in {"PUNISHMENT", "PENALTY"} or "처벌" in lowered:
                return "상대방이 처벌을 언급하며 압박한 정황입니다."
            return "상대방이 협박·위협성 표현으로 압박한 정황입니다."
        if "고립" in lowered or "연락" in lowered or "알리" in lowered or "가족" in lowered or "상의를" in lowered:
            return "외부 연락이나 주변 상의를 제한한 정황입니다."
        if "긴급" in lowered or "압박" in lowered:
            return "긴급 처리를 재촉하거나 압박한 정황입니다."
        if "불안" in lowered or "공포" in lowered or "처벌" in lowered:
            return "불안이나 공포를 유발한 정황입니다."
        return f"{display or '압박·조작'} 정황이 나타났습니다."
    return display


def _state_disclaimer(atom: dict[str, Any]) -> str | None:
    state = str(atom.get("action_state") or "").upper()
    polarity = str(atom.get("polarity") or "POSITIVE").upper()
    if state in {"UNKNOWN", "MISSING"}:
        return "현재 확인되지 않은 내용입니다"
    if state == "DENIED" or polarity == "NEGATIVE":
        return "부인되었거나 실행되지 않은 내용으로 기록되어 있습니다"
    if polarity == "CONDITIONAL" or str(atom.get("modality") or "").upper() == "CONDITIONAL":
        return "조건부로 언급된 내용입니다"
    return None


def grounded_fact_text(
    semantic_key: str, display_value: str, value: dict[str, Any] | None = None,
    *, context: dict[str, Any] | None = None, fact: Any | None = None,
) -> str:
    """Render one Fact and preserve exceptional state in the staff sentence."""
    text = _grounded_fact_text_base(semantic_key, display_value, value, context=context, fact=fact)
    atom = _supporting_atom(fact, context) if fact is not None else {}
    disclaimer = _state_disclaimer(atom)
    if not disclaimer or disclaimer in text:
        return text
    return f"{text} ({disclaimer})"


def grounded_fact_item(fact: Any, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a presentation plan while retaining the Fact's lineage."""
    validate_fact_atom_alignment(fact, context)
    atom = _supporting_atom(fact, context)
    return {
        "fact_id": fact.fact_id,
        "text": grounded_fact_text(fact.semantic_key, fact.display_value, fact.value, context=context, fact=fact),
        "status_label": status_label(fact.status),
        "supporting_refs": [dict(ref) for ref in fact.evidence_refs],
        "allowed_claims": [fact.semantic_key],
        "semantic_state": atom.get("action_state") or (fact.value or {}).get("action_state"),
        "polarity": atom.get("polarity") or (fact.value or {}).get("polarity", "POSITIVE"),
        "modality": atom.get("modality") or (fact.value or {}).get("modality"),
    }


def validate_grounded_fact(fact: Any, text: str, context: dict[str, Any] | None = None) -> None:
    """Reject empty reconstruction and epistemic status upgrades."""
    if not _text(text):
        raise ValueError("근거 문장이 비어 있습니다.")
    lowered = text.casefold()
    if fact.status == "PROPOSED" and any(word in lowered for word in ("확정", "완료됨", "실행됨")):
        raise ValueError("검토 전 Fact를 확정 또는 완료 사실로 문장화할 수 없습니다.")
    if fact.status != "CONFIRMED" and any(word in lowered for word in ("완료됐", "완료되었", "제공했습니다", "송금했습니다")):
        raise ValueError("확인되지 않은 Fact를 완료 사실로 문장화할 수 없습니다.")
    atom = _supporting_atom(fact, context)
    if (
        str(atom.get("action_state") or "").upper() in {"CUSTOMER_REPORTED_COMPLETED", "REPORTED_ACTION", "COMPLETED"}
        and str(atom.get("claim_status") or "").upper() not in {"VERIFIED", "STAFF_REPORTED"}
        and any(word in lowered for word in ("확인된", "검증된", "공식 확인"))
    ):
        raise ValueError("고객 진술 완료를 공식 확인 완료로 승격할 수 없습니다.")
    validate_grounded_statement_scope(fact, text, context)
    validate_unknown_not_upgraded(fact, text, context)
    validate_semantic_slot_preservation(fact, text, context)


def validate_no_unlinked_fact_join(
    facts: list[Any], text: str, context: dict[str, Any] | None = None,
) -> None:
    """Reject causal/purpose joins unless a persisted Relation connects them."""
    if len(facts) < 2:
        return
    lowered = _text(text).casefold()
    join_markers = (
        "because", "therefore", "due to", "so that",
        "\ub54c\ubb38\uc5d0", "\ub530\ub77c\uc11c", "\uadf8\ub798\uc11c", "\uc704\ud574",
    )
    if not any(marker in lowered for marker in join_markers):
        return
    diagnosis = (context or {}).get("diagnosis", context or {})
    relation_pairs = {
        frozenset((str(item.get("source_atom_id")), str(item.get("target_atom_id"))))
        for item in diagnosis.get("semantic_relations", [])
        if isinstance(item, dict)
    }
    atom_ids = []
    for fact in facts:
        atom = _supporting_atom(fact, context)
        if atom.get("atom_id"):
            atom_ids.append(str(atom["atom_id"]))
    if len(atom_ids) >= 2 and frozenset(atom_ids[:2]) not in relation_pairs:
        raise ValueError("Relation이 없는 Fact들을 인과·목적 관계로 결합할 수 없습니다.")


def validate_unknown_not_upgraded(
    fact: Any, text: str, context: dict[str, Any] | None = None,
) -> None:
    """Reject reconstruction that turns an unknown state into a concrete claim."""
    atom = _supporting_atom(fact, context)
    value = getattr(fact, "value", {}) or {}
    state = str(atom.get("action_state") or value.get("action_state") or "").upper()
    if state not in {"UNKNOWN", "MISSING"}:
        return
    disclaimer = _state_disclaimer(atom or {"action_state": state})
    if disclaimer and disclaimer not in text:
        raise ValueError("UNKNOWN/MISSING state cannot be upgraded to a concrete fact.")


def validate_semantic_slot_preservation(
    fact: Any, text: str, context: dict[str, Any] | None = None,
) -> None:
    """Ensure concrete slots that drive a sentence remain visible after rendering."""
    atom = _supporting_atom(fact, context)
    if not atom:
        return
    lowered = _text(text).casefold()
    value = getattr(fact, "value", {}) or {}

    amount = atom.get("amount_krw", value.get("amount_krw"))
    if amount is not None:
        try:
            rendered_amount = f"{int(float(amount)):,}"
        except (TypeError, ValueError):
            rendered_amount = _text(str(amount))
        if rendered_amount and rendered_amount.casefold() not in lowered:
            raise ValueError("amount semantic slot was not preserved during rendering.")

    key = str(getattr(fact, "semantic_key", ""))
    required_prefixes: tuple[str, ...] = ()
    if key == "offender.claimed_organization":
        required_prefixes = ("ORG.", "INSTITUTION.")
    elif key == "exposure.authentication_information":
        required_prefixes = ("AUTH.",)
    elif key in {"transfer.requested.amount", "circumstance.demand"}:
        required_prefixes = ("TERM.SAFE_ACCOUNT", "TERM.PROTECTIVE_ACCOUNT", "TERM.SECURE_ACCOUNT")
    if required_prefixes:
        concrete_terms = [
            _text(term.get("surface_form")).casefold()
            for term in atom.get("observed_terms", []) or []
            if any(str(term.get("normalized_code") or "").startswith(prefix) for prefix in required_prefixes)
            and _text(term.get("surface_form"))
        ]
        if concrete_terms and not any(term in lowered for term in concrete_terms):
            raise ValueError("a concrete semantic slot was broadened during rendering.")


def validate_grounded_statement_scope(fact: Any, text: str, context: dict[str, Any] | None = None) -> None:
    """Reject a staff sentence that broadens a structured Atom's meaning."""
    atom = _supporting_atom(fact, context)
    if not atom:
        return
    lowered = text.casefold()
    if fact.semantic_key == "offender.claimed_organization":
        organizations = {
            "PROSECUTION_SERVICE": "수사기관", "POLICE_SERVICE": "경찰",
            "FINANCIAL_SUPERVISORY_SERVICE": "금융감독원", "BANK": "은행",
            "COURT": "법원", "CARD_COMPANY": "카드사",
        }
        expected = organizations.get(str(atom.get("claimed_organization") or ""))
        if expected and expected.casefold() not in lowered:
            raise ValueError("문장에 supporting Atom과 다른 기관 정보가 포함되어 있습니다.")
        for label in organizations.values():
            if label.casefold() in lowered and label != expected:
                raise ValueError("문장에 supporting Atom에 없는 기관 정보가 포함되어 있습니다.")
    observed = {
        str(term.get("normalized_code")): str(term.get("surface_form"))
        for term in atom.get("observed_terms", []) or []
        if term.get("normalized_code") and term.get("surface_form")
    }
    # A surface cue may be omitted by a safe template, but a stored cue must
    # never be replaced with a different concrete cue during rendering.
    if fact.semantic_key == "exposure.authentication_information" and observed:
        auth_terms = [surface.casefold() for code, surface in observed.items() if code.startswith("AUTH.")]
        concrete_auth = [term for term in ("otp", "인증번호", "비밀번호", "pin", "cvc") if term in lowered]
        if auth_terms and concrete_auth and not any(term in lowered for term in auth_terms):
            raise ValueError("문장에 supporting Atom과 다른 인증정보 종류가 포함되어 있습니다.")
