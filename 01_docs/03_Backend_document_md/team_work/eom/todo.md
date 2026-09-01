# eom TODO — 최초 진단 Vertical Slice

## 지금 해야 할 일

### 1. Contract 확정

- [ ] `POST /api/cases/analyze` 요청·응답 예시 작성
- [ ] `CASE_CREATED`, `NO_CASE`, `FAILED` 응답 정의
- [ ] WindowAI Segment 출력 Schema 정의
- [ ] Diagnosis LLM 전체 맥락 출력 Schema 정의
- [ ] 공통 Error·Timeout Schema 정의
- [ ] lee에게 Contract Review 요청

### 2. Fixture 기반 E2E

- [ ] Backend 실행 Entrypoint 구성
- [ ] Fixture AI Client 작성
- [ ] 최소 Case Repository와 Core Migration 작성
- [ ] `/api/cases/analyze`가 Fixture 결과를 저장하도록 구현
- [ ] Frontend `caseApi`를 실제 HTTP 호출로 교체
- [ ] `/` Loading·Validation·Error UI 연결
- [ ] `CASE_CREATED`이면 `/cases/:caseId`로 이동
- [ ] `NO_CASE`이면 진단 결과를 표시하고 `/` 유지

### 3. 실제 Diagnosis AI

- [ ] WindowAI Adapter 연결
- [ ] Full Context Diagnosis LLM 연결
- [ ] ML과 LLM을 병렬 호출
- [ ] Feature 중복·근거 중복 제거
- [ ] Risk/Fusion 규칙 구현
- [ ] AI Timeout·부분 실패 정책 구현
- [ ] Fixture Client를 실제 AI Client로 교체

### 4. 테스트

- [ ] 빈 텍스트
- [ ] 일반 통화
- [ ] 정상 금융 상담
- [ ] 보이스피싱 사례
- [ ] 직접 입력
- [ ] WindowAI 실패
- [ ] LLM Timeout
- [ ] DB 저장 실패
- [ ] 중복 `client_request_id`

## 첫 완료 기준

```text
텍스트 입력
→ WindowAI + LLM 병렬 분석
→ Case DB 저장
→ CASE_CREATED
→ 실제 Case 상세 화면 이동
```

## Blocked / 결정 필요

- [ ] Backend Framework 확정
- [ ] MySQL 로컬 실행 방법 확정
- [ ] WindowAI 입력·출력 최종 형식
- [ ] LLM Provider·Model 확정

## 작업 로그

### YYYY-MM-DD — TASK-ID

- 완료:
- 변경 파일:
- 테스트:
- Commit/PR:
- 다음 작업:
