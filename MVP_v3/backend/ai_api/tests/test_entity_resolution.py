from contracts.diagnosis import SemanticAtom, SemanticMention

from ai_api.app.domains.diagnosis.entity_resolution import (
    apply_person_name_aliases_to_mentions,
    resolve_person_name_aliases,
)


def _atom(atom_id: str, name: str, turn: int, *, role: str = "SUSPECTED_PARTY") -> SemanticAtom:
    return SemanticAtom(
        atom_id=atom_id,
        atom_class="ORGANIZATION_CLAIM",
        speaker="CALLER",
        predicate="CLAIMS_ROLE",
        claimed_person_name=name,
        claimed_role_name="수사관",
        speaker_role=role,
        actor_role=role,
        target_role="CUSTOMER",
        source_turn_id=turn,
        semantic_fingerprint=f"fp-{atom_id}",
        attribution_confidence=0.9,
    )


def test_nearby_stt_name_variant_is_canonicalized_when_context_matches() -> None:
    atoms = [
        _atom("a1", "김민수", 1),
        _atom("a2", "김인수", 2),
        _atom("a3", "김민수", 4),
    ]

    resolved, aliases = resolve_person_name_aliases(atoms)

    assert aliases == {"김인수": "김민수"}
    assert [atom.claimed_person_name for atom in resolved] == ["김민수", "김민수", "김민수"]


def test_names_mentioned_in_same_turn_are_not_collapsed() -> None:
    atoms = [_atom("a1", "김민수", 1), _atom("a2", "김인수", 1)]

    resolved, aliases = resolve_person_name_aliases(atoms)

    assert aliases == {}
    assert [atom.claimed_person_name for atom in resolved] == ["김민수", "김인수"]


def test_distant_names_without_shared_context_are_preserved() -> None:
    first = _atom("a1", "김민수", 1)
    second = _atom("a2", "김인수", 12)
    second = second.model_copy(update={"claimed_role_name": None, "actor_role": "UNKNOWN", "speaker_role": "UNKNOWN"})

    resolved, aliases = resolve_person_name_aliases([first, second])

    assert aliases == {}
    assert [atom.claimed_person_name for atom in resolved] == ["김민수", "김인수"]


def test_mentions_follow_the_canonical_name() -> None:
    atoms = [_atom("a1", "김민수", 1), _atom("a2", "김인수", 2)]
    _, aliases = resolve_person_name_aliases(atoms)
    mentions = [
        SemanticMention(
            mention_id="m1", normalized_code="CLAIMED_PERSON_NAME",
            normalized_value="김인수", mention_type="PERSON_NAME",
            source_turn_id=2, sequence_index=1, first_turn_id=2, last_turn_id=2,
            confidence=0.9,
        ),
    ]

    updated = apply_person_name_aliases_to_mentions(mentions, aliases)

    assert updated[0].normalized_value == "김민수"
