# eom TODO — 최초 진단 Vertical Slice

## 지금 해야 할 일

### 1. Contract 확정

- [x] `POST /api/cases/analyze` 요청·응답 예시 작성
- [x] `CASE_CREATED`, `NO_CASE`, `FAILED` 응답 정의
- [x] WindowAI Segment 출력 Schema 정의
- [x] Diagnosis LLM 전체 맥락 출력 Schema 정의
- [x] 공통 Error Schema 정의 (`httpx` timeout은 AI client에서 30초 적용)
- [ ] lee에게 Contract Review 요청

### 2. Fixture 기반 E2E

- [x] Backend 실행 Entrypoint 구성
- [x] Fixture Event Extractor 작성
- [x] 최소 Case Repository와 Core Migration 작성 (로컬 메모리 Repository + MySQL DDL)
- [x] `/api/cases/analyze`가 Fixture 결과를 저장하도록 구현
- [x] Frontend `caseApi`를 실제 HTTP 호출로 교체
- [x] `/` Loading·Validation·Error UI 연결
- [x] `CASE_CREATED`이면 `/cases/:caseId`로 이동
- [x] `NO_CASE`이면 진단 결과를 표시하고 `/` 유지

### 3. 실제 Diagnosis AI

- [x] WindowAI Adapter 연결
- [x] Full Context Diagnosis LLM 연결
- [x] Window 이벤트 추출 LLM과 Full Context LLM 병렬 호출
- [x] Feature 중복·근거 중복 제거
- [x] Risk/Fusion 규칙 구현
- [x] AI Timeout·부분 실패 정책 구현 (30초 timeout, Context 실패 시 이벤트 기반 요약 fallback)
- [x] General API에서 실제 AI HTTP Client 연결

### 4. 테스트

- [x] 빈 텍스트 (Pydantic/API validation)
- [x] 일반 통화/위험 이벤트 없음
- [x] 정상 금융 상담
- [x] 보이스피싱 사례
- [ ] 직접 입력
- [x] Window 모델 artifact 해시·필수 필드 검증
- [ ] LLM Timeout 자동화 테스트
- [ ] DB 저장 실패
- [x] 중복 `client_request_id`

## 첫 완료 기준

```text
텍스트 입력
→ WindowAI + LLM 병렬 분석
→ Case DB 저장
→ CASE_CREATED
→ 실제 Case 상세 화면 이동
```

## Blocked / 결정 필요

- [x] Backend Framework 확정 — FastAPI (현재 Vertical Slice 기준)
- [ ] MySQL 로컬 실행 방법 확정
- [x] WindowAI 입력·출력 v1 형식
- [x] LLM Provider·Model 기본값 — OpenAI Responses API / `gpt-4o-mini`, 환경변수로 교체 가능

## 작업 로그

### 2026-09-01 — CT-01/02, BE-00/01, AI-01~04, AAPI-10, FE-01, INT-01

- 완료: 진단 계약, FastAPI 2계층, Window Logistic adapter, LLM/fixture extractor, Fusion, 공개 API, Frontend 연결
- 변경 파일: `backend/contracts`, `backend/ai_api`, `backend/general_api`, `backend/migrations`, `frontend/src/services/caseApi.ts`, `frontend/src/pages/CasePages.tsx`
- 테스트: Python unittest 6개, 위험/정상 HTTP E2E, Frontend production build
- Commit/PR: 미작성
- 다음 작업: lee Contract Review, MySQL Repository adapter, DB 저장 실패/LLM timeout 자동화 테스트
