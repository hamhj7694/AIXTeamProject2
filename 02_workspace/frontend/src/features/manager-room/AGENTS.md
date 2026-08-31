# 담당자 ROOM Frontend 작업 지침

## 적용 범위와 목적

이 문서는 `src/features/manager-room/**`에서 수행하는 담당자 ROOM 프론트엔드 작업에만 적용한다. 프로젝트 전체를 재설계하거나 다른 팀원의 작업 방식을 변경하기 위한 문서가 아니다.

이 Feature의 목표는 기존 팀 코드와 다른 팀원의 작업을 최대한 보존하면서 담당자 ROOM Frontend MVP를 구현하는 것이다. 기능 수보다 아래 핵심 흐름이 끊기지 않는 것을 우선한다.

```text
Case Entry
→ 담당자 ROOM
→ 현재 사건 Brief 확인
→ AI 사건 업무 확인 / 요청
→ 사건 진행 흐름 확인
→ FDS / STT Evidence 확인
→ AI 추천 질문을 담당자용 고객 ROOM으로 전달
→ 담당자가 질문 수정 / 전송
→ 고객 대화 확인
→ 종료 결과 기록
→ Case 종료
```

AI가 최종 판단을 수행하는 서비스가 아니라, 담당자가 하나의 보이스피싱 의심 Case를 더 빠르고 근거 있게 이해하고 확인할 수 있도록 지원하는 Frontend를 구현한다.

## 작업 범위

담당자 ROOM의 구현 범위는 다음과 같다.

- AI 사건 워크스페이스
- 사건 진행 흐름
- 원본 Evidence
- 담당자용 고객 ROOM
- 사건 종료 Modal과 종료 흐름
- 동일 Case 기준의 최소 Frontend 상태 연결
- 담당자 ROOM 진입에 필요한 최소 Page와 Route 연결

다음 영역은 다른 팀원의 담당 영역이므로 임의로 구현하거나 재설계하지 않는다.

- `/` AI 통화 텍스트 진단
- `/cases` Case List
- `/cases/:caseId` Case Entry / Role Selector
- `/cases/:caseId/customer` 고객 본인용 Customer Safety Room
- Verification 화면
- 기존 `src/features/consultation/**`
- 기타 기존 팀원 Page와 Feature
- 실제 FDS, ASAP, 금융기관 API, Backend, DB, WebSocket, SSE
- 로그인, 인증·인가, 전체 Role Guard 시스템

Page와 Route 같은 공통 경계 파일은 별도 STEP에서 사용자가 명시적으로 요청한 경우에만 최소 범위로 수정한다.

## 코드 보존 및 Git 원칙

- 기존 팀원 코드와 정상 기능을 최대한 보존한다.
- 요청하지 않은 파일을 삭제하거나 이름을 변경하지 않는다.
- 다른 팀원의 Page나 Feature를 담당자 ROOM에 맞춰 수정하지 않는다.
- `src/features/consultation/**`를 담당자 ROOM 용도로 재작성하지 않는다.
- 프로젝트 전체 구조를 새 아키텍처로 리팩터링하지 않는다.
- 공통 파일 수정은 담당자 ROOM 연결에 꼭 필요한 최소 범위로 제한한다.
- 한 번에 대규모 리팩터링을 하지 않는다.
- 사용자의 요청 없이 commit, push, merge 또는 브랜치 변경을 하지 않는다.
- `git reset --hard`, `git clean -fd`, force push, 기존 파일 대량 삭제 같은 파괴적 작업을 하지 않는다.
- 다른 팀원의 파일과 충돌할 가능성이 있으면 수정 전에 사용자에게 알린다.

## 코드 배치와 Route

담당자 ROOM 전용 코드는 가능한 한 다음 영역에 모은다.

```text
src/features/manager-room/
```

Page가 필요하면 기존 구조를 확인한 뒤 `src/pages/ManagerRoomPage.tsx`와 같은 위치를 검토한다. 예상 진입 Route는 `/cases/:caseId/bank`이지만, 구현 전에 기존 Router와 동일 Route의 존재 여부를 확인해 중복 생성하지 않는다.

`/cases/:caseId/customer`는 고객 본인용 화면이고, 담당자 ROOM 내부 고객 ROOM은 담당자가 고객과 확인·대화하는 별도 화면이다. 담당자용 Component에는 `CustomerRoom`처럼 모호한 이름 대신 `ManagerCustomerRoom`처럼 역할이 드러나는 이름을 사용한다.

## UI 재사용과 기술스택

구현 전 기존 `Button`, `Card`, `Badge`, `Dialog` 등 공통 UI와 Layout 사용 방식을 먼저 확인한다.

1. 기존 공통 UI로 해결 가능한지 확인한다.
2. 공통 UI를 조합해 담당자 ROOM 전용 Component를 작성한다.
3. 해결하기 어려운 경우에만 새 UI Primitive를 검토한다.

담당자 ROOM 디자인을 위해 기존 공통 UI를 대규모 수정하지 않는다. 기존 `AppLayout`이 모바일·소비자 화면 중심이라 Desktop Workspace에 맞지 않으면 이를 뜯어고치지 말고 전용 Layout 또는 Shell을 우선 검토한다. 다른 Feature의 Component가 해당 상태나 데이터 구조에 강하게 결합되어 있으면 억지로 재사용하지 않고 패턴만 참고한다.

실제 `package.json`을 먼저 확인하고 Repository에서 사용하는 React, TypeScript, Vite, React Router, Zustand, Tailwind CSS, lucide-react, clsx 등의 기존 기술을 우선한다. 새로운 상태관리 라이브러리, UI Framework, Router, SSR Framework, 실시간 통신 라이브러리, Chart Library를 임의로 도입하지 않는다. Vite 기반 React SPA를 담당자 ROOM 때문에 SSR 구조로 바꾸지 않는다.

## 화면 구조와 기능 기준

담당자 ROOM은 하나의 Case를 기준으로 다음 구조를 사용한다.

```text
담당자 ROOM
├─ AI 사건 워크스페이스
├─ 사건 진행 흐름
├─ 원본 Evidence
└─ 담당자용 고객 ROOM

+ 사건 종료 Action
```

`사건 종료하기`는 Navigation Tab이 아니라 Case 상태를 변경하는 주요 Action으로 구분한다.

### AI 사건 워크스페이스

- 현재 사건 Brief, AI 업무 대화, 업무 요청 입력과 전송, AI 추천 질문을 제공한다.
- 필요하면 위험 근거, 미확인 정보, 다음 확인사항을 포함한다.
- AI 업무 대화는 현재 Case에 연결된 사건 전용 Assistant로 취급한다.
- AI 추천 질문은 `고객 ROOM에서 확인`을 거쳐 담당자용 고객 ROOM의 동일 메시지 입력창에 Draft로 전달한다.
- 담당자가 Draft를 검토·수정한 뒤 전송한다.
- AI Workspace에서 고객에게 질문을 직접 보내지 않는다.
- 별도 AI 업무 탭, 범용 챗봇, 자동 최종 사기 판단, 자동 Brief 재작성, 별도 상태 Dashboard를 만들지 않는다.

### 사건 진행 흐름

- 조회 중심의 `과거 → 현재 → 다음` 구조를 사용한다.
- 과거는 사건 발생, 통화·STT 분석, FDS Alert, 고객 확인, 담당자 처리처럼 의미 있는 상태 변화만 하나의 Timeline Event로 표현한다.
- 모든 AI Chat 메시지를 Timeline에 저장하지 않는다.
- 현재에는 사건 상태, 확인 현황, 현재 작업·대기 상태를 표시하고, 다음에는 다음 진행을 표시한다.
- 통화 또는 FDS Evidence로 이동하는 Context Deep Link를 둘 수 있다.
- 이 화면에서 AI 질문 입력, 고객 메시지 전송, Evidence·확인 현황 수정, 별도 업무 메모 작성을 제공하지 않는다.

### 원본 Evidence

- `[FDS] [통화 / STT]` 구조의 Read-only 조회 화면으로 구현한다.
- FDS에는 거래 정보, 탐지 결과, 필요한 외부 연계 위험정보를 표시할 수 있다.
- 통화·STT에는 통화 기본정보와 화자 구분이 포함된 STT 원문을 표시한다.
- Mock은 `MVP Mock` 등으로 실제 연동과 명확히 구분한다.
- ASAP을 별도 Evidence Tab이나 독립 시스템처럼 만들지 않는다.
- FDS·STT 수정, Evidence 삭제, 위험상태 직접 변경, AI 최종 판단을 제공하지 않는다.

### 담당자용 고객 ROOM

- 고객 대화 내역, 하나의 메시지 입력창, 전송 기능을 제공한다.
- AI 추천 질문 Draft와 일반 고객 대화는 동일 입력창을 사용한다.
- 질문 수정·전송 전용 UI, AI Draft 전용 입력창, 고객 Online·Offline 상태, 고객 응답 후 자동 AI 재분석을 별도로 만들지 않는다.

### 사건 종료

- 모든 담당자 ROOM 화면에서 `사건 종료하기` Action에 접근할 수 있게 한다.
- 즉시 종료하지 않고 Dialog 또는 Modal에서 필수 종료 결과, 선택 종료 메모, 취소, 사건 종료를 제공한다.
- Mock 종료 결과는 정상 확인, 보이스피싱 위험 의심, 기타 등을 사용할 수 있다.
- 지급정지나 거래중단을 서비스가 직접 수행한 것처럼 표현하지 않는다.
- 향후 Mock 흐름은 `종료 결과 저장 → Case Status = CLOSED → Case List 이동` 수준으로 제한한다.

## Mock Data와 보안

- Backend가 준비되지 않은 Case 기본정보, 위험도, 상태, Brief, AI 대화·추천 질문, FDS, STT, Timeline, 고객 대화, 종료 결과는 Mock Data로 구현할 수 있다.
- Mock과 실제 API 연동을 혼동시키지 않고 UI와 Data를 분리해 향후 교체하기 쉽게 만든다.
- UI Component 내부에 데이터 객체를 과도하게 하드코딩하지 않는다.
- API Key, Secret, Token, DB Password, 실제 고객 개인정보·전화번호·계좌번호를 코드나 Mock에 넣지 않는다.
- 금융기관 내부 FDS Rule을 실제 알고 있는 것처럼 임의 작성하지 않는다.
- 환경변수가 필요하면 `.env`를 사용하고 ignore 여부를 확인하며, 실제 Secret이 없는 `.env.example`은 추적 가능하게 유지한다.

## 자동으로 추가하지 않을 기능

다른 설계 문서에 있더라도 P0·P1·P2 Question Queue, Auto Triage 제어, Verification Matrix, Monitor, Co-pilot, Human Takeover, Resume AI, Recovery Mode 전체, 금융조치 Panel 전체, Full Conversation Drawer, 실제 FDS Deep Link, WebSocket·SSE, Source Chip 시스템 전체, 담당자 SLA·Queue, 3열 Dashboard 전체를 현재 범위에 임의 추가하지 않는다.

추가가 필요해 보이면 구현 전에 필요한 이유, Part 1~5에서 해결하는 문제, MVP 비용과 영향을 사용자에게 설명하고 제안한다.

## 단계별 구현 원칙

한 번에 전체를 구현하거나 다음 STEP 기능을 미리 만들지 않는다.

```text
STEP 1  Manager ROOM Shell + 공통 Header + Navigation + 화면 전환 뼈대
STEP 2  AI 사건 워크스페이스
STEP 3  사건 진행 흐름
STEP 4  원본 Evidence
STEP 5  담당자용 고객 ROOM + AI 질문 Draft 전달
STEP 6  사건 종료 Modal + 전체 상태 연결 + 최종 검증
```

각 STEP에서는 사용자가 요청한 범위까지만 구현한다.

## 변경 전 확인과 검증

실제 코드를 변경하기 전에 현재 `src` 구조, Router 구성, 담당자 ROOM Route 존재 여부, 공통 Button·Card·Badge·Dialog, Layout 사용 방식, Feature Naming Convention, 재사용 가능한 Component, 수정 예정 파일, 팀원 파일과의 충돌 가능성을 확인한다. 확인하지 않은 구조를 추측해 구현하지 않는다.

구현 단계에서는 TypeScript 오류, 개발 서버 실행, `npm run build`, 기존 페이지와 담당자 ROOM Route 진입, 내부 Navigation, Evidence Tab, AI 추천 질문의 고객 ROOM Draft 전달, 사건 종료 Modal을 요청 범위에 맞게 검증한다.

오류는 다음 순서로 최소 수정한다.

```text
오류 메시지 → 발생 파일 → 원인 확인 → 영향 범위 확인 → 최소 수정 → 다시 검증
```

작업 결과는 `수정 대상 → 수정 이유 → 변경 내용 → 기존 코드 영향 → 검증 결과` 순서로 설명하고 실제 변경 파일 목록을 함께 제공한다.

## 핵심 원칙

> 기존 팀 코드는 최대한 보존하고, 담당자 ROOM 전용 코드는 별도 Feature 영역에 모으며, 기존 공통 UI를 우선 재사용하고, MVP 핵심 흐름에 필요한 Page와 Route만 최소한으로 연결한다.
