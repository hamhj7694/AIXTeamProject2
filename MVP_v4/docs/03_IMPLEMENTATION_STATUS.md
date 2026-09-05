# 구현 상태

LAST_UPDATED: 2026-09-06
CURRENT_PHASE: 1
PHASE_GATE: PASS — Phase 0 foundation + local structured-feature ML preflight (Phase 1 entry permitted)

| Task | 상태 | 증거/남은 일 |
|---|---|---|
| P0-001 | VERIFIED | 필수 문서 13개, Source/PRD exact copy PASS; V3 267개 non-env tracked hash 기준 저장 |
| P0-002 | VERIFIED | AI_REUSE_MAP 코드 경계/계약/비용 조사. GAP-AI-001 기록 |
| P0-003 | VERIFIED | 11 tests PASS; fresh disposable MySQL migration 001/repeat PASS; 실제 AI/General HTTP liveness + readiness 실패 계약 PASS (18101/18100) |
| P0-004 | VERIFIED | clean npm ci/typecheck/build PASS, UUID/API 7 tests PASS, Vite 7.3.6 online audit 0 |
| P0-005 | VERIFIED | 전체 scaffold gate PASS: Backend/contract/regression 23, Frontend 7, npm ci/typecheck/build, audit/env. evidence/phase0_gate.json |
| P0-006 | VERIFIED | V4 artifact/adapter load/inference PASS; fresh copied V4 + fresh venv model isolation PASS; 39 backend tests, HTTP smoke, full Phase 0 gate PASS |
| P1-001 | VERIFIED | migration 002 Shared Case schema + typed contracts; SQLite/MySQL migration tests, 49 full tests, isolation/env audit PASS |
| P1-002 | VERIFIED | V4 Case create/read/event/projection API; server-attached actor policy, participant scope, CUSTOMER/BANK_INTERNAL projection, AI_PRIVATE exclusion, 409/idempotency PASS on SQLite and disposable MySQL |
| P1-003 | VERIFIED | delta endpoint + Entity ID merge helper; same fingerprint no-op, stale revision ignore, local draft-preserving merge; 54 backend and 9 frontend tests PASS |

Phase 2–7: PLANNED. 기능 구현/AI 실호출/Standalone/E2E 완료 아님.
시작 시 V3에 사용자 staged 변경 18개가 존재한다. 되돌리거나 수정하지 않는다.

현재 기능: React 연결 확인 화면, 두 API liveness, MySQL migration 002, V4 Shared Case create/read/event projection API, V4 내부 승인 structured-feature ML artifact/adapter와 `/ready/ml`.
AI 제품 `/ready`는 Conversational Core와 Intake가 미구현이므로 의도적으로 503이다. P1 Case create/read/event projection 외 Chat/Intake/Conversational/RAG/Tool/Agent 기능은 아직 미구현/미검증이다.
현재 source audit: V3/외부 로컬 path/UUID 위반 0, symlink/junction 0 (애플리케이션 scope).
V3 non-env tracked 파일 267개 hash 및 git status 기준 비교: 변경 0.
환경변수 사용 11개/example 누락 0, 실제 env 열람 0.
알려진 경고: third-party AnyIO deprecation 1, npm esbuild allow-scripts 알림. 실제 build는 PASS.
P0-006 copied V4 + fresh venv ML isolation PASS: 원본 repo read/network 차단, 새 V4 내부 dependency/model에서 정상·위험 synthetic inference PASS.
Ubuntu/Nginx/systemd 실실행, 최종 full standalone build/migration/health/E2E 및 제품 E2E A/B는 NOT_RUN.
