"""Versioned question identity; no semantic eligibility decisions live here."""
from dataclasses import dataclass
import re
from typing import Mapping, Sequence

from contracts.ai_internal.mvp_workflow import TargetField


@dataclass(frozen=True)
class QuestionTarget:
    canonical_scope: str
    parent_question_id: str | None = None

    @property
    def is_follow_up(self) -> bool:
        return self.parent_question_id is not None


def decode_follow_up_target(target: str) -> QuestionTarget:
    if not isinstance(target, str):
        raise ValueError("question target must be a string")
    if not target.strip().casefold().startswith("qf"):
        return QuestionTarget(target)
    if len(target) > 100:
        raise ValueError("invalid follow-up target length")
    parts = target.split(":")
    if len(parts) != 3 or parts[0] != "qf1":
        raise ValueError("unsupported or malformed follow-up target")
    scope, parent = parts[1:]
    TargetField(scope)
    # Repository normalization lowercases identifiers: reject lossy identities.
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", parent):
        raise ValueError("invalid follow-up parent id")
    return QuestionTarget(scope, parent)


def encode_follow_up_target(scope: str, parent_question_id: str) -> str:
    target = f"qf1:{scope}:{parent_question_id}"
    decode_follow_up_target(target)
    return target


def is_follow_up_target(target: str) -> bool:
    return decode_follow_up_target(target).is_follow_up


def canonical_question_scope(target: str) -> str:
    return decode_follow_up_target(target).canonical_scope


def follow_up_registration_allowed(target: str, text: str, history: Sequence[Mapping]) -> bool:
    """Structural invariants, checked under the repository's Case writer lock."""
    decoded = decode_follow_up_target(target)
    if not decoded.is_follow_up:
        raise ValueError("a follow-up target is required")
    parent = next((q for q in history if q["question_id"] == decoded.parent_question_id), None)
    if parent is None or parent["status"] != "ANSWERED":
        return False
    parent_target = decode_follow_up_target(parent["target_field"])
    if parent_target.is_follow_up or parent_target.canonical_scope != decoded.canonical_scope:
        return False
    text_key = " ".join(text.split()).casefold()
    for question in history:
        existing = decode_follow_up_target(question["target_field"])
        if existing.parent_question_id == decoded.parent_question_id:
            return False
        if existing.canonical_scope == decoded.canonical_scope and question["status"] in {"PENDING", "ASKED"}:
            return False
        if " ".join(question["question_text"].split()).casefold() == text_key:
            return False
    return True
