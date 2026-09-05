# Handoff Checkpoint

LAST_UPDATED: 2026-09-06
CURRENT_PHASE: 3
CURRENT_TASK: P3-003
CURRENT_STATUS: NOT_STARTED

## LAST_COMPLETED
- P3-002 VERIFIED: actual Task CRUD/lifecycle, result/reason requirements, same-ID reopen, bank authorization, version/idempotency and persisted suggestion accept/edit/reject. AI proposal generation remains unimplemented (P5); fixture approval checks are not provider evidence.
- P3-001A-1 a86c588: compact list and admin soft-delete/trash/restore.
- P3-001A-2 addbfbb: natural-language notices and honest channel/composer shells.
- P3-001A-3 18d3d88: private notes and stable Event bookmarks.
- Earlier P0-P3-001 baseline remains verified; see status/mapping and evidence. Do not repeat it.

## FILES_CHANGED
- P3-002: backend/contracts/{case,tasks}.py; cases/{repository,workspace_repository,tasks_repository}.py; General main.py; scripts/{task_smoke,phase0_smoke}.py; frontend api/cases, shared/workspace, App/TaskWorkspace/styles; backend task tests and browser smoke; continuity documents and evidence/p3_tasks_smoke.json.

## COMMANDS_RUN
- .venv/Scripts/python.exe -m pytest tests -q: 75 passed, one third-party AnyIO deprecation.
- After MySQL lock sequencing correction: pytest test_tasks.py test_personal_workspace.py: 7 passed.
- Frontend npm run typecheck / npm test / npm run build: PASS, 17 tests.
- node tests/browser/workspace-smoke.mjs --conversation --personal --tasks: real Chrome PASS including Task create/required result/reopen/cancel and existing composer/personal delta preservation.
- python -m backend.scripts.phase0_smoke --general-port 18300 --ai-port 18301 --tasks: disposable MySQL migration 003/repeat; four concurrent duplicates commit once; competing same-version requests yield one commit/one conflict; actual HTTP Task create/replay/projection; ML and intended readiness PASS.
- Static isolation/UUID audit: 65 application files, zero violation/link/direct component UUID calls.

## KNOWN_GOOD_STATE
- Migration head 003. Task/private data use existing schema; no new migration in P3-002.
- V4-only smoke harness: frontend http://127.0.0.1:15173, General 18100, AI 18101. General parent PID 20676; verify current ownership before any restart. General restart is needed to pick up the last lock-order correction. Never stop unrelated services.
- The browser harness uses APP_ENV=test and an ignored V4 SQLite DB. Explicit test proxy actor headers are not production authentication. Administrator test credential is process-only; no actual env file read.
- ML /ready/ml 200, General health 200; product /ready 503 because conversational/production text intake remain unimplemented. No paid provider calls.
- Original ML artifact/features/threshold/guardrail unchanged.
- Private notes/bookmarks never change Case revision, facts, customer projection or trigger AI. Tasks never automatically change CustomerProgress.
- V3 and presentation staged/unstaged user changes are preserved; repository-wide status is intentionally not clean. Only V4 may be staged/committed.

## INCOMPLETE_CHANGES
- No unfinished P3-002 implementation. P3-003 autosave has not started; current notes are explicit append/save only.
- Existing bookmarks target persisted Events. Extend actual structured Task references under P3-003 if needed; do not fabricate Message/Question/Verification/Report instances.
- No actual conversation send/provider/RAG, customer workflow, report generation or final product/standalone E2E completion.

## NEXT_EXACT_STEPS
1. Start P3-003: read PRD personal-note/bookmark criteria and existing PersonalUtilities, personal contract/repository/tests. Reuse owner-scoped persistence/navigation, implement autosave with version/idempotency and draft/focus/IME preservation; prevent stale response overwrites and duplicate notes.
2. Verify only affected backend/frontend/browser behavior, then Phase 3 common gate. Persist test evidence and commit one complete atomic task.
3. Continue P4-001 per implementation plan when Phase 3 gate passes. Do not infer AI generation completed from approved-suggestion fixtures.
4. Resume via AGENTS -> SOURCE -> STATUS -> TODO -> MAPPING -> HANDOFF -> git status/diff; never perform a whole-repository re-audit.

## BLOCKERS
- GAP-AI-001 official RAG corpus remains unresolved for P5-002; see AI_REUSE_MAP.
- Live AWS/provider credentials, when required: [USER_SECRET_REQUIRED] DATABASE_URL, OPENAI_API_KEY. They are unnecessary for current local work; paid calls forbidden.
- Production authentication adapter and unimplemented AI/customer paths remain product integration work. Test headers must stay test-only.

## DO_NOT_REPEAT
- No V3 or actual env access; no external local model path, path injection or symlink. No model/threshold/feature/guardrail changes.
- No push; preserve unrelated staged/unstaged changes. Commit verified V4 paths only and inspect status afterwards.
- No repeated baseline Gate without an affected concern. Task concurrency justified a focused fresh MySQL smoke.
- npm build/Chrome/process launch may require approved sandbox execution; do not weaken product code for sandbox limits.
- Keep Chrome/profile/log/DB artifacts inside ignored V4 .cache or backend/data; only evidence JSON is committed.
- Do not reuse historical PID assumptions; validate V4 process ownership first.
