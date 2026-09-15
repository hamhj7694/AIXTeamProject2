# Prework Step 3 — Canonical Work Resource Contract

작성일: 2026-09-15  
범위: 현재 구현을 기준으로 한 관계·소유권·투영 계약 확정. 런타임 코드는 변경하지 않는다.

## 조사 결과

### Legacy Action (`actions`)

- `POST /api/cases/{case_id}/actions`, `PATCH /api/cases/{case_id}/actions/{action_id}`.
- 계약은 `action_type`, `actor_type`, `note`, `status(REQUESTED/COMPLETED/CANCELLED)`, timestamps이며 title 필드는 없다.
- in-memory/MySQL `actions`에 저장되고 생성·수정 시 `BANK_ACTION_ADDED`/`CASE_CHECKLIST_UPDATED`가 `case_events`에 기록된다.
- Action Dialog가 AI Work Card(`BANK_ACTION`)를 직원 검토 후 저장한다. Timeline과 `STAFF_ACTIONS`에 표시되는 실제 조치 기록이다.

### V2 Task (`case_tasks`)

- `task_id`, `source`, optional `source_suggestion_id`, `task_type`, `title`, `description`, `priority`, `status`, evidence/result, visibility, version을 가진다.
- 직원이 직접 만들거나 Suggestion 수락으로 생성된다. 상태는 `TODO → IN_PROGRESS/BLOCKED → COMPLETED/CANCELLED`다.
- `STAFF_ACTIONS`의 진행 업무 카드가 lifecycle과 완료 결과/evidence를 관리한다. 계획 업무의 canonical resource다.

### AI Suggestion (`case_ai_suggestions`)

- `suggestion_id`, type, title, rationale, priority, evidence, status, `accepted_task_id`, model/prompt/source revision을 가진다.
- `PROPOSED → ACCEPTED/DISMISSED`. ACCEPT는 별도 Task를 생성하고 `source_suggestion_id`/`accepted_task_id`를 연결한다. Action은 만들지 않는다.
- Panel에는 `PROPOSED`만 노출되며 직원이 수락/제외한다. 자동 실행·자동 완료하지 않는다.

### AI Work Card

`POST /api/cases/{case_id}/ai/work-cards`의 추천 초안이다. `BANK_ACTION`은 직원 검토 후 Legacy Action으로 저장되고, 질문/검증 계열은 각 전용 resource 흐름으로 저장된다. Work Card 자체는 영속 canonical 업무 resource가 아니다.

## 확정 관계 모델

`# RECOMMENDED_MODEL: B — Suggestion → Task, Action은 독립 실제 조치 기록`

| 관계 | 현재 구현 및 확정 |
|---|---|
| Suggestion → Task | ACCEPT 시 기존 ID 필드로 연결하는 필수 관계 |
| Task → Action | 자동 연결하지 않음. 실제 조치 기록이 필요하면 직원이 별도 Action 생성 |
| Work Card → Action | `BANK_ACTION` 초안을 직원이 검토 후 명시적으로 저장 |
| Action → Task | 역방향/자동 변환 금지 |

별도 `relation_id`는 현재 필요 없다. Suggestion–Task는 `source_suggestion_id`와 `accepted_task_id`로 충분하다. 향후 교차 추적이 요구될 경우 nullable additive relation을 별도 검토한다.

## Canonical source table

| 의미 | canonical source | 규칙 |
|---|---|---|
| AI recommendation | 영속 `case_ai_suggestions`; Work Card는 transient | 직원 review 필수 |
| employee work | `case_tasks` | 계획·담당 업무 |
| actual action | `actions` | 실제 조치/기록 |
| work status | `case_tasks.status` | Action status는 조치 기록 lifecycle |
| completion result | Task result/evidence; Action note | 서로 덮어쓰지 않음 |
| timeline event | 현재 `case_events` + `case_context_v2_history` | 통합 Activity Event는 후속 |
| `STAFF_ACTIONS` | Action + Task + `PROPOSED` Suggestion union | stable ID/source_kind로 구분; 수락·제외 제안은 중복 표시하지 않음 |
| customer result | Customer Progress, customer-visible Verification/완료 Task, 공개 메시지 | Action/Suggestion 자동 공개 금지 |

## Lifecycle / human control

```text
Work Card(BANK_ACTION) --staff review--> Action REQUESTED --staff update--> COMPLETED/CANCELLED
AI Suggestion PROPOSED --ACCEPT--> Task TODO --start/block--> IN_PROGRESS/BLOCKED --staff complete/cancel--> COMPLETED/CANCELLED
AI Suggestion PROPOSED --DISMISS--> DISMISSED
```

AI는 추천까지만 수행한다. Task 수락, Action 생성, 상태 변경, 완료 결과 입력은 직원 mutation이다.

## Timeline / event contract

| resource | 현재 기록 | canonical future operation |
|---|---|---|
| Action | `BANK_ACTION_ADDED`, `CASE_CHECKLIST_UPDATED` in `case_events` | `ACTION.CREATED/UPDATED` |
| Task | `case_context_v2_history`, context revision | `TASK.CREATED/UPDATED/COMPLETED/CANCELLED` |
| Suggestion | `case_context_v2_history`, context revision | `SUGGESTION.CREATED/ACCEPTED/DISMISSED` |

통합 이벤트의 최소 필드는 `case_id`, `resource_type`, `resource_id`, `operation`, `actor_type`, `actor_id`, `occurred_at`, `visibility`, `source_revision`, `idempotency_key`다. 이번 단계에서는 발행 코드를 추가하지 않는다.

## ABC ownership

- **A Context**: Action/Task/Suggestion을 읽어 Panel projection으로 조합하고 stable ID·visibility를 보장한다.
- **B Conversation/Verification**: 질문·검증 및 AI Suggestion 생성/review 진입을 담당한다. 명시적 Action 저장 외에 legacy Action을 직접 생성하지 않는다.
- **C Case Operations**: Action/Task lifecycle, Work Card→Action 저장, 중앙 bundle/timeline projection을 소유한다.

## Visibility / migration / frontend

- Action과 내부 Task/Suggestion은 기본 `BANK_INTERNAL`/`INTERNAL_ONLY`다. 고객은 allowlist된 Customer Progress, customer-visible Verification, 공개 메시지와 published 완료 결과만 본다. `STAFF_ACTIONS`는 customer projection에서 제외한다.
- **DB verdict: `NO MIGRATION REQUIRED`**. 기존 테이블과 ID가 관계를 표현한다.
- **Frontend verdict: `FRONTEND_CHANGE_NOT_REQUIRED`**. 현재 Action Dialog, Suggestion review, Task card, Panel grouping, reload이 Model B와 일치한다.
- Step 2 exception은 유지한다: Action 편집 UI는 title+description을 받지만 legacy update request에는 note만 전달되어 title 변경이 저장되지 않는다. 이번 단계에서 수정하지 않는다.

## Step 4 handoff

Step 4는 resource별 operation에 ActorContext/role/visibility를 적용하고 legacy Action endpoint의 인증·권한 gap을 검증한다. AI/System은 propose만, 직원은 accept/create/update/complete를 수행한다.

## Final decision

`STEP_3_COMPLETE` — 현재 코드와 대조한 관계 모델, canonical source, lifecycle, human control, event/projection, ownership, visibility, migration/frontend impact를 문서로 확정했다. 런타임·스키마·데이터·business logic은 변경하지 않았다.
