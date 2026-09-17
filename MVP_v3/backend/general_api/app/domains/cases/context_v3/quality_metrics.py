"""Privacy-safe quality metrics for Atom -> Fact -> staff sentence projection."""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .grounded import grounded_fact_item, validate_grounded_fact


_SLOT_FIELDS = (
    "atom_class", "predicate", "speaker", "subject", "actor", "target", "object",
    "action_state", "modality", "polarity", "claim_status", "destination", "amount_scope",
    "claimed_purpose", "threat_type", "repetition_pressure",
)


def _atom_ids(fact: Any) -> set[str]:
    return {
        str(ref.get("id") if isinstance(ref, dict) else ref.id)
        for ref in (fact.evidence_refs or [])
        if str(ref.get("type") if isinstance(ref, dict) else ref.type) == "STRUCTURED_ATOM"
    }


def _stored_slot(value: dict[str, Any], field: str) -> Any:
    """Read scalar slots and the expression feature group consistently."""
    if field in value:
        return value[field]
    return (value.get("expression_features") or {}).get(field)


def find_slot_preservation_violations(
    atoms: Iterable[dict[str, Any]], facts: Iterable[Any],
) -> list[str]:
    """Return privacy-safe ``atom_id:slot`` identifiers that were dropped."""
    atom_by_id = {str(atom.get("atom_id")): atom for atom in atoms if atom.get("atom_id")}
    violations: list[str] = []
    for fact in facts:
        value = fact.value or {}
        for atom_id in _atom_ids(fact):
            atom = atom_by_id.get(atom_id)
            if not atom:
                continue
            for field in _SLOT_FIELDS:
                expected = atom.get(field)
                if expected is not None and _stored_slot(value, field) != expected:
                    violations.append(f"{atom_id}:{field}")
    return sorted(set(violations))


def build_projection_quality_metrics(
    atoms: Iterable[dict[str, Any]], facts: Iterable[Any], context: dict[str, Any] | None = None,
) -> dict[str, float]:
    """Measure loss/expansion without returning source text or lexical literals."""
    atom_rows = list(atoms)
    fact_rows = list(facts)
    atom_by_id = {str(atom.get("atom_id")): atom for atom in atom_rows if atom.get("atom_id")}
    represented = set().union(*(_atom_ids(fact) for fact in fact_rows)) if fact_rows else set()
    represented &= set(atom_by_id)
    slot_total = 0
    slot_preserved = 0
    unsupported_lexicalizations = 0
    lexical_total = 0
    broadening_failures = 0
    for fact in fact_rows:
        for atom_id in _atom_ids(fact):
            atom = atom_by_id.get(atom_id)
            if not atom:
                continue
            value = fact.value or {}
            for field in _SLOT_FIELDS:
                if atom.get(field) is not None:
                    slot_total += 1
                    slot_preserved += int(_stored_slot(value, field) == atom.get(field))
            atom_codes = {
                str(term.get("normalized_code"))
                for term in atom.get("observed_terms", []) or []
                if term.get("normalized_code")
            }
            for code in value.get("observed_lexical_codes", []) or []:
                lexical_total += 1
                unsupported_lexicalizations += int(str(code) not in atom_codes)
        try:
            plan = grounded_fact_item(fact, context)
            validate_grounded_fact(fact, plan["text"], context)
        except ValueError:
            broadening_failures += 1
    atom_count = len(atom_by_id)
    fact_count = len(fact_rows)
    return {
        "atom_count": float(atom_count),
        "fact_count": float(fact_count),
        "semantic_slot_preservation_rate": round(slot_preserved / slot_total, 4) if slot_total else 1.0,
        "aggregation_loss_rate": round(1 - len(represented) / atom_count, 4) if atom_count else 0.0,
        "semantic_broadening_rate": round(broadening_failures / fact_count, 4) if fact_count else 0.0,
        "unsupported_lexicalization_rate": round(unsupported_lexicalizations / lexical_total, 4) if lexical_total else 0.0,
    }
