from __future__ import annotations

import math
import os
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Iterator


class DiagnosisBudgetExceededError(RuntimeError):
    """Raised before an LLM request would exceed the per-diagnosis safety budget."""


def _positive_env_int(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return value if value > 0 else default


@dataclass
class DiagnosisLlmBudget:
    max_calls: int
    max_total_tokens: int
    max_turns: int
    max_input_chars: int
    calls: int = 0
    reserved_tokens: int = 0
    used_tokens: int = 0

    @classmethod
    def from_environment(cls) -> "DiagnosisLlmBudget":
        return cls(
            max_calls=_positive_env_int("OPENAI_MAX_CALLS_PER_DIAGNOSIS", 31),
            max_total_tokens=_positive_env_int("OPENAI_MAX_TOTAL_TOKENS_PER_DIAGNOSIS", 16000),
            max_turns=_positive_env_int("DIAGNOSIS_MAX_TURNS", 30),
            max_input_chars=_positive_env_int("DIAGNOSIS_MAX_INPUT_CHARS", 6000),
        )

    def validate_input(self, *, text: str, turn_count: int) -> None:
        if len(text) > self.max_input_chars:
            raise DiagnosisBudgetExceededError(
                f"입력이 너무 깁니다. 한 번에 최대 {self.max_input_chars:,}자까지 분석할 수 있습니다."
            )
        if turn_count > self.max_turns:
            raise DiagnosisBudgetExceededError(
                f"문장이 너무 많습니다. 한 번에 최대 {self.max_turns}문장까지 분석할 수 있습니다."
            )

    def reserve(self, *, input_text: str, max_output_tokens: int) -> int:
        if self.calls >= self.max_calls:
            raise DiagnosisBudgetExceededError(
                f"AI 분석 호출 한도({self.max_calls}회)에 도달했습니다. 텍스트를 나누어 다시 분석해 주세요."
            )
        # Korean text is conservatively estimated at two characters per token.
        estimate = math.ceil(len(input_text) / 2) + max_output_tokens
        if self.used_tokens + self.reserved_tokens + estimate > self.max_total_tokens:
            raise DiagnosisBudgetExceededError(
                f"이번 분석의 AI 토큰 예산({self.max_total_tokens:,} tokens)을 초과할 수 있습니다. 텍스트를 나누어 다시 분석해 주세요."
            )
        self.calls += 1
        self.reserved_tokens += estimate
        return estimate

    def settle(self, reservation: int, response: object) -> None:
        self.reserved_tokens = max(0, self.reserved_tokens - reservation)
        usage = getattr(response, "usage", None)
        actual = getattr(usage, "total_tokens", None)
        self.used_tokens += int(actual) if isinstance(actual, int) and actual >= 0 else reservation


_active_budget: ContextVar[DiagnosisLlmBudget | None] = ContextVar("diagnosis_llm_budget", default=None)


@contextmanager
def diagnosis_budget_scope() -> Iterator[DiagnosisLlmBudget]:
    budget = DiagnosisLlmBudget.from_environment()
    token = _active_budget.set(budget)
    try:
        yield budget
    finally:
        _active_budget.reset(token)


def active_diagnosis_budget() -> DiagnosisLlmBudget:
    budget = _active_budget.get()
    return budget if budget is not None else DiagnosisLlmBudget.from_environment()
