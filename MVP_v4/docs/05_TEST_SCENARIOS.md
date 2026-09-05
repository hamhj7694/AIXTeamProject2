# 테스트 시나리오

| Phase | 필수 검증 |
|---|---|
| 0 | migration 001/health schema, local path 격리, env 이름, UUID secure/fallback, frontend build |
| 1 | Case/Event/role projection, 409, idempotency, delta no-op/ID merge |
| 2 | threshold no-case, feature-only reconstruction, 원문 DB/log 미저장 |
| 3 | Task 결과/취소/동일 ID 재개, 승인 전 미생성, 개인 메모/북마크 |
| 4 | P0 단일 활성/중복 방지, P1/P2 승인, Progress 독립, 안전 업로드 |
| 5 | direct/rag/tool/agent 최소 라우팅, visibility, tool schema/approval/budget/grounding |
| 6 | 허용 Brief trigger, non-trigger zero AI, 종료 Final Report |
| 7 | draft/focus/cursor/selection/IME, stale AI, 직원 확정/삭제 보호, Scenario A/B |

최종 standalone 환경에서 fresh Python 3.11 venv/requirements 및 npm ci, 새 DB migration, 두 API health, production frontend 핵심 E2E.
각 결과는 PASS/FAIL/NOT_RUN을 구분한다. fixture/비밀키 없는 검증은 실제 LLM/RAG E2E로 표시하지 않는다.
