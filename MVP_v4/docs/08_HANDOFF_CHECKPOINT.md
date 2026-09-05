# Handoff Checkpoint

LAST_UPDATED: 2026-09-06
CURRENT_PHASE: 2
CURRENT_TASK: P3-001
CURRENT_STATUS: IN_PROGRESS

## LAST_COMPLETED
- P1-001 VERIFIED: Shared Case data contracts and V4-only migration 002. SQLite/MySQL migration repeat, 49 tests, audit/env PASS.
- P1-002 VERIFIED: V4 Case create/read/event/projection API. Trusted server actor context, participant authorization, visibility projection, event audit, idempotency/409 all verified on SQLite and disposable MySQL.
- P1-003 VERIFIED: revision/fingerprint delta API and ID merge helper protect no-op polling, stale responses and local drafts without SSE or full Case replacement.
- P2-001 VERIFIED: actual General→AI approved ML structured-feature intake persists V4 context feature, audit Event and Case revision with duplicate/stale/invalid/unavailable protection.
- P2-002 VERIFIED: deterministic feature-only reconstruction endpoint rejects reconstructable source text and has no provider call or persistence.
- P2-003 VERIFIED: test-only transient text adapter maps to approved features then reuses P2-001; raw source is absent from DB/Event payloads.
- P0-006 VERIFIED: 승인 모델/adapter를 V4 내부로 이식하고 실제 load/predict, `/ready/ml`, fresh copied V4 + fresh venv isolation, Phase 0 Gate를 통과.
- P0-005 VERIFIED: AWS 자산/audit/scaffold gate; Backend 23 + Frontend 7 PASS; evidence/phase0_gate.json.
- P0-004 VERIFIED: React/Vite scaffold, same-origin health, createUuid, tests 7 PASS, clean install/typecheck/build PASS.
- P0-003 VERIFIED: backend/contract 11 PASS, disposable MySQL migration/repeat 및 두 API 실제 HTTP PASS.
- P0-002 VERIFIED: AI 코드 경계 조사. 이식/실호출 아직 없음.
- P0-001 VERIFIED: 필수 13 문서 존재 및 Source/PRD exact copy PASS.
- 승인된 네 문서를 START → SOURCE → PRD → MASTER 순서로 읽음.

## FILES_CHANGED
- P0-001: AGENTS.md, .gitignore, README.md, docs/00–09, docs/source 및 docs/evidence.
- P0-002: docs/AI_REUSE_MAP.md.
- P0-003: backend/config.py, database.py, contracts/health.py, 두 API app/main.py, General clients/ai.py, migration 001, scripts/migrate.py 및 phase0_smoke.py, requirements.txt, .env.example, pytest.ini, tests/backend 및 tests/contracts.
- P0-004: frontend package/lockfile/tsconfig/vite config/index, src/app, src/api/health.ts, src/shared/uuid.ts, tests/*.test.mjs, .env.example(GENERAL_API_BASE_URL).
- P0-005: scripts audit/gate 4종, backend/scripts/start.py, deploy/nginx config, systemd 3 units, build/health shell, .gitattributes, tests/regression 2 files, AWS/README/연속성 문서, evidence/phase0_gate.json 및 v3-preservation-check.json.
- P0-006: backend/models/WINDOW_LOGISTIC_DASHBOARD_EXPERIMENTAL_SAMPLE_v1.pkl, diagnosis/{model_adapter,preflight}.py, contracts/ml.py, scripts/{model_preflight,isolated_model_probe}.py, scripts/verify_model_isolation.py, ML dependency pins, health/smoke/gate/tests/docs/evidence 업데이트.
- P1-001: backend/contracts/case.py, migrations/002_shared_case_schema.py, database.py, schema/contract tests, docs/04/03/06/07/08/09.
- P1-002: backend/general_api/app/domains/cases/repository.py, general main.py, contracts/case.py, tests/backend/test_case_api.py, phase0_smoke.py, docs/03/04/06/07/08/09.
- P1-003: backend contracts/repository/main delta path, frontend/src/shared/caseDelta.ts, backend/frontend delta tests, docs/03/06/07/08.
- P2-001: AI /intake/ml, ml/case contracts, General AI client/repository/main, P2 API/contract tests, phase0_smoke.py, docs/03/04/06/07/08.

## COMMANDS_RUN
- P0-006 requirements ML install: sandbox FAIL → 승인 실행 PASS; pip check PASS.
- model_preflight --record PASS: 23 features, threshold 95, zero final20/NORMAL, signal final97.600355/PHISHING; 유료 호출 0.
- pytest tests -q: 39 PASS, AnyIO warning 1. static source audit 42 files PASS.
- phase0_smoke --general-port 18100 --ai-port 18101: 새 MySQL/HTTP ML inference PASS, 제품 readiness 503 정상 구분.
- copied V4 + fresh Python 3.11 venv isolation PASS: V4 내부 wheelhouse clean install/pip check, 원본 repo read/network 차단, 실제 model preflight PASS. evidence/model_isolation.json.
- Phase 0 Gate PASS: actual_model_preflight, 39 backend/contract/regression tests, pip check, npm ci/typecheck/frontend tests/build, isolation/env audit. evidence/phase0_gate.json.
- P1-001: migration 002 applied/reapplied on SQLite and disposable MySQL; full pytest 49 PASS; static isolation/env audit PASS.
- P1-001 final revalidation: `.venv\\Scripts\\python.exe -m pytest tests -q` 49 PASS; disposable MySQL migration 002/repeat + General→AI HTTP smoke PASS; frontend typecheck/test/build PASS; static isolation/env/UUID audits PASS.
- P1-002: `.venv\\Scripts\\python.exe -m pytest tests -q` 53 PASS; disposable MySQL case create/event/customer projection + migration repeat + HTTP health/ML smoke PASS; static isolation/env/UUID audit PASS; frontend typecheck, 7 tests and production build PASS.
- P1-003: 54 backend/contract/regression PASS; frontend 9 tests/typecheck/build PASS; isolation and UUID audit PASS.
- P2-001: 58 backend/contract/regression PASS; frontend 9 tests/typecheck/build PASS; isolation/env audit PASS; disposable MySQL actual General→AI intake persists Case revision PASS.
- P0-005 python -m scripts.phase0_gate: sandbox 마지막 build FAIL → 승인 실행에서 전체 PASS(23 backend, 7 frontend, npm ci/typecheck/build, pip check, static/env audit).
- python -m scripts.verify_frontend_uuid_usage: PASS, helper 밖 직접 사용 0.
- V3 baseline SHA-256/status 비교: 267 non-env tracked 파일 변경 0, status 차이 0. evidence/v3-preservation-check.json.
- git diff --check -- MVP_v4 (실제 env 제외): PASS. 신규 V4는 untracked이므로 이 명령만으로 신규 파일 내용을 검증한 것은 아님.
- P0-004 npm install lockfile / npm ci: sandbox download FAIL → 승인 후 PASS.
- P0-004 npm run typecheck PASS; npm test 7 PASS; npm run build sandbox esbuild access FAIL → 승인 후 PASS.
- npm audit online: Vite 7.1.5 high 1 → 7.3.6 업데이트 후 0. Offline audit 결과는 보안 검증으로 사용하지 않음.
- 최종 lockfile npm ci --offline --no-audit --cache ../.cache/npm → typecheck → test 7 → build: 모두 PASS. esbuild allow-scripts 경고는 있으나 build 정상.
- 재개: AGENTS → SOURCE → STATUS → TODO → MAPPING → HANDOFF → git status/diff 확인 완료.
- 재개 검증: pytest backend/contracts 11 PASS, pip check PASS. frontend/scripts/deploy는 아직 없음(문서 PLANNED와 일치).
- python -m venv .venv: PASS; pip install -r backend/requirements.txt: sandbox network FAIL → 승인 후 PASS.
- .venv/Scripts/python.exe -m pytest tests/backend tests/contracts -q: 11 PASS, third-party AnyIO deprecation warning 1.
- python -m backend.scripts.phase0_smoke: FAIL (기존 8100/8101 점유; sandbox 밖 재시도도 동일).
- python -m backend.scripts.phase0_smoke --general-port 18100 --ai-port 18101: PASS. evidence/phase0_backend_smoke.json.
- 네 원본 Get-Content -Encoding UTF8: PASS (긴 PRD는 구간으로 보완).
- git status --short / git diff --name-only: PASS, 기존 사용자 변경 확인.
- python --version: 3.11.9, node --version: 24.18.0, npm.cmd --version: 11.16.0.
- py -0p: 설치 발견 실패. python 명령은 정상. py launcher 사용하지 않음.

## KNOWN_GOOD_STATE
- P0-006 모델: SHA-256 662db2a9351dc4ca2c453776ae6f45750e465234cc9abcecc65b58a6b047c5fc, scikit-learn 1.6.1, 23 features, threshold 95.0, guardrail 유지.
- V4 actual local preflight: zero signal final 20/NORMAL; 91 synthetic signal features final 97.60035508086297/PHISHING. 유료 API 호출 0.
- `/ready/ml` 200; General → AI actual HTTP smoke PASS; 전체 `/ready`는 conversational/text_intake가 NOT_IMPLEMENTED이므로 의도된 503.
- Phase 0 Gate PASS. Phase 1 entry permitted.
- Migration head is 002. P1-001 establishes schema; P1-002 provides the V4 Case create/read/event authorization and human projection baseline.
- P1-001 common gate revalidated after migration-head reporting fix: frontend typecheck, 7 frontend tests, production build, 49 backend/contract/regression tests, MySQL HTTP smoke, internal-path/env/UUID audits all PASS.
- P1-002: Case create/read/event mutation uses only V4 migration 002; no new schema migration, V3 dependency, header/body/query role override, or AI call.
- P0-005 gate의 모든 구현 범위 검증 PASS. 정적 application source/config/deploy 35개에서 위반 0, symlink/junction 0.
- 사용 환경변수 11개 전부 example에 존재; 8개 AI 설정은 향후 예약 변수. 지금 비용제어가 구현된 것으로 해석 금지.
- 모든 작성은 MVP_v4 내부. V3 267개 non-env tracked 파일 및 기존 staged 상태 보존 확인.
- frontend/dist/index.html 및 assets 생성. UUID native/fallback/request-header 계약 검증. 실제 브라우저 HTTPS/HTTP-IP 핵심 E2E는 아직 아님.

## INCOMPLETE_CHANGES
- P0-001~006/P1-001/P1-002/P1-003/P2-001/P2-002/P2-003 are verified. P3-001 is next.
- 의도된 미구현: Case/Chat/Intake/Conversational/RAG/Tool/Agent 제품 경로. AI 전체 `/ready`는 conversational/text_intake 미구현을 명시하며 503.
- 최종 full standalone copy/frontend build/new DB migration/full API readiness/E2E 및 Ubuntu 실행 NOT_RUN.

## NEXT_EXACT_STEPS
1. P3-001: implement Bank Case list/conversation/context on the existing Shared Case APIs without creating another Case source.

## BLOCKERS
- GAP-AI-001: 공식지식 RAG 원본 미확인. AI_REUSE_MAP 참조.
- P1의 공식지식 RAG/LLM 모델/외부 AI 연결은 아직 범위 밖이다. P0-006 local model 성공을 Conversational 엔진 성공으로 해석하지 말 것.
- AWS/유료 AI live 검증 시 [USER_SECRET_REQUIRED] DATABASE_URL, OPENAI_API_KEY. 현재 P0-006 모델 preflight에는 secret 불필요.
- 기존 8100/8101 점유. 임시 smoke는 18100/18101 사용. 기존 프로세스 종료 금지.

## DO_NOT_REPEAT
- P0-006 모델/adapter/threshold/feature order/guardrail을 재설계·재학습·대체하지 말 것. P2는 이 V4 내부 artifact를 연결해 사용한다.
- Vite 7.1.5 재도입 금지. 7.3.6 갱신 후 online audit 0; offline audit 0 결과는 근거로 사용 금지.
- Vite/esbuild build는 sandbox 상위 디렉터리 접근 오류 발생. 승인된 `npm.cmd run build` 또는 `python -m scripts.phase0_gate`로 실행하며 환경 문제를 코드 결함으로 오인하지 않는다.
- .cache 안 disposable DB 테스트 산출물은 Git 제외. runtime/app 배포에 포함하지 말 것.
- 전체 V3 감사/과거 PRD 재해석 금지. 실제 env 파일 접근 금지.
- 기존 staged 변경을 이번 작업으로 간주하거나 되돌리지 말 것.

## SOURCE_OF_TRUTH_CHANGES
- 제품 요구 변경 없음. D-001~010 참조. P0-006/P1-001/P1-002 완료는 코드/evidence와 stale 상태 문서의 정합화다.
- Git commit policy is now applied. The first V4 commit will establish the already verified P0-001~P0-006 and P1-001 baseline without reconstructing unrecorded intermediate file states; subsequent atomic tasks are committed individually after their gates.
