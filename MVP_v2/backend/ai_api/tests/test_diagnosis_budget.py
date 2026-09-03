from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from ai_api.app.domains.diagnosis.budget import (
    DiagnosisBudgetExceededError,
    DiagnosisLlmBudget,
)


class DiagnosisBudgetTest(unittest.TestCase):
    def test_rejects_input_with_too_many_turns_before_ai_call(self) -> None:
        budget = DiagnosisLlmBudget(9, 16_000, 2, 6_000)
        with self.assertRaisesRegex(DiagnosisBudgetExceededError, "최대 2문장"):
            budget.validate_input(text="a. b. c.", turn_count=3)

    def test_rejects_next_call_when_accumulated_budget_would_be_exceeded(self) -> None:
        budget = DiagnosisLlmBudget(2, 500, 8, 6_000)
        budget.reserve(input_text="a" * 100, max_output_tokens=350)
        with self.assertRaisesRegex(DiagnosisBudgetExceededError, "토큰 예산"):
            budget.reserve(input_text="b" * 100, max_output_tokens=350)

    def test_environment_defaults_are_safe_and_positive(self) -> None:
        with patch.dict(os.environ, {
            "OPENAI_MAX_CALLS_PER_DIAGNOSIS": "0",
            "OPENAI_MAX_TOTAL_TOKENS_PER_DIAGNOSIS": "invalid",
        }, clear=False):
            budget = DiagnosisLlmBudget.from_environment()
        self.assertEqual(budget.max_calls, 31)
        self.assertEqual(budget.max_total_tokens, 16_000)


if __name__ == "__main__":
    unittest.main()
