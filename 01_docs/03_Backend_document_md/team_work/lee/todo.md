# lee TODO — 후속 AI 시스템

## 지금 해야 할 일

### 1. eom 초기 흐름 지원

- [ ] eom의 Public/Diagnosis Contract Review
- [ ] Case Header·Feature·Evidence 입력 확인
- [ ] Report Initialize Request·Response Schema 작성
- [ ] 고정 Fixture로 초기 Report Sections 반환
- [ ] eom이 Backend에서 호출할 수 있는 Contract Test 제공

### 2. Case Report AI

- [ ] Section Key와 content Schema 확정
- [ ] `/ai/reports/initialize` 구현
- [ ] 규칙 기반 Event→Section Impact 표 작성
- [ ] `/ai/reports/update` Section Patch 구현
- [ ] 변경되지 않은 Section 재생성 방지 테스트
- [ ] Source ID 연결
- [ ] `/ai/reports/finalize` Revision 구현

### 3. Customer·Bank 지원 AI

- [ ] P0 표준질문 Registry Contract 확인
- [ ] P1/P2 Question Planner 구현
- [ ] 질문과 Options 분리
- [ ] 고객 비정형 답변 Case Structurer 구현
- [ ] 기존 확정값 Conflict 반환
- [ ] Bank Copilot 근거 기반 응답 정책 정의
- [ ] 민감 인증정보 질문 차단 테스트

### 4. Knowledge·Verification RAG

- [ ] Knowledge Source Metadata Schema 확정
- [ ] Chunk·Embedding·Retriever Fixture
- [ ] Verification RAG
- [ ] Response Guide RAG
- [ ] Recovery Guide RAG
- [ ] Institution RAG
- [ ] 근거 없음·오래된 Source 처리 테스트
- [ ] 공식 연락처·URL 생성 금지 테스트

## 우선순위

```text
Report Initialize Contract
→ Report Initialize Fixture
→ LIVE Section Update
→ Question/Case Structurer
→ Verification RAG
→ FINAL Report
```

## Blocked / 결정 필요

- [ ] Report content JSON 최종 Schema
- [ ] LLM Provider·Model
- [ ] Embedding Model·Vector DB
- [ ] 공식문서 Corpus 범위

## 작업 로그

### YYYY-MM-DD — TASK-ID

- 완료:
- 변경 파일:
- 테스트:
- Commit/PR:
- 다음 작업:
