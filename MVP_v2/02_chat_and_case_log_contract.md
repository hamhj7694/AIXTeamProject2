# Chat Block · Case Live Log Contract

## 1. 채팅을 단순 문자열 목록으로 만들지 않는 이유

MVP v2의 채팅에는 일반 텍스트뿐 아니라 질문·선택지·검증·조치·결과가 함께 나타난다. 따라서 각 항목을 `type + audience + data + source`를 가진 구조화 Block으로 렌더링한다.

채팅 Block은 화면 표현이며 DB 진실값이 아니다. 원본은 Message·Question·Verification·Action·Report·Event Entity다.

## 2. MVP 필수 Block

| Block Type | 역할 | 고객 | 은행 |
|---|---|:---:|:---:|
| `TEXT_MESSAGE` | 일반 대화 | O | O |
| `QUESTION_CARD` | 질문·선택지·자유답변 | 응답 | 생성·검토·전송 |
| `SAFETY_ACTION_CARD` | 즉시 중단·안전 행동 | O | O |
| `CASE_UPDATE_CARD` | Case 정보 반영 결과 | 고객용 요약 | 변경 상세 |
| `VERIFICATION_CARD` | 기관 검증 요청·상태·결과 | 요약 | 상세·관리 |
| `BANK_ACTION_CARD` | 은행 조치 | 결과 확인 | 추천·기록·완료 |
| `FINAL_RESULT_CARD` | 사건 종료 결과 | 고객용 결과 | 확정 결과 |
| `SYSTEM_EVENT` | 연결·상태 전환·오류 | O | O |

## 3. 확장 Block

- `FILE_CARD`: 이미지·문자 캡처·문서
- `EVIDENCE_CARD`: 근거와 출처
- `RAG_GUIDE_CARD`: 공식문서 기반 예방·구제 가이드
- `TAKEOVER_CARD`: 담당자 개입과 AI 재개
- `REPORT_PREVIEW_CARD`: 요청 시 현재 Case 구조 요약
- `ERROR_CARD`: 실패·충돌·Retry

확장 Block은 처음부터 모두 구현하지 않는다. 실제 API와 데이터가 연결되는 순서대로 추가한다.

## 4. 권장 Conversation Item Envelope

```json
{
  "item_id": "item_102",
  "case_id": "VP-014",
  "type": "QUESTION_CARD",
  "audience": "CUSTOMER",
  "actor_type": "CUSTOMER_AGENT",
  "source_entity": {
    "entity_type": "QUESTION",
    "entity_id": "q_transfer_status",
    "version": 3
  },
  "data": {
    "text": "이미 송금했나요?",
    "options": [
      {"label": "아직 송금하지 않았어요", "value": "NOT_TRANSFERRED"},
      {"label": "이미 송금했어요", "value": "TRANSFERRED"}
    ]
  },
  "actions": [
    {"type": "ANSWER_QUESTION", "enabled": true}
  ],
  "created_at": "2026-09-02T14:20:00+09:00"
}
```

### 필수 원칙

- `audience`로 고객·은행·내부 공개 범위를 구분한다.
- `source_entity`로 원본 Entity와 Version을 추적한다.
- Frontend가 자연어를 해석해 Case 값을 임의 생성하지 않는다.
- Action 실행은 General API Command를 호출한다.
- 저장 성공 후 받은 Entity 또는 Event를 기준으로 Block을 갱신한다.

## 4.1 은행 채널과 AI 호출

은행 화면은 하나의 Message 목록을 공유하지 않는다. 최소 세 가지 Channel을 구분한다.

| Channel | 작성자·수신자 | 기본 AI 동작 |
|---|---|---|
| `TEAM` | 은행 관계자 ↔ 은행 관계자 | 침묵 |
| `CUSTOMER` | 은행 담당자 ↔ 고객 | 고객 Agent 정책에 따름 |
| `AI_INTERNAL` | 은행 담당자 ↔ Bank Copilot | 명시 호출 시 응답 |

`TEAM` 채널에서 `@CaseCopilot`을 언급하거나 AI 요청 버튼을 누르면 Backend가 AI Invocation Command를 생성한다. AI는 권한 있는 Case Projection·현재 채널의 관련 대화·저장된 근거만 받아 응답하며, 응답 Audience는 기본적으로 `AI_INTERNAL`이다.

```text
TEAM: 김OO가 @CaseCopilot 현재 미확인사항을 정리해줘
  → AI Invocation Command
  → Case Context Projection 생성
  → Bank Copilot 응답 저장
  → AI_INTERNAL 채널과 Case Live Log에 결과 반영
```

AI가 만든 고객 질문은 `DRAFT` 상태로 저장하고, 은행 담당자의 승인·편집 후에만 `CUSTOMER` 채널로 전송한다.

---

## 5. 은행 Case Live Log

### 5.1 역할

`Case Live Log`는 실시간 보고서가 아니다. 하나의 Case에서 **언제, 누가, 어떤 정보를 추가하거나 상태를 바꿨는지** 확인하는 운영 이력이다.

은행 담당자는 다음 질문에 빠르게 답할 수 있어야 한다.

- 고객이 마지막으로 무엇을 답했는가?
- 어떤 사실이 Case에 반영됐는가?
- 기관 검증은 언제 요청됐고 현재 상태는 무엇인가?
- 어떤 은행 조치가 기록됐는가?
- 담당자가 언제 개입하거나 AI 상담을 재개했는가?
- Case가 왜 현재 상태로 전환됐는가?

### 5.2 Log에 포함할 Event

| Event | Log 표현 |
|---|---|
| `CASE_CREATED` | Case가 생성됨 |
| `CASE_FIELD_UPDATED` | Case 상태·Mode·핵심 필드 변경 |
| `MESSAGE_ADDED` | 고객·직원·Agent 메시지 추가 |
| `QUESTION_UPDATED` | 질문 생성·전송·응답 완료 |
| `VERIFICATION_UPDATED` | 기관 검증 요청·진행·완료 |
| `BANK_ACTION_ADDED` | 은행 조치 기록 |
| `REPORT_SECTION_UPDATED` | Case 구조 요약의 특정 영역 변경 |
| `HUMAN_TAKEOVER` | 담당자 직접 개입 |
| `AI_RESUMED` | AI 상담 재개 |
| `VOICE_SESSION_UPDATED` | 음성 Session 상태 변경 |
| `TRANSCRIPT_SEGMENT_ADDED` | Final Transcript Segment 추가 |
| `CASE_CLOSED` | 사건 종료 |

실제 Event 이름은 기존 Backend Contract를 우선하며, Frontend에서 임의로 비슷한 Event를 추가하지 않는다.

### 5.3 Log Row 구성

```text
[10:42:18] CUSTOMER · 고객 답변
이미 송금했는지 여부가 NOT_TRANSFERRED로 확인됨
연결: message_21 · question_4
```

필수 필드:

- 발생시각
- Actor
- Event Type
- 한 줄 요약
- 상태 또는 Operation
- 연결된 Entity ID
- Event ID와 Entity Version
- 상세 Payload 펼치기

### 5.4 표시 규칙

- Event는 Append-only로 표시한다.
- 기존 Log Row를 조용히 수정하거나 삭제하지 않는다.
- 정정이 필요하면 새로운 Correction Event를 추가한다.
- 최신 Event를 위에 표시하는 것을 기본으로 한다.
- 새 Event가 들어오면 `새 업데이트 N건` 표시 후 사용자가 위치를 잃지 않게 한다.
- 자동 Scroll은 사용자가 최신 위치를 보고 있을 때만 적용한다.
- 고객 메시지·검증·조치·시스템 Event 필터를 제공한다.
- Log 요약은 원본 의미를 바꾸지 않는 규칙 기반 문구를 우선 사용한다.

### 5.5 Realtime 단계

#### MVP

```text
GET /api/cases/:caseId/events?after=:cursor
  → 새 Event 수신
  → event_id 중복 제거
  → Case Live Log Append
  → 필요한 Entity/Bundle만 재조회
```

#### 이후

```text
SSE 또는 WebSocket
  → 동일 Event Envelope 사용
  → 재접속 시 Cursor 이후 Event 복구
```

Transport를 바꿔도 Event 적용 규칙은 유지한다.

---

## 6. Chat과 Log의 차이

| 구분 | Chat | Case Live Log |
|---|---|---|
| 목적 | 사용자와 AI/직원의 상호작용 | 사건 변경 이력 추적 |
| 내용 | 메시지·질문·카드·실행 버튼 | 저장 완료된 Event 요약 |
| 수정 | Draft 입력·질문 편집 가능 | Append-only |
| 고객 노출 | 고객용 Projection만 | 원칙적으로 은행 내부 |
| 원본 | 여러 Entity의 Conversation Projection | `case_events` |

Chat 메시지가 추가되면 Log에도 `MESSAGE_ADDED`가 나타날 수 있지만 두 영역의 목적은 다르다.

---

## 7. 실패·중복·순서 처리

- 모든 Command에 `client_request_id`를 사용한다.
- Event는 `event_id`로 중복 제거한다.
- Entity는 `version`이 더 최신일 때만 갱신한다.
- Cursor 공백이나 순서 불연속을 감지하면 Event 목록 또는 Bundle을 재조회한다.
- `409 VERSION_CONFLICT` 발생 시 최신 Entity를 다시 받아 사용자에게 알린다.
- AI 응답 실패와 원본 고객 Message 저장 실패를 구분한다.
- AI 부가 응답이 실패해도 저장된 고객 Message와 Case Event는 유지한다.
