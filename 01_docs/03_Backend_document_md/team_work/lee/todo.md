# lee TODO — B AI & Multi-Agent

> 기존 Public Contract·Backend 인계 기여는 하단 완료 이력에 보존한다. 현재 TODO는 새 AI 책임 기준이다.

## P0 — 지금 바로

- [ ] ML bundle 위치·SHA-256·필수 field 재검증
- [ ] 실제 model status가 `EXPERIMENTAL_SAMPLE`임을 확인
- [ ] 최종 Feature 목록과 누락 기본값 확인
- [ ] Risk Score·Risk Level·Evidence output 확인
- [ ] Python Diagnosis DTO와 `ai_internal` JSON Schema 정합성 점검
- [ ] 정상·고위험·NO_CASE·부분실패 Example 최신화
- [ ] LLM timeout 자동화 test
- [ ] Model artifact 손상·누락 test
- [ ] Window AI 실패·Full Context 실패 조합 test
- [ ] A에게 AI Internal Contract 소비자 Review 요청

## P1 — 핵심 MVP

- [ ] P0/P1/P2 Question Schema
- [ ] `priority`, `target_field`, `execution_mode` 정의
- [ ] P0 표준질문 Guardrail
- [ ] 고객 자유답변 → Case Patch 구조화
- [ ] Customer Agent
- [ ] Bank Agent
- [ ] Verification Agent
- [ ] Initial/LIVE Brief initialize·update
- [ ] Event→changed_sections Impact Routing
- [ ] 근거·confidence·warnings·model/prompt version 반환

## P2 — 안정화

- [ ] 3종 Agent orchestration·idempotency
- [ ] Timeout·부분 실패·Fallback 정책
- [ ] 근거 없는 최종 판단·조치 차단 test
- [ ] 정상·위험·경계·공격 입력 Evaluation Dataset
- [ ] AI 품질·비용·latency 지표

## P3 — 확장

- [ ] 공식문서 Corpus 범위 확정
- [ ] Source Registry·Chunking·Embedding·Vector Index
- [ ] Verification/Response/Recovery/Institution RAG
- [ ] Source Metadata·최신성·RAG 평가
- [ ] Streaming STT·Voice Delta·Summary

## 다른 담당자에게 필요한 것

- A=eom: Case/Message/Event/Verification 조회 Service와 저장 Contract
- C=ham: 화면이 소비할 AI output과 Error/Loading 요구 Review

## 건드리지 않기

- [ ] DB를 직접 Query하지 않는다.
- [ ] Migration·General API·Frontend를 직접 수정하지 않는다.
- [ ] Public Contract 변경이 필요하면 A에게 먼저 요청한다.

## 기존 완료 이력 — 과거 구현 기여

- [x] Public Analyze Contract v1 확정에 기여
- [x] `CASE_CREATED`/`NO_CASE`/`FAILED` 공개 Envelope와 내부 결과 비노출 검증
- [x] 기존 Vertical Slice 인계·회귀 기록 작성
- 당시 기록된 Contract/API/E2E/build 결과는 보존하되, 2026-09-02 감사 환경에서 전체가 재검증된 것은 아니다.

## Blocked / 결정 필요

- [ ] 운영 LLM Provider·Model·비용 한도
- [ ] Embedding Model·Vector DB
- [ ] 공식문서 Corpus·최신성 정책
- [ ] STT Provider·Streaming 방식

## 작업 로그 템플릿

### YYYY-MM-DD — TASK-ID

- 목표:
- 변경 파일:
- 테스트·평가 결과:
- 미검증/Blocker:
- Contract 요청:
- 다음 작업:
