# B Part 기능 계약

이 문서는 B Part 기능의 현재 공식 계약을 정의한다.

## 1. Semantic State

현재 semantic state:

```text
UNRESOLVED
WAITING
CLEAR_CUSTOMER_STATEMENT
UNCERTAIN
CONFLICT
STAFF_CONFIRMED
VERIFIED
SKIPPED
```

Semantic State 판단은 `QuestionStateEvaluator`가 single source of truth다.

Lifecycle:

```text
PENDING
ASKED
ANSWERED
SKIPPED
```

와 semantic sufficiency를 혼동하지 않는다.

## 2. Question Eligibility

Eligibility 판단은 `QuestionPolicy`가 single source of truth다.

대표 규칙:

* 명확한 고객 진술은 동일 basic 질문 반복 억제
* ANSWERED만으로 해결 처리하지 않음
* UNCERTAIN은 의미 있는 follow-up 가능
* WAITING은 즉시 follow-up하지 않음
* SKIPPED는 즉시 동일 질문 재추천하지 않음
* PENDING / ASKED 중복 보호 유지
* PROPOSED Fact 존재만으로 확인 완료 처리하지 않음

## 3. Dynamic Follow-up

현재 follow-up 최소 contract:

```text
basic:
<canonical-scope>

follow-up:
qf1:<canonical-scope>:<parent-question-id>
```

규칙:

* follow-up target 생성/검증/해석은 공통 helper가 담당
* 각 서비스가 문자열을 직접 임의 파싱하지 않음
* parent는 같은 Case의 실제 질문이어야 함
* parent 질문은 ANSWERED 상태여야 함
* 현재 최소 구현은 parent당 follow-up 최대 1개
* 동일 semantic scope의 PENDING / ASKED 질문이 있으면 차단
* 같은 parent의 반복 follow-up 차단
* follow-up 답변을 자동 correction / CONFIRMED / VERIFIED로 처리하지 않음
* 고객에게 자동 전송하지 않음

LLM 역할:

* 질문 문장
* 짧은 reason
* 필요한 경우 options

서버 역할:

* semantic scope
* parent
* eligibility
* follow-up target
* safety
* dedupe
* normalization

LLM이 서버 식별자를 결정하지 않는다.

## 4. Bank Copilot 기본 계약

Bank Copilot은 현재 Case Context를 이용해 담당자의 판단을 지원한다.

목표:

```text
현재 질문에 직접 답하기
+
누적 Case Context 활용
+
근거 수준 구분
+
불확실성 표시
+
불필요한 장문 억제
```

반드시 구분해야 하는 개념:

* CUSTOMER_STATEMENT
* staff confirmation
* BANK_RECORD
* 기타 Evidence
* 실제 scope가 연결된 completed Verification
* 미확인 / 불확실 / 충돌

고객 진술만으로 객관 사실을 확정적으로 표현하지 않는다.

예:

```text
"고객은 1,000만원을 송금했다고 진술했습니다.
현재 전달된 거래 Evidence만으로 실제 이체 완료 여부는 확인되지 않았습니다."
```

## 5. Source-aware Grounding 원칙

현재 Case 저장 구조에는 provenance 정보가 존재할 수 있으나,
Bank Copilot 전달 과정에서 문자열로 축약되면 의미가 손실될 수 있다.

P3-4에서는 가능한 범위에서 다음 정보를 typed context로 유지한다.

```text
source
status
evidence reference
version
timestamp
supersede/current
```

주의:

* `CONFIRMED` != `BANK_RECORD`
* EvidenceRef 존재 != Evidence 내용 검증 완료
* retrieval hit != VERIFIED
* 오래된 customer message를 최신 current Fact보다 우선하지 않음
* conflict/correction 정보가 없으면 임의로 최신값을 선택하지 않음

## 6. 계층별 책임

```text
QuestionStateEvaluator
→ semantic state

QuestionPolicy
→ question eligibility

CaseSnapshotAdapter
→ typed input 준비 / semantic 연결

QuestionService
→ deterministic candidate

WorkCardService
→ 제한된 LLM question generation

General API
→ orchestration / contract 전달

Repository
→ 저장 / duplicate protection

Bank Copilot
→ 제공된 Case Context 기반 설명

CopilotQualityEvaluator
→ role / safety / certainty / quality 검사
```

각 계층이 다른 계층의 semantic 규칙을 중복 구현하지 않는다.

## 7. 현재 보류 영역

다음은 핵심 Workflow 안정화 후 필요성을 다시 평가한다.

* Official Corpus
* RAG
* Vector DB
* 공식기관 Verification 고도화

현재 P3 작업의 필수 선행 조건으로 간주하지 않는다.
