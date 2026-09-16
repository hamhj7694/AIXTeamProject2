# 중앙 Timeline 연결 기준

작성일: 2026-09-15

## 현재 동작

`frontend/src/timeline.ts`의 `buildTimeline`이 Case bundle을 다음 순서로 합친다.

- 일반 Message
- Customer Question/Answer
- Verification 요청·결과
- `recent_actions` 대응 업무 기록
- Final Report
- `view === 'timeline'`일 때만 `recent_events`

중복 질문·답변 메시지와 다른 사용자를 위한 `AI_PRIVATE` 메시지는 중앙에서 제외한다.

## 우측 패널과의 관계

Context Panel은 `context-v2/panel`의 최신 projection을 사용한다. Fact·Context Task·AI Suggestion의 상세는 중앙 Timeline에 자동 복제되지 않는다. Action과 Verification만 양쪽에 별도 표현된다.

## 목표 연결 규칙

향후 Activity Event가 도입되면 Timeline은 실제 메시지와 사용자에게 허용된 변경 이벤트를 시간순으로 병합한다. 이벤트는 변경 요약만 표시하고, 상세 Fact·근거·AI reasoning은 우측 패널에서 확인한다.

## 안전 규칙

- 고객 화면에는 `CUSTOMER_SHARED` 또는 `PUBLIC_EVENT`만 표시한다.
- `AI_PRIVATE`, 은행 내부 Fact, 개인 메모는 중앙 카드로 만들지 않는다.
- 이벤트 중복 키는 `case_id/resource_type/resource_id/revision/event_type`이다.
- 원본 리소스와 projection을 중앙에서 임의로 합성하지 않는다.

이번 단계에서는 기존 Timeline 런타임을 변경하지 않고 현재 연결 범위와 Activity Event 도입 지점을 고정한다.
