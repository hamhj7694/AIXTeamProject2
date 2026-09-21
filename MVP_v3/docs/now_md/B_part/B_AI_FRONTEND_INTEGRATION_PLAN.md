# B Part AI Frontend Integration Plan

작성일: 2026-09-19. **READ-ONLY 코드 분석 결과와 향후 구현 계획**이다. 이 문서 작성 외 코드·계약·설정·기존 문서를 변경하지 않았다.

## 1. 목표와 판단 기준

기존 B Part 기능을 이용해 다음 흐름을 실제 은행·고객 화면에서 연결한다.

```text
Case Context → Bank AI → 확인 필요사항 → 질문 추천
→ 담당자 검토·수정·선택 → 질문 등록 → 고객 순차 노출
→ 고객 답변 → 답변 구조화·Fact 후보 → 의미 상태·Eligibility 재평가
→ 필요 시 qf1 검토 초안 → 담당자 등록 → 후속 답변
→ 갱신된 Context를 읽는 다음 Bank AI
```

현재 브랜치 코드가 구현 판단의 기준이다. 첨부 화면은 사용자가 관찰한 UI 증거로 사용하며, 해당 화면의 실행 서버가 현재 HEAD와 동일했는지는 확인되지 않았다. API 호출 코드, 테스트 코드의 존재, 실제 REST/MySQL/Live AI 성공을 각각 구분한다.

의미 계약은 유지한다: `ANSWERED != SUFFICIENT`, `PROPOSED != CONFIRMED`, `CUSTOMER_STATEMENT != VERIFIED FACT`, `CUSTOMER_REPORTED_COMPLETED != VERIFIED_COMPLETED`, `UNKNOWN != FALSE`, `Question Lifecycle != Semantic State`. 명확한 고객 진술의 기본 문진 충분성과 객관적 사실 검증도 별개다.

### 1.1 진행 전략: 기능 안정화 후 AI 품질 고도화

Integration은 다음 두 단계로 진행한다.

1. **1차 기능 안정화:** Case Context → Bank AI 기본 호출 → AI 질문 추천 → 담당자 검토·등록 → 고객 순차 노출·답변 저장 → Context 반영 → qf1/후속 질문 → 갱신 Context 기반 다음 Bank AI → Browser E2E의 핵심 Workflow가 끊기지 않게 한다.
2. **2차 AI 품질 고도화:** Workflow 연결 후 Bank AI의 직접성·사건 요약 과다·requester/화자/이름 해석·conversation self-introduction 정책·한국어 일관성·답변 형식과 길이·quality evaluator 정밀화·실패 UX를 별도 Backlog로 다룬다.

판단 기준은 “핵심 Workflow 진행을 막는가?”다. AI API/provider 호출 반복 실패, AI_RESPONSE 저장 실패, 질문 추천·등록·답변 저장·Context 반영·qf1 흐름 단절, 새로고침 뒤 핵심 상태 소실은 1차에서 처리한다. 반대로 Workflow가 진행되는 상태의 장황함, 세부 directness, 일반 대화 기억·referent 해석, 외국어 혼입, 오류 배너 UX는 삭제하지 않고 2차 Backlog로 보류한다. 단, CSR 업무성 질문에서도 AI가 반복적으로 503으로 실패하면 품질 문제가 아니라 기능 안정성 문제로 1차에서 계속 처리한다.

## 2. 현재 실제 상태

### 2.1 Git·분석 환경

| 항목 | 확인 결과 |
|---|---|
| 브랜치 | `feat/b-ai-integration-workflow` |
| HEAD | `ed83080fcd5760ba7895d20b950bf47d5b51cc1a` |
| 시작 Git 상태 | `nothing to commit, working tree clean` |
| 수행 | PowerShell을 통한 코드·설정·테스트·문서 읽기, 첨부 5장 대조 |
| Python 환경 | `MVP_v3/.venv` 존재. 현재 셸의 `VIRTUAL_ENV`, `CONDA_PREFIX`는 비어 있음 |
| 실행 제한 | Python/테스트/빌드/서버/브라우저 조작/REST/DB/유료 LLM 호출 미실행. 실제 interpreter 검증도 미실행 |
| 변경 허용 | 이 Plan MD 신규 작성만. 패키지 설치·환경 변경·commit·push 없음 |

이 문서의 코드 경로는 별도 표시가 없으면 **`MVP_v3/` 기준**, 줄 번호는 위 HEAD 기준이다. 기존 AGENTS의 상태 문서 갱신·실행 검증 일반 규칙보다 이번 요청의 문서 1개 작성 및 READ-ONLY 제한을 우선했다.

### 2.2 구현 여부를 현재 코드에서 확인한 범위

| 기반 기능 | 현재 코드상 상태 | 실행 판정 |
|---|---|---|
| P3-1 Semantic State | `QuestionStateEvaluator.evaluate` 구현 | 현재 실행 통과 여부 미검증 |
| P3-2 Eligibility | `QuestionPolicy`와 `CaseSnapshotAiAdapter.question_eligibilities` 연결 | 현재 REST/MySQL 미검증 |
| P3-3 Dynamic Follow-up | qf1 helper, parent 선정, LLM 초안, 재검증, 등록·답변 저장 구현 | Frontend 초안 보존 단절 확인 |
| P3-4 Source-aware Copilot | typed `BankCopilotSourceContext`, General 전달, provider 입력, quality 검사 구현 | 과거 문서의 “구현 전” 상태와 다름. Live AI 미검증 |
| 고객 질문 Queue | PENDING 생성, 1개 ASKED, 답변 후 다음 dispatch 구현 | 화면 04·05에서 순차 표시 관찰 |
| 담당자 질문·답변 조회 | 전용 GET과 bundle에 데이터 존재, 화면이 bundle 수신 | 담당자 대화창의 표시 단절 확인 |

### 2.3 첨부 Browser 관찰

| 화면 | 관찰한 사실 | 화면만으로 확정할 수 없는 것 |
|---|---|---|
| 01_BANK_ROOM_AI_FAILURE | 은행 AI 요청 UI, 저장 후 실패 배너. 말미에 “AI 응답이 역할·안전 기준을 충족하지 않아 전달하지 않았습니다.” 표시 | 실제 HTTP 상태, provider 응답, 실패 criterion, 네트워크 장애 여부 |
| 02_BANK_QUESTION_REVIEW_MODAL | 후보·복수 선택·편집·삭제·직접 추가·AI 추천 버튼·4개 전달 버튼 | 표시된 후보의 Live AI 생성 여부와 출처 |
| 03_BANK_AFTER_QUESTION_SEND | 담당자 대화창에서 등록 질문·상태·답변 관계가 드러나지 않음 | DB 저장 누락이라고 단정할 수 없음 |
| 04_CUSTOMER_QUESTION_CARD_PENDING | 1/4 카드, 선택지·직접 입력·답변 보내기, 답변할 질문 4개 | 4개 모두 ASKED라는 의미가 아님 |
| 05_CUSTOMER_ANSWERED_AND_NEXT | 첫 질문과 “잘 모르겠어요” 답변을 함께 보존, 다음 2/4 카드, 남은 3개 | 충분성 확보·Fact 확정·공식 업무 완료를 뜻하지 않음 |

이번 분석에서 브라우저를 새로 실행하거나 위 현상을 재현하지 않았다. 오른쪽 사건 맥락 패널의 외형·빈 표시 원인은 이번 개선 대상에서 제외한다.

## 3. CONFIRMED BUG / INTEGRATION GAP

### B1. CONFIRMED BUG — 유효한 qf1 초안이 재조정 과정에서 제거됨

코드만으로 입력과 제거 조건을 연결할 수 있다.

1. `ai_api/app/domains/case_support/work_card_service.py:193`은 허용된 parent에 대해 LLM 질문을 생성하고 `question_id`, `target_field`를 서버 qf1 값으로 고정한다.
2. `general_api/app/main.py:948`의 `filter_contextual_questions`는 유효한 qf1을 그대로 반환한다. 일반 contextual 질문만 `ai-context-*`로 바꾼다.
3. `frontend/src/components/CaseActionDialogs.tsx:112`는 work-card 질문을 합친 직후 `questionCandidates`를 다시 읽고 `reconcileQuestionDraft`를 호출한다.
4. 같은 파일 `:31–45`의 보존 조건은 `staff-*`, `ai-context-*`, 또는 authoritative 목록에 **동일 target**이 있는 경우다. qf1 전용 보존 조건은 없다.
5. authoritative GET은 snapshot의 deterministic basic 후보와 정적 basic 후보를 합친다(`main.py:1154`). `QuestionIntelligenceService`의 후보 target은 기본 `TargetField`이며 qf1 생성은 work-card 경로에 있다.

따라서 예를 들어 `qf1:transfer_status:question-parent`를 받은 후 기본 후보 목록으로 reconcile하면 그 초안과 선택 상태가 삭제된다. 로컬 저장 초안을 다시 여는 과정에도 같은 조건이 적용된다. 이는 **현재 코드의 조건부 실행 경로로 확정한 버그**이며, 실제 Live AI가 해당 초안을 반환한 Browser 재현은 별도 필요하다.

최소 해결 방향: 서버가 검증한 follow-up 검토 초안을 기본 후보 목록과 구분해 보존한다. 단순 무조건 보존으로 끝내지 않고 parent·scope·active question의 최신 유효성 및 등록 시 서버 재검증을 유지한다. UI가 semantic eligibility를 독자 구현하지 않는다.

### G1. INTEGRATION GAP — 담당자 질문·답변 가시성 단절

- Repository: 질문의 상태·순번·원문·답변·시각·답변 메시지 ID·구조화 payload를 조회한다.
- General: `GET /api/cases/{id}/customer-questions`와 `/bundle?view=bank`가 이미 존재한다. bundle의 `questions`, `progress_items`에도 질문과 답변 수가 포함된다(`main.py:1179`, `:2609`). 답변 전용 신규 API가 없어도 질문 자원에서 답변을 읽을 수 있다.
- Frontend: `casesApi.bundle`로 이미 수신하며 `CaseRoomPage.tsx:38`은 질문 상태·답변 변화를 refresh signature에도 반영한다.
- `frontend/src/timeline.ts:24–37`은 중복 방지를 위해 질문 원문 메시지와 answer_message_id의 메시지를 제거한 뒤 QUESTION/ANSWER entry로 대체한다.
- 그러나 `SharedConversation.tsx:190–196`은 MESSAGE 외 모든 entry를 제거하고 `:214`는 MessageEntry만 렌더링한다. 기존 질문 카드 렌더 코드가 파일에 남아 있어도 현재 렌더 경로에서 사용되지 않는다.
- PENDING 질문은 `asked_at`이 없으므로 기존 timeline에도 entry가 생기지 않는다. 단순히 필터 하나를 제거하는 것만으로 전체 Queue 가시성 요구가 해결되지는 않는다.

**주원인은 현재 Frontend 표시 통합의 누락**이다. 질문·답변 핵심 read model이나 Repository가 없다는 문제가 아니다. 최소 필요 정보는 등록 수, 질문 원문, PENDING/ASKED/ANSWERED 구분, 현재 질문, 질문별 답변, 답변 시각이다. 이 단계에서 카드·목록·패널 등 UI 형태는 결정하지 않는다.

### G2. INTEGRATION GAP — 질문 추천 경로의 provenance는 Copilot 경로보다 축약됨

`merge_support_records` → `_case_support_ai_input` → `CaseSnapshotFact`는 Fact를 `fact_id/field/value/status`로 축약한다. source_kind, evidence_refs, version, timestamp, supersedes 관계는 이 경로에 없다. `question_state`는 typed DTO이지만 완전한 source-aware context는 아니다.

`CaseSnapshotAiAdapter.question_eligibilities`는 evaluator의 conflict/correction 플래그와 verification_scope를 production 입력에서 연결하지 않는다. 같은 scope의 질문이 여러 개면 단일 대표 질문을 임의로 고르지 않는다. 따라서 parent와 follow-up 모두 ANSWERED라는 이유로 현재 의미 상태가 SUFFICIENT라고 결론 낼 수 없다. 이 보수적 처리는 오확정을 막지만 복수 기록의 current 관계를 해석하는 통합은 제한적이다.

추천 결과의 `PublicQuestionCandidateResponse`에는 generator source/evidence 필드가 없다. work-card 응답의 `model_mode`, `context_sources`, `warnings`는 카드 단위이고, QuestionDialog는 주로 `questions`만 취한다. 등록 후 `source=BANK_SELECTED`는 **담당자 등록 경로**를 뜻하며 “LLM이 생성했다”는 provenance가 아니다.

최소 해결 방향: 핵심 시나리오에서 실제로 필요한 source·current 관계가 무엇인지 먼저 fixture로 검증한다. 필요하면 기존 내부 snapshot/adapter에 한정해 보완한다. Copilot에 이미 존재하는 typed 계약을 다시 만들거나 모든 public DTO/DB를 일괄 확장하지 않는다.

### G3. INTEGRATION GAP — 실패 표시가 provider 무응답과 quality 차단을 같은 문구로 묶음

`CaseRoomPage.tsx`의 AI 실패 catch는 공통 “실제 AI 서버가 응답하지 않았습니다” 안내에 상세 오류를 덧붙인다. 반면 quality 차단은 provider의 텍스트 응답을 받은 **후** 발생한다(`copilot_service.py:428–447`). 화면 01의 문구 조합은 이 차이를 드러내지 못한다.

실제 차단 사유를 확보한 뒤 서버 오류 코드와 화면 안내의 구분을 최소 범위에서 검토한다. quality guard를 제거하거나 실패를 임시 답변으로 가리지 않는다.

## 4. 기능별 실제 호출·데이터 흐름

### 4.1 Bank AI와 실패 경계

```text
CaseRoomPage: 메시지 저장 / @AI·AI 요청 → enqueueAiReply
→ casesApi.invokeAi → POST /api/cases/{id}/ai/invocations
→ General: Case·Facts·Questions·Messages·V2 resources·Verification 재조회
→ bank_source_context + 문자열 보조 context
→ HttpDiagnosisAiClient.generate_case_copilot_reply
→ POST /ai/case-copilot/replies
→ CaseCopilotInput 검증 → CaseCopilotService.generate
→ OpenAI Responses → output_text → CopilotQualityEvaluator
→ 성공 시 General이 은행 내부 AI_RESPONSE 저장 → Frontend 표시
```

일반 은행 응답은 Live LLM 경로다. 예외적으로 담당자 조회 질문은 `SHARED_CASE_LOOKUP` 결정론적 응답을 사용한다. 파일 안의 `_bank_case_fallback` 함수 존재를 장애 시 호출 증거로 해석하면 안 된다. 현재 generate의 provider 실패는 오류로 전달된다.

| 경계 | 현재 처리 | 다음 검증 |
|---|---|---|
| 브라우저 → General | `api/client.ts` fetch, 네트워크 실패와 HTTP 오류 표시. 별도 AbortController timeout 없음 | 실제 요청 URL·HTTP status·body, 저장/AI 요청 분리 확인 |
| General → AI | `AI_API_BASE_URL`, 기본 HTTP timeout 120초. 401/429 별도 예외, 기타 실패 AiServiceError | 실행 중 프로세스/배포본/유효 설정 일치 확인 |
| 응답 parsing | `response.json()` 및 실패 body의 `detail.get` 가정 | non-JSON, detail이 list/string, 성공 body 필드 누락 시 정규 오류로 처리되는지. 현재 catch는 주로 httpx 예외이므로 별도 검증 필요 |
| AI 입력 계약 | Pydantic case/mode 경계 및 source_context 검증 | 422 body가 General 오류 처리에 들어가는 경우 확인 |
| AI → provider | 기본 timeout 20초, Copilot `max_retries=0`; 인증·quota 구분 | 실제 모델·timeout override·provider 결과 확인 |
| provider 응답 | 빈 텍스트 오류, 그 후 quality 검사 | 안전한 재현 자료로 원응답과 차단 criterion 대조 |
| quality 차단 | role_adherence/internal_visibility/unsupported_certainty/unsafe_instruction 실패는 전달 차단 | 정당한 차단인지 false positive인지 구분 |
| General 오류 매핑 | 401 인증, 429 quota, 503 `AI_CASE_COPILOT_FAILED` | 실제 화면 01 요청과 로그 상관관계 확인 |

화면 01의 상세 문구는 현재 quality 차단 예외와 일치하므로 그 경로를 **우선 조사**한다. 화면만으로 provider에 연결되지 않았다고 결론 내리지 않는다. 어떤 응답·criterion이 원인인지는 `VERIFICATION NEEDED`다.

### 4.2 기본 후보와 “AI에게 질문 추천 받기”는 다른 경로

| 구분 | 실제 흐름 | 생성 방식 |
|---|---|---|
| 모달 initial | Case support의 recommended_questions | snapshot 기반 deterministic 후보 |
| 열기·재조회 | GET customer-question-candidates → support snapshot + build_customer_question_candidates → 최신 policy 필터 | deterministic 후보 + 정적 basic 보충. 보충은 장애 때만이 아니라 미포함 target에도 수행 |
| AI 추천 버튼 | QuestionDialog.recommendQuestions → POST ai/work-cards, QUESTION_PLAN + 현재 초안 → General → POST /ai/work-cards/generate | Live LLM 추가 질문 또는 서버 선정 parent의 follow-up |
| 담당자 등록 | 선택된 chosen → POST customer-questions | 담당자 명시 동작. 추천 함수는 queue를 호출하지 않음 |

snapshot 내부 호출은 `/ai/case-support/snapshot` → `CaseSnapshotAiAdapter.build_presentation` → workflow brief/QuestionIntelligenceService다. AI API를 호출한다는 이유만으로 Live LLM 추천이라고 부르지 않는다. diagnosis가 없으면 adapter가 빈 presentation을 반환할 수 있고 basic 보충 경로가 남는다.

일반 QUESTION_PLAN provider 입력에는 Case summary, support.case_context를 문자열화한 known_facts, 최근 대화, 기존 질문·답변, 현재 초안, retrieved/staff context, question_candidates와 `question_state`가 들어간다. 단, known_facts 등은 개수 제한이 있다. follow-up 생성 시 provider 입력은 **서버 선정 scope, UNCERTAIN state, parent 질문·답변, 확인 목적**으로 좁혀진다. 전체 source_context가 전달되는 것은 아니다.

WorkCardService는 키 없음·provider 오류·JSON parsing/검증 실패를 오류로 반환한다. `_fill_empty_proposal`은 제목 등 빈 보조 필드를 규칙 기반으로 채우지만 QUESTION_PLAN의 빈 questions를 fallback 질문으로 채우지 않는다. `RULE_BASED_FALLBACK` 객체·helper의 존재와 실제 장애 fallback 반환을 구분한다. 성공해도 필터 후 questions가 비어 있을 수 있다.

### 4.3 등록·Lifecycle·고객 노출

```text
담당자 선택 → General queue_customer_questions
→ qf1이면 최신 parent/eligibility 검증
→ Repository 중복 검사·PENDING 저장
→ dispatch_next_customer_question_message
→ Repository: ASKED가 없을 때만 sequence상 첫 PENDING을 ASKED로 변경
→ 고객 공개 질문 메시지 생성·question_message_id 연결
→ customer bundle polling → buildCustomerTimeline → ASKED 카드만 표시
```

근거: `main.py:1188–1211`, `:1249`; InMemory `repository.py:629`, `:697`; MySQL `mysql_repository.py:976`, `:1013`; `frontend/src/customer/timeline.ts:33`; `CustomerConversation.tsx:43`.

| 상태 | 생성/전이 조건 |
|---|---|
| PENDING | 담당자가 등록한 새 질문. MySQL은 Case row lock 아래 sequence 부여·중복 보호 |
| ASKED | 기존 ASKED가 없고 대기 질문이 있을 때 하나만 dispatch. 단순 조회나 카드 렌더가 상태를 바꾸지 않음 |
| ANSWERED | 현재 ASKED 질문에 답변을 commit. 이미 저장한 동일 답변의 재시도와 다른 답변 충돌을 구분 |
| SKIPPED | DTO·정책·조회·테스트에서 지원하나 현재 추적한 production endpoint/Repository에 질문을 SKIPPED로 변경하는 동작은 발견하지 못함. 새 skip 기능은 이번 범위에 추가하지 않음 |

4개 등록 직후 DB의 정상 기대값은 ASKED 1개 + PENDING 3개다(기존 active 질문이 없을 때). POST 반환 객체는 dispatch 전 상태일 수 있으므로 최종 상태는 후속 GET/bundle/DB로 검증한다. 고객 화면 분모는 SKIPPED 제외 질문 수, 현재 위치는 answeredCount + 1이다.

등록 commit, ASKED 변경, 질문 메시지 append·link는 하나의 거대한 트랜잭션이 아니다. 중간 실패 복구와 재시도는 MySQL 검증 대상으로 둔다. 이것이 첨부 증상의 실제 원인이라고 단정하지 않는다.

### 4.4 고객 답변 → Fact → Semantic State → Context

```text
CustomerQuestionCard: option IDs + free_text + question_version
→ CustomerCaseRoomPage.answer → POST customer-questions/{question_id}/answer
→ General: 질문 version·option·복수 선택 검증, labels+free_text를 answer_text로 결합
→ submit_customer_answer: 원답변 메시지 + ANSWERED + legacy PROPOSED Fact + events 저장
→ _persist_structured_answer_fact: canonical scope의 명확한 답변만 V2 Fact 후보 생성
→ context extraction job enqueue(추가 경로)
→ 다음 대기 질문 dispatch → 고객 refresh / 은행 polling
→ 다음 support/candidate 요청에서 저장된 질문·Fact를 읽고 evaluator/policy 재평가
```

근거: `main.py:1265–1376`, `mysql_repository.py:1061–1117`, `case_context_v2_repository.py:630`, `answer_service.py:16`.

- Answer Structure는 여기서 LLM 호출이 아닌 `CustomerAnswerStructuringService`의 결정론적 처리다. 실제 송금, 개인정보·인증정보 제공, 원격 앱 설치의 명확한 진술을 제한적으로 변환한다.
- “잘 모르겠어요”는 raw answer를 저장하고 lifecycle은 ANSWERED가 되지만, 명확한 V2 값으로 강제 변환하지 않는다. 기본 질문 하나와 연결된 현재 답변이면 evaluator가 UNCERTAIN으로 판단할 수 있다.
- legacy Fact는 `source=AI_EXTRACTED`, `status=PROPOSED`, source_question_id와 evidence_message_id를 저장한다. 명확한 구조화 V2 Fact는 `source_kind=CUSTOMER_STATEMENT`, `status=PROPOSED`, QUESTION_ANSWER evidence reference를 사용한다. 두 저장 표현의 출처 이름이 같지 않다는 점도 보존한다.
- V2 추가 저장이나 extraction enqueue가 실패해도 이미 commit한 raw answer를 취소하지 않고 로그를 남긴다. 답변 성공 HTTP만으로 모든 Context 처리가 성공했다고 판정하면 안 된다.
- semantic state는 별도 상태 컬럼에 무조건 덮어쓰는 방식이 아니라 read/생성 시 evaluator 결과로 계산된다. MySQL에서는 013/014/015 migration의 revision trigger와 `ContextProjectionRepository`의 lease/cache가 support 재생성에 관여한다.
- support의 `CURRENT`, `UPDATING`, `STALE`, `FAILED`와 source/projection revision을 확인해야 한다. `available=true`가 반드시 최신이라는 뜻은 아니다.
- 다음 PENDING dispatch는 Queue 진행이다. 모든 대기 질문을 최신 충분성으로 재심사해 자동 제거하는 흐름은 이 dispatch 함수에 없다.

### 4.5 Dynamic Follow-up의 현재 범위와 이후 상태

`contracts/question_target.py`가 encode/decode/canonical scope와 등록 구조 검사를 담당한다. parent는 같은 Case의 실제 ANSWERED 기본 질문이어야 한다. `CaseSnapshotAiAdapter.follow_up_parents`는 policy가 허용한 UNCERTAIN parent를 선택한다. PENDING/ASKED 동일 scope, 기존 follow-up, 잘못된 parent는 차단한다. 자식은 다시 parent가 되지 않는다.

WorkCardService가 질문 문장·reason·options를 생성한 뒤 서버가 qf1을 설정하고 안전성을 검사한다. General은 provider 대기 이후 최신 상태로 다시 필터링하며, 담당자 등록 시에도 재검증한다. 현재 Frontend는 B1 때문에 검토 초안을 잃는다.

등록·답변까지 진행되면 child 질문은 고유 question_id와 qf1 target으로 보존된다. Fact에는 canonical scope와 child source_question_id를 사용하며 parent의 raw answer를 자동 정정하지 않는다. “확인할 수 있어요” 같은 확인 가능성 답변을 실제 이체 Fact로 만들지 않는 테스트도 있다.

child 답변 이후 동일 scope에 parent/child 복수 기록이 생기므로 `question_eligibilities`가 단일 질문을 고르지 않는 조건과 함께 검증해야 한다. 현재 구현을 “최신 child 답변이 자동 current로 승격되어 충분성이 확정됨”이라고 설명하지 않는다. 추가 follow-up 자동 반복도 기대하지 않는다.

### 4.6 갱신 Context → 다음 Bank Copilot의 provenance

다음 `invoke_case_copilot`는 매번 Repository와 V2 resources를 다시 읽는다. Frontend가 이전 snapshot을 그대로 재전송하는 구조가 아니다. 따라서 새 질문·답변·Fact가 다음 요청에 포함될 코드 경로는 있다.

```text
V2 resources + legacy facts + questions/answers + verifications + human messages
→ case_retrieval.bank_source_context
→ BankCopilotSourceContext / CaseCopilotInput.source_context
→ AI API → _context_sections의 typed JSON → provider
→ 동일 source_context를 CopilotQualityEvaluator에도 전달
```

근거: `case_retrieval.py:198–235`, `main.py:1824–1865`, `contracts/ai_internal/case_copilot.py`, `copilot_service.py:211`, `:348`, `:432`.

V2 Fact의 source_kind/status/evidence_refs/version/created_at/updated_at/supersedes_fact_id를 보존한다. legacy Fact, Q/A parent 연결, Verification version·결과·근거 URL도 별도 typed 항목이다. provider 입력이 JSON 텍스트가 되는 것은 필드가 제거된 list[str] 축약과 다르다. 기존 문자열 보조 context는 남지만 typed context 우선 지시 및 검사 경로가 존재한다.

제한: facts 각 100개, questions 50개, verifications 20개, messages 20개 등 bounded input이다. `truncated`와 원자료 누락을 고려해야 한다. current/superseded를 timestamp만으로 결정하거나 없는 conflict 관계를 생성하지 않는다. EvidenceRef는 원본 거래 증빙 자체가 아니다. Bank Copilot에는 evaluator의 semantic-state 결과 전체를 직접 전달하는 필드가 없고, 갱신된 원자료를 제공한다. strict snapshot 일관성은 별도 검증이 필요하다.

## 5. VERIFICATION NEEDED

| ID | 확인해야 할 것 | 필요한 증거 |
|---|---|---|
| V1 | 화면 01의 실제 실패 원인 | 동일 HEAD 재현, 브라우저 status/body, General·AI 로그, provider 응답 및 quality failed criterion. 민감값을 제거한 기록 |
| V2 | 실제 실행 설정·배포 일치 | Frontend proxy/base URL, General AI base URL, 프로세스 HEAD, 모델·timeout의 유효 설정. 설정 파일 기본값과 런타임을 구분 |
| V3 | 질문 추천의 Live AI 성공·빈 결과·오류 구분 | work-card request/response, model_mode, 질문 생성·필터 결과. 화면 02 목록만으로 Live AI 성공 판정 금지 |
| V4 | qf1 전체 연결 | UNCERTAIN parent → 추천 → reconcile·재열기 → 편집·선택 → 등록 → 답변. invalid/stale parent도 포함 |
| V5 | MySQL 저장·조회와 동시성 | migration/trigger 적용 상태, raw answer·payload·Fact·evidence 연결, ASKED 단일성, 중복 등록·동일 답변 재시도·충돌 |
| V6 | Context 최신성 | answer 전후 context_revision, projection_revision/status, cache lease·stale 응답, extraction 실패·지연 시 raw answer 유지 |
| V7 | follow-up 이후 의미 상태 | parent/child 복수 기록, 명확/불확실/상충 답변, PROPOSED·CONFIRMED·검증 출처별 evaluator 입력·결과 |
| V8 | source-aware Copilot 실제 전달 | 답변 전후 source_context 차이, customer statement vs bank record, rejected/superseded, evidence revision mismatch, truncated 상태 |
| V9 | 오류 계약 내구성 | AI 401/429/503, timeout, 422 list detail, non-JSON 응답, 누락 필드가 사용자에게 잘못된 성공으로 보이지 않는지 |

설정의 정적 근거: `frontend/vite.config.ts`의 5176 → `/api` 8100 proxy, `docker-compose.yml`의 mysql Repository 및 AI API 8101 연결, `diagnosis_ai.py:51`의 기본 timeout. 실제 `.env` 비밀값은 출력하거나 문서화하지 않았다. 이번 분석은 런타임 설정 확인 완료를 주장하지 않는다.

## 6. DOCUMENT MISMATCH

| 문서 기록 | 현재 판단 |
|---|---|
| B_CURRENT_PROGRESS의 branch `feat/b-dynamic-question-plan-p3`, HEAD `39c7732` | 과거 baseline이다. 이번 branch/HEAD로 대체해 읽지 않음 |
| 같은 문서의 P3-4 “READY_FOR…IMPLEMENTATION”, typed provenance 미전달 | 현재 typed source_context와 provider/quality 연결 코드가 존재한다. “앞으로 전부 새로 구현” 계획은 부정확 |
| B_PART_FOUNDATION의 Frontend 기본 수정 금지 | 과거 P3 작업 경계. 이번 사용자 지시는 향후 최소 Frontend 수정 필요성을 Plan에 기록하도록 허용. 이번 턴에는 여전히 수정하지 않음 |
| B_part/README의 진행 문서를 현재 상태 기준으로 읽는 안내 | 이번 분석에서는 진행 이력 참고로만 사용 |
| PRD.md:672 부근의 P0 질문 자동 Queue 등록 | 현재 `run_proactive_case_automation`은 support/checklist 갱신만 하고 고객 queue/dispatch를 호출하지 않는다. 현재 코드와 이번 지시대로 담당자 검토·등록 유지 |

기존 문서는 수정하지 않는다. 과거 테스트 통과 수치도 이번 HEAD에서 다시 통과한 수치로 재사용하지 않는다.

## 7. 작업 우선순위·선행 의존 관계·예상 수정 범위

아래는 **후속 구현 작업의 계획**이며 이번 턴에 실행하지 않았다.

```text
S0 실행 기준 확보 → S1 Bank AI 실패 분리·복구 → S2 Queue/답변/Context REST·MySQL 기준 확보
                                                  ↓
                               S3 담당자 질문·답변 가시성
                                                  ↓
                               S4 qf1 검토 초안 연결·유효성 유지
                                                  ↓
                               S5 답변 이후 의미·출처 전달 검증/최소 보완
                                                  ↓
                               S6 Browser 전체 Workflow
```

S3의 표시 수정은 S1의 세부 AI 품질 고도화와 기술적으로 독립적이다. S1은 Bank AI가 CSR 업무성 질문에 기능적으로 사용 가능함을 확인하면 완료할 수 있으며, 남은 품질 문제는 2차 Backlog로 관리한다. 다만 최종 성공 기준을 혼동하지 않도록 S2의 저장·조회 baseline을 확보한 뒤 검증한다. S4 함수 수준 재현도 Live AI 없이 가능하지만 최종 수용에는 S1의 기능 안정화와 실제 추천 성공이 필요하다.

| 단계 | 작업·선행 조건 | 예상 수정 영역 | 완료 조건 |
|---|---|---|---|
| S0 | 현재 HEAD, 실행 서버, API 경로, MySQL migration 상태 확보 | 기본은 수정 없음. 실제 불일치가 확인될 때만 해당 실행 설정 | 코드 수정 불필요. REST health 및 DB schema/trigger 확인. 화면과 서버의 버전 기록 |
| S1 | V1/V9로 provider 실패와 quality 차단을 구분하고, 핵심 경로를 막는 원인만 수정 | AI API의 원인 지점 또는 General client/error mapping. Contracts·Frontend 실패 안내는 Workflow blocker일 때만 | Bank AI API/provider 호출, 정상 AI_RESPONSE 저장·담당자 ROOM 표시, 실패 시 임시 답변 미생성, requester 전달, grounding/certainty 경계 유지, CSR 업무성 Browser smoke test. 세부 답변 품질·실패 UX는 2차 Backlog로 분리 |
| S2 | 기존 질문·답변 API 기준 확보. 4개 등록·1개 답변·다음 dispatch·Context 갱신 | 우선 무수정 검증. 실패가 확인된 General/Repository 부분만 수정. migration 선제 추가 없음 | targeted Queue/Answer/Projection 테스트, 실제 REST, MySQL commit·재시도·revision 검증. 고객 UI 순차 표시 확인 |
| S3 | G1 해결. 기존 bundle로 등록·대기·현재·답변 관계 표시. S2 데이터 활용 | Frontend `CaseRoomPage`, `SharedConversation`, 필요 시 timeline/최소 view model. API·DB 추가는 기본적으로 불필요 | 실제 렌더 경로 test, 중복 메시지 방지, typecheck/build, 은행·고객 동시 Browser 확인. 별도 DB 구조 변경 없음 |
| S4 | B1 해결. 생성 직후·재열기·편집 후 qf1 보존 및 stale 후보 처리 | Frontend QuestionDialog 중심. 필요할 때 General의 후보 유효성 조회/응답 최소 보완. 기존 qf1 helper/등록 guard 재사용 | reconciliation targeted test, stale/동일 scope/잘못된 parent 거부, REST 등록·답변, MySQL parent 보존·중복 보호, Live AI→Browser 검토·등록 |
| S5 | G2/V6/V7/V8 검증. S4 child 답변까지 있어야 복수 기록 상태 평가 가능 | 필요성 확인 후 General snapshot builder, AI adapter, 내부 Contracts만 최소 보완. Copilot source_context 기존 구현 재사용. DB 변경은 실제 저장 필드 부족이 증명될 때만 | clear/uncertain/conflict/source별 targeted test, REST snapshot 및 다음 Bank AI 입력 비교, MySQL read-back·revision, Live AI 출처 표현. ANSWERED 자동 확정 금지 |
| S6 | S1–S5를 동일 Case에서 연결 | 통합 검증과 드러난 최소 결함 수정만 | 아래 Browser E2E 성공, REST/DB/AI 증거 연결, 기존 고객 공개 경계·실패 안전성 유지 |

선행 작업 없이 먼저 하지 않을 것: Bank AI 실패를 추측해 prompt만 교체하기, typed provenance 계약을 새로 중복 구축하기, 질문 조회 API를 새로 만들기, qf1을 무조건 보존하면서 등록 검증 제거하기, 화면 수용 시험을 대규모 UI 개편으로 확장하기.

## 8. Targeted test 계획과 증거 수준

현재 테스트 파일은 읽었으며 실행하지 않았다. 후속 작업에서는 프로젝트 `.venv` interpreter를 확인한 뒤 기존 관리 방식을 사용한다. AI/General suite의 `tests` package 충돌을 피하도록 suite별 실행한다.

| 영역 | 기존 테스트 활용 | 필요한 보강 |
|---|---|---|
| Frontend 질문 모달 | `frontend/scripts/test-question-dialog-stabilization.cjs` | 기존 케이스는 staff/basic/ai-context 보존 중심. qf1 생성 직후·reload·편집·stale 재검증 추가 |
| Frontend 질문 표시 | `frontend/scripts/test-question-report-cards.cjs` | 현재는 소스 문자열·CSS 존재 검사여서 실제 렌더 제외를 잡지 못함. bundle 입력부터 화면 출력까지 검증 |
| General follow-up | `backend/general_api/tests/test_dynamic_question_plan.py` | InMemory/AsyncMock 및 가짜 SQL cursor 검증을 실제 MySQL REST 결과와 구분 |
| Answer/Context | `test_customer_answer_structured_fact.py`, `test_case_support_snapshot_endpoint.py`, `test_contextual_question_plan.py` | raw answer commit 후 추가 처리 실패, revision/cache, parent/child 복수 답변 |
| Source 전달 | General `test_case_retrieval.py`, AI `test_copilot_fact_grounding.py` | 실제 provider에 전달된 입력과 응답의 source/status 대응 검증 |
| 의미·정책 | AI `test_question_state_evaluator.py`, `test_question_policy.py`, `test_dynamic_question_plan.py` | 실제 snapshot builder가 만든 입력으로 평가. evaluator 단독 fixture만으로 production 연결 완료 판정 금지 |
| runtime/MySQL | General `test_ai_runtime_contract.py`, `test_mysql_repository_integration.py` | 운영 데이터와 분리한 검증용 Case/DB에서 실제 실행. live 미실행 또는 skip을 PASS로 집계하지 않음 |

## 9. Browser E2E 최종 시나리오

1. 동일 HEAD의 은행·고객 화면과 검증용 Case를 준비한다. 고객 진술만 있는 항목, 미확인 항목을 포함하고 기준 revision을 기록한다.
2. Bank AI에 현재 확인된 내용과 추가 확인 필요사항을 요청한다. 정상 응답을 받으며 customer statement를 거래 검증 사실로 승격하지 않는지 확인한다. 실패 시 status·code·quality 원인을 기록한다.
3. 질문 모달을 연다. deterministic 기본 후보와 AI 버튼으로 생성된 질문을 구분해 기록한다. 추천만으로 DB Queue나 고객 화면이 바뀌지 않아야 한다.
4. 담당자가 질문을 편집·선택·등록한다. 4개 등록 시 담당자 화면에서 전체 등록·현재 질문·나머지 대기를 구분한다. DB는 기존 active가 없을 때 ASKED 1 + PENDING 3이어야 한다.
5. 고객은 첫 질문 1/4에 “잘 모르겠어요”를 답한다. ANSWERED와 원답변 연결, 이전 카드 유지, 다음 2/4 노출, 남은 3개를 확인한다. 담당자도 같은 Q/A 관계를 확인한다.
6. raw answer/payload/legacy PROPOSED Fact를 조회하고 명확하지 않은 V2 값을 강제 생성하지 않았는지 확인한다. snapshot revision·policy에서 해당 scope의 불확실성을 확인한다. 다음 Queue 진행과 의미 충분성은 별개로 기록한다.
7. AI 질문 추천을 다시 요청해 허용된 qf1 초안을 받는다. 모달 재열기와 문장 편집 후에도 target/parent/선택이 유지되어야 한다. 아직 고객에게 자동 전송되지 않아야 한다.
8. 다른 담당자·고객 동작으로 parent 조건이 달라진 경우 stale 초안 등록이 거부되는지 별도 분기로 검증한다. 정상 분기에서는 담당자가 등록하고 기존 ASKED 처리 이후 child가 순서대로 노출되는지 확인한다.
9. child에 명확한 사건 진술을 답한다. parent 답변은 보존하고 child 출처로 PROPOSED만 추가한다. “확인 가능”만 답한 대조 케이스에서는 실제 송금 사실을 생성하지 않아야 한다. 여러 기록의 의미 상태는 실제 evaluator 출력으로 확인한다.
10. 다음 Bank AI가 새 Q/A·Fact·근거를 다시 읽는지 요청 payload와 DB read-back을 비교한다. 고객 진술, 담당자 확인, BANK_RECORD, 연결된 Verification을 구별해 설명해야 한다. 제공되지 않은 Evidence를 확인했다고 말하면 실패다.
11. 양쪽 새로고침·재접속 후 상태를 재확인한다. 중복 클릭/동일 답변 재시도, AI 실패, extraction 지연에도 데이터 중복·raw answer 손실·거짓 성공·고객에게 은행 내부 정보 노출이 없어야 한다.

각 단계의 증거는 Case/question/message ID로 연결하되 공유 보고서에는 민감 원문·실제 자격증명을 포함하지 않는다. 화면 성공만으로 DB·LLM 내부 경로 성공을 대체하지 않는다.

## 10. NOT A BUG / EXPECTED BEHAVIOR

- 기본 질문이 deterministic/static이라는 이유만으로 버그가 아니다. AI 추천 버튼의 실제 Live 경로와 구분하면 된다.
- 여러 질문을 등록해도 하나씩 ASKED가 되는 것은 현재 Queue 계약이다.
- “잘 모르겠어요”도 답변 접수는 완료되므로 ANSWERED가 될 수 있다. 이는 충분성·검증 완료가 아니다.
- PROPOSED Fact 유지, quality 기준 미충족 응답 차단, AI 장애 시 임시 답변 미생성은 안전 계약이다.
- 추천·follow-up은 담당자 검토 초안이며 자동 고객 전송되지 않는다. parent당 제한과 child의 재귀 follow-up 금지도 현재 최소 계약이다.
- 명시적 current/conflict 연결이 없는 복수 기록을 최신 timestamp만으로 하나로 정하지 않는 것은 안전한 보수적 처리다. 필요한 관계 통합의 부족은 G2로 별도 관리한다.

## 11. 제외 범위와 이번 작업 종료 상태

이번 분석에서는 Plan 작성 외 구현을 수행하지 않는다. 기존 B Part 문서, AGENTS, CURRENT_STATUS, README도 수정하지 않는다.

후속 Integration 범위에서도 오른쪽 사건 맥락 패널 개선, 대규모 UI 재설계, 새 RAG/Vector DB/Agent/Fine-Tuning, 질문 자동 전송, AI 최종 판단, 자동 지급정지·거래차단·사건 종료는 제외한다. Official Corpus/Verification 고도화는 핵심 Workflow 안정화 이후 실제 필요성을 재평가한다.

완료 기준은 “코드가 존재함”이 아니라 단계별 targeted test와 필요한 REST/MySQL/Live AI/Browser 증거다. 이번 문서는 그 증거를 확보하기 위한 순서를 정리한 결과이며, 런타임 검증 완료 보고서가 아니다.
