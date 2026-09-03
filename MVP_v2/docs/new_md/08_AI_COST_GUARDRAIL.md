# AI Cost Guardrail

## Purpose

Prevent a single diagnosis request, retry loop, or long transcript from creating an uncontrolled number of LLM calls or consuming an unbounded number of tokens.

## Enforced at the AI API

`ai_api` enforces one shared budget for the sentence-event pipeline and the full-context LLM pipeline of each diagnosis request.

| Environment variable | Default | Effect |
| --- | ---: | --- |
| `DIAGNOSIS_MAX_INPUT_CHARS` | 6,000 | Rejects overly long raw input before any LLM call. |
| `DIAGNOSIS_MAX_TURNS` | 30 | Rejects excessive sentence/turn counts before any LLM call. |
| `OPENAI_MAX_CALLS_PER_DIAGNOSIS` | 31 | Caps event + context API calls for one diagnosis. |
| `OPENAI_MAX_TOTAL_TOKENS_PER_DIAGNOSIS` | 16,000 | Caps estimated and observed token accumulation for one diagnosis. |
| `OPENAI_EVENT_MAX_OUTPUT_TOKENS` | 350 | Caps every sentence-event response. |
| `OPENAI_CONTEXT_MAX_OUTPUT_TOKENS` | 500 | Caps the full-context response. |

The budget reserves a conservative estimate before calling the provider, then settles to the provider-reported `usage.total_tokens` after a successful response. This prevents the next function call when the accumulated request budget would be exceeded.

## User-visible behavior

- A request over a guardrail is stopped before calling the model.
- AI API returns `429` with code `AI_BUDGET_LIMIT_REACHED` and an action-oriented message.
- Provider credit exhaustion is returned as `429` with code `OPENAI_QUOTA_EXHAUSTED`, rather than a generic analysis failure.
- The frontend shows that response message instead of silently retrying.
- The current diagnosis client sends one request per button click and does not automatically retry failed AI analysis.

## Operating rules

1. Do not enable automatic retries for provider failures without a bounded retry policy.
2. Keep `OPENAI_MAX_CALLS_PER_DIAGNOSIS` at or below `DIAGNOSIS_MAX_TURNS + 1`.
3. Use a separate project API key with spending limits and usage alerts.
4. For UI-only development, use a non-provider fixture mode only when explicitly intended; it must be labelled as non-LLM output.
5. Rotate any key that was displayed in a terminal, screenshot, commit, or conversation log.

## Verification

`python -m unittest discover -s ai_api/tests -v` includes budget-limit tests. The test suite must not call an external LLM provider.
