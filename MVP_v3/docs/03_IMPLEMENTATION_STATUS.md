# V3 구현 및 인수인계 현황

최종 갱신: 2026-09-03

> 현재 실행 구현은 은행 직원용 V3다. 고객용 V3의 요구사항과 완료 기준은 `MVP_v3/CUSTOMER_PRD.md`에 정의했으며 아직 구현 완료 상태로 표시하지 않는다.

## 현재 결과

`MVP_v3/frontend`에 V2와 분리된 은행 직원용 Shared Case Workspace를 구현했다. 화면은 Case 목록, 시간순 Shared Case Conversation, Case Context의 3열 구조이며 좁은 화면에서는 목록과 Context가 Drawer로 전환된다.

Frontend는 AI API에 직접 연결하지 않는다. `/api` 프록시를 통해 General API만 호출하고, General API가 필요한 Case Context를 구성해 AI API를 호출한다.

```text
V3 Frontend :5176
  └─ /api → General API :8100
                ├─ Case DB / Attachment Storage
                └─ AI API :8101
```

## 완성된 사용자 흐름

1. 위험도·상태·검색 조건으로 Case를 찾는다.
2. Case Room에서 AI Brief와 모든 업무 기록을 시간순으로 읽는다.
3. 고객 공개 메시지 또는 은행 내부 메시지를 명시적으로 선택해 보낸다.
4. 고객 확인 질문을 추천받아 선택하거나 직접 추가해 Queue로 보낸다.
5. 기관 검증 업무를 만들고 결과·근거·상태를 갱신한다.
6. 보호조치를 실제 실행한 것처럼 보이지 않도록 “업무 기록”으로 남긴다.
7. 파일을 먼저 서버에 올린 뒤 attachment ID를 메시지와 연결한다.
8. 우측 Context에서 위험 근거, 주장·요구, Fact, 미확인 항목, 검증, 권장 조치를 함께 확인한다.

## 데이터 표시 원칙

- Message, Question, Answer, Verification, Action, Event는 하나의 Timeline으로 변환한다.
- 모든 항목은 `occurredAt ASC`로 정렬한다.
- 동일 질문·답변을 표현하는 원문 Message와 구조화 Card가 함께 있으면 Card만 표시한다.
- 현재 은행 사용자 본인의 Message만 오른쪽에 둔다.
- `AI_PRIVATE`는 Shared Case Conversation에서 제외한다.
- 낮은 위험은 중립·녹색 계열로 표현하고, 근거 없는 긴급 적색을 사용하지 않는다.
- 사용자가 과거 기록을 읽는 동안 새 데이터 때문에 강제로 아래로 이동시키지 않는다.

## API 갱신 정책

- 최초 진입: Case detail, bank Bundle, Fact, AI Case Support를 조회한다.
- 5초 polling: Case detail, Bundle, Fact만 갱신한다.
- Mutation 완료: 관련 Case 데이터를 즉시 다시 조회한다.
- AI Case Support: 최초 진입과 의미 있는 변경 직후에만 갱신한다.

이 정책은 서버 상태 최신성과 AI 호출 비용을 함께 고려한 것이다. React 개발 모드의 중복 Effect 호출을 피하기 위해 StrictMode도 현재 제거했다.

## 검증 완료

- TypeScript 및 정적 검사 통과
- Vite production build 통과
- General API 34개 unittest 통과
- AI API 61개 unittest 통과
- V3·General·AI health 및 V3 proxy 실제 조회 통과
- Timeline out-of-order fixture의 단일 시간순 정렬 통과
- 소스의 Mock/TODO/FIXME와 conflict marker 없음
- 검증 중 외부 유료 AI 호출 없음

## 현재 제한과 다음 담당자 작업

1. 인증과 RBAC가 없어 서버가 actor와 view를 완전히 신뢰하면 안 된다.
2. 실시간 endpoint가 없어 현재는 5초 polling이다.
3. Work Card lifecycle은 서버 영속화가 필요하다.
4. 고객 답변 후보와 담당자·기관이 확정한 Fact를 Backend 상태로 더 엄격히 구분해야 한다.
5. 질문·답변·Fact·AI 요약의 다단계 저장은 원자성 또는 보상 처리 설계가 필요하다.
6. sklearn 모델 artifact/runtime 버전 경고를 배포 전에 해소해야 한다.
7. 연결 가능한 브라우저 세션이 없어 이번 인수에서는 화면 캡처, 콘솔, 키보드·스크린리더, 실제 버튼 클릭 E2E를 수행하지 못했다.

세부 후속 항목과 완료 근거는 `02_DETAILED_TODO.md`를 단일 작업 추적 문서로 사용한다.
