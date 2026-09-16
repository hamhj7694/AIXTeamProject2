# Case 협업 Resource 공통 계약 초안

작성일: 2026-09-15

이 문서는 AI와 은행 직원이 동일 Case의 구조화 데이터를 함께 생성·수정·검증하기 위한 공통 계약 초안이다. 이번 단계에서는 런타임·DB·API를 변경하지 않는다.

## 공통 식별·감사 필드

모든 협업 Resource는 다음 필드를 공통적으로 가져야 한다.

| 필드 | 의미 | 규칙 |
|---|---|---|
| `id` | Resource 고유 ID | Case 범위에서 유일 |
| `case_id` | 소속 Case | 변경 불가 |
| `title` | 직원에게 표시할 제목 | Action/Task는 내용과 분리 |
| `description` 또는 `result` | 상세 내용·처리 결과 | 리소스별 명칭은 DTO에서 명확히 정의 |
| `status` | 현재 상태 | Resource별 허용 enum 사용 |
| `actor_type` | 작성 주체 종류 | AI_AGENT/BANK_STAFF/CUSTOMER/SYSTEM |
| `created_by` | 최초 작성자 | 감사 이력에 보존 |
| `updated_by` | 마지막 수정자 | 감사 이력에 보존 |
| `source` | 생성 경로 | AI_EXTRACTION, STAFF_CREATED 등 |
| `visibility` | 노출 경계 | BANK_INTERNAL, AI_PRIVATE, CUSTOMER_SHARED, PUBLIC_EVENT |
| `version` | 낙관적 잠금 버전 | 수정 요청에 expected_version 사용 |
| `evidence_refs` | 근거 연결 | 가능한 경우 message/event ID를 참조 |
| `created_at`/`updated_at` | 생성·수정 시각 | 서버 기준 UTC |

## Resource별 상태

### Fact

`PROPOSED → CONFIRMED / REJECTED / SUPERSEDED`

확정 Fact를 직접 덮어쓰지 않고 새 Fact를 생성해 정정 이력과 supersede 관계를 보존한다.

### Verification

`PENDING → IN_PROGRESS → COMPLETED` 또는 `FAILED / ON_HOLD`

완료 결과는 수정 이력으로 남기며, 삭제 대신 실패·중단·보관 상태를 사용한다.

### Task

`TODO → IN_PROGRESS → COMPLETED` 또는 `BLOCKED / CANCELLED`

완료·취소 Resource는 hard delete하지 않고 archived/history에서 조회할 수 있어야 한다.

### Action

`REQUESTED → COMPLETED / CANCELLED`

현재 `action_type + note` 구조를 `title + description/note + status`로 확장하는 것을 목표로 한다.

## Actor 규칙

- `AI_AGENT`: AI가 생성·수정한 제안 또는 자동 추출
- `BANK_STAFF`: 은행 직원의 입력·수정·확정·검토
- `CUSTOMER`: 고객 답변·고객 진행 입력
- `SYSTEM`: projection·상태 전이·감사 이벤트

AI가 생성한 값은 직원 확정 전까지 자동으로 확정 사실로 승격하지 않는다.

## Visibility 규칙

- `BANK_INTERNAL`: 은행 직원 화면만
- `AI_PRIVATE`: AI 처리 전용, 고객·직원 UI에 직접 노출하지 않음
- `CUSTOMER_SHARED`: 고객 화면에 공개된 값
- `PUBLIC_EVENT`: 고객에게 공개 가능한 변경 이벤트

서버 projection에서 allowlist를 적용하고, Frontend가 visibility를 추측하지 않는다.

## 변경·이력 규칙

모든 mutation은 다음을 보존해야 한다.

```text
resource_id
before
after
actor_type
actor_id
expected_version
result_version
reason
created_at
```

동시 수정 시 version이 일치하지 않으면 충돌을 반환하고, 먼저 저장된 변경을 덮어쓰지 않는다.

## 중앙 카드와 우측 패널 사용 규칙

- 우측 Context Panel은 최신 Resource projection을 표시한다.
- 중앙 채팅은 실제 Message와 Resource 변경 Activity Event를 시간순으로 표시한다.
- Resource 상세 전체를 중앙에 복제하지 않고 변경 요약만 이벤트 카드로 표시한다.
- 동일 `case_id + resource_type + resource_id + revision + event_type` 이벤트는 중복 표시하지 않는다.

## 확정이 필요한 결정

1. Action의 `title`과 `description` 필드명 확정
2. `actor_id`의 AI·직원 식별자 체계
3. Resource별 visibility 허용 조합
4. Activity Event 저장 테이블과 보존 기간
5. 기존 Action 데이터 backfill 정책

