"""Additive Semantic Atom projection for the v3.1 diagnosis pipeline."""

from __future__ import annotations

import hashlib

from contracts.diagnosis import ContextSignal, ExtractedEvent, SemanticAtom, SemanticRelation

from .lexical_cues import enrich_atom_payload


def _fingerprint(*parts: str) -> str:
    return "sha256:" + hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _atom_class(event: ExtractedEvent) -> str:
    return {
        "IMPERSONATION": "ORGANIZATION_CLAIM",
        "MONEY_MOVEMENT": "FINANCIAL_ACTION",
        "ACTION_REQUEST": "ACTION_REQUEST",
        "AMOUNT": "STATE_CLAIM",
    }.get(event.event_family, "EVENT_CLAIM")


def _predicate(event: ExtractedEvent) -> str:
    if event.event_family == "MONEY_MOVEMENT":
        return {
            "TRANSFER": "TRANSFER_FUNDS",
            "WITHDRAWAL": "WITHDRAW_CASH",
        }.get(event.subtype or "", "OTHER")
    if event.event_family == "IMPERSONATION":
        return "CLAIMS_ORGANIZATION"
    return "OTHER"


def _claimed_organization(event: ExtractedEvent) -> str | None:
    if event.event_family != "IMPERSONATION":
        return None
    return {
        "PROSECUTION": "PROSECUTION_SERVICE",
        "POLICE": "POLICE_SERVICE",
        "FSS": "FINANCIAL_SUPERVISORY_SERVICE",
        "COURT": "COURT",
        "BANK": "BANK",
        "CARD_COMPANY": "CARD_COMPANY",
        "LOAN_COMPANY": "LOAN_COMPANY",
        "TELECOM": "TELECOM_COMPANY",
        "DELIVERY": "DELIVERY_COMPANY",
    }.get(event.subtype or "", "UNKNOWN")


def build_semantic_atoms(events: list[ExtractedEvent]) -> list[SemanticAtom]:
    """Create deterministic, non-text atoms while preserving event lineage."""

    atoms: list[SemanticAtom] = []
    ordered = sorted(events, key=lambda item: (item.detected_at_turn, item.event_family, item.subtype or ""))
    for index, event in enumerate(ordered, start=1):
        subtype = event.subtype or event.event_family
        subject = "CUSTOMER_ACCOUNT" if event.event_family == "MONEY_MOVEMENT" else None
        predicate = _predicate(event)
        requested = event.is_requested is not False and event.event_family in {"ACTION_REQUEST", "MONEY_MOVEMENT"}
        is_urgent = event.event_family == "PSY_STRATEGY" and event.subtype == "URGENCY"
        is_fear = event.event_family == "PSY_STRATEGY" and event.subtype == "FEAR"
        is_isolation = event.event_family == "PSY_STRATEGY" and event.subtype == "ISOLATION"
        is_auth = event.event_family == "ACTION_REQUEST" and event.subtype == "AUTH_INFO"
        is_contact_control = event.event_family == "ACTION_REQUEST" and event.subtype == "CONTACT_RESTRICTION"
        payload = dict(
            atom_id=f"ATM-{event.detected_at_turn:04d}-{index:04d}",
            atom_class=_atom_class(event),
            # Event extraction is the demo adapter's anti-fraud signal stream:
            # an impersonation, pressure tactic, requested action, or money
            # movement is spoken by the suspected party unless an upstream
            # structured atom explicitly says otherwise.  The old fallback
            # used CUSTOMER for money events, which made a request such as
            # "send the money" read as if the customer had initiated it.
            speaker="CALLER",
            subject=subject,
            predicate=predicate,
            actor="CALLER" if event.event_family in {
                "IMPERSONATION", "PSY_STRATEGY", "ACTION_REQUEST", "MONEY_MOVEMENT",
            } else None,
            target="CUSTOMER" if event.event_family in {
                "IMPERSONATION", "PSY_STRATEGY", "ACTION_REQUEST", "MONEY_MOVEMENT",
            } else None,
            destination="CLAIMED_SAFE_ACCOUNT" if event.event_family == "MONEY_MOVEMENT" else None,
            action_state="REQUESTED" if requested else None,
            modality="DIRECTIVE" if requested else "ASSERTION",
            claim_status="CALLER_CLAIM" if event.event_family in {"IMPERSONATION", "PSY_STRATEGY"} else "UNVERIFIED",
            lexical_cues=[subtype],
            speech_act="DIRECTIVE" if requested or is_contact_control else "ASSERTION",
            directive_strength="STRONG" if requested else None,
            obligation="REQUIRED" if requested else None,
            urgency="IMMEDIATE" if is_urgent else None,
            authority_pressure="HIGH" if event.event_family == "IMPERSONATION" else None,
            fear_pressure="HIGH" if is_fear else None,
            isolation_pressure="HIGH" if is_isolation or is_contact_control else None,
            communication_control="NO_EXTERNAL_CONTACT" if is_contact_control else None,
            auth_secret_type="UNKNOWN" if is_auth else None,
            financial_pressure="HIGH" if event.event_family == "MONEY_MOVEMENT" else None,
            amount_scope="EXPLICIT_AMOUNT" if event.amount_krw is not None else None,
            amount_value_krw=event.amount_krw,
            amount_role=(
                "REQUESTED_AMOUNT" if event.is_requested is True else
                "CLAIMED_LOSS" if event.event_family == "AMOUNT" and event.is_requested is False else
                "TRANSFER_OUT" if event.event_family == "MONEY_MOVEMENT" else None
            ),
            amount_direction=(
                "REQUEST" if event.is_requested is True else
                "IN" if event.event_family == "AMOUNT" and event.is_requested is False else
                "OUT" if event.event_family == "MONEY_MOVEMENT" else None
            ),
            amount_event_id=f"AMT-{event.detected_at_turn:04d}-{index:04d}" if event.amount_krw is not None else None,
            claimed_organization=_claimed_organization(event),
            source_event_id=f"EVT-{event.detected_at_turn:04d}-{index:04d}",
            source_turn_id=event.detected_at_turn,
            semantic_fingerprint=_fingerprint(
                str(event.detected_at_turn), event.event_family, subtype,
                subject or "", predicate, "POSITIVE",
            ),
        )
        # Evidence text is used only during deterministic extraction.  The
        # enriched payload contains short, source-verified cues and no source
        # text itself.
        atoms.append(SemanticAtom.model_validate(enrich_atom_payload(event.evidence_text, payload)))
    return atoms


def _event_is_covered(event: ExtractedEvent, atoms: list[SemanticAtom]) -> bool:
    turn_atoms = [atom for atom in atoms if atom.source_turn_id == event.detected_at_turn]
    if event.event_family == "IMPERSONATION":
        organization = _claimed_organization(event)
        return any(
            atom.predicate == "CLAIMS_ORGANIZATION"
            and atom.claimed_organization in {organization, "UNKNOWN"}
            for atom in turn_atoms
        )
    if event.event_family == "MONEY_MOVEMENT":
        return any(atom.predicate == _predicate(event) for atom in turn_atoms)
    if event.event_family == "ACTION_REQUEST":
        if event.subtype == "AUTH_INFO":
            return any(atom.auth_secret_type is not None for atom in turn_atoms)
        if event.subtype == "CONTACT_RESTRICTION":
            return any(atom.communication_control is not None for atom in turn_atoms)
        if event.subtype == "SENSITIVE_INFO":
            return any(atom.atom_class == "DISCLOSURE_REQUEST" for atom in turn_atoms)
        return any(atom.atom_class in {"ACTION_REQUEST", "ACTION_INSTRUCTION"} for atom in turn_atoms)
    if event.event_family == "PSY_STRATEGY":
        if event.subtype == "URGENCY":
            return any(atom.urgency not in {None, "NONE"} for atom in turn_atoms)
        if event.subtype == "FEAR":
            return any(
                atom.fear_pressure not in {None, "NONE"} or atom.threat_type is not None
                for atom in turn_atoms
            )
        if event.subtype == "ISOLATION":
            return any(
                atom.isolation_pressure not in {None, "NONE"}
                or atom.secrecy_pressure not in {None, "NONE"}
                or atom.communication_control is not None
                for atom in turn_atoms
            )
    if event.event_family == "AMOUNT":
        return any(
            atom.amount_value_krw == event.amount_krw
            for atom in turn_atoms
            if event.amount_krw is not None
        )
    return bool(turn_atoms)


def merge_semantic_atoms(
    llm_atoms: list[SemanticAtom], events: list[ExtractedEvent],
) -> list[SemanticAtom]:
    """Keep detailed LLM atoms and fill only uncovered critical event signals."""

    merged = list(llm_atoms)
    uncovered_events = [event for event in events if not _event_is_covered(event, merged)]
    if not uncovered_events:
        return merged

    existing_fingerprints = {atom.semantic_fingerprint for atom in merged}
    for atom in build_semantic_atoms(uncovered_events):
        if atom.semantic_fingerprint not in existing_fingerprints:
            merged.append(atom)
            existing_fingerprints.add(atom.semantic_fingerprint)
    return merged


def build_structure_coverage_report(
    events: list[ExtractedEvent],
    atoms: list[SemanticAtom],
    relations: list[SemanticRelation] | None = None,
    signals: list[ContextSignal] | None = None,
) -> dict[str, object]:
    """Return privacy-safe counts showing how far fine-grained extraction reached."""
    covered_events = sum(_event_is_covered(event, atoms) for event in events)
    atom_predicates = sorted({atom.predicate for atom in atoms})
    observed_term_codes = sorted({
        term.normalized_code for atom in atoms for term in atom.observed_terms
    })
    return {
        "schema_version": "semantic-coverage.v1",
        "event_count": len(events),
        "covered_event_count": covered_events,
        "event_coverage": round(covered_events / len(events), 4) if events else 1.0,
        "semantic_atom_count": len(atoms),
        "semantic_predicate_count": len(atom_predicates),
        "semantic_predicates": atom_predicates,
        "observed_term_count": sum(len(atom.observed_terms) for atom in atoms),
        "observed_lexical_codes": observed_term_codes,
        "relation_count": len(relations or []),
        "context_signal_count": len(signals or []),
    }
