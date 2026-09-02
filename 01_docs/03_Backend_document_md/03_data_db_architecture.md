# DB · 데이터 구조 구현 문서

> 기준 문서: [개발 구현 체크리스트 | Frontend · Backend API · MySQL](https://app.notion.com/p/3cdc753ff28a81f9b261c9d157543bac?pvs=204)  
> 목적: MySQL, Vector DB, RAG Source Registry, Case Evidence, Case Report 데이터의 저장 책임을 분리한다.

> **현재 구현 상태:** A=eom 책임 문서다. 실제 Migration은 `cases`, `case_inputs`, `analysis_segments`, `context_features`, `case_events`, `case_reports`, `case_report_sections`까지 존재한다. 이 중 Event는 `CASE_CREATED` 저장만 구현됐다. 아래 messages/questions/verification/actions/voice/official_contacts/knowledge_sources/case_evidence와 Vector DB는 목표 설계다.

---

## 1. 저장소 분리 원칙

```text
MySQL
= 사건의 사실·정확한 구조값·업무상태

Vector DB
= 공식문서 Chunk + Embedding + 검색 Metadata

RAG
= 현재 Case와 관련된 공식 근거를 검색하는 파이프라인

Case Report AI
= MySQL 사건정보 + RAG 근거를 종합해 LIVE/FINAL 보고서 작성
```

### 중요 원칙

- `case_id`가 사건 데이터의 핵심 연결키다.
- MySQL은 모든 Case 상태의 Single Source of Truth다.
- 공식 전화번호·URL 같은 정확값은 MySQL에서 조회한다.
- Vector DB는 공식문서 의미검색용이다.
- RAG 결과 중 실제 Case에서 사용한 근거는 `case_evidence`로 남긴다.
- AI는 DB를 직접 수정하지 않는다.
- Timeline은 덮어쓰는 메모가 아니라 Append Event Log로 관리한다.

---

## 2. MySQL 논리 테이블

아래 표는 최종 목표다. `구현`으로 표시되지 않은 테이블은 설계만 존재한다.

| Table | 핵심 저장내용 |
|---|---|
| `cases` | case_id, risk, mode, type, status, latest_summary, timestamps — **구현** |
| `case_inputs` | 최초 입력 텍스트, 샘플유형, 입력시각 — **구현** |
| `analysis_segments` | Window/segment index, 구간 텍스트, risk — **구현** |
| `context_features` | 사칭·권위·공포·긴급성·고립·송금요구·금액 등 — **구현** |
| `case_reports` | LIVE Report Root/Manifest, 선택적 Snapshot, FINAL Revision — **초기 LIVE만 구현** |
| `case_report_sections` | LIVE 보고서의 section_key별 현재 내용·Version — **초기 Section 구현** |
| `case_report_section_sources` | 각 LIVE Section의 근거 연결 |
| `case_report_sources` | FINAL/Snapshot Report의 근거 연결 |
| `messages` | Customer Agent·고객·은행 담당자 메시지 |
| `questions` | P0/P1/P2, target_field, status, approved_by, sent_at |
| `question_options` | 질문별 A/B/C 선택지, option_key, label, value, sort_order, version |
| `progress_items` | P0/Verification/Recovery 등 UI 진행도 항목별 상태·Version |
| `verification_tasks` | 검증 질문·대상·토큰·응답·검증상태 |
| `actions` | 은행조치·Takeover·Recovery 등 작업기록 |
| `voice_sessions` | case_id, session 상태, 참여자, 시작/종료 |
| `voice_transcript_segments` | session_id, case_id, speaker, text, final 여부, 시간정보 |
| `case_events` | Timeline Event, actor, type, payload, created_at — **Table과 CASE_CREATED만 구현** |
| `official_contacts` | 기관명, 역할, 연락용도, 대표번호, 신고채널, 공식 URL |
| `knowledge_sources` | RAG 원본문서 Registry |
| `case_evidence` | Case에서 실제 사용한 RAG Chunk·주장·근거·검증상태 |

> 컬럼의 정확한 타입·길이·Index는 노션에 확정되어 있지 않으므로 실제 Migration 설계에서 결정한다.

---

## 3. 핵심 관계

```text
cases
├─ case_inputs
├─ analysis_segments
├─ context_features
├─ case_reports
│   ├─ case_report_sections
│   │   └─ case_report_section_sources
│   └─ case_report_sources
├─ messages
├─ questions
│   └─ question_options
├─ progress_items
├─ verification_tasks
├─ actions
├─ voice_sessions
│   └─ voice_transcript_segments
├─ case_events
└─ case_evidence

knowledge_sources
└─ Vector DB Chunk source_id로 연결

official_contacts
└─ 기관/연락목적 기준 Backend에서 직접 조회
```

---

## 4. `cases`

### 역할

Case의 **현재 최신 상태**를 빠르게 조회하기 위한 기준 테이블.

노션 기준 핵심 필드:

```text
case_id
risk
mode
type
status
latest_summary
created_at
updated_at
```

### 원칙

- 상세 이력은 하위 테이블에 저장
- `cases`는 현재 상태 Snapshot 성격
- PREVENT / RECOVERY / CLOSED 등 Mode·상태 표현은 실제 구현 Enum 정의 시 확정

---

## 5. 분석 데이터

### `case_inputs`

```text
case_id
raw_text
sample_type
created_at
```

### `analysis_segments`

```text
segment_id
case_id
segment_index
text
risk
timestamp/text-span 관련 값
```

### `context_features`

정확히 검색해야 하는 핵심 Feature는 Column, 가변 부가정보는 JSON 사용을 검토한다.

예:

```text
case_id
segment_id (optional)
feature_name
feature_value
evidence
source_type
created_at
```

> 위 행 기반 구조는 구현 제안이며, Wide Table/JSON 구조 중 최종안은 DB 설계 시 확정한다.

---

## 6. Case Report 데이터

### `case_reports`

`case_reports`는 LIVE 보고서의 **Root/Manifest**, 필요 시 남기는 전체 Snapshot, 그리고 FINAL Revision을 관리한다.

매 작은 Event마다 전체 LIVE `structured_report`를 새 Version으로 저장하는 방식을 기본으로 하지 않는다.

노션 기준 필요한 개념:

```text
report_id
case_id
report_type       # LIVE / FINAL
status
version
revision
is_latest
structured_report
summary_text
source_snapshot
generated_at
finalized_at
```

### 버전 원칙

```text
Case VP-014
├─ LIVE Root
│   ├─ summary v2
│   ├─ risk_context v4
│   ├─ transfer_status v3
│   ├─ verification_status v7
│   └─ current_actions v5
└─ FINAL
    ├─ Revision 1
    └─ Revision 2 (필요한 경우)
```

- LIVE는 `case_report_sections`에서 Section별 독립 Version 관리
- 중요한 시점만 선택적으로 전체 Snapshot 저장 가능
- FINAL은 기존 확정본 덮어쓰기보다 Revision 추가
- `source_snapshot` 또는 동등 구조로 FINAL/Snapshot 생성 시점의 근거 목록을 남김

### `case_report_sources`

```text
report_id
source_type
source_id
evidence_text
```

`source_type` 예:

```text
STT
FEATURE
MESSAGE
VERIFICATION
RAG
ACTION
EVENT
```

---

### `case_report_sections`

```text
section_id
report_id
case_id
section_key
content_json / content_text
version
is_latest
updated_at
```

권장 `section_key` 예:

```text
summary
risk_context
transfer_status
exposure_status
verification_status
current_actions
unresolved_items
next_checks
```

변경된 Section만 새 Version으로 저장하고, 전체 LIVE 보고서 조회 시 최신 Section을 조합한다.

### `case_report_section_sources`

```text
section_id
source_type
source_id
evidence_text
```

Section 단위로 근거를 연결해 특정 문장/카드가 무엇을 근거로 갱신됐는지 추적한다.

## 7. Conversation / Question

### `messages`

```text
message_id
case_id
actor_type
content
created_at
```

`actor_type`은 고객 / Customer Agent / 은행 담당자 등을 구분할 수 있어야 한다.

### `questions`

노션 기준:

```text
question_id
case_id
priority          # P0 / P1 / P2
target_field
status
approved_by
sent_at
```

질문 원문·편집본·응답 연결 방식은 실제 Schema 설계에서 확정한다.

---

### `question_options`

```text
option_id
question_id
option_key
label
value
sort_order
version
is_active
```

질문 본문과 선택지를 분리하면 A/B/C 선택지만 독립 변경하거나 Frontend에서 필요한 질문의 선택지만 조회할 수 있다.

### `progress_items`

```text
progress_item_id
case_id
progress_group
progress_key
label
status
sort_order
completed_at
version
updated_at
```

예:

```text
P0 / transfer_status / 송금 여부 확인 / COMPLETED
P0 / remote_control / 원격제어 앱 여부 / PENDING
VERIFICATION / prosecutor_procedure / 공식절차 검증 / IN_PROGRESS
RECOVERY / payment_stop / 지급정지 요청 / COMPLETED
```

한 항목이 완료돼도 전체 Progress 객체를 덮어쓰지 않는다.

## 8. Verification / Action

### `verification_tasks`

저장 대상:

- 검증할 주장
- 대상
- token
- 질문
- 응답
- 검증상태
- 생성/완료시간

### `actions`

저장 대상:

- 은행 조치
- Human Takeover
- Resume AI
- Recovery 관련 작업
- actor
- timestamp

---

## 9. Voice Session / STT

### `voice_sessions`

- 반드시 `session_id`와 `case_id`를 함께 유지
- 참여자
- 상태
- 시작시각
- 종료시각
- 상담요약 연결정보

### `voice_transcript_segments`

- DB에는 Final Segment 중심 저장
- Partial Transcript는 실시간 화면 표시용으로 사용할 수 있음

필요 개념:

```text
segment_id
session_id
case_id
speaker
text
is_final
started_at
ended_at
created_at
```

원본 음성 저장 여부는 STT·구조화 결과와 분리된 별도 보관정책으로 결정한다.

---

## 10. Timeline / Event Log

### `case_events`

```text
event_id
case_id
actor
type
payload
created_at
```

Append-only 이벤트 흐름으로 사용하는 것을 기본 원칙으로 한다.

예:

```text
CASE_CREATED
VOICE_TRANSCRIPT_UPDATED
VOICE_ANALYSIS_UPDATED
VERIFICATION_UPDATED
BANK_ACTION_ADDED
CASE_REPORT_UPDATED
CASE_REPORT_FINALIZED
RECOVERY_STARTED
```

---

## 11. 공식 연락처 DB

### `official_contacts`

공식 연락처는 RAG가 아니라 **MySQL 정확값 조회**를 우선한다.

노션 기준 권장 필드:

```text
agency_id
agency_name
agency_type
contact_purpose
phone
website
report_url
available_hours
source_url
last_verified_at
status
```

### 사용 흐름

```text
Case에서 검찰 사칭 확인
 → Backend가 official_contacts 조회
 → 현재 유효한 공식 연락처 반환
```

LLM이 기억으로 전화번호를 생성하는 방식은 사용하지 않는다.

---

## 12. RAG Source Registry

### `knowledge_sources`

Vector DB에 적재된 공식문서의 원본 출처를 MySQL에서 관리한다.

```text
source_id
agency
title
document_type
topic
source_url
effective_date
last_verified_at
status
```

역할:

- 문서 출처 추적
- 최신성 확인
- 비활성/폐기 문서 필터
- Vector Chunk와 원본문서 연결

---

## 13. Vector DB

### 역할

공식기관 문서를 Chunk 단위로 분할·Embedding하여 **의미검색**한다.

```text
Vector DB
├─ 금융위원회
├─ 금융감독원
├─ 경찰
├─ 검찰
├─ 법원
├─ 은행 피해예방·피해구제 안내
└─ 통신·보안 대응 가이드
```

### Chunk Metadata

노션 기준:

```text
chunk_id
source_id
agency
document_type
topic
effective_date
source_url
text
embedding
```

### 원칙

- Source Metadata는 MySQL `knowledge_sources`
- 검색용 Chunk·Embedding은 Vector DB
- 오래된 문서가 검색되는 것을 막기 위해 `effective_date`, `last_verified_at`, `status` 기반 필터 고려

---

## 14. `case_evidence`

특정 사건에 실제 사용된 RAG 근거를 저장한다.

노션 기준 저장 개념:

```text
case_id
source_id
chunk_id
claim
evidence
verification_status
retrieval_score
```

이를 통해:

- 어떤 공식근거가 사용됐는지
- Case Report가 무엇을 근거로 작성됐는지
- 검증 결과가 어디서 왔는지

를 추적할 수 있다.

---

## 15. 데이터 흐름

```text
Frontend 입력
   ↓
Backend
   ↓
AI 분석
   ↓
analysis_segments / context_features
   ↓
Case Report AI
   ↓
case_reports
   ↓
고객답변 / STT / Verification / Action 추가
   ↓
각 하위 Table + case_events
   ↓
Case Report LIVE 새 버전
   ↓
사건 종료
   ↓
FINAL Report
```

RAG:

```text
Case 질문
   ↓
AI RAG
   ↓
Vector DB
   ↓
공식 Chunk
   ↓
AI 구조화
   ↓
Backend
   ↓
case_evidence 저장
   ↓
필요 시 case_reports 갱신
```

---

## 16. Fragment / Delta 저장 원칙

### Mutability 구분

```text
Append 중심
- case_events
- voice_transcript_segments
- messages
- actions

Item Patch 중심
- questions
- question_options
- progress_items
- verification_tasks
- cases 일부 Field

Section Version 중심
- case_report_sections

Immutable / Revision 중심
- FINAL case_reports
```

### Version / 동시성

변경 가능한 조각에는 다음 중 하나를 둔다.

```text
version
updated_at
etag/hash (선택)
```

Backend는 Client/AI가 보낸 `base_version`과 DB 최신 Version이 맞는지 확인해 오래된 Patch가 최신값을 덮어쓰지 않게 한다.

### 초기 조회와 증분 조회

- 초기 진입: 필요한 전체 Projection/Bundle 조회
- 이후: cursor/event 기반 증분 조회 또는 SSE/WebSocket
- Timeline: `after=cursor`
- Report: 변경된 `section_key`
- Progress: 변경된 `item_id`
- Question: 변경된 `question_id` / `option_id`

---

## 17. DB 구현 체크리스트

- [ ] MySQL Schema 작성
- [ ] Migration 적용
- [ ] 모든 하위 Table `case_id` FK
- [ ] Voice Table에 `session_id` + `case_id`
- [ ] 생성/수정시각
- [ ] `case_report_sections`
- [ ] `case_report_section_sources`
- [ ] Report LIVE Section별 버전 관리
- [ ] FINAL Revision 관리
- [ ] Report ↔ Source 근거 연결
- [ ] STT Final Segment 저장
- [ ] Event Append 구조
- [ ] official_contacts Seed
- [ ] knowledge_sources Registry
- [ ] Vector DB Index
- [ ] case_evidence 저장
- [ ] 최신성/상태 Metadata 관리
- [ ] 필요한 Index 설계
- [ ] 개인정보·민감정보 저장범위 검토

---

## 18. SQL DDL 작성 전 확정 필요

노션에는 정확한 SQL 데이터 타입, 인덱스, FK Cascade 정책이 확정되어 있지 않다. 따라서 다음은 DB 구현 시 결정한다.

- PK 타입
- UUID vs 숫자 ID
- VARCHAR 길이
- JSON Column 사용범위
- ENUM 사용 여부
- 인덱스
- FK Delete/Update Policy
- 암호화 대상 Column
- Retention / 삭제 정책
