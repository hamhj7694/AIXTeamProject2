# 사용자 표시 문구·영문 내부 코드 노출 점검

점검일: 2026-09-05. 상위 기준: `03_IMPLEMENTATION_STATUS.md`.

## 1. 범위와 결론

`Social Engineering` 사건 제목 노출을 출발점으로 MVP_v3의 사용자 표시 경로를 점검했다.
Frontend 소스 41개, General API 앱 18개, AI API 앱 32개, 공용 Python 계약 19개를 정적 검색하고 관련 생성·저장·표시·내보내기 경로를 상세 검토했다.
관련 PRD·설계 문서·회귀 테스트도 대조했다. 의존성, 빌드 산출물, 바이너리 모델, 비밀 환경변수 및 통화 원문은 조사 대상에서 제외했다.

**일곱 가지 문제군을 확인했다. 단어 사전 누락뿐 아니라 변환 대상 누락·과도한 변환이 함께 존재한다.**
특히 보고서 JSON 문자열의 키까지 바뀌는 문제를 먼저 막아야 한다.

이번 작업은 조사 및 문서화다. 애플리케이션 코드, DB 데이터, 서버 설정은 수정하지 않았으며 서버 재시작이나 유료 AI 호출도 하지 않았다.
사용자가 직전에 요청한 CSS 변경은 그대로 보존했다.

## 2. 확인 사항과 우선순위

### U-01 / P0 — JSON 보고서를 문장처럼 변환해 키를 훼손

- 위치: `frontend/src/userText.ts:18`, `:20`, `:28`; `components/SharedConversation.tsx:63`.
- `presentResponse()`는 AI 메시지의 `content`가 JSON 문자열이어도 `userText()`를 적용한다.
- 이때 미등록 snake_case를 일괄 치환하는 정규식이 값뿐 아니라 `report_id`, `executive_summary`, `verified_facts` 같은 JSON 키도 `추가 확인 정보`로 바꾼다. 같은 키로 합쳐져 상세 필드가 사라진다.
- 합성 REPORT_CARD를 실제 변환 함수에 넣어 재현했다. 기존 네 키가 변환 후 두 키로 줄고 `report_id`를 찾지 못했다.
- 영향: `parseFinalReport()`가 실패해 원래 상세 대신 호환 카드로 표시될 수 있다. **DB 원본 훼손을 확인한 것은 아니며, 클라이언트 응답 가공 단계의 문제다.**
- 현재 `bundle.final_report`가 있으면 타임라인이 이를 우선 사용하므로 모든 종결 사건에서 발생한다고 단정하지 않는다.
- 수정: 메시지 종류별로 JSON을 먼저 해석하고 표시용 값만 변환한다. JSON 키·ID·enum·스키마 버전은 그대로 보존한다. 사전 확대 전에 이 경계를 회귀 테스트로 고정한다.

### U-02 / P1 — 사건 유형 생성과 표시 사전에 한국어 제약 누락

- 위치: `backend/ai_api/app/domains/diagnosis/extractor.py:344`, `:409`, `:419`; `backend/general_api/app/domains/cases/signal_projection.py:77`; `frontend/src/presentation.ts:77`; `frontend/src/userText.ts:2`.
- 초기 분석 프롬프트는 한국어 요약을 요청하지만 사건 유형 등 모든 표시 필드의 언어를 명확히 제한하지 않는다. `incident_type`은 자유 문자열이며 형식 검증만 받는다.
- Case 저장 projection은 LLM 사건 유형을 유지한다. 화면 제목은 이 값을 사용한다.
- 실제 활성 사건 목록 6건을 읽기 전용으로 확인했다. 현재 제목에서 영어가 남은 사건은 VP-7 한 건이며, 저장 값은 `Impersonation/Social Engineering`, 표시 결과는 `기관·신분 사칭/Social Engineering`이다.
- `Social Engineering`, `social-engineering`은 그대로 통과하고, `SOCIAL_ENGINEERING`은 의미 없는 `추가 확인 정보`로 바뀌는 차이도 재현했다.
- 수정: 신규 생성의 모든 사용자 표시 필드를 쉬운 한국어로 요구하고 응답 처리에서도 보완한다. 기존 기록은 표시 변환으로 대응한다. 예: `Social Engineering` → `심리적 기만`. 기존 DB 일괄 수정이나 AI 재분석은 필요하지 않다.

### U-03 / P1 — 프론트·서버의 변환 사전 및 처리 정책 불일치

- 위치: `frontend/src/userText.ts`; `backend/contracts/user_text.py`.
- Frontend 등록 키 41개, Backend 22개로, 프론트에만 19개가 있다.
- 차이: `actual_loss_amount_krw`, `sensitive_info`, `contact_restriction`, `prosecution`, `urgency`, `isolation`, `fear`, `casefact`, `proposed`, `confirmed`, `unresolved`, `payment_hold_review`, `human_takeover`, `staff_judgment`, `evidence_preservation`, `account_report_guidance`, `not_provided`, `not_transferred`, `unknown`.
- 양쪽 모두 `Social Engineering`은 없다. Frontend는 미등록 snake_case를 대체하지만 Backend는 그대로 둔다. 파일명 보호도 Frontend에만 있다.
- 영향: UI·AI 입력·내보내기의 문구가 달라질 수 있다. Backend `user_text()`는 RAG 검색 정규화와 근거 문장 생성에도 사용된다.
- 수정: 코드별 뜻과 별칭에 대한 단일 명세 및 양쪽 동일 입력/출력 테스트를 만든다. 모든 영어를 삭제하는 정규식으로 대체하지 않는다. RAG 정규화에 미치는 영향도 함께 검증한다.

### U-04 / P1 — 실제 표시 필드·배열 중 변환 대상에서 빠진 항목

- 위치: `frontend/src/userText.ts:20`; `components/CaseActionDialogs.tsx:133`; `customer/CustomerQuestionCard.tsx:35`; `components/SharedConversation.tsx:80`.
- `suggested_claim`, `suggested_target`, `suggested_action_note`, `suggested_notice`, `rationale`, `context_sources`, 질문 `options`, 보고서 `content.items` 등은 공통 표시 변환 목록에 없다.
- 기관 확인 초안은 `suggested_claim/target`을 입력창에 사용하고, 고객 선택지는 `options`를 직접 표시한다. 저장된 최종 보고서의 목록은 `content.items`를 직접 읽는다.
- 실제 함수에 합성 응답을 넣어 `suggested_claim: Impersonation`, `options: [YES, NO]`, `content.items: [personal_info_shared]`가 그대로 남는 것을 확인했다. 이 합성 문구들이 현재 모든 Case에 저장돼 있다는 의미는 아니다.
- 수정: 단순한 이름 기반 재귀 처리보다 응답 종류별 표시 필드를 지정한다. 선택지는 전송 값과 표시 라벨을 구분해야 하며 enum 자체를 번역하면 안 된다.

### U-05 / P1 — PDF·Word 내보내기에 표시 변환 부재

- 위치: `backend/general_api/app/main.py:2088`; `:2111`; `backend/ai_api/app/domains/case_support/final_report_service.py:74`.
- `_report_export_lines()`는 저장된 `text`와 `items`를 그대로 PDF·Word 작성기에 전달한다. 알려지지 않은 section key도 제목으로 그대로 출력한다.
- 이 함수만 별도로 추출해 합성 보고서에 실행한 결과, `personal_info_shared: UNKNOWN`, `Impersonation/Social Engineering`, 알 수 없는 내부 section key가 출력용 줄에 남았다.
- LLM 보고서에는 한국어 지침이 있지만 출력 후 언어·용어 검증은 없다. 프롬프트만으로 모든 결과가 한글이라고 보장할 수 없다.
- 수정: 보고서 화면과 내보내기에 같은 표시 계약을 사용하고, 알 수 없는 section key는 안전한 한국어 제목으로 처리한다. 직원 종결 메모·원본 근거는 별도로 보존한다.
- 실제 PDF/Word 파일 렌더링은 이번 조사에서 하지 않았다. 출력에 사용되는 문자열 경로를 검증한 결과다.

### U-06 / P1 — API·검증·네트워크 오류가 영어로 노출

- 위치: `backend/general_api/app/main.py:411`, `:471`, `:1509`, `:2084` 등; `frontend/src/api/client.ts:7`, `:22`, `:39`.
- General API의 고정 `message` 문자열 중 영어 문구를 쓰는 위치를 20곳 확인했다. 예: `Case not found.`, `Case has changed.`, `Verification task not found.`, `Final report not found.`.
- 프론트는 서버의 `detail.message`를 상태별 한국어 기본 안내보다 먼저 반환한다. Pydantic `msg`와 네트워크 예외도 그대로 노출될 수 있다.
- 외부 요청 없이 fetch를 대체한 실제 클라이언트 함수 검사에서 영어 404, `Input should be 'CONFIRM' or 'REJECT'`, `Failed to fetch` 노출을 재현했다.
- 수정: 오류 code별 사용자 안내와 필드/검증 사유별 한국어 문구를 제공하고, 네트워크 실패는 별도로 처리한다. 원본 기술 오류는 개발 로그에서 확인하며 사용자에게 무조건 그대로 출력하지 않는다.

### U-07 / P2 — 사용자 원문·구조화 값의 보호 경계가 일관되지 않음

- 위치: `frontend/src/userText.ts:18`, `:20`, `:28`; `components/EditableContext.tsx:49`; `components/ContextWorkspace.tsx:87`.
- 고객·은행 직원의 채팅 `content`는 보호하지만 `answer_text`, `staff_text`, 일반 `value`는 일괄 변환 대상이다. 같은 문장이 위치에 따라 다르게 보일 수 있다.
- 미등록 snake_case는 모두 `추가 확인 정보`로 바뀌므로 필요한 의미까지 사라진다. 합성 structured `value.text`에서도 이를 재현했다.
- 편집 폼에서 표시용으로 변환된 문장을 초깃값으로 쓰는 경로도 있어, 이후 사용자가 저장할 때 원문을 바꾸게 될 가능성은 별도 검증해야 한다. 이번에는 실제 저장을 실행하지 않았다.
- 수정: 원본 데이터·직원 작성본과 자동 생성 표시 문구를 분리한다. 알려진 내부 분류만 설명 문구로 바꾸며 ID, URL, 파일명, 인용 원문 및 enum은 가공하지 않는다.

## 3. 유지할 정상 동작과 제외 사항

- `IMPERSONATION/PROSECUTION` 등 구조화 탐지 신호의 Case 저장 projection은 구체적인 한국어 라벨을 제공한다. 알 수 없는 신호에도 한국어 기본 설명이 있다.
- 사건 상태, 기관 확인 상태, 업무 종류, 참여자 역할, 우선순위, 이벤트명에는 별도의 한국어 표시 함수/옵션이 이미 있다. 내부 enum은 이 기능들을 위해 유지해야 한다.
- `CSR | Case Share Room`, `AI`, `PDF`, `Word`, `OTP`, URL, 파일명, 사건 ID는 내부 코드 노출과 구분한다.
- 정적인 `CASE CONTEXT`, `SHARED CASE`, `AI FINAL REPORT`, `AI BRIEF`, `CASE TRASH`, `NEW SHARED CASE`는 별도의 UI 문구 선택 사항이다. 자동 생성된 분류명이 잘못 노출되는 문제와 동일시하지 않는다.
- 보안·인증·성능·금융 업무 정확성의 전 항목을 검증한 감사가 아니라, **영문/내부 코드의 사용자 노출 경로에 한정한 점검**이다.

## 4. 권장 수정 순서

1. U-01: JSON·ID·enum 보호 및 응답 가공 → 보고서 파싱 통합 회귀 테스트.
2. U-02/U-03: 누락 용어·별칭과 AI 생성 지침 보완. 기존 Case 제목은 DB 변경 없이 표시 교정.
3. U-04/U-05: 질문 선택지·업무 초안·보고서 화면 및 내보내기 표시 계약 연결.
4. U-06: 서버 오류·422 검증·네트워크 안내 한글화.
5. U-07: 직원 편집 원문 보존과 재저장 검증. 운영 인증·리팩터링으로 범위를 넓히지 않는다.

## 5. 수행한 검증 및 제한

- 실제 General API 사건 목록 읽기: 활성 6건, 영어 사건 제목 잔여 VP-7 한 건 확인.
- 실제 Frontend 변환 함수 실행: 미등록 용어, 누락 필드/배열, JSON 키 변형, 원문 처리 차이 재현.
- 실제 API 클라이언트 + 합성 fetch 응답: 영어 오류·422·네트워크 오류 재현.
- 실제 Backend 표시 함수 및 내보내기 줄 생성 함수: 변환 불일치·미변환 출력 재현. 서버 초기화 없이 함수만 실행.
- 기존 Frontend 표시 10개 + 질문/보고서 8개 검사 통과. General 표시 라벨 테스트 3개 통과.
- 기존 테스트 통과는 위 누락이 없다는 의미가 아니다. 특히 API 응답 가공 후 REPORT_CARD 파싱을 잇는 검사가 부족하다.
- 이번에 제품 코드는 바꾸지 않아 전체 빌드/전체 회귀를 새로 실행하지 않았다. 실제 브라우저 클릭, 유료 LLM 생성, 파일 렌더링, 실제 데이터 저장은 미수행이다.
