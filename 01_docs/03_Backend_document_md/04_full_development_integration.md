# 전체 개발 작업 및 연동 문서

> 기준 문서: [개발 구현 체크리스트 | Frontend · Backend API · MySQL](https://app.notion.com/p/3cdc753ff28a81f9b261c9d157543bac?pvs=204)  
> 목적: CSR Frontend부터 일반 Backend, AI API, MySQL, Vector DB, RAG, 음성상담, 실시간 동기화까지 전체 시스템의 개발·연동 순서를 한 문서에서 관리한다.

---

## 1. 전체 서비스 Route

```text
/
AI 통화 텍스트 진단
   ↓
/cases
생성된 Case 목록
   ↓
/cases/:caseId
선택 Case의 Entry & Role Selector
   ├─ /cases/:caseId/customer
   │    Customer Safety Room
   │
   ├─ /cases/:caseId/bank
   │    Fraud Case Workspace
   │
   └─ /verify/:token
        기관/외부 최소 검증
```

> 실제 Route는 `/cases/:caseId`이며 위 흐름을 기준으로 구현한다.

---

## 2. 시스템 전체 구조

```text
┌─────────────────────────────────────────────┐
│ CSR Frontend                                │
│ React SPA / Client Router                   │
│ Customer / Bank / Verification             │
└──────────────────┬──────────────────────────┘
                   │ REST + SSE/WebSocket
                   ▼
┌─────────────────────────────────────────────┐
│ 일반 Backend                               │
│ 결정론적 Workflow 통합·조정 계층             │
│ Case / 권한 / Session / Event / AI 호출     │
└───────┬────────────────┬────────────────────┘
        │                │
        │                └──────────────┐
        ▼                               ▼
┌───────────────┐              ┌──────────────────────┐
│ MySQL         │              │ AI API               │
│ Shared State  │              │ ML / LLM / STT       │
│ Exact Data    │              │ Case Report AI       │
└───────────────┘              │ RAG                  │
                               └──────────┬───────────┘
                                          │
                                          ▼
                               ┌──────────────────────┐
                               │ Vector DB            │
                               │ Official Documents   │
                               └──────────────────────┘
```

일반 Backend는 Event별 실행 DAG를 관리한다. 서로 독립적인 Full/Window 분석, 공식 연락처 조회/RAG 검색 등만 병렬 실행하고, Feature → Risk → Report처럼 선행 결과가 필요한 작업은 순차 실행한다. AI Agent 수를 늘리는 방식으로 병렬성을 확보하지 않는다.

---

## 3. CSR Frontend 원칙

- React SPA
- Client-Side Routing
- 페이지 진입 시 Backend API Data Fetching
- Loading / Empty / Error 상태
- 동일 Case 변경사항은 SSE/WebSocket 구독
- Frontend → 일반 Backend만 호출
- MySQL / AI API / Vector DB 직접 접근 금지

### Frontend 페이지

| ID | Route | 페이지 |
|---|---|---|
| FE-01 | `/` | AI 통화 텍스트 진단 |
| FE-02 | `/cases` | Case List |
| FE-03 | `/cases/:caseId` | Case Entry & Role Selector |
| FE-04 | `/cases/:caseId/customer` | Customer Safety Room |
| FE-05 | `/cases/:caseId/bank` | Fraud Case Workspace |
| FE-06 | `/verify/:token` | Verification Link |

---

## 4. 초기 Bundle + 이후 Delta 연동 원칙

```text
페이지 최초 진입
  ↓
Backend에서 초기 Bundle
  ├─ Case Header
  ├─ 최신 Report Section들
  ├─ 현재 Question + Options
  ├─ Progress Items
  ├─ 최근 Timeline
  └─ Verification / Action 요약
  ↓
CSR 화면 최초 렌더링

이후 변경
  ↓
Delta Event
  ↓
해당 Entity만 Client State / Query Cache 갱신
  ↓
해당 Component만 재렌더링
```

### 예시 1 — 질문 선택지

```text
Question q17 생성
  ↓
options A/B/C 저장
  ↓
QUESTION_UPDATED / QUESTION_OPTIONS_UPDATED
  ↓
Frontend의 현재 질문 Card만 갱신
```

### 예시 2 — LIVE Brief/Report

```text
새 Verification 결과
  ↓
verification_status Section만 영향
  ↓
Case Report AI가 해당 Section Patch
  ↓
case_report_sections 저장
  ↓
REPORT_SECTION_UPDATED
  ↓
은행 화면의 Verification/Brief 영역만 갱신
```

### 예시 3 — Progress

```text
원격제어 앱 확인 완료
  ↓
progress_item 한 건 COMPLETE
  ↓
PROGRESS_ITEM_UPDATED
  ↓
P0 4/6 → 5/6 및 해당 한 줄만 변경
```

### 예시 4 — Timeline

```text
은행 담당자 질문 전송
  ↓
case_events Event 1건 Append
  ↓
TIMELINE_EVENT_APPENDED
  ↓
기존 Timeline 유지 + 새 한 줄 추가
```

---

## 5. `/` 진단 E2E

```text
[일반 통화] [정상 금융 상담] [보이스피싱 사례]
                 또는
             직접 텍스트
                  ↓
              [진단하기]
                  ↓
POST /api/cases/analyze
                  ↓
일반 Backend
                  ↓
AI API
 ├─ 전체 분석
 ├─ Window 분석
 ├─ Feature 추출
 └─ Risk 분류
                  ↓
Case Report AI /initialize
                  ↓
일반 Backend
                  ↓
MySQL
 ├─ cases
 ├─ case_inputs
 ├─ analysis_segments
 ├─ context_features
 └─ case_reports
                  ↓
CASE_CREATED
                  ↓
/cases 또는 /cases/:caseId
```

---

## 6. Case 조회 E2E

```text
/cases
  ↓
GET /api/cases
  ↓
MySQL
  ↓
Case 목록

행 클릭
  ↓
/cases/:caseId
  ↓
GET /api/cases/:caseId
  ↓
Case Summary + LIVE Report
  ↓
[은행] [소비자] [기타/검증]
```

---

## 7. 고객 화면 E2E

```text
Customer Safety Room
   ↓
Case State + LIVE Report + Messages 조회
   ↓
P0 자동 긴급문진
   ↓
고객 답변
   ↓
Backend
   ├─ messages 저장
   ├─ case structure AI
   ├─ 필요 시 Feature 갱신
   ├─ Case Report AI update
   └─ Event Publish
   ↓
은행 Workspace 실시간 갱신
```

P1/P2 질문은 은행 담당자의 선택·편집·승인을 거쳐 고객에게 전달한다.

---

## 8. 은행 화면 E2E

```text
Fraud Case Workspace
   ↓
GET Case / Report / Feature / Message / Verification / Action
   ↓
P0 상태 모니터링
   ↓
P1/P2 Question Queue
   ↓
[선택] [편집] [전송] [직접질문]
   ↓
필요 시 Human Takeover
   ↓
은행 조치
   ↓
Backend
   ↓
MySQL + Case Event
   ↓
Case Report AI update
   ↓
고객/은행 화면 실시간 반영
```

---

## 9. 음성상담 E2E

고객 또는 은행 어느 쪽에서든 음성상담 시작 가능.

```text
[음성상담 시작]
   ↓
Backend Voice Session 생성
   ↓
WebRTC / RTC
   ↓
고객 ↔ 은행 담당자
   ↓
Audio Track / Chunk
   ↓
AI Streaming STT
   ↓
Final Transcript Segment
   ↓
MySQL transcript 저장
   ↓
AI Voice Delta Analysis
   ↓
Context Feature / Risk / Facts 갱신
   ↓
Case Report AI update
   ↓
Backend 저장
   ↓
VOICE_TRANSCRIPT_UPDATED
VOICE_ANALYSIS_UPDATED
CASE_REPORT_UPDATED
   ↓
고객·은행 CSR 화면 실시간 갱신
```

상담 종료:

```text
Voice Session End
 → Final Transcript
 → AI 상담 최종 요약
 → Case Report AI 갱신
 → 필요한 후속조치/질문 후보
 → MySQL
 → VOICE_SESSION_ENDED
```

---

## 10. Verification / RAG E2E

```text
Case에서 검증할 주장 발견
   ↓
Verification Planner
   ↓
RAG 필요?
   ├─ 공식 연락처 → MySQL official_contacts
   └─ 공식절차 근거 → Vector DB RAG
                          ↓
                     공식 Chunk 검색
                          ↓
                     근거 구조화
                          ↓
Backend
   ↓
case_evidence 저장
   ↓
Verification Status 갱신
   ↓
Case Report AI update
   ↓
Realtime UI 갱신
```

---

## 11. Case Report E2E

### LIVE

```text
Case Event
  ↓
Backend Trigger
  ↓
현재 Case State + 최근 변경 범위 수집
  ↓
POST /ai/reports/update
  ↓
Changed Section Patch
  ↓
Backend version/근거 검증
  ↓
case_report_sections 해당 section_key만 새 version
  ↓
case_report_section_sources
  ↓
REPORT_SECTION_UPDATED
  ↓
Customer / Bank의 해당 Component만 갱신
```

### FINAL

```text
사건 종료/해결
  ↓
POST /api/cases/:caseId/reports/finalize
  ↓
Backend 전체 Case 이력 조회
  ↓
POST /ai/reports/finalize
  ↓
FINAL Report
  ↓
DB FINALIZED 저장
  ↓
CASE_REPORT_FINALIZED
```

---

## 12. 데이터 저장 원칙

```text
정확한 현재 상태 / 사건이력       → MySQL
공식 연락처 / 공식 URL           → MySQL
공식문서 Source Registry         → MySQL
검색용 공식문서 Chunk/Embedding   → Vector DB
실제 Case에서 사용한 RAG 근거     → MySQL case_evidence
LIVE 사건 보고서 Section          → MySQL case_report_sections
FINAL/선택적 Snapshot               → MySQL case_reports
```

---

## 13. 권장 개발 순서

노션에 정의된 순서를 기준으로 정리한다.

1. [ ] MySQL Schema + Migration
2. [ ] `/` 진단 페이지 + `POST /api/cases/analyze`
3. [ ] `/cases` + Case Detail API
4. [ ] `/cases/:caseId` Role Selector
5. [ ] Customer Safety Room + messages/questions
6. [ ] Fraud Case Workspace + Question Queue
7. [ ] Verification Link
8. [ ] 일반 Backend / AI API 분리 및 내부 호출
9. [ ] Fragment/Delta API + Entity Version + Realtime Event 규격
10. [ ] `official_contacts` + `knowledge_sources` MySQL
11. [ ] 공식문서 수집·Chunking·Embedding + Vector DB
12. [ ] Verification RAG
13. [ ] 음성상담 Session + WebRTC/RTC + 실시간 STT
14. [ ] Transcript 증분 분석 + Live Feature/Brief
15. [ ] SSE/WebSocket Case 동기화
16. [ ] Human Takeover + Bank Actions
17. [ ] PREVENT → RECOVERY
18. [ ] Response / Recovery / Institution RAG
19. [ ] Demo Scenario 전체 E2E Test

### 추가로 반드시 포함할 작업

현재 AI/API·DB 섹션에 명시된 **Case Report AI** 구현을 위 개발순서에 함께 배치해야 한다.

권장 삽입 위치:

```text
초기 Diagnosis가 동작한 뒤
→ Case Report AI initialize

messages / voice / verification / action 연동 뒤
→ Case Report AI update

RECOVERY / 종료 처리 뒤
→ Case Report AI finalize
```

이 위치는 기존 기능 의존관계를 정리한 구현 배치이며, 노션의 Case Report AI 요구사항을 개발순서에 연결한 것이다.

---

## 14. E2E 완료조건

- [ ] 3종 샘플 + 직접 입력 진단
- [ ] 전체·Window 분석 저장
- [ ] Case List 재조회
- [ ] 동일 Case 고객/은행 화면 조회
- [ ] P0 자동질문
- [ ] P1/P2 승인형 질문
- [ ] Human Takeover
- [ ] 음성상담 시작/종료
- [ ] 실시간 STT
- [ ] Transcript → Feature 증분 분석
- [ ] LIVE Case Report 자동 갱신
- [ ] FINAL Case Report 확정
- [ ] Verification
- [ ] 공식 연락처 조회
- [ ] Verification RAG
- [ ] 은행 조치 기록
- [ ] PREVENT → RECOVERY
- [ ] SSE/WebSocket UI 동기화
- [ ] 재접속 후 최신 Case 복구
- [ ] 질문 선택지 A/B/C를 질문 단위로 독립 갱신
- [ ] Report Section 1개만 Patch되고 다른 Section은 유지
- [ ] Progress Item 1개 완료 시 전체 Progress를 덮어쓰지 않음
- [ ] Timeline Event 1건 Append 시 기존 Timeline 유지
- [ ] Realtime Event가 entity_type/entity_id/version을 포함

---

## 15. Demo 시나리오 권장 연결

```text
보이스피싱 샘플 진단
 → Case 생성
 → 고객 화면
 → P0 자동질문
 → 은행 화면에 답변 실시간 반영
 → 은행 P1 질문
 → 고객 응답
 → Verification RAG
 → 음성상담
 → STT / Feature / LIVE Report 갱신
 → 은행 조치
 → 피해 발생 여부에 따라 PREVENT 또는 RECOVERY
 → FINAL Report
```

---

## 16. 구현 전 확정이 필요한 공통 사항

- Backend / AI API 기술 스택
- 인증/인가
- SSE vs WebSocket
- RTC 방식
- STT/LLM/Embedding Provider
- Vector DB
- RAG Corpus 범위
- 개인정보/음성 Retention
- 실제 FDS/은행 연동 범위
- 배포 환경
- 로깅/모니터링
