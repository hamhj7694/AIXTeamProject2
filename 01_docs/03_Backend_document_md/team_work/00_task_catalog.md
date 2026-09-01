# 전체 작업 카탈로그 · 3인 배정

> 상세 설계: 상위 `01~07`, `ai_system_design/**`
> 개인 진행상황: `eom/todo.md`, `lee/todo.md`, `ham/todo.md`

## 1. 코드 소유권

| 영역 | 소유자 | 다른 작업자의 변경 규칙 |
|---|---|---|
| Frontend 최초 진단·Case API Client | eom | eom Review 필요 |
| 일반 Backend 최초 진단 모듈 | eom | eom Review 필요 |
| AI Backend Diagnosis·WindowAI | eom | eom Review 필요 |
| AI Backend Report·Customer/Bank·Knowledge | lee | lee Review 필요 |
| 추후 Realtime·Voice·Verification Backend | ham | 합류 후 ham Review 필요 |
| 공통 Root 설정·Docker·Entrypoint | 작업 시작 전 1명 지정 | 공동 직접 수정 금지 |

권장 코드 경계:

```text
02_workspace/frontend/**                         eom: 최초 연결
02_workspace/backend/**                          eom: analyze/core부터 시작
02_workspace/backend/ai_api/app/domains/diagnosis/**    eom
02_workspace/backend/ai_api/app/domains/report/**       lee
02_workspace/backend/ai_api/app/domains/case_support/** lee
02_workspace/backend/ai_api/app/domains/knowledge/**    lee
02_workspace/backend/realtime|voice|verification ham: 추후
```

## 2. 지금 진행할 작업

| 순서 | ID | 작업 | 담당 | Reviewer | 선행 | 상태 |
|---|---|---|---|---|---|---|
| 1 | CT-01 | `/api/cases/analyze` 공개 Contract | eom | lee | 없음 | TODO |
| 1 | CT-02 | Diagnosis AI Contract | eom | lee | 없음 | TODO |
| 1 | CT-03 | Report Initialize Contract/Fixture | lee | eom | Case DTO | TODO |
| 2 | BE-00 | Backend Skeleton·Error·AI Client Interface | eom | lee | CT-01/02 | TODO |
| 2 | DB-01 | 최초 Case Core Schema·Migration | eom | lee | CT-01 | TODO |
| 2 | FE-01 | `/` 실제 API Client·Loading·Error | eom | lee | CT-01 | TODO |
| 2 | AI-01 | Full Context Diagnosis LLM | eom | lee | CT-02 | TODO |
| 2 | AI-02 | WindowAI Segment Analyzer | eom | lee | CT-02 | TODO |
| 3 | AI-03 | Feature Extractor | eom | lee | AI-01/02 | TODO |
| 3 | AI-04 | Risk/Fusion 규칙 | eom | lee | AI-01~03 | TODO |
| 3 | AAPI-10 | Diagnosis AI API | eom | lee | AI-01~04 | TODO |
| 3 | AI-05A | Initial Report Fixture/AI | lee | eom | CT-03 | TODO |
| 4 | BE-01 | `POST /api/cases/analyze` Orchestration | eom | lee | BE-00, AAPI-10 | TODO |
| 4 | INT-01 | `/` → Case 생성 → 상세 이동 E2E | eom | lee | FE-01, BE-01 | TODO |

## 3. lee 후속 AI 작업

| ID | 작업 | 담당 | Reviewer | 선행 | 상태 |
|---|---|---|---|---|---|
| AI-05B | LIVE Report Section Update | lee | eom | AI-05A | TODO |
| AI-05C | FINAL Report Generator | lee | eom | AI-05B | TODO |
| AI-06 | P0/P1/P2 Question Planner | lee | eom | Question Schema | TODO |
| AI-07 | Verification Planner | lee | eom | Verification Schema | TODO |
| AI-08 | Customer Answer Case Structurer | lee | eom | Case Schema | TODO |
| AI-12 | Verification RAG | lee | eom | Knowledge Source | TODO |
| AI-13 | Response Guide RAG | lee | eom | Knowledge Source | TODO |
| AI-14 | Recovery Guide RAG | lee | eom | Knowledge Source | TODO |
| AI-15 | Institution RAG | lee | eom | Knowledge Source | TODO |
| AI-16 | Report Impact Router | lee | eom | Section Schema | TODO |
| AAPI-20 | Report AI API | lee | eom | AI-05 | TODO |
| AAPI-21 | Case Support AI API | lee | eom | AI-06~08 | TODO |
| AAPI-30 | Knowledge/RAG API | lee | eom | AI-12~15 | TODO |

## 4. ham 합류 후 배정 후보

ham의 실제 시작 시점에 남은 Task와 현재 코드 상태를 확인한 뒤 확정한다.

| ID | 작업 | 예정 담당 | 선행 | 상태 |
|---|---|---|---|---|
| BE-02/03 | Case List·Detail·Bundle 확장 | ham | INT-01 | WAITING |
| BE-04 | Conversation·Question·Progress API | ham | AI-06/08 | WAITING |
| BE-05 | Verification·외부 Token API | ham | AI-07/12 | WAITING |
| BE-06 | LIVE/FINAL Report 저장·Version API | ham | AI-05/16 | WAITING |
| BE-07/08 | Action·Recovery·Official Data | ham | DB Schema | WAITING |
| BE-09 | Voice Session API | ham | Voice 결정 | WAITING |
| RT-01 | SSE/WebSocket·Cursor Recovery | ham | Case Event Schema | WAITING |

## 5. 마일스톤

| 마일스톤 | 완료 결과 | 담당 |
|---|---|---|
| M0 Contract | Public/Diagnosis/Report 초기 Contract 합의 | eom + lee |
| M1 Fixture E2E | 실제 Frontend→Backend→Fixture→Case 이동 | eom |
| M2 Real Diagnosis | WindowAI+LLM 병렬 분석으로 Fixture 교체 | eom |
| M3 Initial Report | Case 생성 시 초기 Report 연결 | lee + eom |
| M4 Follow-up AI | Customer/Bank 질문·구조화·Report Patch | lee |
| M5 Backend 확장 | Realtime/Verification/Voice 등 독립 모듈 | ham 합류 후 |

## DONE 공통 기준

- [ ] Request/Response Schema와 Example 확정
- [ ] 정상·빈 입력·오류·Timeout 테스트
- [ ] Secret·민감정보·로그 점검
- [ ] 직접 연결되는 E2E 통과
- [ ] 담당자의 `todo.md`에 테스트와 Commit/PR 기록
