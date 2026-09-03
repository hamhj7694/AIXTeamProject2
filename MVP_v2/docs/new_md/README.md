# CONTEXT-FIRST CASE MVP_v2 개발 문서

상위 기준: `../CONTEXT_FIRST_CASE_MVP_v2_PRD_2026-09-03.md`

1. `01_PRD.md` 제품 목표·사용자·범위 요약
2. `02_TODO.md` 프론트·백엔드·AI 실행 상태
3. `03_WORK_MAPPING.md` 역할별 소유 영역과 작업 순서
4. `04_WORK_RULES.md` 계약·보안·UI·검증 규칙
5. `05_DATA_SCHEMA_AND_FLOW.md` Case 중심 데이터 계약과 이벤트 흐름
6. `06_LIVE_DETAILED_IMPLEMENTATION_TODO.md` 계약·API·컴포넌트·검증 단위의 실시간 세부 실행 백로그
7. `07_WORK_CARD_CATALOG.md` Chat-first 업무 카드 종류·상태·호출 계약·완료 기준
8. `WorkDetails/260903_part1/260903_part1.md` 2026-09-03 Frontend-first 1차 목표
9. `WorkDetails/260903_part1/260903_part1_rog.md` 구현 완료 순서와 점검 로그

상위 PRD가 변경되면 이 폴더의 문서를 같은 작업에서 갱신한다.

## 문서 역할과 중복 방지

- 상위 PRD는 제품 요구의 유일한 정본이다. `01_PRD.md`는 구현자가 빠르게 확인하는 요약본이며 새 요구의 원본으로 사용하지 않는다.
- `02_TODO.md`는 분야별 진행도, `06_LIVE_DETAILED_IMPLEMENTATION_TODO.md`는 구현 가능한 최소 단위의 실시간 백로그다.
- `WorkDetails/**`는 완료 순서와 검증 증거를 보존하는 이력이며 현재 요구사항을 대신하지 않는다.
- 같은 역할의 `*_copy`, `old`, `backup`, 별도 버전 문서를 만들지 않고 Git 이력으로 복구한다.
