"""Shared, frontend-compatible AI runtime error vocabulary.

The existing public error codes remain valid. New callers should prefer the
stable codes below; legacy codes can be carried in ``legacy_code`` during the
transition without exposing provider details.
"""

from typing import Literal

from pydantic import BaseModel, Field

AiRuntimeErrorCode = Literal[
    "AI_PROVIDER_UNAVAILABLE",
    "AI_PROVIDER_TIMEOUT",
    "AI_PROVIDER_RATE_LIMITED",
    "AI_PROVIDER_AUTH_ERROR",
    "AI_INVALID_RESPONSE",
    "AI_CONTRACT_VIOLATION",
    "AI_SERVICE_UNAVAILABLE",
]


class PublicAiRuntimeError(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    message: str = Field(min_length=1, max_length=500)
    retryable: bool = False
    legacy_code: str | None = None


def runtime_error(
    code: AiRuntimeErrorCode,
    message: str,
    *,
    retryable: bool,
    legacy_code: str | None = None,
) -> dict[str, object]:
    return PublicAiRuntimeError(
        code=code, message=message, retryable=retryable, legacy_code=legacy_code
    ).model_dump(exclude_none=True)

