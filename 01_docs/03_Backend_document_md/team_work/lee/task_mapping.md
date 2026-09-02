# lee 작업 매핑 — B AI & Multi-Agent Engineer

## 역할

lee는 Case를 읽고 무엇을 분석·질문·검증할지 결정하며, 구조화된 AI 결과와 평가를 책임진다.

## 향후 소유 영역

```text
02_workspace/backend/ai_api/**
02_workspace/backend/contracts/ai_internal/**
02_workspace/backend/ai_api/models/**
AI Fixture·Prompt·Evaluation·RAG Pipeline
```

## 핵심 책임

- ML Risk Score, Context Feature, Full/Window 분석
- LLM Initial/LIVE/FINAL Brief
- Customer/Bank/Verification Agent
- P0/P1/P2 질문과 자유답변 구조화
- RAG, Prompt, Agent Orchestration
- AI Output Schema, 근거, confidence, version
- Timeout·부분 실패·Fallback·환각 처리와 평가

## 작업 순서

| Phase | 목표 | 대상 | 완료 조건 |
|---|---|---|---|
| B-0 | 기존 Diagnosis 인계 검증 | diagnosis domain·model | hash·feature·risk fixture 재현 |
| B-1 | AI Internal Contract 정리 | diagnosis DTO·ai_internal | Python/JSON 정합성과 실패 Example |
| B-2 | Diagnosis Hardening | extractor/window/fusion | timeout·artifact·부분실패 test |
| B-3 | Question/Answer Intelligence | 신규 AI domain | P0/P1/P2·target·execution·구조화 |
| B-4 | Brief/Report AI | report domain·schema | initialize/update/finalize·근거 test |
| B-5 | Agent Orchestration | AI service layer | 3종 Agent routing·fallback test |
| B-6 | RAG·Evaluation | ingestion/search/eval | 출처·최신성·환각 평가 |
| B-7 | Voice Intelligence | STT/Delta/Summary | Partial/Final·중복·순서 test |

## 수정하지 않을 영역

- `backend/general_api/**`, `migrations/**`, DB 직접 Query
- `frontend/**`, Realtime client, Docker
- eom·ham 개인 작업 문서

새 Case Field가 필요하면 의미·Schema·Example을 작성해 A=eom에게 요청한다. UI 표현이 필요하면 C=ham에게 output 의미와 안전 문구를 전달한다.

## 과거 구현 기여

lee가 기존 Public Analyze Contract와 Backend Schema 정리에 기여한 기록은 유지한다. 향후 Public API·DB 책임은 A=eom으로, Frontend·통합 책임은 C=ham으로 전환된다.

## Codex 수칙

1. 기존 AI 모델·Contract·Fixture를 먼저 읽고 임의로 새 구조를 만들지 않는다.
2. DB를 직접 Query하거나 Migration을 수정하지 않는다.
3. Prompt/Model 변경 시 version과 평가 결과를 기록한다.
4. 입력에 없는 사실·기관 연락처·금융조치를 생성하지 않는다.
5. 근거·불확실성·부분 실패를 output에 보존한다.

## 작업 Branch

`new_lee`를 사용한다. 기능별 Branch를 추가 생성하지 않고 최신 `main`을 merge 방식으로 반영한다.
