# 프론트엔드 우선 재설계 작업공간

작성일: 2026-09-18  
기준 브랜치: `v3.1-ham3`

이 폴더는 기존 API·백엔드 계약과 분리된 **새 프론트엔드 설계 자료의 단일 작업공간**이다.

## 작업 원칙

- 좌측·중앙·우측 큰 화면 구획은 유지한다.
- 새 화면은 우선 mock View Model로 설계한다.
- 기존 Context/Fact/Question 카드 UI는 새 화면에서 렌더링하지 않는다.
- 우측 패널은 현재 빈 레이아웃만 유지한다.
- 백엔드 API는 새 View Model이 승인될 때까지 변경하지 않는다.
- 새 API 계약은 화면 설계가 확정된 뒤 별도 작성한다.
- 기존 문서는 삭제·덮어쓰기하지 않고 `legacy_reference/`에서 참고 목록으로 관리한다.

## 이 폴더의 문서

1. `01_FRONTEND_FIRST_DESIGN.md` — 새 화면의 목적·범위·레이아웃
2. `02_FRONTEND_VIEW_MODEL_DRAFT.md` — 백엔드 확정 전 임시 View Model 초안
3. `03_FRONTEND_REBUILD_CHECKLIST.md` — 사람/Codex 공동 체크리스트
4. `legacy_reference/README.md` — 기존 계약·A파트 문서의 참고 위치와 사용 규칙

## 현재 프론트 foundation 상태

- 은행 Case Room의 좌측·중앙·우측 레이아웃은 유지된다.
- 중앙에는 일반 메시지만 표시된다.
- 질문·답변·기관 확인·업무·최종 보고서 카드는 표시하지 않는다.
- 우측 사건 맥락 패널은 제목과 빈 영역만 표시한다.
- 기존 `ContextPanelV3`와 기존 카드 컴포넌트는 삭제하지 않고 legacy 경로로 보존한다.

이 상태는 최종 제품이 아니라 새 계약을 설계하기 위한 기초 화면이다.
