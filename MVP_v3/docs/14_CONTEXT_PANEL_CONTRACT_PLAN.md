# MVP_v3 7개 맥락 패널 최종 계약 및 구현 계획

상태: **팀 승인 대기 / 기능 구현 전 계약안**  
작성일: 2026-09-14  
근거: 실제 실행 코드, DB schema/migration, Public/AI Pydantic contract, Frontend, 테스트, `09_CASE_CONTEXT_DATA_CONTRACT.md`, `13_CONTEXT_PANEL_DATA_AUDIT.md`

> 이 문서는 7개 UI Section의 최종 데이터 계약과 구현 순서를 고정하기 위한 문서다. 이번 단계에서는 실제 기능 코드, Frontend, Backend, AI Prompt, DB Schema를 변경하거나 migration을 실행하지 않는다.

## 1. 결정 요약

### 1.1 확정안

1. 은행 화면은 정확히 다음 7개 Section만 사용한다.
   1. 현재 사건 요약
   2. 피해·노출
   3. 사칭·접촉 정보
   4. 사기 정황
   5. 사실·확인 현황
   6. 담당자 조치 및 결과
   7. 고객 공유 결과
2. UI Section과 DB table을 1:1로 만들지 않는다.
3. canonical Fact는 장기적으로 Context v2 `case_context_facts_v2`가 담당한다.
4. Gap, Verification, Task, Decision은 각자의 기존 저장소와 상태를 유지한다.
5. 일반 직원 업무의 장기 canonical store는 Context v2 `case_tasks`다. legacy `actions`는 Case control, Customer Progress event 및 기존 데이터 호환에 유지한다.
6. 현재 사건 요약과 고객 공유 결과는 canonical 저장소가 아니라 서버가 만드는 derived projection이다.
7. AI·고객 입력은 기본적으로 `PROPOSED`이며 자동 `CONFIRMED`되지 않는다.
8. 동일 semantic key의 충돌값은 overwrite하지 않고 새 후보로 저장한다. 권한 있는 직원이 confirm/reject/supersede한다.
9. 원문 고객/직원 메시지를 먼저 DB에 저장한 뒤 비동기로 Fact 후보를 추출한다. AI 생성 메시지는 자동 Fact evidence로 사용하지 않는다.
10. 고객 질문 답변은 `selected_option_ids[]`와 `free_text`를 동시에 받을 수 있는 구조화 payload로 확장한다. 기존 `answer_text`는 호환 표시 snapshot으로 유지하되 canonical 답변으로 사용하지 않는다.
11. 고객 공개는 Frontend 숨김이 아니라 General API의 customer projection에서 완료·공개 승인 조건을 강제한다.
12. 기존 화면·API·table은 새 projection과 호환 adapter가 검증되기 전 삭제하지 않는다.

### 1.2 실제 코드 재확인 결과

| 확인 항목 | 실제 코드 상태 | 계약에 미치는 영향 |
|---|---|---|
| Case Support 입력 | diagnosis, questions, facts, verifications, actions를 읽고 messages는 읽지 않음 | 메시지→Fact 연결이 필요 |
| 메시지 저장 순서 | 고객/직원 메시지 commit 후 별도 AI invocation | 이 순서를 보존 |
| 고객 질문 답변 | `raw_answer: string`, `answer_text`, 단일 선택 또는 직접입력 | API/DB/UI 계약 확장 필요 |
| Fact | legacy Fact와 Context v2 Fact 공존 | v2 authoritative + legacy read adapter |
| 직원 표시 편집 | `case_context_items.state_json`의 `staff_text`가 AI 표시값보다 우선 | stale override metadata 필요 |
| Summary | Case snapshot adapter의 규칙 기반 문자열; projection cache 존재 | derived view + cache 유지 |
| AI Suggestion | v2 저장소 존재, 현재 production 생성은 제한적 | 추천 workflow 내부 유지, 독립 UI 제거 가능 |
| Task/Action | v2 Task와 legacy Action 공존 | 신규 일반 업무는 Task, 기존 Action 호환 유지 |
| Verification | 별도 table/status/result/customer flag | 별도 authoritative store 유지 |
| 기관 검색 | Case-local lexical RAG만 존재; 공식기관 corpus/Web/API 없음 | 구현 범위를 명시적으로 분리 |
| 고객 공개 | customer message, completed+customer_visible verification, progress 중심 | 서버 projection 강화 필요 |
| 권한 | Context v2 역할 검사 존재하나 MVP_OPEN 및 고정 사용자 사용 가능 | 계약은 서버 강제, 실제 인증은 별도 과제 |

## 2. 7개 Section 최종 계약

| Section | 책임 | 입력 | 출력 | 쓰기 방식 | canonical 여부 |
|---|---|---|---|---|---|
| 현재 사건 요약 | 지금 사건을 3~5개 핵심 bullet로 파악 | 유효 Fact, exposure, impersonation, circumstance, verification, task/action | summary bullets, revision, generation status | 표시 override만 허용 | derived view |
| 피해·노출 | 고객이 실제로 겪거나 제공한 정보 | exposure/transfer/device Fact | typed Fact items | Fact 후보 작성→검토 | canonical Fact |
| 사칭·접촉 정보 | 상대방이 내세운 신원과 접촉 수단 | organization/person/account/contact Fact | typed Fact items | Fact 후보 작성→검토 | canonical Fact |
| 사기 정황 | 주장·요구·압박을 혼동 없이 구분 | diagnosis signal과 message-derived Fact | CLAIM/DEMAND/TACTIC items | Fact 후보 작성→검토 | canonical Fact 기반 view |
| 사실·확인 현황 | 확인 필요→진행→확인됨을 한곳에 표시 | Fact, Gap, Verification | 단순 UI 상태 + 내부 resource/status/ref | 자원별 기존 API | aggregate view |
| 담당자 조치 및 결과 | AI 추천과 실제 직원 업무/결과 구분 | Suggestion, Task, legacy Action, Decision, Verification work | active/archived task, result, evidence, decision | 직원 채택/작성/완료 | Task 중심 aggregate |
| 고객 공유 결과 | 공개 승인된 결과만 고객/은행에 동일하게 보여줌 | published task result, public verification, progress, customer message | customer-safe items | 별도 공개 승인 | derived customer projection |

### 2.1 Section 불변식

- `DEMAND`는 상대방이 요구한 행동이고, `EXPOSURE`는 고객이 실제로 한 행동이다.
- `transfer.requested.amount`와 `transfer.actual.amount`는 절대 합치지 않는다.
- Summary는 다른 Section의 근거가 될 수 없다.
- AI Suggestion은 Task/Action이나 완료 결과가 아니다.
- 고객 공유 결과는 은행 내부 원본을 그대로 전달하지 않고 공개 가능한 필드만 다시 투영한다.
- 화면의 “확인됨”은 반드시 confirmed Fact 또는 직원이 완료 처리한 Verification에 근거한다.

## 3. Canonical field와 semantic key

### 3.1 값 표현 공통 규칙

- `semantic_key`는 의미 식별자이며 표시 문구가 아니다.
- typed value는 `value_json`, 사용자 표시는 `display_value`에 둔다.
- `display_value` 수정만으로 canonical value가 바뀌지 않는다.
- scalar key는 한 시점에 active confirmed Fact가 최대 하나다.
- multi key는 서로 다른 항목이 동시에 confirmed일 수 있다.
- 알 수 없는 값은 임의 문자열 `UNKNOWN`을 Fact로 만들기보다 Gap으로 표현한다. 기존 Case compatibility field가 `UNKNOWN`을 요구하는 경우에만 adapter에서 변환한다.

### 3.2 최종 semantic key 표

| Semantic Key | Section | Cardinality / Type | Allowed value 핵심 | Existing Mapping | Writer | Reviewer | Visibility | Migration | Notes |
|---|---|---|---|---|---|---|---|---|---|
| `transfer.actual.status` | 피해·노출 | scalar enum | `TRANSFERRED`, `NOT_TRANSFERRED` | `transfer_status`, `victim_transfer_status YES/NO` | AI/customer/staff/bank | owner/reviewer | 기본 internal | 없음 | 기존 key 재사용 |
| `transfer.requested.amount` | 피해·노출 | multi money object | `{amount_krw:int, currency:"KRW"}` | diagnosis `requested_amount_max`, event amount | AI/staff | owner/reviewer | internal | 없음 | 요청액이며 피해액 아님 |
| `transfer.actual.amount` | 피해·노출 | scalar money object | `{amount_krw:int, currency:"KRW"}` | `actual_loss_amount_krw` | customer/staff/bank | owner/reviewer | 승인 시 shared | 없음 | Case field에 compatibility projection |
| `transfer.purpose` | 사기 정황/DEMAND | multi text/code | `{text, code?}` | `transfer_purpose` | AI/customer/staff | owner/reviewer | internal | 없음 | 기존 key 재사용 |
| `exposure.personal_information` | 피해·노출 | scalar enum | `EXPOSED`, `PARTIALLY_EXPOSED`, `NOT_EXPOSED` | `personal_information_exposure` | AI/customer/staff | owner/reviewer | 승인 시 shared | 없음 | 기존 key 재사용 |
| `exposure.account_information` | 피해·노출 | scalar enum+types | `{status, types[]}` | 민감정보 generic field뿐 | AI/customer/staff | owner/reviewer | internal | 없음 | 신규 key, table 변경 불필요 |
| `exposure.authentication_information` | 피해·노출 | scalar enum+types | `{status, types:[PASSWORD,OTP,AUTH_CODE,...]}` | `authentication_information_exposure` | AI/customer/staff | owner/reviewer | internal | 없음 | 기존 key 재사용 |
| `exposure.identity_or_card` | 피해·노출 | scalar enum+types | `{status, types:[ID_DOCUMENT,CARD_INFORMATION]}` | 전용 field 없음 | AI/customer/staff | owner/reviewer | internal | 없음 | 신규 key |
| `device.remote_control_app` | 피해·노출 | scalar object | `{status:INSTALLED/NOT_INSTALLED, app_name?}` | `remote_control_app` | AI/customer/staff | owner/reviewer | internal | 없음 | 기존 key 재사용 |
| `exposure.occurred_at` | 피해·노출 | scalar datetime/range | `{occurred_at?, from?, to?, precision}` | message/evidence time뿐 | customer/staff | owner/reviewer | internal | 없음 | 신규 key; 추정 시 PROPOSED |
| `offender.claimed_organization` | 사칭·접촉 | multi object | `{name, organization_type?}` | `claimed_organization`, diagnosis role code | AI/customer/staff | owner/reviewer | internal | 없음 | 기존 key 재사용 |
| `offender.claimed_person_or_role` | 사칭·접촉 | multi object | `{name?, role_or_title}` | diagnosis subtype/group/claim text | AI/customer/staff | owner/reviewer | internal | 없음 | 신규 key |
| `offender.requested_account` | 사칭·접촉 | multi object | `{bank_name?, account_ref, holder_name?}` | `requested_account` label/adapter 흔적 | AI/customer/staff | owner/reviewer | internal | 없음 | 신규 key; 민감 표시 마스킹 |
| `offender.contact` | 사칭·접촉 | multi object | `{type:PHONE/MESSENGER/EMAIL/OTHER, value}` | `caller_phone` label 흔적 | AI/customer/staff | owner/reviewer | internal | 없음 | 신규 key; 고객 공개 기본 금지 |
| `offender.incident_claim` | 사기 정황/CLAIM | multi object | `{text, claim_code?}` | `incident_claim`, diagnosis claims | AI/customer/staff | owner/reviewer | internal | 없음 | 기존 key 재사용, 다중 허용 |
| `circumstance.demand` | 사기 정황/DEMAND | multi object | `{text, action_code?}` | diagnosis demands/requested action codes | AI/customer/staff | owner/reviewer | internal | 없음 | 신규 key; exposure와 분리 |
| `circumstance.tactic` | 사기 정황/TACTIC | multi object | `{text, tactic_code?}` | manipulation tactics/codes | AI/customer/staff | owner/reviewer | internal | 없음 | 신규 key |

### 3.3 Backward compatibility mapping

| Legacy/current field | Canonical key | Read rule | Write rule |
|---|---|---|---|
| `victim_transfer_status` | `transfer.actual.status` | v2 confirmed 우선, 없으면 Case field | v2 confirm 후 compatibility Case field 갱신 |
| `actual_loss_amount_krw` | `transfer.actual.amount` | v2 confirmed 우선, 없으면 Case field | v2 confirm 후 compatibility Case field 갱신 |
| `transfer_status` | `transfer.actual.status` | alias normalize | 신규 write 금지, v2로 작성 |
| `personal_information_exposure` | `exposure.personal_information` | 기존 workspace mapping 유지 | v2로 작성 |
| `authentication_information_exposure` | `exposure.authentication_information` | 기존 mapping 유지 | v2로 작성 |
| `remote_control_app` | `device.remote_control_app` | 기존 mapping 유지 | v2로 작성 |
| `claimed_organization` | `offender.claimed_organization` | 기존 mapping 유지 | v2로 작성 |
| `incident_claim` | `offender.incident_claim` | 기존 mapping 유지 | v2로 작성 |
| diagnosis arrays | claim/demand/tactic key | 최초 Case에서 proposed projection | 원 diagnosis 불변; v2 proposal만 추가 |

기존 row를 일괄 rewrite하지 않는다. Adapter가 읽고, 새 write부터 v2에 저장한다.

## 4. Source 계약

Context v2의 기존 `FactSource`를 그대로 사용한다.

| Source | 의미 | 기본 Status | 누가 생성 | 자동 Confirm |
|---|---|---|---|---|
| `AI_EXTRACTION` | AI가 입력에서 추출한 후보 | `PROPOSED` | General API가 AI proposal 검증 후 | 금지 |
| `CUSTOMER_STATEMENT` | 고객 원문/질문 답변에서 나온 진술 | `PROPOSED` | General API | 금지 |
| `STAFF_OBSERVATION` | 직원이 관찰·기록한 내용 | `PROPOSED` | 직원 | 금지; reviewer 별도 |
| `BANK_RECORD` | 은행 내부 공식 record에 근거 | `PROPOSED` 기본 | 직원/향후 trusted integration | MVP 자동 확정 금지 |
| `OFFICIAL_VERIFICATION` | 기관 확인 결과에 근거 | `PROPOSED` 기본 | Verification 완료 후 General API | 직원 검토 후 confirm |

### 4.1 legacy source mapping

| Legacy source | v2 source | Status 처리 |
|---|---|---|
| `AI_EXTRACTED` | `AI_EXTRACTION` 또는 근거가 고객 답변이면 `CUSTOMER_STATEMENT` | legacy status 보존 |
| `HUMAN_CONFIRMED` | provenance 확인 시 `STAFF_OBSERVATION` | confirmed actor/time가 있으면 confirmed view |
| `VERIFIED` | `OFFICIAL_VERIFICATION` | verification ref가 있어야 confirmed 후보 |
| `UNRESOLVED` | Fact source로 변환하지 않음 | Gap으로 read projection |

Source는 provenance이고 Status는 검토 상태다. Source가 높아도 MVP에서는 자동 confirm하지 않는다.

## 5. Status 계약과 UI projection

새 통합 enum을 만들지 않는다. 각 resource의 내부 상태를 유지하고 General API가 UI 상태를 계산한다.

| Resource | Internal Status | UI Status | 의미 |
|---|---|---|---|
| Fact | `PROPOSED` | 확인 필요 | 후보, 진술, AI 추출 |
| Fact | `CONFIRMED` | 확인됨 | 권한 있는 직원이 근거와 함께 확정 |
| Fact | `REJECTED` | 이력/제외 | 사실 아님 또는 근거 부족 |
| Fact | `SUPERSEDED` | 이력/대체 | 더 최신 confirmed Fact로 대체 |
| Gap | `OPEN` | 확인 필요 | 아직 확인 경로 미지정 |
| Gap | `STAFF_REVIEW_REQUIRED` | 확인 필요 | 답변/결과 도착, 직원 검토 필요 |
| Gap | `AWAITING_CUSTOMER` | 확인 중 | 고객 답변 대기 |
| Gap | `AWAITING_INSTITUTION` | 확인 중 | 기관 결과 대기 |
| Gap | `RESOLVED` | 확인됨 | confirmed Fact 연결됨 |
| Gap | `DISMISSED` | 이력/제외 | 직원 사유로 제외 |
| Verification | `PENDING` | 확인 필요 | 기관 확인 미시작 |
| Verification | `IN_PROGRESS`, `ON_HOLD` | 확인 중 | 진행 또는 보류 |
| Verification | `COMPLETED` | 확인됨 | 직원이 결과를 기록한 완료 |
| Verification | `FAILED` | 확인 불가 | 실패 사유/결과 표시 필요 |
| Task | `TODO` | 예정 | 실제 직원 업무 생성됨 |
| Task | `IN_PROGRESS`, `BLOCKED` | 진행 중 | 진행 또는 보류 |
| Task | `COMPLETED` | 완료 | actor/time/result 필수 |
| Task | `CANCELLED` | 취소 | 사유 필수 |

UI status는 표시용이며 내부 transition command로 다시 보내지 않는다.

## 6. Actor와 Visibility 계약

### 6.1 Actor

현재 Actor를 유지한다: `CUSTOMER`, `BANK_STAFF`, `CUSTOMER_AGENT`, `BANK_AGENT`, `VERIFICATION`, `SYSTEM`.

- `INSTITUTION` actor는 새로 만들지 않는다. 기관은 Verification target과 `OFFICIAL_VERIFICATION` source로 표현한다.
- Actor는 “누가 행위했는가”, Source는 “어떤 근거에서 나온 사실인가”다.
- `CUSTOMER_AGENT/BANK_AGENT`가 생성한 문장은 Fact evidence가 아니다.
- 직원 검토 actor는 인증 세션의 user id를 사용해야 한다. 현재 고정 actor/query parameter는 임시 호환이다.

### 6.2 Visibility별 소비자

| 데이터 | 고객 AI | 직원 AI | 고객 Frontend | 은행 Frontend |
|---|---:|---:|---:|---:|
| Message `CUSTOMER` | 허용 | 허용 | 허용 | 허용 |
| Message `BANK_INTERNAL` | 금지 | 허용 | 금지 | 허용 |
| Message `AI_PRIVATE` | 금지 | 동일 requester의 private Copilot만 | 금지 | 소유자만 |
| Context `BANK_INTERNAL` | 금지 | 허용 | 금지 | 허용 |
| Context `CUSTOMER_SHARED` | 허용 | 허용 | customer projection을 통해 | 허용 |
| Task `INTERNAL_ONLY` | 금지 | 허용 | 금지 | 허용 |
| Task `RESULT_SHAREABLE` | 아직 금지 | 허용 | 금지 | 허용 |
| Task `RESULT_PUBLISHED` | 결과 필드만 허용 | 허용 | 결과 projection만 | 허용 |
| Verification `customer_visible=false` | 금지 | 허용 | 금지 | 허용 |
| completed Verification + `customer_visible=true` | 결과만 허용 | 허용 | 결과만 허용 | 허용 |

### 6.3 공개 강제 규칙

- 고객용 endpoint/bundle은 server-side allowlist projection을 사용한다.
- Fact의 `CUSTOMER_SHARED` write는 일반 create 요청이 직접 결정하지 않는다. reviewer 권한의 별도 publish/disclosure command가 필요하다.
- Task는 `COMPLETED`이며 `result_summary`, `completed_by`, `completed_at`이 있고 `RESULT_PUBLISHED`여야 공개한다.
- Verification은 `COMPLETED`, non-empty result, `customer_visible=true`를 모두 만족해야 한다.
- AI_PRIVATE 원문은 share command로 새 visibility message를 만들기 전까지 다른 audience에 노출하지 않는다.

## 7. Conflict와 Supersede 규칙

### 7.1 우선순위는 자동 overwrite 순위가 아니다

표시 선택 시 신뢰 우선순위는 `OFFICIAL_VERIFICATION/BANK_RECORD > confirmed STAFF_OBSERVATION > confirmed CUSTOMER_STATEMENT > proposed customer/staff > AI proposal`이다. 그러나 어떤 source도 기존 confirmed 값을 자동 overwrite하지 않는다.

| 현재 상태 | 새 입력 | 저장 동작 | 화면 동작 | 필요한 사람 동작 |
|---|---|---|---|---|
| 같은 key, 같은 normalized value, proposed | 새 evidence | 기존 후보에 evidence 병합 또는 멱등 반환 | 한 후보 | 없음/검토 |
| 같은 key, 다른 value, proposed만 존재 | 새 후보 | 별도 Fact 생성 | 충돌 후보 표시 | confirm/reject |
| active confirmed 존재, 같은 value | 새 evidence | confirmed row overwrite 금지; evidence 보강 command 또는 별도 후보 | confirmed 유지 | 필요 시 검토 |
| active confirmed 존재, 다른 value | 새 `PROPOSED` 생성, `conflicts_with`는 조회 시 계산 | confirmed 유지 + 충돌 배지 | 새 값 검토 |
| 새 후보를 confirm해 기존 confirmed 대체 | 한 transaction에서 새 Fact confirm + 기존 Fact superseded | 새 값 active | owner/reviewer가 `supersedes_fact_id` 지정 |
| official/bank 후보가 기존 confirmed와 충돌 | 별도 proposed | 기존 confirmed 유지 | 높은 신뢰 근거 표시 | 반드시 직원 검토 |
| AI가 직원 confirmed와 충돌 | AI proposed 저장 가능, overwrite 금지 | confirmed 우선 | 직원 검토/거절 |

### 7.2 불변식

- scalar semantic key별 active confirmed Fact는 최대 하나다. 현재 DB 제약이 없으므로 General API transaction과 향후 generated unique key로 보강한다.
- multi semantic key는 서로 다른 normalized value를 함께 확정할 수 있다.
- `SUPERSEDED` row의 `supersedes_fact_id`는 새 active Fact를 가리킨다.
- 상태 변경 전후를 `case_context_v2_history`에 남긴다.
- review command는 `expected_version`, reason, actor를 요구한다.
- 과거 evidence와 display value를 덮어쓰지 않는다.

## 8. 직원 편집 보호 규칙

### 8.1 두 종류의 편집

| 구분 | 의미 | 저장소 | AI regeneration 영향 |
|---|---|---|---|
| Display Override | 문장 순서·표현·요약 문구만 수정 | 기존 `case_context_items.state_json` | 삭제/overwrite 금지 |
| Canonical Fact Edit | 실제 값·상태·근거를 수정/확정 | Context v2 Fact + history | AI가 overwrite 금지 |

### 8.2 최소 확장 계약

`case_context_items.state_json`에 schema 변경 없이 다음 metadata를 추가한다.

```json
{
  "override_scope": "DISPLAY_ONLY",
  "staff_text": "...",
  "base_projection_revision": 42,
  "base_content_hash": "sha256:...",
  "updated_by": "user-id"
}
```

- 현재 projection revision/hash가 base와 같으면 `CURRENT_OVERRIDE`다.
- canonical data가 바뀌고 section content hash도 바뀌면 `STALE_OVERRIDE`다.
- stale일 때 직원 문구를 폐기하지 않는다.
- stale 직원 문구만 최신 사실을 가리지 않도록 최신 generated content를 기본 표시하고, 기존 직원 편집본을 “이전 편집본”으로 함께 보존한다.
- 직원은 `최신 내용 기준으로 다시 편집` 또는 `현재 편집본을 재적용`하여 base revision을 갱신한다.
- Fact 값 변경은 display API가 아니라 Fact create/review/supersede API를 사용한다.

## 9. Message → Fact 후보 계약

### 9.1 대상과 제외

| Message actor/kind | 추출 대상 | Source | 이유 |
|---|---:|---|---|
| `CUSTOMER` 일반 CHAT | 예 | `CUSTOMER_STATEMENT` | 고객 원문 진술 |
| `BANK_STAFF` 일반 CHAT | 예 | `STAFF_OBSERVATION` | 직원 관찰/기록; 확정은 아님 |
| 질문 답변 message | 예, 전용 answer pipeline 우선 | `CUSTOMER_STATEMENT` | question/evidence 연결 |
| `CUSTOMER_AGENT` | 아니오 | 없음 | AI 자기 출력 loop 방지 |
| `BANK_AGENT` | 아니오 | 없음 | AI 자기 출력 loop 방지 |
| `SYSTEM`, `VERIFICATION`, REPORT_CARD, AI_RESPONSE | 아니오 | 없음 | 상태/생성문은 원문 evidence 아님 |
| `AI_PRIVATE` | 아니오 | 없음 | private 생성문/대화 보호 |

### 9.2 처리 순서

```text
1. Frontend → General API message 요청
2. messages transaction commit
3. 사용자에게 저장 성공 응답
4. extraction job/worker가 message_id 기준으로 AI API 호출
5. General API가 schema/key/evidence/visibility/dedupe 검증
6. Context v2 PROPOSED Fact를 멱등 생성
7. 충돌이면 기존 confirmed 유지 + 새 후보 저장
8. Fact insert가 context_revision 증가
9. 새 revision으로 7 Section projection 생성
```

### 9.3 실패·멱등·revision

- AI 실패는 message transaction을 rollback하지 않는다.
- `client_request_id = message-fact:{message_id}:{semantic_key}:{normalized-value-hash}` 형식으로 Fact create를 멱등화한다.
- message 저장 revision과 Fact 저장 revision을 구분한다. projection은 Fact 저장 후 revision을 기준으로 한다.
- 처리 성공/실패/skip을 추적할 durable 상태가 현재 없으므로 신규 `message_context_extractions` table 또는 동등한 durable outbox가 필요하다. 단순 in-process background task만으로 완료 처리하지 않는다.
- extraction record에는 `message_id`, status, attempt, last_error의 안전한 오류명, model/prompt version, processed revision/time을 둔다. 원문을 복제하지 않는다.
- AI output은 허용 semantic key만 받으며, evidence ref는 반드시 원본 `MESSAGE` id다.

## 10. Question Answer 계약

### 10.1 목표 Public contract

```json
{
  "selected_option_ids": ["opt-transfer-yes"],
  "free_text": "오늘 오전에 300만 원을 보냈습니다.",
  "question_version": 1,
  "actor_user_id": "customer-id",
  "actor_display_name": "고객"
}
```

```json
{
  "question_id": "...",
  "question_version": 1,
  "status": "ANSWERED",
  "option_items": [
    {"option_id": "opt-transfer-yes", "label": "이미 송금했어요"}
  ],
  "structured_answer": {
    "selected_options": [
      {"option_id": "opt-transfer-yes", "label_snapshot": "이미 송금했어요"}
    ],
    "free_text": "오늘 오전에 300만 원을 보냈습니다."
  },
  "answer_text": "이미 송금했어요 / 오늘 오전에 300만 원을 보냈습니다."
}
```

### 10.2 검증 규칙

- `selected_option_ids`는 중복 없는 최대 8개다.
- `SINGLE_CHOICE`는 최대 1개, `TEXT`는 선택지 0개, `CHOICE_OR_TEXT`는 질문 정책이 허용하면 복수 선택과 free text를 함께 허용한다.
- `allow_free_text=false`이면 free text를 거부한다.
- 선택 id는 해당 `question_version`의 option set에 존재해야 한다.
- 둘 다 비어 있으면 422다.
- 서버가 option label snapshot을 저장한다. Client가 label을 제출해 신뢰하지 않는다.
- Fact extraction은 option의 canonical value와 free text를 각각 읽고 하나 이상의 proposed Fact를 만들 수 있다.

### 10.3 DB 및 backward compatibility

- `customer_questions`에 `question_version BIGINT`, `answer_payload_json JSON`, `answer_question_version BIGINT`를 additive migration으로 추가한다.
- 기존 `options_json`은 새 row에서 `{option_id,label,canonical_value?}` object 배열을 저장한다. 기존 string 배열은 read adapter가 안정적인 option id를 생성한다.
- 기존 `answer_text`는 사람이 읽는 snapshot과 기존 API 호환을 위해 계속 저장한다. 쉼표/특수문자 parsing으로 canonical 값을 복원하지 않는다.
- 기존 `raw_answer` 요청은 compatibility window 동안 받아 `{selected_option_ids:[], free_text:raw_answer}`로 변환한다.
- 신규 response에 `option_items`, `structured_answer`, `question_version`을 추가하고 기존 `options`, `answer_text`도 유지한다.
- 동일 payload retry는 기존 답변을 반환하고 다른 payload는 현재처럼 409 conflict다.

## 11. 질문 중복 제거 Workflow

대규모 rewrite 없이 deterministic 후보와 `QUESTION_PLAN`을 순서대로 결합한다.

```text
canonical confirmed/proposed Fact + active Gap 확인
→ 기존 PENDING/ASKED/ANSWERED 질문 확인
→ CUSTOMER/BANK_STAFF 원문 메시지만 Case-local 검색
→ deterministic baseline 후보 생성
→ QUESTION_PLAN이 추가 contextual 후보 생성
→ General API가 field/status/text similarity/evidence/visibility 최종 필터
→ 직원이 선택·수정
→ customer_questions 저장 및 전달
```

- confirmed field는 질문 금지한다.
- proposed customer statement가 있으면 같은 질문을 자동 재발송하지 않고 직원 검토 대상으로 보낸다.
- pending/asked/answered field와 의미상 중복 질문을 제거한다.
- 메시지 검색은 AI 응답과 REPORT_CARD를 제외한다.
- lexical RAG는 보조 방어이며 semantic key 검사를 우선한다.
- 직원이 제거한 draft와 dismissed suggestion은 dedupe key/history로 같은 revision에서 재생성하지 않는다.

## 12. Verification 계약

### 12.1 세 범위

| 범위 | 현재 구현 | MVP 필요성 | 난이도 | 신뢰성 | 출처 저장 |
|---|---|---|---|---|---|
| A. Case 내부 검색 | 구현됨. lexical TF-IDF로 message/fact/question/verification/staff record 검색 | 필수 | 낮음~중간 | Case 기록 품질에 의존 | entity id + kind; 향후 revision 포함 |
| B. 공식기관 문서 RAG | 미구현 | 사칭 기관 안내 품질을 위해 제한적 도입 권장 | 중간~높음 | corpus 갱신·출처 품질에 의존 | document id/version/url/retrieved_at |
| C. 실시간 외부 Web/API | 미구현 | 이번 MVP에서는 제외 권장 | 높음 | API/웹 변경·실패 위험 | provider/request/result/audit 필요 |

MVP 현실 범위는 A를 유지·강화하고, 승인된 소수 공식 문서 corpus가 준비될 때만 B를 추가하는 것이다. C는 외부 시스템 계약과 운영 정책 전에는 시작하지 않는다.

### 12.2 결과 연결

```text
Verification PENDING
→ 직원 시작(IN_PROGRESS)
→ 직원이 공식 근거와 결과 기록(COMPLETED)
→ General API가 OFFICIAL_VERIFICATION + PROPOSED Fact 후보 생성
→ owner/reviewer가 Fact CONFIRM 또는 REJECT
→ confirmed Fact 연결 시 Gap RESOLVED
→ 별도 공개 승인 시 customer projection
```

- Work Card/AI는 claim과 target 초안만 제안한다.
- AI/RAG 검색 성공만으로 Verification을 `COMPLETED`로 만들지 않는다.
- `COMPLETED`에는 직원 actor, result, evidence URL/document ref가 필요하다.
- customer AI는 완료·공개된 결과만 읽는다.

## 13. Action / Task 계약

### 13.1 역할 분리

| Resource | 장기 역할 | 신규 write 정책 |
|---|---|---|
| `case_ai_suggestions` | AI 업무 후보와 검토 이력 | workflow에 진입하는 AI 추천은 저장 |
| `case_tasks` | 일반 담당자 업무와 실제 결과의 canonical store | 신규 일반 업무는 여기 저장 |
| legacy `actions` | 기존 체크리스트, Case control, Customer Progress event, 호환 | 일반 업무 신규 write는 단계적으로 중단; control/progress는 유지 |
| `case_decisions` | 업무·사실·공개 판단 이유 | append-only 정정 유지 |

### 13.2 목표 흐름

```text
최신 7 Section Context
→ AI Suggestion(PROPOSED: 이유, 근거, source revision)
→ 직원 검토/수정
→ ACCEPT transaction
→ CaseTask(TODO)
→ IN_PROGRESS/BLOCKED
→ 직원 완료 또는 취소
→ result + actor + time + evidence
→ 필요 시 proposed Fact
→ 별도 customer publish decision
```

- AI 추천은 자동 Task 생성 또는 `COMPLETED`를 수행하지 않는다.
- 직원이 고친 title/description은 생성된 Task에 저장하고 원 AI suggestion은 보존한다.
- legacy Work Card가 바로 Action을 만드는 현재 흐름은 compatibility adapter를 거쳐 suggestion→task로 점진 전환한다.
- legacy Action은 read adapter로 Section 6에 표시하되 v2 Task로 자동 rewrite하지 않는다.

## 14. Customer Share 계약

고객 공유 결과는 독립 Fact table이 아니라 server-side projection이다.

### 14.1 포함 allowlist

- `COMPLETED` + non-empty result + `customer_visible=true` Verification
- `COMPLETED` + `RESULT_PUBLISHED` Task의 제목/결과/완료 시각
- 기존 Customer Progress의 고객용 필드
- `visibility=CUSTOMER` message
- reviewer가 `CUSTOMER_SHARED`로 공개 승인한 Fact의 표시값

### 14.2 제외 denylist

- risk score, 내부 판단 이유, AI prompt/output metadata
- BANK_INTERNAL/AI_PRIVATE message
- proposed/rejected/superseded Fact
- pending/failed 내부 Verification 상세
- Suggestion, Task 내부 description/evidence/assignee
- 개인 메모, 다른 직원 private AI 대화

### 14.3 공개 감사

- 공개 명령은 actor, time, 대상 entity/version, 공개 snapshot을 Decision/history에 남긴다.
- 원본이 정정/superseded되면 customer projection은 이전 결과를 active로 유지하지 않는다. 정정 공개 여부를 다시 판단한다.
- Frontend는 받은 customer projection만 표시하며 자체 filtering을 보안 경계로 사용하지 않는다.

## 15. Summary 계약

### 15.1 입력

```text
active confirmed/proposed Facts
+ Exposure view
+ Impersonation view
+ Claim/Demand/Tactic view
+ active Gap/Verification
+ active/completed Task와 Action 결과
→ Summary
```

### 15.2 생성 규칙

- deterministic fallback은 transfer/exposure, 사칭 대상, 핵심 요구/수법, 확인 진행, 다음 업무를 최대 5개 bullet로 만든다.
- LLM summary는 동일한 typed projection만 입력받고 원문 message 전체를 직접 받지 않는다. message-derived proposed Fact는 source/status를 유지해 입력한다.
- summary는 canonical Fact나 conflict winner로 사용하지 않는다.
- 같은 `context_revision`에서는 중복 생성하지 않는다.
- `case_context_projections` cache/lease/last-success 구조를 유지한다.
- source revision이 바뀌면 `UPDATING`, 오래된 정상본은 `STALE`, 실패 시 deterministic fallback 또는 last success를 명시한다.
- 직원 display override는 Section 8의 base revision/hash로 stale 여부를 판단한다.

## 16. Authoritative Store

| Data Domain | Current Stores | Proposed Authoritative Store | Legacy Compatibility | Migration Needed |
|---|---|---|---|---|
| Case lifecycle/risk | `cases`, diagnosis JSON | `cases` | 그대로 | 없음 |
| canonical Fact | legacy `case_facts`, v2 facts | `case_context_facts_v2` | legacy read adapter; 신규 write v2 | 기존 data bulk migration 없음 |
| unknown/verification need | legacy AI checklist, gaps | `case_gaps` | legacy read/명시 변환 | 없음 |
| AI recommendation | Work Card ephemeral, Action checklist, suggestions | `case_ai_suggestions` | Work Card adapter | 없음 |
| staff work | actions, tasks | `case_tasks` | legacy Action read-only adapter | 없음 |
| Case control/progress events | actions | legacy `actions` 유지 | 그대로 | 없음 |
| institution verification | `verification_tasks` | `verification_tasks` | 그대로 | 향후 evidence ref 확장 검토 |
| staff decision | legacy judgment action, decisions | `case_decisions` | legacy read-only | 없음 |
| customer progress | Action projection | 기존 Action 기반 progress projection | 그대로 | 없음 |
| customer share | bundle filters/flags | General API customer projection | 기존 bundle field 유지 | 없음 |
| summary/panel read model | support cache, workspace, bundle | `case_context_projections`의 7-section payload | old support/workspace 병행 | schema version bump, table 변경 없음 |
| display override | context items | `case_context_items` | 그대로 | state JSON metadata만 |
| structured question answer | questions.answer_text | `customer_questions.answer_payload_json` | answer_text 유지 | additive migration 필요 |
| message extraction state | 없음 | `message_context_extractions` | 없음 | 신규 migration 필요 |

## 17. 기존 구조 재사용 전략

| 자원 | 분류 | 처리 |
|---|---|---|
| legacy Fact | G 계약 확정 후 신규 write 중단 | read adapter 유지, 자동 bulk migration 금지 |
| Context v2 Fact | A 그대로 재사용 | canonical Fact로 확정 |
| Gap | A 그대로 재사용 | Section 5에 UI 통합 |
| Suggestion | A/B | 내부 추천 workflow 유지, 독립 패널만 제거 |
| Task | A 그대로 재사용 | Section 6 canonical 업무 |
| Decision | A 그대로 재사용 | 검토·공개·정정 감사 기록 |
| Verification | A/B | 저장소 유지, Fact/Gap 연결 adapter 추가 |
| Action | A/G | control/progress 유지, 일반 업무는 신규 write 축소 |
| Customer Progress | A/B | 기존 Action projection 유지, Section 7로 통합 |
| `case_context_items` | A/B | display override 유지, stale metadata 확장 |
| `case_context_projections` | B | 7 Section payload/schema version으로 확장 |
| 질문 답변 | C/D | API 확장 + additive DB migration |
| Message→Fact | D/E | extraction state migration + orchestration 신규 구현 |

분류: A 기존 재사용, B Adapter/Projection, C API Contract, D DB migration, E 신규 구현, F 제거 가능, G 계약/호환 후 제거.

## 18. Migration / Backward Compatibility

### 18.1 원칙

- 이번 단계에서는 migration을 작성하거나 실행하지 않는다.
- 실제 구현 시 additive migration만 사용하고 rollback SQL을 함께 둔다.
- 기존 row를 일괄 변환·삭제하지 않는다.
- 신규 reader는 old/new를 모두 읽고, 신규 writer는 new contract를 쓴다.
- compatibility telemetry와 테스트 후 old write를 중단한다.

### 18.2 예상 migration

1. Question answer 확장
   - `question_version`
   - `answer_payload_json`
   - `answer_question_version`
   - update trigger가 structured answer 변경도 `context_revision`에 반영
2. Message extraction 상태
   - `message_context_extractions` 신규 table
   - message id unique, processing status/attempt/version/time
3. Fact scalar active-confirmed uniqueness
   - 우선 General API transaction으로 강제
   - DB generated key/index는 기존 중복 data audit 후 별도 결정

### 18.3 API compatibility window

- old `/ai/case-support`, `/context-v2/workspace`, bundle fields를 유지한다.
- 새 `/context-v2/panel`을 먼저 추가하고 Frontend 전환 후 old field 사용량을 확인한다.
- old `raw_answer`와 new structured answer를 일정 기간 동시에 받는다.
- response는 기존 `options/answer_text`와 신규 `option_items/structured_answer`를 함께 제공한다.
- old endpoint/table 삭제는 별도 승인과 rollback point 후 수행한다.

## 19. 삭제/통합 판정

| 현재 항목 | 최종 위치 | 판정 | UI | API/DB |
|---|---|---|---|---|
| 검토 대기 사실 | 사실·확인 현황 | 새 projection 구현 후 UI 통합 | 독립 subsection 제거 가능 | Fact data/API 유지 |
| AI 업무 제안함 | 담당자 조치 및 결과의 추천 workflow | 새 projection 구현 후 삭제 | 독립 Section 제거 | suggestion API/table 유지 |
| 담당자 업무 | 담당자 조치 및 결과 | 새 projection 구현 후 UI 통합 | 독립 Section 제거 | Task data/API 유지 |
| 이전 업무 제안 표시 기록 | 담당자 조치 및 결과 | API compatibility 후 삭제 | override reconciliation 후 UI 제거 | `next_actions`/history compatibility 유지 |
| 사기 수법 신호 | 사기 정황 | 새 projection 구현 후 통합 | 독립 Section 제거 | diagnosis source 유지 |
| 주장/요구/압박 3 Section | 사기 정황 하위 kind | 새 projection 구현 후 통합 | 1개 Section으로 교체 | source fields/Fact 유지 |

현재 즉시 완전 삭제 가능한 production component/API/table은 없다. 먼저 새 read projection과 회귀 검증이 필요하다.

## 20. Layer별 책임

| Layer | 책임 | 책임이 아닌 것 |
|---|---|---|
| Frontend | 7 Section 표시, typed command 제출, 직원 display/canonical 편집 구분, structured answer UX, loading/error/conflict 표시 | visibility 보안, conflict winner 결정, AI output 신뢰 |
| General API | authoritative read, 권한/visibility, validation, idempotency, conflict/supersede transaction, customer projection, AI orchestration, revision/cache | 사실 추론 자체, UI local-only 보안 |
| AI API | Fact proposal extraction, summary proposal, question/verification/action proposal, customer/staff response | confirm, task complete, disclosure, DB 직접 write |
| DB | source of truth, evidence ref, history, status, visibility, version, idempotency | UI 7 Section 구조, AI 판단 |

## 21. 변경 필요한 API / Schema

| 현재 endpoint/schema | 문제 | 변경안 | 호환 | 담당 | 선행 | 관련 영역 | 테스트 |
|---|---|---|---|---|---|---|---|
| `GET /ai/case-support` + `/context-v2/workspace` + bundle | 7개 Section이 여러 응답에 분산 | `GET /context-v2/panel?view=bank` 추가, 7-section read model 반환 | 기존 유지 | A | keys/store 승인 | FE/AI/DB cache | contract, projection, visibility |
| `PublicCaseContextProjection` | 문자열 7종, source/status/evidence 없음 | typed `CaseContextPanelView`/item contract 추가 | old schema 유지 | A+B | panel contract | FE/AI | Pydantic parity |
| `POST .../questions/{id}/answer` raw string | multi-select+text 불가 | structured request/response 추가 | raw adapter 유지 | A+C | answer contract | FE/DB/AI | validation, retry, conflict |
| `customer_questions` | 구조화 답변/version 없음 | additive columns 및 options object adapter | answer_text 유지 | A | migration review | C/B | MySQL transaction/integration |
| message create 이후 | Fact extraction 연결 없음 | durable extraction enqueue/status + v2 proposed facts | message endpoint 응답 변경 최소화 | A+B | source/key rules | DB/AI | failure nonrollback/idempotency |
| Fact create/review | conflict/supersede command 부족 | evidence dedupe, confirm-with-supersedes 또는 별도 supersede API | 기존 confirm 유지 | A | conflict rule | DB/FE | concurrent scalar confirm |
| Verification update | result→Fact/Gap 연결 없음 | completed 후 official proposed Fact command/orchestration | existing response 유지 | A+B | verification contract | DB/AI/FE | no auto confirm/complete |
| Work Card→Action | general task canonical과 불일치 | suggestion→Task path로 adapter | legacy action 유지 | A+B+C | Task policy | all | accept transaction, UI |
| customer bundle | v2 shared fact/published task 미포함 | allowlist customer projection 추가 | 기존 fields 유지 | A | visibility | customer FE/AI | leakage tests |
| context display | stale 판단 없음 | base revision/hash와 override status 응답 | 기존 item fields 유지 | A+C | summary contract | FE/DB JSON | stale/current/rebase |

## 22. A 작업 계획 — Backend & Shared Case

| Phase | Task | 파일 후보 | 선행 | 구현 | 의존 | 완료 조건 / 테스트 | 난이도·충돌 |
|---|---|---|---|---|---|---|---|
| 1 | 계약 코드화 | `contracts/public_api/case_context_v2.py`, `case_workflow.py` | 팀 승인 | 7-section view, structured answer, supersede command contract | B/C가 import | Public contract tests 통과 | 중간; B/C 공통 파일 |
| 1 | 7-section assembler | `main.py`, `context_workspace.py`, 신규 소형 projection module | 계약 | 기존 stores를 typed view로 조립 | B output | source/status/evidence 누락 없음 | 높음; `main.py` 충돌 큼 |
| 1 | authoritative adapters | `case_retrieval.py`, repositories | key mapping | legacy read + v2 우선 | B | 기존 Case 화면 회귀 | 중간 |
| 2 | 질문 DB/API | migration, `mysql_repository.py`, contracts/main | answer 승인 | additive columns, structured transaction, raw adapter | C UI, B structuring | retry/409/rollback/MySQL tests | 높음; repository 충돌 |
| 2 | conflict/supersede | v2 repository/main | rule 승인 | scalar atomic confirm/supersede/history | C review UI | concurrency/409/invariant tests | 높음 |
| 2 | message extraction orchestration | migration, message service/repository/main | B extractor | commit 후 durable enqueue, retry/idempotency | B | AI 실패 시 message 보존 | 높음; message path 충돌 |
| 3 | customer projection | bundle builder/main | visibility 승인 | shared Fact/published Task allowlist | C/B | cross-audience leakage tests | 높음 |
| 3 | Verification/Task bridging | main/repositories | policies | completed verification→proposed fact; suggestion→task | B/C | no auto confirm/complete | 중간~높음 |

## 23. B 작업 계획 — AI & Multi-Agent

| Phase | Task | 파일 후보 | 선행 | 구현 | 의존 | 완료 조건 / 테스트 | 난이도·충돌 |
|---|---|---|---|---|---|---|---|
| 1 | Fact proposal schema | `contracts/ai_internal`, `domains/case_support` | semantic keys | key/value/source/evidence proposal, no status authority | A validator | 허용 key/typed value eval | 중간; contract 충돌 |
| 1 | 7-section summary | snapshot adapter/service/prompt | panel input | deterministic fallback + LLM proposal 분리 | A assembler | same revision stable, no canonical claim | 중간 |
| 2 | Message Fact extraction | 신규 bounded service + AI route | A durable job contract | CUSTOMER/BANK_STAFF만, agent output 제외 | A orchestration | loop/dedupe/conflict/failure eval | 높음 |
| 2 | 질문 후보 통합 | question/work-card services | A fact view | structured filter input + contextual proposal | C flow | answered/confirmed/message duplicate 제거 | 중간~높음 |
| 2 | Verification proposal | work card/retrieval | key/verification rules | 내부 Case search 강화; 공식 완료 표현 금지 | A result bridge | source citation, no fake completion | 중간 |
| 3 | 공식 문서 RAG spike | 별도 retrieval adapter/eval | corpus 승인 | B 범위만, source/version 필수 | A storage | curated fixture precision 확인 | 높음; 외부 source |
| 3 | Action recommendation | work card/copilot | Task policy | 7-section context, rationale/evidence, suggestion only | A/C | no auto task complete/publication | 중간 |

## 24. C 작업 계획 — Realtime & Service Integration

| Phase | Task | 파일 후보 | 선행 | 구현 | 의존 | 완료 조건 / 테스트 | 난이도·충돌 |
|---|---|---|---|---|---|---|---|
| 1 | 7 Section shell/adapter | `CaseContextPanel.tsx`, 신규 panel types/components | A response fixture | 정확히 7개 Section, old endpoint fallback | A | fixture render, accessibility | 중간; panel 충돌 |
| 1 | 상태/출처 표시 | Context components | status mapping | UI status와 내부 status 분리 | A | 모든 resource state render | 중간 |
| 2 | structured answer UI | `CustomerQuestionCard.tsx`, cases API/types | A contract | checkbox multi-select + free text 동시 유지 | A/B | reload/retry/409/focus tests | 중간 |
| 2 | display vs Fact edit UX | EditableContext/new editor | A commands | 표현 편집과 사실 수정 진입점 분리 | A | stale override 표시/rebase | 높음 |
| 2 | 업무/추천 통합 UI | ContextWorkspace/panel | Task policy | 추천→검토→Task, active/result/history | A/B | no suggestion-as-complete | 높음 |
| 3 | customer share UI | customer timeline/progress | A projection | 서버 응답만 표시 | A | no internal fields snapshot test | 중간 |
| 3 | integration/realtime | CaseRoom pages/timeline/tests | A/B ready | message-save-first, revision refresh, stale response guard | A/B | browser E2E + refresh | 높음; room page 충돌 |

## 25. 병렬 개발 Dependency Graph

```text
[공동 결정]
7 Section + semantic keys + source/status/visibility
+ authoritative store + structured answer + Task/Action
                         │
                         ▼
              [A: Public contract/fixtures]
                    ┌────┴────┐
                    ▼         ▼
       [A: API/DB/projection] [B: AI schemas/evals]
                    │         │
                    └────┬────┘
                         ▼
              [C: Frontend integration]
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
 [A+B: message/verification] [B+C: question/action]
              └──────────┬──────────┘
                         ▼
       [A+B+C: regression + migration rehearsal + E2E]
                         │
                         ▼
                 [old UI cleanup]
```

- 공동 결정 전에는 조사·fixture 작성만 병렬 가능하다.
- A가 Pydantic response/request fixture를 고정하면 B와 C가 갈라질 수 있다.
- Message→Fact와 structured answer는 DB transaction이 준비된 뒤 통합한다.
- old UI cleanup 직전에 세 역할이 다시 합쳐져 usage search, compatibility, E2E를 승인한다.
- 충돌 hotspot은 `general_api/app/main.py`, shared contracts, `CaseContextPanel.tsx`, `ContextWorkspace.tsx`, `api/types.ts`다. 담당별 branch에서 이 파일의 소유 구간을 미리 정한다.

## 26. P0/P1/P2/P3 구현 순서

### P0 — 계약과 fixture

- 본 문서 팀 승인
- semantic key/value/cardinality 승인
- source/status/visibility/conflict 규칙 승인
- authoritative store와 Task/Action 경계 승인
- structured question answer payload 승인
- A가 Public/AI contract fixture 작성

### P1 — 병렬 기반 구현

- A: 7-section read API/assembler, compatibility adapters, DB migration 초안
- B: typed Fact extraction/summary/question AI schema와 eval
- C: fixture 기반 7 Section UI와 structured answer UI

### P2 — workflow 연결

- message→durable extraction→proposed Fact
- verification→official proposed Fact→Gap
- suggestion→Task→result
- customer allowlist projection
- stale display override/rebase

### P3 — 전환과 정리

- old/new dual-read regression
- migration apply/rollback rehearsal on isolated DB
- browser E2E: Case 생성→대화→Fact→질문→확인→업무→고객 공개
- source usage search 후 old UI render 제거
- compatibility 관찰 기간 후 old API/write deprecation 결정
- 문서 및 실제 검증 수치 갱신

## 27. 바로 삭제 가능한 항목

현재 계약 단계에서 즉시 삭제 가능한 production UI component, API, DB table은 **없다**.

새 projection 구현 후에는 다음 **UI render만** 제거할 수 있다.

- `사기 수법 신호`, `상대방 주장`, `상대방 요구`, `압박·조작` 독립 Section → `사기 정황`으로 대체 후
- `검토 대기 사실` 독립 subsection → `사실·확인 현황`으로 대체 후
- `AI 업무 제안함` 독립 Section → Section 6 추천 workflow로 대체 후
- `담당자 업무` 독립 Section → Section 6으로 대체 후

공용 `EditableContext`/`ContextWorkspace` component 자체는 다른 usage가 0인지 확인하기 전 삭제하지 않는다.

## 28. 아직 삭제하면 안 되는 항목

- legacy `case_facts`와 read adapter
- Context v2 Fact/Gap/Suggestion/Task/Decision tables와 APIs
- `verification_tasks`
- legacy `actions` 및 Customer Progress projection
- `case_context_items`와 history
- `case_context_projections`와 last-success cache
- old case-support/workspace endpoints
- `next_actions`와 NEXT_STEP override/history
- diagnosis events/features/claims/demands/tactics
- 관련 tests, migrations, rollback SQL

UI에서 안 보이게 되는 것과 source data를 삭제하는 것은 별도 승인 대상이다.

## 29. 팀 결정이 필요한 항목

1. `exposure.identity_or_card`를 하나로 유지할지 identity/card 두 key로 분리할지
2. `offender.requested_account.account_ref`, `offender.contact.value`의 저장·마스킹·보존 기간
3. multi Fact의 active confirmed 중복 판정 기준
4. STAFF_OBSERVATION을 작성자 본인이 confirm할 수 있는지, owner/reviewer 분리가 필요한지
5. `CUSTOMER_SHARED` Fact 공개를 누가 승인할지
6. trusted bank integration 도입 시 `BANK_RECORD` 자동 confirm 예외를 허용할지
7. stale Display Override의 기본 화면: 최신 generated 우선 또는 직원 문구 우선+경고
8. Message extraction의 retry 횟수/지연/운영 모니터링
9. 질문 `CHOICE_OR_TEXT`에서 복수 선택을 기본 허용할지 질문별 flag를 추가할지
10. official document RAG에 넣을 기관·문서·갱신 책임자
11. legacy Work Card→Action 신규 write를 언제 중단할지
12. 실제 인증 도입 전 MVP_OPEN에서 공개/확정 command를 허용할지

## 30. 구현 전 최종 승인 Checklist

- [ ] 7개 Section 확정
- [ ] canonical semantic key와 cardinality 확정
- [ ] authoritative store 확정
- [ ] source 규칙 확정
- [ ] status와 UI mapping 확정
- [ ] actor/visibility 규칙 확정
- [ ] conflict/supersede 규칙 확정
- [ ] 직원 display override/stale 규칙 확정
- [ ] message→Fact 대상·제외·retry 규칙 확정
- [ ] question answer payload/option id/version 확정
- [ ] 질문 중복 제거 순서 확정
- [ ] Verification A/B/C 범위 확정
- [ ] Task vs Action 정책 확정
- [ ] 고객 공개 승인자와 server allowlist 확정
- [ ] summary input/cache/fallback 확정
- [ ] migration/backward compatibility/rollback 확인
- [ ] A/B/C 역할 경계와 충돌 hotspot owner 확인
- [ ] contract fixtures를 A/B/C가 동일하게 승인
- [ ] old UI/API/table 삭제는 P3 이후 별도 승인

## 31. 참조 문서와 코드

- `09_CASE_CONTEXT_DATA_CONTRACT.md`: 기존 승인된 Context v2 resource 원칙
- `13_CONTEXT_PANEL_DATA_AUDIT.md`: 실제 데이터 흐름 전수 조사
- `backend/contracts/public_api/case_context_v2.py`: Fact/Gap/Suggestion/Task/Decision 계약
- `backend/contracts/public_api/case_workflow.py`: Case Support/Question/Fact/Verification/Action 공개 계약
- `backend/contracts/ai_internal/case_snapshot.py`: 현재 Support AI 입력/출력
- `backend/general_api/app/main.py`: orchestration 및 customer filtering
- `backend/general_api/app/domains/cases/case_context_v2_repository.py`: 상태 전이, history, transaction
- `backend/general_api/app/domains/cases/mysql_repository.py`: 메시지/질문/Fact/Action 영속화
- `backend/general_api/app/domains/cases/case_retrieval.py`: semantic mapping과 Case-local retrieval
- `backend/ai_api/app/domains/case_support/case_snapshot_adapter.py`: 현재 규칙 기반 context projection
- `frontend/src/components/CaseContextPanel.tsx`: 현재 패널 구성
- `frontend/src/components/EditableContext.tsx`: display override
- `frontend/src/components/ContextWorkspace.tsx`: 현재 resource UI
- `frontend/src/customer/CustomerQuestionCard.tsx`: 현재 단일 선택/직접입력 UI
- `database/01_mysql_csr_schema.sql`, `backend/migrations/014_case_context_v2_foundation.sql`: 저장 구조

## 32. 이번 단계 변경 확인

이번 단계에서 새로 작성한 파일은 `docs/14_CONTEXT_PANEL_CONTRACT_PLAN.md` 하나다. `docs/13_CONTEXT_PANEL_DATA_AUDIT.md`는 1차 조사 결과로 유지했다. 실제 기능 코드, Frontend, Backend, AI Prompt, DB Schema, migration, test는 수정하거나 삭제하지 않았고 DB migration도 실행하지 않았다.

2차 계약 설계가 완료되었습니다.
아직 실제 기능 코드, Frontend, Backend, AI Prompt, DB Schema는 수정하지 않았습니다.
팀이 계약안을 승인하면 다음 단계에서 A/B/C가 병렬 구현을 시작할 수 있습니다.
