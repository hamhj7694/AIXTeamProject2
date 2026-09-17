"""Deterministic, atom-grounded relation and signal construction."""

from __future__ import annotations

import hashlib

from contracts.diagnosis import ContextSignal, SemanticAtom, SemanticRelation


def _id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def build_semantic_relations(atoms: list[SemanticAtom]) -> list[SemanticRelation]:
    """Connect atoms only when a closed, non-text rule is satisfied."""

    relations: list[SemanticRelation] = []
    for source in atoms:
        for target in atoms:
            if source.atom_id == target.atom_id or source.source_turn_id != target.source_turn_id:
                continue
            relation_type: str | None = None
            if (
                source.predicate == "CLAIMS_ORGANIZATION"
                and target.predicate == "CLAIMS_ROLE"
                and source.claimed_organization is not None
                and target.claimed_role is not None
            ):
                relation_type = "SUPPORTS"
            elif (
                source.predicate == target.predicate
                and source.polarity != target.polarity
                and source.speaker != target.speaker
            ):
                relation_type = "CONTRADICTS"
            elif (
                source.threat_type is not None
                and target.action_state in {"REQUESTED", "INSTRUCTED", "PLANNED"}
            ):
                relation_type = "JUSTIFIES"
            elif (
                source.atom_class == "DISCLOSURE_REQUEST"
                and target.auth_secret_type is not None
            ):
                relation_type = "REQUIRES"
            elif (
                (source.urgency not in {None, "NONE"} or source.communication_control is not None)
                and target.action_state in {"REQUESTED", "INSTRUCTED", "PLANNED"}
            ):
                relation_type = "CAUSES"
            elif target.modality == "CONDITIONAL" and source.action_state in {"REQUESTED", "INSTRUCTED", "PLANNED"}:
                relation_type = "CONDITIONAL_ON"
            if relation_type is None:
                continue
            relation_id = _id(
                "REL", relation_type, source.atom_id, target.atom_id,
            )
            if any(item.relation_id == relation_id for item in relations):
                continue
            relations.append(SemanticRelation(
                relation_id=relation_id,
                relation_type=relation_type,  # type: ignore[arg-type]
                source_atom_id=source.atom_id,
                target_atom_id=target.atom_id,
                confidence=0.9 if relation_type == "SUPPORTS" else 0.8,
            ))
    return relations


def build_context_signals(atoms: list[SemanticAtom]) -> list[ContextSignal]:
    """Emit only a closed-pattern signal with all supporting atom IDs present."""

    turns = sorted({atom.source_turn_id for atom in atoms})
    signals: list[ContextSignal] = []
    for turn in turns:
        current = [atom for atom in atoms if atom.source_turn_id == turn]
        organization = next((a for a in current if a.predicate == "CLAIMS_ORGANIZATION"), None)
        roles = [a for a in current if a.predicate == "CLAIMS_ROLE"]
        transfer = next((a for a in current if a.predicate == "TRANSFER_FUNDS"), None)
        controls = [a for a in current if a.communication_control is not None]
        if organization is None or transfer is None or not controls:
            continue
        atom_ids = [organization.atom_id, *(a.atom_id for a in roles), transfer.atom_id, *(a.atom_id for a in controls)]
        signals.append(ContextSignal(
            signal_id=_id("SIG", "IMPERSONATION_TRANSFER_CONTROL", *atom_ids),
            signal_code="IMPERSONATION_TRANSFER_CONTROL_COMBINATION",
            atom_ids=atom_ids,
            severity="HIGH",
            confidence=0.9,
            claim_status="CALLER_CLAIM",
        ))
    return signals
