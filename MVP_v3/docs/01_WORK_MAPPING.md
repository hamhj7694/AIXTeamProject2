# CONTEXT-FIRST CASE Frontend V3 작업 매핑

기준 문서: `MVP_v3/PRD.md`

## 1. 제품 목표와 정본

V3는 은행 담당자가 하나의 Shared Case에서 사건 파악, 고객 대화, 주장·요구 확인, 기관 검증, 추가 질문, 보호조치와 Recovery 기록까지 처리하는 업무 화면이다. Frontend에 Customer/Verification/Bank Agent 선택기를 만들지 않는다. Agent 선택은 Backend의 Case Orchestrator 책임이고 Frontend는 결과와 상태만 사람의 언어로 표시한다.

화면 정본은 두 개다.

- `/`: 현재 대응 Case 목록과 선택 안내
- `/cases/:caseId`: 좌측 Case 목록, 중앙 Shared Case Conversation, 우측 Case Context

## 2. 코드 소유 경로

| 영역 | V3 정본 | 책임 |
|---|---|---|
| 앱 시작 | `frontend/src/main.tsx`, `frontend/src/App.tsx` | Router, 전역 Shell |
| API 계약 | `frontend/src/api/types.ts` | General API 응답/요청 Type |
| API 호출 | `frontend/src/api/client.ts`, `frontend/src/api/cases.ts` | URL, 오류, Case API, binary upload |
| Case 목록 | `frontend/src/components/CaseListPane.tsx` | 우선순위 선택, 검색, Empty/Error |
| Case Room | `frontend/src/pages/CaseRoomPage.tsx` | Case 데이터 조율, polling, mutation refresh |
| 중앙 Timeline | `frontend/src/components/SharedConversation.tsx` | 메시지·질문·검증·조치·Event 시간순 통합 |
| 우측 Context | `frontend/src/components/CaseContextPanel.tsx` | 위험 근거, Claim, Demand, Fact, AI 확인 체크리스트, 담당자 판단·조치 기록, 완료 항목 복원 |
| 입력/첨부 | `frontend/src/components/ConversationComposer.tsx` | 고객/내부 채널, Enter 전송, 첨부 업로드 |
| 업무 Dialog | `frontend/src/components/CaseActionDialogs.tsx` | 질문, Verification, Action 생성/수정 |
| UI 표현 규칙 | `frontend/src/presentation.ts` | 상태·위험·시간·진단 Context 투영 |
| Timeline 계약 | `frontend/src/timeline.ts` | 모든 항목의 단일 `occurredAt ASC` 정렬 |
| 디자인 | `frontend/src/styles.css` | 금융 업무도구 정보 위계와 반응형 |

## 3. V2 재사용 판단

### 재사용하는 계약과 동작

- `generalApiClient`: 단일 API base URL, JSON 오류 해석 방식
- `caseApi`: `/api/cases`, `/api/cases/{id}`와 diagnosis Context
- `mvpChatApi`: Bundle, Message, Attachment, Question, Fact, AI invocation
- `caseWorkflowApi`: Verification, Action mutation과 version conflict
- `caseSync`: mutation 뒤 동일 화면 재조회 원칙
- 첨부 제한: 최대 10개, 파일당 10MB, 서버 MIME/signature 검증
- 메시지 작성자 ID 기반 본인 말풍선 판정
- 고객 공개/BANK_INTERNAL/AI_PRIVATE 공개 경계
- 모든 채팅 내부 항목의 시간순 정렬 원칙

### V3에서 다시 만드는 UI

- V2의 페이지별 은행/고객/검증 분리 Navigation
- AI 개인 작업공간과 Agent 이름 중심 탭
- 여러 카드가 중첩된 Dashboard형 화면
- 별도 Live Log와 Conversation의 중복 표시
- localStorage 보고서·북마크 UI

### 현재 Backend의 실제 한계

- 인증/RBAC가 없어 Frontend가 보낸 actor/view를 서버가 신뢰한다.
- SSE/WebSocket endpoint가 없고 polling만 가능하다.
- WorkCard lifecycle은 DB에 영속화되지 않는다.
- Action은 업무 기록이며 실제 지급정지·신고를 자동 실행하지 않는다.
- 음성 통화 기능은 V3 범위에서 제외한다.

## 4. Frontend → API → 데이터 매핑

| 사용자 기능 | General API | Source of Truth | V3 표시 |
|---|---|---|---|
| Case 목록 | `GET /api/cases` | `cases` | 좌측 Case List |
| Case 상세 | `GET /api/cases/{id}` | `cases + diagnosis_json` | Header, Claim, Demand, Risk |
| Case 묶음 | `GET /api/cases/{id}/bundle?view=bank` | Message/Question/Verification/Action/Event | Conversation과 Context |
| AI Brief | `GET /api/cases/{id}/ai/case-support` | AI Case snapshot projection | 중앙 상단 2~4문장 Brief |
| Fact | `GET /api/cases/{id}/facts` | `case_facts` | 확인된 사실/확인 후보 |
| 고객 메시지 | `POST /api/cases/{id}/messages` channel CUSTOMER | `messages` | Conversation |
| 내부 기록 | 같은 endpoint, channel TEAM | `messages` | 은행 내부 표시 |
| AI 도움 | `POST /api/cases/{id}/ai/invocations` | AI API 경유 후 Message 저장 | Conversation의 AI 분석 |
| 확인 질문 | 후보 GET → Queue POST | `customer_questions` | 질문/답변 Timeline |
| Verification | POST/PATCH `/verifications` | `verification_tasks` | 요청·결과 Timeline + Context |
| Action | POST `/actions` | `actions` | 조치 기록 Timeline + Context |
| 첨부 | POST `/attachments` → Message `attachment_ids` | 파일 저장소 + attachment DB | 메시지 첨부 |
| 변경 감지 | Case/Bundle/Fact polling | Event cursor/각 aggregate | 5초 안전 갱신 |

Frontend는 AI API `8101`을 직접 호출하지 않는다. Frontend `5176`의 `/api` proxy가 General API `8100`을 호출하고 General API가 AI API를 오케스트레이션한다.

AI Case Support는 5초 polling 대상이 아니다. 최초 Case 진입과 메시지·질문·검증·조치 등 의미 있는 변경 직후에만 갱신해 반복 유료 호출과 화면 지연을 방지한다.
은행의 `사건 맥락`은 AI support의 최신 `case_context`(`key_signals`, `offender_claims`, `offender_demands`)를 우선 사용한다. 질문·답변·Fact·기관 확인·조치처럼 AI 입력에 포함되는 의미 상태의 변경 지문이 달라질 때만 재투영하며, 일반 채팅·presence 갱신만으로 AI support를 다시 호출하지 않는다.

## 5. Shared Case Timeline 규칙

`Message.created_at`, `Question.asked_at/answered_at`, `Verification.created_at/updated_at`, `Action.created_at`, `Event.occurred_at`, `AI Brief/Case.created_at`을 `TimelineEntry`로 투영한다. 모든 항목은 `occurredAt ASC`로 정렬한다. 동일 사건을 표현하는 원본 Message와 구조화 Question 카드가 겹치면 구조화 카드를 우선하고 Message는 중복 제거한다.

`대화` 보기에는 사람이 읽고 행동해야 하는 메시지·질문·검증·조치만 보인다. `전체 기록`은 여기에 기술 Event를 추가한다. 별도 Timeline 페이지는 만들지 않는다.

## 6. 사용자 관점 완료 기준

- 5초 안에 사건 유형과 AI Brief를 읽을 수 있다.
- 10초 안에 위험 근거, 범죄자 주장·요구, 확인됨/확인 필요, 다음 조치를 찾을 수 있다.
- 30초 안에 메뉴 이동 없이 고객 메시지, 질문, Verification, Action을 실행할 수 있다.
- AI 제안, 고객 진술, 기관 확인, 담당자 조치가 시각적으로 구분된다.
- 낮은 위험 Case는 붉은 긴급 UI를 사용하지 않는다.
- 좁은 화면에서는 Case List와 Context가 Drawer로 이동하고 Conversation 폭을 유지한다.

## 7. 변경 영향 확인 순서

`Component → State → Type → API Client → General API Contract → Repository/DB → AI API` 순으로 확인한다. V3에서 계약 부족이 발견되면 전체 검색 후 최소 Backend 변경만 수행하며, V2 파일을 삭제하거나 덮어쓰지 않는다.

## 8. 운영 연결 전 책임 경계

| 주체 | 반드시 제공할 것 | Frontend가 기대하는 결과 |
|---|---|---|
| Backend | 인증 사용자·역할, RBAC, customer/bank view 강제 | actor를 요청 본문이 아닌 서버 세션으로 확정 |
| Backend | Case 전체 이벤트 sequence 또는 cursor | 같은 시각의 Card와 Message도 결정적으로 정렬 |
| Backend | 질문→답변→Fact 후보→사람 확정 lifecycle | 고객 답변과 공식 확인 사실을 혼동하지 않음 |
| Backend | Work Card 영속화, idempotency, 보상 처리 | 중간 실패 후 중복·반쪽 상태 방지 |
| AI | 구조화 질문·Brief·권고 계약과 출처·신뢰도 | 자유문 텍스트가 아닌 검증 가능한 Card 렌더링 |
| AI/Backend | quota와 cache를 다중 인스턴스에서 공유 | 반복 호출과 비용 폭증 방지 |
| Infra | 악성 파일 검사·Object Storage·서명 URL | 운영 첨부파일의 안전한 조회와 만료 |

현재 V3는 이 계약을 호출할 수 있는 Frontend adapter와 UI를 제공한다. 인증, 실제 외부 금융 업무 실행, SSE/WebSocket, 운영 저장소는 후속 담당자의 서버 구현 범위다.
