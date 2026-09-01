# lee 담당 작업 매핑

## 역할

eom의 최초 진단과 파일 충돌 없이 Case 생성 이후 필요한 Report, 고객·은행 지원, Verification/RAG AI를 설계·구현한다.

## 소유 영역

```text
AI Backend report
AI Backend case_support
AI Backend knowledge
Report/Question/Verification AI Contract
AI 평가 Fixture
```

## 담당 Task

| Task ID | 작업 | 산출물 | 선행 | Reviewer |
|---|---|---|---|---|
| CT-03 | Report Initialize Contract | 초기 Section Schema·Fixture | Case DTO | eom |
| AI-05A | Report Initializer | 최초 LIVE Sections | CT-03 | eom |
| AI-05B/C | LIVE Update·FINAL | Section Patch·Revision | AI-05A | eom |
| AI-06 | Question Planner | P0/P1/P2·Options | Question Schema | eom |
| AI-07 | Verification Planner | 주장·대상·질문 | Verification Schema | eom |
| AI-08 | Case Structurer | 고객 답변 Field Patch | Case Schema | eom |
| AI-12~15 | Knowledge RAG | 검증·안내·Recovery·기관 근거 | Source Pipeline | eom |
| AI-16 | Report Impact Router | Event→changed_sections | Section Schema | eom |
| AAPI-20 | Report AI API | initialize/update/finalize | AI-05 | eom |
| AAPI-21 | Case Support API | question/verification/structure | AI-06~08 | eom |
| AAPI-30 | Knowledge API | RAG Endpoints | AI-12~15 | eom |

## 수정하지 않을 영역

- Frontend `/`와 `caseApi`
- 일반 Backend `cases/analyze` 구현
- `ai_backend/diagnosis/**`
- WindowAI Adapter
- eom의 작업 문서

## 권장 브랜치

```text
lee/contract-report-initialize
lee/ai-report
lee/ai-case-support
lee/ai-knowledge-rag
```
