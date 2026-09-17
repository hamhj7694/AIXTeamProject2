"""Build privacy-safe episode, action and entity indexes from Semantic Atoms."""

from __future__ import annotations

import hashlib
from collections import defaultdict

from contracts.diagnosis import ActionGroup, ConversationEpisode, EntityReference, SemanticAtom


def _id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def build_conversation_episodes(atoms: list[SemanticAtom]) -> list[ConversationEpisode]:
    """Group nearby atoms by turn; no cross-turn inference is performed."""
    by_turn: dict[int, list[SemanticAtom]] = defaultdict(list)
    for atom in atoms:
        by_turn[atom.source_turn_id].append(atom)
    episodes: list[ConversationEpisode] = []
    for turn in sorted(by_turn):
        current = by_turn[turn]
        classes = {atom.atom_class for atom in current}
        if any(atom.predicate.startswith("CLAIMS_") for atom in current):
            episode_type = "IDENTITY_CLAIM"
        elif any(atom.communication_control or atom.urgency for atom in current):
            episode_type = "PRESSURE"
        elif any(atom.action_state for atom in current):
            episode_type = "ACTION"
        else:
            episode_type = "MIXED" if len(classes) > 1 else "OTHER"
        atom_ids = [atom.atom_id for atom in current]
        episodes.append(ConversationEpisode(
            episode_id=_id("EPI", str(turn), *atom_ids),
            start_turn=turn, end_turn=turn, atom_ids=atom_ids,
            episode_type=episode_type,
        ))
    return episodes


def build_action_groups(atoms: list[SemanticAtom]) -> list[ActionGroup]:
    """Group only identical predicates; action state remains a set."""
    grouped: dict[str, list[SemanticAtom]] = defaultdict(list)
    for atom in atoms:
        if atom.action_state is not None:
            grouped[atom.predicate].append(atom)
    groups: list[ActionGroup] = []
    for predicate, members in sorted(grouped.items()):
        groups.append(ActionGroup(
            group_id=_id("ACT", predicate, *(atom.atom_id for atom in members)),
            action_predicate=predicate,
            atom_ids=[atom.atom_id for atom in members],
            action_states=list(dict.fromkeys(atom.action_state for atom in members if atom.action_state)),
            target_codes=list(dict.fromkeys(atom.target for atom in members if atom.target)),
        ))
    return groups


def build_entity_registry(atoms: list[SemanticAtom]) -> list[EntityReference]:
    """Index explicit entity codes; never resolve free-text coreference."""
    grouped: dict[str, list[SemanticAtom]] = defaultdict(list)
    for atom in atoms:
        for code in (atom.subject, atom.actor, atom.target, atom.destination):
            if code:
                grouped[code].append(atom)
    registry: list[EntityReference] = []
    for code, members in sorted(grouped.items()):
        roles = [role for atom in members for role in (
            "subject" if atom.subject == code else "",
            "actor" if atom.actor == code else "",
            "target" if atom.target == code else "",
            "destination" if atom.destination == code else "",
        ) if role]
        registry.append(EntityReference(
            entity_id=_id("ENT", code), entity_code=code,
            mention_roles=list(dict.fromkeys(roles)),
            atom_ids=list(dict.fromkeys(atom.atom_id for atom in members)),
            source_turn_ids=list(dict.fromkeys(atom.source_turn_id for atom in members)),
        ))
    return registry
