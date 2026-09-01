# 작업 진행내역 · TODO

> 기준 문서: [개발 구현 체크리스트 | Frontend · Backend API · MySQL](https://app.notion.com/p/3cdc753ff28a81f9b261c9d157543bac?pvs=204)  
> 이 문서는 **노션에 표시된 체크 상태를 출발점**으로 사용한다. 노션에서 완료가 명시되지 않은 Backend/AI/DB 작업은 임의로 완료 처리하지 않는다.

---

## 0. 상태 정의

```text
[x] DONE       = 노션에서 완료 체크됨
[ ] TODO       = 노션에서 미완료
[-] PARTIAL    = 일부 화면/설계는 있으나 연동 미완료
[?] UNKNOWN    = 노션만으로 진행상태 판단 불가
```

---

## 1. Frontend 현재 상태

### FE-01 `/` — AI 통화 텍스트 진단

- [x] Textarea
- [x] 직접 텍스트 입력
- [x] 일반 통화 샘플
- [x] 정상 금융 상담 샘플
- [x] 보이스피싱 사례 샘플
- [x] 진단하기 CTA
- [x] 리스트 보기
- [x] Loading
- [x] Error 처리
- [x] 진단 후 Case 이동 흐름

> **주의:** 화면 체크가 완료됐다는 의미이며 Backend/AI 실제 연동 완료 여부는 별도 확인 필요.

### FE-02 `/cases` — Case List

- [x] 목록 UI
- [x] 피해여부/유형/금액/상태
- [x] 생성/최근 업데이트 시각
- [x] 검색/필터
- [x] 날짜 검색
- [x] 행 클릭 이동
- [x] 새 진단
- [x] 요약 컬럼

### FE-03 `/cases/:caseId` — Role Selector

- [x] Case Summary
- [x] Mode/유형/최근 업데이트
- [x] 초기 Brief
- [x] 은행 화면 진입
- [x] 소비자 화면 진입
- [x] 기타/검증 진입
- [x] Case List 복귀

### FE-04 Customer Safety Room

- [x] 위험/Mode Banner
- [x] 초기 위험 Brief
- [x] 우선 행동
- [x] Customer Agent Chat
- [x] P0 자동 긴급문진 UI
- [x] 카드형 답변 + 자유입력
- [x] 파일/사진
- [x] 검증상태
- [x] 은행 확인/조치상태
- [x] Human 담당자 표시
- [x] Recovery 진입 UI
- [x] 파일/이미지/마이크 UI
- [x] 대화 전체 스크롤
- [x] 직원/AI 발화 구분

### FE-05 Fraud Case Workspace

노션 기준 미완료 항목:

- [ ] Case Header / Mode / 담당자
- [ ] Live Case Brief
- [ ] 최근 변경사항
- [ ] FDS Snapshot
- [ ] P0 Auto Triage
- [ ] P1/P2 Question Queue
- [ ] 질문 선택·편집·전송·보류
- [ ] 직접 질문
- [ ] Verification Matrix
- [ ] Customer Conversation Monitor
- [ ] 전체 대화
- [ ] Monitor / Co-pilot / Human Takeover / Resume AI
- [ ] Live Timeline
- [ ] 금융조치 Panel

### FE-06 Verification Link

- [x] 요청 주체
- [x] 전체 Case 비노출
- [x] 최소 확인 질문
- [x] 사실임 / 사실 아님 / 확인 불가

### 신규 추가 UI

- [ ] 고객 화면 음성상담 시작/종료 UI
- [ ] 은행 화면 음성상담 시작/종료 UI
- [ ] 실시간 STT 표시
- [ ] 음성상담 상태 표시
- [ ] LIVE Case Report View
- [ ] FINAL Case Report View / 조회
- [ ] 질문 A/B/C 선택지만 부분 갱신
- [ ] LIVE Brief/Report Section 단위 렌더링
- [ ] Progress Item 한 줄 단위 갱신
- [ ] Timeline Append-only 렌더링
- [ ] Delta Event 기반 Client State/Query Cache 갱신

---

## 2. 일반 Backend TODO

### Core / Case

- [ ] `POST /api/cases/analyze`
- [ ] `GET /api/cases`
- [ ] `GET /api/cases/:caseId`
- [ ] `PATCH /api/cases/:caseId`
- [ ] Shared Case State 조립
- [ ] 역할/권한 검증

### Report

- [ ] `GET /reports/live`
- [ ] `GET /reports/final`
- [ ] `GET /reports`
- [ ] `POST /reports/refresh`
- [ ] `POST /reports/finalize`
- [ ] Report Trigger
- [ ] Report version 저장
- [ ] `CASE_REPORT_UPDATED`
- [ ] `CASE_REPORT_FINALIZED`

### Fragment / Delta Backend

- [ ] 초기 State Bundle API와 이후 Delta API 역할 분리
- [ ] Report Section 조회/PATCH API
- [ ] Question Options 조회
- [ ] Progress Item PATCH
- [ ] Timeline cursor 증분 조회
- [ ] Field-level Case PATCH
- [ ] `base_version` 검증
- [ ] Version Conflict 처리
- [ ] 변경되지 않은 Entity 재저장 방지
- [ ] Delta Event Envelope 표준화

### Conversation / Question

- [ ] messages 조회/저장
- [ ] questions Queue
- [ ] next question
- [ ] 승인/편집/보류
- [ ] send
- [ ] Human Takeover
- [ ] Resume AI

### Verification

- [ ] Verification Task 생성
- [ ] Verification 상태 조회
- [ ] token 조회
- [ ] 외부 응답 저장

### Actions / Recovery

- [ ] 은행 Action 기록
- [ ] Action History
- [ ] Recovery Start
- [ ] Recovery Task 변경

### Voice

- [ ] Voice Session 생성
- [ ] 참여
- [ ] 종료
- [ ] Transcript 조회
- [ ] Summary 조회
- [ ] Audio → AI STT 전달
- [ ] Final Segment 저장
- [ ] Voice Event 발행

### Backend Orchestration

- [ ] Frontend ↔ Backend
- [ ] Backend ↔ AI API
- [ ] Backend ↔ MySQL
- [ ] Backend ↔ Realtime
- [ ] Backend ↔ Voice Session
- [ ] AI 결과 Schema Validation
- [ ] Retry/Timeout
- [ ] 오류 표준화

---

## 3. AI API TODO

### Diagnosis

- [ ] `/ai/analyze/text`
- [ ] `/ai/analyze/windows`
- [ ] `/ai/features/extract`
- [ ] `/ai/risk/predict`
- [ ] Segment/Text Span evidence

### Case Report AI

- [ ] `/ai/reports/initialize`
- [ ] `/ai/reports/update`
- [ ] `/ai/reports/finalize`
- [ ] LIVE Report Schema
- [ ] FINAL Report Schema
- [ ] Source/Evidence 연결
- [ ] LIVE 버전 전략
- [ ] FINAL Revision 전략
- [ ] Report 품질 테스트
- [ ] LIVE Section Key 정의
- [ ] Report Impact Router
- [ ] changed_sections 계산
- [ ] Report Patch Schema
- [ ] Section별 source_ids
- [ ] 전체 Refresh 조건 정의
- [ ] 변경되지 않은 Section 재생성 방지

### Agent

- [ ] `/ai/questions/next`
- [ ] P0 표준질문 제약
- [ ] P1/P2 후보
- [ ] `/ai/verifications/plan`
- [ ] `/ai/case/structure`

### RAG

- [ ] `/ai/rag/search`
- [ ] `/ai/rag/verify-claim`
- [ ] Verification RAG
- [ ] `/ai/rag/response-guide`
- [ ] `/ai/rag/recovery-guide`
- [ ] `/ai/rag/institution-info`
- [ ] Source Metadata 반환
- [ ] 최신성 필터
- [ ] RAG 평가

### Voice AI

- [ ] Streaming STT
- [ ] Partial / Final 구분
- [ ] 화자 구분
- [ ] `/ai/voice/analyze-delta`
- [ ] `/ai/voice/summarize`
- [ ] 기존 Case와 신규 사실 충돌 감지
- [ ] 음성상담 결과 → Case Report 연결

---

## 4. MySQL / Vector DB TODO

### Core Tables

- [ ] `cases`
- [ ] `case_inputs`
- [ ] `analysis_segments`
- [ ] `context_features`
- [ ] `messages`
- [ ] `questions`
- [ ] `verification_tasks`
- [ ] `actions`
- [ ] `case_events`

### Reports

- [ ] `case_reports`
- [ ] `case_report_sources`
- [ ] `case_report_sections`
- [ ] `case_report_section_sources`
- [ ] `question_options`
- [ ] `progress_items`
- [ ] LIVE version / is_latest
- [ ] FINAL status / revision
- [ ] source_snapshot

### Voice

- [ ] `voice_sessions`
- [ ] `voice_transcript_segments`

### Official Data / RAG

- [ ] `official_contacts`
- [ ] 연락처 Seed Data
- [ ] `knowledge_sources`
- [ ] 공식문서 Source 수집
- [ ] 문서 정제
- [ ] Chunking
- [ ] Embedding
- [ ] Vector DB Index
- [ ] `case_evidence`
- [ ] effective_date / last_verified_at / status

---

## 5. Realtime TODO

- [ ] SSE vs WebSocket 결정
- [ ] Case 구독 Channel
- [ ] 저장 성공 후 Publish
- [ ] Customer UI 반영
- [ ] Bank UI 반영
- [ ] Transcript Event
- [ ] Voice Analysis Event
- [ ] Verification Event
- [ ] Action Event
- [ ] Report Updated Event
- [ ] Report Finalized Event
- [ ] 재접속 State 복구

---

## 6. 개발 단계 TODO

노션의 권장 개발 순서:

- [ ] STEP 1 MySQL Schema + Migration
- [ ] STEP 2 `/` 진단 + Analyze API
- [ ] STEP 3 `/cases` + Case Detail API
- [ ] STEP 4 Role Selector
- [ ] STEP 5 Customer Safety Room + messages/questions
- [ ] STEP 6 Fraud Case Workspace + Question Queue
- [ ] STEP 7 Verification Link
- [ ] STEP 8 Backend / AI API 분리 연동
- [ ] STEP 8-1 Fragment/Delta API + Version + Event 규격
- [ ] STEP 9 official_contacts + knowledge_sources
- [ ] STEP 10 공식문서 + Vector DB
- [ ] STEP 11 Verification RAG
- [ ] STEP 12 Voice Session + RTC + STT
- [ ] STEP 13 Transcript 증분 분석
- [ ] STEP 14 Realtime Case 동기화
- [ ] STEP 15 Human Takeover + Bank Actions
- [ ] STEP 16 PREVENT → RECOVERY
- [ ] STEP 17 Response / Recovery / Institution RAG
- [ ] STEP 18 Full Demo E2E

### Case Report AI 연동 작업

- [ ] 최초 Diagnosis 후 Report initialize
- [ ] Message/Event 후 Report update
- [ ] STT Final Segment 후 Report update
- [ ] Verification/RAG 후 Report update
- [ ] Bank Action 후 Report update
- [ ] Recovery 상태 반영
- [ ] 사건 종료 후 Report finalize
- [ ] LIVE/FINAL 화면 연결

---

## 7. E2E 테스트 TODO

### Scenario A — 일반 통화

- [ ] 입력
- [ ] 진단
- [ ] Case 생성
- [ ] 분석결과 저장
- [ ] 정상/낮은 위험 흐름 확인

### Scenario B — 정상 금융 상담

- [ ] 입력
- [ ] 분석
- [ ] 정상 상담 Context 확인
- [ ] Case List 표시

### Scenario C — 보이스피싱

- [ ] 입력
- [ ] 전체/Window 분석
- [ ] Feature
- [ ] Risk
- [ ] LIVE Report
- [ ] P0
- [ ] Bank Workspace
- [ ] P1/P2
- [ ] Verification RAG
- [ ] 음성상담
- [ ] STT
- [ ] Report 실시간 갱신
- [ ] Bank Action
- [ ] PREVENT 또는 RECOVERY
- [ ] FINAL Report

---

## 8. 작업 로그 템플릿

매 작업 완료 시 아래 형식으로 추가한다.

```text
## YYYY-MM-DD

### 완료
- [x] TASK-ID 작업명
  - 변경사항:
  - API/파일:
  - 테스트:
  - PR/Commit:

### 진행중
- [ ] TASK-ID 작업명
  - 현재 상태:
  - 다음 작업:

### Blocked
- [ ] TASK-ID 작업명
  - 차단 이유:
  - 필요한 결정/지원:
```

---

## 9. 현재 주요 Blocker / 결정 필요

- [ ] Backend 기술 스택 확정
- [ ] AI API Serving 방식
- [ ] MySQL 실제 Schema 타입
- [ ] Vector DB 선택
- [ ] STT 선택
- [ ] LLM 선택
- [ ] SSE vs WebSocket
- [ ] RTC 방식
- [ ] 공식문서 Corpus 범위
- [ ] 음성 원본 보관정책
- [ ] 인증/권한
- [ ] 실제 금융사/FDS 연동 범위


## 10. Fragment Update E2E 테스트

- [ ] 질문 1개 생성 후 A/B/C 선택지만 별도 조회 가능
- [ ] 질문 문구 수정 시 Timeline/Report 전체가 불필요하게 갱신되지 않음
- [ ] Verification 결과 추가 시 `verification_status` Report Section만 Patch
- [ ] 송금상태 변경 시 관련 Section만 Patch
- [ ] Progress Item 1개 완료 후 해당 Row와 전체 count만 갱신
- [ ] Timeline Event 추가 시 기존 목록 유지 + 1건 Append
- [ ] STT Segment 1개 추가 시 Transcript 1건 Append
- [ ] Backend가 entity version 충돌을 탐지
- [ ] Frontend가 Delta Event로 해당 Component만 갱신
- [ ] FINAL 보고서는 종료 시 전체 이력 기준으로 정상 조립
