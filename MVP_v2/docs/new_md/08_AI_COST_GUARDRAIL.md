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

## CaseCopilot calls

CaseCopilot is intentionally separate from diagnosis. A bank user must explicitly send an AI request. 고객 화면의 일반 메시지는 고객 공개 전용 `CUSTOMER_SUPPORT` 응답을 한 번 요청하며, 질문 카드 응답·화면 진입·Polling은 이 호출을 발생시키지 않는다.

| Environment variable | Default | Effect |
| --- | ---: | --- |
| `CASE_COPILOT_MAX_INPUT_CHARS` | 6,000 | Rejects a single oversized prompt before provider use. |
| `OPENAI_CASE_COPILOT_MAX_OUTPUT_TOKENS` | 400 | Caps a single CaseCopilot reply. |
| `OPENAI_CASE_COPILOT_MODEL` | `gpt-4o-mini` | Identifies the model returned in `model_mode`. |
| `CASE_COPILOT_MODE` | `openai` | `fixture` is allowed only for explicitly labelled UI development. |
| `OPENAI_CUSTOMER_AI_MAX_OUTPUT_TOKENS` | `250` | 고객용 단일 응답의 최대 출력 토큰. |
| `CUSTOMER_AI_MAX_CALLS_PER_MINUTE` | `6` | Case별 1분 고객 AI 호출 상한. |
| `CUSTOMER_AI_MAX_CALLS_PER_DAY` | `40` | Case별 24시간 고객 AI 호출 상한. |
| `CUSTOMER_AI_MAX_CONCURRENCY` | `2` | 한 AI API 프로세스의 고객 응답 동시 호출 상한. |

There is no automatic retry and no silent deterministic fallback when a real CaseCopilot request fails. The API returns a clear `401`, `429`, or `503`; no fabricated AI answer is stored in the Case timeline.

현재 고객 AI 호출 예산은 AI API 프로세스 단위 hard stop이다. 다중 worker·다중 인스턴스 운영에서는 Redis/DB의 공유 quota와 인증 사용자 기준 rate limit으로 교체해야 한다. 고객 AI 응답은 원 고객 Message의 `reply_to_message_id`를 저장해 대화 근거를 추적한다.

## Work-card generation

Each quick-AI button makes exactly one explicit `POST /ai/work-cards/generate` call. Ordinary typing, channel changes, heartbeat, and polling never generate a card or consume provider tokens.

| Environment variable | Default | Effect |
| --- | ---: | --- |
| `OPENAI_CASE_WORK_CARD_MAX_OUTPUT_TOKENS` | 700 | Caps one structured card proposal. |
| `OPENAI_CASE_WORK_CARD_MODEL` | `gpt-4o-mini` | Model used for typed work-card payloads. |
| `CASE_WORK_CARD_MODE` | `openai` | `fixture` is test/UI mode and is explicitly labelled. |
