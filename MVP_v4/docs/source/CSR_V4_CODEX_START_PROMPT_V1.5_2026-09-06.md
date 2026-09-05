# CSR V4 — Codex Start Prompt v1.5

CSR | Case Share Room V4를 **새 코드베이스**로 구축하세요.

## 가장 먼저 기억할 절대 조건

**완성된 V4는 `MVP_v4` 폴더 하나만 복사해도 실행되어야 합니다.**

V4 밖의 로컬 코드·파일·모델·프롬프트·migration·static asset에 runtime으로 조금이라도 연결되면 실패입니다.

- V3는 개발 중 AI Engine 확인용 read-only reference만 허용
- 재사용 코드는 V4 내부로 이식
- V3 import/API runtime dependency 금지
- sibling project import 금지
- symlink 금지
- sys.path/PYTHONPATH hack 금지
- 개발 PC absolute path 금지
- V3가 삭제되어도 V4는 돌아가야 함

허용 외부 인프라는 Ubuntu/Nginx/MySQL/승인된 외부 AI API와 서버에서 V4 안에 새로 만드는 `.venv`뿐입니다.


## Secret 접근 금지

실제 `.env` 파일은 절대 읽지 마세요.

- `.env.example`만 읽고 작성
- 실제 `.env`, `.env.local`, `.env.production`, `MVP_v3/.env` 열람 금지
- 환경변수 이름은 코드와 `.env.example`에서 확인
- Secret 값이 필요한 경우 `[USER_SECRET_REQUIRED]`로 변수 이름만 보고
- 실제 `.env`는 사용자가 직접 생성

## 최초 폴더 위치

현재 Repository root에서:

```text
<repo-root>/
├─ MVP_v3/
└─ MVP_v4/
```

형태로 `MVP_v4`를 새로 생성하세요.

**이번에 생성하는 모든 V4 코드·모델·Prompt·contract·migration·deploy file·test·doc는 MVP_v4 안에만 둡니다.**

Repository root나 다른 sibling folder에 V4 실행코드를 만들지 마세요.

## 반드시 이 순서로 문서를 읽으세요

1. `CSR_V4_00_SOURCE_OF_TRUTH_V1.5_2026-09-06.md`
2. `CSR_V4_REBUILD_PRD_FINAL_V1.5_2026-09-06.md`
3. `CSR_V4_CODEX_MASTER_PROMPT_V1.5_2026-09-06.md`

이 셋이 과거 V3 PRD/TODO/로그보다 우선합니다.

## 구현

- 기존 `MVP_v3` 수정·삭제·덮어쓰기 금지
- `MVP_v4`에 Frontend + General Backend + AI API local runtime + V4 DB/Migrations를 새로 구축
- ML/LLM/RAG/WorkCard/Verification은 V3에서 검증된 구현을 분석해 V4 내부로 이식
- AI는 Conversational Core를 기본으로 DIRECT/RAG/TOOL/AGENT 중 필요한 최소 경로 선택
- Orchestrator는 rule/state/policy 우선
- 모든 Event마다 AI 실행 금지
- 상시 자동 Live Report 금지
- Structured Shared Case State는 데이터 변경 시만 갱신
- AI Case Brief는 제한 Trigger/명시 요청에서만
- Final Report는 Case 종료 시
- change-aware polling 기본, SSE optional
- background update가 draft/focus/cursor/IME를 건드리지 않음
- Fine-tuning은 MVP 선행조건 아님. AI evaluation/run log를 먼저 구축

## AWS Production을 처음부터 고려

최종 기준 root:

`/home/ubuntu/MVP_v4/`

- Python 3.11 `.venv`는 AWS에서 새로 생성
- dependency는 `backend/requirements.txt`
- `.env.example`에 필요한 변수 이름 전체
- Frontend: `npm ci → npm run typecheck → npm run build`
- Nginx는 `frontend/dist`를 service
- Browser는 `/api/*`로 General API만 호출
- General API 127.0.0.1:8100
- AI API 127.0.0.1:8101
- Runtime uploads는 `/home/ubuntu/MVP_v4/backend/data/uploads` 등 V4 내부
- `node_modules`, local `.venv`, real `.env`는 배포/commit 금지

## HTTP IP UUID 문제 재발 금지

Component에서 `crypto.randomUUID()` 직접 호출 금지.

공통 `createUuid()` helper:
1. `crypto.randomUUID` 가능하면 사용
2. 아니면 `crypto.getRandomValues` 기반 RFC4122 v4 fallback

localhost/HTTPS/AWS HTTP IP 조건에서 핵심 흐름을 테스트하세요.


## 중간에 사용량이 끝나도 이어갈 수 있도록 반드시 Checkpoint 방식으로 작업

이번 작업은 한 번에 끝난다고 가정하지 마세요.

Phase 0에서 아래를 먼저 만드세요.

```text
MVP_v4/AGENTS.md
MVP_v4/docs/02_IMPLEMENTATION_PLAN.md
MVP_v4/docs/03_IMPLEMENTATION_STATUS.md
MVP_v4/docs/06_TODO.md
MVP_v4/docs/07_WORK_MAPPING.md
MVP_v4/docs/08_HANDOFF_CHECKPOINT.md
MVP_v4/docs/09_DECISION_LOG.md
```

모든 작업에 Task ID를 부여하고, 작업 단위마다 위 상태 문서를 갱신하세요.

특히 `08_HANDOFF_CHECKPOINT.md`는 항상:
- 현재 작업
- 마지막 완료 작업
- 변경 파일
- 실행한 테스트와 결과
- 미완료 변경
- 다음 정확한 작업 순서
- blocker
를 담아 최신 상태로 유지하세요.

사용량이 부족해 보이면 새 큰 작업을 시작하지 말고 현재 작업을 안전한 checkpoint로 정리한 뒤 문서를 업데이트하세요.

다음 세션에서 사용자가 “계속해”라고 하면 전체 분석을 다시 하지 말고:
`AGENTS → SOURCE_OF_TRUTH → STATUS → TODO → MAPPING → HANDOFF → git status/diff`
순서로 확인하고 `NEXT_EXACT_STEPS`부터 이어가세요.

## Phase 0에서 먼저 만들 것

- `MVP_v4/docs/00_SOURCE_OF_TRUTH.md`
- `MVP_v4/docs/AI_REUSE_MAP.md`
- `MVP_v4/docs/AWS_DEPLOYMENT.md`
- V4 skeleton
- `.env.example`
- backend/frontend dependency baseline
- self-containment audit script

각 Phase Gate를 통과하면 다음 Phase로 진행하세요.
Hard blocker가 아니면 과거 V3 문서를 다시 해석해 제품 결정을 바꾸지 마세요.

최종 완료 전 반드시 `MVP_v4`만 standalone 위치에 복사하여 build/test/health/E2E를 통과하고, V3 runtime reference 0건을 증명하세요.
