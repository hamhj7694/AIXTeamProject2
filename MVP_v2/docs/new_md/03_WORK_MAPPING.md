# 역할별 작업 매핑

| 역할 | 소유 영역 | 필수 협업 |
|---|---|---|
| Orchestrator | 요구사항·순서·통합·릴리스 | 모든 역할 |
| Frontend | `frontend/src/**` | Backend 계약, UI/UX 검토 |
| Backend | `backend/general_api/**`, `contracts/public_api/**` | 데이터·Frontend |
| AI | `backend/ai_api/**`, `contracts/ai_internal/**` | Backend, Product |
| UI/UX | 화면 규칙·접근성·시각 검수 | Frontend |
| Product | PRD·우선순위·Acceptance Criteria | Orchestrator |
| Service Reviewer | 사용자 관점·정보 노출 검토 | Product, Frontend |
| Debugger | 재현·원인분석·최소수정·검증 | 변경 소유자 |
| User Liaison | 사용자 피드백·시연·결정 전달 | Orchestrator |

작업 순서는 계약/스키마 → Backend → AI → Frontend → UI/UX → Debugger/E2E다.

개인 메모와 북마크는 Backend가 공개 계약·SQLite 저장소를 소유하고 Frontend가 카드·바로가기 UI를 소유한다. AI는 개인 메모를 기본 입력으로 사용하지 않으며, 사용자가 명시적으로 공유 또는 Fact 후보 전환한 내용만 이용한다.
