# Frontend ↔ Backend 연결 스키마

> 참조: `01_general_backend_architecture.md` ~ `06_progress_todo.md`  
> 대상 Frontend: `02_workspace/frontend`  
> 목적: 현재 Mock 기반 CSR 화면을 일반 Backend의 Case 중심 API·MySQL·AI API·Realtime Delta 구조에 안전하게 연결하기 위한 화면/API/상태 스키마를 정의한다.

---

## 1. 적용 기준과 현재 상태

### 실행 기준 Frontend

```text
02_workspace/frontend
├─ /                              AI 통화 텍스트 진단
├─ /cases                         Case 목록
├─ /cases/:caseId                 Case Role Selector
├─ /cases/:caseId/customer        Customer Safety Room
├─ /cases/:caseId/bank            Bank Workspace v2 (Manager Room, 기본 은행 화면)
├─ /cases/:caseId/bank-v1         기존 Bank 화면 보존용
└─ /cases/:caseId/verify          Case 내부 검증 화면
```

- `/cases/:caseId/bank`는 **v2 Manager Room**을 기본 은행 화면으로 사용한다.
- `bank-v1`은 비교·보존용이며 신규 Backend 연결의 우선 대상이 아니다.
- 현재 `src/data/mock/**`, `managerRoomMock.ts`, `caseApi.ts`, `localStorage`는 모두 임시 데이터 계층이다.
- Backend 연결 시 화면 Component가 직접 `fetch`하지 않고, `src/services/`의 API Client와 Feature별 상태 Hook을 통해 호출한다.

### Route 정합성 결정

가이드의 외부 검증 Route는 `/verify/:token`이다. 현재 화면의 `/cases/:caseId/verify`는 내부 담당자용 Case 검증 화면으로 유지한다.

```text
/cases/:caseId/verify  = 내부 담당자 검증 현황·Task 관리 화면
/verify/:token          = 외부 기관/검증자 최소 정보 응답 화면 (추가 필요)
```

외부 검증 화면에서는 Case 전체, 고객 상세, 내부 메모를 반환하지 않는다.

---

## 2. 연결 원칙

```text
React CSR
  ├─ REST: 최초 화면 Bundle, 사용자 Command
  └─ SSE/WebSocket: 저장 완료 후 Delta Event 수신
          ↓
일반 Backend
  ├─ 권한·입력·version 검증
  ├─ AI API 호출·결과 Schema 검증
  ├─ MySQL Shared Case State 저장
  └─ case_events Append + Realtime Publish
```

- Frontend는 일반 Backend만 호출한다. AI API, MySQL, Vector DB를 직접 호출하지 않는다.
- 최초 진입은 화면에 필요한 **Bundle**을 조회한다.
- 이후에는 `entity_type + entity_id + operation + entity_version`을 가진 **Delta Event**만 반영한다.
- `case_id`는 모든 조회, Command, Event의 공통 연결키다.
- Client는 오래된 `base_version`으로 Patch하지 않으며, `409 VERSION_CONFLICT` 수신 시 해당 Entity 또는 Bundle을 재조회한다.
- 사용자 Command 성공은 저장 성공을 의미한다. UI 낙관 갱신은 `client_request_id`로 서버 Event와 중복 제거할 수 있을 때만 적용한다.

---

## 3. Frontend 상태 경계

### 3.1 권장 폴더 구조

```text
src/
├─ services/
│   ├─ httpClient.ts              # Authorization, timeout, API Error 표준화
│   ├─ caseApi.ts                 # cases / bundle / header patch
│   ├─ conversationApi.ts         # messages / questions / takeover
│   ├─ reportApi.ts               # LIVE / FINAL Report
│   ├─ verificationApi.ts         # 내부·외부 검증
│   ├─ actionApi.ts               # bank action / recovery
│   ├─ voiceApi.ts                # voice session / transcript
│   └─ caseStream.ts              # SSE 또는 WebSocket 구독
├─ features/
│   ├─ case-state/
│   │   ├─ types.ts               # 아래 DTO와 View Model
│   │   ├─ useCaseBundle.ts
│   │   └─ applyCaseDelta.ts
│   ├─ consultation/              # Customer Safety Room 연결
│   └─ manager-room/              # Bank Workspace v2 연결
└─ data/mock/                     # API 전환 완료 후 demo fixture 전용으로 축소
```

### 3.2 화면 상태와 서버 상태의 분리

| 구분 | 예시 | 저장 위치 |
|---|---|---|
| 서버 기준 상태 | Case Header, LIVE Report, 질문, 검증, Action, Timeline | MySQL → API/Stream |
| 임시 UI 상태 | Tab 선택, Dialog 열림, 입력 중인 Draft, 목록 필터 | Component/Feature Store |
| 통신 상태 | loading, submitting, error, lastEventId | Query/Feature Store |
| 브라우저 지속 상태 | 접근성 설정 등 비업무 설정만 | localStorage 선택 |

현재 `human-takeover`, `customer-last-response`, `voice-call`을 `localStorage`로 화면 간 공유하고 있다. 실제 연결 후에는 각각 `actions/messages/voice_sessions`의 서버 상태로 전환한다. `localStorage`는 화면 UI 복원 외의 업무 상태 저장소로 사용하지 않는다.

---

## 4. 공통 DTO / Bundle Schema

### 4.1 공통 값 타입

```ts
type Id = string;
type IsoDateTime = string;
type EntityVersion = number;

type CaseMode = 'PREVENT' | 'RECOVERY' | 'CLOSED';
type CaseStatus = 'NEW' | 'TRIAGE' | 'VERIFYING' | 'IN_PROGRESS' | 'CLOSED';
type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH';
type QuestionPriority = 'P0' | 'P1' | 'P2';
type ItemStatus = 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'ON_HOLD' | 'FAILED';
```

실제 Enum 명칭·DB 타입은 Migration에서 확정한다. 화면에 노출되는 한국어 라벨은 Enum 값과 분리한다.

### 4.2 Case Header

```json
{
  "case_id": "VP-014",
  "version": 12,
  "risk": "HIGH",
  "type": "검찰 사칭",
  "mode": "PREVENT",
  "status": "VERIFYING",
  "assigned_to": { "user_id": "usr_12", "display_name": "김○○" },
  "latest_summary": "검찰 사칭 및 긴급 송금 요구 정황이 확인됨",
  "created_at": "2026-09-01T10:00:00+09:00",
  "updated_at": "2026-09-01T10:05:00+09:00"
}
```

### 4.3 최초 조회 Bundle

각 화면이 여러 API를 동시에 조합하지 않도록, Case 화면은 다음 Bundle을 기본 조회로 사용한다.

```json
{
  "case": {},
  "live_report": {
    "report_id": "live_014",
    "report_version": 7,
    "sections": [
      { "section_key": "summary", "content": {}, "version": 3 },
      { "section_key": "risk_context", "content": {}, "version": 2 },
      { "section_key": "transfer_status", "content": {}, "version": 4 },
      { "section_key": "verification_status", "content": {}, "version": 5 },
      { "section_key": "current_actions", "content": {}, "version": 2 },
      { "section_key": "unresolved_items", "content": {}, "version": 2 },
      { "section_key": "next_checks", "content": {}, "version": 1 }
    ]
  },
  "questions": [],
  "progress_items": [],
  "verification_tasks": [],
  "recent_messages": [],
  "recent_actions": [],
  "recent_events": [],
  "voice_session": null,
  "cursor": "evt_20260901_001"
}
```

권장 API:

```text
GET /api/cases/:caseId/bundle?view=customer
GET /api/cases/:caseId/bundle?view=bank
```

이는 기존 문서의 `GET /api/cases/:caseId` Shared State 원칙을 화면 연결을 위해 구체화한 Projection API다. 원본 상세 Resource API는 계속 별도로 유지한다.

---

## 5. 화면별 API 연결 매핑

| Frontend 화면 / 실제 파일 | 최초 데이터 | 사용자 Command | Delta 반영 대상 |
|---|---|---|---|
| `/` `pages/CasePages.tsx` | 샘플은 로컬 fixture | `POST /api/cases/analyze` | 생성 결과로 `/cases/:caseId` 이동 |
| `/cases` `pages/CasesTablePage.tsx` | `GET /api/cases` | 없음 | `CASE_CREATED`, `CASE_UPDATED`로 목록 Row Upsert |
| `/cases/:caseId` `pages/CaseEntryPageV2.tsx` | `GET /api/cases/:caseId/bundle?view=entry` | 필요 시 `PATCH /api/cases/:caseId` | `CASE_FIELD_UPDATED`, `REPORT_SECTION_UPDATED` |
| `/customer` `pages/CustomerPage.tsx`, `features/consultation/**` | `bundle?view=customer` | message, P0 answer, recovery, voice | 메시지/질문/진행도/보고서/음성 Delta |
| `/bank` `features/manager-room/**` | `bundle?view=bank` + segments/features 필요 시 Lazy Load | P1/P2 승인·전송, takeover, action, finalize | Header, Report, Progress, Event, Verification, Message Delta |
| `/cases/:caseId/verify` `pages/CaseVerificationPage.tsx` | `GET /api/cases/:caseId/verifications` | Task 생성·상태 확인 | `VERIFICATION_UPDATED` |
| `/verify/:token` (신규) | `GET /api/verify/:token` | `POST /api/verify/:token/respond` | 제출 성공 상태만 표시 |

### 5.1 진단 → Case 생성

```text
DiagnosisPage
  POST /api/cases/analyze
  { text, sample_type?, client_request_id }
       ↓
201 { case_id, risk, mode, status, initial_bundle }
       ↓
navigate(/cases/:caseId)
```

UI의 Loading/Error는 HTTP 요청 상태를 사용한다. “정상 상담은 Case를 만들지 않음” 같은 정책은 Frontend 문자열 판정이 아니라 Backend의 `case_created` 또는 `disposition` 결과로 결정한다.

### 5.2 Customer Safety Room

| 현재 화면 동작 | Backend Command | 저장 Entity |
|---|---|---|
| 고객 자유 메시지 전송 | `POST /api/cases/:caseId/messages` | `messages`, `case_events` |
| P0 선택지 응답 | `PATCH /api/cases/:caseId/questions/:questionId` | `questions`, 필요 시 `context_features` |
| 다음 P0 질문 조회 | `POST /api/cases/:caseId/questions/next` | `questions`, `question_options` |
| Recovery 시작 | `POST /api/cases/:caseId/recovery/start` | `cases.mode`, `actions`, `progress_items` |
| 음성상담 요청 | `POST /api/cases/:caseId/voice-sessions` | `voice_sessions` |

P0 응답 후 Backend는 Case Structurer와 Report Update를 오케스트레이션하고, 실제 저장된 결과만 Delta Event로 전송한다.

### 5.3 Bank Workspace v2 (Manager Room)

| v2 영역 | Bundle/API Source | Frontend 연결 방식 |
|---|---|---|
| `ManagerRoomHeader`, `ManagerAssigneeOverview` | `case`, 담당자 정보 | Case Header Field Patch |
| `AiWorkspace`, `CaseOverview` | `live_report.sections` | `section_key` 단위 렌더링 |
| `RecommendedQuestion` | `questions` (P1/P2) | 승인/편집 후 Send Command |
| `CustomerConsultation` | `messages` | Append-only Message List |
| `CaseProgress`, `InvestigationChecklist` | `progress_items`, `verification_tasks` | item id별 Patch |
| `ProgressTimeline` | `recent_events`, `GET events?after=` | event_id 기준 Append |
| `EvidenceView` | `GET segments`, `GET features`, `case_evidence` | Read-only Lazy Load |
| 사건 종료 Action | `POST /reports/finalize` + `PATCH case` | FINAL Report/Case Header Event |

Manager Room의 AI 업무 대화는 고객에게 직접 메시지를 보내지 않는다. 추천 질문은 `questions`의 Draft/Proposed 상태로 만들고, 담당자가 승인·편집 후 `send` API로 전송한다.

### 5.4 내부/외부 검증

```text
Bank 또는 내부 Verification 화면
  POST /api/cases/:caseId/verifications
  GET  /api/cases/:caseId/verifications
          ↓
검증 Task + 외부 token 생성
          ↓
외부 검증자 /verify/:token
  GET  /api/verify/:token
  POST /api/verify/:token/respond
          ↓
VERIFICATION_UPDATED → Report verification_status Section Patch
```

---

## 6. Resource DTO 상세

### 6.1 Question / Option / Progress

```json
{
  "question_id": "q_transfer_status",
  "case_id": "VP-014",
  "priority": "P0",
  "status": "SENT",
  "target_field": "transfer_status",
  "text": "이미 송금했나요?",
  "answer": { "value": "NOT_SENT", "answered_at": "..." },
  "version": 4,
  "options": [
    { "option_id": "opt_1", "option_key": "A", "label": "아직 송금하지 않았어요", "value": "NOT_SENT", "version": 1 },
    { "option_id": "opt_2", "option_key": "B", "label": "이미 송금했어요", "value": "SENT", "version": 1 }
  ]
}
```

```json
{
  "progress_item_id": "p0_transfer_status",
  "case_id": "VP-014",
  "progress_group": "P0",
  "progress_key": "transfer_status",
  "label": "송금 여부 확인",
  "status": "COMPLETED",
  "version": 2,
  "completed_at": "..."
}
```

### 6.2 Verification / Action / Event

```json
{
  "verification_task_id": "ver_18",
  "case_id": "VP-014",
  "claim": "검찰청 직원 사칭",
  "target": "검찰청",
  "status": "IN_PROGRESS",
  "token": "external-token",
  "questions": [],
  "response": null,
  "version": 1
}
```

```json
{
  "action_id": "act_20",
  "case_id": "VP-014",
  "action_type": "HUMAN_TAKEOVER",
  "status": "COMPLETED",
  "actor": { "user_id": "usr_12", "display_name": "김○○" },
  "note": "담당자 상담 전환",
  "created_at": "..."
}
```

```json
{
  "event_id": "evt_009",
  "case_id": "VP-014",
  "type": "MESSAGE_ADDED",
  "actor": "CUSTOMER",
  "payload": { "message_id": "msg_12" },
  "created_at": "..."
}
```

### 6.3 Voice Session / Transcript

```json
{
  "session_id": "vs_001",
  "case_id": "VP-014",
  "status": "ACTIVE",
  "participants": [],
  "rtc": { "provider": "TBD", "join_token": "server-issued" },
  "started_at": "..."
}
```

원본 오디오 URL이나 Provider 비밀 토큰을 Case Bundle, Event, Browser localStorage에 넣지 않는다. Transcript는 Final Segment 중심으로 저장·전달한다.

---

## 7. Realtime Delta Event Schema

### 7.1 Event Envelope

```json
{
  "event_id": "evt_...",
  "case_id": "VP-014",
  "entity_type": "REPORT_SECTION",
  "entity_id": "verification_status",
  "operation": "PATCH",
  "changed_fields": ["content", "status"],
  "payload": {},
  "entity_version": 7,
  "case_version": 31,
  "occurred_at": "2026-09-01T10:05:00+09:00",
  "client_request_id": "optional-id"
}
```

### 7.2 화면별 Event 처리

| Event | Client 처리 | 갱신 범위 |
|---|---|---|
| `CASE_FIELD_UPDATED` | `case` merge | Header/Mode/담당자 Badge |
| `MESSAGE_ADDED` | 메시지 append | Customer Chat, Bank CustomerConsultation |
| `QUESTION_UPDATED` | question id upsert | 현재 질문 Card 또는 추천 질문 |
| `QUESTION_OPTIONS_UPDATED` | option 목록 교체 | 해당 A/B/C만 |
| `PROGRESS_ITEM_UPDATED` | item id upsert | 해당 Row + 완료 수 |
| `VERIFICATION_UPDATED` | task id upsert | Verification Card |
| `BANK_ACTION_ADDED` | action append | Bank Action / 담당자 상태 |
| `TIMELINE_EVENT_APPENDED` | event append | Timeline 마지막 행 |
| `TRANSCRIPT_SEGMENT_ADDED` | final segment append | Evidence STT 목록 |
| `REPORT_SECTION_UPDATED` | section_key upsert | 영향받은 Brief Section만 |
| `VOICE_SESSION_*` | voice session merge | 통화 상태 UI |
| `CASE_REPORT_FINALIZED` | final report 표시 가능 상태 | FINAL Report View |

### 7.3 Stream 재연결

```text
1. Bundle 응답의 cursor(last_event_id)를 저장
2. /api/cases/:caseId/stream?after=:cursor 구독
3. Event 적용 후 cursor 갱신
4. 재연결 실패/버전 공백 감지 시 GET /events?after=:cursor
5. 불연속 또는 409 발생 시 Bundle 재조회
```

SSE와 WebSocket 중 최종 기술은 별도 결정 사항이다. Event Envelope와 Client 적용 로직은 두 방식에서 동일하게 유지한다.

---

## 8. API Error / Version Conflict Schema

```json
{
  "error": {
    "code": "VERSION_CONFLICT",
    "message": "Question has been updated by another actor.",
    "entity_type": "QUESTION",
    "entity_id": "q_transfer_status",
    "current_version": 5,
    "request_id": "req_..."
  }
}
```

| HTTP | code 예시 | Frontend 동작 |
|---|---|---|
| 400 | `INVALID_INPUT` | Field Error 노출 |
| 401/403 | `UNAUTHORIZED` / `FORBIDDEN` | 로그인·권한 안내, 민감 데이터 숨김 |
| 404 | `CASE_NOT_FOUND` | Not Found 화면 |
| 409 | `VERSION_CONFLICT` | 해당 Entity 재조회 후 사용자에게 최신 상태 안내 |
| 422 | `AI_RESULT_INVALID` | 재시도하지 않고 표준 오류 표시·서버 로그 추적 |
| 429/503/504 | `RATE_LIMITED` / `UPSTREAM_TIMEOUT` | 재시도 가능 상태와 요청 ID 표시 |

---

## 9. Mock → API 전환 순서

### Phase 1 — Case 공통 기반

1. `httpClient.ts`, API Error 타입, 환경변수 `VITE_API_BASE_URL` 추가
2. `caseApi`의 `list/analyze`를 실제 API로 교체
3. `MOCK_CASES/getCase` 의존 화면을 `Case List`, `Case Bundle` 조회로 교체
4. 화면별 loading/empty/error 상태를 실제 응답 기준으로 확인

### Phase 2 — Customer Room

1. messages, P0 questions/options, progress bundle 연결
2. 고객 답변을 `localStorage` 대신 `POST/PATCH` Command로 저장
3. recovery/voice session Command 연결
4. `MESSAGE_ADDED`, `QUESTION_UPDATED`, `PROGRESS_ITEM_UPDATED` 적용

### Phase 3 — Bank Workspace v2

1. `managerRoomMock`을 bundle/live report/progress/events로 분리 교체
2. EvidenceView에 segments/features/case_evidence Lazy Load 연결
3. 추천 질문 승인·편집·전송, Human Takeover, Bank Action 연결
4. Report Section Delta와 Timeline Append 연결

### Phase 4 — Verification / RAG / FINAL

1. 내부 Verification Task API 연결
2. `/verify/:token` 최소 정보 외부 화면 구현
3. RAG 근거와 `case_evidence`를 Read-only Evidence에 표시
4. FINAL Report 조회·확정 화면 연결

### Phase 5 — Voice / Realtime

1. Voice Session/참여/종료 및 Final Transcript 연결
2. SSE 또는 WebSocket Stream 적용
3. reconnect/cursor/version conflict E2E 검증

---

## 10. 구현 체크리스트

- [ ] `caseApi.ts`를 Mock 반환에서 REST Client로 전환
- [ ] `CaseBundle`, `DeltaEvent`, `ApiError` TypeScript 타입 정의
- [ ] `/api/cases/:caseId/bundle?view=` Projection API 구현
- [ ] `/api/cases/:caseId/stream` 또는 동등 Stream 확정
- [ ] Customer Room의 localStorage 업무 상태 제거
- [ ] Bank Workspace v2의 `managerRoomMock` API 교체
- [ ] `REPORT_SECTION_UPDATED`의 section_key 단위 렌더링
- [ ] Timeline / Message / Transcript append-only 처리
- [ ] `base_version` 포함 PATCH 및 409 처리
- [ ] 내부 `/cases/:caseId/verify`와 외부 `/verify/:token` 분리
- [ ] FINAL Report View 및 Case 종료 연결
- [ ] `쓰레기/`와 `bank-v1`을 신규 Backend 연결 대상에서 제외

---

## 11. 구현 전 확정 필요

- Backend Framework / 인증·권한 방식
- API Base URL 및 개발 Proxy 구성
- SSE vs WebSocket
- MySQL 실제 Enum·PK·Index·FK 정책
- AI API Timeout / Retry / Queue 정책
- WebRTC/관리형 RTC 및 STT Provider
- 외부 검증 Token 만료·재발급·접근 정책
- P0 표준 질문 정의와 P1/P2 승인 권한
- 개인정보, STT, 원본 음성 Retention 정책

이 문서는 위 기술 선택을 임의로 확정하지 않으며, 선택 이후에도 Case 중심 Bundle + Delta Event 원칙은 유지한다.
