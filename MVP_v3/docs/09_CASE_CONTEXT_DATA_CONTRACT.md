# 사건 맥락 v2 목표 데이터 계약

상태: **저장소·General API·은행 업무 화면 연결 완료 / 실제 LLM projection과 기존 사실 자동 이관은 후속**
작성일: 2026-09-05
적용 대상: 은행 화면의 사건 맥락, AI 질문·업무 추천, 직원 업무 처리, 향후 LLM/RAG 입력·출력

승인 상태: **제품 책임자 승인 완료·단계적 구현 허용 (2026-09-05)**

> 이 문서는 목표 계약을 정의한다. Public/AI Pydantic 계약, 개발 DB migration과 저장·조회 API, 은행 화면의 분리된 업무 처리를 연결했다. 기존 사실·판단 기록은 호환 조회로 보존하고 기존 AI 체크리스트는 명시적 검토 시 새 업무로 채택한다. 기존 고객 답변 자동 이관과 실제 LLM projection은 아직 후속 단계다.

## 1. 해결하려는 문제

현재 화면의 다음 영역은 데이터 출처와 상태 의미가 일부 겹친다.

- `확인된 사실`: `case_facts.status=CONFIRMED`를 표시한다.
- `AI 추가 확인 체크리스트`: 미확인 필드에서 만든 `AI_CHECKLIST:*` Action을 표시한다.
- `다음 업무 제안`: AI snapshot의 `case_context.next_actions`를 표시한다.
- `담당자 판단·조치 기록`: `STAFF_JUDGMENT` Action을 체크리스트처럼 표시한다.

현재 `next_actions`와 AI 체크리스트는 모두 `next_checks`와 미확인 필드에서 파생될 수 있다. 또한 직원의 판단 근거와 실제 실행 업무를 하나의 Action 상태로 관리해 의미가 모호하다.

목표 계약은 다음 두 축을 분리한다.

```text
지식 상태: 사실 후보 → 확인된 사실
              └→ 미확인 핵심 사항

업무 상태: AI 제안 → 직원 채택 → 담당자 업무 → 결과 기록
                                      └→ 사실 후보 또는 진행 상황 갱신
```

## 2. 사용자 화면의 목표 명칭

| 현재 명칭 | 목표 명칭 | 처리 |
|---|---|---|
| 확인된 사실 | 확인된 사실 | 유지하되 출처·확인자·확인 시각을 표시 |
| AI 추가 확인 체크리스트 | 미확인 핵심 사항 | 체크박스를 없애고 확인 상태 중심으로 변경 |
| 다음 업무 제안 | AI 업무 제안 | AI 체크리스트와 통합 |
| 담당자 판단·조치 기록 | 담당자 업무 | 실행할 업무와 처리 결과 관리 |
| 없음 | 판단·결정 이력 | 직원 판단 근거를 업무와 분리하여 보존 |

## 3. 공통 규칙

1. AI 추출 또는 고객 답변만으로 사실을 `CONFIRMED`로 만들 수 없다.
2. AI는 원칙적으로 제안을 만들며 은행의 실제 업무 완료 상태를 직접 변경할 수 없다.
3. 직원이 AI 제안을 채택해야 담당자 업무가 생성된다.
4. 담당자 업무 완료만으로 관련 사실이나 고객 진행 상황을 자동 완료 처리하지 않는다.
5. 업무 완료 결과에서 새 사실 후보를 만들 수 있지만 별도 확인 절차를 거친다.
6. 미확인 사항은 연결된 사실이 확정되거나 직원이 사유를 남겨 제외한 경우에만 해소된다.
7. 고객 공개 상태와 은행 내부 상태를 동일 필드로 암묵적으로 공유하지 않는다.
8. 모든 수정 명령은 `expected_version`과 행위자 정보를 사용하고 충돌은 HTTP 409로 처리한다.
9. 생성 명령은 `client_request_id`로 멱등성을 보장한다.
10. 내부 코드와 사용자 표시 문구를 분리한다. API의 `semantic_key`나 enum 값은 UI에 직접 출력하지 않는다.
11. 원문 통화 내용은 저장하거나 RAG 색인에 넣지 않는다. 허용된 구조화 피처와 참조 ID만 사용한다.
12. AI 결과는 적용 명령이 아니라 제안 결과다. General API가 정책·권한·중복·revision을 검증한 뒤 저장한다.

## 4. 핵심 엔터티

### 4.1 CaseFact — 사실 후보와 확인된 사실

한 사건에 관해 현재 알려진 정보를 구조화한다.

```text
CaseFact
  fact_id: string
  case_id: string
  semantic_key: string
  display_label: string
  value: object
  display_value: string
  source_kind: AI_EXTRACTION | CUSTOMER_STATEMENT | STAFF_OBSERVATION |
               BANK_RECORD | OFFICIAL_VERIFICATION
  status: PROPOSED | CONFIRMED | REJECTED | SUPERSEDED
  confidence: 0..1 | null
  evidence_refs: EvidenceRef[]
  visibility: BANK_INTERNAL | CUSTOMER_SHARED
  confirmed_by: string | null
  confirmed_at: datetime | null
  rejection_reason: string | null
  supersedes_fact_id: string | null
  version: integer
  created_at: datetime
  updated_at: datetime
```

규칙:

- `PROPOSED`: AI 추출, 고객 답변, 직원 관찰 등 아직 검토가 필요한 상태다.
- `CONFIRMED`: 은행 기록, 공식 기관 확인 또는 권한 있는 직원 검토로 확정된 상태다.
- `REJECTED`: 사실이 아니거나 근거가 부족하다고 판단한 상태다.
- `SUPERSEDED`: 같은 의미의 더 최신 사실로 대체된 과거 상태다.
- `CONFIRMED`에는 `confirmed_by`, `confirmed_at`, 하나 이상의 근거 또는 확인 사유가 필요하다.
- 값을 수정할 때 기존 확정 사실을 덮어쓰지 않고 새 사실이 이전 사실을 `supersedes`한다.
- `display_label`과 `display_value`는 사용자용 문구이며 내부 `semantic_key`를 그대로 노출하지 않는다.

예시:

```json
{
  "fact_id": "FACT-101",
  "case_id": "VP-12",
  "semantic_key": "transfer.actual.status",
  "display_label": "실제 송금 여부",
  "value": {"status": "TRANSFERRED", "amount_krw": 3000000},
  "display_value": "300만 원을 송금한 사실이 확인됨",
  "source_kind": "BANK_RECORD",
  "status": "CONFIRMED",
  "confidence": null,
  "evidence_refs": [{"type": "BANK_TRANSACTION", "id": "TX-82"}],
  "visibility": "BANK_INTERNAL",
  "confirmed_by": "USER-17",
  "confirmed_at": "2026-09-05T04:30:00Z",
  "rejection_reason": null,
  "supersedes_fact_id": null,
  "version": 1,
  "created_at": "2026-09-05T04:30:00Z",
  "updated_at": "2026-09-05T04:30:00Z"
}
```

### 4.2 CaseGap — 미확인 핵심 사항

사건 대응에 필요하지만 아직 확인되지 않은 정보의 상태를 관리한다. 체크리스트나 업무가 아니다.

```text
CaseGap
  gap_id: string
  case_id: string
  semantic_key: string
  title: string
  reason: string
  priority: URGENT | HIGH | NORMAL
  status: OPEN | AWAITING_CUSTOMER | AWAITING_INSTITUTION |
          STAFF_REVIEW_REQUIRED | RESOLVED | DISMISSED
  source: AI | BANK_STAFF | SYSTEM_RULE
  evidence_refs: EvidenceRef[]
  related_question_ids: string[]
  related_verification_ids: string[]
  resolution_fact_id: string | null
  dismissal_reason: string | null
  visibility: BANK_INTERNAL
  source_revision: integer
  version: integer
  created_at: datetime
  updated_at: datetime
```

규칙:

- 고객에게 질문을 발송하면 `AWAITING_CUSTOMER`로 변경한다.
- 기관 확인 업무를 시작하면 `AWAITING_INSTITUTION`으로 변경한다.
- 고객 답변이 도착해도 자동 `RESOLVED`하지 않고 `STAFF_REVIEW_REQUIRED`로 변경한다.
- 연결된 `CONFIRMED` 사실이 생기면 `resolution_fact_id`를 연결하고 `RESOLVED`한다.
- 직원이 제외할 때는 `dismissal_reason`을 요구한다.
- 같은 Case에서 같은 `semantic_key`의 활성 Gap은 하나만 허용한다.

### 4.3 AiSuggestion — AI 업무 제안

AI가 미확인 사항을 해결하거나 피해 확산을 막기 위해 제안한 작업이다. 아직 은행 업무가 아니다.

```text
AiSuggestion
  suggestion_id: string
  case_id: string
  suggestion_type: CUSTOMER_QUESTION | INSTITUTION_VERIFICATION |
                   TRANSACTION_REVIEW | PROTECTIVE_ACTION |
                   DOCUMENT_REQUEST | STAFF_REVIEW
  title: string
  rationale: string
  priority: URGENT | HIGH | NORMAL
  status: PROPOSED | ACCEPTED | DISMISSED | EXPIRED | SUPERSEDED
  related_gap_ids: string[]
  evidence_refs: EvidenceRef[]
  dedupe_key: string
  execution_mode: HUMAN_REVIEW_REQUIRED | AUTO_CUSTOMER_QUESTION_ALLOWED
  source_revision: integer
  model_version: string | null
  prompt_version: string | null
  accepted_task_id: string | null
  reviewed_by: string | null
  reviewed_at: datetime | null
  dismissal_reason: string | null
  created_at: datetime
  updated_at: datetime
```

규칙:

- 기본 실행 모드는 `HUMAN_REVIEW_REQUIRED`다.
- `ACCEPTED`되면 정확히 하나의 `CaseTask`를 생성하고 `accepted_task_id`를 연결한다.
- 직원이 내용을 고친 뒤 채택하면 원본 제안은 보존하고 생성된 업무에 수정 내용을 저장한다.
- `DISMISSED`된 제안의 `dedupe_key`는 동일 근거·동일 revision의 재생성을 막는 데 사용한다.
- `source_revision`보다 최신 데이터에서 근거가 사라지면 `SUPERSEDED` 또는 `EXPIRED` 처리한다.
- AI 제안은 고객에게 직접 공개하지 않는다.

선제적 고객 질문 예외:

`AUTO_CUSTOMER_QUESTION_ALLOWED`는 기존 기획의 긴급 질문 자동 발송을 위한 제한적 예외다. 다음 조건을 모두 만족해야 한다.

- 허용 목록에 있는 필수 안전 질문이다.
- 우선순위가 `URGENT`다.
- 같은 필드의 확정 사실, 답변 완료 질문, 대기 중 질문이 없다.
- 외부 금융 업무 실행이나 고객의 금전 이동을 요구하지 않는다.
- 민감한 은행 내부 정보나 다른 참여자의 개인정보를 포함하지 않는다.
- 정책 버전과 자동 발송 사유를 감사 로그에 기록한다.
- 자동 발송은 질문 카드 생성만 허용하며 사실 확정이나 업무 완료를 수행하지 않는다.

### 4.4 CaseTask — 담당자 업무

은행 직원이 실제로 수행하기로 결정한 업무다.

```text
CaseTask
  task_id: string
  case_id: string
  source: STAFF_CREATED | AI_SUGGESTION_ACCEPTED | SYSTEM_REQUIRED
  source_suggestion_id: string | null
  task_type: CUSTOMER_CONTACT | INSTITUTION_VERIFICATION |
             TRANSACTION_REVIEW | PROTECTIVE_ACTION |
             DOCUMENT_REVIEW | OTHER
  title: string
  description: string
  priority: URGENT | HIGH | NORMAL
  status: TODO | IN_PROGRESS | BLOCKED | COMPLETED | CANCELLED
  assignee_user_id: string | null
  due_at: datetime | null
  related_gap_ids: string[]
  related_verification_ids: string[]
  result_code: string | null
  result_summary: string | null
  evidence_refs: EvidenceRef[]
  customer_visibility: INTERNAL_ONLY | RESULT_SHAREABLE | RESULT_PUBLISHED
  completed_by: string | null
  completed_at: datetime | null
  cancellation_reason: string | null
  version: integer
  created_by: string
  created_at: datetime
  updated_at: datetime
```

규칙:

- AI는 `CaseTask`를 직접 생성하지 않는다. 직원 채택 또는 승인된 시스템 정책을 거친다.
- `COMPLETED`에는 `result_summary`, `completed_by`, `completed_at`이 필요하다.
- 외부 금융 절차는 공식 연동 결과나 직원 확인 없이 `COMPLETED`로 만들 수 없다.
- 업무 완료 결과가 사실을 포함하면 별도의 `PROPOSED CaseFact`를 생성한다.
- 고객에게 결과를 보여주려면 별도의 공개 승인 상태를 거친다.
- 완료·취소 항목은 숨김 목록으로 보낼 수 있지만 DB에서 삭제하지 않는다.

### 4.5 DecisionRecord — 판단·결정 이력

직원이 왜 업무를 채택·보류·취소하거나 사실을 확정했는지 기록하는 감사 엔터티다.

```text
DecisionRecord
  decision_id: string
  case_id: string
  decision_type: FACT_REVIEW | TASK_DECISION | CASE_STATUS |
                 CUSTOMER_DISCLOSURE | OTHER
  title: string
  rationale: string
  related_entity_type: FACT | GAP | SUGGESTION | TASK | VERIFICATION | CASE
  related_entity_id: string
  visibility: BANK_INTERNAL | CUSTOMER_SHAREABLE
  actor_user_id: string
  supersedes_decision_id: string | null
  created_at: datetime
```

규칙:

- 체크박스 상태를 갖지 않는다.
- 작성 후 직접 덮어쓰지 않는다. 정정은 새 기록과 `supersedes_decision_id`로 남긴다.
- AI는 DecisionRecord의 작성자가 될 수 없다.
- 개인 메모와 다르다. 사건 인계와 감사에 필요한 공식 기록만 저장한다.

### 4.6 EvidenceRef — 근거 참조

```text
EvidenceRef
  type: MESSAGE | QUESTION_ANSWER | BANK_TRANSACTION |
        VERIFICATION_RESULT | ATTACHMENT | STRUCTURED_SIGNAL |
        STAFF_RECORD
  id: string
  revision: integer | null
```

- 근거 원문을 복제하지 않고 기존 저장 레코드의 ID를 참조한다.
- RAG 검색 결과도 출처 ID와 revision을 통해 추적한다.
- 접근 권한이 없는 근거는 고객용 projection에 포함하지 않는다.

## 5. 상태 전이

### Fact

```text
PROPOSED ──직원/기관 검토──> CONFIRMED
    ├────근거 부족/오류────> REJECTED
    └────새 사실로 대체────> SUPERSEDED

CONFIRMED ──정정 사실 생성──> SUPERSEDED
```

### Gap

```text
OPEN ──질문 발송──> AWAITING_CUSTOMER
OPEN ──기관 확인──> AWAITING_INSTITUTION
답변/결과 도착 ──> STAFF_REVIEW_REQUIRED
CONFIRMED Fact 연결 ──> RESOLVED
직원 사유 입력 ──> DISMISSED
```

### AI Suggestion

```text
PROPOSED ──직원 채택──> ACCEPTED ──> CaseTask 생성
    ├────직원 제외────> DISMISSED
    ├────근거 만료────> EXPIRED
    └────새 제안 대체──> SUPERSEDED
```

### Task

```text
TODO ──> IN_PROGRESS ──> COMPLETED
  ├────> BLOCKED ──────┘
  └────> CANCELLED
```

## 6. 사건 맥락 화면용 Projection

Frontend는 원시 엔터티를 조합하지 않고 General API가 만든 은행용 projection을 받는다.

```text
CaseContextViewV2
  schema_version: case-context.v2
  case_id: string
  source_revision: integer
  projection_revision: integer | null
  projection_status: CURRENT | UPDATING | STALE | FAILED | UNCACHED
  generated_by: LLM | DETERMINISTIC_FALLBACK | LAST_SUCCESS
  generated_at: datetime | null

  summary_bullets: ContextBullet[]          # 최대 4개
  customer_exposure: ContextItem[]
  key_signals: ContextItem[]
  offender_claims: ContextItem[]
  offender_demands: ContextItem[]
  manipulation_tactics: ContextItem[]

  confirmed_facts: CaseFactView[]
  proposed_facts: CaseFactView[]
  open_gaps: CaseGapView[]
  ai_suggestions: AiSuggestionView[]
  active_tasks: CaseTaskView[]
  archived_tasks: CaseTaskView[]
  verification_tasks: VerificationView[]
  recent_decisions: DecisionRecordView[]
```

Projection 규칙:

- `summary_bullets`는 과거 문장을 누적하지 않고 최신 상태로 매번 교체한다.
- 직원이 수정한 표시 overlay와 AI projection을 분리하며 직원 수정본을 우선 표시한다.
- AI 제안과 담당자 업무를 같은 배열에 넣지 않는다.
- 미확인 사항과 확정 사실을 동시에 활성 상태로 표시하지 않는다.
- 완료·취소 업무는 기본 접기 처리하며 언제든 복원 가능한 이력을 유지한다.
- `generated_by`를 이용해 실제 LLM 결과와 규칙 fallback을 구분한다.

## 7. AI 입력·출력 계약

### AI 입력

AI는 다음의 구조화된 최소 데이터만 받는다.

- privacy-safe 진단 피처
- 확인된 사실과 검토 중 사실 후보
- 활성 미확인 사항
- 질문 상태와 구조화된 답변
- 기관 확인 상태와 결과 요약
- 담당자 업무 상태와 결과 요약
- 직원 결정 중 AI가 참조하도록 허용된 사건 관련 결론
- 기존 AI 제안의 채택·제외 상태와 `dedupe_key`
- 현재 `context_revision`

AI 입력에서 제외한다.

- 원문 통화 전체
- 개인 메모
- 고객에게 공개할 수 없는 다른 사용자의 개인정보
- API 키, 인증정보, 내부 라우팅 정보
- 검색 문서에 포함된 행동 지시문

### AI 출력

```text
CaseContextAiProposalV2
  source_revision: integer
  summary_bullets: ProposedContextBullet[]
  context_items: ProposedContextItem[]
  proposed_gap_upserts: ProposedGap[]
  proposed_suggestions: ProposedSuggestion[]
  obsolete_suggestion_ids: string[]
  warnings: string[]
  model_version: string
  prompt_version: string
```

AI가 출력할 수 없는 것:

- 확정 사실 생성
- 기존 사실의 직접 삭제
- 담당자 업무 완료
- 피해구제·지급정지·신고 완료 표시
- 직원 DecisionRecord 작성
- 고객 공개 승인

General API는 AI 출력 적용 전 다음을 검사한다.

1. `source_revision`이 현재 Case revision과 같은지
2. 기존 확정 사실이나 답변 완료 질문과 충돌하는지
3. 동일 `semantic_key` 또는 `dedupe_key`가 존재하는지
4. 직원이 제외하거나 수정한 항목인지
5. 사용자가 볼 수 없는 내부 코드와 데이터가 포함됐는지
6. 필드 길이, 허용 enum, 근거 참조 권한을 만족하는지

## 8. RAG 중복 방지 계약

RAG는 구조화 검사를 대체하지 않고 두 번째 방어 계층으로만 사용한다.

검사 순서:

1. 같은 `semantic_key`의 확정 사실 확인
2. 같은 필드의 대기·답변 완료 질문 확인
3. 같은 `dedupe_key`의 활성·제외 제안 확인
4. 같은 Case와 허용 공개 범위 안에서 의미 유사도 검색
5. 검색 결과를 근거로 사용하되 자동 상태 변경은 금지

색인 레코드:

```text
CaseKnowledgeIndexRecord
  index_id: string
  case_id: string
  entity_type: FACT | QUESTION | ANSWER | GAP | VERIFICATION | TASK_RESULT
  entity_id: string
  semantic_key: string | null
  normalized_text: string
  status: string
  visibility: BANK_INTERNAL | CUSTOMER_SHARED
  source_revision: integer
  content_hash: string
  embedding_model_version: string
  indexed_at: datetime
```

- 삭제·대체·비공개 변경 시 해당 색인을 무효화한다.
- 유사도가 높아도 상태와 출처를 함께 확인한다.
- 임계값만으로 질문을 자동 차단하지 않고 구조화 상태를 우선한다.

## 9. 목표 API 경계

구현된 General API 경계는 다음과 같다. 현재 화면 전환 전이므로 기존 API와 병행한다.

```text
GET    /api/cases/{case_id}/context-v2/resources
GET    /api/cases/{case_id}/context-v2/workspace
POST   /api/cases/{case_id}/context-v2/legacy-suggestions/{action_id}/review

POST   /api/cases/{case_id}/context-v2/facts
PATCH  /api/cases/{case_id}/context-v2/facts/{fact_id}/review

POST   /api/cases/{case_id}/context-v2/gaps
PATCH  /api/cases/{case_id}/context-v2/gaps/{gap_id}

PATCH  /api/cases/{case_id}/context-v2/suggestions/{suggestion_id}/review

POST   /api/cases/{case_id}/context-v2/tasks
PATCH  /api/cases/{case_id}/context-v2/tasks/{task_id}
POST   /api/cases/{case_id}/context-v2/tasks/{task_id}/complete
POST   /api/cases/{case_id}/context-v2/tasks/{task_id}/cancel

POST   /api/cases/{case_id}/context-v2/decisions
```

- 역할 모드(`MVP_OPEN_PERMISSIONS=0` 또는 미설정)에서는 리소스 조회를 Case 참여자에게만 허용하며, 열람자는 읽기만 가능하다.
- 역할 모드에서는 상담 담당자가 후보·Gap·업무를 작성할 수 있고, 메인 담당자/검토자만 확정·채택·완료·결정 기록을 수행한다.
- 2026-09-05 사용자 승인 예외: 로컬 MVP 테스트는 `MVP_OPEN_PERMISSIONS=1`로 모든 은행 사용자에게 작성·검토를 허용한다. 저장된 참여자 역할을 변경하지 않으며 고객/AI의 은행 업무 권한, 고객 공개 범위, 관리자 암호, version·결과 필수값 검사는 확대하거나 해제하지 않는다. 실제 인증이 아니므로 외부 공개 운영에 사용하지 않는다.
- 실제 인증 세션 도입 전까지 `actor_user_id` query parameter와 Case 참여자 레코드로 임시 권한을 검사한다. 클라이언트 actor 값을 신뢰하는 현재 방식은 운영용 인증이 아니다.
- 범용 Action PATCH 하나로 사실·제안·업무·판단 상태를 모두 처리하지 않는다.
- 각 명령은 전용 감사 이력을 기록하고 `context_revision`을 증가시킨다.
- `client_request_id`가 있는 생성 명령은 멱등 처리하며, 수정 명령은 `expected_version` 충돌 시 409를 반환한다.
- AI 제안 채택과 Staff Task 생성은 한 트랜잭션으로 처리한다.
- workspace 조회는 저장 상태를 분류하고 기존 기록을 별도 호환 영역에 표시한다. 조회 자체는 이관·확정·업무 생성을 하지 않는다.
- 기존 AI 제안은 원본 Action ID로 중복 방지하며 채택·제외 후에도 동일 원본의 재채택으로 업무를 추가 생성하지 않는다.
- 완료·취소 업무는 명시적으로 TODO로 다시 진행할 수 있다. 이전 결과·취소 사유는 감사 이력에 남기며 현재 완료 표시를 해제한다.

## 10. 권한 기준

| 행위 | AI | 고객 | 은행 직원 | 메인 담당자/승인권자 |
|---|---:|---:|---:|---:|
| 사실 후보 제안 | 가능 | 답변을 통해 가능 | 가능 | 가능 |
| 사실 확정·거절 | 불가 | 불가 | 역할에 따라 가능 | 가능 |
| 미확인 사항 제안 | 가능 | 불가 | 가능 | 가능 |
| AI 제안 채택·제외 | 불가 | 불가 | 가능 | 가능 |
| 담당자 업무 생성·수정 | 불가 | 불가 | 가능 | 가능 |
| 외부 업무 완료 승인 | 불가 | 불가 | 제한 | 가능 |
| 판단·결정 기록 | 불가 | 불가 | 가능 | 가능 |
| 고객 공개 승인 | 불가 | 불가 | 제한 | 가능 |

현재 고정 사용자 ID와 공용 관리자 암호는 이 목표 권한을 충족하지 않는다. 실제 구현은 인증·RBAC 계약과 함께 진행한다.

## 11. 기존 데이터 호환·이행 원칙

기존 데이터를 파괴적으로 변환하지 않는다.

| 기존 데이터 | 목표 데이터 | 이행 원칙 |
|---|---|---|
| `case_facts.CONFIRMED` | `CaseFact.CONFIRMED` | 출처·확인자·근거가 부족하면 `legacy` 표시 후 직원 보완 |
| `case_facts.PROPOSED` | `CaseFact.PROPOSED` | 그대로 사실 후보로 이관 |
| snapshot `unresolved_items` | `CaseGap` | semantic key별 활성 Gap 생성 후보 |
| `AI_CHECKLIST:*` Action | `AiSuggestion` | 열린 항목만 제안 후보로 이관; 완료 의미는 자동 추정하지 않음 |
| snapshot `next_actions` | 없음 | projection 파생값이므로 직접 이관하지 않음 |
| `STAFF_JUDGMENT` Action | Task 또는 Decision | 문장만으로 자동 분류하지 않고 `LEGACY_REVIEW_REQUIRED`로 표시 |
| `verification_tasks` | 기존 Verification + Task 연결 | 기존 결과와 version을 유지 |
| `case_context_items` | 직원 표시 overlay | 기존 직원 수정·숨김 이력 유지 |

단계적 적용 순서:

1. 새 enum·테이블·계약을 additive migration으로 추가한다.
2. 기존 읽기 경로를 유지한 채 새 projection을 내부에서 비교 생성한다.
3. legacy Action을 자동 확정하지 않고 검토 대기 상태로 매핑한다.
4. General API의 새 리소스별 command를 추가하고 계약 테스트를 만든다.
5. Frontend를 `사실 현황 / AI 제안 / 담당자 업무 / 결정 이력` 구조로 전환한다.
6. 실제 브라우저·MySQL E2E 후 기존 표시 경로를 제거한다.
7. 이 계약이 안정된 뒤 실제 LLM 재요약과 RAG를 연결한다.

## 12. 구현 전 승인 체크리스트

- [x] 사실 후보와 확정 사실의 승인 주체를 역할별로 확정
  - 상담 담당자는 후보를 만들 수 있고, 메인 담당자와 검토자가 확정·거절한다. 열람자는 조회만 한다.
- [x] Gap 자동 해소 조건과 직원 제외 사유 정책 확정
  - 동일 `semantic_key`의 확정 사실 연결 시에만 자동 해소한다. 수동 제외에는 사유를 필수로 남긴다.
- [x] AI 제안 자동 질문 허용 필드와 정책 버전 확정
  - `transfer_status`, `personal_information_exposure`, `authentication_information_exposure`, `remote_control_app`만 `auto-question.v1` 정책에서 허용한다.
- [x] 외부 금융 업무의 완료 승인자와 공식 결과 근거 확정
  - 메인 담당자가 확인 시각과 접수번호·거래 기록·기관 결과 중 하나를 근거로 승인한다.
- [x] 고객 공개 가능 Fact·Task 결과의 범위 확정
  - 명시적으로 `CUSTOMER_SHARED` 또는 `RESULT_PUBLISHED` 승인된 최소 결과만 공개하고 인증정보·내부 메모·직원 개인정보는 제외한다.
- [x] `semantic_key`, `dedupe_key` 표준과 사용자 표시 사전 확정
  - semantic key는 점으로 구분한 안정 키를 사용하고, dedupe key는 제안 유형·Gap 키·근거 ID의 정규화 조합으로 만든다. 사용자 문구는 별도 한국어 사전을 사용한다.
- [x] legacy `STAFF_JUDGMENT` 분류 정책 확정
  - 자동으로 업무나 결정으로 확정하지 않고 `LEGACY_REVIEW_REQUIRED` 상태에서 직원이 분류한다.
- [x] 개인정보 보존 기간과 RAG 색인 삭제 정책 확정
  - RAG 색인은 원본 엔터티보다 오래 보관하지 않는다. 공개 범위 변경·대체·삭제 시 즉시 무효화하고, 휴지통 30일 만료 시 함께 영구 삭제한다.
- [x] additive DB migration과 rollback 계획 검토
  - 기존 테이블을 변경하지 않고 v2 테이블을 추가한다. 데이터 기록 전에는 테이블 제거 rollback이 가능하고, 기록 후에는 백업·기능 비활성화·검증 후 이관하는 비파괴 rollback만 허용한다.
- [x] Public API·AI internal API contract test fixture 작성 계획 검토
  - 상태 불변조건, extra field 거부, 고객 공개 범위, AI 금지 행위를 계약 테스트로 고정한다.

승인 이후에도 기존 표시 경로를 즉시 제거하지 않는다. 각 단계의 테스트가 실패하거나 기존 사건 데이터의 의미를 안전하게 이관할 수 없으면 다음 단계로 진행하지 않는다.
