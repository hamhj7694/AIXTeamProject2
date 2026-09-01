# lee TODO — Frontend·General API 통합

## 현재 우선순위

### 1. 기존 Vertical Slice 인계

- [ ] eom이 작성한 `frontend`, `general_api`, `migrations` 변경 구조 확인
- [ ] Backend·AI API 로컬 실행
- [ ] 기존 Python Unit Test 실행
- [ ] Frontend production build 실행
- [ ] `/` 위험·정상 입력 HTTP E2E 재현
- [ ] Public Contract v1의 최종 편집자 인계 기록
- [ ] General API·Frontend·Migration 소유권 인계 완료 표시

### 2. 공개 Contract와 General API 정리

- [ ] `POST /api/cases/analyze` 요청·응답 Example 검토
- [ ] `CASE_CREATED`, `NO_CASE`, `FAILED` 공개 응답 확정
- [ ] 공개 DTO와 AI 내부 DTO 분리
- [ ] AI Fixture Client와 실제 HTTP Client 교체 지점 확인
- [ ] AI Timeout·부분 실패를 공개 오류로 변환하는 규칙 구현
- [ ] 중복 `client_request_id`와 Idempotency 검증
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

### YYYY-MM-DD — TASK-ID

- 완료:
- 변경 파일:
- 테스트:
- Commit/PR:
- 다음 작업:
