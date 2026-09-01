# 일반 Backend 구현 구조

> 기준 문서: [개발 구현 체크리스트 | Frontend · Backend API · MySQL](https://app.notion.com/p/3cdc753ff28a81f9b261c9d157543bac?pvs=204)  
> 목적: CSR Frontend, AI API, MySQL, Vector/RAG 결과, 음성상담, 실시간 이벤트를 연결하는 **일반 Backend 통합·조정 계층**의 구현 범위를 정의한다.

---

## 1. 핵심 역할

일반 Backend는 단순 CRUD 서버가 아니라 서비스의 **통합·조정 계층(Orchestration Layer)** 이다.

이 Orchestration Layer는 별도의 자율 AI Agent가 아니라 **일반 Backend의 결정론적 Workflow 코드**로 구현한다. Event와 Case State에 따라 필요한 AI 작업만 선택하고, 의존성이 없는 작업은 병렬 실행하며, 권한·버전·저장·재시도·Event 발행은 일반 코드가 책임진다. 상세 실행 구조는 `ai_system_design/01_backend_workflow_orchestrator.md`를 따른다.

```text
CSR Frontend
    │
    │ REST / SSE / WebSocket
    ▼
일반 Backend API
    │
    ├─ MySQL
    │   ├─ Case / Input / Segment / Feature
    │   ├─ Report / Message / Question
    │   ├─ Verification / Action / Event
    │   ├─ Voice Session / Transcript
    │   └─ Official Contact / Knowledge Registry / Case Evidence
    │
    ├─ AI API
    │   ├─ Text Diagnosis / Window Analysis / ML Risk
    │   ├─ Context Feature Extraction
    │   ├─ Case Report AI
    │   ├─ Question / Verification Planning
    │   ├─ STT / Voice Analysis
    │   └─ RAG / Official Procedure Verification
    │
    └─ Realtime Publisher
        └─ 고객 화면 · 은행 화면 즉시 갱신
```

### 원칙

- Frontend는 **일반 Backend만 호출**한다.
- Frontend는 MySQL, Vector DB, AI API를 직접 호출하지 않는다.
- AI API는 MySQL을 직접 수정하지 않는다.
- AI API 결과는 일반 Backend가 받아 검증·정규화한 뒤 동일 `case_id`에 저장한다.
- DB 저장 성공 후 SSE/WebSocket Event를 발행한다.
- MySQL의 최신 Case State를 서비스의 기준 상태로 사용한다.

---


## 2. Fragment / Delta 기반 상태 전달 원칙

Frontend가 Case 전체를 매번 다시 받거나 다시 그리는 구조를 기본으로 하지 않는다.

- **최초 진입 / 새로고침 / 재접속**: 필요한 초기 State를 Bundle 형태로 조회 가능
- **이후 실시간 동작**: 변경된 조각만 Delta/Patch로 저장·전달
- 변경되지 않은 데이터는 재생성·재저장·재전송하지 않음
- 각 조각은 안정적인 `id` 또는 `key`를 가짐
- 변경 가능한 조각은 `version` 또는 동등한 동시성 제어값을 가짐
- Backend는 AI/API 결과를 그대로 통째로 교체하지 않고 변경 범위를 검증한 뒤 해당 Entity만 반영
- 저장 성공 후 해당 Entity를 특정할 수 있는 Realtime Event 발행

### Frontend에 노출되는 기본 조각

| 조각 | Backend/DB 단위 | Frontend 갱신 예 |
|---|---|---|
| 질문 | `question_id` | 현재 질문 문구만 변경 |
| 질문 선택지 | `option_id` / `option_key` | A/B/C 선택지만 교체 |
| LIVE Brief/Report | `section_key` | `verification_status` 섹션만 갱신 |
| 진행도 | `progress_item_id` | `P0_TRANSFER_STATUS` 한 줄만 완료 체크 |
| Timeline | `event_id` | 새 Event 한 줄 Append |
| Verification | `verification_task_id` | 해당 검증 카드만 상태 변경 |
| STT | `segment_id` | Final Transcript 한 줄 Append |
| Case Header | Field-level Patch | 담당자/Mode/상태만 변경 |
| Bank Action | `action_id` | 새 조치 한 건 추가 |

### 왜 필요한가

```text
잘못된 방식
새 STT 1줄
  ↓
Case 전체 재조회
  ↓
보고서 전체 재생성
  ↓
Timeline 전체 재전송
  ↓
Frontend 전체 재렌더링

권장 방식
새 STT 1줄
  ↓
Transcript Segment Append
  ↓
변경된 Feature만 Patch
  ↓
영향받는 Report Section만 Patch
  ↓
Timeline Event 1건 Append
  ↓
Frontend 해당 Component만 갱신
```

### 변경 Operation

```text
APPEND
UPSERT
PATCH
COMPLETE
INVALIDATE
DELETE   # 실제 필요할 때만
```

---

## 3. Backend 책임 체크리스트

- [ ] Frontend ↔ Backend REST API 연결
- [ ] Backend ↔ AI API 내부 호출 연결
- [ ] Backend ↔ MySQL 저장·조회·수정·버전관리
- [ ] Backend ↔ SSE/WebSocket 실시간 이벤트 연결
- [ ] Backend ↔ Voice Session / RTC 상태 관리
- [ ] 사용자·역할별 권한 검증
- [ ] AI 결과 Schema 검증
- [ ] 동일 `case_id` 기준 Shared Case State 병합
- [ ] 오류·재시도·Timeout 처리
- [ ] Case Event Append 및 감사 추적
- [ ] 재접속 시 MySQL 최신 상태 복구

---

## 4. 일반 요청 처리 흐름

```text
Frontend Action
   ↓
일반 Backend 요청 수신
   ↓
권한·입력값 검증
   ↓
필요 시 MySQL에서 현재 Case State 조회
   ↓
AI 처리가 필요한가?
   ├─ NO
   │   └─ DB 처리
   │
   └─ YES
       └─ AI API 호출
            ↓
       구조화 결과 반환
            ↓
일반 Backend가 결과 검증·병합
   ↓
MySQL 저장
   ↓
case_events Append
   ↓
SSE / WebSocket Event Publish
   ↓
CSR Frontend 관련 Component 갱신
```

---

## 5. Case / Diagnosis API

| Method | Path | 역할 |
|---|---|---|
| POST | `/api/cases/analyze` | 텍스트 진단 요청, AI 분석 호출, Case 생성 |
| GET | `/api/cases` | Case 목록 조회 |
| GET | `/api/cases/:caseId` | Case 상세 / Shared State 조회 |
| PATCH | `/api/cases/:caseId` | Mode·상태·담당자 변경 |

### `POST /api/cases/analyze` 처리 순서

```text
텍스트 입력
 → AI 전체 분석
 → AI Window 분석
 → Context Feature
 → ML Risk / 분류
 → Case Report AI 초기 보고서
 → Case 및 분석결과 MySQL 저장
 → CASE_CREATED Event
 → 생성 Case 반환
```

---

## 6. Analysis / Case Report API

| Method | Path | 역할 |
|---|---|---|
| GET | `/api/cases/:caseId/features` | Context Feature 조회 |
| GET | `/api/cases/:caseId/segments` | Window/Segment 분석 조회 |
| GET | `/api/cases/:caseId/reports/live` | 최신 Section들을 조합한 LIVE 보고서 Projection |
| GET | `/api/cases/:caseId/reports/live/sections` | LIVE 보고서 Section 목록 |
| GET | `/api/cases/:caseId/reports/live/sections/:sectionKey` | 특정 Section만 조회 |
| PATCH | `/api/cases/:caseId/reports/live/sections/:sectionKey` | 특정 Section만 갱신 |
| GET | `/api/cases/:caseId/reports/final` | FINAL 사건 보고서 |
| GET | `/api/cases/:caseId/reports` | 보고서 Snapshot/Revision 이력 |
| POST | `/api/cases/:caseId/reports/refresh` | 명시적으로 전체 재구성이 필요할 때만 LIVE 전체 Refresh |
| POST | `/api/cases/:caseId/reports/finalize` | 사건 종료 시 FINAL 보고서 생성·확정 |

### Case Report AI 갱신 Trigger

다음 주요 Event가 발생하면 일반 Backend가 Case Report AI 갱신을 요청한다.

- STT Final Segment 추가
- Context Feature 추가·변경
- 고객 답변 추가
- 은행 담당자 질문·답변 추가
- Verification 결과 변경
- RAG 근거 추가
- 금융조치 추가
- 피해 발생 / Recovery 전환
- 음성상담 종료
- 사건 상태 변경

LIVE 상황에서 AI API는 우선 **변경된 Section Patch**를 반환한다. 일반 Backend는 `section_key`별 Patch를 검증해 `case_report_sections`에 반영하고 해당 Section Event만 발행한다.

```text
REPORT_SECTION_UPDATED
CASE_REPORT_REFRESHED      # 전체 Refresh가 실제 발생한 경우
CASE_REPORT_FINALIZED
```

전체 LIVE 보고서는 최신 Section을 조합한 Projection이다. 매 이벤트마다 전체 보고서를 새로 생성·저장하는 방식을 기본으로 하지 않는다.

---

## 7. Customer Agent / Conversation API

| Method | Path | 역할 |
|---|---|---|
| GET | `/api/cases/:caseId/messages` | 전체 대화 조회 |
| POST | `/api/cases/:caseId/messages` | 고객·직원 메시지 저장 |
| GET | `/api/cases/:caseId/questions` | P0/P1/P2 질문 Queue |
| POST | `/api/cases/:caseId/questions/next` | 다음 자동 질문 요청 |
| PATCH | `/api/cases/:caseId/questions/:questionId` | 승인·편집·보류 |
| POST | `/api/cases/:caseId/questions/:questionId/send` | 고객에게 질문 전송 |
| POST | `/api/cases/:caseId/conversation/takeover` | Human Takeover |
| POST | `/api/cases/:caseId/conversation/resume-ai` | AI 대화 재개 |

### Fragment API

| Method | Path | 역할 |
|---|---|---|
| GET | `/api/cases/:caseId/questions/:questionId/options` | 특정 질문의 A/B/C 선택지 조회 |
| PATCH | `/api/cases/:caseId/questions/:questionId` | 질문 1개 상태·문구·답변 Field Patch |
| GET | `/api/cases/:caseId/progress` | 진행도 항목 목록 |
| PATCH | `/api/cases/:caseId/progress/:itemId` | 진행도 항목 1개만 상태변경 |
| GET | `/api/cases/:caseId/events?after=:cursor` | Timeline의 이후 Event만 증분 조회 |

초기 화면은 여러 Resource를 묶어 받을 수 있지만, 변경 동작은 가능한 한 위와 같은 Item 단위 API로 처리한다.

### 질문 운영 원칙

- P0: 표준 안전질문은 자동 실행
- P1/P2: 사건별 심화질문은 담당자 선택·편집·승인 후 전송
- 금융조치·고난도 판단·설득: Human Takeover

---

## 8. Verification API

| Method | Path | 역할 |
|---|---|---|
| POST | `/api/cases/:caseId/verifications` | 검증 Task 생성 |
| GET | `/api/cases/:caseId/verifications` | 검증현황 조회 |
| GET | `/api/verify/:token` | 외부 검증 질문 조회 |
| POST | `/api/verify/:token/respond` | 외부 검증 응답 저장 |

외부 검증자는 전체 Case가 아니라 필요한 최소 질문만 본다.

---

## 9. Bank Action / Recovery API

| Method | Path | 역할 |
|---|---|---|
| POST | `/api/cases/:caseId/actions` | 은행 모의조치 기록 |
| GET | `/api/cases/:caseId/actions` | 조치 이력 |
| POST | `/api/cases/:caseId/recovery/start` | RECOVERY Mode 전환 |
| PATCH | `/api/cases/:caseId/recovery/:taskId` | Recovery Task 상태 변경 |

금융조치의 최종 책임은 AI가 아니라 은행 담당자/업무 규칙에 둔다.

---

## 10. Voice Consultation / 음성상담 API

고객 또는 은행 담당자가 Case 화면에서 음성상담 버튼을 누르면 동일 `case_id`에 연결된 Voice Session을 생성한다.

| Method | Path | 역할 |
|---|---|---|
| POST | `/api/cases/:caseId/voice-sessions` | Voice Session 생성 |
| GET | `/api/cases/:caseId/voice-sessions/:sessionId` | 상태·참여자 조회 |
| POST | `/api/cases/:caseId/voice-sessions/:sessionId/join` | 상담 참여 |
| POST | `/api/cases/:caseId/voice-sessions/:sessionId/end` | 상담 종료 |
| GET | `/api/cases/:caseId/voice-sessions/:sessionId/transcript` | STT Transcript 조회 |
| GET | `/api/cases/:caseId/voice-sessions/:sessionId/summary` | 상담 요약·추출정보 조회 |

### 처리 흐름

```text
음성상담 시작
 → Voice Session 생성
 → 고객/은행 참여
 → Audio Track/Chunk 전달
 → AI STT
 → Final Transcript Segment
 → AI 증분 분석
 → Feature / Risk / Case Report 갱신
 → MySQL 저장
 → Realtime Event
 → 고객·은행 화면 갱신
```

### 구현 원칙

- 음성 통신: WebRTC 또는 관리형 RTC
- Backend: Session·권한·Signaling Metadata 관리
- 가능하면 고객/은행 Audio Track을 분리
- Mixed Audio만 있으면 AI Speaker Diarization 사용
- MVP 기본 저장은 원본 음성보다 STT·구조화 결과 중심
- 원본 음성 보관 여부와 보관기간은 별도 정책으로 확정

---

## 11. Official Contact / RAG 연결

정확한 연락처·URL은 AI가 생성하지 않고 MySQL에서 조회한다.

```text
Case
 → 사칭기관/필요기관 확인
 → Backend가 official_contacts 조회
 → 정확한 전화번호/URL 반환
```

공식 절차 확인이 필요한 경우:

```text
Backend
 → AI RAG API 호출
 → Vector DB 검색
 → 공식 근거 + Metadata 반환
 → Backend 검증
 → case_evidence 저장
 → 필요 시 Case Report AI 갱신
```

---

## 12. Realtime

- [ ] `GET /api/cases/:caseId/events`
- [ ] `/api/cases/:caseId/stream` 또는 동등 WebSocket Channel
- [ ] 저장 성공 후 Event Publish
- [ ] Event 수신 시 전체 페이지 새로고침 없이 관련 Component만 갱신
- [ ] 재접속 시 MySQL 최신 State 재조회

### Realtime Delta Event Envelope

```json
{
  "event_id": "evt_...",
  "case_id": "VP-014",
  "entity_type": "REPORT_SECTION",
  "entity_id": "verification_status",
  "operation": "PATCH",
  "changed_fields": ["content", "status"],
  "payload": {},
  "entity_version": 7,
  "case_version": 31,
  "occurred_at": "..."
}
```

Frontend는 `entity_type + entity_id + operation`을 기준으로 해당 Component만 갱신한다.

주요 Event 예시:

```text
CASE_CREATED
CASE_UPDATED
MESSAGE_ADDED
QUESTION_UPDATED
VERIFICATION_UPDATED
BANK_ACTION_ADDED
VOICE_SESSION_STARTED
VOICE_PARTICIPANT_JOINED
VOICE_TRANSCRIPT_UPDATED
VOICE_ANALYSIS_UPDATED
VOICE_SESSION_ENDED
REPORT_SECTION_UPDATED
QUESTION_UPDATED
QUESTION_OPTIONS_UPDATED
PROGRESS_ITEM_UPDATED
TIMELINE_EVENT_APPENDED
TRANSCRIPT_SEGMENT_ADDED
CASE_FIELD_UPDATED
CASE_REPORT_FINALIZED
RECOVERY_STARTED
```

---

## 13. 구현 시 아직 확정이 필요한 항목

노션에서 구체 기술값이 확정되지 않은 항목은 구현 단계에서 결정한다.

- Backend Framework / Language
- 인증 방식
- SSE vs WebSocket 최종 선택
- WebRTC 직접 구성 vs 관리형 RTC
- Queue/Worker 사용 여부
- AI API Timeout / Retry / Circuit Breaker 기준
- 원본 음성 보관 정책
- 실제 금융사·FDS 연동 범위

이 문서는 위 항목을 임의로 확정하지 않는다.
