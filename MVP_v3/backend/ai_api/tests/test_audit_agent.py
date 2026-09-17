import json
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch


from contracts.diagnosis import SemanticAuditResult
from ai_api.app.domains.diagnosis.audit_agent import review_semantic_audit


def test_llm_audit_review_returns_codes_and_allowed_turns_only() -> None:
    client = Mock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.responses.create = AsyncMock(return_value=SimpleNamespace(
        output_text=json.dumps({
            "schema_version": "semantic-audit-review.v1",
            "review_status": "REEXTRACTION_REQUIRED",
            "issue_codes": ["MISSING_AUTH_TYPE"],
            "missing_turns": [2, 99],
            "rationale_codes": ["ACTION_WITHOUT_AUTH_SLOT"],
        }),
        usage=SimpleNamespace(total_tokens=20),
    ))
    audit = SemanticAuditResult(audit_status="NEEDS_REVIEW", overall_score=0.8)
    with patch("ai_api.app.domains.diagnosis.audit_agent.AsyncOpenAI", return_value=client), \
         patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=False):
        result = asyncio.run(review_semantic_audit({1: "첫 턴", 2: "둘째 턴"}, [], audit))

    assert result is not None
    assert result.review_status == "REEXTRACTION_REQUIRED"
    assert result.missing_turns == [2]
    assert result.issue_codes == ["MISSING_AUTH_TYPE"]


def test_llm_audit_review_is_optional_when_provider_is_not_configured() -> None:
    with patch.dict("os.environ", {}, clear=True):
        result = asyncio.run(review_semantic_audit({}, [], SemanticAuditResult(audit_status="PASS", overall_score=1.0)))
    assert result is None
