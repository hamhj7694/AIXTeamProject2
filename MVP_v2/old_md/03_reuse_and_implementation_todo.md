# 기존 코드 재활용 범위 · 구현 TODO

## 1. 기본 전략

`MVP_v2`는 기존 프로젝트를 폐기하고 전부 다시 만드는 작업이 아니다.

- 기존 Backend의 Case·Message·Event·Verification·Action·Bundle API를 기준선으로 재활용한다.
- 기존 Frontend의 API Client·공통 UI·Case Route 처리 방식을 선별 재활용한다.
- 기존 복잡한 페이지 Layout과 Mock 중심 업무상태는 그대로 복사하지 않는다.
- 새 Frontend는 Chat Block과 Case Live Log를 중심으로 새로 구성한다.

## 2. 예정 폴더 구조

```text
MVP_v2/
├─ README.md
├─ 01_frontend_final_direction.md
├─ 02_chat_and_case_log_contract.md
├─ 03_reuse_and_implementation_todo.md
├─ backend/                       # 기존 Backend 기준선 재활용 예정
└─ frontend/                      # Chat-first Frontend 신규 구현 예정
   └─ src/
      ├─ app/
      ├─ components/
      │  ├─ chat/
      │  ├─ case-log/
      │  └─ layout/
      ├─ features/
      │  ├─ customer-room/
      │  ├─ bank-room/
      │  └─ case-state/
      ├─ services/
      └─ types/
```

이번 문서 작업에서는 `backend/`, `frontend/` 코드를 아직 복사하지 않는다.

---

## 3. Backend 재활용 Map

기준 위치: `02_workspace/backend`

| 기존 기능 | MVP v2 사용 | 비고 |
|---|:---:|---|
| `POST /api/cases/analyze` | O | 최초 Case 생성 |
| `GET /api/cases`, `GET /api/cases/:id` | O | 목록·기본 상태 |
| `PATCH /api/cases/:id` | O | Version 기반 상태 전환 |
| Message create/list | O | 고객·은행 대화 저장 |
| Event list + cursor | O | Bank Case Live Log와 화면 갱신 |
| Verification create/list/update | O | 기관 검증 카드 |
| Action create/list | O | 은행 조치 카드와 Log |
| Takeover/Resume | O | 고객·담당자 연결 상태 |
| Case Bundle | O | 화면 최초 Projection |
| LIVE/FINAL Report | 부분 | 상시 패널이 아닌 요청형 요약·종료 결과 |
| Voice Session/Transcript | 후순위 | UI Hook만 준비 가능 |
| Diagnosis AI | O | 기존 Case 생성 기준 유지 |
| Case Support Workflow | 부분 | General API 연결 Contract 추가 필요 |
| RAG·Vector DB | 후순위 | 공식문서 Corpus 확정 후 연결 |

### 추가로 필요한 Backend 경계

```text
POST /api/cases/:caseId/chat
GET  /api/cases/:caseId/conversation?channel=
POST /api/cases/:caseId/questions/:questionId/answer
POST /api/cases/:caseId/questions/:questionId/send
GET  /api/cases/:caseId/events?after=
```

Endpoint 이름은 구현 전 A/B/C Contract Review로 확정한다. 기존 Resource API로 충분하다면 불필요한 통합 Endpoint를 추가하지 않는다.

---

## 4. Frontend 재활용 Map

기준 위치: `02_workspace/frontend`

| 기존 파일·영역 | 재활용 방향 |
|---|---|
| `src/services/caseApi.ts` | Case Analyze/List/Get Client 재활용 |
| `src/services/caseWorkflowApi.ts` | Bundle·Message·Verification·Action·Voice Client 재활용 |
| `src/services/conversationApi.ts` | Message·Event Cursor Client와 통합 검토 |
| `src/features/case-state/useCaseEventRefresh.ts` | MVP Polling 기준선으로 재활용 |
| `src/components/ui/**` | Button·Card·Badge 등 선별 재활용 |
| `src/components/layout/**` | 최소 Header만 선별 재활용 |
| `CustomerPage.tsx` | API 동작 참고, Layout은 새로 작성 |
| `features/manager-room/**` | Case/Message 연결 참고, 복잡한 Layout은 미재사용 |
| `data/mock/**` | Demo Fixture로만 격리, 실제 결과처럼 표시 금지 |

## 5. 새 Frontend 핵심 Component

### 공통

- `ChatWorkspace`
- `ChatMessageList`
- `ChatComposer`
- `ChatBlockRenderer`
- `QuestionCard`
- `VerificationCard`
- `CaseUpdateCard`
- `BankActionCard`
- `SystemEventCard`
- `ConnectionIndicator`

### 고객

- `CustomerRoomPage`
- `SafetyActionBar`
- `CustomerProgressMini`
- `HumanConnectionBadge`
- `UrgentHelpButton`

### 은행

- `BankRoomPage`
- `BankCaseHeader`
- `ConversationChannelTabs`
- `CaseLiveLogPanel`
- `CaseLogRow`
- `CaseLogFilter`
- `PriorityActionBar`
- `CaseSummaryDrawer`

---

## 6. 구현 순서

### Phase 0 — 기준선 복제와 실행환경

- [ ] `MVP_v2/backend`에 기존 Backend 기준선 복사
- [ ] `MVP_v2/frontend`에 새 Vite React TypeScript App 구성
- [ ] `.env.example`과 API Base URL 구성
- [ ] 기존 프로젝트와 Port·환경변수 충돌 여부 확인
- [ ] 기존 Secret을 복사하거나 Commit하지 않음

### Phase 1 — 공통 Chat Shell

- [ ] 공통 Header·Chat Workspace·하단 Composer
- [ ] Chat Scroll과 입력 Draft 보존
- [ ] Block TypeScript Discriminated Union
- [ ] `ChatBlockRenderer`
- [ ] Loading·Empty·Error·Retry
- [ ] Desktop·Mobile Layout

### Phase 2 — 고객 핵심 흐름

- [ ] Case Bundle 조회
- [ ] 고객 Message 저장·조회
- [ ] 질문 카드 응답
- [ ] Safety Action과 현재 진행 표시
- [ ] 은행 담당자 연결 상태
- [ ] Verification 고객용 요약
- [ ] 고객 Message → Case 반영 → Event E2E

### Phase 3 — 은행 핵심 흐름

- [ ] Case Member 역할과 Presence Contract 구현
- [ ] AI 업무 대화와 고객 대화 Channel 분리
- [ ] 팀 협업 채팅에서 `@CaseCopilot` 명시 호출
- [ ] 고객 Message 조회·직원 Message 전송
- [ ] 질문 추천·편집·승인·전송
- [ ] Verification Task 생성·상태 변경
- [ ] Bank Action 기록
- [ ] Takeover·Resume
- [ ] Case 요약 Drawer

### Phase 4 — Case Live Log

- [ ] Event Cursor Polling 연결
- [ ] Log Row Actor·Type·요약 Mapping
- [ ] 중복 제거·순서 처리
- [ ] 새 업데이트 Badge
- [ ] Event Filter와 상세 Payload
- [ ] Event 수신 후 필요한 Entity만 갱신
- [ ] Customer↔Bank 동일 Case Browser E2E

### Phase 5 — AI Orchestration 연결

- [ ] Case Support Workflow Internal Contract 확정
- [ ] General Backend → AI API 호출 경계
- [ ] 고객 자유답변 구조화
- [ ] Question Candidate 생성
- [ ] Brief/Case Patch 저장
- [ ] Agent 결과의 evidence·confidence·warnings 표시
- [ ] AI 부분 실패와 Retry

### Phase 6 — 종료 결과와 안정화

- [ ] FINAL 결과 생성·조회
- [ ] 고객용 종료 결과와 은행용 확정 결과 분리
- [ ] 409 Version Conflict 처리
- [ ] 권한·Audience 검증
- [ ] 민감정보·로그 점검
- [ ] Frontend Build·Backend Test·Browser E2E

### Phase 7 — 후순위

- [ ] SSE 또는 WebSocket 전환
- [ ] 공식문서 RAG와 Case Evidence
- [ ] 실제 FDS·외부기관 Adapter
- [ ] Streaming STT·Voice AI
- [ ] Docker·Deployment·운영 모니터링

---

## 7. MVP 완료 조건

- [ ] 고객과 은행이 동일한 Case를 조회한다.
- [ ] 두 화면의 Composer가 각각 채팅 하단에 있다.
- [ ] 고객 답변이 Browser 저장소가 아니라 Backend에 저장된다.
- [ ] 은행이 고객의 새 답변을 동일 Case에서 확인한다.
- [ ] 은행 내부 AI 대화가 고객에게 노출되지 않는다.
- [ ] 사람끼리 TEAM 채널에서 대화할 때 AI가 자동 응답하지 않는다.
- [ ] `@CaseCopilot` 호출만 AI_INTERNAL 응답을 만든다.
- [ ] 채팅 담당자·Case 담당자·검토자·보고 중 인원이 은행 Header에 표시된다.
- [ ] 질문·검증·조치가 구조화된 Card로 표시된다.
- [ ] 은행 Case Live Log가 저장 완료된 Event만 Append한다.
- [ ] Event 중복·순서·재연결을 처리한다.
- [ ] 고객에게 내부 FDS·모델·담당자 정보가 노출되지 않는다.
- [ ] Mock과 실제 API 데이터가 명확하게 구분된다.
- [ ] 주요 오류와 AI 부분 실패를 복구할 수 있다.
- [ ] Frontend Production Build와 핵심 Backend Test가 통과한다.

## 8. 하지 말아야 할 것

- 기존 복잡한 Dashboard를 새 폴더에 그대로 복사하지 않는다.
- 모든 정보를 채팅 텍스트 한 덩어리로 저장하지 않는다.
- AI 업무 대화와 고객 전송 메시지를 같은 Channel로 처리하지 않는다.
- Frontend에서 Case 사실을 추론해 DB 값처럼 표시하지 않는다.
- Case Live Log를 수정 가능한 메모 목록으로 만들지 않는다.
- 고객에게 은행 내부 분석·FDS·RAG Debug 정보를 노출하지 않는다.
- RAG 또는 LLM이 공식 연락처·금융조치를 기억으로 생성하게 하지 않는다.
- 저장 실패한 AI 결과를 성공한 Case Update처럼 표시하지 않는다.
