# Context Panel 입력·확인 UI 전환 기준선

작성일: 2026-09-15

이 문서는 `prompt / confirm / alert`를 Context Panel 전용 UI로 전환하기 전 현재 동작을 고정하는 기준선이다. 이번 단계에서는 런타임 동작과 Backend 계약을 변경하지 않는다.

## 조사 범위

- Frontend: `frontend/src/context-v3/ContextPanelV3.tsx`, `components.tsx`, `sections.tsx`
- API wrapper: `frontend/src/context-v3/api.ts`
- General API: `backend/general_api/app/main.py`
- 저장·상태 전이: `backend/general_api/app/domains/cases/case_context_v2_repository.py`

## 현재 얼럿 호출 기준선

| 호출 | 실행 버튼/상태 | 입력 또는 확인 | 저장 API·결과 |
|---|---|---|---|
| `confirm` | 정보 복구 | 제외 Fact를 확인 필요로 복구할지 확인 | Fact review `RESTORE` |
| `confirm` | 확정 취소 | 확정 Fact를 다시 확인 필요로 바꿀지 확인 | Fact review `UNCONFIRM` |
| `prompt` | 확정 Fact → 정보 정정 | 새 값을 입력. 지원하는 typed Fact만 허용 | Fact create → `PROPOSED`, 이후 confirm 시 기존 Fact `SUPERSEDED` |
| `prompt` | 확정 Fact → 잘못된 정보로 제외 | 제외 사유 필수 | Fact review `INVALIDATE` → `REJECTED` |
| `prompt` | 확인 필요 Fact → 잘못된 정보로 제외 | 제외 사유 필수 | Fact review `REJECT` → `REJECTED` |
| `prompt` | AI 제안 → 제안 제외 | 제외 사유 입력 | Suggestion review `DISMISS` |
| `prompt` | 진행 중 업무 → 완료 | 완료 결과 필수 | Task complete → `COMPLETED` |
| `prompt` | 업무 → 업무 취소 | 취소 사유 필수 | Task cancel → `CANCELLED` |
| `confirm` | 완료·취소 업무 → 업무 복구 | 대기 상태로 복구할지 확인 | Task update → `TODO` |
| `alert` | 지원하지 않는 Fact 정정 | 지원되지 않는 입력 형식 안내 | API 호출 없음 |
| `alert` | 금액 정정 오류 | 0 이상 숫자 안내 | API 호출 없음 |
| `alert` | 이체 여부 정정 오류 | `TRANSFERRED / NOT_TRANSFERRED / UNKNOWN` 안내 | API 호출 없음 |

## 현재 UI 버튼과 노출 위치

- Fact Row의 확정 버튼: `확정`
- 확정 Fact의 More Menu: `정보 정정`, `확정 취소`, `잘못된 정보로 제외`
- 확인 필요 Fact의 More Menu: `잘못된 정보로 제외`
- AI Suggestion Card: `업무로 채택`, `제안 제외`
- Task Card: `시작`, `완료`, More Menu 안의 `업무 수정`, `보류`, `업무 취소`
- 완료·취소 업무 기록: `업무 복구`
- 제외 정보 기록: `정보 복구`

## 취소·오류 기준선

- 기본 창에서 취소하거나 빈 값을 제출하면 API를 호출하지 않는다.
- `INVALIDATE`, `DISMISS`, `COMPLETE`, `CANCEL`은 사유·결과가 비어 있으면 저장하지 않는다.
- 정정 입력이 기존 표시값과 같으면 저장하지 않는다.
- API 호출 중에는 공통 `busy` 상태로 버튼을 비활성화한다.
- 저장 성공 후 Context Panel을 다시 조회한다.
- 충돌·서버 오류는 Panel의 공통 오류 영역에 표시한다.
- Case 변경 시 입력 상태는 초기화되어야 한다.

## 전환 시 보존해야 할 계약

- API path와 HTTP method
- `expected_version` 기반 낙관적 잠금
- Fact `PROPOSED / CONFIRMED / REJECTED / SUPERSEDED` 상태 의미
- Task `TODO / IN_PROGRESS / BLOCKED / COMPLETED / CANCELLED` 상태 의미
- 정정 시 기존 확정 Fact를 직접 덮어쓰지 않는 정책
- 복구·정정·제외·완료·취소의 감사 이력
- 저장 성공 후 최신 projection을 다시 불러오는 동작

## 다음 단계 진입 조건

공통 `ContextActionModal`, `ContextTextArea`, `ContextConfirmModal`, `ContextInlineError`를 만든 뒤 업무 수정부터 단계적으로 교체한다. 이 문서의 표와 현재 테스트를 변경 전·후 회귀 비교 기준으로 사용한다.
