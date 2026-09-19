# B Part AI Frontend Integration Checklist

작성일: 2026-09-19

기준 문서: [B_AI_FRONTEND_INTEGRATION_PLAN.md](B_AI_FRONTEND_INTEGRATION_PLAN.md)

Plan은 구조·문제·의존 관계·완료 기준을 관리하고, 이 Checklist는 실제 작업 단위와 진행 상태를 관리한다. 상세 근거와 설계는 Plan을 참조한다.

## 현재 진행 상태

**현재 전략은 “핵심 Workflow 완성 우선”이다. 작업 1·2는 DONE이며, 작업 2는 CSR 업무성 질문 Browser smoke test로 기능적 사용 가능성을 확인했다.** 세부 AI 품질 문제는 보류 — 기능 안정화 이후 고도화 Backlog로 관리하며, 작업 3~5는 아직 시작하지 않았다.

| 실제 작업 묶음 | 관련 Plan | 현재 상태 |
|---|---|---|
| 1. Runtime 확인 + Bank AI 실패 원인 진단 | S0 + S1 원인 진단 / V1·V2·V9 | DONE |
| 2. Bank AI 최소 수정 + 검증 | S1 수정·복구 | DONE |
| 3. 질문/답변 저장 흐름 검증 + 담당자 ROOM 가시성 | S2 + S3 | TODO |
| 4. qf1 수정 + Dynamic Follow-up 흐름 검증 | S4 + S5 follow-up 이후 의미 상태 | TODO |
| 5. Context / 출처 검증 + 전체 Browser E2E | S5 의미·출처 전달 + S6 | TODO |

문서 작성 시 브랜치는 `feat/b-ai-integration-workflow`, HEAD는 `ed83080fcd5760ba7895d20b950bf47d5b51cc1a`다. 이는 Git 기준 확인이며 실행 중 서버와의 일치 확인은 작업 1에서 수행한다. 시작 시 기존 Plan 파일은 미추적 상태였으며 이번 작업에서 수정하지 않는다.

### 진행 우선순위

1. **기능 안정화:** Bank AI 기본 호출부터 질문 추천·등록·고객 답변·Context 반영·qf1·갱신 Context 기반 다음 Bank AI·Browser E2E까지 핵심 Workflow가 끊기지 않게 한다.
2. **AI 품질 고도화:** Workflow가 연결된 뒤 직접성, 사건 요약 과다, requester/화자/이름의 세밀한 해석, conversation self-introduction, 한국어 일관성, 답변 형식·길이, quality evaluator 정밀화, AI 실패 UX를 별도 Backlog로 다룬다.

판단은 “Workflow 진행을 막는가?”로 한다. API/provider 반복 실패, AI_RESPONSE 저장 실패, 질문 추천·등록·답변 저장·Context 반영·qf1 흐름 단절, 새로고침 후 핵심 상태 소실은 지금 처리한다. Workflow가 진행되는 답변 품질 문제는 Backlog로 남긴다. 단, CSR 업무성 질문에서도 Bank AI가 반복적으로 503으로 실패하면 작업 2의 기능 안정성 문제다.

Plan의 READ-ONLY 분석 참고 사항: qf1 reconciliation 버그(B1), 담당자 질문·답변 렌더링 단절(G1), P3-4 typed provenance 코드의 존재가 기록되어 있다. 이 사실들은 아래 작업의 Runtime 검증 또는 DONE 근거가 아니다.

## 상태와 기록 규칙

| 상태 | 사용 기준 |
|---|---|
| TODO | 아직 시작하지 않음 |
| IN_PROGRESS | 일부 진행했으나 완료 조건 미충족. 추가 확인이 가능하면 이 상태 유지 |
| BLOCKED | 선행 조건·실행 환경·오류 때문에 더 진행할 수 없음. 원인과 재개 조건 기록 |
| DONE | 해당 작업의 모든 완료 조건을 실제 증거로 확인 |

- 코드 존재나 테스트 하나의 통과로 REST·MySQL·Live AI·Browser까지 완료 처리하지 않는다. 미실행·skip·미확인은 성공과 구분한다.
- 체크박스는 해당 항목을 실제 수행하고 근거를 남긴 경우에만 체크한다. 일부 완료라면 IN_PROGRESS, 진행 불가능하면 BLOCKED로 유지하며 모든 항목을 완료 표시하지 않는다.
- 결과에는 실행 일시, 대상 HEAD·환경, 변경 파일(있을 때), 검증 종류별 결과와 증거 위치, 미확인 사항을 간결하게 남긴다. 비밀값·민감 원문은 기록하지 않는다.
- 선행 작업 미착수만으로 후속 작업을 미리 BLOCKED로 바꾸지 않는다. 실제 착수 후 진행 불가능한 조건이 확인되면 기록한다.
- 이후 작업은 **Plan 확인 → Checklist 현재 작업 확인 → 해당 작업 수행 → 테스트/실행 결과 확인 → 해당 항목과 상태 요약 갱신** 순서로 진행한다.
- 새로운 구조·기능·상세 설계를 이 문서에서 만들지 않는다. Plan과 충돌하면 해당 항목에 충돌과 확인 필요 사항을 기록하고 새 기준으로 대체하지 않는다. 제외 범위와 의미 규칙은 Plan 1·11절을 따른다.

## 실제 작업 Checklist

### 1. Runtime 확인 + Bank AI 실패 원인 진단

**상태:** DONE

**관련 Plan:** S0, S1의 원인 진단 부분; V1·V2·V9, Plan 4.1절.

**목표:** 실행 환경과 HEAD의 일치를 확인하고 Bank AI 실패의 최초 경계와 원인을 증거로 특정한다. **이 작업에서는 Bank AI 코드를 수정하지 않는다.**

**확인/작업 항목:**

- [x] 현재 Git 기준과 실행 중 Frontend·General API·AI API의 코드 버전, 연결 경로, 유효 설정을 확인한다.
- [x] MySQL 연결 및 schema/migration/trigger 적용 기준을 확인한다.
- [x] Bank AI 실패를 재현하고 요청 HTTP status/body와 General·AI 로그를 같은 요청에 연결한다.
- [x] timeout·인증·quota·parsing·provider 실패·quality 차단을 구분해 최초 실패 경계를 확인한다. quality 차단이면 실제 응답과 failed criterion을 대조한다.
- [x] 확인된 원인, 재현 조건, 미확인 사항과 작업 2의 최소 수정 대상을 기록한다.

**완료 조건:** Runtime 기준과 DB 기준, 실패 재현 및 원인 증거가 연결되어 작업 2의 수정 대상을 정할 수 있어야 한다. 화면 오류 문구나 코드상 가능성만으로 DONE 처리하지 않는다. 재현·원인 확인이 부족하면 IN_PROGRESS, 환경 등으로 확인을 계속할 수 없으면 BLOCKED다.

**결과:**

- 확인 시각: 2026-09-19 15:41 KST. branch `feat/b-ai-integration-workflow`, HEAD `ed83080fcd5760ba7895d20b950bf47d5b51cc1a`. Plan·Checklist만 미추적 상태였고 추적 파일 변경은 없었다.
- 기존 Runtime 확인: Frontend PID 14876은 현재 `MVP_v3/frontend`의 Vite 실행 경로를 확인했다. General parent PID 5860과 AI parent PID 28176은 각각 `MVP_v3/.venv/Scripts/python.exe -m uvicorn ... --reload`로 실행 중이었다. reload child의 전역 Python 표시는 Windows venv launcher 동작과 일치하지만, 기존 프로세스에서는 작업 디렉터리·실제 import 경로·유효 환경과 요청 로그를 직접 확정할 수 없어 현재 HEAD 동일성 근거로 사용하지 않았다.
- 현재 checkout Runtime 확보: 기존 5176/8100/8101 서비스를 재시작하지 않고, 현재 `MVP_v3/backend`를 작업 디렉터리로 하여 프로젝트 `.venv`에서 General/AI 진단 Runtime을 18100/18101에 별도로 실행했다. 일회성 import 확인에서 `general_api.app.main`과 `ai_api.app.main`이 모두 현재 checkout의 실제 파일로 해석됐다. General은 진단 중 startup 자동 쓰기를 막기 위해 프로세스 환경에서만 `PROACTIVE_QUESTION_AUTOMATION=0`, AI 연결을 `http://127.0.0.1:18101`로 지정했다. 설정 파일·의존성·실행 스크립트는 변경하지 않았다. 두 health는 HTTP 200이었고 General은 `database=mysql`을 반환했다. 진단 로그를 확보했으며 종료 후 PID 14652/28332/28212/33688을 정리하고 18100/18101 포트가 닫힌 것을 확인했다.
- DB 기준: 읽기 전용 트랜잭션으로 `csr`, MySQL `8.4.11` 접속 성공. 현재 migration 21개가 모두 기록되어 누락이 없고 필요한 trigger 29개가 존재한다. `cases.context_revision`, 질문 상태·순번·답변 payload/version, Fact 연결·출처·상태·근거·버전 관련 필수 컬럼도 확인했다. 실제 trigger 발동과 데이터 정합성은 작업 3 범위로 남긴다.
- 실패 재현: 안전한 기존 Case에서 동일한 Bank AI 요청을 진단 General에 전송했다. 첫 요청은 General HTTP 503, General→AI 요청도 AI HTTP 503이었고 메시지 수는 전후 동일했다. 같은 요청의 두 번째 실행은 General HTTP 201, AI HTTP 200으로 성공해 실패가 간헐적임을 확인했다. 성공 경로 계약에 따라 AI 응답 메시지 1건이 해당 테스트 Case에 저장됐다. 추가 DB 쓰기를 피하기 위해 이후에는 현재 General 코드가 구성한 동일 payload를 메모리에서 캡처하고 append 전에 중단한 뒤 AI에 직접 재현했다.
- 성공한 마지막 경계: provider가 `gpt-4o-mini` 응답 text를 반환했고 `CopilotQualityEvaluator`가 이를 평가했다. 동일 payload의 정상 실행도 AI HTTP 200으로 확인했다.
- 최초 실패 경계: **D. provider 성공 후 quality guard 차단**. 직접 재현의 실패 응답은 AI HTTP 503, error code `AI_CASE_COPILOT_FAILED`였다. 평가 결과 `unsupported_certainty`와 비차단 항목 `conciseness`가 실패했고, runtime blocking criterion은 `unsupported_certainty`였다. General 실패 응답은 HTTP 503으로 매핑됐다. 요청별 General·AI access log가 같은 호출의 503을 기록했다.
- 원인 판정: **CONFIRMED**. provider text 반환과 evaluator 실행 뒤 `unsupported_certainty`가 차단한 증거가 있다. 확인한 실패에서는 timeout·authentication·quota/rate limit·provider 예외·parsing·API contract 오류가 최초 원인이 아니었다. 개인정보와 provider 전체 원문은 기록하지 않았다. `unsupported_certainty` 내부의 어느 세부 표현 조건이 발동했는지는 민감 원문을 남기지 않아 작업 2에서 최소 재현 fixture로 좁혀야 한다.
- 작업 2 최소 수정 예상 영역: `backend/ai_api/app/domains/case_support/copilot_service.py`의 출력 제약과 `copilot_quality.py`의 `unsupported_certainty` 판정을 실제 차단 문장과 대조한 뒤 둘 중 원인인 한 곳만 수정한다. 회귀 검증 후보는 `backend/ai_api/tests/test_copilot_fact_grounding.py`다. 현재 증거상 General error mapping과 Frontend는 최소 수정 대상이 아니다.

**Blocker:** 없음.

**다음 작업:** 별도 작업에서 작업 2를 시작한다. 실패를 만든 표현과 `unsupported_certainty`의 세부 조건을 개인정보 없는 최소 fixture로 고정한 뒤, prompt 또는 evaluator 중 확인된 원인만 수정하고 정당한 차단과 정상 응답을 함께 회귀 검증한다.

### 2. Bank AI 최소 수정 + 검증

**상태:** DONE

**관련 Plan:** S1의 수정·복구 부분; V1·V9, Plan 8절.

**목표:** Bank AI가 핵심 업무 흐름에서 기능적으로 사용 가능함을 확인한다. 답변 품질 완성은 이 작업의 완료 기준이 아니다.

**선행 조건:** 작업 1에서 실패 경계·원인·재현 조건이 충분히 확인되어야 한다.

**확인/작업 항목:**

- [x] 작업 1의 증거를 기준으로 최소 수정 범위를 정하고 해당 원인만 수정한다. 추정으로 prompt·quality evaluator·error mapping을 변경하지 않는다.
- [x] 원인에 대한 targeted test와 안전한 정상 응답·정당한 차단 회귀 검증을 수행한다.
- [x] 실제 REST·Live AI에서 복구를 확인하고 오류 응답과 메시지 저장 분리를 검증한다.
- [x] 현재 requester ID·표시 이름·역할을 General에서 내부 AI contract까지 전달하고, source-aware 최근 메시지의 작성자·channel·audience 경계를 보존한다.
- [x] Bank Copilot이 현재 질문과 1인칭 requester를 사건 인물보다 우선하도록 입력을 보강하고 synthetic 회귀 및 Live provider로 확인한다.
- [x] 담당자 ROOM에서 CSR 업무성 질문 Browser smoke test를 수행한다. 예: 확인된 위험 근거, 미확인 정보, 고객에게 추가 확인할 내용, 현재까지 확인된 사실의 간단한 정리. 정상 응답이 저장·표시되고 핵심 업무를 진행할 수 있는지 확인한다.

**완료 조건:** Bank AI API/provider 호출, 정상 AI_RESPONSE 저장·담당자 ROOM 표시, 실패 시 임시 답변 미생성, requester 전달, grounding/certainty 안전 경계가 유지되어야 한다. 이어 CSR 업무성 Browser smoke test에서 핵심 업무를 진행할 수 있을 정도의 응답을 확인해야 한다. 장황함·세부 directness·일반 대화 기억·이름 해석·외국어 혼입·오류 배너 UX는 기능 흐름을 막지 않는 한 이 완료 조건을 막지 않으며 Backlog로 관리한다. 일부 검증만 통과하면 IN_PROGRESS다.

**결과:**

- 확인 시각: 2026-09-19 16시대 KST. branch `feat/b-ai-integration-workflow`, HEAD `ed83080fcd5760ba7895d20b950bf47d5b51cc1a`. 작업 시작 시 코드 변경은 없고 Plan·Checklist만 미추적 상태였다. Plan은 수정하지 않았다.
- 수정 전 최소 재현: `CUSTOMER_STATEMENT + PROPOSED`인 synthetic 송금 진술에서 `고객은 ... 송금했다고 진술했습니다. 하지만 이 내용은 아직 확인된 상태가 아닙니다.`가 `unsupported_certainty`로 차단됐다. 반면 고객 진술을 객관적 송금 사실로 단정, PROPOSED를 확인 완료로 표현, 전달되지 않은 영수증 제출 주장도 각각 차단됐다.
- Gate 판정: **QUALITY EVALUATOR FALSE POSITIVE**. prompt는 이미 고객 진술 귀속과 미확인 상태 표현을 지시하고 있었고, 문제가 된 문장은 확정을 명시적으로 부정하므로 허용 대상이다. 정당한 위험 문장 차단은 계약상 타당했다.
- 최소 수정: `copilot_quality.py`의 source-aware absence 판정에 `확인된 상태가/는 아닙니다` 계열만 추가했다. prompt, General error mapping, Frontend, API Contract, DB는 변경하지 않았다.
- Targeted regression: `test_copilot_fact_grounding.py`에 정상 부정형 통과와 객관적 송금 단정·PROPOSED 확인 완료·미제공 영수증 주장의 차단을 함께 고정했다. source-aware/quality/directness 83개가 모두 통과했고 `conciseness`는 계속 비차단 기준이다. AI API 전체 unittest discovery는 259개를 실행했으나 현재 `.venv`에 `pytest`가 없어 pytest 의존 모듈 3개가 import error였으며, 이를 전체 PASS로 처리하지 않았다.
- REST·Live AI: 현재 checkout의 `MVP_v3/backend`와 프로젝트 `.venv`로 별도 AI/General Runtime을 18101/18100에 실행했다. synthetic 짧은 Bank AI 요청은 AI HTTP 200과 `gpt-4o-mini` 응답을 반환했다. 기존 안전한 Case의 General 호출은 첫 시도에 HTTP 201, 내부 AI 호출은 HTTP 200이었고 메시지 수가 10→11로 증가했다. 마지막 저장 메시지는 `AI_RESPONSE / BANK_AGENT / TEAM / BANK_INTERNAL`이었다. 성공 경로에 따라 AI 응답 1건이 테스트 Case에 추가됐다.
- 안전 경계: 같은 synthetic 입력에서도 provider가 근거보다 강한 표현을 생성한 경우 AI HTTP 503으로 계속 차단됐다. in-process Live 재현에서는 정상 응답이 전달됐고 `conciseness`만 실패해 비차단 계약을 확인했다. 위험한 확정 응답은 provider test에서 계속 예외가 발생하며 임시 답변을 만들지 않는다.
- Runtime 정리: 별도로 시작한 진단 Runtime의 wrapper와 listener만 종료했고 18100/18101 포트가 닫힌 것을 확인했다. 기존 5176/8100/8101 서비스는 재시작하지 않았으며 정리 후 모두 HTTP 200이었다.
- Browser 표시 확인: 사용자가 제공한 담당자 ROOM 화면과 기존 General API read-back을 대조해 `AI_RESPONSE / BANK_AGENT / TEAM / BANK_INTERNAL` 메시지가 새로고침 후 화면에 표시되는 것을 확인했다. 임시 Frontend 답변이 아니라 저장된 AI 응답이다. 이번 화면에는 실패 응답 경계 재현이 없어 실패 안내는 별도 미확인이다.
- 현재 질문 전달 경로: 담당자 TEAM 메시지를 먼저 저장한 뒤 Frontend가 같은 내용을 `은행 담당자의 질문:`으로 감싸 `prompt`에 넣어 General `invoke-ai`로 보낸다. General은 이 prompt와 Case 요약·참여자·검색 자료·최근 대화·미해결 항목·`source_context`를 AI `CaseCopilotInput`으로 조합한다. 따라서 질문 누락은 아니지만 같은 대화가 최근 대화와 source context에도 포함되어 큰 사건 맥락이 함께 전달된다.
- 직접성·맥락 우선순위 판정: `CONVERSATIONAL` 규칙은 이미 “먼저 질문에 직접 답하고 필요한 경우만 근거·다음 행동”을 요구한다. 그럼에도 짧은 `내가 누구야?`에 사건 요약과 후속 질문을 반환했으므로 **QUALITY GAP**이다. 질문이 긴 사건 맥락 뒤에 배치되고 맥락이 여러 표현으로 중복되어 모델이 사건 브리핑을 우선한 것이 기여 요인이지만, 현재 증거만으로 provider 내부 원인을 단정하지 않는다.
- 수정 전 화자·지시어 판정: Frontend 요청에는 `requester_user_id`와 `requester_display_name`이 있었지만 General이 AI contract로 전달하지 않았다. 최근 대화도 `표시 이름: 내용` 문자열로 평탄화되고 retrieval의 `CopilotMessage`는 `actor_type`만 보존하여 “현재 질문자”와 다른 참여자의 관계가 사라졌다. 이는 **CONFIRMED INTEGRATION GAP**이었고, 실제 저장 응답이 담당자의 자기소개 이름을 사칭 상대방 이름처럼 해석한 것은 이 경계에서 드러난 **CONFIRMED BUG**였다.
- 언어 일관성 판정: 실제 저장된 해당 응답에 한국어 문장 중 중국어 `请求`가 섞인 것을 확인했다. prompt의 자연스러운 한국어 규칙을 위반한 **QUALITY GAP**이며 화면 렌더링 문제는 아니다.
- Evaluator 통과 원인: blocking 기준은 role adherence·internal visibility·unsupported certainty·unsafe instruction뿐이다. relevance는 질문 또는 evidence 어느 쪽과든 어휘가 겹치면 통과하고 비차단이며, 사건 요약은 evidence와 겹친다. 응답은 현재 길이·문장·목록 임계값도 넘지 않는다. 현재 질문 직접 응답, `나/내`의 현재 requester 해석, 한국어 일관성을 검사하는 기준과 회귀 fixture가 없어 이 응답이 허용됐다.
- Requester 최소 구현: `CaseCopilotInput`에 optional `requester_user_id`, `requester_display_name`, `requester_role`을 추가해 기존 호출 호환성을 유지했다. General은 기존 public 요청의 ID·표시 이름과 Case member의 ACTIVE 역할을 내부 AI payload로 전달하며, 멤버를 찾지 못한 Bank 요청은 `BANK_STAFF`로 제한한다. public API·Frontend·DB schema·migration은 변경하지 않았다.
- 대화 역할 보존: `CopilotMessage`에 optional 작성자 ID·표시 이름·역할·channel·audience를 추가하고 `bank_source_context`에서 기존 저장 메시지 값을 그대로 매핑했다. 문자열 `recent_conversation`에도 표시 이름 뒤 작성자 역할을 붙여 담당자 자기소개와 고객의 사칭 상대 진술을 구분했다.
- 현재 질문 우선 처리: Bank provider 입력의 마지막을 `[현재 요청 - 최우선]` 블록으로 구성해 requester 표시 이름·역할·현재 질문을 함께 전달한다. 지시에는 1인칭을 현재 requester에 결속하고 requester 이름을 고객·사칭 상대 진술로 재분류하지 않으며 짧은 질문에 불필요한 사건 요약을 붙이지 않도록 추가했다. 명확한 1인칭 identity 질문은 기존 메인 담당자 조회와 같은 좁은 결정론적 `REQUESTER_LOOKUP` 경로에서 requester 이름만 답한다. 이름 자체나 예시 응답을 하드코딩하지 않는다.
- Requester regression: synthetic `김담당/이고객/박사칭` fixture에서 General payload의 requester와 실제 member 역할, source message의 actor·channel·audience, 결정론적 `내가 누구야?` 응답, provider input의 최우선 블록과 사건 맥락 뒤 배치를 검증했다. 고객 또는 사칭 상대 이름과 사건 요약이 identity 응답에 포함되지 않음을 함께 확인했다.
- Targeted test: requester·contract·General·Bank Copilot 관련 56개가 통과했다. 이어 source-aware grounding, quality, directness, customer progress prompt까지 합친 116개가 통과했다. 의도된 provider 장애 테스트의 예외 로그가 출력됐지만 해당 오류 경계 테스트를 포함한 최종 결과는 `OK`다. 기존 고객 진술 귀속, PROPOSED/CONFIRMED 구분, 미제공 Evidence 차단과 `unsupported_certainty` 정당한 차단이 유지됐다.
- REST·Live AI 추가 확인: 기존 8100/8101 health는 모두 HTTP 200이었다. AI REST에서 `내가 누구야?`는 HTTP 200과 `REQUESTER_LOOKUP`으로 현재 requester만 반환했다. 결정론적 경로가 아닌 `현재 요청자의 표시 이름을 한 문장으로 알려줘.`도 Live `gpt-4o-mini`가 HTTP 200으로 synthetic requester를 한 문장으로 직접 답했다. 유일한 실제 DB Case `VP-1`에는 진단 메시지를 추가하지 않아 이번 단계에서 General 저장 경로를 다시 쓰지는 않았다.
- 범위 보존: 새로운 directness/language blocking evaluator, 한자 금지 규칙, 전체 recent-message 재설계, Frontend, DB, 작업 3~5는 구현하지 않았다. 기존 언어 일관성 문제는 Browser 재검증 결과에 따라 별도 최소 보완 여부를 판단한다.
- Browser 재현 A (2026-09-19 08:26:43 UTC 저장 TEAM CHAT): 시스템 requester는 `mvp-v3-bank-operator / 은행 담당자 / CHAT_OPERATOR`이고, 담당자 자기소개 `내 이름은 박은행이야. 잘부탁해`는 `BANK_STAFF / TEAM / BANK_INTERNAL`으로 정상 저장됐다. 이어진 화면 배너의 정확한 문구는 `copilot_service.py`가 provider의 non-empty text를 받은 뒤 quality의 runtime blocking failure가 있을 때만 만드는 문구와 일치한다. 따라서 **provider text 반환 후 evaluator 차단**까지는 CONFIRMED이며, AI_RESPONSE와 MESSAGE_ADDED event가 없는 것도 차단 후 미저장 계약과 일치한다.
- Browser 재현 A의 criterion: Bank mode에서 `internal_visibility`는 항상 통과하므로 후보는 `role_adherence`, `unsupported_certainty`, `unsafe_instruction`뿐이다. provider 원문과 `failed_criteria`가 저장·로그화되지 않아 세 criterion 중 실제 최초 실패는 **VERIFICATION NEEDED**다. 이는 이전 `unsupported_certainty` 오탐과 같은 유형이라고 확정할 수 없다. 안전한 synthetic 자기소개 요청은 Live provider에서 HTTP 200으로 통과해, 자기소개 문장 자체가 결정론적으로 차단되는 것은 아님을 확인했다. 실제 Case 전체 맥락을 provider로 다시 전송해 원문을 재생성하는 진단은 민감 내부 맥락 외부 전송으로 자동 승인 검토에서 거절됐다.
- Browser 재현 B (08:27:06 UTC): 다음 질문 `내 이름이 뭔지 기억해?`는 provider path를 탔고, 저장된 AI_RESPONSE가 `BANK_STAFF`의 박은행 자기소개와 CUSTOMER의 테스터 이름을 고객·사칭 상대 맥락으로 섞어 사건 요약과 추가 질문을 반환했다. 저장 원문은 actor/user/display/role/channel/audience를 보존하며, General `recent_conversation`도 `은행 담당자 (CHAT_OPERATOR): ...`로, `source_context`도 같은 메타데이터로 전달한다. 따라서 **최초 의미 혼동은 저장·retrieval·source_context가 아니라 provider가 구조화되지 않은 conversation self-introduction을 해석하는 단계**다. 이는 현재 질문 직접성·화자 의미 해석의 **CONFIRMED QUALITY GAP**이고, conversation self-introduction을 authenticated identity와 별도로 모델링하지 않는 **INTEGRATION GAP**이 함께 있다.
- 세 identity 구분: authenticated/system requester는 member의 `은행 담당자 / CHAT_OPERATOR`이며 General이 public request와 ACTIVE member에서 결정한다. conversation self-introduction의 `박은행`은 동일 BANK_STAFF 메시지 content에만 존재하며 공식 account 이름을 바꾸지 않는다. Case participant는 customer·사칭 상대 등 사건 맥락의 별도 인물이다. 현재 구조에는 self-introduction을 requester와 별도로 기억·조회하는 typed field나 resolver가 없다. 즉 **conversation self-introduction을 authenticated identity와 별도로 유지하는 기능은 없다**; raw message provenance만 존재한다.
- Browser 재현 C (08:27:40 UTC): `내가 누구야`는 `_asks_about_requester_identity`에 일치해 provider/evaluator를 거치지 않는 `REQUESTER_LOOKUP`으로 처리됐다. 실제 값은 `requester_display_name=은행 담당자`, `requester_role=CHAT_OPERATOR`이며 role은 출력 template에 사용되지 않는다. `현재 질문자는 은행 담당자 {requester_display_name}입니다.`의 고정 역할 접두사와 display name이 결합되어 `현재 질문자는 은행 담당자 은행 담당자입니다.`가 됐다. 이는 **CONFIRMED BUG — deterministic formatter 중복**이다. Contract상 display name과 role은 별도 문자열이지만 의미가 겹칠 수 있고, 현 Runtime에서는 값 자체가 아니라 formatter가 중복 원인이다.
- 기존 테스트 blind spot: 현재 fixture는 synthetic 개인 이름과 `내가 누구야`의 requester 우선만 검증한다. generic display name `은행 담당자`, `CHAT_OPERATOR` 역할, BANK_STAFF 자기소개 후 이름 기억 질문, customer·사칭 상대·담당자 이름 동시 존재, self-introduction의 quality blocking, provider가 현재 질문 대신 사건 인물을 답하는 경우, role label 중복 출력은 검증하지 않는다.
- 직전 READ-ONLY 진단에서 정한 최소 구현 우선순위: (1) `REQUESTER_LOOKUP` formatter 중복 수정과 generic display-name fixture, (2) A의 criterion-only 안전 관측 경계, (3) 제품 요구 확정 후 별도 self-introduction provenance/resolver 검토 순이었다.
- 직전 READ-ONLY 진단의 regression 제안: authenticated requester `은행 담당자/CHAT_OPERATOR`, BANK_STAFF self-introduction, CUSTOMER·사칭 상대를 구분하고 원문 Case 데이터 없이 criterion code만 검증한다는 기준이었다. 이번 최소 구현은 이 중 C와 A 관측 경계만 수행했고 B의 기억 기능은 보류했다.
- 문제 C 최소 수정(2026-09-19 18:02 KST): 원인은 `REQUESTER_LOOKUP`이 고정 접두사 `은행 담당자` 뒤에 `requester_display_name`을 붙인 formatter임을 재확인했다. 출력은 role을 합성하지 않고 `현재 질문자는 {requester_display_name}입니다.`로 변경했다. 따라서 generic 표시 이름은 `현재 질문자는 은행 담당자입니다.`, 실제 이름 형태는 `현재 질문자는 김담당입니다.`가 되며 display name과 role의 계약은 그대로 유지한다. identity intent 범위와 provider 경로는 변경하지 않았다.
- 문제 C regression: generic `은행 담당자/CHAT_OPERATOR` fixture에서 역할명 중복 금지와 고객·사칭 상대 이름 미사용을 검증했고, 실제 이름 형태 `김담당` fixture도 이름 보존과 Case 인물 미사용을 검증했다.
- 문제 A 기존 관측 경로 확인: runtime blocking failure는 동일한 public provider error로 변환될 뿐 criterion이 server log·API·DB에 남지 않아 실제 Browser A의 criterion을 사후 확인할 수 없었다.
- 문제 A 안전 진단 경계: quality 차단 직전에 `runtime_blocking_failures`의 criterion identifier만 server-side WARNING으로 기록한다. provider 응답, prompt, Case ID·Context, 이름, 대화, Evidence는 기록하지 않으며 public API Contract·DB·Frontend는 변경하지 않았다. synthetic 차단 테스트에서 `criteria=role_adherence` 기록과 원문·prompt·Case ID 부재를 함께 확인했다.
- 문제 A synthetic 재현: 개인정보 없는 requester `김담당`, 자기소개형 질문과 합성 Case만 사용한 현재 8101 Live provider 호출은 HTTP 200, `gpt-4o-mini`, non-empty response로 통과했다. 동일 차단이 재현되지 않았으므로 실제 Browser A criterion은 계속 **VERIFICATION NEEDED**이며 evaluator는 수정하지 않았다. 실제 VP-1 전체 맥락 재전송과 승인 우회는 수행하지 않았다.
- 문제 B 범위 보존: conversation self-introduction memory, typed field/resolver, authenticated requester 변경, Case Fact 승격은 구현하지 않았다. 기존 actor·channel·audience provenance 전달을 그대로 유지했다.
- 자동 검증: 변경 경계 targeted 42개와 source-aware grounding·directness·quality·requester·고객 progress·General 전달/retrieval을 포함한 targeted regression 118개가 프로젝트 `.venv`에서 모두 `OK`였다. 의도된 provider 실패 회귀의 exception log와 새 criterion-only warning이 출력됐지만 테스트 실패는 아니다.
- Runtime 검증: 기존 8101 health HTTP 200. synthetic `내가 누구야?` 호출은 HTTP 200, `REQUESTER_LOOKUP`이며 UTF-8 디코딩 기준 정확히 `현재 질문자는 은행 담당자입니다.`를 반환해 중복이 없었다. VP-1에는 테스트 메시지를 추가하지 않았다.
- 최종 기능 안정화 smoke 확인(2026-09-19): Frontend 5176, General 8100, AI 8101 health/root 응답은 모두 HTTP 200이었다. 실제 Case를 사용하지 않은 합성 Bank 요청으로 업무성 질문 4개(확인된 위험 근거, 미확인 정보, 고객 추가 확인사항, 현재 확인 사실 요약)를 AI 8101에 각각 전송했고 모두 HTTP 200, `gpt-4o-mini`, non-empty response였다. 이 호출은 direct AI API 확인이므로 AI_RESPONSE 저장·담당자 ROOM 표시·새로고침 유지 증거는 아니다.
- Browser smoke 판정: Codex 환경에는 targetable in-app Browser와 Chrome이 없어 담당자 ROOM을 직접 조작할 수 없었다. 따라서 네 질문의 Browser 전송, General 저장, AI_RESPONSE 표시, 새로고침 후 유지, 실패 시 임시 답변 미생성은 **NOT VERIFIED**이며 REST/Live AI 결과로 Browser PASS를 대체하지 않는다. 합성 4건에서 503은 없었으므로 criterion-only server log를 확인할 실패도 없었다.
- 사용자 Browser smoke 증거(VP-3): 사용자가 실제 담당자 ROOM의 새 Case에서 다음 네 CSR 업무성 질문을 각각 전송했다. (1) 현재 이 사건에서 확인된 위험 근거, (2) 아직 확인되지 않은 정보, (3) 고객에게 추가로 확인할 내용, (4) 현재까지 확인된 사실의 간단한 정리. 네 건 모두 Bank AI 응답이 성공했고 503 및 AI 실패 배너가 없었다. 각 AI 응답은 담당자 ROOM에 표시됐으며 Browser 새로고침 후에도 질문과 응답이 유지됐다. 이로써 담당자 ROOM → General → AI → AI_RESPONSE 저장 → 화면 재조회·표시의 기능 흐름을 사용자 검증 증거로 확인했다.
- 완료 판정: 기존 REST·Live AI·targeted regression, requester 전달 및 grounding/certainty 안전 경계 증거와 위 VP-3 Browser smoke를 합쳐 작업 2 DONE gate를 충족했다. 실패 시 임시 AI 답변을 만들지 않는 계약은 기존 failure regression과 runtime 기록으로 유지되며, 이번 VP-3 smoke에서는 실패가 발생하지 않았다. **작업 2 완료 — commit checkpoint 도달**.

### 보류 — 기능 안정화 이후 AI 품질 고도화 Backlog

- Bank AI 답변 직접성, 사건 요약 과다 출력, 답변 길이·형식 개선
- requester/화자/이름의 세밀한 referent 해석과 conversation self-introduction 기억 정책
- 한국어 일관성 및 중국어·불필요한 외국어 혼입
- 실제 Browser A의 criterion 세부 원인 확인과 quality evaluator 정밀화. criterion-only 안전 로그는 유지한다.
- 오류 배너를 채팅 내부 안내로 개선하는 AI 실패 UX

위 항목은 삭제하지 않는다. CSR 업무성 질문의 반복 503, 저장 실패, 질문 추천·등록·답변 저장·Context·qf1 단절처럼 Workflow blocker로 확인되는 경우에만 기능 안정화 작업으로 되돌린다.

**Blocker:** 없음. 고도화 Backlog 항목은 VP-3 smoke에서 핵심 업무 진행을 실제로 막는 경우에만 후속 기능 안정화 문제로 재분류한다.

**다음 작업:** commit checkpoint 후 작업 3 시작. 작업 3의 REST/MySQL 질문·답변 저장 baseline과 담당자 ROOM 가시성 검증을 수행한다. Backlog의 세부 품질 문제는 별도 고도화 작업으로 보류한다.

### 3. 질문/답변 저장 흐름 검증 + 담당자 ROOM 가시성

**상태:** TODO

**관련 Plan:** S2 + S3; G1, V5·V6, Plan 4.3·4.4절.

**목표:** 기존 REST/MySQL 데이터 흐름을 먼저 검증하고, 정상 데이터로 담당자 ROOM의 질문·답변 관계를 표시한다.

**선행 조건:** 작업 1의 Runtime·DB 기준과 작업 2의 기능 안정화 완료. Bank AI 세부 품질 고도화는 선행 조건이 아니다. 표시 수정은 Bank AI 복구와 기술적으로 독립적이지만 **REST/MySQL baseline 확인은 반드시 선행**한다.

**확인/작업 항목:**

- [ ] 여러 질문 등록 후 기존 ASKED가 없는 경우 ASKED 1개와 나머지 PENDING, 순번·중복 보호를 REST/MySQL에서 확인한다.
- [ ] 고객 답변 저장, ANSWERED 전이, 다음 질문 dispatch, 질문별 답변·payload·근거 read-back을 확인한다.
- [ ] Fact 후보·Context revision/projection과 추가 처리 실패 시 raw answer 보존, 재시도·충돌 처리를 확인한다.
- [ ] baseline이 예상과 다르면 차이와 추가 확인 사항을 기록한다. 확인 가능한 동안 IN_PROGRESS, 진행 불가능하면 BLOCKED로 두고 가시성 구현을 진행하지 않는다.
- [ ] baseline 정상 확인 후 기존 데이터로 등록 수·질문 원문·PENDING/ASKED/ANSWERED·현재 질문·답변·시각을 표시한다. UI 형태를 이 문서에서 미리 정하지 않는다.
- [ ] 실제 렌더 경로·중복 방지 targeted test, Frontend typecheck/build, 은행·고객 Browser 동시 확인을 수행한다.

**완료 조건:** REST/MySQL baseline 증거와 실제 렌더 검증이 모두 있어야 한다. 담당자는 Queue 상태와 질문별 답변을 구분할 수 있고, 고객의 순차 노출이 유지되어야 한다. baseline 불일치를 Frontend 표시로 숨기지 않는다.

**결과:** 미작성

**Blocker:** 없음

**다음 작업:** 작업 4.

### 4. qf1 수정 + Dynamic Follow-up 흐름 검증

**상태:** TODO

**관련 Plan:** S4 + S5의 follow-up 이후 의미 상태 검증; B1, V3·V4·V7, Plan 4.5절.

**목표:** qf1 초안 보존부터 담당자 등록·고객 답변·parent/child 관계와 의미 상태 재평가까지 연결한다.

**선행 조건:** 작업 3의 저장·조회 baseline. 함수 수준 재현은 Live AI 없이 가능하지만 최종 완료에는 작업 2의 기능 안정화와 실제 질문 추천 성공이 필요하다.

**확인/작업 항목:**

- [ ] 확인된 reconciliation 버그를 최소 수정하고 생성 직후·재조회·모달 재열기에서 qf1 초안과 선택 상태를 보존한다.
- [ ] 담당자 편집·선택 과정에서 target/parent를 유지하고, 추천만으로 고객에게 전송하지 않는지 확인한다.
- [ ] stale parent·잘못된 parent·동일 scope active 질문·중복 follow-up의 서버 거부를 targeted test와 REST로 확인한다.
- [ ] Live AI 추천 → 담당자 등록 → 고객 Queue 노출 → 답변 흐름을 Browser에서 검증한다.
- [ ] MySQL read-back으로 parent 답변 보존, child 연결, PROPOSED Fact와 근거를 확인한다.
- [ ] child 답변 후 실제 입력에 기반한 Semantic State/Eligibility를 확인한다. 명확·불확실·상충 답변과 “확인 가능” 답변을 구분하며 자동 current/CONFIRMED/VERIFIED 승격을 금지한다.

**완료 조건:** reconciliation targeted test뿐 아니라 REST·MySQL·Live AI·Browser의 전체 follow-up 흐름과 이후 의미 상태 재평가 증거가 있어야 한다. **화면에서 qf1이 사라지지 않는 것만으로 DONE 처리하지 않는다.**

**결과:** 미작성

**Blocker:** 없음

**다음 작업:** 작업 5.

### 5. Context / 출처 검증 + 전체 Browser E2E

**상태:** TODO

**관련 Plan:** S5의 의미·출처 전달 검증 + S6; G2, V6·V7·V8, Plan 4.6·8·9절.

**목표:** 답변 후 갱신된 Fact·Semantic State·Case Context와 출처가 다음 Bank AI에 반영되는지 전체 Workflow로 확인한다.

**선행 조건:** 작업 2~4의 정상 흐름과 검증 증거, 특히 follow-up child 답변까지 확보되어야 한다. 작업 4의 의미 상태 결과를 재사용하고 전체 Context 전달과의 연결을 확인한다.

**확인/작업 항목:**

- [ ] 답변 전후 Fact·Semantic State·Context와 source/projection revision을 REST·MySQL에서 비교한다. stale/cache 및 추가 처리 지연을 구분한다.
- [ ] source/status/evidence, 고객 진술·담당자 확인·BANK_RECORD·연결된 Verification, superseded/current·근거 revision·truncated 의미를 targeted test와 실제 전달 자료로 검증한다.
- [ ] 다음 Bank AI의 요청 입력과 Live 응답을 비교해 갱신된 Context 재조회와 안전한 출처 표현을 확인한다. 필요한 보완은 Plan S5의 검증된 최소 범위에 한정한다.
- [ ] Plan 9절의 Browser E2E를 동일 Case로 수행하고 REST·DB·AI 증거를 연결한다.
- [ ] 새로고침·재접속·중복 재시도·AI 실패·추가 처리 지연에서도 답변 보존과 고객 공개 경계를 확인한다.

**완료 조건:** targeted test, REST snapshot/AI 입력 비교, MySQL read-back/revision, Live AI 출처 표현, 전체 Browser E2E가 각각 확인되어야 한다. 고객 답변을 검증 사실로 승격하거나 전달되지 않은 Evidence를 확인했다고 표현하면 완료가 아니다.

최종 확인 흐름:

```text
Case Context → Bank AI → 질문 추천 → 담당자 검토/수정
→ 고객 질문 등록 → 고객 질문 노출 → 고객 답변 → Context 갱신
→ qf1 / 다음 질문 → 갱신된 Context 기반 다음 Bank AI
```

**결과:** 미작성

**Blocker:** 없음

**다음 작업:** 모든 완료 조건과 증거를 정리해 Integration 완료 보고. 새 범위를 자동으로 추가하지 않는다.

## 이번 문서 작성의 범위

Checklist 작성 이후 작업 1을 완료했다. 작업 2에서는 `unsupported_certainty` 오탐 수정, requester 구조 전달·현재 질문 우선 처리, `REQUESTER_LOOKUP` 중복 수정과 criterion-only 안전 로그를 구현하고 자동 회귀 및 synthetic AI REST·Live provider를 통과했다. 사용자 VP-3 Browser smoke에서 업무성 질문 4건의 성공·AI_RESPONSE 표시·새로고침 후 유지를 확인해 작업 2는 DONE이다. **작업 2 완료 — commit checkpoint 도달.** 세부 AI 품질은 고도화 Backlog로 보류하며, 작업 3~5는 TODO다.
