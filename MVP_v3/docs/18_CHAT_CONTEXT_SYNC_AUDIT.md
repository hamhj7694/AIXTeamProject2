# 중앙 채팅 카드와 우측 Context Panel 데이터 흐름 기준선

작성일: 2026-09-15

## 결론

중앙 채팅과 우측 패널은 일부 리소스만 공유한다. 중앙은 대화와 주요 업무 이벤트를 시간순으로 보여주고, 우측 패널은 최신 구조화 상태를 보여주는 별도 projection이다.

## 현재 저장·조회 경로

| 리소스 | 저장 원본 | 중앙 채팅 | 우측 패널 |
|---|---|---|---|
| Message | `messages` | 실제 메시지 카드 | 직접 표시하지 않음 |
| Customer Question | `customer_questions` | 질문·답변 카드 | 관련 Fact/Gap에 간접 반영 |
| Verification | `verification_tasks` | 기관 확인 카드 | 사실·확인 현황 |
| Action | `actions` | 대응 업무 기록 카드 | 담당자 조치 및 결과 |
| Context Task | `case_tasks` | 현재 표시 없음 | 담당자 조치 및 결과 |
| Fact | `case_facts` | 직접 표시하지 않음 | 피해·노출·사칭·사기 정황·확인 현황 |
| AI Suggestion | Context resources | 직접 표시하지 않음 | AI 업무 제안 |
| Customer Progress | `actions`의 progress record | 고객 화면 중심 | 고객 공유 projection |

## 갱신 규칙

중앙 Action/Verification 저장 후 `CaseRoomPage.refreshAfterMutation`이 Case bundle을 다시 조회한다. Context Panel은 `accessRevision`, bundle cursor/context revision 변화에 따라 `/context-v2/panel`을 다시 조회한다. 양쪽 모두 저장 성공 후 재조회 방식이며, 한쪽 화면의 로컬 상태를 다른 쪽으로 직접 복사하지 않는다.

## 확인된 불일치

1. `actions`에는 현재 `action_type`, `note` 중심으로 저장되어 업무 제목 수정이 제한된다.
2. `case_tasks`는 우측 패널 전용이라 중앙 채팅에는 카드가 없다.
3. Fact와 AI Suggestion도 우측 패널 전용이다.
4. 중앙 카드와 패널은 동일 Action이라도 표시 label·상태 표현이 별도 구현될 수 있다.
5. Activity Event가 공통 계약으로 존재하지 않아 모든 패널 변경이 중앙에 기록되지는 않는다.

## 다음 계약 작업의 기준

- Action에 `title`과 `description/note`를 분리한다.
- 변경 이벤트에 `resource_type`, `resource_id`, `actor_type`, `visibility`, `revision`을 기록한다.
- 중앙은 이벤트 요약, 우측 패널은 최신 projection을 표시한다.
- 고객 공개 이벤트와 은행 내부 이벤트를 분리한다.
- 동일 resource/revision 이벤트 중복 표시를 막는다.

이 문서는 구현 변경 전 현재 동작 기준선이며, 이번 단계에서는 Backend·Frontend 런타임을 변경하지 않는다.
