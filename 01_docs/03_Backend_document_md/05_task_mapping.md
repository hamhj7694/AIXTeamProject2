# 작업 매핑 문서

> 기준 문서: [개발 구현 체크리스트 | Frontend · Backend API · MySQL](https://app.notion.com/p/3cdc753ff28a81f9b261c9d157543bac?pvs=204)  
> 목적: 프론트엔드·일반 Backend·AI API·DB/RAG·실시간 연동 작업의 **담당자 배정과 의존성 관리**에 사용한다.

> 이 문서는 공통 Task ID와 의존성의 기준이다. 실제 담당자 배정은 `team_work/00_task_catalog.md`, 개인 진행상황은 `team_work/{ham|eom|lee}/todo.md`에서 관리한다.

> 현재 배정 원칙은 **AI 계열(`AI`, AI 내부 Contract)=eom**, **Frontend·일반 Backend·서비스 DB·Realtime·통합(`FE`, `BE`, `DB`, `RT`, `INT`)=lee**다. ham은 현재 작업에서 제외한다. 아래 상세 표의 `TBD`는 공통 템플릿 값이며 실제 소유권은 `team_work/00_task_catalog.md`가 우선한다.

---

## 1. 작업 코드 규칙

```text
FE   = Frontend
BE   = 일반 Backend
AI   = AI API
DB   = MySQL / Vector DB / 데이터
RT   = Realtime / Voice
INT  = Integration / E2E
DOC  = 문서/설계
```

공통 Task 정의를 재사용하기 위해 상세 표의 담당자 칸은 템플릿으로 유지한다. 현재 담당자는 `team_work/00_task_catalog.md`에서 확정한다.

---

## 2. Frontend 매핑

| ID | 작업 | Route | 의존성 | 담당 | 상태 |
|---|---|---|---|---|---|
| FE-01 | 통화 텍스트 진단 | `/` | BE-01 | TBD | Notion 기준 UI 체크 완료 |
| FE-02 | Case List | `/cases` | BE-02 | TBD | Notion 기준 UI 체크 완료 |
| FE-03 | Case Role Selector | `/cases/:caseId` | BE-03 | TBD | Notion 기준 UI 체크 완료 |
| FE-04 | Customer Safety Room | `/cases/:caseId/customer` | BE-04, AI-05, RT-01 | TBD | Notion 기준 UI 체크 완료 |
| FE-05 | Fraud Case Workspace | `/cases/:caseId/bank` | BE-04~08, AI-05~08, RT-01 | TBD | Notion 기준 미완료 |
| FE-06 | Verification Link | `/verify/:token` | BE-05 | TBD | Notion 기준 UI 체크 완료 |
| FE-07 | 음성상담 UI | Customer/Bank | BE-09, AI-09, RT-02 | TBD | 추가 구현 필요 |
| FE-08 | LIVE/FINAL Report UI | Customer/Bank | BE-06, AI-05 | TBD | 추가 구현 필요 |
| FE-09 | Fragment State 적용 | 질문/선택지/Report Section/Progress/Timeline 부분 갱신 | BE-13, RT-06 | TBD | TODO |

---

## 3. 일반 Backend 매핑

| ID | 작업 | 주요 결과물 | 의존성 | 담당 | 상태 |
|---|---|---|---|---|---|
| BE-01 | Case Analyze API | `POST /api/cases/analyze` | AI-01~05, DB-01 | TBD | TODO |
| BE-02 | Case List API | `GET /api/cases` | DB-01 | TBD | TODO |
| BE-03 | Case Detail API | Shared State API | DB-01 | TBD | TODO |
| BE-04 | Conversation/Question API | messages/questions/takeover | DB-02, AI-06/08 | TBD | TODO |
| BE-05 | Verification API | token/respond | DB-04, AI-07 | TBD | TODO |
| BE-06 | Case Report API | live/final/history/refresh/finalize | DB-05, AI-05 | TBD | TODO |
| BE-07 | Bank Action/Recovery API | actions/recovery | DB-06 | TBD | TODO |
| BE-08 | Official Contact Service | MySQL 정확값 조회 | DB-09 | TBD | TODO |
| BE-09 | Voice Session API | create/join/end/transcript | DB-07, RT-02 | TBD | TODO |
| BE-10 | AI API Client Layer | 내부 호출/Schema 검증 | AI 전체 | TBD | TODO |
| BE-11 | Realtime Publisher | SSE/WebSocket publish | DB-08, RT-01 | TBD | TODO |
| BE-12 | Case Orchestration | Event → AI/DB/Realtime 조정 | BE 전체 | TBD | TODO |

---

## 4. AI API 매핑

| ID | 작업 | 주요 API/모델 | 입력 | 출력 | 담당 | 상태 |
|---|---|---|---|---|---|---|
| AI-01 | 전체 텍스트 분석 | `/ai/analyze/text` | 통화 텍스트 | 전체 맥락 | TBD | TODO |
| AI-02 | Window 분석 | `/ai/analyze/windows` | 통화 텍스트 | Segment 분석 | TBD | TODO |
| AI-03 | Context Feature | `/ai/features/extract` | 전체/Segment | Feature+evidence | TBD | TODO |
| AI-04 | Risk Model | `/ai/risk/predict` | Feature | Risk/분류 | TBD | TODO |
| AI-05 | Case Report AI | initialize/update/finalize | Case State + changed scope | LIVE Section Patch / FINAL Report | TBD | TODO |
| AI-06 | Question Planner | `/ai/questions/next` | Case State | P0/P1/P2 | TBD | TODO |
| AI-07 | Verification Planner | `/ai/verifications/plan` | Claim/Case | 검증계획 | TBD | TODO |
| AI-08 | Case Structurer | `/ai/case/structure` | 비정형 답변 | Shared Fields | TBD | TODO |
| AI-09 | Streaming STT | WS STT | Audio | Transcript | TBD | TODO |
| AI-10 | Voice Delta Analyzer | `/ai/voice/analyze-delta` | Final Segment | Feature 변화 | TBD | TODO |
| AI-11 | Voice Summarizer | `/ai/voice/summarize` | Transcript | 상담요약 | TBD | TODO |
| AI-12 | Verification RAG | `/ai/rag/verify-claim` | Claim | 공식 근거 | TBD | TODO |
| AI-13 | Response RAG | `/ai/rag/response-guide` | Case | 안전행동 근거 | TBD | TODO |
| AI-14 | Recovery RAG | `/ai/rag/recovery-guide` | Case | 피해구제 근거 | TBD | TODO |
| AI-15 | Institution RAG | `/ai/rag/institution-info` | 기관/질문 | 업무절차 근거 | TBD | TODO |
| AI-16 | Report Impact Router | 새 Event가 어떤 section_key에 영향주는지 판별 | Event + Case State | changed_sections | TBD | TODO |

---

## 5. DB / 데이터 매핑

| ID | 작업 | 대상 | 의존성 | 담당 | 상태 |
|---|---|---|---|---|---|
| DB-01 | Core Case Schema | cases, inputs, segments, features | - | TBD | TODO |
| DB-02 | Conversation Schema | messages, questions | DB-01 | TBD | TODO |
| DB-03 | Conversation 저장 로직 | messages/questions | BE-04 | TBD | TODO |
| DB-04 | Verification Schema | verification_tasks | DB-01 | TBD | TODO |
| DB-05 | Report Schema | case_reports, case_report_sources | DB-01 | TBD | TODO |
| DB-06 | Action/Recovery Schema | actions | DB-01 | TBD | TODO |
| DB-07 | Voice Schema | voice_sessions, transcript_segments | DB-01 | TBD | TODO |
| DB-08 | Event Schema | case_events | DB-01 | TBD | TODO |
| DB-09 | Official Contact | official_contacts | - | TBD | TODO |
| DB-10 | Knowledge Registry | knowledge_sources | - | TBD | TODO |
| DB-11 | Case Evidence | case_evidence | DB-01, DB-10 | TBD | TODO |
| DB-12 | Vector DB | Chunk/Embedding Index | DB-10 | TBD | TODO |
| DB-13 | Official Document Pipeline | 수집·정제·Chunk·Embedding | DB-10, DB-12 | TBD | TODO |
| DB-14 | Fragment State Schema | question_options, progress_items, report_sections | DB-01/05 | TBD | TODO |
| DB-15 | Report Section Sources | case_report_section_sources | DB-14 | TBD | TODO |

---

## 6. Realtime / Voice 매핑

| ID | 작업 | 설명 | 의존성 | 담당 | 상태 |
|---|---|---|---|---|---|
| RT-01 | Case Realtime Channel | SSE/WebSocket | BE-11, DB-08 | TBD | TODO |
| RT-02 | Voice RTC | WebRTC/관리형 RTC | BE-09 | TBD | TODO |
| RT-03 | Audio → STT 연결 | Track/Chunk → AI-09 | RT-02, AI-09 | TBD | TODO |
| RT-04 | STT → Case Update | Segment 저장·AI 증분분석 | DB-07, AI-10, BE-12 | TBD | TODO |
| RT-05 | Report Realtime | Report Event → UI | AI-05, BE-06, RT-01 | TBD | TODO |

---

## 7. 통합 작업 매핑

| ID | 작업 | 포함 영역 | 선행조건 | 담당 | 상태 |
|---|---|---|---|---|---|
| INT-01 | Text Diagnosis E2E | FE-01, BE-01, AI-01~05, DB-01/05 | Core Schema | TBD | TODO |
| INT-02 | Case Navigation E2E | FE-02/03, BE-02/03 | INT-01 | TBD | TODO |
| INT-03 | Customer Agent E2E | FE-04, BE-04, AI-06/08 | INT-02 | TBD | TODO |
| INT-04 | Bank Workspace E2E | FE-05, BE-04/07 | INT-03 | TBD | TODO |
| INT-05 | Verification E2E | FE-06, BE-05, AI-07/12 | DB-04/10/12 | TBD | TODO |
| INT-06 | Voice E2E | FE-07, BE-09, AI-09~11, RT-02~04 | Customer/Bank UI | TBD | TODO |
| INT-07 | Realtime Report E2E | FE-08, BE-06/11, AI-05 | INT-03/04/06 | TBD | TODO |
| INT-08 | Recovery E2E | Customer/Bank, BE-07 | Action Flow | TBD | TODO |
| INT-09 | Full Demo E2E | 전체 | INT-01~08 | TBD | TODO |
| INT-10 | Fragment Update E2E | 질문/Report/Progress/Timeline 부분 갱신 검증 | FE-09, BE-13/14, RT-06 | TBD | TODO |

---

## 8. 주요 의존성 그래프

```text
DB-01 Core Schema
 ├─ BE-01 Diagnosis
 ├─ BE-02/03 Case
 ├─ DB-02 Conversation
 ├─ DB-04 Verification
 ├─ DB-05 Report
 ├─ DB-06 Action
 ├─ DB-07 Voice
 └─ DB-08 Events

AI-01~04 Diagnosis
 └─ AI-05 Report initialize
      └─ INT-01

DB-10 Knowledge Registry
 └─ DB-12 Vector DB
      └─ AI-12 Verification RAG
           └─ INT-05

BE-09 + AI-09
 └─ RT-02/03
      └─ AI-10
           └─ AI-05 update
                └─ RT-05

BE-11 Realtime
 └─ Customer / Bank / Report UI 실시간 동기화
```

---

## 9. 담당자 배정용 복사 템플릿

```text
Task ID:
작업명:
담당자:
Reviewer:
선행작업:
예상 시작:
예상 완료:
Branch:
PR:
상태: TODO / IN_PROGRESS / REVIEW / DONE / BLOCKED
차단요인:
테스트 결과:
비고:
```

---

## 10. Definition of Done 공통 기준

각 Task는 최소 다음이 충족돼야 DONE으로 변경한다.

- [ ] 구현 완료
- [ ] 입력/출력 Schema 확인
- [ ] Error 처리
- [ ] 테스트
- [ ] 연동 대상과 E2E 확인
- [ ] 환경변수/설정 분리
- [ ] 민감정보 로그 노출 확인
- [ ] README 또는 API 문서 갱신
- [ ] PR/Review 완료


## 11. Fragment Update 의존성

```text
DB-14 Fragment State
 ├─ question_options
 ├─ progress_items
 └─ case_report_sections
      ↓
BE-13 Fragment/Delta API
      ↓
BE-14 Version Control
      ↓
RT-06 Delta Event Envelope
      ↓
FE-09 Fragment State
      ↓
INT-10 Fragment Update E2E

AI-05 Case Report AI
 └─ AI-16 Report Impact Router
      └─ changed section patch
           └─ DB-14 → RT-06 → FE-09
```
