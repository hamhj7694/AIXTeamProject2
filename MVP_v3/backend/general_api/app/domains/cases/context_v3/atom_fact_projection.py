"""Project persisted Semantic Atoms into reviewable Context V3 Fact candidates.

This adapter is intentionally deterministic.  It does not read or persist source
utterances; an Atom id is the only lineage reference passed to the Fact layer.
One Atom produces at most one candidate, so fine-grained values are not collapsed
into a single broad tactic or demand.
"""
from __future__ import annotations

from typing import Any


_LABELS = {
    "exposure.authentication_information": "인증 정보 제공 요청",
    "exposure.personal_information": "개인정보 제공 요청",
    "device.remote_control_app": "원격 제어 또는 앱 설치 요청",
    "offender.claimed_organization": "사칭 기관",
    "offender.claimed_person_or_role": "사칭 인물 또는 직책",
    "offender.incident_claim": "상대방의 사건 관련 주장",
    "transfer.requested.amount": "요구 금액",
    "transfer.actual.amount": "실제 이체 금액",
    "circumstance.demand": "상대방의 요구",
    "circumstance.tactic": "압박·조작 정황",
}


def _key(atom: dict[str, Any]) -> str:
    predicate = str(atom.get("predicate") or "").upper()
    atom_class = str(atom.get("atom_class") or "").upper()
    if atom.get("auth_secret_type") or predicate in {"DISCLOSE_OTP", "REQUEST_AUTH_INFO"}:
        return "exposure.authentication_information"
    if "SENSITIVE" in predicate or "PERSONAL" in predicate or atom_class == "DISCLOSURE_REQUEST":
        return "exposure.personal_information"
    if predicate == "CLAIMS_ORGANIZATION":
        return "offender.claimed_organization"
    if atom.get("claimed_role") or predicate in {"CLAIMS_ROLE", "CLAIMS_PERSON"}:
        return "offender.claimed_person_or_role"
    if predicate.startswith("CLAIMS_"):
        return "offender.incident_claim"
    if atom.get("amount_value_krw") is not None:
        if atom.get("amount_role") in {"TRANSFER_OUT", "REFUND_IN", "CLAIMED_LOSS"}:
            return "transfer.actual.amount"
        if atom.get("action_state") in {"REQUESTED", "INSTRUCTED"}:
            return "transfer.requested.amount"
        if predicate in {"TRANSFER_FUNDS", "WITHDRAW_CASH"}:
            return "transfer.actual.amount"
    if predicate in {"TRANSFER_FUNDS", "WITHDRAW_CASH", "OPEN_URL", "OPEN_APP", "INSTALL_APP"}:
        return "circumstance.demand"
    if atom.get("communication_control") or predicate in {"AVOID_EXTERNAL_CONTACT", "KEEP_CALL", "KEEP_SECRET"}:
        return "circumstance.tactic"
    if any(atom.get(name) not in {None, "", "NONE", "UNKNOWN", "UNKNOWN_DEADLINE"} for name in (
        "urgency", "fear_pressure", "isolation_pressure", "secrecy_pressure", "authority_pressure",
    )):
        return "circumstance.tactic"
    return "circumstance.demand" if atom_class in {"ACTION_REQUEST", "ACTION_INSTRUCTION", "FINANCIAL_ACTION"} else "offender.incident_claim"


def _display(key: str, atom: dict[str, Any]) -> str:
    terms = atom.get("observed_terms") or []
    term = next((str(item.get("surface_form")) for item in terms if item.get("surface_form")), None)
    observed = [str(item.get("surface_form")).strip() for item in terms if item.get("surface_form")]
    observed_text = "·".join(dict.fromkeys(observed))[:160]
    if key == "transfer.requested.amount":
        raw = atom.get("amount_value_krw")
        amount = f"{int(float(raw)):,}원" if raw is not None else "금액"
        return f"상대방이 {amount} 송금을 요구한 정황"
    if key == "transfer.actual.amount":
        raw = atom.get("amount_value_krw")
        amount = f"{int(float(raw)):,}원" if raw is not None else "금액"
        role = atom.get("amount_role")
        if role == "REFUND_IN":
            return f"상대방에게 {amount}을 반환받았다고 보고한 정황"
        if role == "CLAIMED_LOSS":
            return f"상대방에게 {amount}의 피해를 입었다고 보고한 정황"
        return f"상대방에게 {amount}을 송금했다고 보고한 정황"
    if key == "exposure.authentication_information":
        return f"상대방이 {atom.get('auth_secret_type') or term or '인증 정보'} 제공을 요구한 정황"
    if key == "exposure.personal_information":
        return f"상대방이 {observed_text or '개인정보'} 제공을 요구한 정황"
    if key == "offender.claimed_organization":
        code_labels = {
            "PROSECUTION_SERVICE": "수사기관", "POLICE_SERVICE": "경찰",
            "FINANCIAL_SUPERVISORY_SERVICE": "금융감독원", "BANK": "은행",
            "COURT": "법원", "CARD_COMPANY": "카드사", "LOAN_COMPANY": "대출기관",
        }
        organization = term or code_labels.get(str(atom.get("claimed_organization") or ""), "특정 기관")
        return f"상대방이 {organization}을 사칭한 정황"
    if key == "offender.claimed_person_or_role":
        return f"상대방이 {atom.get('claimed_role') or term or '특정 인물 또는 직책'}을 내세운 정황"
    if key == "circumstance.tactic":
        control = atom.get("communication_control")
        if control:
            return f"상대방이 {observed_text or '외부 확인이나 연락'}을 제한한 정황"
        urgency = atom.get("urgency")
        if urgency and urgency not in {"NONE", "UNKNOWN", "UNKNOWN_DEADLINE"}:
            return f"상대방이 {term or '긴급성'}을 강조해 행동을 재촉한 정황"
        if atom.get("fear_pressure") or atom.get("threat_type"):
            return f"상대방이 {observed_text or '불안이나 처벌 우려'}를 자극한 정황"
        return f"상대방이 {observed_text or '행동을 유도하거나 압박'}한 정황"
    if key == "circumstance.demand":
        return f"상대방이 {observed_text or '특정 행동'}을 요구한 정황"
    return f"상대방이 {observed_text or '사건과 관련된 내용'}을 주장한 정황"


def project_semantic_atoms_to_fact_candidates(atoms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return one privacy-safe Fact candidate per valid Semantic Atom."""
    candidates: list[dict[str, Any]] = []
    for atom in atoms:
        atom_id = str(atom.get("atom_id") or "").strip()
        if not atom_id:
            continue
        key = _key(atom)
        expression = {
            field: atom[field]
            for field in (
                "speech_act", "directive_strength", "obligation", "urgency", "authority_pressure",
                "fear_pressure", "secrecy_pressure", "isolation_pressure", "financial_pressure",
                "communication_control", "speech_form_codes",
            )
            if atom.get(field) not in (None, "", [], {})
        }
        value: dict[str, Any] = {
            "atom_id": atom_id,
            "atom_class": atom.get("atom_class"),
            "predicate": atom.get("predicate"),
            "speaker": atom.get("speaker"),
            "subject": atom.get("subject"),
            "actor": atom.get("actor"),
            "target": atom.get("target"),
            "object": atom.get("object"),
            "action_state": atom.get("action_state"),
            "amount_role": atom.get("amount_role"),
            "amount_direction": atom.get("amount_direction"),
            "amount_event_id": atom.get("amount_event_id"),
            "modality": atom.get("modality"),
            "polarity": atom.get("polarity", "POSITIVE"),
            "claim_status": atom.get("claim_status"),
            "expression_features": expression,
            "observed_lexical_codes": [
                str(term.get("normalized_code"))
                for term in atom.get("observed_terms") or []
                if term.get("normalized_code")
            ],
            # Surface forms are privacy-safe lexical features, not a transcript.
            # Persist them so panel copy does not collapse into a generic label.
            "observed_terms": [
                {"surface_form": str(term.get("surface_form")), "normalized_code": str(term.get("normalized_code"))}
                for term in atom.get("observed_terms") or []
                if term.get("surface_form") and term.get("normalized_code")
            ][:20],
        }
        if atom.get("amount_value_krw") is not None:
            value.update(amount_krw=atom["amount_value_krw"], currency="KRW")
        if atom.get("auth_secret_type"):
            value["auth_secret_type"] = atom["auth_secret_type"]
        if atom.get("destination"):
            value["destination"] = atom["destination"]
        for field in ("amount_scope", "claimed_purpose", "threat_type", "repetition_pressure"):
            if atom.get(field) not in (None, ""):
                value[field] = atom[field]
        candidates.append({
            "atom_id": atom_id,
            "semantic_key": key,
            "display_label": _LABELS[key],
            "value": value,
            "display_value": _display(key, atom),
            "source_kind": "AI_EXTRACTION",
            "confidence": None,
            "evidence_refs": [{"type": "STRUCTURED_ATOM", "id": atom_id}],
            "visibility": "BANK_INTERNAL",
        })
    return candidates
