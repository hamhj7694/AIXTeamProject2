# ActorContext 전환 최종 체크리스트 (Step 15)

작성일: 2026-09-15

## 완료된 범위

- Context Panel과 중앙 타임라인은 서버 projection과 동일한 사건 revision을 사용한다.
- 은행 mutation은 사건 멤버 역할에 따라 READ/WRITE/REVIEW 권한을 검사한다.
- 고객 projection은 `CUSTOMER_SHARE` allowlist만 반환하고, 고객 사건 멤버 검증을 수행한다.
- `ActorContext` 정규화 모듈과 권한 단위 테스트를 추가했다.
- action journal의 actor/visibility/source가 패널 투영 규칙에 반영된다.

## 세션 인증 도입 시 필수 전환

1. 인증 미들웨어에서 `ActorContext`를 생성해 request scope에 주입한다.
2. 프론트엔드의 `actor_user_id` query 파라미터를 제거하고 세션 쿠키/토큰을 사용한다.
3. `actor_type`, `role`, `updated_by` 등 클라이언트가 제출하는 권한성 필드는 무시하고 서버 context로 덮어쓴다.
4. 고객 패널 조회에 사건 소유권 또는 공유 토큰 검사를 적용한다.
5. 서비스 토큰 없이 `AI_AGENT`/`SYSTEM` mutation을 거부한다.
6. 전환 기간이 끝나면 레거시 actor 파라미터를 410 또는 명시적 deprecation 오류로 종료한다.

## 운영 전 수용 테스트

- 다른 역할의 은행 사용자가 REVIEW 작업을 수행할 수 없다.
- 고객 사용자가 은행 내부 사실·메시지·업무를 조회할 수 없다.
- 다른 사건 ID로 고객 패널을 조회할 수 없다.
- 동일 `expected_version` 충돌 시 감사 이벤트와 최신 projection이 일치한다.
- AI 제안과 직원 승인 결과의 actor/audit 정보가 구분된다.

현재 MVP에는 세션 인증 공급자가 없으므로 위 전환 항목은 보류 상태다. `MVP_OPEN_PERMISSIONS`와 레거시 query actor는 데모 호환을 위해 유지한다.

