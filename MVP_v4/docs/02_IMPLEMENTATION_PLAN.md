# 구현 계획

기준: 승인된 V1.5 문서. 각 작업 시작 → 구현 → 테스트 → 연속성 문서 갱신.

| Task | Phase / 작업 | 선행 | 완료 기준 |
|---|---|---|---|
| P0-001 | 기준/연속성 문서와 초기 보호 기준 | 없음 | 원본 보존, resume 문서, 기존 변경 기준 기록 |
| P0-002 | AI 재사용 경계 조사 | P0-001 | endpoint/module/schema/dependency/cost/side-effect/이식 계획 |
| P0-003 | 독립 backend/migration/health 기반 | P0-002 | Python 3.11 requirements, migration 001, 양 API health와 계약 테스트 |
| P0-004 | frontend/UUID 기반 | P0-003 | lockfile, npm ci/typecheck/build, UUID fallback 테스트 |
| P0-005 | 배포/격리 검사와 Phase 0 gate | P0-004 | nginx/systemd, env/격리 audit, 전체 gate, DB/AI readiness 사실 기록 |
| P0-006 | V4 AI 엔진 실제 preflight 및 Phase 0 종료 판정 | P0-005 | 승인 ML artifact/adapter 최소 물리 이식, 실제 모델 load/predict/health, 미준비 LLM 구분, Phase 0 gate 재검증 |
| P1-001 | Shared Case schema/contract | Phase 0 gate | 새 Entity schema와 migration, 버전/감사 필드 |
| P1-002 | Case/Event/Projection API | P1-001 | 서버 역할/참여자 권한, 내부정보 유출 0 |
| P1-003 | revision/delta 병합 | P1-002 | 동일 payload no-op, entity ID merge, 삭제/경합 계약 |
| P2-001 | ML intake 연결 | Phase 1 gate, P0-006 | P0-006의 이식 모델을 재사용하여 event feature/threshold intake 연결(모델 복제/재감사 금지) |
| P2-002 | feature extraction/reconstruction | P2-001 | 원문 폐기 경계, feature-only contract |
| P2-003 | Text/Feature intake | P2-002 | threshold 미만 no case, 두 API와 privacy regression |
| P3-001 | Bank Case list/conversation/context | Phase 2 gate | 실제 DB 연결, 작성 대상 구분 |
| P3-002 | Task/suggestion 승인 흐름 | P3-001 | 결과/취소 사유 필수, 채택 시에만 Task 생성 |
| P3-003 | Notes/bookmarks | P3-002 | 개인 소유권, autosave/원본 이동, draft 보존 |
| P4-001 | Customer chat/questions | Phase 3 gate | P0 중복/단일 활성, P1/P2 승인 |
| P4-002 | Progress/recovery/attachments | P4-001 | 실제 조치와 안내 구분, 업로드 V4 내부 |
| P5-001 | Conversational Core/role policy | Phase 4 gate | 자유 대화/맥락/visibility |
| P5-002 | RAG/verification/official data | P5-001 | 출처/유효일/조회일, 정확값 tool lookup |
| P5-003 | Tool registry/routing/agent/eval | P5-002 | 최소 경로/승인/비용/중복/stale/평가 로그 |
| P6-001 | 제한 Brief/Final Report | Phase 5 gate | 허용 trigger만, 종료 보고서, no live report |
| P7-001 | 경합/보안/입력 회귀 | Phase 6 gate | 409/idempotency/stale/overwrite/IME |
| P7-002 | Standalone/AWS/E2E 최종 gate | P7-001 | 독립 복사 clean install/migrate/build/health/Scenario A+B |

각 Phase 공통 gate: frontend typecheck + production build + backend tests + contract tests + 이전 회귀.
Phase 0의 process liveness와 실제 AI/model readiness는 구분하며 준비되지 않은 AI는 실패/미검증으로 기록한다.
MySQL 접속정보 없이 별도 DB 생성을 검증할 수 없으면 Phase 0 완료를 주장하지 않는다.
P0-003은 disposable MySQL로 별도 DB 생성/001/repeat를 검증했다. AWS DB 설정은 별도 운영 gate다.
P0-005의 scaffold gate PASS는 AI engine readiness/전체 Phase 0 완료와 다르다. P0-006에서 남은 preflight를 닫는다.
