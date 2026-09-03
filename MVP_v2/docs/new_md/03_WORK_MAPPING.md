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

첨부파일은 Frontend가 선택·대기열·전송 상태·미리보기·다운로드 UI를 소유하고, Backend가 파일 검증·저장·메타데이터·공개 범위·접근 권한을 소유한다. AI 담당자는 Backend가 허용한 첨부만 대상으로 문서 파싱/OCR/추출 결과와 RAG 색인을 구현한다. 서버의 실제 저장 경로는 Frontend 응답에 노출하지 않는다.

음성 통화 상담은 모든 담당자의 현재 작업 범위에서 제외한다. 기존 voice 코드는 휴면 참고 코드로 취급하고, Product가 별도 후속 PRD를 승인하기 전에는 활성 라우트·Acceptance Criteria·완료율에 포함하지 않는다.

고객 Frontend 단일 진입점은 `frontend/src/pages/CustomerChatPage.tsx`다. 고객 공개 카드 조각은 `frontend/src/features/mvp-chat/customer-cards`, 공용 Chat Shell은 `frontend/src/features/mvp-chat/ChatWorkspace.tsx`에서 관리한다. 별도 CustomerPage·SafetyRoom·목데이터 고객 화면을 새로 만들지 않으며, 기존 기능을 가져올 때는 이 정본 컴포넌트의 카드 또는 상태 projection으로 병합한다. 개발 서버 기준 포트는 `5175`이고 `strictPort`로 중복 Vite 인스턴스의 자동 포트 변경을 금지한다.
