# eom TODO — A Backend & Case Platform

> 아래 체크리스트는 앞으로의 책임 기준이다. 과거 AI/Vertical Slice 기여는 하단 완료 이력에 보존한다.

## P0 — 지금 바로

- [x] 현재 MySQL Migration과 실제 사용 Table 확인
- [x] `CASE_REPOSITORY=memory/mysql` 전환 재검증
- [x] MySQL Repository Create/List/Get transaction test
- [x] DB 실패 시 rollback 자동화 test
- [x] Case List/Get 공개 응답 DTO 확정
- [x] Case status/mode/risk/error enum 정리
- [x] `PATCH /api/cases/{case_id}` 상태전이 요구 정리
- [ ] C에게 Case 화면 필수 필드 Review 요청

## P1 — 핵심 MVP

- [x] Case PATCH·허용 상태전이·409 Version Conflict
- [x] Message migration·Repository·create/list API
- [x] Event/Timeline append·list·cursor API
- [x] Event actor·timestamp·payload·version Contract
- [x] Verification Task migration·API
- [x] 외부 Verification 응답 저장·상태 변경
- [x] Action/History API
- [x] Human Takeover/Resume 상태 저장 API
- [x] 저장 성공 후 Event 발행 경계 제공

## P2 — 안정화

- [ ] 역할/권한 검증
- [x] Request ID·구조화 로그·민감정보 제거
- [ ] DB 재시도·Pool 종료·장애 처리
- [ ] 공통 Error/Validation Envelope 확대
- [x] Repository·Service·API 통합 test

## 다른 담당자에게 필요한 것

- B=lee: 질문·자유답변·Agent output의 의미, Schema, Example
- C=ham: 화면에 필요한 Case/Event field와 Realtime 소비 요구

## 건드리지 않기

- [ ] AI Prompt·Agent 내부 로직을 직접 수정하지 않는다.
- [ ] Frontend 화면 문제는 C에게 재현 자료와 함께 전달한다.
- [ ] 공용 Contract는 B/C 영향 확인 없이 깨뜨리지 않는다.

## 기존 완료 이력 — 과거 구현 기여

- [x] WindowAI·Full Context LLM·Feature·Risk/Fusion 초기 구현
- [x] FastAPI 2계층과 Diagnosis→Case 생성 흐름 초기 구현
- [x] Core Case/Diagnosis/LIVE Report Migration과 MySQL Repository 초기 구현
- [x] Analyze/List/Get/LIVE Report와 Frontend 프록시 연결 초기 구현
- 기록된 과거 실행에서는 Python test·HTTP E2E·Frontend build가 통과했다.
- 2026-09-02 감사 환경에서는 공개 Contract test 4건만 재통과했고, 일부 Python test와 Frontend build는 로컬 의존성/실행환경 제한으로 재검증하지 못했다.

## 작업 로그 템플릿

### 2026-09-02 — A-0 기준선 재검증

- 목표: Core Migration·Repository·저장소 전환의 실제 동작을 운영 Case 데이터와 분리해 재검증
- 변경 파일:
  - `backend/general_api/app/domains/cases/mysql_repository.py` — MySQL Pool 종료 메서드 추가
  - `backend/general_api/tests/test_mysql_repository_integration.py` — 임시 DB 기반 통합 테스트 추가
- 테스트 결과:
  - 운영 DB에서 Migration 001~003, Core 7개 Table, FK 7개, 인덱스 확인
  - 임시 DB에서 Migration 반복 실행, Create/List/Get, `client_request_id` 조회, 실패 rollback 통과
  - `CASE_REPOSITORY=memory/mysql` 선택 분기 통과
  - General API 테스트 10개 통과
- 미검증/Blocker:
  - 모델 점수·Feature의 소수점이 DB scale에서 반올림될 때 MySQL 경고가 발생함. 저장 정밀도 정책은 A-1 DTO/Enum 정리에서 결정 필요
- 협업 요청: C=ham에게 Case List/Get 화면 필수 field Review 요청 예정
- 다음 작업: A-1 Public Case DTO·Enum·상태전이 요구 정리

### 2026-09-02 — A-1/A-4 Case Lifecycle and Verification State

- [x] Public Case risk/mode/status/error enum contract implemented.
- [x] `PATCH /api/cases/{case_id}` implemented with allowed transitions and `409 VERSION_CONFLICT`.
- [x] Case `version` migration 006 applied to the real MySQL database.
- [x] Verification task status patch implemented with version checking and `VERIFICATION_UPDATED` event.
- Test: General API and MySQL integration suite passed (21 tests).
- Boundary: AI Prompt/Agent and frontend-owned realtime/voice work remain outside eom.

### 2026-09-02 — A-4 Workflow Completion

- [x] Verification Task status update persists with optimistic version check.
- [x] `VERIFICATION_UPDATED` event is appended for every status change.
- [x] `POST /api/cases/{case_id}/takeover` and `/resume` persist explicit control actions.
- [x] API responses include an `X-Request-ID` for request tracing.
- Test: General API and MySQL integration suite passed (22 tests).

### 2026-09-02 — A-5 Voice and Report Completion

- [x] Voice Session create/status API and MySQL persistence.
- [x] Append-only transcript segment API and Timeline Event.
- [x] Bundle returns the latest Case voice session.
- [x] FINAL Report finalize/read API and CLOSED Case transition.
- Test: public workflow contract tests and MySQL integration passed (23 tests).
- Boundary: role authorization, DB retry policy, full error envelope, and realtime transport remain dependent on auth/stream contracts.

### YYYY-MM-DD — TASK-ID

- 목표:
- 변경 파일:
- 테스트 결과:
- 미검증/Blocker:
- 협업 요청:
- 다음 작업:
