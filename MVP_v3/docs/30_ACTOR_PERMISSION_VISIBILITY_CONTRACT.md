# Prework Step 4 — Actor / Permission / Visibility Contract

작성일: 2026-09-15

## 1. 원칙

Actor type, Case role, permission은 분리한다. 권한은 `ActorContext + active Case membership + role + resource visibility + operation`의 결합으로 판단한다. `MVP_OPEN_PERMISSIONS`는 명시적인 은행 직원 actor의 demo 편의만 허용하며 CUSTOMER/AI/System 승격을 허용하지 않는다.

## 2. Actor / Role / Operation

- Actor type: 현재 `CUSTOMER`, `BANK_STAFF`, `BANK_AGENT`, `CUSTOMER_AGENT`, `AI_AGENT`, `SYSTEM` 계열을 정규화한다.
- Case role: `CASE_OWNER`, `REVIEWER`, `CHAT_OPERATOR`, `VIEWER`, `CUSTOMER`.
- Operation: `READ`, `WRITE`, `REVIEW`를 기본 단위로 사용하며 ACCEPT/DISMISS/COMPLETE/CANCEL은 해당 mutation 권한으로 묶는다.

## 3. Resource permission matrix

| Resource | CUSTOMER | BANK STAFF | AI/SYSTEM | 비고 |
|---|---|---|---|---|
| Case/Message | own read, allowed answer | member read/write by role | proposal only | case isolation 필수 |
| Fact/Gap | proposal 또는 공개 projection | REVIEW/WRITE by role | proposal only | confirm/reject는 직원 review |
| Verification | 공개 결과 read | create/update/complete | recommendation only | Provider ingestion은 후속 |
| Suggestion | 접근 금지 | REVIEW로 ACCEPT/DISMISS | proposal만 | ACCEPT가 Task 생성 |
| Task | 내부 task 접근 금지 | WRITE, 최종 상태는 REVIEW 경로 | 직접 mutation 금지 | customer-visible 결과만 공개 |
| Action | create/update/read 금지 | WRITE/READ by active membership | 일반 route 직접 mutation 금지 | Work Card는 draft |
| Question | 자신의 ASKED answer | review/queue/dispatch | candidate proposal | 타 고객 질문 차단 |
| Customer Progress | own confirmation request/read | 상태 update | recommendation only | 완료 직접 변경 금지 |
| Context Display | customer projection read | WRITE | 접근 금지 | BANK_INTERNAL 차단 |
| Final Report | 공개 결과만 | member read/generate | draft recommendation | 내부 자료 customer 노출 금지 |

## 4. Visibility matrix

| Resource | BANK_INTERNAL | CUSTOMER_SHARED | AI_PRIVATE | Customer 공개 조건 |
|---|---|---|---|---|
| Message | 가능 | 가능 | 가능 | audience/channel allowlist |
| Fact | 가능 | 가능 | 가능 | confirmed + shared |
| Verification | 가능 | 가능 | 가능 | completed + customer-visible |
| Task | 기본값 | 선택 | 가능 | published completed result |
| Suggestion | 기본값 | 금지 | 가능 | 자동 공개 금지 |
| Action | 기본값 | 금지 | 가능 | 자동 공개 금지 |
| Progress | 내부 상태 | 허용 결과 | 가능 | case owner/customer projection |

## 5. 적용 결과

- Context V2 routes already use `require_context_v2_member` and `ActorContext` for READ/WRITE/REVIEW.
- Suggestion ACCEPT/DISMISS review route now requires `REVIEW`.
- Legacy Action list/create/update routes now require an explicit actor and active Case membership through `require_context_v2_member`; CUSTOMER/AI/System cannot use the staff route.
- Customer Context projection remains ownership-checked and excludes internal resources.
- Customer Progress mutation remains a separate customer confirmation/status contract; it does not grant Action/Task privileges.

## 6. AI/System boundary

AI/System may create proposals through an explicit service boundary only. No general user Action/Task completion or Suggestion ACCEPT/DISMISS is granted. Provider success does not bypass General API validation.

## 7. Remaining limits / Step 5 handoff

Production session/token/OAuth authentication, service-to-service identity, and external-system identity are outside this MVP Step 4. Step 5 must define AI Runtime error contracts while preserving: proposal/draft only, General API validation, and no privileged mutation via fallback.

## 8. Final decision

`STEP_4_COMPLETE` — Actor/role/operation separation, resource matrix, visibility boundaries, Action endpoint protection, Suggestion review protection, customer ownership, and AI/System restrictions are documented and the focused Backend boundaries are applied. No migration, Frontend change, commit, or push was performed.
