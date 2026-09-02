# ham 작업 매핑 — C Realtime & Service Integration Engineer

## 역할

ham은 Backend와 AI 결과를 실제 React 화면, Realtime 흐름, Demo 실행환경에 연결한다.

## 향후 소유 영역

```text
02_workspace/frontend/**
02_workspace/backend/docker/**
Frontend API Client·Adapter
SSE/WebSocket Client·통합 E2E·실행환경·배포
Verification/FDS/ASAP Mock Adapter
```

## 핵심 책임

- React↔FastAPI 연결과 화면별 server state
- Customer↔Bank 동일 Case 실시간 동기화
- Event 구독·재접속·중복·순서 처리
- Human Takeover/Resume AI 연결
- Verification·FDS·ASAP Mock을 명시적 Adapter로 제공
- 통합 Error/Loading/Empty UI
- Browser E2E, Docker Compose, Demo·배포

## 작업 순서

| Phase | 목표 | 대상 | 완료 조건 |
|---|---|---|---|
| C-0 | 화면 Data Source 감사 | router/pages/features | API/Mock/localStorage Map |
| C-1 | Case API Adapter 안정화 | `caseApi.ts`, Case pages | Analyze/List/Detail 회귀 |
| C-2 | Customer/Bank 연결 | CustomerPage/ManagerRoom | 동일 Case message/status 반영 |
| C-3 | 외부 Mock Adapter | Verification/FDS/ASAP | Mock 경계·Scenario fixture |
| C-4 | Realtime | stream client/state | 재접속·중복·순서 E2E |
| C-5 | Takeover/Resume | Customer/Bank UI | 서버 상태 기반 동기화 |
| C-6 | 통합 E2E | Browser test | 핵심 Demo Scenario 자동화 |
| C-7 | 실행환경·배포 | docker/config | 4개 서비스 cold start·health |

## 수정하지 않을 영역

- `backend/migrations/**`, DB Schema
- `backend/ai_api/**` Prompt·Agent·RAG 내부 구현
- eom·lee 개인 작업 문서

새 Event가 필요하면 화면 갱신 요구를 먼저 정의하고 A/B/C가 Contract를 합의한다. 새 AI output이 필요하면 B에게 요구하며 Frontend에서 임의 값을 만들어 실제 결과처럼 표시하지 않는다.

## 과거 구현 기여

ham의 Manager Room·Frontend 통합·merge 기여 기록은 유지한다. 과거 `PAUSED` 표시는 폐기하고 새 C 역할을 현재 책임으로 사용한다.

## Codex 수칙

1. Router·Page·Mock·API Client의 실제 연결 상태를 먼저 확인한다.
2. Mock 제거 전 동일 동작의 API 또는 Fixture를 확인한다.
3. DB Schema와 AI Prompt를 직접 수정하지 않는다.
4. Realtime은 재접속·중복·순서 역전을 반드시 고려한다.
5. E2E에서 Customer와 Bank의 동일 Case 상태를 함께 검증한다.

## 작업 Branch

`new_ham`을 사용한다. 기능별 Branch를 추가 생성하지 않고 최신 `main`을 merge 방식으로 반영한다.
