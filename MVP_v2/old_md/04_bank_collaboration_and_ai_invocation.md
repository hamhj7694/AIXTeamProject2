# 은행 협업 Room · 참여자 상태 · AI 호출 Contract

## 1. 결정

은행 화면은 기본 1:1 챗봇이 아니라 **Case Collaboration Room**이다. 여러 관계자가 동일 Case를 보면서 사람끼리 협의하고, 필요할 때만 AI를 호출한다.

이유:

- 은행의 내부 대화는 고객 대화와 다른 권한을 가진다.
- AI가 모든 사람 대화에 반응하면 협업 흐름을 방해한다.
- AI의 가설·질문 초안·대응전략은 고객에게 자동 노출되면 안 된다.
- 담당자·검토자·관찰자의 역할과 현재 접속 상태가 팀 협업에 필요하다.

## 2. Room 구성

```text
Case Collaboration Room
├─ TEAM 채널
│  ├─ 은행 관계자 간 협업 대화
│  └─ @CaseCopilot 호출 가능
├─ CUSTOMER 채널
│  └─ 은행 담당자와 고객의 실제 대화
├─ AI_INTERNAL 채널
│  └─ Bank Copilot 요청·응답·질문 초안
├─ Participant Presence
│  └─ 담당자·검토자·보고 중·입력 중
└─ Case Live Log
   └─ 저장 완료된 Case Event 이력
```

## 3. Case Member와 Presence 분리

### 3.1 영구 역할: `case_members`

Case에 참여할 권한과 업무 역할을 저장한다.

| 필드 | 설명 |
|---|---|
| `case_id` | 대상 Case |
| `user_id` | 사용자 식별자 |
| `display_name` | 화면 표시 이름 |
| `role` | `CASE_OWNER`, `CHAT_OPERATOR`, `REVIEWER`, `VIEWER` |
| `assigned_at` | 참여 또는 배정 시각 |
| `assigned_by` | 배정자 |
| `status` | `ACTIVE`, `REMOVED` |

역할은 DB에 영구 저장하며, 변경되면 `CASE_MEMBER_UPDATED` Event를 추가한다.

### 3.2 임시 상태: `case_presence`

현재 화면을 보고 있거나 입력 중인지 나타내는 상태다. 업무 이력이나 보고서의 사실로 저장하지 않는다.

| 필드 | 설명 |
|---|---|
| `case_id`, `user_id` | 현재 Room과 사용자 |
| `presence` | `VIEWING`, `TYPING`, `AWAY`, `OFFLINE` |
| `channel` | `TEAM`, `CUSTOMER`, `AI_INTERNAL` 중 현재 위치 |
| `last_seen_at` | Heartbeat 기준 시각 |
| `expires_at` | TTL 만료 시각 |

MVP에서는 15~30초 단위 Heartbeat/Polling으로 시작할 수 있다. SSE/WebSocket 전환 시 동일 모델을 사용한다.

## 4. Header 표시 규칙

```text
[Case 담당 이OO] [채팅 담당 김OO] [검토 박OO] [보고 중 3명]
```

- Header에는 최대 3명의 역할 Avatar와 `보고 중 N명`만 표시한다.
- 전체 참여자 명단과 마지막 접속 시각은 Popover에서 확인한다.
- `입력 중`은 현재 선택한 Channel의 상태만 짧게 표시한다.
- 고객에게는 내부 이름·역할·Presence를 보여주지 않는다.

## 5. AI 호출 규칙

### 5.1 기본값: AI 침묵

은행 관계자가 `TEAM` 채널에서 일반 대화를 나눌 때 AI는 답변하지 않는다.

```text
김OO: 기관 확인은 아직 응답 대기입니다.
이OO: 고객에게 송금 여부를 한 번 더 물어보죠.
```

위 대화만으로 AI Message나 고객 Message를 생성하지 않는다.

### 5.2 명시 호출: `@CaseCopilot`

```text
김OO: @CaseCopilot 지금 확인된 사실, 미확인사항, 다음 질문 후보를 정리해줘.
```

호출 조건:

- 발신자가 해당 Case의 `CASE_OWNER`, `CHAT_OPERATOR`, `REVIEWER` 권한을 가진다.
- Message Channel이 `TEAM` 또는 `AI_INTERNAL`이다.
- 명시적인 Mention 또는 AI 요청 Action이 있다.
- AI 요청은 `client_request_id`로 멱등성을 보장한다.

AI가 받는 정보:

- 권한에 맞춘 Case Header와 구조화 상태
- 최근 관련 Message와 Event
- Verification·Action·Report 요약
- 필요 시 승인된 RAG 근거

AI가 반환하는 정보:

- 내부 업무 답변
- 질문 후보 Draft
- 대응전략 Draft
- Case Patch 제안
- Evidence·Confidence·Warning

AI는 직접 DB를 수정하거나 고객에게 Message를 전송하지 않는다. General Backend가 결과를 검증하고 Entity 저장·Event 발행을 처리한다.

### 5.3 고객 전송 안전장치

```text
AI 질문 초안
  → DRAFT Question 저장
  → 담당자 편집·승인
  → CUSTOMER Channel 전송
```

AI 답변, 내부 추론, RAG Debug 정보, 승인 전 조치는 고객 Channel에 자동 복사하지 않는다.

## 6. 최소 API Contract

기존 Case API에 다음 리소스를 추가하는 것을 목표로 한다.

```text
GET  /api/cases/:caseId/members
POST /api/cases/:caseId/members
PATCH /api/cases/:caseId/members/:userId

GET  /api/cases/:caseId/presence
POST /api/cases/:caseId/presence/heartbeat

GET  /api/cases/:caseId/messages?channel=TEAM
POST /api/cases/:caseId/messages

POST /api/cases/:caseId/ai/invocations
GET  /api/cases/:caseId/ai/invocations/:invocationId
```

기존 `messages` API를 확장할 때는 적어도 다음 필드를 추가한다.

```json
{
  "channel": "TEAM | CUSTOMER | AI_INTERNAL",
  "audience": "BANK_INTERNAL | CUSTOMER",
  "mentions": ["CaseCopilot"],
  "reply_to_message_id": null,
  "client_request_id": "..."
}
```

## 7. MVP 검증 시나리오

1. 김OO와 이OO가 같은 Case의 `TEAM` Channel에 접속한다.
2. Header에는 채팅 담당자·Case 담당자·보고 중 인원이 보인다.
3. 일반 TEAM Message 두 건을 작성해도 AI는 응답하지 않는다.
4. 김OO가 `@CaseCopilot`을 호출한다.
5. AI 응답은 `AI_INTERNAL`에만 기록된다.
6. AI가 제안한 질문은 Draft로 표시된다.
7. 이OO가 질문을 승인한 후에만 CUSTOMER Channel에 전송한다.
8. 고객 답변은 Message와 Case Event로 저장된다.
9. 은행의 Case Live Log에는 고객 답변과 질문 전송 Event가 Append된다.
10. 고객 화면에는 은행 내부 TEAM/AI_INTERNAL Message가 노출되지 않는다.

