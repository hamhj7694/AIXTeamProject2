# 구현 상태

LAST_UPDATED: 2026-09-06
CURRENT_PHASE: 3
PHASE_GATE: PASS — Phase 2 structured-feature intake and privacy boundary complete; P3-001 local implementation gate passed

| Task | 상태 | 증거/남은 일 |
|---|---|---|
| P3-002 | VERIFIED | 75 backend/contract/regression, 17 frontend/typecheck/build PASS; real Chrome Task lifecycle PASS; MySQL concurrent duplicate/stale + actual HTTP PASS (evidence/p3_tasks_smoke.json). Persisted suggestion adoption tested with fixtures; AI recommendation generation remains P5 scope. |
| P3-001A-3 | VERIFIED | 70 backend tests, 17 frontend tests/typecheck/build; real Chrome notes/bookmark toggle/persistence/delta-stable scroll/focus/highlight PASS. Private writes leave Case revision unchanged. |
| P3-001A-2 | VERIFIED | 17 frontend tests/typecheck/build; real Chrome natural-language updates, channel drafts, AI OFF with actual ML/polling, editor focus/selection/IME DOM preservation PASS. No fake message/provider contract. |
| P3-001A-1 | VERIFIED | 68 backend tests, 14 frontend tests/typecheck/build; MySQL migration 003/repeat + real HTTP PASS; real Chrome search/filter/sort/selection/admin failure+success/trash/restore PASS |
| P0-001 | VERIFIED | 필수 문서 13개, Source/PRD exact copy PASS; V3 267개 non-env tracked hash 기준 저장 |
| P0-002 | VERIFIED | AI_REUSE_MAP 코드 경계/계약/비용 조사. GAP-AI-001 기록 |
| P0-003 | VERIFIED | 11 tests PASS; fresh disposable MySQL migration 001/repeat PASS; 실제 AI/General HTTP liveness + readiness 실패 계약 PASS (18101/18100) |
| P0-004 | VERIFIED | clean npm ci/typecheck/build PASS, UUID/API 7 tests PASS, Vite 7.3.6 online audit 0 |
| P0-005 | VERIFIED | 전체 scaffold gate PASS: Backend/contract/regression 23, Frontend 7, npm ci/typecheck/build, audit/env. evidence/phase0_gate.json |
| P0-006 | VERIFIED | V4 artifact/adapter load/inference PASS; fresh copied V4 + fresh venv model isolation PASS; 39 backend tests, HTTP smoke, full Phase 0 gate PASS |
| P1-001 | VERIFIED | migration 002 Shared Case schema + typed contracts; SQLite/MySQL migration tests, 49 full tests, isolation/env audit PASS |
| P1-002 | VERIFIED | V4 Case create/read/event/projection API; server-attached actor policy, participant scope, CUSTOMER/BANK_INTERNAL projection, AI_PRIVATE exclusion, 409/idempotency PASS on SQLite and disposable MySQL |
| P1-003 | VERIFIED | delta endpoint + Entity ID merge helper; same fingerprint no-op, stale revision ignore, local draft-preserving merge; 54 backend and 9 frontend tests PASS |
| P2-001 | VERIFIED | General→AI approved structured-feature ML intake, V4 context feature/Event/revision persistence, duplicate/stale/invalid/unavailable handling; 58 backend and 9 frontend tests PASS |
| P2-002 | VERIFIED | feature-only deterministic reconstruction contract; raw text rejected, no source persistence/provider call |
| P2-003 | VERIFIED | test-only transient text adapter maps to approved features and reuses ML intake; raw source not persisted; 64 backend tests PASS |
| P3-001 | VERIFIED | Bank-only case list/workspace projection and actual 3-column frontend; existing delta Entity-ID merge polling; 65 backend, 11 frontend tests, typecheck/build and isolation/env/UUID audit PASS; V4-only browser HTTP smoke rendered Case/Event/Context risk flow PASS |

Phase 4–7: PLANNED. 제품 Conversational Core, RAG, standalone/AWS E2E 완료 아님.
시작 시 V3에 사용자 staged 변경 18개가 존재한다. 되돌리거나 수정하지 않는다.

현재 기능: migration 003, Case 목록/휴지통, 자연어 Event 표시, 개인 메모/북마크, Task 생성·수정·완료·취소·재개 및 저장된 제안의 승인 흐름, Entity ID delta polling, General→AI 승인 ML intake. P3-003의 메모 autosave는 다음 작업이다.
AI 제품 `/ready`는 Conversational Core와 production text intake가 미구현이므로 의도적으로 503이다. 구조화 ML intake와 test-only text intake는 구현·검증됐다. 실제 대화/AI 추천 생성/RAG/Tool/Agent 및 전체 제품 E2E는 미완료다.
현재 source audit: V3/외부 로컬 path/UUID 위반 0, symlink/junction 0 (애플리케이션 scope).
V3 non-env tracked 파일 267개 hash 및 git status 기준 비교: 변경 0.
환경변수 사용 13개/example 누락 0, 실제 env 열람 0.
알려진 경고: third-party AnyIO deprecation 1, npm esbuild allow-scripts 알림. 실제 build는 PASS.
P0-006 copied V4 + fresh venv ML isolation PASS: 원본 repo read/network 차단, 새 V4 내부 dependency/model에서 정상·위험 synthetic inference PASS.
Ubuntu/Nginx/systemd 실실행, 최종 full standalone build/migration/health/E2E 및 제품 E2E A/B는 NOT_RUN.
