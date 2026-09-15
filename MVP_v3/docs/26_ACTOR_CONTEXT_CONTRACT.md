# ActorContext 계약 초안 (Step 9)

작성일: 2026-09-15

기존 endpoint는 `actor_user_id`를 query/body로 전달하고 있어 호출자가 actor type·역할을 임의로 주장할 수 있다. 인증 도입 전까지는 호환성을 유지하되, 내부 서비스 경계에서 공통 `ActorContext`로 정규화하는 것을 목표로 한다.

## 공통 구조

```text
ActorContext {
  actor_id: string       # 인증 주체의 불변 식별자
  actor_type: BANK_STAFF | CUSTOMER | AI_AGENT | SYSTEM
  display_name?: string
  case_role?: CASE_OWNER | CHAT_OPERATOR | REVIEWER | VIEWER | CUSTOMER
  auth_source: SESSION | SERVICE_TOKEN | MVP_DEMO
  permissions: string[]  # 서버가 계산한 operation 권한
}
```

`actor_type`, `case_role`, `permissions`는 클라이언트 입력을 신뢰하지 않고 인증 주체와 사건 멤버십에서 서버가 계산한다. `MVP_OPEN_PERMISSIONS`는 `auth_source=MVP_DEMO`로만 표시한다.

## 호환 계층

1. 요청에서 세션 actor가 있으면 이를 우선한다.
2. 세션이 없는 로컬 데모에서만 기존 `actor_user_id`를 임시 actor로 변환한다.
3. 기존 `actor_type`/`updated_by` 값은 감사 로그의 참고 메타데이터로만 보존하고 권한 판정에는 사용하지 않는다.
4. 변환된 ActorContext를 `require_context_v2_member`와 모든 mutation handler에 전달한다.

## 엔드포인트 적용 원칙

- 은행 패널/리소스 조회: `READ` 필요
- 사실 확정·제외·복구, 업무 완료·취소: `REVIEW` 필요
- 사실·업무·공유 메시지 생성/편집: `WRITE` 필요
- 고객 패널: 고객 사건 소유권 또는 명시적 공유 권한 검증 후 `CUSTOMER_SHARED` projection만 반환
- AI/System mutation: 서비스 토큰과 허용된 source operation을 별도 검증하고 사람 권한으로 가장하지 않음

## 감사 필드

모든 생성·수정·상태 전이는 `actor_id`, `actor_type`, `case_role`, `auth_source`, `visibility`, `expected_version`를 감사 이벤트에 기록한다. `display_name`은 변경 가능하므로 식별자로 사용하지 않는다.

## 수용 기준

- actor type을 위조한 요청이 권한을 상승시키지 않는다.
- 은행 actor가 고객 projection을 통해 `BANK_INTERNAL` 데이터를 받지 않는다.
- 고객 actor가 다른 사건의 패널을 조회하지 못한다.
- 중앙 타임라인과 Context Panel의 이벤트에 동일한 actor/audit 메타데이터가 표시된다.
- 기존 데모 프론트엔드는 호환 계층을 통해 계속 동작한다.

이번 단계에서는 인증 미들웨어와 endpoint 시그니처를 변경하지 않았다. 다음 단계에서 `ActorContext` 생성기와 테스트를 먼저 추가한 뒤 endpoint를 점진적으로 전환한다.

