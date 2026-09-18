# 새 프론트엔드 View Model 초안

상태: 초안  
주의: 이 문서는 백엔드 API 계약이 아니다. 화면이 필요로 하는 표시 모델을 먼저 정의하기 위한 문서다.

## 1. 화면 입력 모델

```ts
type FrontendCaseRoomModel = {
  caseHeader: {
    caseId: string;
    title: string;
    riskLabel: string;
    statusLabel: string;
    assigneeLabel: string;
  };
  leftNavigation: {
    selectedCaseId: string;
    items: Array<{ id: string; label: string; statusLabel: string }>;
  };
  conversation: {
    entries: Array<{
      id: string;
      actor: 'CUSTOMER' | 'BANK_STAFF' | 'AI' | 'SYSTEM';
      displayText: string;
      occurredAt: string;
      visibility: 'CUSTOMER' | 'BANK_INTERNAL';
    }>;
    composer: {
      enabled: boolean;
      target: 'CUSTOMER' | 'BANK_INTERNAL';
    };
  };
  contextPanel: {
    status: 'EMPTY' | 'LOADING' | 'READY' | 'STALE' | 'FAILED';
    projectionRevision: number | null;
    summary: string | null;
    sections: Array<{
      id: string;
      title: string;
      items: Array<{
        id: string;
        displayText: string;
        reviewStatus: 'PROPOSED' | 'CONFIRMED' | 'REJECTED' | 'SUPERSEDED';
        evidenceCount: number;
      }>;
    }>;
  };
};
```

## 2. 표시 문장 규칙

- `displayText`는 한 번에 완성된 한국어 문장이다.
- 프론트엔드는 `기관명 + 행위 + 금액`을 이어 붙이지 않는다.
- `UNKNOWN`, `OTHER`, `POLICE_SERVICE` 같은 내부 값은 View Model에 표시값으로 전달하지 않는다.
- `evidenceCount`는 근거 개수만 표시하며, 민감한 원문은 별도 권한 확인 뒤에만 조회한다.
- `reviewStatus`는 버튼/상태 표현용이며 문장 자체를 조립하는 근거로 사용하지 않는다.

## 3. 백엔드 계약으로 넘길 후보

화면 검토 후 다음 항목만 새 API 계약에 포함한다.

- 최신 사건 revision
- 화면 표시용 완성 문장
- 문장별 공개 범위
- 검토 상태
- 근거 개수와 안전한 근거 참조 ID
- projection 상태와 생성 시각
- provider 실패·재시도 상태

## 4. 계약에 넣지 않을 것

- 프론트에서 조립해야 하는 부분 문장
- 화면에 직접 노출되는 내부 enum
- LLM 내부 reasoning/raw prompt
- 고객에게 공개되면 안 되는 원문 전체
- 화면이 임의로 확정할 수 있는 boolean 값

## 5. 사람이 승인할 질문

- [ ] 7개 우측 섹션이 실제로 필요한가?
- [ ] 각 섹션의 한국어 제목이 적절한가?
- [ ] 하나의 항목에 문장 하나를 사용할 것인가?
- [ ] 서로 다른 이체 사건을 어떤 방식으로 구분할 것인가?
- [ ] `PROPOSED`와 `CONFIRMED`를 화면에서 어떻게 구분할 것인가?
- [ ] 고객 화면에서 허용할 문장 범위는 어디까지인가?
