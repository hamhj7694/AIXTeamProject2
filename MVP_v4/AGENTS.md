# CSR V4 작업 진입 규칙

직접 사용자 요청 > docs/00_SOURCE_OF_TRUTH.md > docs/01_PRD.md > V4 계약/코드 순서다.
모든 작성은 MVP_v4 내부만 허용한다. MVP_v3는 AI 이식 경계의 read-only 참고다.
실제 .env 및 .env.*는 열람/검색/출력/복사/생성 금지. .env.example만 허용한다.
Secret은 `[USER_SECRET_REQUIRED]`와 변수명만 보고한다.

## 재개 순서
1. 이 파일
2. docs/00_SOURCE_OF_TRUTH.md
3. docs/03_IMPLEMENTATION_STATUS.md
4. docs/06_TODO.md
5. docs/07_WORK_MAPPING.md
6. docs/08_HANDOFF_CHECKPOINT.md
7. git status / diff (Secret 경로 제외)
8. NEXT_EXACT_STEPS의 코드와 테스트만 확인하여 진행한다. 전체 재감사 금지.

## 작업 단위
- 고유 Task ID: P<phase>-<number>.
- 시작: Status IN_PROGRESS 및 Handoff CURRENT_TASK 기록.
- 구현 범위 변경: Mapping 즉시 갱신.
- 구현 → 테스트 → Status/TODO/Mapping/Handoff 즉시 갱신.
- 각 Phase는 typecheck/build/backend/contract/regression gate 통과 후 진행.
- 미실행/실패/fixture 검증을 실제 서비스 성공으로 표시하지 않는다.
- 다음 큰 작업을 안전하게 끝낼 수 없으면 현재 작업을 clean state로 정리하고 checkpoint.
- 자동 push 금지. 기존 staged/unstaged 사용자 변경 보존.

## Runtime 원칙
- 코드/모델/prompt/RAG/migration 모두 V4 내부로 실제 이식. 외부 로컬 의존, symlink, 경로 주입 금지.
- Browser /api → General API 8100 → AI API 8101. Python 3.11, MySQL 별도 V4 DB.
- AI는 Conversational Core + 최소 DIRECT/RAG/TOOL/AGENT 경로, rule/state/policy 우선.
- Task 단일 업무 원본. Progress 별도. 부작용과 고객 심화질문 발송은 서버 검증/직원 승인.
- Structured Case 변경만 revision/fingerprint polling + ID merge. draft/focus/cursor/selection/IME 보존.
- 상시 Live Report 없음. Brief 제한 trigger, Final Report 종료 시.
- UUID는 frontend/src/shared/uuid.ts의 createUuid만 호출.
- 최종 완료는 독립 복사 clean install/migration/build/health/E2E 검증 이후.
