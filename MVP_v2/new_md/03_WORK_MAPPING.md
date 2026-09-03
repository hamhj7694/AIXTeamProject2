# 에이전트 작업 매핑

## 읽는 순서

1. new_md/01_PRD.md
2. new_md/02_TODO.md
3. new_md/03_WORK_MAPPING.md
4. new_md/04_WORK_RULES.md

## 역할별 소유 영역

| 역할 | 주 소유 영역 | 변경 전 확인 |
|---|---|---|
| Orchestrator | 요구사항 분해, 작업 순서, 검증 | PRD와 TODO |
| Frontend | frontend/src/pages, features/mvp-chat, services | API 계약과 routes |
| Backend | backend/general_api, contracts/public_api, 저장소 | 공개 응답 계약과 migration |
| AI | backend/ai_api, contracts/ai_internal | 입력/출력 스키마와 안전성 |
| UI/UX | 정보 구조, 상태 문구, 접근성 | 사용자 흐름과 PRD |
| Product | 우선순위, 완료 정의, 데이터 의미 | PRD |
| User liaison | 사용자 요구 수집과 결과 전달 | 확정/미확정 구분 |
| Service reviewer | 사용자 여정, 역할별 정보 노출, 완료 기준 점검 | PRD, UI/UX 흐름, 실제 화면 |
| Debugger | 실행 오류 재현, 원인 분석, 최소 수정 및 회귀 검증 | 로그, API 계약, 테스트, 영향을 받은 화면 |

## 기능별 변경 경로

| 기능 | 프론트 | 백엔드/계약 | AI |
|---|---|---|---|
| 분석과 Case 생성 | Case entry, caseApi | analyze endpoint, Case service | diagnosis |
| Case 목록 | CasesTablePage | cases list, case read contract | 없음 |
| 피해 결과 | 목록/고객/은행 | outcome endpoint | 고객 Agent 후속 |
| 은행 협업 | BankCollaborationPage, mvpChatApi | messages/members/presence | AgentRouter |
| 검증 | CaseVerificationPage | verification endpoint | Verification Agent 후속 |
| 보고서 | BankCollaborationPage | final report endpoint | 보고서/RAG 후속 |
| Case 휴지통 | CasesTablePage | trash/delete/restore | 없음 |

## 공통 영역

- backend/contracts: 공개 계약 변경 시 프론트와 테스트를 같이 수정한다.
- backend/general_api/app/main.py: 라우트 충돌과 응답 모델을 확인한다.
- frontend/src/router/routes.tsx: 기존 URL 호환성을 유지한다.
- frontend/src/services: API 호출과 응답 변환의 단일 진입점이다.
- frontend/src/data/mock: 운영 화면에 새 목데이터 의존성을 추가하지 않는다.

## 구현 순서

1. Product와 Orchestrator가 완료 기준을 확정한다.
2. Backend가 계약과 저장 모델을 먼저 정의한다.
3. AI가 계약에 맞는 구조화 결과를 제공한다.
4. Frontend가 services를 통해 연결한다.
5. UI/UX 검토 후 build와 API 테스트를 실행한다.
6. TODO 상태와 문서를 갱신한다.
7. Service reviewer가 사용자 관점의 수용 기준을 점검하고, Debugger가 발견된 오류의 재현·회귀 검증을 남긴다.
