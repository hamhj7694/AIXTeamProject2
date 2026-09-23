# AI 연결 상태·개선 검증 체크리스트

> 목적: 소스 코드에 호출 경로가 존재하는지와 실제 실행 중인 Frontend → General API → AI API → Provider 응답이 정상인지 분리해서 확인한다. 확인된 오류를 수정하고, 각 기능을 `연결됨`으로 표시할 수 있는 근거를 남긴다.

- 기준일: 2026-09-23
- 범위: `MVP_v3/frontend`, `MVP_v3/backend/general_api`, `MVP_v3/backend/ai_api`
- 원칙: AI는 제안만 만들고 고객 발송·금융 조치·기관 API 호출·사건 종결을 자동 실행하지 않는다.
- DB 원칙: 신규 테이블·컬럼·마이그레이션을 만들지 않는다.

## 1. 상태 판정 기준

| 상태 | 의미 |
|---|---|
| `연결됨` | 코드 경로, API 계약, 실제 실행 응답, 화면 반영을 모두 확인함 |
| `부분 연결` | 일부 경로는 동작하지만 화면 반영·저장·재조회·실제 Case payload 중 하나가 미완성임 |
| `계약 실패` | API는 호출되지만 응답 JSON/schema 검증 또는 입력 계약에서 실패함 |
| `미연결` | 백엔드 계약만 있거나 프론트에서 호출하는 화면이 없음 |
| `환경 차단` | 서버·Provider·`OPENAI_API_KEY`·네트워크 문제로 기능을 검증할 수 없음 |

“AI API에 라우트가 있다”만으로 `연결됨`으로 표시하지 않는다. 실행 중인 서버의 OpenAPI와 실제 응답까지 확인한다.

## 2. 현재 기준 상태 요약

| 기능 | 호출 경로 | 현재 판정 | 확인 메모 |
|---|---|---|---|
| 새 통화 분석·Case 생성 | `POST /api/cases/analyze` → `/ai/analyze/text` | `부분 연결` | 경로는 연결되어 있으나 Provider·실제 입력으로 재검증 필요 |
| 사건 지원 스냅샷·우측 패널 | `GET /api/cases/{id}/ai/case-support` → `/ai/case-support/snapshot` | `부분 연결` | 정상 응답하지만 `CaseSnapshotAiAdapter` 기반 결정적 projection이며 생성형 LLM 결과가 아님 |
| 새 메시지 정황·Fact 추출 | 백그라운드 → `/ai/context/facts/extract` | `부분 연결` | 저장·재시도 worker와 함께 확인 필요 |
| 은행 내부 Copilot | `POST /api/cases/{id}/ai/invocations` → `/ai/case-copilot/replies` | `부분 연결` | 응답 본문은 생성되지만 현재 실행 중 API에 `recommended_actions`가 노출되지 않음 |
| AI 답변 하단 액션 트레이 | Copilot `recommended_actions[]` → `AiRecommendationTray` | `계약 실패/환경 불일치` | 최신 소스에는 구현됐으나 실행 중 OpenAPI 응답 계약이 구버전이면 트레이가 숨겨짐 |
| 고객용 Copilot | `POST /api/cases/{id}/ai/customer-replies` | `부분 연결` | 고객 공개 context 분리는 있으나 실제 고객 시나리오 회귀 필요 |
| 고객 질문 추천 | `QUESTION_PLAN` Work Card | `검증 필요` | 단일 Case 직접 호출은 성공했으나 UI 오류 재현·재시작 후 재검증 필요 |
| 기관 확인 요청 추천 | `VERIFICATION_REQUEST` Work Card | `검증 필요` | 단일 Case 직접 호출은 성공했으나 UI 오류 재현·재시작 후 재검증 필요 |
| 대응 조치 체크리스트 | `BANK_ACTION` Work Card | `계약 실패` | 실제 Case payload에서 `AI_WORK_CARD_FAILED`와 응답 형식 오류가 재현됨 |
| 최종 보고서 | `POST /api/cases/{id}/reports/finalize` → `/ai/final-reports/generate` | `부분 연결` | 최소 입력 AI 호출은 성공했으나 실제 종결 payload 오류가 보고됨 |
| 백그라운드 체크리스트 보정 | General API proactive worker | `부분 연결` | 소스상 기본 활성화이나 실행 worker의 최신 코드·실제 변경 반영 확인 필요 |
| `FACT_REVIEW` Work Card | 계약·AI service만 존재 | `미연결` | 호출하는 활성 UI 없음 |
| `CUSTOMER_NOTICE` Work Card | 계약·AI service만 존재 | `미연결` | 고객 안내문 초안 UI 없음 |
| `CASE_TRANSITION` Work Card | 계약·AI service만 존재 | `미연결` | 사건 단계 전환 추천 UI 없음 |

## 3. 실행 환경 사전 점검

### 3.1 서버 및 Provider

- [ ] Frontend 개발 서버가 현재 소스 경로를 제공한다. (현재 확인 포트: `5176`)
- [ ] General API `http://127.0.0.1:8100/health`가 200을 반환한다.
- [ ] AI API `http://127.0.0.1:8101/health`가 200을 반환한다.
- [ ] AI API `http://127.0.0.1:8101/readiness`의 `provider_configured`가 `true`다.
- [ ] 실행 프로세스를 재시작한 뒤 OpenAPI를 다시 조회한다.
- [ ] `OPENAI_API_KEY`를 로그·응답·문서에 출력하지 않는다.
- [ ] `AI_API_BASE_URL`이 General API에서 실제 AI API 주소를 가리킨다.
- [ ] `OPENAI_TIMEOUT_SECONDS`, Work Card/Final Report 출력 토큰 제한을 확인한다.

~~~powershell
Invoke-RestMethod http://127.0.0.1:8100/health
Invoke-RestMethod http://127.0.0.1:8101/health
Invoke-RestMethod http://127.0.0.1:8101/readiness
~~~

### 3.2 실행 중 계약이 최신인지 확인

- [ ] General API OpenAPI의 `PublicAiInvocationResponse`에 `recommended_actions`가 있다.
- [ ] AI API OpenAPI의 `CaseCopilotOutput`에 `recommended_actions`가 있다.
- [ ] Work Card OpenAPI에 `verification_messages`, `suggested_actions.steps`가 있다.
- [ ] 실행 중 서버와 현재 checkout의 commit/file timestamp가 일치한다.
- [ ] 구버전 서버가 남아 있지 않다. Frontend만 HMR로 갱신된 상태를 정상으로 간주하지 않는다.

## 4. 기능별 End-to-End 체크리스트

### 4.1 새 통화 분석·Case 생성

- [ ] Frontend 입력이 `casesApi.analyze`로 전송된다.
- [ ] General API가 `/ai/analyze/text` 또는 production envelope 경로를 호출한다.
- [ ] AI 응답이 Diagnosis 계약을 통과한다.
- [ ] Case, diagnosis, 초기 brief가 저장된다.
- [ ] AI 실패 시 가짜 Case·가짜 사실을 만들지 않고 오류를 표시한다.
- [ ] 동일 `client_request_id` 재시도 시 중복 Case가 생기지 않는다.
- [ ] 긴 입력·빈 입력·Provider timeout을 각각 확인한다.

완료 기준: 새 통화 1건으로 Case가 생성되고 이후 우측 패널·질문·Work Card가 같은 `case_id`를 사용한다.

### 4.2 우측 패널 사건 지원 정보

- [ ] `/api/cases/{case_id}/ai/case-support`가 200을 반환한다.
- [ ] `case_brief`, `case_context`, `recommended_questions`, `unresolved_items`가 계약에 맞는다.
- [ ] `case_context`의 값이 diagnosis·Fact·질문·기관 확인·업무 상태와 일치한다.
- [ ] `PROPOSED` 사실이 `CONFIRMED`로 자동 승격되지 않는다.
- [ ] 고객 채널에 은행 내부 업무·미공개 기관 결과가 노출되지 않는다.
- [ ] 우측 패널이 “생성형 AI가 새로 만든 사실”과 “기존 구조화 projection”을 구분한다.
- [ ] 최신 발화·시간 순서가 정황 흐름에 반영된다.

개선 기준:

- [ ] 생성형 요약이 필요하면 별도 계약과 근거 필드를 정의한다.
- [ ] 요약 문장마다 source revision/evidence reference를 확인할 수 있다.
- [ ] AI 장애 시 마지막 정상 projection과 `STALE/FAILED` 상태를 구분한다.

### 4.3 새 메시지 정황·Fact 추출

- [ ] 고객/직원 메시지 저장 후 extraction job이 생성된다.
- [ ] `/ai/context/facts/extract` 입력에 허용된 구조화 context만 포함된다.
- [ ] AI 추출 결과는 `PROPOSED` 상태로 저장된다.
- [ ] 직원 검토 전 Fact가 사건 확정 사실로 표시되지 않는다.
- [ ] 중복 메시지·재시도·worker 재시작 시 중복 Fact가 생기지 않는다.
- [ ] 실패 job이 retryable 상태로 남고 다음 worker cycle에서 재처리된다.

### 4.4 은행 내부 Copilot 및 액션 트레이

- [ ] TEAM 요청만 내부 Copilot 계약을 사용한다.
- [ ] `AI_RESPONSE`가 BANK_INTERNAL visibility로 저장된다.
- [ ] 응답 본문이 비어 있지 않고 Case 근거를 벗어난 확정 표현이 없다.
- [ ] `recommended_actions`는 최대 3개다.
- [ ] 동일 `action_key`가 제거된다.
- [ ] 허용되지 않은 action key가 제거된다.
- [ ] `DRAFT_REPLY`는 `draft_text`가 있을 때만 표시된다.
- [ ] 내부 TOOL action은 `target_channel=TEAM`이어야 한다.
- [ ] 트레이 버튼은 최신 AI 답변 아래에만 표시된다.
- [ ] 고객 채널에는 트레이가 표시되지 않는다.
- [ ] 질문/송금 조회/기관 확인/대응 조치 버튼이 기존 Dialog를 연다.
- [ ] 답변 초안은 고객 composer에만 삽입되고 자동 전송되지 않는다.
- [ ] 새로고침 시 마지막 AI 답변의 액션만 localStorage에서 복원된다.

실패 재현 시 기록할 것:

- [ ] request id
- [ ] API HTTP status와 `detail.code`
- [ ] 실행 중 OpenAPI의 응답 schema
- [ ] 개인정보를 제거한 AI raw output fixture
- [ ] 프론트에서 받은 `recommended_actions` 값

### 4.5 고객용 Copilot

- [ ] 고객 대화·공개 질문·공개된 기관 결과만 입력에 포함된다.
- [ ] TEAM 메시지·내부 메모·비공개 기관 결과가 입력에서 제외된다.
- [ ] `recommended_actions`가 고객 응답에 포함되지 않는다.
- [ ] 고객에게 내부 업무 수행 완료를 암시하지 않는다.
- [ ] 답변 초안 자동 전송이 발생하지 않는다.
- [ ] OTP, PIN, 비밀번호, 인증번호 등을 요구하지 않는다.

### 4.6 고객 질문 추천 (`QUESTION_PLAN`)

- [ ] `QuestionDialog`에서 `generateWorkCard(caseId, 'QUESTION_PLAN')`가 호출된다.
- [ ] 기존 질문·답변·미확인 필드와 중복 제거된다.
- [ ] AI 질문은 직원 검토 후 선택할 수 있다.
- [ ] 선택하지 않은 질문은 저장·발송되지 않는다.
- [ ] 질문 후보 계약 검증 실패 시 기존 목록이 유지된다.
- [ ] 질문 발송 후 고객 채널 Report Card가 생성된다.
- [ ] AI가 고객에게 자동 발송하지 않는다.
- [ ] 최소 입력, 실제 Case 입력, 빈 후보 입력을 각각 테스트한다.

### 4.7 기관 확인 요청 추천 (`VERIFICATION_REQUEST`)

- [ ] `InstitutionVerificationBoardDialog`에서 Work Card를 호출한다.
- [ ] 기관명·확인 대상 조합으로 중복 제거된다.
- [ ] 최대 10개 기관으로 제한된다.
- [ ] 직원이 초안을 수정해도 재추천이 수정본을 덮어쓰지 않는다.
- [ ] 선택된 행만 `verification_tasks`에 저장된다.
- [ ] 실제 이메일·전화·기관 API 호출이 없다.
- [ ] 내부 TEAM Report Card가 1개 생성된다.
- [ ] 고객 채널에 내부 발송 카드가 노출되지 않는다.
- [ ] 일부 저장 실패 시 성공 행과 실패 행이 구분된다.

### 4.8 대응 조치 체크리스트 (`BANK_ACTION`)

- [ ] `ResponseActionChecklistDialog`가 현재 활성 진입점인지 확인한다.
- [ ] 실제 Case payload로 503 응답을 재현한다.
- [ ] AI raw JSON 파싱 실패인지 Pydantic 계약 검증 실패인지 로그로 구분한다.
- [ ] 출력 토큰 제한으로 JSON이 잘리는지 확인한다.
- [ ] `suggested_actions[]` 최대 12개, 각 `steps[]` 최대 8개를 적용한다.
- [ ] 부모·단계 action type이 `RESPONSE_CHECKLIST`/`RESPONSE_STEP` 규칙을 따른다.
- [ ] 질문 문장·답변 후보·단순 사실 확정 문장이 조치 목록에 들어가지 않는다.
- [ ] AI 실패 시 기존 체크리스트를 유지한다.
- [ ] 부모 진행률이 단계 상태에서 계산된다.
- [ ] 체크·체크 해제가 기존 Action PATCH로 저장된다.

개선 우선순위:

1. 실제 Case payload와 Provider raw output을 개인정보 제거 fixture로 고정한다.
2. 출력 토큰 부족·필수 배열 누락·중첩 단계 누락을 계약 테스트로 재현한다.
3. 허용 범위 내에서 응답 정규화 후 Pydantic 검증을 수행한다.
4. 검증 실패 시 fallback을 자동 저장하지 말고 기존 목록과 오류를 유지한다.

### 4.9 최종 보고서

- [ ] 사건 종결 버튼이 `reports/finalize`만 호출하는지 확인한다.
- [ ] 관리자 비밀번호·expected version 검사가 먼저 수행된다.
- [ ] 최신 Fact·고객 답변·기관 확인·직원 조치·종결 메모가 입력된다.
- [ ] AI 실패 시 사건을 종결하거나 가짜 보고서를 저장하지 않는다.
- [ ] JSON schema의 보고서 필드가 모두 검증된다.
- [ ] 미확인 사항은 `unresolved_items`에 남는다.
- [ ] `PROPOSED` Fact가 확정 사실처럼 보고서에 쓰이지 않는다.
- [ ] 생성된 보고서가 내부 Report Card와 재조회 Bundle에 동일하게 나타난다.
- [ ] 긴 Case에서 출력 토큰 제한과 JSON truncation을 확인한다.

### 4.10 백그라운드 proactive worker

- [ ] `PROACTIVE_QUESTION_AUTOMATION` 기본값이 의도한 환경에서 활성화되어 있다.
- [ ] startup 시 worker가 정확히 하나만 시작된다.
- [ ] Case revision이 바뀐 경우에만 재조정한다.
- [ ] extraction retry와 checklist reconciliation을 구분한다.
- [ ] worker 실패가 메시지 저장·고객 채널을 막지 않는다.
- [ ] worker가 자동으로 고객 질문을 발송하거나 금융 조치를 실행하지 않는다.
- [ ] worker 마지막 실행 시각·처리 건수·실패 건수를 관찰할 수 있다.

## 5. 추후 연결할 Work Card

### `FACT_REVIEW`

- [ ] 우측 패널 또는 대응 검토 창에서 호출 버튼을 정한다.
- [ ] AI가 확인 대상 Fact와 근거를 반환한다.
- [ ] 직원 검토 전 `CONFIRMED`로 저장하지 않는다.
- [ ] 기존 Fact와 중복 제거한다.
- [ ] 직원 승인 시 기존 Context/Fact API로 저장한다.

### `CUSTOMER_NOTICE`

- [ ] 고객 안내문 초안을 보여줄 전용 UI를 정한다.
- [ ] 고객 composer에만 삽입한다.
- [ ] 자동 전송하지 않는다.
- [ ] 내부용 문구·미공개 기관 정보·추정 사실을 제거한다.
- [ ] 직원 수정본을 AI 재추천으로 덮어쓰지 않는다.

### `CASE_TRANSITION`

- [ ] 추천 단계와 실제 Case 상태 변경을 분리한다.
- [ ] AI는 상태 변경 API를 직접 호출하지 않는다.
- [ ] 직원 승인 후 기존 transition API를 사용한다.
- [ ] 권한·version conflict·되돌리기 정책을 확인한다.

## 6. 계약·보안 검증

- [ ] AI 응답의 unknown field가 거부되거나 안전하게 제거된다.
- [ ] 허용되지 않은 action key/category/priority가 제거된다.
- [ ] 고객 채널에 BANK_INTERNAL 데이터가 포함되지 않는다.
- [ ] 원문·민감정보가 불필요하게 Copilot 입력에 전달되지 않는다.
- [ ] 기관명·연락처·사건번호를 AI가 생성해 공식 사실처럼 표시하지 않는다.
- [ ] AI 결과만으로 금융 조치 완료·기관 확인 완료·경찰 접수 완료를 표시하지 않는다.
- [ ] 외부 이메일·전화·기관 API 전송이 발생하지 않는다.
- [ ] DB schema/migration diff가 없다.

## 7. 검증 명령

~~~powershell
# Frontend
Set-Location MVP_v3/frontend
npm.cmd run typecheck
npm.cmd run build

# Backend syntax/contract smoke check
Set-Location ..
python -m compileall -q backend/contracts backend/ai_api/app backend/general_api/app

# Runtime health
Invoke-RestMethod http://127.0.0.1:8100/health
Invoke-RestMethod http://127.0.0.1:8101/health
Invoke-RestMethod http://127.0.0.1:8101/readiness

# Working tree and migration guard
git diff --check
git status --short
git diff --name-only -- database migrations backend/database
~~~

## 8. 완료 판정

이 문서의 AI 기능을 `연결됨`으로 변경하려면 다음을 모두 만족해야 한다.

- [ ] 최신 서버 재시작 후 OpenAPI 계약이 현재 소스와 일치한다.
- [ ] 정상 입력 1건과 빈/경계 입력 1건을 통과한다.
- [ ] 실제 Case payload를 통과한다.
- [ ] Provider 실패·timeout·계약 실패 시 기존 데이터가 보존된다.
- [ ] 화면에 올바른 결과가 표시되고 고객 채널로 누출되지 않는다.
- [ ] 새로고침 후 필요한 상태가 복원된다.
- [ ] DB schema/migration 변경이 없다.
- [ ] 재현 명령, request id, 기대 응답, 실제 응답을 이력에 남긴다.

## 9. 관련 문서·코드

- `MVP_v3/docs/31_AI_RUNTIME_ERROR_CONTRACT.md`
- `MVP_v3/docs/09_CASE_CONTEXT_DATA_CONTRACT.md`
- `MVP_v3/docs/10_FINAL_CASE_REPORT_CONTRACT.md`
- `MVP_v3/docs/07_CUSTOMER_PROGRESS_AND_AI.md`
- `MVP_v3/backend/general_api/app/clients/diagnosis_ai.py`
- `MVP_v3/backend/general_api/app/main.py`
- `MVP_v3/backend/ai_api/app/main.py`
- `MVP_v3/backend/ai_api/app/domains/case_support/work_card_service.py`
- `MVP_v3/backend/ai_api/app/domains/case_support/copilot_service.py`
- `MVP_v3/frontend/src/components/CaseActionDialogs.tsx`
- `MVP_v3/frontend/src/components/SharedConversation.tsx`
