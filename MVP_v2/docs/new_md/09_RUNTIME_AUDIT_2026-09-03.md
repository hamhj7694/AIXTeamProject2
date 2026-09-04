# Runtime and usability audit — 2026-09-03

## Fixed in this pass

- Customer Question Queue, answers, and proposed Case Facts now survive a local SQLite repository restart.
- The SQLite adapter closes each connection, preventing Windows file locks during a restart or test cleanup.
- Customer structured cards are ordered with ordinary messages by `created_at`; an answered question suppresses its duplicate raw answer bubble using `answer_message_id`.
- CaseCopilot is now an explicit bank-user AI command. It stores the resulting AI reply in the requested channel and records the provider/model label instead of claiming a deterministic reply.
- Provider failure is visible as an error. It does not store a fabricated AI message and it does not retry automatically.
- Customer startup now clears a stale auto-question error after the command succeeds. String-shaped FastAPI `detail` responses and HTTP status codes are shown instead of the ambiguous `요청을 처리하지 못했습니다.` fallback.
- Earlier runtime logs contained `500` responses because persisted customer-question rows included `created_at` while an older public response contract rejected that extra field. The current contract/projection no longer reproduces the mismatch: customer Bundles and both customer/bank question views return `200` for every active local Case checked on 2026-09-03.
- General API OpenAPI now generates a tracked TypeScript schema, and all Frontend domain clients share one General API transport/error/mutation layer.
- Every quick-work card now receives non-empty Case-context content and its card-specific execution fields. Missing provider credentials produce an explicitly labelled rule-based draft rather than an empty shell; successful execution closes the transient card and refreshes the server-backed result.
- The bank AI-card hierarchy now exposes Shared Case context sources, a concise situation summary, decision rationale, the immediate next action, and the editable execution component. Provider/model internals are visually secondary to operational meaning.

## Usability decisions agreed by the review

### Bank staff

1. Keep **은행 협업** for human coordination and shared AI results; keep **AI 개인 작업공간** private by default. The visual internal/external boundary must remain explicit.
2. Do not make AI answer every human message. A mention or a deliberate action invokes it, preserving team conversation readability and cost control.
3. Treat question cards as a lifecycle: draft → bank selected → customer delivered → customer answered → fact proposed → human confirmed. The timeline must show the status at the work item, not duplicate chat bubbles.
4. Present unresolved facts and progress as click-through work context, not a noisy event feed. Only state-changing actions belong in the Case timeline.

### Customer

1. Customer chat is the primary workspace. Progress and recovery assistance are secondary, stable sidebar content and must never shrink the chat to a narrow column.
2. Customer-facing cards expose only customer-safe language, options, and direct input. Internal rationale, verification evidence, risk score, bank notes, and other participants remain excluded.
3. The recovery mode is durable after the customer declares harm. The compact guide stays outside chat; selecting a procedure opens a detailed, stepwise card below the workspace.
4. Do not force-scroll an already reading customer to the latest message. Auto-scroll only after that user sends, answers, or explicitly requests the latest activity.

## Remaining release blockers

- Replace the current caller-supplied identity fields with authenticated server-side identity/RBAC before any non-demo deployment.
- Complete MySQL parity for Question/Answer and attachment storage before changing the active SQLite adapter.
- Move reports and bookmarks from browser storage into protected server APIs.
- Add abortable, consolidated refresh/SSE or WebSocket updates; current polling is only a recovery mechanism.
- Pin the scikit-learn runtime to the model artifact version (1.6.1) or regenerate the artifact with the deployed version.

## Validation completed

- Focused General API tests: SQLite persistence, collaboration AI contract, and Case-support mapping passed.
- AI API test suite: 55 tests passed without making external LLM requests.
- Frontend production build passed; generated `frontend/dist` was removed afterwards.

## Latest user-journey correction

- Customer UI now uses a dedicated safe shell and no longer exposes bank/verification navigation by normal interaction.
- Bank screens recover customer changes from other devices every three seconds without repeatedly invoking the AI-support endpoint.
- Customer drafts survive navigation; Recovery mode is committed only after the server accepts the emergency command.
- A customer answer now creates an AI-private review card containing the original question, answer, and `담당자 확인 전 정보 후보` state.
- Work-card preparation and completion remain visible as chronological AI-private workflow cards after the transient editor closes.
- Customer question cards show one prominent question instead of repeating the same meaning in a title and explanation.
- Remaining P0 security blocker: the General API still requires real authenticated principal/Case membership enforcement before non-demo deployment. The customer-only shell prevents accidental navigation, not malicious direct API access.
- Latest regression run: General API 31/31 tests passed with the environment-dependent MySQL integration test excluded; AI API 59/59 tests passed. No external OpenAI generation request was made.
