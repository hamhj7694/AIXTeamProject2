# eom TODO — AI 모델·AI API

## 현재 우선순위

### 1. AI 내부 Contract 인계 기준 확정

- [x] WindowAI Segment v1 Schema 작성
- [x] Diagnosis LLM 전체 맥락 v1 Schema 작성
- [x] AI API용 공통 진단 DTO 구현
- [ ] 공개 DTO와 AI 내부 DTO가 섞인 파일 분리 계획 작성
- [ ] `ai_internal` Request·Response Example 최신화
- [ ] Timeout·부분 실패·Fallback Error Schema 명시
- [ ] lee에게 소비자 관점 Contract Review 요청
- [ ] AI Internal v1 Contract Freeze 기록

### 2. 최초 진단 AI Hardening

- [x] WindowAI Adapter 연결
- [x] Full Context Diagnosis LLM 연결
- [x] Window 이벤트 추출과 Full Context LLM 병렬 실행
- [x] Feature·근거 중복 제거
- [x] Risk/Fusion 규칙 구현
- [x] Model artifact hash·필수 필드 검증
- [ ] LLM Timeout 자동화 테스트
- [ ] WindowAI 실패·Artifact 손상 자동화 테스트
- [ ] 한쪽 AI 실패 시 부분 결과 Contract Test
- [ ] 실제 보이스피싱·정상 상담 평가 Fixture 확장
- [ ] Model·Prompt version 응답 필드 검증

### 3. lee 병렬 작업 지원

- [ ] General API가 사용할 결정론적 AI Fixture 제공
- [ ] AI API 실행 방법과 환경변수 문서화
- [ ] 정상·고위험·NO_CASE·부분 실패 Example 제공
- [ ] lee의 AI Client 소비자 Contract Test Review
- [ ] 실제 AI 교체 시 변경되는 값과 고정되는 Schema 구분

### 4. 후속 AI 구현

- [ ] AI-05/16 Case Report Initialize·Update·Finalize
- [ ] AI-06~08 Question·Verification·Case Structurer
- [ ] AI-12~15 Knowledge/RAG
- [ ] AI-09~11 Voice Intelligence

## 수정 금지 체크

- [ ] Frontend 문제를 `frontend/**`에서 직접 수정하지 않고 lee에게 전달
- [ ] 저장 문제를 `general_api/**` 또는 `migrations/**`에서 직접 수정하지 않고 재현 자료 전달
- [ ] 공개 API 변경이 필요하면 lee에게 Public Contract 변경 요청

## Blocked / 결정 필요

- [ ] AI 내부 DTO와 공개 DTO의 물리적 분리 방식
- [ ] 운영 LLM Provider·Model·비용 한도
- [ ] Embedding Model·Vector DB
- [ ] STT Provider·Streaming 방식
- [ ] 공식문서 Corpus 범위

## 기존 완료 이력

### 2026-09-01 — CT-01/02, BE-00/01, AI-01~04, AAPI-10, FE-01, INT-01

- 완료: 진단 계약, FastAPI 2계층, Window Logistic Adapter, LLM/Fixture Extractor, Fusion, 공개 API, Frontend 연결
- 변경 파일: `backend/contracts`, `backend/ai_api`, `backend/general_api`, `backend/migrations`, `frontend/src/services/caseApi.ts`, `frontend/src/pages/CasePages.tsx`
- 테스트: Python unittest 6개, 위험/정상 HTTP E2E, Frontend production build
- 비고: 새 분담 적용 후 `ai_api`와 AI 내부 Contract만 eom 소유로 유지한다. 나머지는 lee에게 인계한다.

## 작업 로그

### YYYY-MM-DD — TASK-ID

- 완료:
- 변경 파일:
- 테스트:
- Commit/PR:
- 다음 작업:
