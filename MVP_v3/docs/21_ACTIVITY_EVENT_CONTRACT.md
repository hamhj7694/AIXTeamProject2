# Case Activity Event 공통 계약

작성일: 2026-09-15

## 목적

Fact·Verification·Action·Task·Customer Progress의 변경을 중앙 채팅에 간결한 시스템 카드로 표시하면서, 우측 Context Panel은 최신 projection을 유지하도록 연결한다.

## 이벤트 구조

```json
{
  "event_id": "evt-...",
  "case_id": "VP-10",
  "event_type": "ACTION_UPDATED",
  "resource_type": "ACTION",
  "resource_id": "act-...",
  "actor_type": "BANK_STAFF",
  "actor_id": "staff-...",
  "visibility": "BANK_INTERNAL",
  "summary": "고객 재확인 업무가 완료되었습니다.",
  "before": {"status": "REQUESTED"},
  "after": {"status": "COMPLETED"},
  "revision": 12,
  "created_at": "2026-09-15T00:00:00Z"
}
```

## 이벤트 종류

| Resource | 생성 | 수정 | 상태·검토 |
|---|---|---|---|
| Fact | `FACT_CREATED` | `FACT_UPDATED` | `FACT_CONFIRMED`, `FACT_REJECTED`, `FACT_RESTORED` |
| Verification | `VERIFICATION_CREATED` | `VERIFICATION_UPDATED` | `VERIFICATION_COMPLETED`, `VERIFICATION_FAILED` |
| Action | `ACTION_CREATED` | `ACTION_UPDATED` | `ACTION_COMPLETED`, `ACTION_CANCELLED`, `ACTION_RESTORED` |
| Task | `TASK_CREATED` | `TASK_UPDATED` | `TASK_COMPLETED`, `TASK_CANCELLED`, `TASK_RESTORED` |
| Customer Progress | `CUSTOMER_PROGRESS_UPDATED` | 동일 이벤트 | 상태 변경 포함 |
| Summary | `SUMMARY_UPDATED` | 동일 이벤트 | 직원 override 포함 |

## 표시 규칙

- 중앙 채팅: 실제 Message와 공개 가능한 Activity Event를 시간순으로 표시한다.
- 우측 Context Panel: Activity Event를 직접 정답으로 사용하지 않고 canonical resource를 다시 projection한다.
- `BANK_INTERNAL` 이벤트는 은행 화면에만 표시한다.
- `CUSTOMER_SHARED`/`PUBLIC_EVENT`만 고객 화면에 표시할 수 있다.
- `AI_PRIVATE` 이벤트는 UI에 직접 표시하지 않는다.
- 이벤트에는 전체 근거나 내부 reasoning을 복제하지 않고 직원용 요약만 포함한다.

## 멱등성·정렬

- 이벤트 고유 키: `case_id + resource_type + resource_id + revision + event_type`.
- 동일 키는 한 번만 저장·표시한다.
- `revision`과 `created_at`을 사용해 순서를 결정하고, 늦게 도착한 이전 revision은 최신 상태를 덮어쓰지 않는다.
- 원본 mutation과 event 기록은 같은 트랜잭션에서 처리한다.

## 실패·권한 규칙

- Resource 저장 성공 후 event 기록이 실패하면 재시도 가능한 outbox 상태로 남긴다.
- Event 기록 실패가 이미 저장된 Resource를 rollback하지 않는다.
- actor 권한과 visibility는 서버에서 검증한다.
- 고객 화면 projection은 allowlist를 적용해 내부 상태·개인 메모·AI reasoning을 차단한다.

## 현재 구현과 GAP

- 현재 중앙 Timeline은 `messages`, 질문, verification, `actions`, final report를 조합한다.
- 현재 모든 Context Fact/Task/Suggestion 변경이 공통 Activity Event로 기록되지는 않는다.
- 이 문서는 계약 기준선이며, 실제 테이블·API·outbox 도입은 다음 구현 단계에서 수행한다.
