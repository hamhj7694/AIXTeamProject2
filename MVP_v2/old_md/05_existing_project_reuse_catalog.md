# 기존 프로젝트 재활용 Catalog

> 기준 경로: `02_workspace`  
> 목적: MVP_v2에서 그대로 재활용할 것, 참고만 할 것, 새로 만들어야 할 것을 구분한다.

## 1. Route 전략

| 기존 화면 | MVP_v2 판단 | 이유 |
|---|---|---|
| `/` 통화 텍스트 진단 | 스타일·흐름 재활용 | Case 생성 진입점으로 충분함 |
| `/cases` Case List | 스타일·API 재활용 | 최신 Case 목록과 진입 흐름 유지 |
| `/cases/:caseId` Entry | 단순화하여 재활용 | 고객·은행 Room 선택 또는 바로 진입 |
| Customer Page | API 흐름 참고, UI 신규 | 기존 Layout은 Chat-first 목적과 다름 |
| Manager Room | API 흐름 참고, UI 신규 | 기존 Dashboard/Mock 비중이 큼 |
| Verification Page | API 흐름 참고, Card로 흡수 | MVP_v2에서는 Chat/Log에서 요청·결과 표시 |

## 2. Frontend 재활용 후보

| 기존 파일 | MVP_v2에서의 사용 | 판단 |
|---|---|---|
| `frontend/src/services/caseApi.ts` | Root·List·Case 기본 조회 | 그대로 재활용 후보 |
| `frontend/src/services/caseWorkflowApi.ts` | Bundle, Message, Verification, Action, Takeover, Voice API | 타입을 MVP_v2 Contract에 맞춰 확장 |
| `frontend/src/services/conversationApi.ts` | Message 목록과 Event Cursor 조회 | `caseWorkflowApi`와 통합 검토 |
| `frontend/src/features/case-state/useCaseEventRefresh.ts` | Polling 기반 Event Refresh | MVP 시작점으로 재활용 |
| `frontend/src/components/ui/**` | Button, Card, Badge, Dialog | 선별 재활용 |
| `frontend/src/components/layout/**` | Root/List용 Header·Layout | 선별 재활용 |
| `frontend/src/pages/CustomerPage.tsx` | Customer Message 저장·Bundle 사용 방식 | 데이터 흐름만 참고 |
| `frontend/src/features/manager-room/ManagerRoom.tsx` | Bank Bundle·Message·Takeover 사용 방식 | 데이터 흐름만 참고 |
| `frontend/src/pages/CaseVerificationPage.tsx` | Verification 생성·목록 UI 흐름 | Card 설계 참고 |
| `frontend/src/components/voice/VoiceCallPopup.tsx` | 후순위 Voice Session UI | 나중에 선별 재활용 |
| `frontend/src/data/mock/**` | Storybook/Demo Fixture | 실제 API 데이터로 표시 금지 |

## 3. Backend 재활용 후보

| 기존 파일·영역 | 현재 제공 기능 | MVP_v2 활용 |
|---|---|---|
| `backend/general_api/app/main.py` | Public Case·Message·Event·Verification·Action·Report API | Backend 출발 기준선 |
| `backend/general_api/app/domains/cases/repository.py` | Memory Repository와 Workflow Resource 경계 | 새 Entity Method 추가 위치 |
| `backend/general_api/app/domains/cases/mysql_repository.py` | MySQL Case 저장과 Transaction | MVP_v2 Migration 후 확장 |
| `backend/contracts/public_api/case_activity.py` | Message·Event DTO | Channel·Audience·Mention DTO로 확장 |
| `backend/contracts/public_api/case_workflow.py` | Verification·Action·Bundle·Voice·Report DTO | Member·Presence DTO 추가 위치 |
| `backend/migrations/001~007` | Core Case, Message, Verification, Action, Version, Voice Table | 새 Migration의 기준선 |
| `backend/ai_api/app/domains/case_support/**` | Brief·질문·답변 구조화·Agent Router | `@CaseCopilot` 내부 호출의 초기 기반 |
| `backend/ai_api/app/domains/diagnosis/**` | 텍스트 진단·Feature·Risk | Root 진단 유지 |

## 4. 현재 코드의 한계와 MVP_v2 신규 작업

| 요구사항 | 기존 상태 | MVP_v2 조치 |
|---|---|---|
| 팀/고객/AI 채널 | `actor_type`만 존재 | `channel`, `audience` 추가 |
| 멘션 기반 AI 호출 | 없음 | Mention Parse + Invocation API |
| 참여자 역할 | Voice Session participants만 있음 | `case_members` 추가 |
| 보고 중·입력 중 상태 | 없음 | TTL 기반 `case_presence` 추가 |
| AI 자동응답 제어 | 없음 | 명시 호출 Policy 추가 |
| Chat Block | 문자열 Message 중심 | Block Renderer와 Source Entity 연결 |
| 은행 Live Log | Event API 존재 | Log Row Mapping UI 추가 |
| 실시간 Transport | 2초 Polling | MVP Polling 유지 후 SSE/WS 전환 |
| 질문 Entity | Bundle에 빈 배열 | Question 저장·승인·전송 Contract 구현 |
| 실제 RAG | 없음 | 후순위 Pipeline 연결 |

## 5. 복사 전 확인사항

- `MVP_v2`는 기존 프로젝트와 별도 Port·DB 이름·환경변수 Prefix를 사용한다.
- `.env`의 Secret을 복사하거나 Commit하지 않는다. `.env.example`만 기준으로 새 환경을 만든다.
- 기존 `node_modules`, `dist`, Python Cache는 복사 대상이 아니다.
- 기존 Mock 파일은 MVP_v2 Demo Fixture로 격리하고 화면에 Mock임을 표시한다.
- 기존 API Contract를 변경하기 전에는 A(Backend)·B(AI)·C(Frontend) 영향도를 먼저 확인한다.
- 중복된 API Client를 계속 늘리지 않고 MVP_v2에서 하나의 `caseApi` 경계로 정리한다.

