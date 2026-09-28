"""Conservative cross-turn resolution for STT name variants.

STT can turn one spoken name into near-identical strings (for example,
``김민수`` and ``김인수``).  The extractor is intentionally turn-local, so
this module performs a small, deterministic pass after extraction.  It only
merges short Korean person-name candidates when the surrounding semantic
context supports the merge; otherwise both names are preserved for review.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import re
import unicodedata
from typing import Callable

from contracts.diagnosis import SemanticAtom, SemanticMention


_HANGUL_NAME = re.compile(r"^[\uAC00-\uD7A3]{2,5}$")
_NAME_FIELDS = ("claimed_person_name", "vocative_target")
_CONTEXT_FIELDS = (
    "claimed_organization_name",
    "claimed_branch_name",
    "claimed_role_name",
    "claimed_role",
    "claimed_relationship",
    "actor_role",
    "speaker_role",
)


def _name_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(value or "")).strip()
    return re.sub(r"\s+", "", normalized)


def _is_person_name(value: str) -> bool:
    return bool(_HANGUL_NAME.fullmatch(_name_key(value)))


def _edit_distance(left: str, right: str) -> int:
    if left == right:
        return 0
    previous = list(range(len(right) + 1))
    for row, left_char in enumerate(left, start=1):
        current = [row]
        for column, right_char in enumerate(right, start=1):
            current.append(min(
                current[-1] + 1,
                previous[column] + 1,
                previous[column - 1] + (left_char != right_char),
            ))
        previous = current
    return previous[-1]


def _context(atom: SemanticAtom) -> set[str]:
    return {
        _name_key(getattr(atom, field, ""))
        for field in _CONTEXT_FIELDS
        if _name_key(getattr(atom, field, ""))
    }


def _union_find(keys: list[str]) -> tuple[dict[str, str], tuple[Callable[[str], str], Callable[[str, str], None]]]:
    parent = {key: key for key in keys}

    def find(value: str) -> str:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(left: str, right: str) -> None:
        root_left, root_right = find(left), find(right)
        if root_left != root_right:
            parent[root_right] = root_left

    return parent, (find, union)


def resolve_person_name_aliases(
    atoms: list[SemanticAtom],
) -> tuple[list[SemanticAtom], dict[str, str]]:
    """Return atoms with only strongly supported name aliases canonicalized.

    A pair is eligible only when it is the same-length Hangul name, differs by
    one syllable, does not occur in the same turn, and shares a role,
    relationship, institution, or nearby speaker context.  This prevents two
    genuinely different people mentioned together from being collapsed.
    """

    occurrences: dict[str, list[tuple[int, int, set[str], float]]] = defaultdict(list)
    display_values: dict[str, list[str]] = defaultdict(list)
    for index, atom in enumerate(atoms):
        context = _context(atom)
        confidence = float(atom.attribution_confidence or atom.speaker_confidence or 0.0)
        for field in _NAME_FIELDS:
            raw = str(getattr(atom, field, "") or "").strip()
            key = _name_key(raw)
            if not raw or not _is_person_name(raw):
                continue
            occurrences[key].append((atom.source_turn_id, index, context, confidence))
            display_values[key].append(raw)

    keys = sorted(occurrences)
    if len(keys) < 2:
        return atoms, {}

    parent, (find, union) = _union_find(keys)
    for index, left in enumerate(keys):
        for right in keys[index + 1:]:
            if len(left) != len(right) or left[0] != right[0] or _edit_distance(left, right) != 1:
                continue
            left_items, right_items = occurrences[left], occurrences[right]
            # If both names are explicitly present in one turn, retain both;
            # that is stronger evidence for two people than for an STT typo.
            if {item[0] for item in left_items} & {item[0] for item in right_items}:
                continue
            shared_context = any(item[2] & other[2] for item in left_items for other in right_items)
            nearby_same_role = any(
                abs(item[0] - other[0]) <= 3
                and item[2].intersection({"SUSPECTED_PARTY", "CUSTOMER", "BANK_STAFF"})
                and item[2].intersection({"SUSPECTED_PARTY", "CUSTOMER", "BANK_STAFF"})
                == other[2].intersection({"SUSPECTED_PARTY", "CUSTOMER", "BANK_STAFF"})
                for item in left_items for other in right_items
            )
            if shared_context or nearby_same_role:
                union(left, right)

    groups: dict[str, list[str]] = defaultdict(list)
    for key in keys:
        groups[find(key)].append(key)

    aliases: dict[str, str] = {}
    for members in groups.values():
        if len(members) < 2:
            continue
        ranked = sorted(
            members,
            key=lambda key: (
                -len(occurrences[key]),
                -sum(item[3] for item in occurrences[key]),
                min(item[0] for item in occurrences[key]),
                key,
            ),
        )
        canonical_key = ranked[0]
        canonical_display = Counter(display_values[canonical_key]).most_common(1)[0][0]
        for member in members:
            if member != canonical_key:
                aliases[member] = canonical_display

    if not aliases:
        return atoms, {}

    def replace(value: str | None) -> str | None:
        if not value:
            return value
        return aliases.get(_name_key(value), value)

    resolved = [atom.model_copy(update={
        "claimed_person_name": replace(atom.claimed_person_name),
        "vocative_target": replace(atom.vocative_target),
    }) for atom in atoms]
    return resolved, aliases


def apply_person_name_aliases_to_mentions(
    mentions: list[SemanticMention], aliases: dict[str, str],
) -> list[SemanticMention]:
    """Keep the persisted mention index aligned with canonicalized atoms."""
    if not aliases:
        return mentions
    return [
        mention.model_copy(update={
            "normalized_value": aliases.get(_name_key(mention.normalized_value), mention.normalized_value),
        })
        if mention.normalized_code in {"CLAIMED_PERSON_NAME", "VOCATIVE_TARGET"}
        else mention
        for mention in mentions
    ]
