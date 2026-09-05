# PRD — CSR | Case Share Room Frontend V3

> 보이스피싱 양방향 상담·대응 플랫폼

## 0. Document Purpose

이 문서는 CSR | Case Share Room 서비스의 Frontend V3를 구축하기 위한
제품 요구사항과 UX 원칙을 정의한다.

V3는 기존 V2를 단순 수정하거나 디자인만 변경하는 프로젝트가 아니다.

기존 V2의:

- 기능
- API
- Type
- State
- Backend 연동
- AI Engine 연동
- 실시간 통신
- Case 구조

를 분석하고 재사용할 것은 재사용하되,

사용자 경험은 새롭게 재설계한다.


---

# 1. Product Vision

## 서비스 정의

범죄자는 피해자의 판단을 흔들고,
탐지 이후에는 은행 직원이 그 사건을 다시 파악·확인·설득해야 한다.

CSR | Case Share Room은

통화 맥락을 하나의 사건으로 연결해,
은행의 대응 업무와 고객 상담을 양방향으로 지원하는
보이스피싱 대응 플랫폼이다.


## 핵심 가치

기존 시스템이 주로

> "위험한가?"

를 판단했다면,

우리 서비스는 탐지 이후

- 범죄자가 무엇을 주장했는가?
- 무엇을 요구했는가?
- 어떤 사실을 확인해야 하는가?
- 실제 송금이 발생했는가?
- 은행 직원이 지금 무엇을 확인해야 하는가?
- 고객에게 무엇을 물어봐야 하는가?
- 고객에게 어떻게 설명해야 하는가?
- 어떤 조치를 취해야 하는가?

까지 하나의 Case 안에서 연결한다.


---

# 2. Product Positioning

우리 서비스는 기존 시스템을 대체하지 않는다.

기존 시스템:

### 통신사 / 스마트폰 AI

핵심 질문:

> 이 통화가 위험한가?

역할:

- 실시간 통화 분석
- 위험 경고

우리 서비스와의 연결:

Call Risk Trigger


### ASAP

핵심 질문:

> 기관 간 공유할 위험정보가 있는가?

역할:

- 위험정보 공유
- 표준 위험정보 활용

우리 서비스와의 연결:

Risk Signal


### 은행 FDS

핵심 질문:

> 이 거래가 이상한가?

역할:

- 이상 거래 탐지
- 금융 조치

우리 서비스와의 연결:

Financial Protect


### 112 / 피해구제

핵심 질문:

> 피해 후 무엇을 조치할 것인가?

역할:

- 신고
- 지급정지
- 피해구제

우리 서비스와의 연결:

Recovery Channel


### CSR | Case Share Room

핵심 질문:

> 범죄자가 무엇을 주장하고 요구했고,
> 무엇을 누구에게 확인해야 하는가?

역할:

- 통화 맥락 구조화
- 사건 중심 정보 통합
- 확인 업무 지원
- 고객 상담 지원
- 은행 대응 지원
- 조치 선택 지원

우리 서비스의 핵심:

Context & Verification Layer


---

# 3. Core Architecture

서비스의 AI 구조는 다음과 같다.

Customer Agent

Verification Agent

Bank Agent

Case Orchestrator

Shared Case Engine


하지만 이 Agent 구조를
Frontend에서 복잡하게 노출하지 않는다.


## Frontend 관점

사용자는 Agent들을 각각 사용하는 것이 아니다.

사용자는

> 하나의 Shared Case를 AI와 함께 처리한다.

Case Orchestrator가
Case 상태와 Event를 기준으로
필요한 Agent를 내부적으로 선택한다.


---

# 4. Core UX Concept

Frontend V3의 핵심 UX는

# Shared Case Workspace

이다.


V3는

"AI Agent 관리 시스템"

처럼 보이면 안 된다.


V3는

> 하나의 사건을 AI와 사람이 같이 해결하는 업무 공간

처럼 보여야 한다.


---

# 5. Primary User

V3 Desktop UI의 가장 중요한 사용자는

## 은행 담당자

이다.

은행 담당자는 사건이 발생했을 때
긴 통화 내용과 여러 시스템을 처음부터 다시 확인할 시간이 없다.

따라서 V3는 처음 사건을 열었을 때
몇 초 안에 다음 내용을 이해할 수 있어야 한다.

1. 지금 무슨 사건인가?
2. 위험도는 어느 정도인가?
3. 범죄자가 무엇을 주장했는가?
4. 무엇을 요구했는가?
5. 무엇이 이미 확인됐는가?
6. 무엇을 더 확인해야 하는가?
7. 고객에게 무엇을 물어봐야 하는가?
8. 지금 어떤 조치를 해야 하는가?


---

# 6. UX Success Criteria

## 5초

처음 사건을 본 사용자가

> 무슨 사건인지

이해할 수 있어야 한다.


## 10초

사용자가

> 무엇이 위험한가?

> 무엇이 확인됐는가?

> 다음에 무엇을 해야 하는가?

를 파악할 수 있어야 한다.


## 30초

사용자가 별도의 메뉴 탐색 없이

- 고객에게 질문
- AI에게 질문
- 기관 확인 요청
- 확인 결과 조회
- 필요한 조치 확인

까지 할 수 있어야 한다.


---

# 7. Frontend V3 Information Architecture

V3 초기 MVP는 화면 수를 최소화한다.

핵심 화면은 두 개다.

## 1. Case List / Home

현재 대응 중인 사건 목록


## 2. Case Room

하나의 사건을 처리하는 핵심 Workspace


별도 Agent 페이지를 만들지 않는다.

가능한 대부분의 기능을 Case Room 안에서 처리한다.


---

# 8. Primary Layout

Desktop 기준:

```text
┌──────────────────────────────────────────────────────────────┐
│ Header                                                       │
├──────────────┬────────────────────────────┬──────────────────┤
│              │                            │                  │
│ Case List    │ Shared Case Conversation   │ Case Context     │
│              │                            │                  │
│ 사건 목록     │ 고객 메시지                 │ 위험도            │
│ 위험도        │ 은행 메시지                 │ 사건 요약          │
│ 상태          │ AI Brief                   │ 범죄자 주장        │
│ 최근 업데이트 │ Verification               │ 범죄자 요구        │
│              │ AI Recommendation          │ 확인 결과          │
│              │                            │ 확인 필요          │
│              │                            │ 권장 조치          │
│              │                            │                  │
└──────────────┴────────────────────────────┴──────────────────┘
9. Left Panel — Case List

Case List는 복잡한 Navigation이 아니다.

현재 대응해야 할 사건을 빠르게 선택하기 위한 영역이다.

각 Case에는 최소한 다음만 표시한다.

Case ID
위험 단계
사건 제목
현재 상태
최근 업데이트 시간

예:

VP-1042

검찰 사칭 · 안전계좌 요구

고위험

검증 진행 중

2분 전

우선순위를 빠르게 판단할 수 있어야 한다.

10. Center — Shared Case Conversation

V3의 가장 중요한 영역이다.

일반적인 ChatGPT Clone을 만들지 않는다.

이 Conversation에는 다음 정보가 함께 존재한다.

고객 메시지
은행 담당자 메시지
AI Brief
AI 분석
Verification 요청
Verification 결과
Case Event
추천 조치

예:

고객
검찰에서 제 계좌가 범죄에 사용됐다고 했어요.


AI Brief
통화에서 검찰 사칭과 안전계좌 이체 요구가 확인되었습니다.


은행 담당자
상대방이 정확히 어떤 기관이라고 말했나요?


고객
서울중앙지검이라고 했어요.


Verification
공식 기관 절차와 일치하지 않는 요구가 확인되었습니다.


AI Recommendation
현재 확인 정보 기준으로
고객에게 송금을 중단하도록 안내하는 것이 권장됩니다.

이 모든 기록이 하나의 Case Timeline을 형성한다.

11. AI Brief

은행 담당자가 사건을 열었을 때
전체 통화 내용을 다시 읽지 않아도 되도록 한다.

Case 상단에 2~4문장 정도의 짧은 AI Brief를 제공한다.

AI Brief는 이벤트를 시간순으로 덧붙이는 로그가 아니다.
초기 진단, 고객의 최신 답변, 확정 Fact, 기관 확인 결과, 진행 중인 대응 업무와
남은 확인 과제를 함께 검토한 뒤 **현재 시점의 사건 전체를 하나의 짧은 상황 보고로 다시 작성**한다.
Case의 의미 있는 상태가 바뀌면 기존 Brief에 `최신 반영` 문구를 이어 붙이지 않고
Brief 전체를 교체한다. `예/아니요` 같은 단독 답변은 반드시 질문의 의미와 결합해
`고객은 이미 송금했다고 답변함`, `개인정보는 제공하지 않았다고 답변함`처럼 표현한다.
확정 Fact가 고객 답변이나 AI 추출 후보와 충돌하면 확정 Fact를 우선한다.

예:

고객은 검찰을 사칭한 상대방으로부터
자신의 계좌가 범죄에 연루됐다는 설명을 들었으며,
1,200만원을 안전계좌로 이체하도록 요구받았습니다.

현재 확인된 정보 기준으로 공식 검찰 절차와 일치하지 않는 요청이 포함되어 있습니다.

AI Brief는 장황하지 않아야 한다.
질문 원문과 답변을 화살표로 나열하거나 변경 이력을 중복 표시해서는 안 된다.

12. Right Panel — Case Context

Case Context는
현재 사건의 Shared Case 상태를 구조화해서 보여준다.

최소 구성:

위험도
고위험
87
사건 유형
검찰 사칭 의심
범죄자 주장
"본인 명의 계좌가 범죄에 연루됐다"
범죄자 요구
안전계좌로 1,200만원 이체
확인된 사실
✓ 공식 수사기관 절차와 불일치

✓ 안전계좌 이체 요구 확인
AI 추가 확인 체크리스트
• 실제 송금 여부

• 상대방 전화번호

• 요구받은 계좌
담당자 판단·조치 기록
1. 송금 중단 안내 결정

2. 거래내역 확인

3. 기관 진위 확인

4. 필요한 경우 지급정지

Chat / Event / Verification 결과에 따라
Case Context는 자동 업데이트되어야 한다.

`탐지된 핵심 신호`, `범죄자 주장`, `범죄자 요구`도 최초 Diagnosis를 고정 표시하지 않는다.
AI support가 초기 구조화 신호에 최신 질문·답변, 확정 Fact와 기관 확인 결과를 병합해
최신 `case_context`로 다시 투영하며, 화면은 이 결과를 우선 표시한다.
AI support 입력의 의미 변경 지문이 같으면 기존 투영을 유지하고 AI를 다시 호출하지 않는다.

Case Context는 최초 통화 분석 결과를 고정 표시하는 영역이 아니다.
고객 질문의 생성·전달·회신, CaseFact의 검토·확정, 기관 확인 결과,
대응 업무 상태가 변경되면 최신 Shared Case 상태를 AI support 입력으로 다시 구성한다.

확인 필요 항목의 상태 전이는 다음을 따른다.

```text
AI 확인 제안
→ 고객 전달 대기
→ 고객 답변 대기
→ 고객 답변 검토(PROPOSED)
→ 확인된 사실(CONFIRMED)
```

동일 필드의 고객 답변이 도착했거나 사실이 확정된 뒤에는
이전 AI 확인 제안이 중복해서 남아서는 안 된다.
주기 갱신 자체가 AI 호출을 발생시키지는 않으며,
Case의 의미 있는 데이터 변경 지문이 달라졌을 때만 AI 사건 맥락을 재생성한다.

`AI 추가 확인 체크리스트`는 AI가 현재 DB, 질문·답변, 확정 Fact와 기관 확인 기록을
검토한 뒤 아직 확인되지 않은 미래 확인 과제만 추천하여 서버에 누적한다.
은행 직원이 완료 체크를 하기 전까지 유지하고, 체크하면 기본 목록에서 숨긴다.

`담당자 판단·조치 기록`은 AI의 권장 문구가 아니라 은행 직원이 사건을 검토해 내린
판단과 실행할 조치를 직접 입력하는 체크리스트다. 완료 체크 전까지 누적한다.

두 체크리스트의 완료 항목은 `COMPLETED` 상태로 서버에 보존한다.
완료·숨김 목록은 언제든 열람할 수 있고, 체크를 해제하면 `REQUESTED`로 복원한다.
AI 항목은 확인 필드 단위로 중복 저장하지 않으며 완료 후에도 같은 항목을 다시 만들지 않는다.

13. Chat Input

입력창은 단순하게 유지한다.

[ 메시지를 입력하세요... ] [첨부] [전송]

AI 호출이 활성화된 채팅도 메시지 저장과 AI 응답을 하나의 대기 상태로 묶지 않는다.
은행 직원의 메시지를 먼저 Timeline에 표시하고 입력 잠금을 해제한 뒤,
AI가 새 메시지를 포함한 최신 Shared Case 전체를 다시 읽어 은행 내부 답변을 생성한다.
연속 요청은 저장 순서대로 처리하여 AI 답변의 시간 순서를 보존한다.

은행 내부 입력창에서 `@AI 요청사항`을 입력하면 별도 버튼 활성화 없이 CaseCopilot을 호출한다.
`@AI`가 포함된 요청 원문은 업무 이력으로 보존하되, AI prompt에는 멘션을 제거한 요청사항과
최신 Shared Case를 전달한다. 고객 공개 채널에서 `@AI`가 감지되면 은행 내부 채널로 전환하여
내부 지시가 고객에게 실수로 공개되지 않게 한다.

필요할 경우 Context Action을 제공한다.

예:

고객에게 확인 질문
기관 확인 요청
거래 확인
조치 기록

하지만 버튼을 과도하게 늘리지 않는다.

14. AI Interaction Principle

AI가 사람 대신 최종 금융 결정을 내리는 것처럼 보이면 안 된다.

피해야 할 표현:

송금을 차단합니다.

선호 표현:

현재 확인된 정보 기준으로 송금 중단을 권장합니다.

또는

추가 확인이 필요합니다.

AI의 역할은:

분석
구조화
설명
근거 제공
확인 제안
조치 선택 지원

이다.

15. Customer Agent

Customer Agent는 다음 역할을 담당한다.

고객 상황 브리핑
추가 확인 질문 생성
피해 발생 여부 확인
고객 응답 구조화
고객에게 이해하기 쉬운 설명 제공
고객 설득 지원

하지만 Frontend에서는
Customer Agent라는 별도 화면을 만들 필요가 없다.

결과는 Shared Case Conversation에 나타난다.

16. Bank Agent

Bank Agent는 다음을 지원한다.

통화 맥락 분석
FDS / 거래정보 해석
사건 Brief
확인할 사항 추천
조치 후보 추천
고객 상담 근거 제공

Frontend에서는 Case Context와 Conversation 안에서 표현한다.

17. Verification Agent

Verification Agent는 다음을 확인한다.

사칭 기관
범죄자가 주장한 기관 절차
검사 / 수사관 관련 주장
계좌
공식 금융기관 절차
기타 사건 Claim

Verification 결과는

확인 중
확인 완료
불일치
확인 불가

처럼 상태가 명확해야 한다.

18. Case Orchestrator

사용자가 직접 AI Agent를 선택하게 하지 않는다.

Case Orchestrator가

Case Event
Shared Case 상태
사용자 행동
검증 상태

를 기준으로 필요한 Agent를 호출한다.

Frontend에는 내부 Agent 구조보다

기관 정보를 확인하고 있습니다.

AI 분석이 업데이트되었습니다.

추가 고객 확인이 필요합니다.

처럼 사용자가 이해할 수 있는 상태로 표현한다.

19. Shared Case Engine

모든 정보의 중심 Source of Truth는

Shared Case다.

가능한 정보:

Claim
Demand
Verification Evidence
Customer Response
Transaction Context
Risk
Action
Event
Timeline

같은 정보를 여러 Frontend State에 별도로 중복 저장하지 않는다.

20. Main Service Flow

서비스 Flow:

DETECT
↓
CASE
↓
VERIFY
↓
PROTECT
↓
RECOVERY
DETECT

입력 가능 Event:

통화 AI 위험 Event
FDS 이상거래 Alert
고객 긴급 요청
CASE

Case Orchestrator가 Shared Case 생성

Case Orchestrator는 화면 요청과 독립적으로 활성 Case의 중앙 DB 변경 지문을 감시한다.
새 Case 생성, 고객·은행 메시지, 질문 답변, Fact, Verification, Action 변경이 저장되면
최신 Case를 다시 평가해 안전 필수 P0 질문만 자동 Queue에 등록한다.

자동 발송 허용 범위는 실제 송금 여부, 개인정보 제공 여부,
인증정보 제공 여부, 원격제어 앱 설치 여부로 제한한다.
P1/P2 질문과 허용 범위 밖의 질문은 반드시 은행 담당자 검토를 거친다.
동일 target field와 의미상 동일한 질문은 다시 생성하지 않고,
고객에게는 답변 대기 카드가 항상 한 장만 활성화된다.

VERIFY
범죄자 주장 구조화
요구사항 구조화
기관 진위 확인
계좌 확인
거래 확인
고객 추가 질문
PROTECT
고객 설득
송금 중단 안내
지급정지 지원
추가 보호 조치
RECOVERY

이미 피해가 발생했다면:

112
피해구제
지급정지
추가 자금 이동 차단
후속 모니터링

Recovery는 기존 기관 서비스를 대체하지 않는다.

기존 대응 시스템과 연결한다.

21. Timeline

별도의 Timeline 중심 화면을 만들 필요는 없다.

Shared Case Conversation 자체가 기본 Timeline이다.

필요하면:

[대화] [Timeline]

정도의 Toggle만 제공한다.

Timeline Event 예:

통화 위험 감지
Case 생성
AI Brief 생성
고객 질문
고객 답변
Verification 요청
Verification 완료
금융 조치
피해 여부 확인
Case 종료
22. Case Status

Case 상태는 사용자가 직관적으로 이해할 수 있어야 한다.

예:

탐지
확인 중
대응 중
피해구제
종료

기술적인 Backend Status 값을
그대로 사용자에게 노출하지 않아도 된다.

23. Risk UI

위험도는 강조하되
화면 전체를 빨갛게 만들지 않는다.

예:

고위험 87

그리고 반드시

"왜 위험한지"

근거도 함께 표시한다.

위험도 숫자 자체보다
위험 근거가 중요하다.

24. Design Direction

전체 디자인 방향:

금융기관 업무도구
신뢰감
정보 위계 명확
빠른 정보 확인
차분함
최소한의 시각적 장식

사용 권장:

Typography
Spacing
Divider
Neutral Background
최소한의 Border

사용 최소화:

Gradient
Glassmorphism
3D
과도한 Animation
Shadow
카드 남발
Agent Character
AI 기술 홍보 요소
25. Color Meaning

Blue

일반 정보
Customer
기본 UI

Orange

확인 필요
Verification

Green

확인 완료
보호 조치 완료

Red

고위험
피해
긴급

색을 의미 전달에만 사용한다.

26. Responsive

Desktop을 우선한다.

은행 담당자 업무용 서비스이기 때문이다.

좁은 화면에서는:

Left Case List
→ Drawer

Right Context
→ Slide-over Panel

Center Conversation
→ Main Content

형태로 대응한다.

27. Loading / Error / Empty

반드시 실제 상태를 구현한다.

Empty
현재 대응 중인 사건이 없습니다.
AI Loading
통화 내용을 분석하고 있습니다.
Verification Loading
기관 정보를 확인하고 있습니다.
Error
정보를 불러오지 못했습니다.

다시 시도해주세요.

Backend 오류 하나 때문에
전체 UI가 무너지지 않도록 한다.

28. V2 Reuse Policy

Frontend V2 전체를 먼저 분석한다.

재사용 후보:

API Client
Authentication
Type
Hook
State
WebSocket
SSE
Case API
Message API
Attachment API
Verification API
Action API
Shared Business Logic

재사용을 강제하지 않는다.

낡거나 복잡하거나 UX에 맞지 않는 Component는
V3에서 새로 구현한다.

29. V2 Preservation

V2는 삭제하지 않는다.

V2를 overwrite 하지 않는다.

V3는 별도 폴더로 구축한다.

예:

frontend-v2/
frontend-v3/

또는 현재 Repository 구조에 가장 자연스러운 방식으로 구성한다.

30. Backend / AI Engine Principle

AI Engine은 이미 존재한다.

Frontend에 새로운 AI 판단 로직을 중복 구현하지 않는다.

Frontend의 역할:

Backend / AI Engine
↓
Response
↓
Shared Case
↓
Frontend State
↓
User Experience

현재 실제 API 계약을 먼저 확인한다.

없는 API를 임의로 만들어서 연결된 것처럼 구현하지 않는다.

31. Mock Policy

실제 API가 존재하면 Mock을 사용하지 않는다.

Mock은 UI 개발상 불가피한 경우에만 제한적으로 사용한다.

Mock이 남아 있다면 반드시 표시한다.

TODO: REAL API CONNECTION

최종 완료 전 Mock 의존성을 다시 검사한다.

32. API Cost Safety

Frontend V3 작업 과정에서도
유료 AI API를 무제한 실행하지 않는다.

OpenAI 등 유료 API가 포함된 테스트는 반드시:

MAX_API_CALLS
MAX_INPUT_TOKENS
MAX_OUTPUT_TOKENS
MAX_RETRIES
MAX_CONCURRENCY
가능하면 MAX_COST

하드 제한을 확인한다.

대량 API 실행은 기본적으로 OFF 상태여야 한다.

Frontend 검증을 위해 실제 유료 API를 반복 호출할 필요가 없다면
기존 결과나 안전한 최소 테스트를 사용한다.

33. Main V3 Scenarios
Scenario A — 보이스피싱 의심
위험 Event
↓
Case 생성
↓
Case Room
↓
AI Brief
↓
범죄자 주장
↓
범죄자 요구
↓
Verification
↓
고객 추가 질문
↓
Verification 결과
↓
권장 조치
↓
은행 담당자 대응
Scenario B — 정상 / 낮은 위험

정상 금융 상담이나 낮은 위험 사건에서
과도한 경고가 나타나지 않아야 한다.

Scenario C — 피해 발생
송금 피해 확인
↓
Recovery Mode
↓
지급정지
↓
112 / 피해구제
↓
추가 피해 방지
↓
Case 기록
34. Frontend Development Order
Phase 1

Repository 전체 분석

Phase 2

V2 Frontend 분석

Phase 3

Backend / AI Engine 계약 확인

Phase 4

V3 Architecture / IA

Phase 5

V3 Shell / Layout

Phase 6

Case List

Phase 7

Case Room

Phase 8

Shared Case Conversation

Phase 9

Case Context

Phase 10

Backend / AI Engine Integration

Phase 11

Verification

Phase 12

Action

Phase 13

Timeline

Phase 14

Loading / Empty / Error

Phase 15

Responsive

Phase 16

E2E Testing

Phase 17

UX Polish

35. Definition of Done

V3는 다음 조건을 모두 충족해야 완료로 판단한다.

 V3 별도 폴더 존재
 V2 보존
 Frontend 정상 실행
 Build 성공
 Type Check 성공
 핵심 Route 정상
 실제 Backend API 연결
 Case List 정상
 Case Room 정상
 AI Brief 정상
 Shared Case Conversation 정상
 Case Context 정상
 Verification 정상
 Action 정상
 Timeline 정상
 Attachment 정상
 Loading 상태 정상
 Empty 상태 정상
 Error 상태 정상
 핵심 사용자 Flow 정상
 Mock 의존성 점검
 Merge Conflict 없음
 Console Error 없음
 주요 TODO 없음
 유료 API Hard Limit 확인
 문서와 구현 상태 일치
36. Non Goals

V3 초기 구현에서 목적이 아니다.

Agent마다 별도 Dashboard
Agent 선택 화면
화려한 AI Demo UI
지나치게 많은 통계 Dashboard
복잡한 관리자 페이지
기존 시스템 전체 대체
새로운 AI Engine 재개발
37. Final Product Principle

Frontend V3의 최종 목표는

"예쁜 화면"

이 아니다.

최종 목표는:

은행 직원이 하나의 Shared Case를 보고
현재 사건을 빠르게 이해하고,
고객과 소통하고,
필요한 사실을 확인하고,
AI의 도움을 받아
다음 대응을 선택할 수 있게 만드는 것.

이다.

그리고 사용자가 V3를 보았을 때

"AI Agent가 여러 개 있구나"

라고 느끼는 것보다

"이 사건에서 지금 무엇이 일어나고 있고,
내가 무엇을 해야 하는지 바로 알겠다."

라고 느껴야 한다.

38. New Call Analysis Entry

Case가 아직 선택되지 않은 Home 화면의 `대응할 사건을 선택하세요.` 영역 하단에는
`새 통화 분석하기` 버튼을 둔다.

버튼을 누르면 같은 Home 영역에서 아래 흐름을 제공한다.

```text
통화 내용 텍스트 입력
↓
문장·줄바꿈 단위 ML 위험 신호 추출
↓
구조화된 핵심 피처만을 이용한 LLM 맥락화
↓
Case 초기 데이터·초기 보고서 생성
↓
ML 최고 위험 점수 + 핵심 신호 + LLM Case 정리 확인
↓
생성된 Case Room 열기
```

Frontend는 분석 결과를 임의로 만들지 않는다. `POST /api/cases/analyze`를 통해 General API에 요청하고,
Case가 생성되면 해당 Case를 다시 읽어 저장된 `diagnosis`, `initial_report`, `initial_brief`를 화면에 표시한다.

분석 화면은 최소한 다음을 보여준다.

- ML 최고 위험 점수 하나와 구조화된 핵심 위험 신호
- 사건 유형과 AI 초기 요약
- 상대방 주장
- 우선 권장 조치
- 아직 확인할 정보
- 생성된 Case를 여는 명확한 버튼

새 통화 분석은 실제 AI/ML 호출이 발생할 수 있으므로 사용자가 분석 버튼을 명시적으로 누를 때만 실행한다.

### 38.1 원문 비저장·피처 우선 데이터 경계

입력 원문은 분석 요청을 처리하는 동안에만 사용한다. Shared Case·초기 보고서·분석 구간 DB에는
원문, 인용문, 원문을 복원할 수 있는 문장 조각을 저장하지 않는다.

- ML/이벤트 추출 결과는 `event_family`, `subtype`, `impersonation_group`, turn 순번, 수치형 feature,
  금액 집계처럼 최소 맥락 피처로 투영한다.
- Case Context LLM은 원문이 아닌 이 구조화 신호 payload만 입력으로 사용해 요약·주장·권장 조치를 만든다.
- 화면은 문장별 위험 점수 목록 대신 최고 위험 점수와 사람이 읽는 핵심 신호를 보여준다.
- 향후 통신/온디바이스 추출기가 일부 핵심 피처만 보내도 같은 API·Case 생성 흐름을 사용할 수 있어야 한다.

### 38.2 피해 중심 사건 상태 표현

은행 담당자 화면의 상태 표기는 ML 위험도나 점수로 판단하지 않는다. 모든 사용자용 표현은 아래 세 상태만 사용한다.

- `피해 발생`: 실제 피해 금액이 있거나, 고객이 송금을 했다고 확인했거나, Case가 피해구제 모드인 경우
- `의심`: 피해가 아직 확인되지 않았고 사실 확인·대응이 진행 중인 경우
- `해결`: Case가 종료된 경우

`risk-pill danger`와 빨간 상태 색은 `피해 발생`에만 사용한다. Case 목록 필터는
`전체 / 피해 발생 / 의심 / 해결` 순서로 제공하며, ML 점수·고위험·주의·낮은 위험은 Frontend에 표시하지 않는다.
