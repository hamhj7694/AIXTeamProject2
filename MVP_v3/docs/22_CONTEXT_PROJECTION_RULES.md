# Context V3 Projection 정리 기준

작성일: 2026-09-15

## Projection 책임

`build_context_panel_v3`는 canonical resource를 은행/고객 화면용 7개 Section으로 변환한다. 중앙 채팅의 Timeline 카드 문구나 AI 내부 snapshot을 입력으로 사용하지 않는다.

## 은행 화면

- Fact는 semantic key에 따라 피해·노출, 사칭·접촉, 사기 정황으로 배치한다.
- REJECTED Fact는 `archived` 그룹에만 배치하고 활성 목록에서 제외한다.
- SUPERSEDED Fact는 현재 목록에서 제외한다.
- Verification은 상태별 lane으로 배치한다.
- `actions`의 은행 직원 기록과 `case_tasks`를 담당자 조치 Section에 표시한다.
- 고객 진행 Action과 AI 내부 제안은 일반 직원 Action과 혼합하지 않는다.

## 고객 화면

고객에게 허용된 `CUSTOMER_SHARED` Fact, 완료·공개된 Verification/Task, 고객 진행 상태, 공개 메시지만 `CUSTOMER_SHARE`에 배치한다. 그 외 Section은 비운다.

## 중복·표시 규칙

- 원본 resource ID를 `item_id`로 유지한다.
- 상태는 backend canonical enum을 사용하고 UI label은 Frontend presentation에서 변환한다.
- raw action type·semantic key를 직원 화면 제목으로 직접 출력하지 않는다.
- 내부 visibility와 AI reasoning은 고객 projection에 포함하지 않는다.
- 중앙 Timeline은 이 projection을 재사용하지 않고, 이후 Activity Event 계약을 통해 별도 구성한다.

## 현재 GAP

- Action title 필드와 공통 Activity Event는 아직 구현 전이다.
- Action과 Context Task가 동일 업무인지 구분하는 canonical relation이 없다.
- projection revision은 Case context revision을 기준으로 하며, resource별 변경 revision은 다음 계약 단계에서 추가한다.
