# Backend Workflow Orchestrator 설계

## 1. 정의

중앙 오케스트레이터는 LLM Agent가 아니라 일반 Backend의 결정론적 Workflow Service다. Event 종류와 현재 Case State를 기준으로 호출할 AI, 저장 순서, 후속 Event를 결정한다.

## 2. 책임

- 사용자 권한·입력·`base_version` 검증
- 목적별 Case Context Projection 생성
- AI 호출 DAG와 병렬 실행
- Timeout·Retry·Fallback·Idempotency
- AI 응답 JSON Schema 검증
- MySQL Transaction과 Entity Version 갱신
- `case_events` Append 후 Realtime Publish

## 3. 금지 책임

- 자연어 근거 없이 위험도를 자체 판단하지 않는다.
- AI 결과를 검증 없이 DB 진실값으로 저장하지 않는다.
- DB Commit 전에 Realtime Event를 발행하지 않는다.

## 4. Event → 작업 라우팅

| Trigger | 호출 작업 | 후속 저장·Event |
|---|---|---|
| `CASE_ANALYZE_REQUESTED` | Full/Window 병렬 → Feature/Risk → Report Initialize | Case/Analysis/Report, `CASE_CREATED` |
| `MESSAGE_ADDED` | Case Structure, 필요 시 Question/Report Update | Message/Feature/Section Delta |
| `QUESTION_ANSWERED` | Case Structure, Impact 계산, Report Update | Question/Progress/Section Delta |
| `VERIFICATION_UPDATED` | Verification Compare, Report Update | Evidence/Verification Section |
| `TRANSCRIPT_SEGMENT_ADDED` | Voice Delta Analysis, Impact 계산 | Feature/Question/Report Delta |
| `BANK_ACTION_ADDED` | Impact 계산, Report Update | Action/Current Actions Section |
| `RECOVERY_STARTED` | 규칙 기반 Task 생성, Recovery RAG | Mode/Progress/Guide/Report |
| `CASE_FINALIZE_REQUESTED` | 전체 이력 → FINAL Report | Immutable Revision, Closed Event |

## 5. 실행 상태

```text
PENDING → RUNNING → SUCCEEDED
                  ├─ RETRYING
                  ├─ PARTIAL_SUCCESS
                  └─ FAILED
```

필요하면 `ai_jobs` 또는 Queue를 사용하되, MVP에서 동기 요청으로 충분한 기능은 불필요하게 비동기화하지 않는다.

## 6. 멱등성·버전

- 사용자 Command는 `client_request_id`를 받는다.
- AI Job은 `case_id + trigger_event_id + task_type`으로 중복을 방지한다.
- Patch 저장 전 `base_section_version`을 검증한다.
- 충돌 시 최신 State로 한 번 재생성하고 계속 충돌하면 `409 VERSION_CONFLICT`를 반환한다.

## 7. 실패 정책

| 실패 | 처리 |
|---|---|
| 부가 질문 생성 실패 | Case 생성은 유지하고 Warning 기록 |
| 초기 핵심 분석 실패 | Case Transaction Rollback 또는 명시적 FAILED 상태 |
| Report Update 실패 | 원본 Event 저장 유지, Report Job 재시도 |
| RAG 검색 결과 없음 | `NEEDS_VERIFICATION`, 생성 근거 금지 |
| Realtime Publish 실패 | DB Event 기준 재발행 가능하게 유지 |

## 8. 완료조건

- [ ] Event별 DAG가 코드와 테스트로 정의됨
- [ ] 독립 호출 병렬 실행 테스트
- [ ] Transaction·Event 순서 테스트
- [ ] 중복 요청·Timeout·부분 실패 테스트
- [ ] AI별 Context 최소화와 민감정보 필터 적용
