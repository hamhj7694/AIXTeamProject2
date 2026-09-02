# Backend · AI 개발 문서 안내

> 기준일: 2026-09-02
> 판단 우선순위: 실제 코드 → 실제 폴더 구조 → 현재 실행 흐름 → 최신 문서 → 과거 계획

## 문서 구조

| 문서 | 역할 |
|---|---|
| `01_general_backend_architecture.md` | A=eom의 General API·Case Platform 목표 구조 |
| `02_ai_api_architecture.md` | B=lee의 AI API·Agent·RAG 목표 구조 |
| `03_data_db_architecture.md` | A=eom의 MySQL·Event·Report 데이터 구조 |
| `04_full_development_integration.md` | C=ham의 화면·서비스 통합과 E2E 기준 |
| `05_task_mapping.md` | 공용 Task ID, 현재 상태, 책임자, 의존성 |
| `06_progress_todo.md` | 프로젝트 전체 구현 현황과 통합 Backlog |
| `07_frontend_backend_connection_schema.md` | Frontend↔Backend 연결 Contract |
| `ai_system_design/**` | AI 기능별 설계와 안전 경계 |
| `team_work/00_task_catalog.md` | 남은 실행 작업과 마일스톤 |
| `team_work/{worker}/task_mapping.md` | 개인 책임·금지 영역·작업 순서 |
| `team_work/{worker}/todo.md` | 개인 P0~P3 체크리스트와 작업 로그 |

## 현재 코드 기준선

- 구현: React routing·진단·Case 목록/상세, FastAPI 2계층, Analyze/List/Get API, Window ML, Context Feature, Risk Fusion, 초기 Brief/LIVE Report, Memory/MySQL Repository와 Core Migration.
- 부분 구현: Case CRUD(Create/List/Get), MySQL 실행 검증, Event(CASE_CREATED), LLM Brief, Backend test/E2E.
- Mock: Customer/Bank/Verification 업무 상태, FDS, Human Takeover, Customer↔Bank 동기화.
- 미구현: Message/Question/Verification/Action API, Agent, RAG, SSE/WebSocket, Browser E2E, Docker/Deployment.

문서에 설계가 있다는 이유만으로 구현 완료로 판단하지 않는다. 완료 여부는 코드, 실행 흐름, 테스트 기록을 함께 확인한다.

## 새 역할

| 구분 | 담당자 | 역할 | 주 소유 영역 |
|---|---|---|---|
| A | eom | Backend & Case Platform Engineer | `backend/general_api`, `contracts/public_api`, `migrations` |
| B | lee | AI & Multi-Agent Engineer | `backend/ai_api`, `contracts/ai_internal`, AI 모델·평가 |
| C | ham | Realtime & Service Integration Engineer | `frontend`, Realtime, Mock Adapter, E2E, Docker |

- A는 데이터·상태·공개 Backend Contract를 책임진다.
- B는 Case 분석·질문·검증 판단과 AI Output Contract를 책임진다. DB를 직접 Query하지 않는다.
- C는 Backend/AI 결과를 화면과 실행환경에 연결한다. DB Schema와 AI 내부 로직을 직접 변경하지 않는다.
- 과거 구현 기여자는 Git·작업 로그에 보존하고, 향후 책임자와 구분한다.

## 공통 작업 규칙

1. 작업 전에 실제 코드와 관련 MD를 읽는다.
2. 기존 구현을 무시한 새 구조나 대규모 리팩터링을 만들지 않는다.
3. 담당 영역 밖 파일은 임의 수정하지 않는다.
4. 공용 Contract 변경은 영향받는 담당자와 먼저 합의한다.
5. Provider는 Schema·Example·Fixture·Contract Test를 함께 제공한다.
6. Mock은 코드·화면·문서에 Mock이라고 표시한다.
7. 테스트하지 않은 기능을 `DONE`으로 표시하지 않는다.
8. 작업 후 변경 파일, 테스트 결과, 미검증 항목, 다음 작업을 개인 TODO에 기록한다.

## 상태 값

`TODO / IN_PROGRESS / REVIEW / DONE / BLOCKED / MOCK / DESIGN_ONLY / VERIFY_REQUIRED`

`DONE`은 구현, Contract, 오류 처리, 테스트, 연동 확인이 모두 끝난 상태다.
