# B Part 대화·Grounding 후속 개선 계획

작성일: 2026-09-20
최종 갱신: 2026-09-20
상태: 기준 문서 `DONE` / P0 원인 특정·최소 수정 `IN_PROGRESS` / 질문 계획 Context 동기화 감사 `TODO`

이 문서는 Browser·Runtime·자동화 검증에서 확인한 Bank AI·Customer AI의 대화 품질, Grounding, 질문 계획(Question Plan) 문제를 B Part 후속 작업의 공통 기준으로 정리합니다.

목표는 자유 대화 챗봇이 아니라 **현재 질문에 직접 답하면서 Case 근거와 필요한 안전·업무 가이드를 제공하고, 이미 확보한 정보를 반복해서 묻지 않는 대화 가능한 업무 코파일럿**입니다.

현재까지 확인된 사실과 아직 확인이 필요한 내용을 구분합니다. Browser 화면만으로 내부 실패 원인을 확정하지 않으며, Runtime·코드·자동화·MySQL 근거가 확보된 항목만 현재 결론으로 기록합니다.

---

## 1. 범위와 판정 원칙

### 1.1 후속 개선 범위

- 새 Case 초기 Bank AI 응답의 간헐적 Quality 차단
- Customer AI의 반복 안전 응답
- Bank AI의 Conversation Context 처리
- Bank·Customer 최신 발화 반영
- 질문에 직접 답하는 응답 정책
- Case Context와 Conversation Context의 Grounding 구분
- 이미 확보된 Customer Statement의 질문 계획 반영
- 해결된 canonical target의 재질문 방지
- 기존 질문과 AI 추천 질문의 의미 중복 제거
- 기존 supersede/batching 회귀 방지
- 기존 질문 카드·Customer answer·qf1 흐름 회귀 방지
- 후속 READ-ONLY 감사 및 Browser 완료 기준

### 1.2 판정 원칙

- 첨부 화면은 해당 시점 Browser에서 관찰한 현상의 증거입니다.
- Browser 화면만으로 Provider, Parsing, Contract, Quality, Grounding 중 실패 지점을 확정하지 않습니다.
- Implementation, Automated Test, REST/Runtime, MySQL, Browser는 서로 다른 검증 축으로 관리합니다.
- `MESSAGE` 저장 성공은 `AI_RESPONSE` 생성·저장 성공을 의미하지 않습니다.
- 여러 사용자 메시지가 하나의 응답에 반영됐다는 사실만으로 in-flight supersede와 stale DB 저장 차단까지 검증됐다고 판단하지 않습니다.
- Conversation Context 입력 직후 오류가 발생해도 Runtime 근거 없이 직접 인과관계를 확정하지 않습니다.
- 원인을 확인하기 전에 Prompt, Quality, Grounding 기준을 임의로 완화하지 않습니다.
- 일반 대화에서 사건 관련 답을 확보했다고 해서 자동으로 `VERIFIED` Fact가 된 것으로 취급하지 않습니다.
- 질문 필요성 판단과 사실 검증 상태는 별도 축으로 관리합니다.
- 표현이 다른 질문이라도 동일 canonical target을 묻는다면 의미 중복으로 판단할 수 있습니다.
- 질문 개수를 채우기 위해 이미 해결된 target을 다시 질문하지 않습니다.

---

## 2. 현재 Browser / Runtime 검증 상태

| 영역 | 현재 판정 | 확인된 내용 | 추가 확인 |
|---|---|---|---|
| Bank 연속 입력 batching | `DONE` | 여러 담당자 질문이 하나의 CaseCopilot 응답에 함께 반영됨 | 후속 변경 후 회귀 확인 |
| Bank in-flight supersede / stale 억제 | `IN_PROGRESS` | 연속 입력 통합 응답은 확인했으나 stale DB 저장 여부는 Browser만으로 확정 불가 | Network·MySQL 대조 |
| Customer supersede/batching | `IN_PROGRESS` | 연속 발화가 하나의 응답 흐름으로 처리되는 것으로 보임 | invocation·응답·DB 메시지 수 대조 |
| 질문 카드 / Customer answer lifecycle | `DONE` | 질문 등록→고객 노출→답변 반영 흐름 정상 | 후속 변경 후 회귀 확인 |
| qf1 follow-up | `TODO` | 코드·자동화 검증은 있으나 Browser E2E 증거 부족 | qf1 child 실제 흐름 확인 |
| Bank 일부 Case 기반 응답 | `DONE` | 새 Case에서도 Case 기반 정상 응답이 생성되는 사례 확인 | Grounding 표현 품질 회귀 확인 |
| 새 Case 초기 Bank AI Quality 차단 | `IN_PROGRESS` | `unsupported_certainty` → `unattributed_certainty_without_confirmed_source`로 503 재현 | trigger 표현/세부 판정 경로 확인 후 최소 수정 |
| Customer 최신 발화 반영 | `IN_PROGRESS` | 서로 다른 발화에도 유사한 안전 안내 반복 | Provider 입력 경로 확인 |
| Bank Conversation Context | `IN_PROGRESS` | 인사에 사건 전체 요약이 우선되거나 일부 흐름에서 오류 관찰 | 최신 발화 우선순위와 Grounding 구분 확인 |
| 질문 계획 Context 동기화 / 중복 제거 | `IN_PROGRESS` | 고객 일반 대화에서 송금 미실행을 밝혔는데 같은 target 질문이 남고 AI 추천에서도 재생성됨 | 질문 source/target/dedupe/sufficiency 흐름 감사 |

> `03_bank_consecutive_batch_success.png`는 **Bank 연속 입력 batching의 대표 Browser 정상 기준**입니다.
>
> Browser 성공만으로 in-flight supersede와 stale `AI_RESPONSE` DB 미저장까지 검증됐다고 판단하지 않습니다.

---

## 3. Browser / Runtime 증거

### 3.1 기존 Bank 초기 응답 실패

#### 관찰 사실

- Case 생성 직후 담당자가 “현재 확인된 사항 있어?”, “지금 상황 어때?” 같은 정상적인 Case 질문을 전송했습니다.
- 담당자 `MESSAGE`는 화면에 남았습니다.
- 일부 generation에서는 Bank `AI_RESPONSE`가 표시되지 않았습니다.
- 상단 오류 배너가 표시됐습니다.

#### 최신 판정

초기에는 “첫 AI 응답 실패”로 관찰했지만, 이후 동일한 새 Case 조건에서도 첫 질문이 정상 응답되는 사례가 확인됐습니다.

따라서 현재 문제 범위는 **새 Case에서 첫 응답이 항상 실패하는 문제**가 아니라 **새 Case 초기 Bank 대화에서 일부 generation이 Quality 기준에 의해 간헐적으로 차단되는 문제**로 갱신합니다.

---

### 3.2 Customer 반복 안전 응답

#### 관찰 사실

- 고객은 이름 소개, 인사, 다른 답변 요청처럼 서로 다른 발화를 했습니다.
- Customer AI는 추가 송금 중단, 상대방과의 접촉 중단, 공식기관 연락 등의 유사한 안내를 반복했습니다.
- 안전 방향은 유지하지만 최신 사용자 발화에 대한 직접 응답이 부족합니다.

#### 판정

- `Customer 최신 발화 반영 부족 및 안전 템플릿 반복`의 Browser 증거입니다.
- 안전 가이드 자체가 문제가 아니라 **현재 질문보다 유사한 전체 안전 안내가 반복적으로 우선되는 점**이 문제입니다.
- Prompt, Context, Provider, Quality 중 어디에서 반복이 시작되는지는 추가 확인이 필요합니다.

---

### 3.3 Bank 연속 입력 batching 정상 기준

#### 관찰 사실

- 담당자가 송금 상태, 고객 상태, 고객 성명에 관한 질문을 연속으로 입력했습니다.
- 하나의 CaseCopilot 응답이 여러 질문을 함께 다루었습니다.
- 확인된 내용과 미확인 내용을 구분하려는 응답이 생성됐습니다.

#### 판정

- **Bank 연속 입력 batching의 대표 Browser 정상 기준**입니다.
- 후속 Quality·Grounding 수정 뒤에도 이 동작을 보존해야 합니다.
- stale `AI_RESPONSE` 부재는 Browser가 아닌 REST/MySQL에서 별도 확인합니다.

---

### 3.4 Bank Conversation Context / 직접 답변 부족

#### 관찰 사실

- 담당자가 “하이” 같은 인사를 입력했을 때 AI_RESPONSE 자체는 정상 생성되는 사례가 확인됐습니다.
- 그러나 인사에 짧게 응답하기보다 Case 전체 요약과 확인 항목을 길게 제시하는 응답이 관찰됐습니다.
- 이름·호칭 같은 Conversation Context 입력이 포함된 과거 흐름에서는 오류도 관찰됐습니다.

#### 판정

- Conversation Context 자체가 Case Evidence가 되어야 하는 것은 아닙니다.
- 이름·호칭·인사는 대화 연결을 위해 사용할 수 있어야 합니다.
- `인사 → 사건 전체 요약`처럼 최신 발화보다 Case Context가 과도하게 우선되는 문제는 P1/P2에서 별도로 다룹니다.

---

### 3.5 P0 최신 Runtime 재현 — `unsupported_certainty`

#### VP-10 재현 조건

```text
새 Case 생성
→ Customer ROOM 별도 대화 없음
→ Bank: "현재 추가로 확인된 사항 있어?"
→ AI_RESPONSE 200 / 정상 생성
→ Bank: "현재 확인된 사항 있어?"
→ AI_RESPONSE 차단 / 오류 배너
```

#### AI API Runtime 로그

```text
CaseCopilot quality blocked:
criteria=unsupported_certainty
rules=unattributed_certainty_without_confirmed_source
normalization_changed=False
raw_rules=none
normalized_rules=unattributed_certainty_without_confirmed_source

POST /ai/case-copilot/replies → 503
```

#### 판정

- 최초 실패 계층은 Provider 이전이 아니라 **Provider 응답 이후 Quality 단계**입니다.
- 실제 runtime blocking criterion은 `unsupported_certainty`입니다.
- 세부 rule은 `unattributed_certainty_without_confirmed_source`로 확인됐습니다.
- 같은 Case·유사 질문에서도 정상 통과하는 generation과 차단되는 generation이 모두 확인됐습니다.
- 따라서 질문 문자열 자체가 항상 실패를 만드는 구조라고 보지 않습니다.
- `normalization_changed=False`인데 `raw_rules=none`, `normalized_rules=...`가 나온 이유는 추가 확인이 필요합니다.
- 실제 Provider 원문 전체는 로그에 남기지 않았으므로, 정확히 어떤 표현이 rule을 발생시켰는지는 아직 확인되지 않았습니다.

---

### 3.6 질문 계획 Context 동기화 / 중복 문제

#### Browser 관찰 사실

Customer ROOM 일반 대화에서 고객이 다음 취지로 답했습니다.

```text
상대방이 돈을 요구했는데 안 보냈어요.
```

그럼에도 Bank ROOM의 고객 확인 질문 후보에는 다음 질문이 계속 남아 있었습니다.

```text
상대방의 요구대로 실제로 송금하거나 이체하셨나요?
```

또한 AI 질문 추천을 실행했을 때 의미가 사실상 동일한 질문이 다시 생성됐습니다.

```text
상대방의 요구대로 실제로 송금하거나 이체하셨는지 궁금합니다.
```

#### 판정

- Customer 일반 대화에서 확보된 사건 관련 답이 질문 계획에 충분히 반영되지 않고 있습니다.
- 기존 질문과 AI 추천 질문 사이의 의미 중복 제거가 부족합니다.
- 문장 문자열이 달라도 동일 canonical target을 묻는 경우 중복으로 다뤄야 합니다.
- 고객 진술을 질문 후보에서 제외할 근거로 사용할 수는 있지만, 이를 자동으로 객관적 `VERIFIED` 사실로 승격해서는 안 됩니다.
- 이 문제는 질문/답변 Workflow의 핵심 연결 문제이므로 P0 마무리 직후 우선 감사합니다.

---

## 4. 확인된 문제와 원인 후보

### A. 새 Case 초기 Bank AI 응답 간헐적 Quality 차단 — `P0 / IN_PROGRESS`

#### 현상

새 Case에서 정상적인 사건 질문에 응답이 생성되는 경우도 있지만, 유사한 질문에서 `MESSAGE` 저장 후 `AI_RESPONSE`가 생성·전달되지 않고 503이 발생하는 경우가 있습니다.

예:

```text
현재 상황 어때?
현재 추가로 확인된 사항 있어?
현재 확인된 사항 있어?
무엇을 먼저 확인해야 해?
```

#### 현재까지 확인된 호출 경계

```text
Bank MESSAGE 저장
→ Frontend AI invocation
→ General API
→ Case Context / recent conversation 구성
→ AI API
→ Provider
→ 응답 normalization (`user_text()` 포함)
→ Quality `_source_certainty_check()`
→ unsupported_certainty runtime blocking
→ AI API 503
→ General 503
→ AI_RESPONSE 미저장
```

현재 경로에는 별도 독립 Formatter가 확인되지 않았으며, Quality 입력 전에 `user_text()`에 의한 일부 기계 라벨 치환이 수행됩니다.

#### 현재 확인된 Context 특성

- `initial_brief`, Context V2 projection, Fact/retrieval 형태가 Bank Copilot 입력에 포함됩니다.
- Initial Report·진단 원문·FDS/STT 원본이 그대로 직접 전달되는 구조로 확인되지는 않았습니다.
- VP-8 감사에서는 typed fact가 주로 `AI_EXTRACTION / PROPOSED`였고, 객관적 확정을 승인할 `CONFIRMED + 확인 주체/시각`, `BANK_RECORD`, 완료 Verification 근거가 확인되지 않았습니다.

#### 확정된 내용

- Provider 이전 실패가 아닙니다.
- runtime blocking criterion은 `unsupported_certainty`입니다.
- VP-10 Runtime에서 세부 rule `unattributed_certainty_without_confirmed_source`가 확인됐습니다.
- 실패 시 임시 AI 답변을 생성하지 않고 AI API/General이 실패로 반환하는 현재 경계는 유지됩니다.
- 관측성 추가 후 관련 자동 테스트는 `64 passed, 59 subtests passed`로 통과했습니다.

#### 아직 확인 필요

- 실제 Provider 표현 중 어떤 문장/claim이 세부 rule을 발생시켰는지
- `normalization_changed=False`인데 `raw_rules=none`, `normalized_rules=...`가 기록된 이유
- Provider가 Evidence 상태를 무시한 확정 표현을 생성한 것인지
- Grounding된 표현을 Quality가 오탐한 것인지
- 생성 표현 계약과 Quality 판정 중 실제 최소 수정 위치

#### 현재 결론

P0는 **실패 계층·criterion·세부 rule까지 특정된 상태**입니다.

아직 Quality 기준을 완화하거나 Provider Prompt를 광범위하게 변경하지 않습니다. 남은 trigger/판정 경로를 확인한 뒤 가장 좁은 계층만 수정합니다.

---

### B. Customer AI 반복 안전 템플릿 — `P1 / TODO`

#### 현상

고객의 최신 발화가 이름, 인사, 다른 답변 요청인데도 위험 안내가 응답의 대부분을 차지합니다.

안전 안내는 필요하지만 현재 질문과 직접 관련 없는 동일·유사 문구가 반복되어 대화성이 떨어집니다.

#### 확인 필요

- 최신 Customer 발화가 recent conversation에 포함되는지
- General → AI → Provider까지 최신 발화가 유지되는지
- 현재 사용자 요청과 Case Context의 Prompt 내 우선순위
- Prompt가 매 응답에 전체 안전 안내를 강제하는지
- Provider의 직접 응답이 Quality 단계에서 바뀌는지
- 이전 AI 응답이 반복을 강화하는 구조인지

#### 가설

다음 중 하나 이상이 영향을 줄 수 있습니다.

- 위험 Context 우선순위가 지나치게 높음
- recent conversation 전달 누락 또는 정렬 문제
- Prompt에서 Case Context가 최신 사용자 요청보다 과도하게 우선됨
- 전체 안전 안내 반복을 Prompt가 강제함
- 이전 AI 응답이 다음 generation의 반복을 강화함

감사 전에는 어느 가설도 사실로 취급하지 않습니다.

---

### C. Bank Conversation Context 처리 — `P1 / TODO`

#### 현상

이름, 호칭, 인사처럼 사건 Evidence가 아닌 대화 정보에 짧고 자연스럽게 반응하지 못하거나 Case 전체 요약이 우선됩니다.

#### 확인 필요

- recent conversation에서 해당 발화의 role·순서·범위
- Conversation Context가 Case Fact 또는 Evidence claim으로 잘못 해석되는지
- Quality/Grounding이 Evidence에 없는 이름을 unsupported Case fact로 판단하는지
- Provider 응답은 정상이었지만 후단 검사에서 차단되는지
- P0의 `unsupported_certainty`와 공유하는 원인이 있는지
- Case Grounding과 Conversation Grounding을 분리할 수 있는 최소 수정 위치

#### 가설

Case Grounding 규칙 또는 Case Context 우선순위가 Conversation Context에도 과도하게 적용될 가능성이 있습니다.

실제 payload와 단계별 로그 확인 전에는 확정하지 않습니다.

---

### D. 직접 답변보다 사건 요약·안전 안내가 우선되는 응답 구조 — `P2 / TODO`

현재 일부 응답은 사용자 질문에 대한 직접 답변보다 전체 사건 요약이나 안전 안내가 먼저 또는 반복적으로 제시됩니다.

목표 응답 순서는 다음과 같습니다.

```text
현재 질문에 직접 답변
→ 필요한 Case 근거와 불확실성 표시
→ 질문과 관련된 안전·업무 가이드만 추가
```

안전 안내를 제거하는 것이 목적이 아니라 **현재 질문과 위험 수준에 맞게 필요한 만큼 제공하는 것**이 목표입니다.

---

### E. 이미 확보된 내용의 질문 잔존 및 AI 추천 중복 — `P1 / TODO`

#### 현상

Customer ROOM의 일반 대화에서 이미 답을 확보한 내용이 Bank ROOM의 고객 확인 질문 후보에 계속 남아 있는 경우가 있습니다.

예:

```text
고객: 상대방이 돈을 요구했는데 안 보냈어요.
```

이후에도 다음 질문이 남아 있습니다.

```text
상대방의 요구대로 실제로 송금하거나 이체하셨나요?
```

AI 질문 추천에서도 같은 의미의 질문이 다시 생성됐습니다.

```text
상대방의 요구대로 실제로 송금하거나 이체하셨는지 궁금합니다.
```

#### 문제

현재 질문 계획이 다음 정보를 함께 충분히 사용하지 못할 가능성이 있습니다.

- Case Context
- Customer 일반 `MESSAGE`
- 구조화된 Customer Statement
- 기존 `QUESTION`
- `ASKED` / `ANSWERED` 상태
- qf1 parent/target
- canonical target
- 기존 AI 추천 질문
- unresolved verification

그 결과:

- 이미 확보한 정보를 다시 질문함
- 표현만 다른 의미 중복 질문을 생성함
- 아직 확인되지 않은 다른 중요한 target이 추천에서 밀릴 수 있음

#### 확정 방향

질문은 단순 문자열보다 **확인 목적(canonical target)** 을 중심으로 계획합니다.

기본 목표 흐름:

```text
Case Context
+ Customer Conversation / Statement
+ 기존 Question / Answer
→ 아직 해결되지 않은 target 계산
→ 기존 질문과 target 중복 제거
→ 현재 Case에서 우선순위 높은 target 선택
→ target별 질문 생성
→ 담당자 검토·수정
→ 고객 전달
```

다음 원칙은 확정 방향으로 사용합니다.

- 이미 충분한 답이 확보된 target은 **새 질문 후보/AI 추천에서 제외**합니다.
- 일반 대화에서 확보된 Customer Statement도 질문 필요성 판단에 반영합니다.
- 동일 canonical target에 대해 표현만 다른 질문을 중복 생성하지 않습니다.
- AI 추천은 기존 질문의 문장 변형보다 **아직 해결되지 않은 다른 target**을 우선합니다.
- 질문 후보에서 제외됐다는 사실을 `VERIFIED` 판정으로 해석하지 않습니다.
- 이미 저장된 QUESTION/ANSWER 이력은 단순히 화면에서 필요 없어졌다는 이유로 삭제하지 않습니다.
- formal question을 실제로 묻지 않았는데 일반 대화에서 답이 확보됐다는 이유만으로 기존 lifecycle을 임의로 `ANSWERED`로 변경하지 않습니다. 필요한 경우 질문 계획 계층에서 후보 제외/비활성 판단을 우선 검토합니다.
- `ANSWERED != SUFFICIENT`를 유지합니다.
- `CUSTOMER_STATEMENT != VERIFIED FACT`를 유지합니다.
- 고객에게 다시 물을 필요가 없더라도 별도 Verification 필요성은 남을 수 있습니다.

#### 검토 중인 방향

다음은 아직 구현 확정사항이 아닙니다.

- Case별로 우선 확인 target을 약 4개 수준으로 구성
- 기존 고정 질문 묶음을 축소하거나 제거
- AI가 Case별 필수 확인 target을 동적으로 구성

`4개`라는 숫자를 고정 목표로 사용하지 않습니다. 실제 unresolved target이 2개라면 억지로 4개를 채우지 않고, 더 많다면 중요도에 따라 우선순위를 정하는 방향을 우선 검토합니다.

#### 확인 필요

- 현재 기본 질문 후보가 어디에서 생성·저장되는지
- 질문마다 canonical target이 실제 연결되어 있는지
- Customer 일반 `MESSAGE`가 Case Context / Fact에 어떻게 반영되는지
- 일반 대화에서 확보된 답을 질문 계획이 읽는지
- AI 질문 추천이 기존 `QUESTION` / `ANSWER` / `MESSAGE` / Fact를 모두 조회하는지
- 현재 중복 방지가 문자열 기준인지 canonical target 기준인지
- qf1의 기존 canonical target / duplicate protection을 재사용할 수 있는지
- 이미 충분한 답이 확보된 target을 후보에서 제외할 가장 작은 계층이 어디인지
- DB/API Contract 변경 없이 해결 가능한지

---

## 5. 목표 응답 정책

Bank와 Customer AI는 다음 원칙을 공통으로 사용합니다.

1. 사용자가 방금 한 질문에 먼저 답합니다.
2. 사건 사실이나 현재 상태 질문에는 Case Context와 Evidence를 사용합니다.
3. Evidence에서 확인되지 않은 내용은 미확인이라고 명시합니다.
4. 이름, 인사, 호칭 등은 Conversation Context를 사용해 짧고 자연스럽게 답합니다.
5. Conversation Context를 Case Fact 또는 `VERIFIED` 정보로 자동 승격하지 않습니다.
6. 사건·업무와 관련성이 낮은 질문은 짧게 답한 뒤 필요할 때만 업무로 안내합니다.
7. 위험과 직접 관련된 질문에는 필요한 안전 가이드를 덧붙입니다.
8. 현재 질문과 직접 관련되지 않는 전체 안전 안내를 매 응답마다 반복하지 않습니다.
9. 직전 응답에서 충분히 안내한 내용은 새 질문과 관련되지 않으면 반복하지 않습니다.
10. AI는 최종 판단을 대신하지 않고 현재 근거, 미확인 정보, 필요한 확인 행동을 구분해 제시합니다.

### 예시 1 — Conversation Context

```text
담당자: 내 이름은 김은행이야.

AI:
알겠습니다.
이 대화에서는 김은행님으로 부를게요.
```

`김은행`은 현재 대화의 호칭으로만 사용하며 Case Evidence 또는 `VERIFIED` Fact로 저장하지 않습니다.

### 예시 2 — Case 상태 질문

```text
담당자: 지금 상황 어때?

AI:
현재 Case에서 제안된 정황은 상대방이 고객에게 송금을 유도하고
앱 설치를 요구했다는 내용입니다.

실제 송금 완료 여부는 아직 확인되지 않았습니다.

우선 고객에게 송금 여부와 앱 설치 여부를 확인하는 것이 좋습니다.
```

Case Context가 `PROPOSED` 상태라면 “확인된 사실”처럼 표현하지 않고 출처·상태에 맞는 표현을 사용합니다.

### 예시 3 — Customer 위험 발화

```text
고객: 상대방이 지금 바로 다시 송금하라고 해요.

AI:
추가 송금은 하지 않는 것이 좋습니다.

상대방과의 통화나 메시지를 중단하고,
현재 상황을 담당자와 확인해 주세요.
```

---

## 6. Context 및 질문 계획 구분 원칙

### 6.1 Case Context

Case Context는 사건 판단에 사용하는 Evidence와 Fact입니다.

다음 정보를 보존합니다.

- source
- status
- evidence reference
- version
- timestamp
- current / superseded 의미

다음 상태를 혼동하지 않습니다.

- `CUSTOMER_STATEMENT`
- `PROPOSED`
- `CONFIRMED`
- `VERIFIED`
- `BANK_RECORD`

원칙:

- Evidence에 없는 사건 사실을 생성하지 않습니다.
- 고객 진술만으로 객관적 사실을 확정하지 않습니다.
- `PROPOSED`를 자동으로 `CONFIRMED` 또는 `VERIFIED`로 승격하지 않습니다.

### 6.2 Conversation Context

Conversation Context는 자연스럽고 이어지는 대화를 위해 사용하는 정보입니다.

예:

- 방금 사용자가 말한 내용
- 이름·호칭·인사
- 직전 질문과 답변
- 현재 대화 흐름
- 현재 지시 대상

Conversation Context는 대화 응답에는 사용할 수 있지만:

- Case Fact로 자동 등록하지 않습니다.
- `VERIFIED` 정보로 승격하지 않습니다.
- 사건 판단 Evidence로 자동 사용하지 않습니다.

### 6.3 두 Context의 연결

```text
Conversation Context
→ 현재 질문 이해와 자연스러운 대화

Case Context
→ 사건 판단과 Evidence 기반 답변
```

Conversation에서 나온 사건 관련 진술은 기존 Case Context 반영 Workflow를 통해 별도로 구조화합니다.

예:

```text
고객: 이미 100만 원 송금했어요.
```

이 내용은 현재 대화를 이해하는 데 사용할 수 있고, 기존 Workflow를 통해 `CUSTOMER_STATEMENT` / `PROPOSED` 등 적절한 상태로 반영할 수 있습니다.

단, 자동으로 `VERIFIED`로 승격하지 않습니다.

### 6.4 질문 필요성(Context Sufficiency)과 Fact Verification 분리

질문을 다시 해야 하는지와 사건 사실이 객관적으로 검증됐는지는 같은 판단이 아닙니다.

예:

```text
고객: 상대방이 돈을 요구했지만 보내지는 않았어요.
```

이 발화가 현재 질문 목적에 충분하다면:

```text
transfer_status target
→ 고객 재질문 필요성: 낮음 / 후보 제외 가능
→ Case Fact 상태: CUSTOMER_STATEMENT 또는 PROPOSED 유지 가능
→ VERIFIED 여부: 별도 Evidence / Verification 필요
```

따라서 다음을 구분합니다.

```text
고객에게 다시 물을 필요 없음
!=
객관적으로 VERIFIED 됨
```

질문 계획은 **현재 Case에서 아직 답이 필요한 target인지**를 판단하고, Verification은 **그 답을 어느 수준까지 신뢰·확정할 수 있는지**를 별도로 판단합니다.

---

## 7. 다음 작업 우선순위

| 우선순위 | 작업 | 완료 조건 | 상태 |
|---|---|---|---|
| P0 | 새 Case 초기 Bank AI Quality 차단 마무리 | trigger/세부 판정 원인을 확정하고 최소 수정 후 새 Case 질문이 안정적으로 정상 응답 | `IN_PROGRESS` |
| P1 | 질문 계획 Context 동기화 / 의미 중복 제거 | 이미 충분한 답이 확보된 target 재질문 방지, 동일 target AI 추천 중복 방지 | `TODO` |
| P1 | Bank·Customer 최신 발화 전달 경로 감사 | recent conversation의 수집→General→AI→Provider 전달 확인 | `TODO` |
| P1 | Customer 반복 안전 템플릿 원인 확인 | Prompt / Context / Provider / Quality 중 최초 발생 단계 특정 | `TODO` |
| P1 | Case/Conversation Grounding 구분 | Conversation Context 허용과 Case Evidence 엄격 검증을 함께 유지 | `TODO` |
| P2 | 직접 답변 우선 정책 | 질문에 먼저 답하고 필요한 근거·안전·업무 가이드만 추가 | `TODO` |

기본 진행 순서:

```text
P0 남은 trigger/판정 경로 확인
→ P0 최소 수정
→ P0 자동 테스트 / Runtime / Browser 재검증
→ 질문 계획 Context 동기화 READ-ONLY 감사
→ 질문 target / dedupe 최소 수정
→ 자동 테스트 / Runtime / Browser
→ 나머지 P1 Context / Grounding 개선
→ P2 직접 답변 정책 고도화
```

### 다음 작업 시작점

다음 작업은 P0인 **새 Case 초기 Bank AI `unsupported_certainty` 차단 마무리**입니다.

현재 이미 확인한 내용:

```text
Provider 이후 Quality 단계
→ unsupported_certainty
→ unattributed_certainty_without_confirmed_source
→ AI API 503
→ General 503
→ AI_RESPONSE 미저장
```

다음 P0 작업에서는 다음 두 가지를 우선 확인합니다.

1. `normalization_changed=False`인데 `raw_rules=none`, `normalized_rules=...`가 된 실제 코드 경로
2. 민감정보를 남기지 않으면서 어떤 claim/표현 유형이 `unattributed_certainty_without_confirmed_source`를 발생시켰는지

이를 확인한 뒤 Provider 표현 계약 또는 Quality 오탐 중 실제 원인에 해당하는 가장 좁은 계층만 수정합니다.

P0를 마무리한 뒤에는 **질문 계획 Context 동기화 / 의미 중복 제거**를 다음 우선 작업으로 진행합니다.

---

## 8. 다음 READ-ONLY 감사 범위

### 8.1 P0 남은 감사

현재 P0에서 이미 확인한 호출 구조를 처음부터 다시 감사하지 않습니다.

남은 확인 범위는 다음으로 제한합니다.

1. `unattributed_certainty_without_confirmed_source`의 실제 세부 trigger 경로
2. raw text와 normalized text에 대한 rule 계산 시점과 입력 차이
3. `normalization_changed=False` / `raw_rules=none` / `normalized_rules=...` 조합이 발생하는 이유
4. Provider가 Case source/status를 무시한 확정 표현을 생성했는지
5. Grounding된 표현을 Quality가 오탐한 것인지
6. 기존 `PROPOSED != CONFIRMED` 안전 경계를 유지하면서 가능한 최소 수정 위치
7. 최소 수정 후 같은 Case 질문에서 200 응답이 안정적으로 생성되는지

Prompt 원문 전체, 개인정보, API Key, Secret, Provider 응답 전체는 로그나 문서에 남기지 않습니다.

### 8.2 질문 계획 Context 동기화 READ-ONLY 감사

P0 마무리 후 아래 흐름을 수정 없이 추적합니다.

```text
Customer 일반 MESSAGE
→ Customer AI / Fact extraction / Case Context 반영
→ 질문 plan source 조회
→ 기존 QUESTION / ANSWER 조회
→ canonical target 구성
→ 질문 후보 filtering
→ AI 추천 생성
→ dedupe
→ Bank 질문 선택 UI
```

확인 항목:

1. 고객 일반 대화의 사건 관련 진술이 어디에 어떤 status/source로 저장되는지
2. “송금하지 않았다” 같은 답이 Case Context 또는 Fact projection에 실제 반영되는지
3. 기존 질문 후보의 canonical target이 무엇인지
4. 질문 후보 생성 시 Customer `MESSAGE` / `CUSTOMER_STATEMENT` / `ANSWER`를 모두 사용하는지
5. `PENDING`, `ASKED`, `ANSWERED` 질문이 추천 후보 계산에 어떻게 사용되는지
6. qf1의 canonical target / duplicate protection 로직을 재사용할 수 있는지
7. 기존 질문과 AI 추천 간 dedupe가 문자열인지 semantic/target 기준인지
8. 이미 충분한 답이 확보된 target을 후보에서 제외할 수 있는 최소 수정 위치
9. 후보 제외와 formal lifecycle 상태 변경을 분리할 수 있는지
10. 기존 고정 질문 묶음을 유지·축소·제거할지 결정하기 위해 필요한 실제 의존 관계

감사 단계에서는 기존 질문을 삭제하거나 AI 질문 개수를 4개로 고정하지 않습니다.

---

## 9. 유지해야 할 정상 동작

### 9.1 AI 연속 입력

- Bank 연속 메시지 batching
- Bank in-flight supersede
- Customer 연속 메시지 batching
- Customer in-flight supersede
- Case/requester/channel별 batch 분리
- 저장 성공한 메시지만 batch에 포함
- reload/reconnect 시 과거 MESSAGE 임의 재호출 금지
- stale `AI_RESPONSE` 저장 방지

`03_bank_consecutive_batch_success.png`는 Bank batching의 대표 Browser 회귀 기준입니다.

### 9.2 질문/답변 Workflow

- `PENDING → ASKED → ANSWERED`
- `QUESTION` / `ANSWER` EntryCard
- 일반 `MESSAGE`와 질문 카드 중복 표시 방지
- 고객 질문 한 건씩 노출
- 고객 답변 저장
- 다음 질문 전환
- 고객 답변의 `CUSTOMER_STATEMENT` / `PROPOSED` 의미 보존
- 이미 저장된 질문/답변 이력을 임의 삭제하지 않음
- 일반 대화에서 답이 확보됐다는 이유만으로 formal 질문 lifecycle을 임의 변경하지 않음

### 9.3 질문 계획 / canonical target

후속 개선에서도 다음 의미를 유지합니다.

- 질문 문장과 확인 target은 구분합니다.
- 동일 target에 대한 표현만 다른 질문은 중복일 수 있습니다.
- “질문 후보에서 제외”와 “Fact VERIFIED”는 다른 상태입니다.
- 이미 충분히 답한 target은 새 질문 후보에서 제외할 수 있습니다.
- 아직 검증이 필요한 target은 Verification 흐름으로 남길 수 있습니다.
- 목표 질문 수를 채우기 위한 불필요한 재질문을 생성하지 않습니다.

### 9.4 qf1

qf1은 질문 카드 lifecycle과 별도 검증 축으로 관리합니다.

보존해야 할 규칙:

- parent question 연결
- canonical target
- stale/missing/wrong parent 보호
- 동일 scope 중복 follow-up 방지
- 담당자 승인 전 자동 고객 전달 금지
- `ANSWERED != SUFFICIENT`
- Customer Statement만으로 자동 `CONFIRMED` / `VERIFIED` 금지

자동화 테스트가 있더라도 Browser qf1 E2E가 완료되지 않았다면 Browser 상태를 `DONE`으로 처리하지 않습니다.

### 9.5 실패 경계

- 실패 시 임시 AI 답변을 생성하지 않습니다.
- Evidence에 없는 Case 사실을 fallback으로 만들지 않습니다.
- Provider/Quality 오류를 성공 응답처럼 표시하지 않습니다.
- stale generation은 일반 AI 장애와 구분합니다.

---

## 10. 수정 원칙

- AI를 최종 판단자로 만들지 않습니다.
- Evidence에 없는 Case 사실을 생성하지 않습니다.
- Conversation Context를 자동 `VERIFIED` Fact로 만들지 않습니다.
- 질문 카드, Customer answer lifecycle, qf1을 보존합니다.
- supersede/batching을 보존합니다.
- 원인 확인 없이 Provider·Quality·Grounding 규칙을 완화하지 않습니다.
- 안전 가이드를 제거하지 않고 반복과 우선순위를 조정합니다.
- 새 Agent, RAG, Vector DB, DB 구조를 불필요하게 추가하지 않습니다.
- 원인이 확인된 가장 좁은 계층만 수정합니다.
- 단순 Prompt 변경 전에 실제 Context 전달 구조를 확인합니다.
- 정상 Browser 기능을 회귀시키지 않습니다.
- 질문 중복 문제를 해결하기 위해 질문 이력 전체를 삭제하지 않습니다.
- 일반 대화의 Customer Statement를 자동 `VERIFIED`로 승격하지 않습니다.
- 질문 개수를 맞추기 위해 해결된 target을 다시 추천하지 않습니다.
- 기존 qf1/canonical target 구조를 확인하기 전 별도 중복 시스템을 새로 만들지 않습니다.

---

## 11. 검증 계획과 완료 기준

### 11.1 검증 축

각 항목은 다음 상태를 독립적으로 관리합니다.

```text
Implementation:
TODO | IN_PROGRESS | DONE | BLOCKED

Automated Test:
TODO | IN_PROGRESS | DONE | BLOCKED

REST/Runtime Validation:
TODO | IN_PROGRESS | DONE | BLOCKED

MySQL Validation:
TODO | IN_PROGRESS | DONE | BLOCKED

Browser Validation:
TODO | IN_PROGRESS | DONE | BLOCKED
```

자동화 테스트가 통과해도 Browser 실패가 남으면 전체 완료로 처리하지 않습니다.

Browser가 정상이어도 stale DB row 또는 provenance 검증이 필요한 항목은 MySQL 확인 전 전체 완료로 처리하지 않습니다.

### 11.2 Bank 완료 기준

- 새 Case에서 “현재 상황 어때?”에 안정적으로 정상 응답
- 새 Case에서 “현재 확인된 사항 있어?”에 안정적으로 정상 응답
- 유사한 정상 질문에서 generation 표현 차이 때문에 간헐적으로 503이 발생하지 않음
- 현재 확인된 내용과 미확인 내용을 source/status에 맞게 구분
- `PROPOSED` / `CUSTOMER_STATEMENT`를 객관적 확정 사실처럼 표현하지 않음
- Evidence에 없는 사건 사실을 확정하지 않음
- Conversation Context 발화에 오류 없이 짧게 반응
- 이름·호칭을 Case Fact 또는 `VERIFIED` Evidence로 승격하지 않음
- 사건 관련 질문에는 최신 Case Context 사용
- 관련성이 낮은 질문에는 짧게 답하고 필요한 경우에만 업무 가이드 추가
- 여러 메시지 입력 시 최종 유효 batch의 AI 응답만 표시
- superseded `AI_RESPONSE`가 DB에 저장되지 않음

### 11.3 Customer 완료 기준

- 이름·인사·간단한 질문에 해당 발화와 맞는 직접 응답
- 모든 질문에 동일 안전 템플릿을 반복하지 않음
- 위험 관련 질문에는 필요한 안전 가이드 유지
- 최신 사용자 발화를 응답에 반영
- Conversation Context와 사건 사실을 혼동하지 않음
- 여러 메시지 입력 시 최종 유효 batch의 응답만 표시
- superseded `AI_RESPONSE`가 DB에 저장되지 않음

### 11.4 질문 계획 / 질문 카드 / qf1 완료 기준

#### 질문 계획 Context 동기화

- Customer 일반 대화에서 충분히 답한 canonical target이 새 질문 후보에서 제외됨
- “송금하지 않았다”는 충분한 Customer Statement가 존재하면 동일 transfer target을 다시 추천하지 않음
- 기존 질문과 AI 추천이 표현만 다르고 target이 같다면 중복 생성하지 않음
- 이미 해결된 target 대신 아직 unresolved인 다른 중요 target을 우선 추천함
- unresolved target이 4개 미만이라고 불필요한 질문으로 개수를 채우지 않음
- 후보 제외가 `VERIFIED` 승격을 의미하지 않음
- 질문 이력과 Case provenance가 유지됨

#### 질문 카드 / Customer answer lifecycle

- 담당자 질문 등록 후 Bank ROOM에 질문 카드 표시
- Customer ROOM에는 현재 `ASKED` 질문만 노출
- 고객 답변 후 동일 질문이 `ANSWERED`로 갱신
- 질문·답변 카드가 일반 MESSAGE와 중복되지 않음
- 다음 질문이 정상 전환됨

#### qf1

- parent question 기준 follow-up 생성
- 잘못된 parent / stale parent 사용 금지
- 같은 scope 중복 생성 금지
- 담당자 승인 없이 자동 고객 전달 금지
- Browser에서 qf1 생성→질문→답변→Context 갱신 확인

### 11.5 공통 완료 기준

- stale `AI_RESPONSE` 없음
- 새로고침 후 질문·응답·순서·상태 일관성 유지
- 질문 카드·qf1 회귀 없음
- 기존 정상 Case 응답 회귀 없음
- 실패 시 원인 단계와 사용자 안내가 일치
- 가짜 성공 응답을 만들지 않음
- Browser와 REST/MySQL 결과가 다르면 불일치 해결 전 완료 처리하지 않음

---

## 12. 현재 작업 보드

| 항목 | Implementation | Automated Test | REST/Runtime | MySQL | Browser |
|---|---|---|---|---|---|
| Bank 연속 입력 batching | `DONE` | `DONE` | `TODO` | `TODO` | `DONE` |
| Bank in-flight supersede / stale 억제 | `DONE` | `DONE` | `TODO` | `TODO` | `IN_PROGRESS` |
| Customer supersede/batching | `DONE` | `DONE` | `TODO` | `TODO` | `IN_PROGRESS` |
| 질문 카드 / Customer answer lifecycle | `DONE` | `DONE` | `TODO` | `TODO` | `DONE` |
| qf1 follow-up | `DONE` | `DONE` | `TODO` | `TODO` | `TODO` |
| 새 Case 초기 Bank Quality 차단 해결 | `IN_PROGRESS` | `IN_PROGRESS` | `IN_PROGRESS` | `TODO` | `IN_PROGRESS` |
| 질문 계획 Context 동기화 / 중복 제거 | `TODO` | `TODO` | `TODO` | `TODO` | `IN_PROGRESS` |
| Customer 최신 발화 직접 응답 | `TODO` | `TODO` | `TODO` | `TODO` | `IN_PROGRESS` |
| Bank Conversation Context 응답 | `TODO` | `TODO` | `TODO` | `TODO` | `IN_PROGRESS` |
| Case / Conversation Grounding 구분 | `TODO` | `TODO` | `TODO` | `TODO` | `TODO` |
| 직접 답변 우선 응답 정책 | `TODO` | `TODO` | `TODO` | `TODO` | `TODO` |

### 상태 해석

- Bank batching Browser `DONE`은 여러 연속 질문이 하나의 응답으로 처리된 화면을 의미합니다.
- Bank supersede Browser는 별도 항목으로 `IN_PROGRESS`를 유지합니다.
- Customer supersede 자동화 `DONE`은 기존 구현 단계의 테스트 결과를 기준으로 하며 후속 변경 뒤 다시 검증합니다.
- qf1은 코드·자동화 검증과 Browser E2E를 분리하며 Browser는 아직 `TODO`입니다.
- P0 Quality 차단은 실패 계층·criterion·세부 rule까지 확인됐지만 실제 최소 수정은 아직 완료되지 않아 `IN_PROGRESS`입니다.
- P0 관측성 관련 선택 테스트는 `64 passed, 59 subtests passed`였으나 실제 fix 이후 회귀 테스트를 다시 수행해야 합니다.
- 질문 계획 Context 동기화는 Browser에서 문제를 확인했으므로 Browser `IN_PROGRESS`, 구현·자동화는 아직 `TODO`입니다.
- `IN_PROGRESS` Browser 항목은 현재 실패 또는 불완전 동작이 관찰되어 수정 후 재검증이 필요합니다.

---

## 13. 현재 확정 / 검토 중 구분

### 13.1 확정

- 사용자 최신 질문에 먼저 답하는 응답 정책
- Case Fact와 Conversation Context 구분
- `PROPOSED != CONFIRMED`
- `CUSTOMER_STATEMENT != VERIFIED FACT`
- `ANSWERED != SUFFICIENT`
- 담당자 승인 전 질문 자동 전송 금지
- 이미 충분히 답한 canonical target의 불필요한 재질문 방지
- 동일 canonical target의 의미 중복 질문 방지
- 일반 Customer 대화에서 확보한 답도 질문 필요성 판단에 사용
- 질문 필요성 판단과 Verification을 별도 축으로 관리
- 기존 질문/답변 이력과 provenance 보존
- P0 마무리 후 질문 계획 Context 동기화를 다음 우선 작업으로 진행

### 13.2 검토 중

- Case별 초기 확인 target을 약 4개 수준으로 제한하는 UI/정책
- 기존 고정 질문 묶음의 축소 또는 제거
- AI가 Case별 필수 확인 target을 동적으로 구성하는 방식
- unresolved target 우선순위 계산 방식
- 일반 대화로 해결된 PENDING 후보를 DB 상태 변경 없이 UI에서 제외할지 여부

### 13.3 현재 확정하지 않는 것

- 모든 Case에 질문을 정확히 4개 생성
- 고객 일반 발화만으로 Fact를 `CONFIRMED` / `VERIFIED`로 승격
- 해결된 질문 record 자체를 삭제
- 기존 질문 카드 lifecycle을 새 구조로 전면 재작성
- qf1/canonical target 구조를 확인하지 않고 별도 질문 중복 시스템을 신규 구축

---

## 14. 문서 운영 규칙

- 주요 작업은 `TODO`, `IN_PROGRESS`, `DONE`, `BLOCKED`로 관리합니다.
- Implementation / Automated Test / REST/Runtime / MySQL / Browser 상태를 독립적으로 기록합니다.
- 새로운 증거에는 날짜, Case 조건, 입력, 관찰 결과, 검증 축을 함께 기록합니다.
- 원인 후보는 증거 확보 전까지 `확인 필요` 또는 `가설`로 유지합니다.
- Browser와 코드·자동화·REST·MySQL 결과가 다르면 한 상태로 합치지 않습니다.
- 정상 동작도 회귀 테스트와 Browser 수용 기준에 포함합니다.
- 원인이 확인된 가장 작은 계층만 수정합니다.
- 이미 안정화된 질문 카드, qf1, Customer answer lifecycle, supersede/batching을 불필요하게 재작성하지 않습니다.
- P0를 마무리한 뒤 질문 계획 Context 동기화 / 의미 중복 제거를 우선 진행합니다.
- P0 원인 경계가 확인된 현재 단계에서도 Quality/Grounding 기준을 근거 없이 광범위하게 완화하지 않습니다.
- 새로운 기능보다 현재 Case Workflow가 처음부터 끝까지 끊기지 않는 것을 우선합니다.
