"""LLM review and targeted re-extraction helpers for the audit gate."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping

from openai import AsyncOpenAI

from contracts.diagnosis import SemanticAtom, SemanticAuditReview

from .audit import audit_semantic_result
from .budget import active_diagnosis_budget
from .extractor import extract_events

_REVIEW_SCHEMA = SemanticAuditReview.model_json_schema()


async def review_semantic_audit(
    source_by_turn: Mapping[int, str],
    atoms: list[SemanticAtom],
    deterministic_audit: object,
) -> SemanticAuditReview | None:
    """Ask an LLM to review structured findings; source remains transient."""
    if not os.getenv("OPENAI_API_KEY"):
        return None
    payload = {
        "turns": [{"turn": turn, "text": text} for turn, text in sorted(source_by_turn.items())],
        "atoms": [atom.model_dump(mode="json") for atom in atoms],
        "deterministic_audit": deterministic_audit.model_dump(mode="json"),
    }
    instructions = (
        "You are a strict reviewer of a semantic feature extraction. "
        "Return only issue codes and turn numbers, never quote or reproduce source text. "
        "Check missing independently reviewable atoms, mixed predicates, action state, "
        "amounts, authentication type, and unsupported lexical cues. "
        "Do not invent terms absent from the source."
    )
    budget = active_diagnosis_budget()
    request = json.dumps(payload, ensure_ascii=False)
    reservation = budget.reserve(input_text=instructions + request, max_output_tokens=700)
    try:
        async with AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=20, max_retries=0) as client:
            response = await client.responses.create(
                model=os.getenv("OPENAI_AUDIT_MODEL", os.getenv("OPENAI_CONTEXT_MODEL", "gpt-4o-mini")),
                instructions=instructions,
                input=request,
                max_output_tokens=700,
                text={"format": {"type": "json_schema", "name": "semantic_audit_review_v1", "schema": _REVIEW_SCHEMA, "strict": True}},
            )
        budget.settle(reservation, response)
        review = SemanticAuditReview.model_validate_json(response.output_text)
    except Exception:
        budget.settle(reservation, locals().get("response"))
        return None
    review.missing_turns = sorted({turn for turn in review.missing_turns if turn in source_by_turn})
    return review


async def targeted_reextract_turns(
    source_by_turn: Mapping[int, str], turn_ids: list[int],
) -> list[SemanticAtom]:
    """Re-run extraction only for selected turns and remap transient turn lineage."""
    recovered: list[SemanticAtom] = []
    for turn_id in sorted(set(turn_ids)):
        source = source_by_turn.get(turn_id)
        if not source:
            continue
        extraction = await extract_events(source)
        for index, atom in enumerate(extraction.semantic_atoms, start=1):
            recovered.append(atom.model_copy(update={
                "atom_id": f"ATM-{turn_id:04d}-RETRY-{index:04d}",
                "source_event_id": f"EVT-{turn_id:04d}-RETRY-{index:04d}",
                "source_turn_id": turn_id,
            }))
    return recovered
