from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from ai_api.app.domains.diagnosis.quality_reviewer import review_narrative
from contracts.diagnosis import AnalysisEnvelope, ContextResult, StructuredTurn


def _client_with(payload: dict) -> Mock:
    client = Mock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.responses.create = AsyncMock(
        return_value=SimpleNamespace(output_text=json.dumps(payload), usage=SimpleNamespace(total_tokens=12))
    )
    return client


def test_narrative_review_returns_bounded_repair_instruction_without_source_text() -> None:
    client = _client_with(
        {
            "review_type": "NARRATIVE",
            "status": "WARN",
            "severity": "HIGH",
            "issue_codes": ["ACTOR_ROLE_MISMATCH"],
            "recommended_action": "RERENDER",
            "source_turns": [1],
        }
    )
    envelope = AnalysisEnvelope(
        source="DEMO_ADAPTER",
        turn_count=1,
        turns=[StructuredTurn(turn_id=1, sequence_index=1, speaker_confidence=0.9, normalized_summary="구조화된 발화")],
    )
    context = ContextResult(summary="구조화 요약", incident_type="PHISHING", confidence=0.8)
    with patch("ai_api.app.domains.diagnosis.quality_reviewer.AsyncOpenAI", return_value=client), patch.dict(
        "os.environ", {"OPENAI_API_KEY": "test-key", "QUALITY_REVIEW_MODE": "repair"}, clear=False
    ):
        result = asyncio.run(review_narrative(envelope, context))

    assert result is not None
    assert result.review_type == "NARRATIVE"
    assert result.recommended_action == "RERENDER"
    request = client.responses.create.await_args.kwargs["input"]
    assert "원문" not in request


def test_quality_review_is_disabled_without_provider_key() -> None:
    with patch.dict("os.environ", {"QUALITY_REVIEW_MODE": "repair"}, clear=True):
        result = asyncio.run(
            review_narrative(
                AnalysisEnvelope(
                    source="DEMO_ADAPTER",
                    turn_count=1,
                    turns=[StructuredTurn(turn_id=1, sequence_index=1, speaker_confidence=0.9, normalized_summary="구조화된 발화")],
                ),
                ContextResult(summary="요약", incident_type="test", confidence=0.5),
            )
        )
    assert result is None


def test_quality_review_provider_failure_degrades_to_human_review() -> None:
    client = Mock()
    client.__aenter__ = AsyncMock(side_effect=RuntimeError("provider unavailable"))
    with patch("ai_api.app.domains.diagnosis.quality_reviewer.AsyncOpenAI", return_value=client), patch.dict(
        "os.environ", {"OPENAI_API_KEY": "test-key", "QUALITY_REVIEW_MODE": "repair"}, clear=False
    ):
        result = asyncio.run(
            review_narrative(
                AnalysisEnvelope(
                    source="DEMO_ADAPTER",
                    turn_count=1,
                    turns=[StructuredTurn(turn_id=1, sequence_index=1, speaker_confidence=0.9, normalized_summary="구조화된 발화")],
                ),
                ContextResult(summary="요약", incident_type="test", confidence=0.5),
            )
        )
    assert result is not None
    assert result.status == "HUMAN_REVIEW"
    assert result.recommended_action == "HUMAN_REVIEW"
