"""Privacy-safe extraction and narrative quality reviewers."""

from __future__ import annotations

import json
import os
from typing import Any

from openai import AsyncOpenAI

from contracts.diagnosis import AnalysisEnvelope, ContextResult, QualityReview, SemanticAuditResult

from .budget import active_diagnosis_budget


def _mode() -> str:
    return os.getenv("QUALITY_REVIEW_MODE", "repair").strip().lower()


def max_retries() -> int:
    try:
        return max(0, min(int(os.getenv("QUALITY_REVIEW_MAX_RETRIES", "1")), 1))
    except ValueError:
        return 1


def max_loops() -> int:
    try:
        return max(0, min(int(os.getenv("QUALITY_REVIEW_MAX_LOOPS", "2")), 2))
    except ValueError:
        return 2


def _model() -> str:
    return os.getenv("OPENAI_AUDIT_MODEL", os.getenv("OPENAI_CONTEXT_MODEL", "gpt-5.6-luna"))


def _max_output_tokens() -> int:
    try:
        return max(256, min(int(os.getenv("QUALITY_REVIEW_MAX_OUTPUT_TOKENS", "900")), 2_000))
    except ValueError:
        return 900


async def _review(*, review_type: str, payload: dict[str, Any], instructions: str) -> QualityReview | None:
    if _mode() == "off" or not os.getenv("OPENAI_API_KEY"):
        return None
    request = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    budget = active_diagnosis_budget()
    max_output_tokens = _max_output_tokens()
    reservation = 0
    response = None
    try:
        reservation = budget.reserve(input_text=instructions + request, max_output_tokens=max_output_tokens)
        async with AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=20, max_retries=0) as client:
            response = await client.responses.create(
                model=_model(),
                instructions=instructions,
                input=request,
                max_output_tokens=max_output_tokens,
                text={"format": {"type": "json_schema", "name": f"{review_type.lower()}_quality_review_v1", "schema": QualityReview.model_json_schema(), "strict": True}},
            )
        budget.settle(reservation, response)
        review = QualityReview.model_validate_json(response.output_text)
        return review.model_copy(update={"review_type": review_type, "reviewer_model": _model()})
    except Exception:
        if reservation:
            budget.settle(reservation, response)
        return QualityReview(
            review_type=review_type,
            status="HUMAN_REVIEW",
            severity="HIGH",
            issue_codes=["QUALITY_REVIEW_UNAVAILABLE"],
            recommended_action="HUMAN_REVIEW",
            reviewer_model=_model(),
        )


async def review_extraction(envelope: AnalysisEnvelope, audit: SemanticAuditResult | None) -> QualityReview | None:
    """Review only structured envelope data; no raw transcript is sent."""
    instructions = (
        "You are a strict extraction quality reviewer for a fraud-response case. "
        "Review only structured metadata. Check speaker_role, actor_role, target_role, "
        "reported_by_role, amounts, deadlines, claim/request/action states, and lineage. "
        "Never invent facts or quote source text. Return only the prescribed JSON. "
        "Use REEXTRACT only for a concrete structural issue; otherwise ACCEPT or HUMAN_REVIEW."
    )
    return await _review(
        review_type="EXTRACTION",
        payload={"envelope": envelope.model_dump(mode="json"), "deterministic_audit": audit.model_dump(mode="json") if audit else None},
        instructions=instructions,
    )


async def review_narrative(envelope: AnalysisEnvelope, context: ContextResult) -> QualityReview | None:
    """Check staff-facing prose against structured facts without raw text."""
    instructions = (
        "You are a strict narrative grounding reviewer. Compare the staff-facing summary, "
        "claims, demands, tactics, next steps, and feature narratives with the structured "
        "events, atoms, mentions, relations, and context features. Detect reversed actors, "
        "wrong amounts or deadlines, omitted named entities, unsupported claims, and prose "
        "that could mislead a bank employee. Do not rewrite text; return issue codes and "
        "the prescribed JSON only. Use RERENDER for wording-only issues."
    )
    return await _review(
        review_type="NARRATIVE",
        payload={"envelope": envelope.model_dump(mode="json"), "context": context.model_dump(mode="json")},
        instructions=instructions,
    )
