# lee 담당 작업 매핑

## 역할

lee는 **Frontend·General API·DB 통합 담당자**다. 사용자 입력부터 공개 API, 결정론적 Backend Workflow, AI API 호출, DB 저장, 화면 응답과 E2E까지 소유한다.

## 소유 영역

```text
02_workspace/frontend/**
02_workspace/backend/general_api/**
02_workspace/backend/contracts/public_api/**
02_workspace/backend/migrations/**
Frontend↔General API Contract·통합 테스트
```

## 핵심 책임

- Frontend API Client, 상태 관리, Loading·Empty·Error UI
- 공개 REST·SSE/WebSocket Contract의 최종 편집
- General API 입력·권한·Version 검증과 Workflow
- eom의 AI API를 호출하는 Client·Timeout·Retry·Circuit Breaker
- AI 결과 Schema 검증·정규화 후 MySQL 저장
- Case·Report·Conversation·Verification·Voice 공개 API
- Fixture E2E와 실제 AI E2E

## 담당 Task

| Task ID | 작업 | 산출물 | Reviewer |
|---|---|---|---|
| HANDOFF-01 | 기존 Vertical Slice 인계 | 실행·코드 이해·회귀 테스트 | eom |
| CT-01 | Public Analyze Contract | `/api/cases/analyze` Schema | eom |
| FE-01~09 | Frontend API 연동 | Root·Case·Customer·Bank v2·Voice·Report | eom은 AI 필드만 Review |
| BE-00~12 | General API | Workflow·AI Client·공개 Endpoint | eom은 내부 Contract만 Review |
| DB-01~15 | 서비스 DB | Migration·Repository·Version | eom은 AI 결과 필드만 Review |
| RT-01~05 | Realtime·Voice 연결 | Event·RTC·STT 연결 Workflow | eom은 AI Endpoint만 Review |
| INT-01~10 | 통합·E2E | Fixture와 실제 AI 전체 흐름 | eom |

## 수정하지 않을 영역

- `02_workspace/backend/ai_api/**`
- `02_workspace/backend/contracts/ai_internal/**`
- AI Model artifact·Prompt·RAG Retriever·AI 평가 구현
- eom·ham의 개인 작업 문서

AI 응답이 요구사항을 충족하지 않으면 General API에서 임의 필드를 생성해 숨기지 않고, 실패를 재현하는 Fixture와 함께 eom에게 내부 Contract 변경을 요청한다.

## 권장 브랜치

```text
lee/handoff-initial-slice
lee/public-case-contract
lee/general-case-api
lee/frontend-case-integration
lee/mysql-persistence
lee/realtime-integration
```
