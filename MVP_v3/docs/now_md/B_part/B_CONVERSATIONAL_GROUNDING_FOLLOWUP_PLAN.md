# B Part 대화·Grounding 후속 개선 계획

작성일: 2026-09-20  
상태: 기준 문서 작성 `DONE` / 후속 원인 감사 및 구현 `TODO`

이 문서는 Browser 검증에서 확인한 Bank AI·Customer AI의 대화 품질과 Grounding 문제를 후속 작업의 공통 기준으로 정리합니다.

목표는 자유 대화 챗봇이 아니라 **현재 질문에 직접 답하면서 Case 근거와 필요한 안전·업무 가이드를 제공하는 대화 가능한 업무 코파일럿**입니다.

이번 문서 작성에서는 코드, DB, API, Prompt, Quality, Grounding 기준을 변경하거나 Runtime·MySQL을 새로 검증하지 않았습니다. 원인 관련 내용은 Browser에서 확인한 사실과 분리하여 `확인 필요` 또는 `가설`로 기록합니다.

---

## 1. 범위와 판정 원칙

### 1.1 후속 개선 범위

- Case 생성 직후 Bank 첫 AI 응답 실패
- Customer AI의 반복 안전 응답
- Bank AI의 Conversation Context 처리
- Bank·Customer 최신 발화 반영
- 질문에 직접 답하는 응답 정책
- Case Context와 Conversation Context의 Grounding 구분
- 기존 supersede/batching 회귀 방지
- 기존 질문 카드·Customer answer·qf1 흐름 회귀 방지
- 후속 READ-ONLY 감사 및 Browser 완료 기준

### 1.2 판정 원칙

- 첨부 화면은 해당 시점 Browser에서 관찰한 현상의 증거입니다.
- 화면만으로 Provider, Parsing, Contract, Quality, Grounding, Formatter 중 실패 지점을 확정하지 않습니다.
- Implementation, Automated Test, REST/Runtime, MySQL, Browser는 서로 다른 검증 축으로 관리합니다.
- `MESSAGE` 저장 성공은 `AI_RESPONSE` 생성·저장 성공을 의미하지 않습니다.
- 여러 사용자 메시지가 하나의 응답에 반영됐다는 사실만으로 in-flight supersede와 stale DB 저장 차단까지 검증됐다고 판단하지 않습니다.
- Conversation Context 입력 직후 오류가 발생해도 Runtime 근거 없이 직접 인과관계를 확정하지 않습니다.
- 원인을 확인하기 전에 Prompt, Quality, Grounding 기준을 임의로 완화하지 않습니다.

---

## 2. 현재 Browser 검증 상태

| 영역 | 현재 판정 | Browser에서 확인한 내용 | 추가 확인 |
|---|---|---|---|
| Bank 연속 입력 batching | `DONE` | 여러 담당자 질문이 하나의 CaseCopilot 응답에 함께 반영됨 | 후속 변경 후 회귀 확인 |
| Bank in-flight supersede / stale 억제 | `IN_PROGRESS` | 연속 입력 통합 응답은 확인했으나 실제 generation stale 여부는 화면만으로 확정하기 어려움 | Network·MySQL 대조 |
| Customer supersede/batching | `IN_PROGRESS` | 연속 발화가 하나의 응답 흐름으로 처리되는 것으로 보임 | invocation·응답·DB 메시지 수 대조 |
| 질문 카드 / Customer answer lifecycle | `DONE` | 질문 등록→고객 노출→답변 반영 흐름 정상 | 후속 변경 후 회귀 확인 |
| qf1 follow-up | `TODO` | 코드·자동화 검증은 있으나 Browser E2E 증거 부족 | qf1 child 실제 흐름 확인 |
| Bank 일부 Case 기반 응답 | `DONE` | 고객 대화가 누적된 뒤 일부 질문에 Case 기반 응답 생성 | 새 Case 첫 응답과 구분 |
| 새 Case Bank 첫 AI 응답 | `IN_PROGRESS` | 정상 Case 질문 뒤 `AI_RESPONSE` 없이 오류 배너 발생 | Runtime 최초 실패 경계 확인 |
| Customer 최신 발화 반영 | `IN_PROGRESS` | 서로 다른 발화에도 유사한 안전 안내 반복 | Provider 입력 경로 확인 |
| Bank Conversation Context | `IN_PROGRESS` | 이름을 기억해 달라는 흐름에서 자연스러운 응답 대신 오류 관찰 | 직접 인과관계와 차단 단계 확인 |

> `03_bank_consecutive_batch_success.png`는 **Bank 연속 입력 batching의 대표 Browser 정상 기준**입니다.
>
> 이 화면만으로 in-flight supersede와 stale `AI_RESPONSE` DB 미저장까지 검증됐다고 판단하지 않습니다.

---

## 3. 첨부 Browser 증거

### 3.1 `01_bank_initial_response_failure.png`

#### 관찰 사실

- Case 생성 직후 담당자가 “현재 확인된 사항 있어?”, “지금 상황 어때?” 같은 정상적인 Case 질문을 전송했습니다.
- 담당자 `MESSAGE`는 화면에 남아 있습니다.
- Bank `AI_RESPONSE`는 표시되지 않았습니다.
- 상단 오류 배너가 표시됐습니다.

#### 판정

- `Bank 첫 AI 응답 실패`의 Browser 증거입니다.
- 어느 단계에서 실패했는지는 화면만으로 확정할 수 없습니다.
- Case 생성 직후에도 Initial Report, Case Context, FDS, STT, 분석 결과가 존재할 수 있으므로 입력 정보가 전혀 없었다고 가정하지 않습니다.
- Runtime 로그와 실제 invocation payload를 기준으로 최초 실패 경계를 확인해야 합니다.

---

### 3.2 `02_customer_repetitive_safety_response.png`

#### 관찰 사실

- 고객은 이름 소개, 인사, 다른 답변 요청처럼 서로 다른 발화를 했습니다.
- Customer AI는 추가 송금 중단, 상대방과의 접촉 중단, 공식기관 연락 등의 유사한 안내를 반복했습니다.
- 안전 방향은 유지하지만 최신 사용자 발화에 대한 직접 응답이 부족합니다.

#### 판정

- `Customer 최신 발화 반영 부족 및 안전 템플릿 반복`의 Browser 증거입니다.
- 안전 가이드 자체가 문제가 아니라 **현재 질문보다 유사한 전체 안전 안내가 반복적으로 우선되는 점**이 문제입니다.
- Prompt, Context, Provider, Quality/Rewrite 중 어디에서 반복이 시작되는지는 추가 확인이 필요합니다.

---

### 3.3 `03_bank_consecutive_batch_success.png`

#### 관찰 사실

- 담당자가 송금 상태, 고객 상태, 고객 성명에 관한 질문을 연속으로 입력했습니다.
- 하나의 CaseCopilot 응답이 여러 질문을 함께 다루었습니다.
- 확인된 내용과 미확인 내용을 구분하려는 응답이 생성됐습니다.

#### 판정

- **Bank 연속 입력 batching의 대표 Browser 정상 기준**입니다.
- 후속 Quality·Grounding 수정 뒤에도 이 동작을 보존해야 합니다.
- stale `AI_RESPONSE` 부재는 Browser가 아닌 REST/MySQL에서 별도 확인합니다.

---

### 3.4 `04_bank_conversation_local_name_failure.png`

#### 관찰 사실

- 담당자가 “내 이름은 김은행인데 기억해줬으면 좋겠어”라는 Conversation Context 정보를 입력했습니다.
- 같은 흐름에서 자연스러운 대화 응답이 이어지지 않고 오류가 관찰됐습니다.

#### 판정

- `Bank Conversation Context 처리`의 분석 대상입니다.
- 현재 증거만으로 이름 입력이 오류를 직접 유발했다고 확정하지 않습니다.
- 정확한 표현은 **Conversation Context 입력이 포함된 같은 Browser 흐름에서 오류를 관찰함**입니다.

---

## 4. 확인된 문제와 원인 후보

### A. Case 생성 직후 Bank 첫 AI 응답 실패 — `P0 / TODO`

#### 현상

새 Case에서 정상적인 사건 질문을 보내도 `MESSAGE` 저장 이후 `AI_RESPONSE`가 생성·전달되지 않는 경우가 있습니다.

담당자가 Case ROOM 진입 직후 가장 먼저 사용할 가능성이 높은 다음 질문이 실패하므로 핵심 Workflow를 중단시키는 문제입니다.

```text
현재 상황 어때?
현재 확인된 사항 있어?
무엇을 먼저 확인해야 해?
```

#### 확인 필요

- 첫 Bank AI invocation payload
- Initial Report / Case Context / Evidence / recent conversation 포함 여부
- General → AI API status와 error code
- Provider → Parsing → Contract → Quality → Grounding → Formatter 중 최초 실패 단계
- Case 생성 직후 데이터 준비 또는 projection 상태 문제 여부
- `AI_RESPONSE` 저장 직전까지 도달했는지 여부

#### 현재 결론

- 실패 현상은 확인했습니다.
- 최초 실패 원인은 아직 `확인 필요`입니다.
- Runtime 근거 없이 Provider, Quality 또는 Grounding 문제로 단정하지 않습니다.

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
- Provider의 직접 응답이 Quality/Rewrite 단계에서 반복 템플릿으로 바뀌는지
- 이전 AI 응답이 반복을 강화하는 구조인지

#### 가설

다음 중 하나 이상이 영향을 줄 수 있습니다.

- 위험 Context 우선순위가 지나치게 높음
- recent conversation 전달 누락 또는 정렬 문제
- Prompt에서 Case Context가 최신 사용자 요청보다 과도하게 우선됨
- 전체 안전 안내 반복을 Prompt가 강제함
- Quality/Rewrite 단계에서 응답이 유사 안전 템플릿으로 정규화됨

감사 전에는 어느 가설도 사실로 취급하지 않습니다.

---

### C. Bank Conversation Context 처리 — `P1 / TODO`

#### 현상

이름, 호칭, 인사처럼 사건 Evidence가 아닌 대화 정보에 짧고 자연스럽게 반응하지 못하거나 같은 흐름에서 오류가 관찰됩니다.

#### 확인 필요

- recent conversation에서 해당 발화의 role·순서·범위
- Conversation Context가 Case Fact 또는 Evidence claim으로 잘못 해석되는지
- Quality/Grounding이 Evidence에 없는 이름을 unsupported Case fact로 판단하는지
- Provider 응답은 정상이었지만 후단 검사에서 차단되는지
- 새 Case 첫 응답 실패와 동일 원인인지 여부
- Case Grounding과 Conversation Grounding을 분리할 수 있는 최소 수정 위치

#### 가설

Case Grounding 규칙이 Conversation Context에도 동일하게 적용되어 과도하게 차단할 가능성이 있습니다.

이 가설은 실제 payload와 단계별 로그 확인 전에는 확정하지 않습니다.

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
현재 확인된 내용은 상대방이 고객에게 송금을 유도하고
앱 설치를 요구했다는 점입니다.

실제 송금 완료 여부는 아직 확인되지 않았습니다.

우선 고객에게 송금 여부와 앱 설치 여부를 확인하는 것이 좋습니다.
```

### 예시 3 — Customer 위험 발화

```text
고객: 상대방이 지금 바로 다시 송금하라고 해요.

AI:
추가 송금은 하지 않는 것이 좋습니다.

상대방과의 통화나 메시지를 중단하고,
현재 상황을 담당자와 확인해 주세요.
```

---

## 6. Context 구분 원칙

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

---

## 7. 다음 작업 우선순위

| 우선순위 | 작업 | 완료 조건 | 상태 |
|---|---|---|---|
| P0 | Case 생성 직후 Bank 첫 AI 응답 실패 | 최초 실패 단계와 재현 조건을 특정하고 새 Case 질문에 정상 응답 | `TODO` |
| P1 | Bank·Customer 최신 발화 전달 경로 감사 | recent conversation의 수집→General→AI→Provider 전달 확인 | `TODO` |
| P1 | Customer 반복 안전 템플릿 원인 확인 | Prompt / Context / Provider / Quality/Rewrite 중 최초 발생 단계 특정 | `TODO` |
| P1 | Case/Conversation Grounding 구분 | Conversation Context 허용과 Case Evidence 엄격 검증을 함께 유지 | `TODO` |
| P2 | 직접 답변 우선 정책 | 질문에 먼저 답하고 필요한 근거·안전·업무 가이드만 추가 | `TODO` |

기본 진행 순서:

```text
P0 READ-ONLY 원인 감사
→ P0 최소 수정
→ P1 Context 전달 감사
→ P1 Grounding/반복 원인 수정
→ 자동 테스트
→ REST/Runtime
→ MySQL
→ Browser
→ P2 응답 정책 고도화
```

### 다음 작업 시작점

다음 Codex 작업은 P0인 **Case 생성 직후 Bank 첫 AI 응답 실패 READ-ONLY 감사**입니다.

다음 흐름에서 최초 실패 지점을 추적합니다.

```text
Bank MESSAGE
→ Frontend AI invocation
→ General API
→ Case Context / recent conversation 구성
→ AI API
→ Provider
→ Parsing
→ Contract
→ Quality
→ Grounding
→ Formatter
→ AI_RESPONSE 저장
→ Browser 표시
```

원인을 확인하기 전에는 Prompt 또는 Quality/Grounding 기준을 광범위하게 수정하지 않습니다.

---

## 8. 다음 READ-ONLY 감사 범위

구현 전에 아래를 수정 없이 확인합니다.

1. Case 생성 직후 Bank AI invocation payload와 requester 정보
2. Initial Report, Case Context, Evidence, FDS/STT·분석 결과의 실제 포함 여부와 truncation 상태
3. Provider → Parsing → Contract → Quality → Grounding → Formatter 중 첫 Bank 응답의 최초 실패 단계
4. General API에서 AI 호출 후 `AI_RESPONSE` 저장까지의 실제 흐름
5. Bank recent conversation의 수집 범위, 정렬, role/requester, 길이 제한, Provider 전달 형태
6. Customer recent conversation의 수집→General→AI→Provider 전달 경로
7. Customer 반복 안전 문구가 Prompt, Context, Provider, Quality/Rewrite 중 처음 생성되는 위치
8. Conversation Context가 Quality/Grounding에서 차단되는 조건
9. Case Grounding과 Conversation Grounding을 최소 수정으로 분리할 수 있는 계층
10. 새 Case 첫 Bank 응답 실패와 Conversation Context 오류가 같은 원인인지 여부
11. Bank·Customer superseded 요청의 `AI_RESPONSE`가 실제로 저장되지 않는지 REST/MySQL read-back

감사 결과에는 다음을 기록합니다.

- 입력 존재 여부
- 데이터 출처
- 전달 범위
- 최초 실패 위치
- 재현 여부

Prompt 원문 전체, 개인정보, API Key, Secret 등 민감정보는 로그나 문서에 남기지 않습니다.

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

### 9.3 qf1

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

### 9.4 실패 경계

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

- 새 Case에서 “현재 상황 어때?”에 정상 응답
- 새 Case에서 “현재 확인된 사항 있어?”에 정상 응답
- 현재 확인된 내용과 미확인 내용을 구분
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

### 11.4 질문/qf1 완료 기준

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
| 새 Case Bank 첫 응답 실패 해결 | `TODO` | `TODO` | `TODO` | `TODO` | `IN_PROGRESS` |
| Customer 최신 발화 직접 응답 | `TODO` | `TODO` | `TODO` | `TODO` | `IN_PROGRESS` |
| Bank Conversation Context 응답 | `TODO` | `TODO` | `TODO` | `TODO` | `IN_PROGRESS` |
| Case / Conversation Grounding 구분 | `TODO` | `TODO` | `TODO` | `TODO` | `TODO` |
| 직접 답변 우선 응답 정책 | `TODO` | `TODO` | `TODO` | `TODO` | `TODO` |

### 상태 해석

- Bank batching Browser `DONE`은 여러 연속 질문이 하나의 응답으로 처리된 화면을 의미합니다.
- Bank supersede Browser는 별도 항목으로 `IN_PROGRESS`를 유지합니다.
- Customer supersede 자동화 `DONE`은 기존 구현 단계의 테스트 결과를 기준으로 하며 이 문서 작성 과정에서 다시 실행한 것은 아닙니다.
- qf1은 코드·자동화 검증과 Browser E2E를 분리하며 Browser는 아직 `TODO`입니다.
- `IN_PROGRESS` Browser 항목은 현재 실패 또는 불완전 동작이 관찰되어 수정 후 재검증이 필요합니다.
- 이 문서 작성 단계에서 Runtime, MySQL, 자동화 테스트를 새로 실행한 것으로 해석하지 않습니다.

---

## 13. 문서 운영 규칙

- 주요 작업은 `TODO`, `IN_PROGRESS`, `DONE`, `BLOCKED`로 관리합니다.
- Implementation / Automated Test / REST/Runtime / MySQL / Browser 상태를 독립적으로 기록합니다.
- 새로운 증거에는 날짜, Case 조건, 입력, 관찰 결과, 검증 축을 함께 기록합니다.
- 원인 후보는 증거 확보 전까지 `확인 필요` 또는 `가설`로 유지합니다.
- Browser와 코드·자동화·REST·MySQL 결과가 다르면 한 상태로 합치지 않습니다.
- 정상 동작도 회귀 테스트와 Browser 수용 기준에 포함합니다.
- 원인이 확인된 가장 작은 계층만 수정합니다.
- 이미 안정화된 질문 카드, qf1, Customer answer lifecycle, supersede/batching을 불필요하게 재작성하지 않습니다.
- P0 → P1 → P2 순서를 기본으로 진행합니다.
- P0 최초 실패 경계 확인 전 광범위한 Prompt 변경을 시작하지 않습니다.
- 새로운 기능보다 현재 Case Workflow가 처음부터 끝까지 끊기지 않는 것을 우선합니다.