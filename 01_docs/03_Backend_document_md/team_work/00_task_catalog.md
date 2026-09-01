# 전체 작업 카탈로그 · 새 2인 배정

> 상세 설계: 상위 `01~07`, `ai_system_design/**`
>
> 개인 진행상황: `eom/todo.md`, `lee/todo.md`
>
> ham 상태: 현재 작업 범위에서 제외(`PAUSED`)

## 1. 코드 소유권

| 영역 | 소유자 | Reviewer·소비자 |
|---|---|---|
| `02_workspace/backend/ai_api/**` | eom | lee |
| `02_workspace/backend/contracts/ai_internal/**` | eom | lee |
| `02_workspace/frontend/**` | lee | eom은 AI 연결 계약만 Review |
| `02_workspace/backend/general_api/**` | lee | eom은 AI Client 계약만 Review |
| `02_workspace/backend/contracts/public_api/**` | lee | eom |
| `02_workspace/backend/migrations/**` | lee | eom은 AI 결과 저장 필드만 Review |
| Root Dependency·Docker·공통 DTO | Task별 1명 지정 | 상대방 필수 Review |
| ham 코드 영역 | 현재 없음 | 합류 시 재배정 |

## 2. 계약 소유권

| Contract | 최종 편집자 | 필수 Review | 호환성 기준 |
|---|---|---|---|
| Frontend ↔ General API 공개 Contract | lee | eom | Frontend View와 HTTP 상태 |
| General API ↔ AI API 내부 Contract | eom | lee | Fixture·Schema·Timeout·부분 실패 |
| DB Schema·Migration | lee | eom | AI source/evidence/version 저장 가능 여부 |

공유 Python DTO가 하나의 파일에 섞여 있으면 공개 DTO와 내부 DTO를 분리한다. 분리 전까지는 변경 PR에 양쪽 Review가 반드시 필요하다.

## 3. 최초 진단 인계·활성 작업

| 순서 | ID | 작업 | 현재 담당 | Reviewer | 상태 |
|---|---|---|---|---|---|
| 0 | HANDOFF-01 | 기존 Vertical Slice 소유권 인계·회귀 테스트 | lee | eom | TODO |
| 1 | CT-01 | `/api/cases/analyze` 공개 Contract 유지·확장 | lee | eom | IN_PROGRESS |
| 1 | CT-02 | Diagnosis AI 내부 Contract 유지·확장 | eom | lee | IN_PROGRESS |
| 2 | AI-01 | Full Context Diagnosis LLM | eom | lee | IN_PROGRESS |
| 2 | AI-02 | WindowAI Segment Analyzer | eom | lee | IN_PROGRESS |
| 2 | AI-03 | Feature Extractor | eom | lee | IN_PROGRESS |
| 2 | AI-04 | Risk/Fusion 모델·규칙 | eom | lee | IN_PROGRESS |
| 2 | AAPI-10 | Diagnosis AI API·Fixture·Contract Test | eom | lee | IN_PROGRESS |
| 2 | BE-00 | General API 공통 Error·AI Client | lee | eom | IN_PROGRESS |
| 2 | DB-01 | Case Core Schema·MySQL Repository | lee | eom | IN_PROGRESS |
| 2 | FE-01 | `/` API Client·Loading·Error·Navigate | lee | eom | IN_PROGRESS |
| 3 | BE-01 | `POST /api/cases/analyze` Workflow·저장 | lee | eom | IN_PROGRESS |
| 4 | INT-01 | `/` → Case 생성 → 상세 이동 E2E | lee | eom | IN_PROGRESS |

기존 구현 여부와 새 소유권은 별개다. 완료된 코드도 `HANDOFF-01`에서 새 소유자가 읽고 회귀 테스트한 뒤 인계를 완료한다.

## 4. 후속 AI 작업 — eom

| ID | 작업 | 선행 | 상태 |
|---|---|---|---|
| AI-05 | Initial/LIVE/FINAL Case Report AI | Case Projection Contract | TODO |
| AI-06 | P0/P1/P2 Question Planner | Question Contract | TODO |
| AI-07 | Verification Planner | Verification Contract | TODO |
| AI-08 | Customer Answer Case Structurer | Case Patch Contract | TODO |
| AI-09~11 | STT·Voice Delta·Voice Summary | Voice Contract | TODO |
| AI-12~15 | Verification·Response·Recovery·Institution RAG | Knowledge Source | TODO |
| AI-16 | Report Impact Router | Report Section Contract | TODO |
| AAPI-20 | Report AI API | AI-05/16 | TODO |
| AAPI-21 | Case Support AI API | AI-06~08 | TODO |
| AAPI-30 | Knowledge/RAG API | AI-12~15 | TODO |

## 5. 후속 통합 작업 — lee

| ID | 작업 | 선행 | 상태 |
|---|---|---|---|
| BE-02/03 | Case List·Detail·Bundle API | DB-01 | TODO |
| BE-04 | Conversation·Question·Progress API | AI-06/08 Contract | TODO |
| BE-05 | Verification·외부 Token API | AI-07/12 Contract | TODO |
| BE-06 | LIVE/FINAL Report 저장·Version API | AI-05/16 Contract | TODO |
| BE-07/08 | Action·Recovery·Official Data | DB Schema | TODO |
| BE-09 | Voice Session API | AI-09~11 Contract | TODO |
| BE-10/12 | AI Client·결정론적 Workflow 확장 | 각 AI Contract | TODO |
| BE-11 / RT-01 | SSE/WebSocket·Cursor Recovery | Case Event Schema | TODO |
| FE-02~09 | Case·Customer·Bank v2·Verification·Voice UI 연결 | 해당 Public API | TODO |
| DB-02~15 | 서비스 DB Schema·Migration·Repository | 해당 Public API | TODO |
| INT-02~10 | 화면별 통합·E2E | 해당 기능 | TODO |

## 6. ham 상태

ham은 현재 작업에서 제외한다. 기존 후보 Task도 자동 배정하지 않는다. 합류 요청이 생기면 그 시점의 `main`, 남은 Task, eom·lee 소유권을 확인하고 별도 재배정한다.

## 7. 마일스톤

| 마일스톤 | 완료 결과 | 담당 |
|---|---|---|
| M0 Contract Freeze | Public v1과 AI Internal v1 Example·Error 정책 합의 | lee + eom |
| M1 Ownership Handoff | 기존 Vertical Slice를 lee가 실행·회귀 검증 | lee |
| M2 AI Hardening | WindowAI+LLM 품질·Timeout·부분 실패 검증 | eom |
| M3 Persistence E2E | General API·MySQL·Frontend 실제 연결 | lee |
| M4 Follow-up Parallel | eom은 후속 AI, lee는 Fixture 기반 공개 API·UI 병렬 구현 | eom + lee |
| M5 Real AI Integration | Fixture를 실제 AI API로 교체하고 Contract/E2E 통과 | lee + eom |
| M6 Ham Replan | 필요할 때만 독립 모듈 재배정 | 미정 |

## DONE 공통 기준

- [ ] Request/Response Schema와 Example 확정
- [ ] 제공자 Contract Test와 소비자 Contract Test 통과
- [ ] 정상·빈 입력·오류·Timeout·부분 실패 테스트
- [ ] Secret·민감정보·로그 점검
- [ ] Fixture E2E와 실제 AI E2E 모두 통과
- [ ] 담당자의 `todo.md`에 테스트와 Commit/PR 기록
