# Frontend Freeze Contract

작성일: 2026-09-15
상태: Step 2 확정 기준선

이 문서는 현재 `MVP_v3/frontend` 구현을 Backend/AI가 맞춰야 하는 기준으로 고정한다. 이 단계에서는 Frontend, Backend business logic, AI, DB migration을 변경하지 않는다.

## 1. Freeze 범위

Freeze 대상은 현재 Frontend가 실제로 사용하는 다음 계약이다.

- Case Room bundle과 5초 polling/reload 동작
- Context Panel V3 7개 Section과 item/group schema
- Fact 상태·근거·visibility·version
- Verification workflow 표시 계약
- Customer Question 후보·queue·answer 계약
- Customer Progress 5단계와 상태
- legacy Action, V2 Task, AI Suggestion의 현재 표시 방식
- Customer/Bank visibility 경계
- resource version과 case `context_revision`의 분리
- mutation 성공 후 canonical 응답 재조회 규칙

이 문서는 canonical resource를 새로 결정하지 않는다. Action/Task/Suggestion 관계는 Step 3의 결정사항이다.

## 2. Context Panel 7 Section Contract

Frontend는 `ContextPanelV3`에서 다음 Section ID를 정확히 사용한다.

| Section | `section_id` | Frontend Component | 허용 Resource | 주요 필드 | visibility | mutation |
|---|---|---|---|---|---|---|
| 현재 사건 요약 | `SUMMARY` | `SummarySection` | Case metadata, deterministic projection, staff display override | `display_value`, `source_kind`, `projection_status`, `source_revision` | 은행 표시용 | 직원 summary override/reset |
| 피해·노출 | `EXPOSURE` | `ExposureSection` | V2 Fact, archived Fact | `semantic_key`, value/display, status, confidence, evidence | 기본 `BANK_INTERNAL`; 확정 후 공유 가능 | Fact create/review/correct |
| 사칭·접촉 정보 | `IMPERSONATION_CONTACT` | `ImpersonationSection` | V2 Fact, archived Fact | 기관·인물·계좌·연락처 | 내부 기본, 민감정보 마스킹 | Fact create/review/correct |
| 사기 정황 | `FRAUD_CIRCUMSTANCES` | `FraudCircumstanceSection` | V2 Fact | `claims`, `demands`, `tactics` groups | 내부 기본, 공유는 별도 확정 | Fact create/review/correct |
| 사실·확인 현황 | `FACT_VERIFICATION` | `FactVerificationSection` | Gap, Verification | `needs_attention`, `in_progress`, `confirmed`, `failed` | 내부 기본; 완료·공개 결과만 공유 | Fact/Gap/Verification mutation |
| 담당자 조치 및 결과 | `STAFF_ACTIONS` | `StaffActionSection` | legacy Action, V2 Task, AI Suggestion | `active`, `completed`, `suggestions`, `item_id`, status | Action/Task는 `BANK_INTERNAL` 기본 | Task/Action/Suggestion workflow |
| 고객 공유 결과 | `CUSTOMER_SHARE` | `CustomerShareSection`, `CustomerProgressEditor` | `CUSTOMER_SHARED` Fact, 공개 Verification/Task, Progress, 공개 Message | 공개 결과·진행 상태·다음 할 일 | 고객 공개 allowlist | Progress update/confirmation |

Backend response는 항상 7개 Section을 반환한다. Frontend는 누락 Section을 빈 Section으로 정규화하지만 Backend는 누락시키지 않는다.

## 3. Fact Contract

Context Panel item 기준 계약:

```text
item_id: string
semantic_key: string
label: string
display_value: string
value: Record<string, unknown>
source_kind: string
status: string
confidence?: number | null
evidence_refs: { type, id, revision? }[]
visibility: BANK_INTERNAL | CUSTOMER_SHARED
masked: boolean
version: number
```

Fact 상태는 다음 의미로 고정한다.

| 상태 | Frontend 표현 | 의미 |
|---|---|---|
| `PROPOSED` | 확인 필요 | AI·고객·직원 입력. 직원 review 전 |
| `CONFIRMED` | 확정 | 직원/검토자가 확인한 canonical Fact |
| `REJECTED` | 검토에서 제외된 정보 | 삭제하지 않고 archived history에 보존 |
| `SUPERSEDED` | 새 정보로 대체된 기록 | 기존 Fact를 덮어쓰지 않고 대체 관계 보존 |

Freeze 원칙:

- `PROPOSED`와 `CONFIRMED`는 서로 다른 상태다.
- AI가 자동으로 `CONFIRMED`를 만들지 않는다.
- 확정 Fact 정정은 기존 Fact overwrite가 아니라 새 제안과 supersede 흐름이다.
- hard delete를 화면 계약으로 사용하지 않는다.
- Fact review에는 `expected_version`이 필요하며 충돌은 `409`다.
- Frontend는 `source_kind`, `evidence_refs`, confidence를 표시하되 내부 UUID·revision을 일반 문구로 노출한다.

## 4. Semantic Key → Section Mapping

현재 Backend allowlist와 Frontend 입력 옵션을 기준으로 하는 전체 mapping이다.

| `semantic_key` | Section | Group | Frontend label | Customer 공개 | Source 유형 |
|---|---|---|---|---|---|
| `transfer.actual.status` | EXPOSURE | item | 실제 이체 여부 | 확정·공유 시 | AI/고객/직원 |
| `transfer.requested.amount` | EXPOSURE | item | 요구 금액 | 확정·공유 시 | AI/고객/직원 |
| `transfer.actual.amount` | EXPOSURE | item | 실제 이체 금액 | 확정·공유 시 | AI/고객/직원 |
| `exposure.personal_information` | EXPOSURE | item | 개인정보 노출 | 확정·공유 시 | AI/고객/직원 |
| `exposure.account_information` | EXPOSURE | item | 계좌정보 노출 | 확정·공유 시 | AI/고객/직원 |
| `exposure.authentication_information` | EXPOSURE | item | OTP·인증정보 노출 | 확정·공유 시 | AI/고객/직원 |
| `exposure.identity_or_card` | EXPOSURE | item | 신분증·카드정보 노출 | 확정·공유 시 | AI/고객/직원 |
| `exposure.occurred_at` | EXPOSURE | item | 노출 시점 | 확정·공유 시 | AI/고객/직원 |
| `device.remote_control_app` | EXPOSURE | item | 원격제어 앱 | 확정·공유 시 | AI/고객/직원 |
| `offender.claimed_organization` | IMPERSONATION_CONTACT | item | 사칭 기관 | 확정·공유 시 | AI/고객/직원 |
| `offender.claimed_person_or_role` | IMPERSONATION_CONTACT | item | 사칭 인물·역할 | 확정·공유 시 | AI/고객/직원 |
| `offender.requested_account` | IMPERSONATION_CONTACT | item | 요구 계좌 | 기본 비공개·마스킹 | AI/고객/직원 |
| `offender.contact` | IMPERSONATION_CONTACT | item | 상대방 연락처 | 기본 비공개·마스킹 | AI/고객/직원 |
| `offender.incident_claim` | FRAUD_CIRCUMSTANCES | `claims` | 상대방 주장 | 확정·공유 시 | AI/고객/직원 |
| `circumstance.demand` | FRAUD_CIRCUMSTANCES | `demands` | 상대방 요구 | 확정·공유 시 | AI/고객/직원 |
| `circumstance.tactic` | FRAUD_CIRCUMSTANCES | `tactics` | 압박·조작 수법 | 확정·공유 시 | AI/고객/직원 |

다음 표현은 현재 별도 semantic key가 아니다. 이번 단계에서 새 key를 만들지 않으며, 기존 claim/demand/tactic Fact 또는 진단 context로만 표현된다.

`기관·권위 사칭`, `범죄 연루`, `인증번호 요구`, `가족 고립`, `안전계좌 명목`, `시간 압박`, `불이익 협박`, `통화 유지 강요`, `즉시 행동 명령`은 현재 **MISSING CONTRACT GAP**이다. v3.1 hierarchical feature 계약에서 별도 결정한다.

## 5. Verification Contract

| 필드 | Frontend 계약 |
|---|---|
| ID | `verification_task_id` |
| 대상 | `target` |
| 주장 | `claim` |
| 방법 | `method`는 Panel value에 보조적으로 표시되며 생성 request에는 없음 |
| 상태 | `PENDING`, `IN_PROGRESS`, `COMPLETED`, `ON_HOLD`, `FAILED` |
| 결과 | `result_summary` |
| 출처 | `evidence_url`, `rag_source` |
| 담당자 | `verified_by` |
| 공개 | `customer_visible=true`이고 `COMPLETED`일 때만 고객 projection |
| 동시성 | `version` + `expected_version`, 충돌 409 |

완료는 “공식 확인 결과가 직원에 의해 기록됨”을 뜻한다. 실제 외부 금융·수사기관 업무 완료를 뜻하지 않는다.

현재 구현 상태와 계약을 분리한다.

- Verification Workflow: 구현됨
- Verification AI Recommendation: Work Card 버튼을 통한 부분 구현
- Verification RAG: 미구현
- Official Provider: unavailable stub
- Human/manual verification: 구현됨

## 6. Customer Question Contract

후보/대기열/답변의 기본 필드:

```text
question_id
case_id
target_field
question_text
reason
priority: P0 | P1 | P2
options: string[]
option_items: { option_id, label }[]
answer_mode: SINGLE_CHOICE | TEXT | CHOICE_OR_TEXT
allow_free_text
allow_multi_select
status: PENDING | ASKED | ANSWERED | SKIPPED
question_version
selected_option_ids[]
free_text
answer_payload
answer_text (compatibility)
```

Freeze 규칙:

- 선택지와 직접입력을 동시에 허용할 수 있다.
- `selected_option_ids[]`와 `free_text`가 canonical structured answer다.
- `answer_text`는 legacy compatibility 필드다.
- 여러 질문을 queue해도 고객에게는 한 번에 하나씩 dispatch한다.
- `PENDING → ASKED → ANSWERED` 흐름을 사용한다.
- 이미 등록·발송·답변됐거나 같은 target/text인 질문은 Backend가 중복 제거한다.
- Frontend는 candidate가 deterministic인지 AI인지 별도 표시 필드를 요구하지 않는다. 임의 source 필드를 추가하지 않는다.
- 최초 후보 목록은 deterministic/hybrid route 결과이며, “AI 질문 추천” 버튼은 별도 Work Card 호출이다.

## 7. Customer Progress Contract

Progress step은 정확히 다음 5개다.

`SAFETY`, `EVIDENCE`, `PAYMENT_HOLD`, `REPORT`, `RELIEF`

Progress status:

`UNKNOWN`, `IN_PROGRESS`, `SUBMITTED`, `COMPLETED`, `NOT_APPLICABLE`

| 상태 | 의미 |
|---|---|
| `UNKNOWN` | 확인되지 않음 |
| `IN_PROGRESS` | 담당자 확인·처리 중 |
| `SUBMITTED` | 제출/접수 확인 후 결과 대기 |
| `COMPLETED` | 담당자 완료 확인. 완료 근거와 시각 필요 |
| `NOT_APPLICABLE` | 해당 없음. 완료와 다른 의미 |

추가 계약:

- `SUBMITTED != COMPLETED`
- `NOT_APPLICABLE != COMPLETED`
- `COMPLETED`와 `SUBMITTED`에는 `reference`와 `confirmed_at`이 필요하다.
- `confirmation_requested=true`인 단계에는 중복 확인 요청을 만들지 않는다.
- `COMPLETED`/`NOT_APPLICABLE` 단계에는 새로운 확인 요청 버튼을 표시하지 않는다.
- 저장 결과는 고객에게 공개되고 Customer Agent context에도 사용된다.

## 8. Action / Task / Suggestion 현재 계약

### legacy Action

Frontend는 다음을 사용한다.

```text
action_id
case_id
action_type
status
actor_type
note
created_at
updated_at?
updated_by?
```

생성은 `POST /api/cases/{case_id}/actions`, 수정은 `PATCH /api/cases/{case_id}/actions/{action_id}`다. 중앙 Timeline과 Context Panel `ACTION_RECORD.item_id`는 같은 `action_id`를 사용한다. 기본 visibility는 `BANK_INTERNAL`이다.

### V2 Task

Context Panel의 `STAFF_ACTIONS.active/completed`에 `task_id`, title, description/result, status, priority, evidence, version으로 표시된다. `TODO`, `IN_PROGRESS`, `BLOCKED`, `COMPLETED`, `CANCELLED`를 사용한다.

### AI Suggestion

`case_ai_suggestions`의 `suggestion_id`, title, rationale, priority, status, evidence, version으로 표시한다. `PROPOSED`만 AI 제안 lane에 표시하며 채택/제외는 직원 workflow다.

이 세 리소스는 현재 Frontend에서 모두 STAFF_ACTIONS 아래 표현되지만, 이번 문서에서는 동일 resource라고 정의하지 않는다.

## 9. Customer / Bank Visibility Contract

| Resource | Bank | Customer | 조건 |
|---|---|---|---|
| BANK_INTERNAL Fact | 허용 | 금지 | 직원 projection only |
| CUSTOMER_SHARED Fact | 허용 | 허용 | CONFIRMED + allowlist |
| legacy Action | 허용 | 금지 | 직원 Action, Panel/TL 내부 |
| V2 Task | 허용 | 결과만 | COMPLETED + RESULT_PUBLISHED |
| AI Suggestion | 허용 | 금지 | 직원 review 전용 |
| Verification | 허용 | 결과만 | COMPLETED + customer_visible |
| Customer Progress | 허용 | 허용 | 공개 진행 상태 |
| Message CUSTOMER | 허용 | 허용 | 공개 message만 |
| Message BANK_INTERNAL | 허용 | 금지 | 내부 대화 |
| Message AI_PRIVATE | 제한적 | 금지 | AI 내부 context |
| Personal Note | 작성자 은행 직원 | 금지 | PRIVATE_TO_AUTHOR |

고객은 자기 Case의 active CUSTOMER member여야 한다. Bank actor는 허용된 사건 member role 또는 로컬 데모 권한이어야 한다. AI/System은 Frontend 사용자 actor가 아니며 canonical DB를 직접 수정하지 않는다.

## 10. Version / Revision Contract

| 이름 | Resource | 용도 | Frontend 전송 | 충돌 처리 |
|---|---|---|---|---|
| `version` | Fact/Gap/Suggestion/Task/Verification | resource optimistic lock | `expected_version` | 409 + 최신 재조회 |
| `question_version` | Customer Question | 질문 내용과 답변 버전 일치 | answer request | stale answer 거부 |
| `context_revision` | Case Context | V2 resource/projection 변경 기준 | 직접 수정하지 않음 | Panel reload/polling |
| display `item_version` | Summary display override | 직원 표시 문구 변경 | `expected_version` | 409/최신 재조회 |
| progress `revision` | Customer Progress step | step snapshot 동시성 | `expected_revision` | 충돌 후 재조회 |
| `report_version` | Final Report | 보고서 revision | finalize request의 case version과 별도 | Case conflict |
| bundle `cursor` | Case events | 중앙 Timeline 최신 위치 | 조회 결과로 보존 | 다음 bundle reload |

서로 다른 version/revision을 하나의 값으로 합치지 않는다.

## 11. Mutation → Reload / Sync Contract

| Mutation | 원본 API | 성공 후 Frontend 갱신 |
|---|---|---|
| Message POST | `/messages` | bundle reload; extraction은 비동기 후 Context revision 변화 |
| Bank AI invocation | `/ai/invocations` | AI message 임시 표시 후 bundle reload |
| Fact create/review | `/context-v2/facts` | Context Panel 자체 reload |
| Gap update | `/context-v2/gaps` | Context Panel reload |
| Suggestion review | `/context-v2/suggestions/.../review` | Context Panel reload |
| Task update/complete/cancel | `/context-v2/tasks` | Context Panel reload |
| Verification create/update | `/verifications` | Case bundle reload + Context reload |
| legacy Action create/update | `/actions` | bundle reload + Panel polling/reload |
| Question queue | `/customer-questions` | bundle reload, 다음 질문은 순차 dispatch |
| Question answer | `/customer-questions/{id}/answer` | 답변 저장·다음 dispatch·bundle reload |
| Customer Progress | `/customer-progress/{step}` | progress state 반영 후 bundle reload |
| Summary display | `/context-display/SUMMARY` | Context display 재조회 |

Case Room은 5초마다 bundle을 polling한다. Context Panel은 `accessRevision`, bundle cursor, Case `context_revision` 변경에 반응해 다시 읽는다. 이 단계에서는 SSE/WebSocket으로 변경하지 않는다.

## 12. Backend / AI Contract Gap

| 기능 | 상태 | Gap | 후속 단계 |
|---|---|---|---|
| 최초 Case → Context population | BACKEND GAP | seed가 transfer status/claim/demand/tactic 일부만 V2 Fact로 bridge | Step 3 이후 Context intelligence |
| CHAT → Fact | AI GAP | route/job은 있으나 현재 extractor가 제한적 deterministic | Context extraction 단계 |
| Fact review | MATCH | 상태·version·supersede 계약 일치 | 유지 |
| Verification workflow | MATCH | CRUD·결과·공개 조건 일치 | 유지 |
| Verification AI | AI GAP | 명시적 Work Card 추천만 존재 | Conversation intelligence |
| Verification RAG/Official provider | BACKEND GAP | provider/corpus가 unavailable stub | 별도 Future |
| 고객 질문 후보 | PARTIAL MATCH | 기본 후보 deterministic/hybrid, AI source를 Frontend는 표시하지 않음 | Question 단계 |
| 고객 질문 answer | MATCH | structured answer와 compatibility answer_text 지원 | 유지 |
| legacy Action | PARTIAL MATCH | id/visibility/projection은 일치, title 필드는 없음 | Step 3 결정 |
| V2 Task | MATCH | Panel task UI와 V2 route 일치 | Step 3 relation 결정 |
| AI Suggestion | MATCH | PROPOSED review lane과 route 일치 | Step 3 relation 결정 |
| Customer Progress | MATCH | 5 step/status/revision/public 조건 일치 | 유지 |
| Summary | PARTIAL MATCH | 현재 deterministic projection + 직원 override, 최신 전체 LLM summary 아님 | 후속 Summary 단계 |
| Customer Agent | PARTIAL MATCH | endpoint/context/visibility는 일치, provider fallback 없음 | AI runtime 후속 |
| Bank Agent | PARTIAL MATCH | endpoint/context/visibility는 일치, provider fallback 없음 | AI runtime 후속 |
| Final Report | PARTIAL MATCH | response 계약은 일치, 실제 provider 의존 | 후속 Report 단계 |

## 13. Frontend Freeze Exceptions

### `FRONTEND_FREEZE_EXCEPTION`: Action title

현재 `ContextPanelV3`의 업무 수정 UI는 title과 description을 모두 편집한다. 그러나 `ACTION_RECORD` 저장 시 `casesApi.updateAction()`에는 `note`만 전달되고 title 필드는 API 계약에도 없다. 따라서 Action title 수정은 저장되지 않는다.

이번 단계에서는 수정하지 않는다. 이후 선택지는 다음 둘 중 하나다.

- 작은 Frontend 변경으로 title 전달 계약을 추가
- title 편집을 지원하지 않는 것으로 명시하고 UI를 제한

이 항목이 현재 확인된 유일한 명확한 Frontend freeze exception이다.

## 14. Step 3에서 결정할 항목

- legacy Action을 유지할지 V2 Task와 어떤 관계로 둘지
- Action과 Task의 동일 업무 여부 및 relation 필드
- AI Suggestion 채택 후 Task/Action 생성 규칙
- Action title/content/note의 최종 표현
- 중앙 Timeline과 Panel에서 Action/Task를 중복 표시할지 여부
- resource별 revision/event/audit 필드 통합 범위
- 고객에게 공개 가능한 업무 결과의 canonical resource

## 15. 조사 근거

- Frontend API: `frontend/src/api/cases.ts`, `frontend/src/api/types.ts`
- Context API/types: `frontend/src/context-v3/api.ts`, `frontend/src/context-v3/types.ts`
- Panel: `frontend/src/context-v3/ContextPanelV3.tsx`, `sections.tsx`, `components.tsx`
- Case flow: `frontend/src/pages/CaseRoomPage.tsx`
- Question/Verification/Action UI: `frontend/src/components/CaseActionDialogs.tsx`
- Progress: `frontend/src/components/CustomerProgressEditor.tsx`
- Timeline: `frontend/src/components/SharedConversation.tsx`, `frontend/src/timeline.ts`
- Backend contracts: `backend/contracts/public_api/case_context_v2.py`, `case_workflow.py`, `customer_progress.py`
- Projection: `backend/general_api/app/domains/cases/context_v3/panel.py`
- Context routes: `backend/general_api/app/main.py`
- Existing related documents: `docs/19~27`

