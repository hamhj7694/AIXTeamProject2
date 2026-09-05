# Bank Workspace canonical UX · P3-001A

Direct user request dated 2026-09-06 supersedes the earlier event-viewer presentation.

- User status: 의심 (no confirmed loss), 피해 발생 (confirmed actual transfer/loss), 해결 및 종결 (closed). ML score/classification never determines this taxonomy. Confirmation must originate in an authenticated customer answer or staff confirmation with audited evidence, never ML alone.
- LEFT: compact rows, visible Case ID and natural-language title/summary; search explicit user-facing metadata only; 전체/피해 발생/의심/해결 filters; ID/created/updated sorting ascending/descending, default updated descending. Trash is reversible Case soft deletion, participant scope plus server-verified administrator password and audited versioned/idempotent mutation. No password in frontend source or audit payload.
- CENTER: shared Conversation. Other/customer/AI conversational messages LEFT; current bank actor's messages RIGHT; System, Brief, Verification, Suggestion, Action and Case updates CENTER structured notices. Existing events receive safe natural-language labels; no invented conversation or generic dumping of payloads.
- Composer: AI participation defaults ON, can be OFF independently of ML/system/explicit AI actions; bank-internal/customer channel drafts isolated by Case and channel. Until real message/provider contracts exist, send/upload/recommend controls are explicitly unavailable. Questions can be drafted and selected locally but cannot be sent yet.
- Future message contract: authenticated server actor; validated CUSTOMER/BANK_INTERNAL channel; bank-only internal messages excluded from customer projection; expected version and client request ID; AI conversational participation only gates automatic responses. Never infer participant identity from browser input. Reuse timeline IDs for real Message/Brief/Verification/Suggestion results.
- Personal notes: actor-private, Case-scoped; never official facts/evidence or AI triggers. Bookmarks: actor+Case+stable Event/Message/Entity reference, no content copy; toggle, personal panel, scroll/focus/highlight; inaccessible/deleted original safely reported.
- Toolbar opens small panels. Provider-dependent functions remain honest shells. P3-002 Task/suggestion behavior is not implemented ahead of its task.
- RIGHT remains unchanged in P3-001A. Follow-up UX task must remove internal feature/developer terminology from final human context presentation without changing ML semantics.
- Polling: existing revision/fingerprint no-op and Entity-ID merge; stale responses ignored, no entire Case replacement, editor DOM/draft/focus/selection/IME preserved.

Atomic execution: P3-001A-1 list/search/filter/sort/trash; P3-001A-2 Conversation/local composer; P3-001A-3 private notes/bookmarks/utilities. Each requires tests, browser smoke, documentation and commit. Then resume P3-002.

## Implemented contracts

- Migration 003 adds Case title/summary and reversible deletion metadata without changing approved ML fields. Search uses explicit user-facing metadata; private Event payloads are never searched.
- POST Case trash requires server actor, administrator credential and expected Case version. Password has no application fallback and is never logged or returned; malformed trash requests use redacted validation responses. Delete/restore generate BANK_INTERNAL audit Events.
- GET Case personal and POST personal/notes or personal/bookmarks are BANK_STAFF participant-only. Owner comes only from ActorContext. Notes are append-only, idempotent private records. Bookmarks currently reference real EVENT IDs, including inactive versions for safe reactivation; inaccessible originals return available=false. Message/entity types are extended only when their real read contracts exist.
- Private mutations serialize per Case, enforce bookmark versions and idempotency, preserve Shared Case revision/fingerprint, and never write a shared Event containing private text or call AI.
- AI participation and message channel are explicitly local preference/draft shells. They do not claim live provider or delivery behavior. RIGHT UX remains deferred.
