"""Privacy-safe observed lexical cues for the LLM Context branch.

Only short, allowlisted terms that are actually present in the transient source
turn are retained.  The source turn itself never leaves the extraction process.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from contracts.diagnosis import ObservedLexicalCue


@dataclass(frozen=True)
class _CueRule:
    pattern: str
    normalized_code: str
    term_type: str
    semantic_value: str | None = None
    lemma: str | None = None


# Longest patterns run first so "은행 직원" wins over the shorter "은행".
_RULES = (
    _CueRule(r"금융\s*감독원", "TERM.FINANCIAL_SUPERVISORY_SERVICE", "INSTITUTION", "FINANCIAL_SUPERVISORY_SERVICE"),
    _CueRule(r"은행\s*직원", "ROLE.BANK_EMPLOYEE", "ROLE", "BANK_EMPLOYEE", "은행직원"),
    _CueRule(r"보안\s*카드", "AUTH.SECURITY_CARD", "AUTH_SECRET_TYPE", "SECURITY_CARD", "보안카드"),
    _CueRule(r"인증\s*번호", "AUTH.AUTH_CODE", "AUTH_SECRET_TYPE", "SECURITY_CODE", "인증번호"),
    _CueRule(r"안전\s*계좌", "TERM.SAFE_ACCOUNT", "SCAM_TERM", "CLAIMED_SAFE_ACCOUNT", "안전계좌"),
    _CueRule(r"보호\s*계좌", "TERM.PROTECTIVE_ACCOUNT", "SCAM_TERM", "CLAIMED_SAFE_ACCOUNT", "보호계좌"),
    _CueRule(r"보안\s*계좌", "TERM.SECURE_ACCOUNT", "SCAM_TERM", "CLAIMED_SAFE_ACCOUNT", "보안계좌"),
    _CueRule(r"범죄\s*연루", "TERM.CRIME_INVOLVEMENT", "SCAM_TERM", "CRIME_INVOLVEMENT", "범죄연루"),
    _CueRule(r"자금\s*세탁", "TERM.MONEY_LAUNDERING", "SCAM_TERM", "MONEY_LAUNDERING", "자금세탁"),
    _CueRule(r"사건\s*번호", "TERM.CASE_NUMBER", "SCAM_TERM", "CASE_NUMBER", "사건번호"),
    _CueRule(r"서울중앙지검", "TERM.PROSECUTION_SERVICE", "INSTITUTION", "PROSECUTION_SERVICE"),
    _CueRule(r"금융감독원", "TERM.FINANCIAL_SUPERVISORY_SERVICE", "INSTITUTION", "FINANCIAL_SUPERVISORY_SERVICE"),
    _CueRule(r"국세청", "TERM.NATIONAL_TAX_SERVICE", "INSTITUTION", "NATIONAL_TAX_SERVICE"),
    _CueRule(r"검찰", "TERM.PROSECUTION", "INSTITUTION", "PROSECUTION_SERVICE"),
    _CueRule(r"경찰", "TERM.POLICE", "INSTITUTION", "POLICE_SERVICE"),
    _CueRule(r"카드사", "TERM.CARD_COMPANY", "INSTITUTION", "CARD_COMPANY"),
    _CueRule(r"은행", "TERM.BANK", "INSTITUTION", "BANK"),
    _CueRule(r"법원", "TERM.COURT", "INSTITUTION", "COURT"),
    _CueRule(r"수사관", "ROLE.INVESTIGATOR", "ROLE", "INVESTIGATOR", "수사관"),
    _CueRule(r"조사관", "ROLE.INVESTIGATOR", "ROLE", "INVESTIGATOR", "조사관"),
    _CueRule(r"검사", "ROLE.PROSECUTOR", "ROLE", "PROSECUTOR", "검사"),
    _CueRule(r"상담원", "ROLE.COUNSELOR", "ROLE", "COUNSELOR", "상담원"),
    _CueRule(r"담당자", "ROLE.REPRESENTATIVE", "ROLE", "REPRESENTATIVE", "담당자"),
    _CueRule(r"OTP", "AUTH.OTP", "AUTH_SECRET_TYPE", "OTP", "OTP"),
    _CueRule(r"비밀번호", "AUTH.PASSWORD", "AUTH_SECRET_TYPE", "PASSWORD", "비밀번호"),
    _CueRule(r"PIN", "AUTH.PIN", "AUTH_SECRET_TYPE", "PIN", "PIN"),
    _CueRule(r"CVC", "AUTH.CARD_CVC", "AUTH_SECRET_TYPE", "CARD_CVC", "CVC"),
    _CueRule(r"송금", "ACTION.TRANSFER", "ACTION", "TRANSFER_FUNDS", "송금하다"),
    _CueRule(r"이체", "ACTION.TRANSFER", "ACTION", "TRANSFER_FUNDS", "이체하다"),
    _CueRule(r"인출", "ACTION.WITHDRAW", "ACTION", "WITHDRAW_CASH", "인출하다"),
    _CueRule(r"대출", "ACTION.LOAN", "ACTION", "TAKE_LOAN", "대출받다"),
    _CueRule(r"설치", "ACTION.INSTALL", "ACTION", "INSTALL_APP", "설치하다"),
    _CueRule(r"접속", "ACTION.OPEN_ACCESS", "ACTION", "OPEN_URL", "접속하다"),
    _CueRule(r"공유", "ACTION.SHARE", "ACTION", "SHARE_SCREEN", "공유하다"),
    _CueRule(r"인증", "ACTION.AUTHENTICATE", "ACTION", "AUTHENTICATE", "인증하다"),
    _CueRule(r"체포", "THREAT.ARREST", "THREAT", "ARREST_THREAT"),
    _CueRule(r"압류", "THREAT.ASSET_FREEZE", "THREAT", "ASSET_FREEZE_THREAT"),
    _CueRule(r"동결", "THREAT.ASSET_FREEZE", "THREAT", "ASSET_FREEZE_THREAT"),
    _CueRule(r"처벌", "THREAT.PENALTY", "THREAT", "LEGAL_ACTION_THREAT"),
    _CueRule(r"수사", "THREAT.INVESTIGATION", "THREAT", "INVESTIGATION_ESCALATION_THREAT"),
    _CueRule(r"당장", "URGENCY.DANGJANG", "URGENCY", "IMMEDIATE"),
    _CueRule(r"즉시", "URGENCY.JEUKSI", "URGENCY", "IMMEDIATE"),
    _CueRule(r"바로", "URGENCY.BARO", "URGENCY", "IMMEDIATE"),
    _CueRule(r"지금", "URGENCY.JIGEUM", "URGENCY", "IMMEDIATE"),
    _CueRule(r"오늘", "URGENCY.TODAY", "URGENCY", "TODAY"),
    _CueRule(r"반드시", "OBLIGATION.MUST", "OBLIGATION", "STRONG"),
    _CueRule(r"무조건", "OBLIGATION.UNCONDITIONAL", "OBLIGATION", "STRONG"),
    _CueRule(r"꼭", "OBLIGATION.MUST", "OBLIGATION", "STRONG"),
    _CueRule(r"전액", "QUANTITY.ALL", "QUANTITY", "ALL_FUNDS"),
    _CueRule(r"전부", "QUANTITY.ALL", "QUANTITY", "ALL_FUNDS"),
    _CueRule(r"잔액", "QUANTITY.REMAINING_BALANCE", "QUANTITY", "REMAINING_BALANCE"),
    _CueRule(r"일부", "QUANTITY.PARTIAL", "QUANTITY", "PARTIAL_FUNDS"),
    _CueRule(r"절반", "QUANTITY.HALF", "QUANTITY", "HALF"),
    _CueRule(r"비밀", "SECRECY.SECRET", "SECRECY", "KEEP_SECRET"),
    _CueRule(r"가족", "SECRECY.FAMILY", "SECRECY", "NO_FAMILY_DISCLOSURE"),
    _CueRule(r"신고", "SECRECY.REPORT", "SECRECY", "NO_REPORTING"),
)

_SENSITIVE_LITERAL = re.compile(r"(?:\d{4,}|\d{2,}[- ]\d{2,}|\b[A-Z]{2,}\s*\d{3,}\b)", re.IGNORECASE)


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


def _rule_relevant(rule: _CueRule, atom: dict[str, Any] | None) -> bool:
    if atom is None:
        return True
    predicate = str(atom.get("predicate") or "").upper()
    atom_class = str(atom.get("atom_class") or "").upper()
    if "ORGANIZATION" in predicate or "ORGANIZATION" in atom_class:
        return rule.term_type in {"INSTITUTION", "ROLE", "SCAM_TERM"}
    if "ROLE" in predicate or "ROLE" in atom_class:
        return rule.term_type == "ROLE"
    if predicate in {"DISCLOSE_OTP", "DISCLOSE_PASSWORD", "PROVIDE_CARD_INFO"} or "DISCLOSURE" in atom_class:
        return rule.term_type == "AUTH_SECRET_TYPE"
    if "TRANSFER" in predicate or "WITHDRAW" in predicate or "FINANCIAL" in atom_class:
        return rule.term_type in {"ACTION", "SCAM_TERM", "URGENCY", "OBLIGATION", "QUANTITY", "THREAT"}
    if "THREAT" in predicate or "THREAT" in atom_class:
        return rule.term_type in {"THREAT", "URGENCY", "OBLIGATION"}
    if "CALL" in predicate or "CONTACT" in predicate or "SECRECY" in atom_class or "AVOID" in predicate or "KEEP_SECRET" in predicate:
        return rule.term_type in {"SECRECY", "URGENCY", "OBLIGATION", "THREAT"}
    if "URGENCY" in predicate or atom.get("urgency") not in {None, "NONE", "UNKNOWN_DEADLINE"}:
        return rule.term_type in {"URGENCY", "OBLIGATION", "THREAT"}
    return True


def extract_observed_terms(source_text: str, atom: dict[str, Any] | None = None) -> list[ObservedLexicalCue]:
    """Select short allowlisted terms that really occur in one transient turn."""
    source = unicodedata.normalize("NFKC", str(source_text or ""))
    occupied: list[tuple[int, int]] = []
    terms: list[ObservedLexicalCue] = []
    for rule in _RULES:
        if not _rule_relevant(rule, atom):
            continue
        for match in re.finditer(rule.pattern, source, flags=re.IGNORECASE):
            surface = match.group(0)
            compact = _compact(surface)
            if "\ufffd" in surface or not compact or len(compact) > 16 or len(surface.split()) > 2 or _SENSITIVE_LITERAL.search(surface):
                continue
            if any(match.start() < end and start < match.end() for start, end in occupied):
                continue
            occupied.append((match.start(), match.end()))
            terms.append(ObservedLexicalCue(
                surface_form=surface,
                lemma=rule.lemma or surface,
                normalized_code=rule.normalized_code,
                term_type=rule.term_type,
                semantic_value=rule.semantic_value,
                confidence=0.99,
            ))
            break
    return terms


def infer_speech_form_codes(source_text: str) -> list[str]:
    source = unicodedata.normalize("NFKC", str(source_text or ""))
    codes: list[str] = []
    if re.search(r"(?:해야|하셔야|셔야|필요합니다|필수|요구합니다)", source):
        codes.append("DIRECTIVE.MUST_FORM")
    if re.search(r"(?:하지\s*마|하면\s*안|말하면\s*안)", source):
        codes.append("PROHIBITION_FORM")
    if re.search(r"(?:하면\s*될|가능하면|할\s*수\s*있으면|않으면)", source):
        codes.append("CONDITIONAL_FORM")
    return codes


def enrich_atom_payload(source_text: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Attach deterministic lexical/pragmatic data without retaining source text."""
    enriched = dict(payload)
    terms = extract_observed_terms(source_text, enriched)
    enriched["observed_terms"] = [term.model_dump(mode="json") for term in terms]
    enriched["speech_form_codes"] = infer_speech_form_codes(source_text)
    semantic_values = {term.semantic_value for term in terms if term.semantic_value}
    if enriched.get("urgency") in {None, "NONE", "UNKNOWN_DEADLINE"}:
        if "IMMEDIATE" in semantic_values:
            enriched["urgency"] = "IMMEDIATE"
        elif "TODAY" in semantic_values:
            enriched["urgency"] = "TODAY"
    if enriched.get("obligation") in {None, "UNKNOWN"} and "STRONG" in semantic_values:
        enriched["obligation"] = "REQUIRED"
    if enriched.get("directive_strength") in {None, "UNKNOWN"} and "STRONG" in semantic_values:
        enriched["directive_strength"] = "STRONG"
    if enriched.get("destination") in {None, "UNKNOWN"} and "CLAIMED_SAFE_ACCOUNT" in semantic_values:
        if "TRANSFER" in str(enriched.get("predicate") or "").upper():
            enriched["destination"] = "CLAIMED_SAFE_ACCOUNT"
    if enriched.get("amount_scope") in {None, "UNKNOWN"}:
        for value in ("ALL_FUNDS", "REMAINING_BALANCE", "PARTIAL_FUNDS", "HALF"):
            if value in semantic_values:
                enriched["amount_scope"] = value
                break
    return enriched


def context_code_matches_atom(code: str, atom: dict[str, Any]) -> bool:
    """Match a Context Feature code to an Atom without using source text."""
    normalized = str(code).upper()
    predicate = str(atom.get("predicate") or "").upper()
    if normalized == "PURPOSE_SAFE_ACCOUNT":
        return atom.get("destination") == "CLAIMED_SAFE_ACCOUNT" or atom.get("claimed_purpose") == "ASSET_PROTECTION" or predicate == "JUSTIFY_ASSET_PROTECTION"
    if normalized in {"TACTIC_URGENCY", "DEADLINE_TODAY", "DEADLINE_IMMEDIATE"}:
        return atom.get("urgency") not in {None, "NONE", "UNKNOWN_DEADLINE"} or any(str(term.get("normalized_code", "")).startswith("URGENCY.") for term in atom.get("observed_terms", []))
    if normalized in {"TACTIC_FEAR"}:
        return atom.get("fear_pressure") not in {None, "NONE"} or atom.get("threat_type") is not None
    if normalized in {"TACTIC_ISOLATION", "REQUEST_SECRECY"}:
        return atom.get("communication_control") is not None or atom.get("isolation_pressure") not in {None, "NONE"} or atom.get("secrecy_pressure") not in {None, "NONE"}
    if normalized in {"REQUEST_TRANSFER", "REQUEST_TRANSFER_FUNDS"}:
        return "TRANSFER" in predicate or predicate == "WITHDRAW_CASH"
    if normalized in {"REQUEST_AUTH_INFO", "AUTH_INFO"}:
        return atom.get("auth_secret_type") is not None or predicate.startswith("DISCLOSE_")
    if normalized in {"REQUEST_INSTALL_APP"}:
        return predicate in {"INSTALL_APP", "OPEN_URL", "SHARE_SCREEN"}
    if normalized in {"CLAIM_CRIME_INVOLVEMENT"}:
        return "CRIME" in predicate or atom.get("claimed_purpose") == "INVESTIGATION"
    if normalized.startswith("ROLE_"):
        return predicate in {"CLAIMS_ROLE", "CLAIMS_IDENTITY"} or atom.get("claimed_role") is not None
    return False


def attach_context_observation_lineage(features: Any, atoms: list[Any]) -> Any:
    """Attach privacy-safe Atom lineage to independent Context observations.

    Case-level observations keep normalized codes and Atom references only.
    Surface forms remain owned by the originating Semantic Atom so the same
    source term is not copied into several persistence layers.
    """
    if not getattr(features, "observations", None):
        return features

    atom_dicts = [atom.model_dump(mode="json") for atom in atoms]
    enriched_observations: list[dict[str, Any]] = []
    for observation in features.observations:
        item = dict(observation)
        code = str(item.get("code") or "")
        turn = int(item.get("turn") or 0)
        matching = [
            atom for atom in atom_dicts
            if atom.get("source_turn_id") == turn and context_code_matches_atom(code, atom)
        ]
        if matching:
            item["source_atom_ids"] = list(dict.fromkeys(
                str(atom["atom_id"]) for atom in matching if atom.get("atom_id")
            ))
            item["observed_lexical_codes"] = list(dict.fromkeys(
                str(term["normalized_code"])
                for atom in matching
                for term in atom.get("observed_terms", [])
                if term.get("normalized_code")
            ))
            semantic_features: dict[str, str] = {}
            for field in ("urgency", "directive_strength", "obligation", "destination", "amount_scope"):
                values = [str(atom[field]) for atom in matching if atom.get(field) not in {None, "NONE", "UNKNOWN"}]
                if values:
                    semantic_features[field] = values[0]
            pressure_by_code = {
                "TACTIC_URGENCY": "URGENCY",
                "TACTIC_FEAR": "FEAR",
                "TACTIC_ISOLATION": "ISOLATION",
                "REQUEST_SECRECY": "SECRECY",
            }
            if code in pressure_by_code:
                semantic_features["pressure_type"] = pressure_by_code[code]
            if semantic_features:
                item["semantic_features"] = semantic_features
        enriched_observations.append(item)
    return features.model_copy(update={"observations": enriched_observations})
