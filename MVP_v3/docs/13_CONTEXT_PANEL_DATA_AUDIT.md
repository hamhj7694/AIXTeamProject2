# MVP_v3 맥락 패널 데이터 구조 전수 조사

> 조사 기준: 2026-09-14 현재 실제 실행 코드
>
> 우선순위: 실행 코드 > DB/Model/Schema > API > Frontend > AI 출력 > 테스트 > 문서
>
> 범위: 조사 및 7개 Section 데이터 계약 초안. 기능 코드, API, DB, Schema, Prompt, Test는 변경하지 않았다.

## 핵심 결론

현재 은행 화면의 `사건 맥락`은 하나의 일관된 Context 저장소가 아니다. 다음 네 계층을 한 패널에 조합한다.

1. `cases.diagnosis_json`에서 시작해 `case_context_projections`에 캐시되는 Case Support 투영
2. `case_context_items`에 저장되는 상단 7종 Section의 직원 표시문구 override/archive
3. Context v2의 Fact, Gap, AI Suggestion, Task, Decision 리소스
4. 별도 업무 테이블인 Verification, Action, Customer Progress

따라서 목표 7개 Section은 단순 UI 재배치만으로 완성되지 않는다. 먼저 canonical field, source/status, 고객 공개 규칙을 확정하고 기존 저장소를 연결해야 한다.

가장 큰 현재 단절은 다음과 같다.

- 고객·직원 메시지는 AI 호출 전에 DB에 저장된다.
- 그러나 Case Support 맥락 투영 입력에는 `messages`가 없다. 메시지 INSERT가 `context_revision`을 올려도 투영 내용은 대화만으로 갱신되지 않는다.
- 직원/고객 CaseCopilot과 Work Card는 최근 메시지를 읽지만, 그 결과가 canonical Fact나 7개 맥락 Section에 자동 반영되지는 않는다.
- 고객 질문 답변은 메시지와 legacy `PROPOSED` Fact로 함께 저장되지만 자동 `CONFIRMED` 처리되지 않는다.
- 상단 직원 편집값은 AI 투영보다 우선 표시되어 보호되지만, 최신 AI 값과 병합되는 구조는 아니므로 오래된 override가 새 정보를 가릴 수 있다.

---

## 1. 프로젝트 구조 요약

| 영역 | 실제 위치 | 역할 |
|---|---|---|
| Frontend | `frontend/src` | React Case Room, 고객 Room, 맥락 패널, 질문/기관 확인/조치 UI |
| Frontend API | `frontend/src/api/cases.ts`, `contextWorkspace.ts`, `types.ts` | General API 호출 및 화면 계약 |
| General API | `backend/general_api/app/main.py` | FastAPI entry point, Case orchestration, 공개 API |
| Case service | `backend/general_api/app/domains/cases/service.py` | 최초 분석 호출, Case/초기 보고서 생성 |
| Repository | `repository.py`, `mysql_repository.py` | In-memory 및 MySQL 영속화 |
| Context repositories | `context_item_repository.py`, `context_projection_repository.py`, `case_context_v2_repository.py` | 직원 표시 override, 투영 캐시, Context v2 리소스 |
| Case-local retrieval | `case_retrieval.py` | 메시지·질문·Fact·기관 확인·직원 기록 대상 lexical TF-IDF 검색 |
| AI API | `backend/ai_api/app/main.py` | 분석, Case Support, CaseCopilot, Work Card, 보고서 AI entry point |
| 최초 분석 | `domains/diagnosis` | turn event, window/ML, context feature, 전체 구조화 맥락, risk fusion |
| 운영 AI | `domains/case_support` | Case snapshot, 질문, 답변 구조화, 직원/고객 Copilot, Work Card |
| Shared contracts | `backend/contracts` | Pydantic 내부/공개 계약 |
| DB | `database/01_mysql_csr_schema.sql`, `backend/migrations` | MySQL 기준선 및 Context v2 migration |
| Tests | `backend/*/tests`, `frontend/scripts/test-*.cjs` | 계약·회귀·UI 소스 검증. MySQL integration은 별도 환경 필요 |
| 관련 문서 | `MVP_v3/docs` | 구현 상태/계약/검토 기록. 실제 코드보다 후순위 |

실제 운영 경로는 Frontend가 AI API나 DB를 직접 호출하지 않고 General API를 통한다. Repository 구현은 MySQL과 in-memory 두 가지가 있으므로, 코드 구조상 실제 endpoint라도 실행 환경의 repository 설정에 따라 영속성은 달라진다. 배포 환경은 MySQL을 전제로 한다.

## 2. 현재 맥락 패널 Section 전수 목록

은행 Case 화면 `CaseContextPanel`의 표시 순서는 다음과 같다.

| 순서 | 현재 화면 Section | Component | 주 데이터 |
|---:|---|---|---|
| 1 | 현재 사건 요약 | `EditableContext` | `support.case_context.situation_summary` → 진단 summary fallback |
| 2 | 고객 피해·노출 상태 | `EditableContext` | `customer_exposure` |
| 3 | 사기 수법 신호 | `EditableContext` | `key_signals` → diagnosis evidence/event fallback |
| 4 | 상대방이 주장한 내용 | `EditableContext` | `offender_claims` → diagnosis claims fallback |
| 5 | 상대방이 요구한 행동 | `EditableContext` | `offender_demands` → diagnosis event fallback |
| 6 | 압박·조작 수법 | `EditableContext` | `manipulation_tactics` |
| 7 | 사실 현황 / 확인된 사실 | `ContextWorkspace` | Context v2 confirmed facts + legacy confirmed facts |
| 8 | 사실 현황 / 검토 대기 사실 | `ContextWorkspace` | Context v2 proposed facts + legacy non-confirmed facts |
| 9 | 미확인 핵심 사항 | `ContextWorkspace` | Context v2 gaps + legacy AI checklist gaps |
| 10 | AI 업무 제안함 | `ContextWorkspace` | Context v2 suggestions + legacy AI checklist suggestions |
| 11 | 담당자 업무 | `ContextWorkspace` | Context v2 tasks |
| 12 | 기관 확인 | `CaseContextPanel`이 주입한 section | `verification_tasks` |
| 13 | 판단·결정 기록 | `ContextWorkspace` | Context v2 decisions + legacy actions |
| 14 | 고객에게 공유할 처리 결과 | `CustomerProgressEditor` | Action 기반 customer progress |
| 15 | 이전 업무 제안 표시 기록 | `EditableContext(NEXT_STEP)` | `case_context.next_actions`와 직원 override |
| 16 | 피해구제 모드 안내 | `CaseContextPanel` | `case.mode === RECOVERY`일 때 정적 문구 |
| 17 | 사건 관리 | `CaseContextPanel` | 종결/재개/휴지통 UI. 맥락 데이터 Section은 아님 |

상단 6개와 `NEXT_STEP`은 모두 `case_context_items`의 직원 편집/제외 이력을 공유한다. Context Workspace는 별도 Context v2 테이블을 사용한다.

## 3. 현재 Field 전수 목록

| 현재 Section | 현재 Field | Frontend | API response | Backend/DB | 생성 주체 | 저장/유지 | 다른 기능 의존성 |
|---|---|---|---|---|---|---|---|
| 현재 사건 요약 | `situation_summary` | `CaseContextPanel.tsx` | `case_support.case_context` | 투영 cache; 원천은 `cases.diagnosis_json`, facts/questions/verifications/actions | deterministic Case snapshot | cache 및 직원 override 유지 | 질문, Work Card, 화면 |
| 피해·노출 | `customer_exposure[]` | 동일 | 동일 | 투영 cache; answers/facts + diagnosis feature | snapshot adapter | cache 및 직원 override | 위험 안내, 질문 |
| 사기 수법 신호 | `key_signals[]` | 동일 | 동일 | diagnosis events/evidence/features + verification result | 최초 AI + adapter | diagnosis/cache/override | Case 이해, Work Card |
| 상대방 주장 | `offender_claims[]` | 동일 | 동일 | diagnosis claims + claimed organization/incident fact | 최초 AI + adapter | diagnosis/cache/override | 기관 확인, 질문 |
| 상대방 요구 | `offender_demands[]` | 동일 | 동일 | diagnosis demands/events + requested action codes/facts | 최초 AI + adapter | diagnosis/cache/override | 위험·조치 |
| 압박·조작 | `manipulation_tactics[]` | 동일 | 동일 | diagnosis context/features | 최초 AI + adapter | diagnosis/cache/override | 위험 설명 |
| 이전 제안 | `next_actions[]` | 동일 | 동일 | diagnosis recommended checks + questions/verifications/actions | adapter | cache/override | 화면; unresolved/checklist과 내용 중복 |
| 상단 편집 공통 | `staff_text`, `deleted_by`, `archive_index`, `item_version` | `EditableContext.tsx` | `/context-display` | `case_context_items.state_json`, history | 직원 | 영구 저장 | 표시 우선순위/감사 이력 |
| Fact | `semantic_key`, label, value, source, status, confidence, evidence, visibility, confirmed/rejected/supersedes/version | `ContextWorkspace` | `/context-v2/workspace` | `case_context_facts_v2` | 직원/API; 자동 연결은 제한적 | 영구 저장 | Case Support 일부 semantic key, RAG, 질문, 업무 |
| legacy Fact | `field`, `value`, `source`, `status`, evidence question/message, confirmed actor/time | 동일 | `/facts`, workspace | `case_facts` | 고객 답변/직원 확정 | 영구 저장 | Case Support, 질문 중복 방지, RAG |
| Gap | semantic key, title, reason, priority, status, source, evidence, related question/verification, resolution fact, dismissal, revision/version | 동일 | `/context-v2/workspace` | `case_gaps` | 직원/legacy 변환 | 영구 저장 | 질문·기관 확인 연결 후보 |
| AI Suggestion | type, title, rationale, priority, status, dedupe, evidence, related ids, execution mode, review/dismiss/task/version | 동일 | `/context-v2/workspace` | `case_ai_suggestions` | legacy 검토 변환/API | 영구 저장 | 채택 시 Task 생성 |
| Task | source/type/title/description/priority/assignee/status, related ids/evidence, customer visibility, result/cancel/completion/version | 동일 | `/context-v2/workspace` | `case_tasks` | 직원 또는 채택된 AI 제안 | 영구 저장 | Support action merge, RAG, 직원 AI |
| Verification | claim, target, status, version, result, evidence URL, verifier, RAG source, customer visible | `CaseActionDialogs`, panel | bundle/verifications | `verification_tasks` | 직원; Work Card는 초안만 생성 | 영구 저장 | Support, RAG, Copilot, 고객 공개 |
| legacy Action | type/status/actor/note/updated info | dialogs/workspace | bundle/actions | `actions` | 직원/system | 영구 저장 | customer progress, AI inputs, final report |
| Customer Progress | step/status/summary/next action/reference/confirmed time/updater/revision | editor/customer panel | bundle/customer-progress | 별도 table이 아니라 Action event projection | 직원/확인 요청 | Action으로 유지 | 고객 AI, 고객 화면 |
| Decision | type/title/rationale/related entity/visibility/actor/supersedes/time | workspace | `/context-v2/workspace` | `case_decisions` | 검토 권한 직원 | append-only 정정 | 직원 AI/RAG |

상단 UI는 실제 API 데이터를 사용하며 mock field를 직접 표시하지 않는다. 테스트에서는 in-memory repository와 fixtures가 사용된다.

## 4. AI 출력 Field 전수 목록

| AI Field 군 | 생성 위치/함수 | Schema | DB 저장 | Frontend 사용 | 다른 AI 입력 | 판단 |
|---|---|---|---|---|---|---|
| turn event | `diagnosis/extractor.py::extract_events` | `ExtractedEvent` | 안전 라벨로 변환 후 `diagnosis_json`; event 원문은 제거 | fallback signal/demand | Case snapshot | 유지 |
| window/segment | `window_ai`, fusion | `WindowResult` | 안전 라벨 text로 `analysis_segments` | 직접 핵심 UI 사용 적음 | diagnosis/brief | 내부 유지 |
| risk | fusion | `risk_level`, score, model label, features | `cases`, `context_features`, report | 배지/모드 | Copilot/Work Card 일부 | 유지 |
| context feature | `context_features.py` | actor/claim/request/tactic/exposure/amount/chronology/observations | `diagnosis_json` | 일부 type 보유 | snapshot adapter | 확장 필요 |
| 최초 context | full context LLM | summary, incident type, claims, demands, tactics, next steps, confidence | `diagnosis_json`, initial report | 상단 fallback | Case snapshot | 유지·재매핑 |
| Case Brief | `brief_service.py`, snapshot adapter | summary, incident, impersonation, claims, transfer, amount, evidence, unresolved, checks | projection cache | support summary | 질문/Work Card | 유지; summary는 view로 전환 |
| Case Context Projection | `case_snapshot_adapter.py` | summary/signals/claims/demands/tactics/exposure/actions | `case_context_projections` cache | 상단 7종 | 질문 및 UI | 목표 7개로 계약 변경 필요 |
| 질문 추천 | deterministic `question_service` + Work Card LLM | question id/field/text/reason/priority/options/explanation/mode | 선택/queue 후 `customer_questions` | 질문 선택·고객 카드 | Support/RAG/Copilot | 유지·답변 계약 확장 |
| 고객 답변 구조화 | `answer_service.py` | target/raw/structured/unresolved/evidence | 현재 answer endpoint는 raw text + proposed fact 저장 | 답변 카드 | Support | 구조 연결 필요 |
| 직원/고객 Copilot 답변 | `copilot_service.py` | content, model mode | AI message로 `messages` | 대화 | generated 응답은 RAG evidence에서 제외 | 유지 |
| Work Card | `work_card_service.py` | card summary/sources/rationale/next action/questions/suggested verification/action/notice/transition | 카드 자체는 미저장; 직원 승인 후 해당 업무 저장 | modal | 직접 재입력 아님 | 유지·7 Section 입력 정렬 |
| 기관 확인 추천 | Work Card `VERIFICATION_REQUEST` | suggested claim/target | 직원 등록 전 미저장 | 기관 확인 dialog | verification 생성 후 사용 | 독립 기관 AI/RAG는 미구현 |
| 조치 추천 | Work Card `BANK_ACTION` | suggested action type/note | 직원 등록 전 미저장 | 조치 dialog | action 생성 후 사용 | AI 추천과 실행은 분리됨 |
| 고객 안내 추천 | Work Card/Copilot | notice/content | 전송/응답 시 message 저장 | 고객 대화 | AI 생성문은 evidence 제외 | 유지 |

`CaseSnapshotAiAdapter.build_presentation`은 현재 비동기 LLM 호출이 아니라 구조화 입력을 규칙으로 재투영한다. 별도의 `CaseBriefService.build()` LLM 경로가 존재하지만 현재 Case Support endpoint는 adapter의 deterministic workflow를 사용한다.

## 5. Frontend → API → DB → AI 데이터 흐름

### 최초 Case 생성

```text
Frontend 분석 요청
→ General API /api/analyze
→ AI API diagnosis
   → turn event + window/ML
   → independent context feature
   → privacy-safe structured signal 기반 context LLM
   → risk fusion
→ General API가 원문 재현 필드 제거
→ MySQL 단일 transaction
   → cases
   → case_inputs(input_text는 현재 빈 문자열)
   → analysis_segments(안전 라벨 text)
   → context_features
   → case_reports/sections
   → CASE_CREATED event
→ Case 화면 응답
```

### Case Room 메시지와 AI

```text
Frontend가 사용자 메시지 POST
→ General API
→ messages INSERT/commit
→ Frontend가 저장 성공 message_id 수신
→ 선택 시 별도 AI invocation POST
→ General API가 messages/facts/questions/verifications/actions 등을 조회
→ AI API Copilot 호출
→ AI 응답 messages INSERT
→ 화면 reload
```

DB trigger가 모든 message INSERT마다 `context_revision`을 증가시킨다. 그러나 Case Support source reader는 messages를 읽지 않으므로, revision/cache는 갱신되어도 free-form 대화 내용이 상단 Context에 자동 반영되지는 않는다.

## 6. 7개 Section 매핑 Matrix

| 현재 Field/영역 | 최종 Section | 분류 | 이유 | 삭제 시 영향 |
|---|---|---|---|---|
| `situation_summary`, diagnosis summary, initial brief | 1 현재 사건 요약 | 통합 | 같은 사건을 여러 요약이 표현 | 질문/AI/보고서 fallback 영향 |
| transfer status/amount, exposure facts/codes, `customer_exposure` | 2 피해·노출 | 통합 | canonical structured exposure 필요 | recovery/질문/조치 영향 |
| claimed organization/person, requested account, caller phone | 3 사칭·접촉 정보 | 통합 | 현재 일부만 semantic field로 존재 | 기관 확인 seed 품질 저하 |
| claims/demands/tactics + key signals | 4 사기 정황 | 통합 | 세 하위 유형을 명시적으로 구분 가능 | risk 설명/질문/기관 확인 영향 |
| confirmed/proposed facts, gaps, verification | 5 사실·확인 현황 | 통합 | 확인 lifecycle을 한 View로 구성 | 질문 중복 방지/RAG/검토 영향 |
| actions, tasks, decisions, verification work/result | 6 담당자 조치 및 결과 | 통합 | 추천과 실제 실행/결과 구분 필요 | Copilot/보고서/customer progress 영향 |
| customer progress, published verification, shared result | 7 고객 공유 결과 | 유지·통합 | 공개 승인된 결과만 노출 | 고객 화면/고객 AI 영향 |
| 사기 수법 신호 독립 Section | 4 사기 정황 | 통합 | claim/demand/tactic과 중복 | 독립 삭제 전 fallback mapping 필요 |
| AI 업무 제안함 | 6의 추천 입력 또는 별도 modal | 제거 후보 | 7개 최종 Section에는 독립 영역 불필요 | suggestion→task workflow 영향 |
| 이전 업무 제안 표시 기록 | 6 | 제거 후보 | next action/업무와 중복 | 직원 override 데이터 보존 판단 필요 |
| 피해구제 정적 안내 | 6 또는 화면 안내 | 확인 필요 | Case Context data가 아닌 UI safety notice | 안전 UX 영향 |
| 사건 관리 | 패널 외 | 제거 후보(패널 기준) | context 정보가 아닌 admin control | 기능 자체 삭제 금지 |

## 7. 피해·노출 상세 조사

| 목표 후보 | 현재 존재 | 현재 저장/출처 | 대화 갱신 | 직원 수정 | Source/Status |
|---|---|---|---|---|---|
| 송금 여부 | 있음 | `cases.victim_transfer_status`; question/fact `transfer_status` | 질문 답변·일부 recovery 흐름 | Case field/fact 검토 | Case field에는 source/status 부족; Fact는 있음 |
| 송금 금액 | 부분 | `actual_loss_amount_krw`; diagnosis의 requested amount는 별개 | 일반 대화 자동 갱신 없음 | 일부 Case update 경로 | 요청액/실피해액 의미 분리 필요 |
| 개인정보 제공 | 있음 | Fact semantic `exposure.personal_information`, question field | 질문 답변은 proposed Fact | Fact 검토 가능 | v2 source/status 재사용 가능 |
| 계좌정보 제공 | 전용 canonical field 없음 | generic 개인정보/자유 Fact로만 가능 | 자동 갱신 없음 | generic Fact 가능 | 계약 필요 |
| 비밀번호/인증번호/OTP | 있음 | `exposure.authentication_information` | 질문 답변은 proposed Fact | Fact 검토 가능 | 요구와 실제 제공 구분 가능 |
| 신분증/카드정보 | 전용 field 없음 | generic Fact 외 없음 | 없음 | generic Fact 가능 | 계약 필요 |
| 원격제어 앱 | 있음 | `device.remote_control_app` semantic mapping | 지원 질문 baseline은 제한적 | Fact 가능 | v2 재사용 가능 |
| 피해 발생 시점 | 전용 field 없음 | message/question/evidence timestamp만 존재 | 자동 구조화 없음 | generic Fact 가능 | 계약 필요 |

현재 코드는 `REQUEST_AUTH_INFO`와 고객의 실제 제공 답변을 별도 데이터로 취급할 수 있으므로, “OTP를 요구했다”와 “OTP를 제공했다”를 구분할 기반은 있다. 다만 free-form 메시지 자동 Fact 추출 연결이 없다.

## 8. 사칭·접촉 정보 상세 조사

| Field | 현재 구조 | DB | AI/화면 상태 |
|---|---|---|---|
| 사칭 기관 | `claimed_organization`, `offender.claimed_organization`, diagnosis actor/claim code | diagnosis JSON, legacy/v2 Fact | 질문·기관 확인 seed에 사용 가능 |
| 사칭 인물/직책 | diagnosis subtype/group과 generic claim text뿐 | 전용 canonical column/semantic mapping 없음 | 구체 인물·직책 보존이 약함 |
| 제시 계좌 | adapter와 UI label에 `requested_account` 흔적 | 전용 baseline 질문/semantic mapping 없음 | 실질적으로 연결이 끊긴 field |
| 제시 연락처 | label에 `caller_phone` 흔적 | 전용 저장 계약 없음 | 현재 자동 추출·투영 미완성 |

기관 확인 Work Card는 pending verification이 있으면 그것을 우선하고, 없으면 summary/facts/recent conversation에서 기관명을 정규식으로 찾는다. 독립적인 기관 directory나 외부 검증 RAG는 현재 없다.

## 9. 사기 정황 상세 조사

현재 세 종류는 AI 계약에서 별도 배열이다.

- 상대방 주장: `ContextResult.claims` → `offender_claims`
- 상대방 요구: `ContextResult.demands`, ACTION_REQUEST/MONEY_MOVEMENT/AMOUNT events → `offender_demands`
- 압박·조작: `ContextResult.manipulation_tactics`, tactic codes → `manipulation_tactics`

하지만 evidence reference를 항목별로 보존하는 canonical 구조는 아니다. 배열 문자열과 진단 event가 병렬로 존재하며, 직원 상단 편집은 전체 Section 표시문구 override다. 목표 구조에서는 각 항목에 `kind`, `value`, `source`, `status`, `evidence_refs`를 연결해야 중복 제거와 안전한 재생성이 가능하다.

## 10. 사실·확인 현황 상세 조사

현재 lifecycle은 하나가 아니라 세 가지다.

| 자원 | 상태 |
|---|---|
| legacy Fact | `PROPOSED`, `CONFIRMED`, `UNRESOLVED` |
| Context v2 Fact | `PROPOSED`, `CONFIRMED`, `REJECTED`, `SUPERSEDED` |
| Context v2 Gap | `OPEN`, `AWAITING_CUSTOMER`, `AWAITING_INSTITUTION`, `STAFF_REVIEW_REQUIRED`, `RESOLVED`, `DISMISSED` |
| Verification | `PENDING`, `IN_PROGRESS`, `COMPLETED`, `ON_HOLD`, `FAILED` |

원하는 “확인 필요 → 확인 중 → 확인됨” View는 기존 상태를 다음처럼 투영할 수 있다.

- 확인 필요: proposed Fact, open/staff-review Gap, pending Verification
- 확인 중: awaiting customer/institution Gap, in-progress/on-hold Verification
- 확인됨: confirmed Fact, resolved Gap, completed Verification

AI 또는 고객 답변이 Fact를 자동 `CONFIRMED`로 만드는 실행 코드는 없다. 고객 질문 답변은 `AI_EXTRACTED/PROPOSED` legacy Fact로 저장되고, 직원 확인 API가 별도로 `CONFIRMED` 처리한다. Context v2 직원 입력도 처음에는 `PROPOSED`이며 owner/reviewer 검토가 필요하다.

## 11. 담당자 조치 및 결과 상세 조사

현재 업무 데이터는 두 계열이다.

- legacy `actions`: 업무 유형, 상태, actor, note, updater. Customer Progress도 특수 Action command/event를 투영한다.
- Context v2 `case_tasks`: source/type/priority/assignee/status/result/evidence/customer visibility를 더 명확히 표현한다.

AI Work Card는 `suggested_action_type/note`만 반환하며 저장하지 않는다. 직원이 modal에서 확인하고 Action을 생성해야 실제 조치가 된다. Context v2 AI Suggestion도 `PROPOSED` 상태이며 직원이 채택할 때 Task가 생성된다. 따라서 현재도 “AI 추천 ≠ 실제 수행”은 분리되어 있다.

지급정지·신고·피해구제는 Action/Customer Progress와 recovery mode에 분산되어 있다. 최종 Section에서는 추천, 예정, 진행, 완료, 취소와 결과 근거를 같은 카드에서 구분하되 canonical Task/Action 통합 정책이 먼저 필요하다.

## 12. 고객 공유 결과 상세 조사

고객 bundle은 은행 내부/AI-private 메시지를 제외한다. 고객에게 보이는 처리 결과는 다음이다.

- `messages.visibility == CUSTOMER`인 메시지
- status가 `COMPLETED`이고 `customer_visible == true`이며 result가 있는 Verification
- Action에서 투영된 Customer Progress
- 고객 질문과 접수된 답변

Context v2에는 `BANK_INTERNAL/CUSTOMER_SHARED`, Task에는 `INTERNAL_ONLY/RESULT_SHAREABLE/RESULT_PUBLISHED` 계약이 있지만, 현재 고객 bundle의 주 공개 경로와 완전히 통합되지는 않았다. 고객 AI 입력은 공개된 verification과 customer progress만 받는다. Prompt/코드에는 미완료 조치를 완료로 단정하지 않도록 하는 방어가 있으나 생성형 응답의 절대적 보장은 아니므로, 최종 공개 결과는 서버가 완료+공개 상태를 필터링해야 한다.

## 13. Source / Status / Actor / Visibility 현황

### Actor

- Message: `CUSTOMER`, `BANK_STAFF`, `CUSTOMER_AGENT`, `BANK_AGENT`, `VERIFICATION`, `SYSTEM`
- Action actor: `BANK_STAFF`, `SYSTEM`
- `INSTITUTION` actor enum은 현재 없음. 기관은 Verification의 target/result로 표현된다.

### Source

- Context v2 Fact: `AI_EXTRACTION`, `CUSTOMER_STATEMENT`, `STAFF_OBSERVATION`, `BANK_RECORD`, `OFFICIAL_VERIFICATION`
- Gap: `AI`, `BANK_STAFF`, `SYSTEM_RULE`
- Task: `STAFF_CREATED`, `AI_SUGGESTION_ACCEPTED`, `SYSTEM_REQUIRED`
- legacy Fact: `AI_EXTRACTED`, `HUMAN_CONFIRMED`, `VERIFIED`, `UNRESOLVED`

요청 후보와 대응시키면 `BANK_STAFF_RECORD`는 `STAFF_OBSERVATION/BANK_RECORD`, `AI_INFERENCE`는 `AI_EXTRACTION`, `INSTITUTION_VERIFICATION`은 `OFFICIAL_VERIFICATION`으로 대부분 재사용 가능하다. `INITIAL_ANALYSIS`는 전용 source가 없으며 AI extraction의 provenance/evidence로 표현할지 결정해야 한다.

### Status

`PROPOSED/PENDING/CONFIRMED/REJECTED`는 자원별로 이미 존재한다. `UNVERIFIABLE` 단일 상태는 없고 Verification의 `FAILED`, Gap의 `DISMISSED`가 유사하지만 의미가 다르므로 합치면 안 된다.

### Visibility

- Message: `CUSTOMER`, `BANK_INTERNAL`, `AI_PRIVATE`
- Context v2: `BANK_INTERNAL`, `CUSTOMER_SHARED`
- Task result: `INTERNAL_ONLY`, `RESULT_SHAREABLE`, `RESULT_PUBLISHED`
- Verification: boolean `customer_visible`

`SHARED`라는 단일 enum은 없다. 현재 계약을 유지하면서 최종 customer projection에서 변환하는 편이 안전하다.

## 14. 메시지 DB 선저장 여부

판정: **YES**. 고객과 직원 모두 사용자 원문 메시지를 먼저 저장하고 성공 응답을 받은 뒤 별도 AI invocation을 호출한다.

- 직원: `CaseRoomPage.send`가 `sendMessage`를 await한 뒤 AI queue에 넣는다.
- 고객: `CustomerCaseRoomPage.send`가 `sendCustomerMessage`를 await한 뒤 저장된 message id로 고객 AI를 호출한다.
- General API는 AI 장애가 사용자 메시지 저장을 막지 않도록 분리되어 있다.

예외/주의:

- 최초 Case 생성 입력 원문은 `case_inputs.input_text`에 빈 문자열로 저장된다. 진단 결과는 privacy-safe projection으로 저장된다.
- AI 응답은 생성 성공 후 DB에 저장된다.
- 메시지 저장 후 Context revision은 증가하지만 Case Support input에 messages가 없어 Context 내용 자동 반영은 되지 않는다.

## 15. 직원 편집 보호 여부

판정: **부분 보호**.

보호되는 부분:

- 상단 `EditableContext`는 `staff_text != null`이면 AI/fallback lines보다 직원 텍스트를 우선한다.
- 제외/복원과 version history가 `case_context_items`에 저장된다.
- Context v2 confirmed Fact는 같은 semantic key의 legacy Fact보다 Support merge에서 우선한다.
- Fact 확정은 별도 reviewer 동작이며 AI가 자동 확정하지 않는다.

없는 부분:

- 상단 override와 canonical source item의 field-level merge/lock은 없다.
- 직원이 수정한 요약 전체가 장기간 최신 AI summary를 가릴 수 있다.
- `updated_by`, revision은 있으나 AI 재생성 충돌을 해결하는 source-aware merge 정책은 없다.
- free-form 메시지에서 새 Fact를 추출해 직원 override와 안전하게 병합하는 파이프라인도 없다.

따라서 “AI가 직원 문구를 직접 overwrite”하지는 않지만, “직원 편집을 보존하면서 최신 canonical Fact를 반영”하는 완전한 보호 장치는 없다.

## 16. 질문 기능 데이터 의존성

현재 기본 Case Support 질문 후보 경로는 다음이다.

```text
diagnosis + Case fields
→ legacy/v2 facts
→ 기존 questions/answers
→ verifications/actions
→ deterministic recommended questions
→ General API confirmed/handled field 및 문장 유사도 필터
```

이 경로에는 free-form messages가 없다. 별도 `QUESTION_PLAN` Work Card는 messages, lexical RAG, support context, 기존 질문/답변, facts, drafts를 읽으므로 대화 기반 추가 질문을 만들 수 있다. 즉 사용자가 원하는 전체 순서는 단일 파이프라인으로는 아직 완성되지 않았다.

현재 답변 계약:

- 저장 API: `raw_answer: string`
- DB: `customer_questions.answer_text`
- UI: `selected` 단일 문자열 또는 `custom` 단일 문자열
- 선택지를 누르면 직접입력이 지워지고, 직접입력하면 선택이 지워진다.
- `selected_option_id` 없음
- `selected_option_ids[]` 없음
- 다중 선택 + free text 동시 전송 없음

질문 생성 계약에는 `options[]`, `answer_mode`, `allow_free_text`가 있지만 저장 계약이 이를 끝까지 보존하지 못한다.

## 17. 기관 확인 AI 의존성

현재 가능한 입력 연결:

- Case summary/initial brief
- legacy facts
- recent customer/team conversation
- pending verifications
- support unresolved items
- lexical retrieved context
- attachment metadata

현재 빠진 연결:

- 목표 3번 Section의 정규화된 사칭 인물/직책/계좌/연락처 전체
- Gap과 Verification의 명시적 1:1/1:N orchestration
- 기관 공식 데이터 source를 검색하는 실제 외부/벡터 RAG
- verification 결과를 `OFFICIAL_VERIFICATION` Context v2 Fact로 자동 제안하는 흐름

현재 “기관 확인 AI”는 독립 agent가 아니라 `VERIFICATION_REQUEST` Work Card 생성이다. 기관명은 pending verification 또는 문자열/정규식 seed에 크게 의존한다.

## 18. 조치 AI 의존성

Work Card 조치 AI는 다음을 읽는다.

- Case summary/status/mode/fraud type
- facts
- staff context(Context v2 facts/tasks/decisions)
- recent customer/team conversation
- pending actions
- attachments
- unresolved items
- pending verifications
- question candidates

CaseCopilot도 questions/facts/verifications/actions/messages/customer progress/participants를 읽는다. 목표 입력 대부분은 이미 연결 가능하지만 피해·노출과 사칭·접촉의 canonical field가 불완전하고, verification completed result와 customer answer를 Context v2 Fact로 일관되게 승격하는 연결이 빠져 있다.

## 19. 삭제 후보 영향 분석

| 후보 | Frontend | Backend/DB | 다른 참조 | 판정 | 이유 |
|---|---|---|---|---|---|
| 검토 대기 사실 | `ContextWorkspace` | legacy/v2 Fact API와 tables | 질문 중복 방지, Support, RAG, 직원 검토 | **KEEP INTERNALLY** | UI 통합은 가능하지만 data/lifecycle 삭제 불가 |
| AI 업무 제안함 | `ContextWorkspace` | suggestions API/table; legacy checklist 변환 | 채택 시 Task, 권한/회귀 테스트 | **REMOVE AFTER CONTRACT** | 독립 UI는 제거 가능하나 추천→업무 변환 계약 필요 |
| 담당자 업무 | `ContextWorkspace` | `case_tasks` API/table | Support action merge, staff RAG/Copilot, 결과 | **KEEP INTERNALLY** | 목표 6번 핵심 데이터 |
| 이전 업무 제안 표시 기록 | `CaseContextPanel`, `EditableContext(NEXT_STEP)` | projection `next_actions`, display override/history | 화면 중복, 일부 직원 편집 기록 | **REMOVE AFTER CONTRACT** | UI만 제거하는 것은 비교적 안전하나 직원 저장값 처리 필요 |

추가 판단:

- AI Suggestion의 자동 production 생성은 현재 제한적이며, 주로 legacy AI checklist를 검토할 때 v2 suggestion으로 변환한다.
- 최종 보고서/직원 AI는 Action/Task/Decision/Verification을 읽으므로 underlying 업무 데이터는 유지해야 한다.
- Section UI 제거와 API/table 삭제는 별도 작업으로 취급해야 한다.

## 20. 7개 Section 데이터 계약 초안

이 표는 기존 Context v2 Fact/Gap/Task/Decision, Verification, Customer Progress를 최대한 재사용하는 초안이다.

| Section | Field | Type | Source | Status | Writer/Editor | DB | Customer Visible | AI Input | Update Rule |
|---|---|---|---|---|---|---|---|---|---|
| 현재 사건 요약 | `summary` | derived text/bullets | 다른 6개 Section | projection status | AI view; 직원 display override | cache + override | 내부 기본 | Yes | canonical data revision마다 재생성; source of truth 금지 |
| 피해·노출 | `transfer_status` | enum | customer/staff/bank record | proposed/confirmed | 고객 진술, 직원 확인 | v2 Fact + Case compatibility | 승인 시 가능 | Yes | source 우선순위와 evidence 유지 |
| 피해·노출 | `requested_amount`, `actual_loss_amount` | KRW number | initial/customer/bank | proposed/confirmed | AI 제안, 직원 확인 | Fact; actual case field compatibility | 제한 | Yes | 요청액과 실피해액 분리 |
| 피해·노출 | personal/account/auth/identity-card exposure | typed facts | customer/staff | proposed/confirmed/rejected | 고객 진술, 직원 검토 | v2 Fact | 승인 시 | Yes | semantic key별 최신 유효 Fact |
| 피해·노출 | remote app, occurred_at | boolean/string, datetime | customer/staff | proposed/confirmed | 고객/직원 | v2 Fact | 제한 | Yes | evidence ref 필수 권장 |
| 사칭·접촉 | organization/person-role/account/contact | typed facts | initial/customer/staff | proposed/confirmed | AI extraction, 직원 검토 | v2 Fact | 기본 내부 | Yes | 값별 semantic key와 provenance |
| 사기 정황 | claims | item[] | initial/customer/staff | proposed/confirmed | AI 제안, 직원 검토 | v2 Fact 또는 명시 item projection | 내부 | Yes | evidence별 dedupe |
| 사기 정황 | demands | item[] | initial/customer/staff | proposed/confirmed | 동일 | 동일 | 내부 | Yes | 실제 고객 행동과 분리 |
| 사기 정황 | tactics | item[] | initial/customer/staff | proposed/confirmed | 동일 | 동일 | 내부 | Yes | code + display label 분리 |
| 사실·확인 | facts | Fact[] | 모든 허용 source | v2 Fact status | staff review | v2 Fact | visibility에 따름 | Yes | AI/customer는 자동 confirm 금지 |
| 사실·확인 | gaps | Gap[] | AI/staff/system | Gap status | staff | Gap | 내부 | Yes | confirmed fact/verification으로 resolve |
| 사실·확인 | verifications | Verification[] | staff/official | verification status | staff | Verification | 완료+승인만 | Yes | result publish 별도 승인 |
| 담당자 조치 | tasks/actions | Task[] | staff/accepted AI | task status | staff | v2 Task; legacy Action compatibility | 기본 내부 | Yes | 추천 채택 후에만 실제 업무 생성 |
| 담당자 조치 | result/evidence/decision | result + refs | staff/bank/official | completed/cancelled | reviewer/owner | Task/Decision | 별도 publish | Yes | 완료 actor/time/result 필수 |
| 고객 공유 결과 | progress | Progress[] | staff action projection | progress status | staff | Action projection | Yes | 확인된 업무 상태만 투영 |
| 고객 공유 결과 | published verification/task result | item[] | official/staff | published | 승인 권한자 | verification/task | Yes | 서버가 완료+공개 조건 강제 |

제안 semantic key 후보는 기존 규칙을 확장하는 방식이 적합하다.

- `transfer.actual.status`, `transfer.requested.amount`, `transfer.actual.amount`
- `exposure.personal_information`, `exposure.account_information`, `exposure.authentication_information`, `exposure.identity_or_card`, `exposure.occurred_at`
- `device.remote_control_app`
- `offender.claimed_organization`, `offender.claimed_person_or_role`, `offender.requested_account`, `offender.contact`

## 21. 현재 → 목표 GAP 분석

| 구분 | GAP | 영향 파일/영역 | 선행 | 난이도 | 충돌 |
|---|---|---|---|---|---|
| A 그대로 사용 | 메시지 DB 선저장, v2 Fact review, Verification 공개 필터, Task result, Decision history | General API/repositories | 없음 | 낮음 | 낮음 |
| A 그대로 사용 | claim/demand/tactic의 의미 구분 | diagnosis contracts/adapter | 항목 계약 확인 | 낮음 | 중간 |
| B 표현 수정 | 현재 다수 Section을 목표 7개 UI로 grouping | panel/workspace | mapping 승인 | 중간 | C UI 작업과 충돌 |
| B 표현 수정 | 상태들을 “필요/진행/확인” View로 projection | workspace adapter | 상태 매핑 승인 | 중간 | Backend/Frontend 동시 |
| C 계약 변경 | Case Support에 messages 또는 안전한 conversation-derived facts 연결 | snapshot contract/API/AI | source·confirmation 정책 | 높음 | A/B 핵심 충돌 |
| C 계약 변경 | 다중 option + free text 답변 | public contract/DB/repository/UI | 답변 payload 결정 | 중간 | C 중심, A 지원 |
| C 계약 변경 | exposure/contact canonical semantic keys | contracts/repository/adapter | field 목록 승인 | 높음 | A/B/C 공통 |
| C 계약 변경 | Action/Task/Customer Progress 통합 projection | General API/context projection | authoritative store 결정 | 높음 | A/C |
| D 미구현 | free-form 대화 → proposed Fact/Context 자동 반영 | AI extraction/orchestration | evidence, dedupe, review rule | 높음 | A/B |
| D 미구현 | 실제 기관 확인 RAG/agent | AI API/retrieval/data source | 데이터 source·법적 범위 | 높음 | B/A |
| D 미구현 | 사칭 인물/직책/계좌/연락처 전용 추출·저장 | diagnosis/Fact/UI | 개인정보 정책 | 높음 | 전 영역 |

## 22. A/B/C 다음 작업 분배

Git 최신 작성자 기록은 핵심 파일별로 `hamhj7694`, `jongyeol-lee`가 섞여 있다. 이는 **기존 작성자 기록**일 뿐 향후 담당 역할을 의미하지 않는다.

| Workstream | 기존 작성 영역/최근 작성자 기록 | 향후 담당 | 작업 | 선행/병렬 |
|---|---|---|---|---|
| canonical context contract | General API/Context v2: 주로 `jongyeol-lee` | **A** | semantic keys, source/status priority, projection read model, migration 필요성 설계 | 최우선, B/C 대기 |
| summary/context projection | adapter: `hamhj7694`; API: `jongyeol-lee` | **A+B** | 7 Section 입력/출력 계약, 대화-derived proposed facts 연결 | 계약 후 병렬 |
| 최초/증분 Fact 추출 | AI diagnosis/support 혼합 | **B** | exposure/contact/circumstance extraction, evidence refs, dedupe/eval | A 계약 후 |
| 기관 확인 AI/RAG | Work Card: `jongyeol-lee` | **B** | source 조사, institution candidate/result fact proposal | field 계약 후 병렬 |
| 조치 AI | Work Card/Copilot 혼합 | **B** | 7 Section 기반 input, 완료 단정 방지 eval | Task 계약 후 병렬 |
| 7 Section UI | panel `hamhj7694`, workspace `jongyeol-lee` | **C** | UI grouping, API adapter, empty/loading/error | read contract 확정 후 |
| 질문 payload/UI | 고객 UI/General API 혼합 | **C + A** | multi-select + free text UI, API/DB payload | 답변 계약 승인 후 병렬 |
| realtime/integration | Case Room pages | **C** | message-save-first 회귀, context refresh/E2E | projection 구현 후 |
| data integrity/migration | MySQL/repository | **A** | backward compatibility, legacy mapping, rollback | 계약 확정 후 |

추천 진행 단계:

1. 세 명 공동으로 field/source/status/visibility 계약 확정
2. A가 read model/API skeleton과 backward mapping 확정
3. B가 extraction/projection/기관·조치 AI를 병렬 구현
4. C가 7 Section UI와 질문 계약 UI를 병렬 구현
5. A+C가 API integration, B가 eval fixture 제공
6. 세 명 공동 contract/regression/E2E 및 migration rehearsal

## 23. 가장 먼저 합의해야 할 사항

1. Context의 authoritative store를 Context v2 Fact/Gap/Task/Decision으로 둘지, legacy Case fields와 병행할 기간
2. 7개 Section별 canonical semantic key와 데이터 타입
3. source 우선순위: official/bank/confirmed staff/customer/AI 사이의 overwrite 및 supersede 규칙
4. 고객/AI 진술은 항상 `PROPOSED`인지, 어떤 작업만 자동화할 수 있는지
5. `actual_loss_amount`와 `requested_amount`의 명확한 구분
6. 고객 공개 승인 주체와 서버 강제 조건
7. summary는 저장 Fact가 아니라 derived view라는 원칙
8. 메시지에서 Fact를 추출할 시점, evidence ref, 중복 제거, 개인정보 보존 범위
9. Question answer payload의 `selected_option_ids[] + free_text` 형식
10. Action과 Context v2 Task 중 어느 것을 장기 canonical 업무 저장소로 할지

## 24. 바로 개발 가능한 작업

계약을 바꾸지 않고도 가능한 범위다.

- 7개 최종 Section용 Frontend read-only composition prototype
- 기존 상태값을 “확인 필요/확인 중/확인됨”으로 표시하는 pure mapping 함수와 테스트
- 현재 API 응답을 7개 Section으로 변환하는 read-only adapter spike
- message-save-before-AI 회귀 테스트 강화
- 현재 semantic key/source/status inventory fixture 작성
- 공개 완료 Verification만 고객 projection에 포함되는 contract test 강화
- AI가 customer/internal audience를 혼동하지 않는 eval case 확장

단, 이 단계에서도 기존 Section 삭제나 DB write 계약 변경은 하면 안 된다.

## 25. 아직 개발하면 안 되는 작업

- 합의 전 기존 Fact/Gap/Task/Suggestion/Action table 또는 API 삭제
- 상단 Section 문자열을 canonical source로 간주하는 migration
- 고객/AI 진술의 자동 `CONFIRMED` 승격
- source 우선순위 없이 AI가 직원 확정값을 overwrite하는 regeneration
- 고객 공개 승인 없이 Task/Verification/Decision을 고객 bundle에 노출
- requested amount와 actual loss amount 통합
- 다중선택 답변을 기존 `answer_text` 문자열에 임의 구분자로만 저장
- 실제 기관 source가 확정되지 않은 상태에서 “기관 RAG 완료”로 구현
- 기존 `context_revision` trigger만으로 대화가 Context에 반영된다고 가정
- UI 제거와 underlying data/API 삭제를 한 번에 수행

---

## 주요 코드 근거

- `frontend/src/components/CaseContextPanel.tsx`: 현재 패널 조립 및 표시 순서
- `frontend/src/components/EditableContext.tsx`: 직원 override/archive/restore와 표시 우선순위
- `frontend/src/components/ContextWorkspace.tsx`: Fact/Gap/Suggestion/Task/Decision UI
- `frontend/src/customer/CustomerQuestionCard.tsx`: 단일 선택 또는 직접입력 답변 UX
- `frontend/src/pages/CaseRoomPage.tsx`, `CustomerCaseRoomPage.tsx`: 메시지 선저장 후 AI 호출
- `backend/general_api/app/main.py`: Case Support/Question/Copilot/Work Card/Context v2/Progress orchestration
- `backend/general_api/app/domains/cases/mysql_repository.py`: Case 생성 및 고객 답변 transaction
- `backend/general_api/app/domains/cases/signal_projection.py`: 최초 입력 privacy-safe persistence boundary
- `backend/general_api/app/domains/cases/case_retrieval.py`: Case-local lexical retrieval와 v2 merge
- `backend/ai_api/app/domains/case_support/case_snapshot_adapter.py`: 현재 Case Support 투영
- `backend/ai_api/app/domains/case_support/work_card_service.py`: 질문/기관 확인/조치 초안 생성
- `backend/contracts/ai_internal/case_snapshot.py`: 현재 Support 입력/출력 계약
- `backend/contracts/public_api/case_context_v2.py`: Fact/Gap/Suggestion/Task/Decision 계약
- `database/01_mysql_csr_schema.sql`, `backend/migrations/014_case_context_v2_foundation.sql`: 실제 저장 구조

아직 어떠한 코드도 수정하지 않았습니다.
위 조사 결과와 7개 Section 데이터 계약 초안을 검토·승인받은 후
2차 작업에서 실제 계약 및 구현 변경을 진행하겠습니다.
