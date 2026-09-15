# 중앙 카드·우측 패널 Mutation 동기화 기준

작성일: 2026-09-15

## 현재 갱신 흐름

중앙 Action/Verification/Question mutation은 `CaseRoomPage.refreshAfterMutation`을 통해 Case bundle을 다시 조회하고 `onMutated`를 호출한다. 우측 Context Panel mutation은 자체 `loadContextPanelV3`를 호출해 projection을 다시 읽는다.

```text
mutation 성공
→ 원본 resource 저장
→ 해당 화면의 canonical 응답 재조회
→ 중앙 bundle 또는 Context projection 갱신
```

## 리소스별 책임

| mutation | 원본 API | 중앙 갱신 | 우측 갱신 |
|---|---|---|---|
| Action 생성/수정/상태 | `/actions` | Case bundle 재조회 | Context Panel 재조회 필요 |
| Context Task 수정/상태 | `/context-v2/tasks` | 현재 중앙 카드 없음 | Context Panel 재조회 |
| Fact 검토/정정 | `/context-v2/facts` | 현재 중앙 카드 없음 | Context Panel 재조회 |
| Verification | `/verifications` | Case bundle 재조회 | Context Panel 재조회 필요 |
| 질문/답변 | 질문 API | Case bundle 재조회 | Fact projection은 후속 추출 시 갱신 |

## 목표 규칙

모든 mutation은 서버 canonical 응답과 변경 이벤트를 기준으로 양쪽을 갱신한다. Frontend가 중앙 카드 데이터를 Context Panel item으로 직접 복사하지 않는다.

- 중앙: Message + 허용된 Activity Event를 시간순 정렬
- 우측: canonical resource를 최신 Context projection으로 재생성
- 고객: visibility allowlist를 적용한 별도 projection

## 회귀 조건

- 저장 직후 중앙 카드와 우측 상태가 동일한 resource revision을 반영한다.
- 새로고침 후에도 제목·내용·상태가 유지된다.
- 이전 revision 응답이 최신 화면을 덮어쓰지 않는다.
- 고객 비공개 mutation은 고객 Timeline에 나타나지 않는다.
- API 실패 시 어느 한쪽만 낙관적으로 남지 않는다.

현재는 Action과 Verification 등 리소스별 refresh 구현이 분리되어 있으며, 공통 Activity Event 도입 후 이 규칙을 단일 coordinator로 통합할 수 있다.
