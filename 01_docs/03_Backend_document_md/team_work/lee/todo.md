# lee TODO — Frontend·General API 통합

## 현재 우선순위

### 1. 기존 Vertical Slice 인계 — HANDOFF-01 DONE

- [x] eom이 작성한 `frontend`, `general_api`, `migrations` 변경 구조 확인
- [x] Backend·AI API 로컬 실행
- [x] 기존 Python Unit Test 실행
- [x] Frontend production build 실행
- [x] `/` 위험·정상 입력 HTTP E2E 재현
- [x] Public Contract v1의 최종 편집자 인계 기록
- [x] General API·Frontend·Migration 소유권 인계 완료 표시

### 2. 공개 Contract와 General API 정리

- [x] `POST /api/cases/analyze` 요청·응답 Example 검토
- [x] `CASE_CREATED`, `NO_CASE`, `FAILED` 공개 응답 확정
- [x] 공개 DTO와 AI 내부 DTO 분리
- [ ] AI Fixture Client와 실제 HTTP Client 교체 지점 확인
- [ ] AI Timeout·부분 실패를 공개 오류로 변환하는 규칙 구현
- [x] 중복 `client_request_id`와 Idempotency 검증
- [ ] Request ID·구조화 로그·민감정보 제거 점검

### 3. DB·Frontend 실제 연동

- [ ] MySQL 로컬 실행 방법 확정
- [ ] In-memory Repository와 MySQL Repository 전환 설정
- [ ] DB 저장 실패·Transaction Rollback 자동화 테스트
- [ ] `/` Loading·Validation·Error·NO_CASE UI 회귀 테스트
- [ ] Case 생성 후 실제 `/cases/:caseId` 조회 연결
- [ ] Mock과 API 데이터 경계 문서화

### 4. 후속 통합

- [ ] Case List·Detail·Bundle API와 화면 연결
- [ ] Customer Room Conversation·Question API 연결
- [ ] Bank Workspace v2 Report·Action·Verification 연결
- [ ] SSE/WebSocket Delta 적용
- [ ] Voice Session·STT 연결 Workflow
- [ ] FINAL Report·Recovery E2E

## eom과의 계약 체크

- [ ] `ai_internal` Example을 소비자 Contract Test로 고정
- [ ] AI API Base URL·Timeout·Retry 설정 합의
- [ ] AI가 아직 없는 기능은 동일 Schema의 Fixture로 먼저 구현
- [ ] 실제 AI 전환 후 Fixture E2E와 실제 AI E2E를 모두 유지
- [ ] AI 내부 Contract 변경 없이 `ai_api/**` 직접 수정 금지

## Blocked / 결정 필요

- [ ] 인증·권한 방식
- [ ] MySQL 로컬·테스트 실행 방식
- [ ] SSE vs WebSocket
- [ ] 공개 API Versioning 정책
- [ ] 배포 환경의 AI API 주소·Secret 주입 방식

## 작업 로그

### 2026-09-01 — CT-01

- 완료: `POST /api/cases/analyze` Public Contract v1을 확정했다. 공개 Request는 `text`, 선택 `client_request_id`, 선택 `sample_type`만 받고, 공개 Response는 `CASE_CREATED` / `NO_CASE` / `FAILED` 공통 Envelope로 고정했다.
- 공개 경계: General API가 AI 내부 `diagnosis`, WindowAI/모델 메타데이터, 내부 오류 `details`를 Browser 응답에서 제거하고 공개 DTO로 정규화한다. `CASE_CREATED`는 Case 기본 정보와 초기 Report 참조만, `NO_CASE`는 `NORMAL` 위험도와 안내문만, `FAILED`는 공개 `error(code, message, retryable)`만 반환한다.
- HTTP 규칙: `CASE_CREATED`와 `NO_CASE`는 기존 동작과 같이 201, 잘못된 입력은 공개 `FAILED` + `INVALID_INPUT` / 400, AI 분석 실패는 공개 `FAILED` + `AI_ANALYSIS_FAILED` / 503으로 고정했다.
- 멱등성: `client_request_id`는 선택값이며 Frontend는 요청마다 UUID를 생성한다. 동일한 비어 있지 않은 값의 재요청은 기존 Case를 반환한다. 빈 문자열은 기존 구현과 같이 미제공으로 취급한다.
- 변경 파일: `contracts/public_api/case_analyze.py`, `contracts/public_api/case_analyze.v1.example.json`, `contracts/public_api/test_case_analyze_contract.py`, `general_api/app/main.py`, `general_api/tests/test_public_analyze_endpoint.py`, `team_work/lee/todo.md`
- 테스트: Public Contract unittest 4건 통과, Public Analyze Endpoint unittest 4건 통과, 기존 General API unittest 2건 통과, fixture AI API 연동 HTTP E2E(`CASE_CREATED` / `NO_CASE` / 멱등성 / INVALID_INPUT / Case·Live Report 조회) 통과, `npm run build` 통과.
- eom 연계 주의: `contracts/diagnosis.py`와 `ai_api/**`, `contracts/ai_internal/**`는 수정하지 않았다. AI 내부 Contract가 변경돼도 General API의 공개 DTO 변환 경계를 유지하며, 내부 결과가 공개 응답으로 다시 노출되지 않도록 확인한다.
- 비차단 이슈: Case 상세 GET 응답은 아직 기존 저장 레코드 구조를 반환하고, Case List는 Mock 기반이다. 각각 후속 Case Detail/List Contract·FE-02/BE-02 범위다. scikit-learn `InconsistentVersionWarning`은 공통 Dependency 기술 부채이며 이번 Task에서 `requirements.txt`를 수정하지 않는다.
- Commit/PR: 없음
- 다음 작업: BE-00 General API 공통 Error·AI Client 검토.

### 2026-09-01 — HANDOFF-01

- 완료: 기존 Vertical Slice 인계 및 회귀 검증 완료. Fixture + `CASE_REPOSITORY=memory` 기준으로 AI API(8001), General API(8000), Frontend(5173)를 검증했다. 위험/보이스피싱 입력은 `CASE_CREATED` 후 `/cases/:caseId` 이동 및 생성 Case 상세 표시를 확인했고, 일반 통화·정상 금융 상담은 `NO_CASE` 안내를 확인했다.
- 검증: AI API 기존 unittest 4건 통과, General API 기존 unittest 2건 통과, General API → AI API 실제 HTTP E2E 통과, `client_request_id` 멱등성 통과, `GET /api/cases/:caseId` 및 `GET /api/cases/:caseId/reports/live` 조회 통과, `npm run build` 통과, 브라우저 수동 UI 회귀 통과.
- 소유권: Public Contract v1의 최종 편집 책임은 lee에게 인계되었다. `frontend/**`, `general_api/**`, `contracts/public_api/**`, `migrations/**`의 후속 통합은 lee 범위이며, `ai_api/**`와 `contracts/ai_internal/**`는 eom 소유로 직접 수정하지 않는다.
- 변경 파일: `01_docs/03_Backend_document_md/team_work/lee/todo.md` (완료 기록만 갱신)
- 비차단 이슈: Case List는 현재 Mock 기반이므로 새 Case가 목록에 즉시 표시되지 않는다. 이는 FE-02 / BE-02에서 실제 List API를 연결할 항목이다. scikit-learn 모델 저장 버전 1.6.1과 설치 버전 1.9.0 차이의 `InconsistentVersionWarning`은 테스트·E2E가 통과한 기술 부채/Review 항목이며, 공통 `requirements.txt`는 수정하지 않는다. MySQL 영구 저장은 이번 완료 조건에 포함하지 않는다.
- Commit/PR: 없음
- 다음 작업: CT-01 Public Analyze Contract 검토. 구현은 HANDOFF-01 종료 후 별도 작업으로 시작한다.

### YYYY-MM-DD — TASK-ID

- 완료:
- 변경 파일:
- 테스트:
- Commit/PR:
- 다음 작업:
