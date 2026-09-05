
# !!! HARD CONSTRAINT — MVP_v4 완전 독립 실행 !!!

이 항목은 다른 모든 구현 편의보다 우선합니다.

## 최종 Runtime Isolation

완성된 V4는 `MVP_v4` 디렉터리 안의 애플리케이션 파일만으로 실행되어야 합니다.

**최종 코드가 V4 밖의 로컬 코드/파일에 조금이라도 runtime 의존하면 실패입니다.**

금지:
- `MVP_v3` import
- V3 API를 runtime backend로 호출
- `../MVP_v3` 또는 다른 sibling project path 참조
- repo 공용 module을 V4 밖에서 import
- `sys.path.append`, `PYTHONPATH`로 외부 프로젝트 연결
- 외부 model/prompt/RAG file path
- symlink로 V3 또는 다른 프로젝트 파일 연결
- 개발 PC absolute path
- `/mnt/data` path
- Frontend에서 V3/dev API endpoint 하드코딩

V3 AI Engine 재사용이 필요하면:
**읽기 전용 분석 → 필요한 코드를 MVP_v4 내부로 이식 → V4 내부 import로 전환**하세요.

runtime에서는 V3가 존재하지 않는다고 가정하세요.

완료 테스트:
1. `MVP_v4`만 standalone 임시 위치에 복사
2. V3 및 다른 repo 폴더 없이
3. clean venv / clean npm install
4. DB migration
5. frontend build
6. AI API / General API health
7. 핵심 E2E
8. external local path/symlink/import audit

를 모두 통과해야 합니다.

---


# !!! SECRET ACCESS HARD BLOCK !!!

이번 작업에서 실제 `.env` 파일을 **절대 열거나 읽지 마세요.**

허용:
- `.env.example`
- 코드 속 환경변수 이름
- Settings schema

금지:
- `.env`
- `.env.local`
- `.env.production`
- `.env.development`
- `.env.*.local`
- `MVP_v3/.env`
- 실제 Secret이 들어 있을 수 있는 환경파일

`cat/type/Get-Content/head/tail/grep/sed/Python/Node/IDE file read` 등 어떤 방식으로도 실제 `.env` 내용을 확인하지 마세요.

Secret이 필요한 테스트는 기존 `.env`를 읽어서 해결하지 말고:

```text
[USER_SECRET_REQUIRED]
변수명: ...
```

형태로 보고하세요.

실제 V4 `.env`는 사용자가 직접 생성합니다. Codex는 `.env.example`만 작성합니다.

---

# AWS Ubuntu Production Contract

최종 산출물은 AWS Ubuntu EC2에서 별도 구조 수정 없이 배포 가능해야 합니다.

기준 root:

```text
/home/ubuntu/MVP_v4/
```

필수 구조:

```text
.env
.env.example
.venv/                     # AWS에서 Python 3.11로 새로 생성

backend/
  ai_api/
  general_api/
  contracts/
  migrations/
  scripts/
  models/
  data/
    uploads/
  requirements.txt

frontend/
  src/
  dist/
    index.html
    assets/
  package.json
  package-lock.json

deploy/
  nginx/
  systemd/
  scripts/

docs/
```

규칙:
- 로컬 `.venv` 복사 금지
- `node_modules` 배포 금지
- backend dependency는 `backend/requirements.txt`로 재현
- `.env.example`은 실제 코드가 읽는 변수 이름 전부 포함
- 실제 `.env`는 Git 제외
- 사용 ML model은 V4 내부에 포함
- 공용 Python module도 V4 내부에 포함
- General API entrypoint / AI API entrypoint 명확화

Runtime:
- General API: `127.0.0.1:8100`
- AI API: `127.0.0.1:8101`
- Frontend는 AI API 직접 호출 금지
- Browser API base는 `/api`
- Nginx `/api/*` → General API reverse proxy

Frontend Production Gate:

```text
npm ci
npm run typecheck
npm run build
```

최종 `frontend/dist/index.html`, `frontend/dist/assets/`를 검증하세요.

Nginx static root는 배포 시 `/var/www/mvp_v4`를 사용할 수 있으나,
그 파일은 반드시 **MVP_v4/frontend/dist에서 생성된 산출물**이어야 합니다.

Runtime data:
```text
ATTACHMENT_STORAGE_ROOT=/home/ubuntu/MVP_v4/backend/data/uploads
```
와 같이 V4 runtime root 내부를 사용하고 Git에서 제외하세요.

---

# Frontend HTTP IP UUID Compatibility — HARD REQUIREMENT

V3 AWS HTTP IP 배포에서 `crypto.randomUUID()` 직접 호출로:

```text
crypto.randomUUID is not a function
```

오류가 발생했습니다.

V4에서는 Component/Hook/API module에서 `crypto.randomUUID()` 직접 호출을 **절대 금지**합니다.

공통 helper 하나만 사용하세요.

예:
```text
frontend/src/shared/uuid.ts
createUuid()
```

우선순위:
1. `globalThis.crypto.randomUUID` 가능 → 사용
2. 아니면 `globalThis.crypto.getRandomValues()` 기반 RFC 4122 UUID v4 fallback
3. request/message/idempotency UUID 형식 유지
4. `Math.random()` 단독 fallback 금지

Frontend 전체 source를 검색하여 helper 외 직접 `randomUUID` 사용 0건을 검증하세요.

테스트:
- localhost
- secure context
- `randomUUID`가 없는 환경을 mocking한 HTTP-IP fallback
- request ID / message ID / idempotency key 핵심 흐름

이 요구를 만족하지 못하면 production-ready 완료로 판단하지 마세요.

---

# CSR | Case Share Room V4 — Codex Master Rebuild Prompt

당신은 시니어 풀스택 아키텍트이자 AI 제품 엔지니어입니다.

이번 작업은 기존 V3를 수정하는 작업이 아닙니다.
**CSR | Case Share Room V4를 Frontend와 General Backend 기준으로 Clean Rebuild**합니다.

기존 AI Engine(ML/LLM/RAG/WorkCard/Verification)은 최대한 재사용하되, V4에서는 이를 **대화형 Conversational Agent Engine**으로 정리·확장합니다. Frontend와 General Backend, V4 DB Schema, Shared Case/Event 구조는 새로 구축합니다.

## 0. 절대 규칙

1. `MVP_v3`를 수정하거나 삭제하지 마세요.
2. V4는 반드시 별도 `MVP_v4` 폴더에서 구축하세요.
3. V3 DB에 migration을 실행하지 마세요.
4. V4는 별도 DB/schema와 migration `001`부터 시작하세요.
5. V3의 과거 PRD/TODO/작업로그는 V4 Source of Truth가 아닙니다.
6. V4 구현 기준은 제공된 `CSR_V4_REBUILD_PRD_FINAL` 문서입니다.
7. 기존 AI Engine의 core logic을 새로 복제하지 마세요.
8. AI Engine은 외부/기존 서비스로 먼저 재사용하고, 필요한 Adapter/contract만 작성하세요.
9. Frontend는 AI API를 직접 호출하지 않습니다. 모든 호출은 General Backend를 경유합니다.
10. AI가 DB를 직접 수정하거나 고객에게 자동 심화질문/금융조치를 실행하게 만들지 마세요.
11. Mock으로 연결된 것처럼 완성하지 마세요. 실제 API가 없으면 gap을 기록하고 실제 계약을 추가하세요.
12. 구현 중 과거 문서와 V4 PRD가 충돌하면 V4 PRD가 우선입니다.

## 0.1 Source of Truth 생성 규칙

V4 `docs/00_SOURCE_OF_TRUTH.md`에는 최소 다음을 잠그세요.
- Conversational Core가 기본 경험
- Direct/RAG/Tool/Agent 중 최소 필요 경로 선택
- Orchestrator는 rule/state 우선, 복합 상황만 LLM planning
- Bank/Customer는 하나의 Shared Case를 role projection으로 공유
- 신규 은행 업무 Source는 Task 하나
- Structured Case State는 데이터 변경 시 갱신
- 상시 자동 Live Report 없음
- AI Case Brief는 최초/중요 trigger/명시 요청에서만 갱신
- Final Report는 Case 종료 시 생성
- change-aware revision polling이 MVP 기본, SSE는 optional
- background update가 local draft/focus/IME를 건드리지 않음
- Fine-tuning은 MVP 선행조건이 아니며 Prompt/RAG/Tool/Eval 이후 판단
- V3는 동결하고 AI Engine만 재사용

과거 V3 Source of Truth의 SSE 기본/Live Report 자동갱신 결정을 복사하지 마세요.

## 1. 제품 핵심

CSR은 보이스피싱 탐지 정확도를 다시 경쟁하는 서비스가 아닙니다.

탐지 이후:
- 범죄자가 무엇을 주장했는가
- 무엇을 요구했는가
- 어떤 압박/고립 전략이 있었는가
- 무엇이 확인됐는가
- 무엇을 더 확인해야 하는가
- 고객에게 무엇을 물어야 하는가
- 은행 직원이 어떤 조치를 검토해야 하는가

를 하나의 Shared Case에서 연결하는 Context & Verification Layer입니다.

은행과 고객은 서로 다른 화면을 사용하지만 **동일한 case_id와 Shared Case State를 사용**합니다.

서비스는 전체적으로 Chat-first입니다.

## 2. V4의 핵심 AI 구조

V4 AI의 기본 경험은 **일상적인 대화가 가능한 Chat Assistant**입니다.

사용자는 자유롭게 질문·설명·요청할 수 있어야 하고 AI는 다음 중 필요한 경로만 선택해야 합니다.

1. Direct conversational answer
2. RAG retrieval
3. Function / Tool call
4. 전문 Agent handoff
5. 위 작업의 제한된 조합

구성:
- Conversational Core LLM
- Case Orchestrator
- Customer Role Policy / Customer Agent
- Bank Role Policy / Bank Agent
- Verification Agent + RAG
- Function / Tool Registry
- Brief / Final Report Generator
- Shared Case Engine

사용자에게 Agent 선택 UI를 제공하지 마세요.

Case Orchestrator는 LLM 하나가 모든 Event에서 마음대로 계획하는 구조가 아닙니다.
기본 라우팅은 `user_intent + event_type + Case State + unresolved fields + mode + permissions` 규칙으로 처리하고, 복합적인 작업에서만 LLM Planner가 작업 후보를 제안할 수 있습니다.

모든 Agent를 매 메시지마다 호출하지 마세요.
Agent 결과는 자연어 응답과 구조화된 Proposal/Tool Call을 지원하세요.

## 3. 가장 중요한 Intake 구조

V4 MVP에는 테스트용 `새 통화 분석하기` 화면이 필요합니다.

MVP 흐름:

통화 텍스트 입력
→ 문장/구간 분리
→ ML 위험 분석
→ Threshold 미만: Case 미생성
→ Threshold 이상: Context Feature Extraction
→ Raw Text 경계 종료
→ Structured Feature Payload만으로 Context Reconstruction
→ Shared Case 생성
→ Orchestrator 초기 Agent 호출

중요:
- Raw Text는 분석 중 임시 입력으로만 사용
- V4 Case DB에 원문 전체를 기본 저장하지 않음
- Context Reconstruction LLM에는 원문 대신 Context Feature Payload를 전달

이 구조를 지켜야 실제 서비스에서 `통신사 AI → Context Feature Event → CSR`로 교체할 수 있습니다.

따라서 두 입력 계약을 만드세요.

1. MVP Text Analyze endpoint
2. Production-like Context Feature Event endpoint

## 4. 실제 서비스 Event

V4는 향후 다음 Event를 같은 Case에 병합할 수 있어야 합니다.

- Telecom AI Call Risk / Context Feature Event
- FDS Transaction Alert
- ASAP Risk Signal
- Customer Emergency Request
- Customer Answer
- Verification Result
- Bank Task Result

## 5. Frontend UX

### Bank

Desktop:

Left = Case List
Center = Shared Conversation
Right = Compact Case Context

대부분의 업무는 중앙 Chat/Action에서 수행합니다.

Quick Actions:
- 고객에게 질문
- AI에게 사건 질문
- 기관 확인
- 대응 업무 기록
- AI에게 대응 업무 추천 받기
- 고객 진행 결과 기록
- 보고서/파일

Right Context 기본 영역:
1. 사건 요약
2. 피해·노출
3. 상대방 주장
4. 상대방 요구
5. 확인된 사실
6. 확인 필요
7. 진행 중 할 일

큰 카드와 반복 설명을 줄이고 한 줄 정보 중심으로 만드세요.

은행 개인 도구:
- Personal Memo
- Bookmark

Memo와 Composer draft는 background update가 와도 focus/cursor/text를 잃지 않아야 합니다.

### Customer

Customer Case Chat 중심.

기능:
- 상황 브리핑
- P0 안전질문
- 은행 승인 질문
- 자유 채팅
- 검증 결과
- 지금 해야 할 행동
- 은행 확인 요청
- Recovery Navigator
- Attachment

Progress 기본 노출:
- 지금 상태
- 완료된 것
- 내가 지금 해야 할 것

untouched UNKNOWN 단계는 큰 카드로 전부 보여주지 마세요.

## 6. Task

신규 은행 대응 업무의 Source of Truth는 `tasks` 하나입니다.

AI BANK_ACTION 추천:
AI 추천 요청
→ 1~3개 후보
→ 직원 선택
→ 수정
→ 저장
→ AISuggestion 감사정보 + Task 생성

추천 수신만으로 Task를 생성하지 마세요.

## 7. Question Policy

P0 자동 Queue 가능:
- 실제 송금 여부
- 개인정보 제공 여부
- 인증정보/OTP 제공 여부
- 원격제어 앱 설치 여부

P1/P2:
AI 후보 → 직원 검토/수정 → 고객 발송

한 번에 고객에게 활성 질문 하나만 보여주세요.

## 8. Verification

Verification은 official data/RAG를 사용합니다.
정확한 전화번호와 URL을 LLM이 임의 생성하지 않게 하세요.

상태:
PENDING / IN_PROGRESS / VERIFIED / MISMATCH / UNVERIFIABLE

은행에는 Evidence 포함 상세 결과.
고객에는 공개 승인된 쉬운 요약만 제공합니다.

## 9. Change-aware Update / AI Trigger

V4는 polling마다 전체 Case object를 갈아끼우거나 AI를 재실행하는 구조를 만들지 마세요.

MVP 권장:
- Write는 HTTP
- 작성자가 수행한 Write는 성공 즉시 해당 Entity만 반영
- 다른 사용자/백그라운드 변경은 revision/fingerprint 기반 polling을 허용
- 동일 revision이면 state 교체 금지
- Entity ID 기반 부분 병합
- SSE는 안정적으로 추가 가능한 경우 선택 사항이며 MVP 필수 아님

사용자의 local draft/focus/cursor/selection/IME 상태는 server state와 분리하세요.

AI는 다음 Trigger에서만 실행합니다.
- 새 Case 생성/Feature 입력
- 사용자의 명시적 AI 질문
- 고객 일반 상담 메시지 중 실제 생성이 필요한 경우
- P1/P2 질문 후보 요청
- Verification 요청
- Bank Task 추천 요청
- 중요 Case 상태 변경에 따른 Brief 갱신 정책
- Final Report 생성

AI를 실행하면 안 되는 예:
- polling tick
- 화면 새로고침/패널 open-close
- Memo/Bookmark 변경
- 동일 payload 수신
- 단순 Task 상태 렌더링

## 10. Structured Live Case / Brief / Final Report

V4에는 상시 자동 재생성되는 Live Report를 만들지 마세요.

실시간에 가까워야 하는 것은 **구조화된 Shared Case State**입니다.

- Claim / Demand
- 피해·노출
- Fact
- Verification status
- Customer answer
- Task status
- CustomerProgress
- Timeline/Event

위 데이터는 실제 DB 변경 시 해당 Entity만 갱신합니다.

AI Case Brief는:
- Case 생성 시 최초 1회
- P0 핵심질문 완료
- 중요한 Verification 완료
- Recovery 진입
- 은행 직원의 명시적 [AI 브리프 갱신]
등 제한된 Trigger에서만 갱신합니다.

Case 종료 시 Final Report를 1회 생성합니다.

## 10.1 Conversational Engine / RAG / Tool Requirements

### Conversational behavior
- 기본적으로 자연스러운 일상 대화가 가능해야 합니다.
- 사건 맥락 질문뿐 아니라 사용자의 짧은 후속 질문, 확인 요청, 설명 요청에도 맥락을 유지해 답하세요.
- Customer와 Bank는 같은 Core Model을 재사용할 수 있지만 role policy, visibility, tools, tone을 분리하세요.

### RAG
- 공식 기관 절차, 피해구제, 공식 안내, 검증 근거가 필요할 때만 사용하세요.
- 모든 메시지에 RAG를 강제하지 마세요.
- retrieval source metadata를 보존하세요.
- 전화번호/URL 등 정확값은 official DB/tool을 사용하고 LLM이 생성하지 않게 하세요.

### Function / Tool Registry
각 Tool은 최소 다음 메타데이터를 가져야 합니다.
- name
- description
- input_schema
- output_schema
- allowed_roles
- side_effect
- human_approval_required
- idempotency policy
- timeout/retry

핵심 Tool 예:
- get_case_state
- search_official_procedure
- lookup_official_contact
- propose_customer_question
- request_verification
- propose_bank_task
- refresh_case_brief
- recommend_recovery_step

### Tool/Agent execution rule
AI가 Tool Call을 반환했다고 바로 실행하지 마세요.
General Backend가 role/permission/case state/schema를 검증한 후 실행합니다.
Side effect가 있는 Task 생성·고객 발송·상태 변경은 Human approval 규칙을 지킵니다.

### Fine-tuning
V4 MVP에서 Fine-tuning을 선행조건으로 만들지 마세요.
먼저 Prompt/RAG/Tool routing/Evaluation을 안정화하세요.

단, 향후 Fine-tuning을 적용할 수 있도록 다음 로그와 평가셋을 남기세요.
- user intent
- selected route(direct/rag/tool/agent)
- tool name / result
- accepted/rejected AI proposal
- human edited output
- schema validation result
- hallucination/grounding failure label

Fine-tuning 후보는 routing, schema adherence, role tone, 반복 질문 감소입니다.
변경 가능한 공식 절차/연락처 지식을 Fine-tuning으로 넣지 마세요.

### Evaluation harness
최소 평가:
- 일반 대화 응답
- Case context 유지
- Direct vs RAG vs Tool vs Agent routing
- Tool call 정확도
- RAG grounding
- 중복 질문 방지
- visibility leakage
- side-effect Human approval
- 구조화 output schema

## 11. Backend 구조

General Backend 책임:
- Case CRUD
- Message/Question/Answer
- Context/Fact
- Verification
- Task
- CustomerProgress
- AI orchestration
- visibility
- idempotency
- version conflict
- Event
- Change-aware update/revision
- AI Case Brief / Final Report

AI API는 DB를 직접 수정하지 않습니다.

## 12. DB

V4 전용 DB를 새로 만드세요.
기존 V3 DB를 migration하지 마세요.

최소 테이블:
- cases
- case_participants
- context_features
- context_items
- messages
- questions
- question_answers
- facts
- verifications
- verification_evidence
- tasks
- customer_progress
- ai_suggestions
- case_events
- case_briefs
- reports
- ai_runs
- personal_notes
- bookmarks
- attachments
- official_contacts

모든 변경가능 업무 엔티티에 version과 timestamp/history 또는 event 추적을 고려하세요.

## 12.1 AI Run / Evaluation Logging

향후 평가와 필요 시 Fine-tuning을 위해 AI 실행 로그를 남기되, 서비스 원본 데이터와 분리하세요.

최소 필드:
- run_id / case_id / actor_role
- intent
- route: DIRECT / RAG / TOOL / AGENT / COMPOSITE
- agent/tool
- model / prompt_version
- source_revision or case_fingerprint
- schema_valid
- grounding source ids
- latency / token usage / estimated cost
- employee/customer outcome where appropriate
- accepted / edited / rejected
- error_type

민감한 통화 원문을 학습로그로 자동 축적하지 마세요.
Fine-tuning 데이터셋 생성은 별도의 명시적 후처리 단계로 남기세요.

## 13. Safety Contracts

- expected_version mismatch → 409
- retry write → client_request_id idempotency
- stale AI result 저장 금지
- 직원 확정정보 AI overwrite 금지
- 직원 삭제정보 자동복구 금지
- CUSTOMER / BANK_INTERNAL / AI_PRIVATE visibility 분리
- 고객 Bundle에 내부 데이터 유출 금지
- AI 자동 금융조치 금지

## 14. 작업 방식

이번에는 V3 전체를 다시 Audit하는 데 크레딧을 쓰지 마세요.

V4 PRD를 읽고 아래 순서로 직접 구현하세요.



# !!! DURABLE CONTINUATION / RATE-LIMIT RESUME — HARD REQUIREMENT !!!

이 작업은 한 Codex 턴/한 사용량 창에서 끝나지 않을 수 있습니다.
따라서 **언제 중단되어도 다른 세션이 Repository만 읽고 정확히 이어갈 수 있게 작업하세요.**

## Phase 0에서 반드시 생성

```text
MVP_v4/AGENTS.md
MVP_v4/docs/02_IMPLEMENTATION_PLAN.md
MVP_v4/docs/03_IMPLEMENTATION_STATUS.md
MVP_v4/docs/06_TODO.md
MVP_v4/docs/07_WORK_MAPPING.md
MVP_v4/docs/08_HANDOFF_CHECKPOINT.md
MVP_v4/docs/09_DECISION_LOG.md
```

기존 필수 문서들과 함께 유지하세요.

## AGENTS.md의 세션 진입 규칙

모든 새 Codex 세션은 구현 전에:

1. `docs/00_SOURCE_OF_TRUTH.md`
2. `docs/03_IMPLEMENTATION_STATUS.md`
3. `docs/06_TODO.md`
4. `docs/07_WORK_MAPPING.md`
5. `docs/08_HANDOFF_CHECKPOINT.md`
6. `git status` / diff
7. 현재 Task 관련 코드/테스트

를 읽도록 지시하세요.

## Task ID / Atomic Work

모든 작업에 `P<phase>-<number>` ID를 부여하세요.

예:
- P0-001
- P1-003
- P3-007

작업 하나는 가능하면 한 개의 명확한 완료조건과 test gate를 갖는 원자 단위로 만드세요.

## 작업할 때마다 즉시 업데이트

Task 시작:
- Status = IN_PROGRESS
- Handoff CURRENT_TASK 업데이트

파일/API/DB/Test 범위 변경:
- WORK_MAPPING 업데이트

Task 완료:
- TODO 업데이트
- Status = DONE 또는 VERIFIED
- 변경 파일
- 실행 명령
- test 결과
- 남은 이슈
- Handoff의 LAST_COMPLETED / NEXT_EXACT_STEPS
를 즉시 기록

문서 업데이트를 전체 작업 마지막에 몰아넣지 마세요.

## Handoff 파일은 항상 최신이어야 함

최소:

```text
LAST_UPDATED
CURRENT_PHASE
CURRENT_TASK
CURRENT_STATUS
LAST_COMPLETED
FILES_CHANGED
COMMANDS_RUN + PASS/FAIL
KNOWN_GOOD_STATE
INCOMPLETE_CHANGES
NEXT_EXACT_STEPS
BLOCKERS
DO_NOT_REPEAT
SOURCE_OF_TRUTH_CHANGES
```

## 사용량/중단 위험이 보이면

- 다음 큰 Task 시작 금지
- 현재 Atomic Task를 가능한 clean state로 정리
- test
- Continuity docs 업데이트
- 미완료 코드가 있으면 정확한 파일/함수/상태 기록
- 다음 세션이 실행할 첫 1~3개 명령/작업까지 `NEXT_EXACT_STEPS`에 기록

## Resume 동작

다음 세션에서 “계속해” 요청을 받으면 전체 Repository audit을 다시 하지 마세요.

Continuity docs + git status/diff + 마지막 test를 확인하고,
Handoff의 `NEXT_EXACT_STEPS`부터 계속하세요.

단, 실제 코드가 Handoff와 다르면 실제 코드와 tests를 우선 검증한 뒤 문서를 바로 정합화하세요.

## Git

검증된 Phase Gate에서는 local checkpoint commit을 사용할 수 있습니다.
자동 push는 하지 마세요.
Secret은 절대 commit하지 마세요.

# Phase 0 Folder Bootstrap — EXACT LOCATION

현재 repository root에서 기존 `MVP_v3`와 같은 레벨에 `MVP_v4`를 생성하세요.

```text
<repo-root>/
├─ MVP_v3/    # 절대 수정 금지
└─ MVP_v4/    # 이번 작업의 모든 완성 코드
```

V4 실행파일을 `MVP_v4` 밖에 생성하지 마세요.

Phase 0에서 먼저 다음 skeleton을 만드세요.

```text
MVP_v4/
  .gitignore
  .env.example
  README.md

  backend/
    ai_api/
    general_api/
    contracts/
    migrations/
    scripts/
    models/
    prompts/
    data/
      uploads/
    requirements.txt

  frontend/
    src/
    public/
    package.json
    package-lock.json

  deploy/
    nginx/
    systemd/
    scripts/

  docs/
    00_SOURCE_OF_TRUTH.md
    01_PRD.md
    02_IMPLEMENTATION_PLAN.md
    03_IMPLEMENTATION_STATUS.md
    04_DATA_CONTRACTS.md
    05_TEST_SCENARIOS.md
    AI_REUSE_MAP.md
    AWS_DEPLOYMENT.md

  scripts/
  tests/
```

실제 `.env`는 만들지 마세요.
`.env.example`만 작성하세요.

필요하다면 V4 전용 `.venv`는 사용자/배포환경에서 `MVP_v4/.venv`로 생성하며 Git 제외합니다.

V3에서 가져오는 코드는 분석 후 V4 내부로 물리적으로 이식하고, 이식 완료 후 V4가 V3 경로를 참조하지 않는지 검사하세요.

### Phase 0
- V3 freeze 확인
- MVP_v4 skeleton
- V4 DB
- health
- **AI Engine 재사용 경계만 집중 확인**
- `docs/AI_REUSE_MAP.md` 작성: endpoint/module, request/response schema, model/RAG/tool dependency, side effect, cost 위험, V4 adapter 계획
- `docs/00_SOURCE_OF_TRUTH.md` 작성

V3 전체 UX/Backend를 다시 Audit하지 마세요. AI Engine 재사용에 필요한 파일과 계약만 읽으세요.
확인되지 않은 AI 기능을 새로 복제하거나 Mock으로 연결하지 마세요.

### Phase 1
- contracts/schema
- Case/Event/Bundle
- revision/fingerprint 기반 change-aware sync

### Phase 2
- Text Intake
- ML
- Context Feature
- Feature-only Reconstruction
- Case creation

### Phase 3
- Bank Workspace 전체

### Phase 4
- Customer Workspace 전체

### Phase 5
- Conversational Core + Orchestrator + RAG + Function/Tool + Agent integration + Verification
- AI evaluation harness

### Phase 6
- Structured Case State 안정화
- On-demand/important-trigger AI Brief
- Final Report

### Phase 7
- E2E + polish + production build

각 Phase가 끝날 때 테스트하고 성공하면 사용자 확인을 기다리지 말고 다음 Phase로 진행하세요.

단, 각 Phase는 다음 Gate를 통과해야 합니다.
- Type/Build 또는 해당 Backend test 성공
- 핵심 계약 테스트 성공
- 이전 Phase regression 없음
- Mock/TODO가 새 핵심경로에 남지 않음
- `03_IMPLEMENTATION_STATUS.md` 또는 동등한 상태 문서 갱신

Gate 실패를 숨긴 채 다음 Phase로 넘어가지 마세요.

단, 다음 hard blocker가 있는 경우만 중단하고 보고하세요.
- 기존 AI Engine에 필요한 핵심 endpoint가 전혀 없음
- V4 DB 변경이 데이터 손상을 일으킬 위험
- 제품 결정을 새로 내려야 하는 상충 요구
- 유료 API가 대량 호출될 위험

## 14.1 AI 호출 최소화 원칙

AI 품질은 호출 횟수로 평가하지 않습니다.

- Case에 이미 있는 사실을 단순 조회할 때 LLM 호출 금지
- official DB direct lookup이 가능한 값은 LLM 생성 금지
- 동일 Case fingerprint + 동일 user intent에 대한 불필요 재호출 억제
- Tool result가 충분하면 추가 Agent 호출 금지
- Agent 간 무한 handoff/loop 금지: 최대 hop과 tool call budget 설정
- 실패 retry는 제한하고 사용자 입력을 보존

## 15. 비용 안전

실제 OpenAI/유료 AI API 테스트는 최소화하세요.

- MAX_API_CALLS
- MAX_INPUT_TOKENS
- MAX_OUTPUT_TOKENS
- MAX_RETRIES
- MAX_CONCURRENCY
- 가능하면 MAX_COST

테스트는 mock이 아니라 **기존 저장 fixture/contract test**를 우선 활용하고, 실제 AI는 핵심 E2E에서 제한 횟수만 호출하세요.

## 16. 테스트 Scenario

### Prevent
텍스트 입력
→ 위험 판정
→ Feature 추출
→ Case 생성
→ 고객 P0 질문
→ 고객 답변
→ Verification
→ Bank AI Task 추천
→ 직원 채택
→ 고객 안전행동
→ Case Closed

### Recovery
피해 송금 확인
→ Recovery Mode
→ 지급정지/112/피해구제 안내
→ 직원 실제 결과 기록
→ 고객 Progress
→ Final Report

## 17. 완료 조건

- V4가 V3와 독립적으로 실행
- V4 DB 별도
- Raw text 미저장 경계 테스트
- Feature Event 직접 Case 생성 가능
- Bank/Customer same Case
- Chat-first interaction
- Orchestrator/Agent 역할 동작
- Verification/Task/Progress/Recovery
- AI 추천은 Human approval
- 변경된 Entity 중심 업데이트 / draft 보호
- AI Case Brief는 제한 Trigger에서만 갱신
- Final Report 생성
- draft/focus 안정
- visibility/idempotency/version conflict
- production build
- E2E 2개 통과

## 18. 보고 형식

작업 종료 후 장문의 재설계 보고서 대신 다음만 보고하세요.

1. 생성한 V4 폴더 구조
2. 구현 완료 기능
3. 재사용한 AI Engine 기능
4. 신규/변경 API
5. DB Schema
6. 테스트 결과
7. 실제 E2E 결과
8. 남은 blocker/TODO
9. 실행 방법
10. Conversational/RAG/Tool/Agent 평가 결과
11. V3를 수정하지 않았는지 확인

**V4를 V3의 리팩터링으로 만들지 마세요. V4는 새로운 제품 코드베이스입니다.**


# Final Production / Isolation Gate

모든 기능 구현이 끝난 뒤 반드시 별도 최종 Gate를 실행하세요.

## A. Self-contained audit

소스 전체에서 다음 패턴을 검색하고 0건 또는 승인된 인프라 예외만 남겨야 합니다.

- `MVP_v3`
- `frontend-v3`
- `backend-v3`
- `C:\Users`
- `/mnt/data`
- `sys.path.append`
- `PYTHONPATH`
- 프로젝트 root 밖 상대경로 import/read
- symlink
- Browser의 localhost/127.0.0.1 API 하드코딩
- Component의 직접 `crypto.randomUUID`

`MVP_v4`만 복사한 standalone 환경에서 V4를 실행하여 hidden dependency가 없음을 증명하세요.

## B. AWS production dry-run

문서/스크립트 기준으로 다음 순서를 검증하세요.

1. Python 3.11 `.venv` 새 생성
2. `backend/requirements.txt` 설치
3. `.env.example` → `.env` 변수 누락 검사
4. V4 migration
5. `npm ci`
6. `npm run typecheck`
7. `npm run build`
8. AI API 8101 health
9. General API 8100 health
10. Nginx same-origin `/api` 구조 확인
11. production `dist` 기준 핵심 frontend route 확인
12. HTTP-IP UUID fallback test
13. 전체 E2E

## C. 최종 보고에 추가

- 외부 로컬 runtime dependency 수: 반드시 0
- symlink 수: 반드시 0
- direct `crypto.randomUUID` 사용 수: 반드시 0
- V3 runtime reference 수: 반드시 0
- production dist build 결과
- AWS deployment required files 목록
- `.env.example` 변수 대조 결과
- standalone copy test 결과
