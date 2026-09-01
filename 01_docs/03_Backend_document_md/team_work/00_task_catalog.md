# 전체 작업 카탈로그 · 담당자 배정

> 상세 설계는 상위 `01~07`과 `ai_system_design/**`를 따른다. 이 문서는 전체 Task와 최초 담당 배정만 관리한다.

## 운영 규칙

- 이 파일은 한 명의 조정자만 수정한다.
- 담당자는 자신의 `ham.md`, `eom.md`, `lee.md`에 배정 Task를 복사한다.
- 이후 진행상태·작업 로그는 개인 문서에서만 갱신한다.

## 1. AI 시스템·모델

| ID | 작업 | 핵심 산출물 | 선행 | 담당 | Reviewer | 상태 |
|---|---|---|---|---|---|---|
| AIS-01 | Backend Workflow Orchestrator | Event DAG, 병렬 실행, Retry/Version | Core Backend | TBD | TBD | TODO |
| AI-01 | Full Text Analyzer | 전체 맥락·주장·근거 | Schema | TBD | TBD | TODO |
| AI-02 | Window Analyzer | Segment 위험신호·근거 | Segment 규칙 | TBD | TBD | TODO |
| AI-03 | Feature Extractor | 표준 Context Feature | AI-01/02 | TBD | TBD | TODO |
| AI-04 | Risk Model | risk·score·reason | AI-03, 평가셋 | TBD | TBD | TODO |
| AI-05 | Case Report AI | initialize/update/finalize | AI-01~04, Report Schema | TBD | TBD | TODO |
| AI-06 | Question Planner | P0/P1/P2·Options | Question Schema | TBD | TBD | TODO |
| AI-07 | Verification Planner | 검증 주장·대상·방법 | Verification Schema | TBD | TBD | TODO |
| AI-08 | Case Structurer | 비정형 답변 Field Patch | Case Schema | TBD | TBD | TODO |
| AI-09 | Streaming STT | Partial/Final Transcript | Voice Provider | TBD | TBD | TODO |
| AI-10 | Voice Delta Analyzer | 신규 사실·충돌·Feature 변화 | AI-03/04/09 | TBD | TBD | TODO |
| AI-11 | Voice Summarizer | 상담 요약·미확인사항 | AI-09/10 | TBD | TBD | TODO |
| AI-12 | Verification RAG | 공식 근거·주장 비교 | Source/Vector Pipeline | TBD | TBD | TODO |
| AI-13 | Response RAG | 현재 안전행동 근거 | Source/Vector Pipeline | TBD | TBD | TODO |
| AI-14 | Recovery RAG | 피해구제·후속조치 근거 | Source/Vector Pipeline | TBD | TBD | TODO |
| AI-15 | Institution RAG | 기관 역할·정상절차 근거 | Source/Vector Pipeline | TBD | TBD | TODO |
| AI-16 | Report Impact Router | Event→changed_sections | Report Section 규칙 | TBD | TBD | TODO |

## 2. AI API

| ID | API 묶음 | Endpoint | 담당 | Reviewer | 상태 |
|---|---|---|---|---|---|
| AAPI-01 | 공통 기반 | Health, Error, Schema, Provider Client | TBD | TBD | TODO |
| AAPI-10 | Diagnosis | `/ai/analyze/text`, `/windows`, `/features/extract`, `/risk/predict` | TBD | TBD | TODO |
| AAPI-20 | Report | `/ai/reports/initialize`, `/update`, `/finalize` | TBD | TBD | TODO |
| AAPI-21 | Case Intelligence | `/ai/questions/next`, `/verifications/plan`, `/case/structure` | TBD | TBD | TODO |
| AAPI-30 | Knowledge/RAG | `/ai/rag/search`, `/verify-claim`, `/response-guide`, `/recovery-guide`, `/institution-info` | TBD | TBD | TODO |
| AAPI-40 | Voice | STT Stream, `/ai/voice/analyze-delta`, `/summarize` | TBD | TBD | TODO |

## 3. 일반 Backend·DB·Realtime

| ID | 작업 묶음 | 핵심 산출물 | 담당 | Reviewer | 상태 |
|---|---|---|---|---|---|
| BE-00 | 공통 Backend | Server, Auth, Error, DB Transaction, AI Client | TBD | TBD | TODO |
| DB-01 | Core Schema | cases, inputs, segments, features | TBD | TBD | TODO |
| DB-02 | Interaction Schema | messages, questions, options, progress | TBD | TBD | TODO |
| DB-03 | Report Schema | reports, sections, sources, revision | TBD | TBD | TODO |
| DB-04 | Verification/Action Schema | verification, evidence, actions | TBD | TBD | TODO |
| DB-05 | Voice/Event Schema | sessions, transcript, events | TBD | TBD | TODO |
| DB-06 | Knowledge Data | official_contacts, knowledge_sources, Vector Index | TBD | TBD | TODO |
| BE-01 | Case Analyze | `POST /api/cases/analyze` | TBD | TBD | TODO |
| BE-02 | Case List | `GET /api/cases` | TBD | TBD | TODO |
| BE-03 | Case/Bundle | Detail, Patch, Bundle, Feature, Segment | TBD | TBD | TODO |
| BE-04 | Conversation | Message, Question, Option, Progress, Takeover | TBD | TBD | TODO |
| BE-05 | Verification | 내부 Task, 외부 Token/Response | TBD | TBD | TODO |
| BE-06 | Report | LIVE Section, Refresh, FINAL Revision | TBD | TBD | TODO |
| BE-07 | Action/Recovery | Bank Action, Recovery State/Task | TBD | TBD | TODO |
| BE-08 | Official Data/Evidence | 정확 연락처, Case Evidence 조회 | TBD | TBD | TODO |
| BE-09 | Voice Session | Create, Join, End, Transcript, Summary | TBD | TBD | TODO |
| RT-01 | Case Realtime | Event Envelope, Stream, Cursor Recovery | TBD | TBD | TODO |

## 4. 통합 E2E

| ID | 시나리오 | 포함 영역 | 담당 | Reviewer | 상태 |
|---|---|---|---|---|---|
| INT-01 | Text Diagnosis | Front `/` → BE → AI → DB → Case | TBD | TBD | TODO |
| INT-02 | Case Navigation | List/Entry/Bundle | TBD | TBD | TODO |
| INT-03 | Customer Room | P0/Message/Progress/Recovery | TBD | TBD | TODO |
| INT-04 | Bank Workspace v2 | Brief/Question/Timeline/Evidence/Action | TBD | TBD | TODO |
| INT-05 | Verification/RAG | 내부 Task → 외부 응답 → Evidence/Report | TBD | TBD | TODO |
| INT-06 | Voice | Session → STT → Delta → Report | TBD | TBD | TODO |
| INT-07 | Fragment/Realtime | Section/Item/Event 단위 갱신 | TBD | TBD | TODO |
| INT-08 | FINAL/Full Demo | Recovery/종료/FINAL Revision | TBD | TBD | TODO |

## DONE 공통 기준

- [ ] 구현과 입력·출력 Schema 완료
- [ ] 정상·오류·Timeout·Version Conflict 테스트
- [ ] 민감정보·Secret·권한 점검
- [ ] 직접 연결되는 Contract/E2E 통과
- [ ] 개인 작업 문서에 변경 파일·테스트·Commit/PR 기록
