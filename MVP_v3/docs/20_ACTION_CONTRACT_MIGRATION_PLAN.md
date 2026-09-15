# Action 계약 확장 계획

작성일: 2026-09-15

## 목적

중앙 대응 업무 카드와 우측 `담당자 조치 및 결과`가 동일한 제목·내용·상태를 표시하고, AI와 은행 직원이 업무를 수정할 수 있도록 Action 계약을 확장한다.

## 현재 계약

`action_type`, `status`, `actor_type`, `note`, `created_at` 중심이다. 현재 `action_type`이 화면 제목 역할을 겸하고 있어 사용자가 제목을 수정할 수 없다.

## 목표 계약

`action_id`, `case_id`, `action_type`, `title`, `description/note`, `status`, `actor_type`, `created_by`, `updated_by`, `version`, `visibility`, `created_at`, `updated_at`.

초기 호환 단계에서는 `title`을 nullable로 두고, 값이 없으면 기존 `action_type` label을 사용한다.

## 구현 순서

1. migration에 nullable `title`과 version/updated 메타데이터 추가
2. Public create/update/response DTO 확장
3. MySQL repository의 insert/select/update 확장
4. in-memory repository 동일 동작 구현
5. Action API가 title과 note를 각각 저장하도록 수정
6. Context V3 projection과 중앙 Timeline이 title/description을 사용하도록 수정
7. 기존 데이터 fallback 및 backfill 검증
8. 동시 수정·권한·visibility 회귀 테스트

## 호환·안전 규칙

- 기존 Action 레코드는 `title IS NULL`이면 `action_type`을 제목으로 표시한다.
- 제목과 내용은 서로 합쳐 저장하지 않는다.
- 상태 전이 API는 허용 enum을 유지한다.
- 수정 요청은 `expected_version`을 사용하고 성공 시 version을 증가시킨다.
- 고객 진행 Action은 일반 직원 Action projection에 중복 표시하지 않는다.
- hard delete 대신 CANCELLED/archived 이력을 유지한다.

## 이번 단계 범위

이 문서는 계약과 migration 순서를 고정하기 위한 계획이며, 이번 단계에서는 런타임·DB·API 코드를 변경하지 않는다.
