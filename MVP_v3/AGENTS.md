# MVP_v3 작업 지침

이 지침은 `MVP_v3` 아래의 모든 파일과 폴더에 적용한다.

## 작업 시작 전

1. `docs/03_IMPLEMENTATION_STATUS.md`를 가장 먼저 읽는다.
2. 요청과 관련된 `PRD.md`, `CUSTOMER_PRD.md`, 설계 문서를 확인한다.
3. 문서만 믿지 말고 실제 Frontend·General API·AI API·DB 계약과 테스트를 대조한다.
4. `docs/03_IMPLEMENTATION_STATUS.md`의 서비스 원칙과 P0 → P1 → P2 순서를 기본 우선순위로 삼는다.

## 구현 원칙

- AI는 은행 직원의 결정을 대신하지 않는다.
- 미확인 고객 답변과 공식 확인 사실을 구분한다.
- 고객 공개 데이터와 은행 내부 데이터를 분리한다.
- 내부 변수명·코드명·민감정보를 사용자 화면에 노출하지 않는다.
- Frontend는 General API를 통해서만 AI 기능을 사용한다.
- 직원 편집본과 결정권을 AI 자동 갱신으로 덮어쓰지 않는다.
- 실제 외부 업무를 실행하지 않았으면 완료된 것처럼 표시하지 않는다.
- 기존 사용자 변경과 관련 없는 파일을 되돌리거나 삭제하지 않는다.

## 작업 완료 전

1. 변경 범위에 맞는 Backend 테스트와 Frontend typecheck/build를 실행한다.
2. 필요한 기능은 실제 브라우저·MySQL 통합 검증까지 수행한다.
3. 실제로 검증하지 않은 LLM, RAG, 인증, 외부 시스템 기능을 완료로 표시하지 않는다.
4. `docs/03_IMPLEMENTATION_STATUS.md`의 완료 범위, 다음 작업, 검증 수치, 남은 경고를 갱신한다.
5. 세부 체크 이력이 필요하면 `docs/02_DETAILED_TODO.md`도 함께 갱신한다.
