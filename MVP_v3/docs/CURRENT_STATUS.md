# MVP v3 현재 구현 상태

최종 갱신: 2026-09-14
역할: 개발·점검 작업을 시작할 때 확인하는 단일 최신 상태 문서

> 실제 코드와 최신 테스트 결과가 이 문서보다 우선한다. 완료하지 않은 기능은 구현된 것처럼 표시하지 않는다.

## 서비스와 변경 불가 원칙

CSR(Case Share Room)은 보이스피싱 의심 사건에서 고객, 은행 직원, AI가 하나의 Shared Case를 통해 확인된 사실과 진행 업무를 공유하는 서비스다.

- AI는 분석·추천·요약을 지원하지만 은행 직원의 결정을 대신하지 않는다.
- 고객 진술과 AI 추출 결과는 직원 또는 공식기관 확인 전까지 확정 사실이 아니다.
- 안내 열람, 질문 답변, AI 추론만으로 지급정지·신고·피해구제가 완료됐다고 표시하지 않는다.
- 고객 공개 데이터와 은행 내부 데이터를 서버 경계에서 분리한다.
- 통화 원문은 분석 중에만 사용하고 Shared Case에는 privacy-safe 구조화 결과만 저장한다.
- 직원 편집과 확정 사실을 AI 자동 갱신으로 덮어쓰지 않는다.
- Frontend는 General API만 호출하며 AI API와 DB를 직접 사용하지 않는다.

## 현재 실행 구조

```text
React Frontend :5176
  └─ /api → General FastAPI :8100
                ├─ MySQL / attachment storage
                └─ AI FastAPI :8101
                     ├─ Event·Context Feature extraction
                     ├─ Window Logistic risk model
                     └─ LLM support services
```

- 로컬 시연은 `MVP_OPEN_PERMISSIONS=1`을 사용할 수 있지만 실제 인증/RBAC를 의미하지 않는다.
- 환경변수는 `MVP_v3/.env` 하나를 사용한다.
- 신규 DB는 기본 schema 적용 후 `backend/scripts/apply_migrations.py`로 남은 migration을 적용한다.

## 현재 구현된 핵심 기능

### 분석과 Case 생성

- 통화 원문을 Event, Context code, 숫자 Feature로 변환하고 Window Logistic 위험도를 계산한다.
- 원문을 DB에 저장하지 않고 구조화 신호와 privacy-safe projection으로 Case를 만든다.
- 모델은 실험용 sample artifact이며 금융기관의 최종 판단으로 표시하지 않는다.
- 과거 LLM pipeline의 합성 30건 baseline과 Feature inventory는 `../../tests/context_test/`에 보존한다.

### Context Panel V3

- 은행 Case Room은 `frontend/src/context-v3/`의 정확한 7개 Section을 사용한다.
- 고객·직원 CHAT 저장 후 durable extraction job이 Message를 typed `PROPOSED` Fact로 변환한다.
- 요청 금액·실제 송금액·수행 상태와 CLAIM·DEMAND·TACTIC을 분리한다.
- Fact confirm/reject/supersede, Gap, Verification, AI Suggestion, Staff Task, Decision을 분리한다.
- 고객 공개는 서버 allowlist를 사용하며 민감 연락처·계좌는 마스킹한다.
- Summary 직원 override는 revision이 맞을 때만 표시하고 canonical data를 변경하지 않는다.
- Context Quick Nav, 최근 사건 기록 Drawer, projection 오류·재시도 UI를 제공한다.

### 최근 Frontend 단순화

- 은행 `고객 공유 결과` Section은 `CustomerProgressEditor`를 바로 표시한다. 중복 notice, lane, count, empty state를 제거했다.
- Summary의 중복 `위험도 · 진행 상태` 문구는 구조화 Case metadata와 정확히 일치하는 deterministic item만 표시에서 제외한다. Case의 risk/status 데이터는 유지한다.
- 고객 `현재 진행 상황`은 5개의 큰 카드를 compact step list로 변경했다.
- `COMPLETED`, `SUBMITTED`, `IN_PROGRESS`, `UNKNOWN`, `NOT_APPLICABLE`을 서로 다른 의미로 표시한다.
- 상세 summary, next action, reference, 확인 시각, 담당자 확인 요청은 단계별 접근 가능한 상세 영역에 보존한다.
- 단일로 확정할 수 있는 `IN_PROGRESS`/`SUBMITTED` next action만 `지금 할 일`로 강조한다.
- 고객 진행 상태의 `COMPLETED`/`NOT_APPLICABLE` 단계에는 새 담당자 확인 요청을 노출하지 않고, 이미 기록된 요청 상태만 중복 없이 표시한다.
- 은행 Context Quick Nav의 고객 공유 항목은 본문에 표시되지 않는 공개 자원 수를 숫자로 표시하지 않는다.
- 고객 진행 패널의 핵심 상태·상세·안전 문구 가독성과 Fact 추가 작업 버튼의 클릭 영역을 보강하고, 직원 화면의 개발자용 미구현 안내 문구를 제거했다.

### 고객 진행 상태와 AI

- SAFETY, EVIDENCE, PAYMENT_HOLD, REPORT, RELIEF의 독립 상태를 append-only snapshot으로 저장한다.
- 제출·완료 확인에는 근거와 시각이 필요하다.
- 고객 확인 요청은 revision 단위로 멱등 저장하며 고객·은행 채팅에 기록한다.
- 고객 화면과 Customer Agent는 동일한 고객 공개 진행 상태를 사용한다.

### 보고서와 협업

- 사건 종결은 관리자 암호와 AI 최종 보고서 생성 경로를 사용한다.
- 메시지, 질문·답변, Fact, Verification, Task, 결정 기록을 Case 단위로 검색해 은행 AI와 고객 AI에 서로 다른 공개 범위로 제공한다.
- 질문 카드, 구조화 답변, 참여자, 개인 메모, 북마크, 첨부파일, 종결·복구·휴지통 흐름을 제공한다.

## 아직 완료되지 않은 범위

- Context Summary는 현재 규칙 기반 projection이며 최신 Case 전체를 LLM으로 재요약하는 구조가 아니다.
- 실제 인증 세션과 운영형 RBAC가 없다.
- 실제 브라우저에서 은행·고객 전체 업무를 연속 수행한 E2E 증거가 없다.
- 실제 금융기관·수사기관·통신사 API와 공식 corpus가 없다.
- 모든 legacy 메시지·답변의 Context V3 backfill은 없다.
- `bundle.recent_events`는 전체 감사 이력이 아니다. resource별 before/after와 cursor를 제공하는 History API가 필요하다.
- 신규 Fact 생성 시 기존 Fact를 대체하려는 의도를 polling 이후까지 보존하는 계약이 없다.
- Task 원본 상세 편집 projection과 Fact evidence 후보·직원 메모 계약이 부족하다.
- 고객 공개 Draft/Review/Publish/Withdraw workflow는 없다. 현재는 서버가 이미 공개한 결과만 사용한다.
- RAG는 한국어 TF-IDF/동의어 검색이며 embedding 의미 검색이 아니다.
- 변경 동기화는 polling 중심이며 SSE/WebSocket이 아니다.
- 첨부파일 악성코드 검사, object storage, signed URL이 없다.
- 실제 외부 업무가 연결되지 않았으므로 앱의 업무·Action 기록은 외부 처리 완료 증거가 아니다.

## 다음 작업 우선순위

### P0

1. 은행·고객 두 브라우저에서 새 분석→Case→채팅→질문→Fact→업무→고객 공개→새로고침 전체 E2E를 검증한다.
2. 같은 dataset/evaluator로 최신 LLM pipeline을 실행해 `tests/context_test/baseline_v1`과 비교한다.
3. 실제 인증 세션과 서버 권한 모델을 설계·구현한다.
4. resource별 전체 History API와 고객 공개 workflow 계약을 확정한다.

### P1

1. 최신 Shared Case 기반 LLM Summary와 revision cache를 구현한다.
2. persistent supersede intent, Task detail, Fact evidence/staff note 계약을 보강한다.
3. RAG 중복 질문 방지와 검색 provenance를 개선한다.
4. polling을 SSE/WebSocket과 장애 시 fallback polling 구조로 개선한다.

### P2

1. 외부 기관·금융 시스템 연동과 직원 승인·감사·재시도 체계를 구현한다.
2. 첨부파일 보안·object storage·signed URL을 구현한다.
3. AI quota, model/prompt version, 비용, latency, 장애 복구를 운영 지표로 관리한다.

## 최신 검증 기준

| 검증 | 최신 확인 결과 |
|---|---|
| LLM Context baseline | 합성 30건 재집계: Context Feature Recall 0.4145, Critical Fact Recall 0.3137, contradiction 7건, hallucination 76건 |
| Context V3 General API | 전체 174개 통과 기록. 이번 정리 후 customer progress·panel·vertical slice 15개 재통과 |
| Context V3 AI API | 전체 106개 통과 기록. 이번 정리 후 bounded Fact extraction 8개 재통과 |
| Migration | 격리 MySQL에서 Context Panel V3 migration apply→rollback→reapply 통과 기록 |
| Frontend | typecheck PASS, production build 1,462 modules PASS, `scripts/test-*.cjs` 13개 전부 PASS; 실제 브라우저 E2E는 미실행 |
| LLM Context evaluator | `tests/context_test/test_evaluate.py` 2개 PASS |
| Judge Explorer metadata | 현재 코드 기준 재생성, 관련 테스트 `8 passed` |

작업 종료 시 실제로 다시 실행한 검증만 이 표에 갱신한다. 과거 HTTP 200, 과거 유료 호출, 특정 Case 수동 보정 기록은 최신 기능 검증으로 재사용하지 않는다.

## 알려진 경고

- FastAPI `on_event`와 TestClient/httpx 관련 deprecation warning
- General API와 AI API의 `tests` Python package명이 같아 전체 경로를 한 pytest 명령에 섞지 않고 suite별로 실행해야 함
- MySQL `risk_score` 정밀도 경고
- MySQL `VALUES()` upsert deprecation warning
- 브라우저 E2E와 실제 외부기관 연동 미검증

## 유지하는 기준 문서

- 문서 안내: `README.md`
- 개인정보 안전 분석 흐름: `04_PRIVACY_SAFE_SIGNAL_FLOW.md`
- 고객 진행 상태와 AI: `07_CUSTOMER_PROGRESS_AND_AI.md`
- Case Context 데이터 계약: `09_CASE_CONTEXT_DATA_CONTRACT.md`
- 사건 종결 보고서 계약: `10_FINAL_CASE_REPORT_CONTRACT.md`
