# Actor·권한·Visibility 적용 기준

작성일: 2026-09-15

8단계에서는 중앙 타임라인과 우측 Context Panel이 같은 사건 데이터를 사용하되, 누가 어떤 범위에서 읽고·수정·검토할 수 있는지 기준을 고정한다. 이번 단계는 계약 기준과 GAP 기록이며, 인증 방식을 임의로 변경하지 않는다.

## Actor 분류

| Actor | 식별 방식(현재) | 책임 |
|---|---|---|
| `BANK_STAFF` | `actor_user_id` + 사건 멤버 역할 | 사건 정보 읽기/수정/검토 |
| `CUSTOMER` | 고객 세션의 `actor_user_id` | 고객 입력 및 고객에게 공개된 결과 조회 |
| `CUSTOMER_AGENT` | 고객 진행 자동화 식별자 | 고객 진행 상태 기록 |
| `AI_AGENT` | `case-copilot` 등 시스템 식별자 | AI 제안·자동 진행 생성, 사람 검토 대기 |
| `SYSTEM` | `system:*` 식별자 | 내부 동기화·마이그레이션 |

현재 action 생성 계약은 `BANK_STAFF`와 `SYSTEM`만 허용하고, 고객 진행은 별도 API에서 `CUSTOMER`/`CUSTOMER_AGENT`로 기록한다. AI가 만든 제안과 직원이 승인한 결과를 동일한 사람으로 기록하지 않도록 actor와 source를 분리해야 한다.

## 권한 매트릭스

| 작업 | CASE_OWNER | CHAT_OPERATOR | REVIEWER | VIEWER | CUSTOMER |
|---|---:|---:|---:|---:|---:|
| 은행 패널 읽기 | 허용 | 허용 | 허용 | 허용 | 거부 |
| 사실·제안·업무 생성/일반 수정 | 허용 | 허용 | 허용 | 거부 | 거부 |
| 사실 확정·제외·복구, 업무 완료·취소 | 허용 | 거부 | 허용 | 거부 | 거부 |
| 고객 공유 결과 읽기 | 허용 | 허용 | 허용 | 허용 | 공개 범위만 |
| 고객 진행 입력 | 내부 대행 시에만 | 내부 대행 시에만 | 내부 대행 시에만 | 거부 | 허용 |

서버가 최종 권한 판정을 담당한다. 프론트엔드의 버튼 숨김/비활성화는 사용성 제어일 뿐 보안 경계가 아니다. `MVP_OPEN_PERMISSIONS`는 로컬 데모 전용이며 운영 인증을 대체하지 않는다.

## Visibility 규칙

- `BANK_INTERNAL`: 은행 패널과 내부 타임라인에만 노출한다.
- `CUSTOMER_SHARED`: 확정된 사실 또는 게시된 결과만 고객 패널에 투영한다.
- 메시지는 `CUSTOMER` 공개 메시지만 고객 공유 projection에 포함한다. `BANK_INTERNAL`·`AI_PRIVATE`는 제외한다.
- 업무 결과는 `customer_visibility == RESULT_PUBLISHED`이고 상태가 `COMPLETED`일 때만 고객에게 노출한다.
- 거절/제외/대체(`REJECTED`, `SUPERSEDED`) 항목은 일반 활성 목록에서 제거하고, 은행 전용 보관 그룹에서만 보여준다.
- 민감 사실은 은행 projection에서도 마스킹 정책을 적용하며, 고객 projection에는 원문을 재사용하지 않는다.

## 현재 구현 점검

- 은행 Context Panel 조회와 Context V2 mutation은 `require_context_v2_member`의 READ/WRITE/REVIEW 역할 검사를 사용한다.
- 패널 projection은 서버에서 `view == customer`일 때 `CUSTOMER_SHARE`만 남기고, 사실·검증·업무·메시지의 공개 조건을 다시 필터링한다.
- action journal은 은행 직원 action만 `STAFF_ACTIONS`에 투영하고 고객 진행 action은 제외한다.
- 고객 패널 조회 endpoint에는 현재 은행 멤버 검사와 동등한 고객 세션 검증이 연결되어 있지 않다. 실제 인증 도입 시 고객 본인 사건 소유권/공유 토큰 검사를 추가해야 한다.
- action 응답에는 actor type/user가 있으나 AI·직원·시스템의 공통 actor schema와 권한 스냅샷이 없다. 감사 이력에는 actor id, actor type, 역할, source, visibility를 함께 보존해야 한다.

## 다음 백엔드 작업

1. 인증 주체를 요청 쿼리의 `actor_user_id`에서 세션 토큰의 `ActorContext`로 교체한다.
2. 모든 읽기/쓰기 endpoint에 사건 범위와 operation별 권한 검사를 적용한다.
3. 고객 패널 조회에 사건 소유권 또는 명시적 공유 권한 검사를 추가한다.
4. action/fact/task/verification 공통 감사 필드와 visibility 전이 규칙을 계약에 반영한다.
5. 중앙 타임라인과 패널 projection이 동일한 event id·revision을 반환하도록 동기화한다.

