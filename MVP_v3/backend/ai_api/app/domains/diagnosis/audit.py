"""Deterministic quality gate for privacy-safe Semantic Atom output."""

from __future__ import annotations

import re
from collections.abc import Mapping

from contracts.diagnosis import (
    ContextSignal,
    ExtractedEvent,
    SemanticAtom,
    SemanticAuditResult,
    SemanticRelation,
)

from .constants import PREDICATE_CODES
from .lexical_cues import extract_observed_terms
from .semantic_atoms import build_structure_coverage_report

_SENSITIVE_LITERAL = re.compile(r"(?:\d{4,}|\d{2,}[- ]\d{2,}|\b[A-Z]{2,}\s*\d{3,}\b)", re.IGNORECASE)


def _mixed_atom(atom: SemanticAtom) -> bool:
    predicate = atom.predicate
    if predicate not in PREDICATE_CODES:
        return True
    if predicate == "CLAIMS_ORGANIZATION" and atom.claimed_role is not None:
        return True
    if predicate == "CLAIMS_ROLE" and atom.claimed_organization is not None:
        return True
    action_predicates = {"TRANSFER_FUNDS", "WITHDRAW_CASH", "INSTALL_APP", "OPEN_URL", "SHARE_SCREEN"}
    if predicate in action_predicates and (atom.communication_control or atom.auth_secret_type):
        return True
    disclosure_predicates = {"DISCLOSE_OTP", "DISCLOSE_PASSWORD", "PROVIDE_CARD_INFO"}
    if predicate in disclosure_predicates and (atom.destination or atom.amount_value_krw is not None):
        return True
    return False


def audit_semantic_result(
    events: list[ExtractedEvent],
    atoms: list[SemanticAtom],
    relations: list[SemanticRelation] | None = None,
    signals: list[ContextSignal] | None = None,
    source_by_turn: Mapping[int, str] | None = None,
) -> SemanticAuditResult:
    """Audit structured output while keeping source text transient and unreturned."""
    source_by_turn = source_by_turn or {}
    coverage = build_structure_coverage_report(events, atoms, relations, signals)
    missing = [
        f"EVENT_NOT_COVERED:T{event.detected_at_turn}:{event.event_family}:{event.subtype or 'UNKNOWN'}"
        for event in events
        if not any(atom.source_turn_id == event.detected_at_turn for atom in atoms)
    ]
    invalid: list[str] = []
    mixed = [atom.atom_id for atom in atoms if _mixed_atom(atom)]
    privacy: list[str] = []
    unsupported: list[str] = []
    for atom in atoms:
        source = source_by_turn.get(atom.source_turn_id, "")
        expected = extract_observed_terms(source, atom.model_dump(mode="json")) if source else []
        expected_keys = {(term.surface_form, term.normalized_code) for term in expected}
        for term in atom.observed_terms:
            key = (term.surface_form, term.normalized_code)
            if _SENSITIVE_LITERAL.search(term.surface_form):
                privacy.append(f"{atom.atom_id}:SENSITIVE_LITERAL")
            if len(term.surface_form) > 16 or key not in expected_keys:
                unsupported.append(f"{atom.atom_id}:{term.normalized_code}")
        if atom.action_state == "VERIFIED" and atom.claim_status not in {"VERIFIED", "STAFF_REPORTED"}:
            invalid.append(f"{atom.atom_id}:VERIFIED_WITHOUT_VERIFIED_CLAIM")
        if atom.source_turn_id not in source_by_turn and atom.observed_terms:
            unsupported.append(f"{atom.atom_id}:SOURCE_NOT_AVAILABLE_FOR_OBSERVED_TERM_CHECK")

    atom_ids = {atom.atom_id for atom in atoms}
    orphan: list[str] = []
    for relation in relations or []:
        if relation.source_atom_id not in atom_ids or relation.target_atom_id not in atom_ids:
            orphan.append(relation.relation_id)
    for signal in signals or []:
        orphan.extend(
            f"{signal.signal_id}:{atom_id}"
            for atom_id in signal.atom_ids
            if atom_id not in atom_ids
        )

    event_coverage = float(coverage["event_coverage"])
    issue_count = len(invalid) + len(mixed) + len(privacy) + len(unsupported) + len(orphan)
    score = max(0.0, round(event_coverage - min(issue_count * 0.05, 0.5), 4))
    if privacy or mixed or orphan:
        status = "REEXTRACTION_REQUIRED"
        action = "TARGETED_REEXTRACTION"
    elif missing or invalid or unsupported or event_coverage < 1:
        status = "NEEDS_REVIEW"
        action = "HUMAN_REVIEW"
    else:
        status = "PASS"
        action = "NONE"
    return SemanticAuditResult(
        audit_status=status,
        overall_score=score,
        missing_features=missing,
        invalid_features=invalid,
        privacy_violations=sorted(set(privacy)),
        unsupported_terms=sorted(set(unsupported)),
        mixed_atoms=sorted(set(mixed)),
        orphan_references=sorted(set(orphan)),
        metrics={
            "event_coverage": event_coverage,
            "semantic_atom_count": float(coverage["semantic_atom_count"]),
            "observed_term_count": float(coverage["observed_term_count"]),
            "relation_count": float(coverage["relation_count"]),
            "context_signal_count": float(coverage["context_signal_count"]),
        },
        recommended_action=action,
    )
