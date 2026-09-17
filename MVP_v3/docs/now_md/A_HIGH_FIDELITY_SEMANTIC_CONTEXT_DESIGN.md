# High-Fidelity Semantic Context Pipeline 설계안

작성일: 2026-09-16  
상태: Phase B~F 구조화 출력·저장 구현 완료, 핵심 Fact projection·Grounded 패널 문장화·중앙 직원용 표시 구현 (전체 semantic coverage 진행 중)

## 1. 목적과 범위

이 문서는 통화 원문 transcript를 장기 보관하지 않는 환경에서, 나중에 사건 맥락을 재구성할 수 있을 만큼 세밀한 의미·표현·관계 정보를 보존하는 v3.1 설계 기준이다. 다만 은행직원·고객이 서비스 안에서 직접 입력한 채팅과 카드 답변은 별도 데이터 분류로 보며, 내부 정책과 법무 검토가 허용하는 범위에서 원문을 저장할 수 있다.

통화 원문에 대한 목표는 원문 복원이 아니다. 통화 분석 시점에만 원문을 사용하고, 저장소에는 다음 정보를 계층적으로 남긴다. 반면 채팅·카드 답변은 원문 자체와 구조화 결과를 함께 보존할 수 있으며, 구조화 결과에는 동일한 lineage 규칙을 적용한다.

- 누가, 누구에게, 무엇을 주장·요구·지시·금지했는가
- 어떤 기관·역할·사건·행동·대상·금액·목적을 언급했는가
- 표현의 강도, 긴급성, 협박·고립·비밀 요구, 조건·부정 여부
- 각 결과가 어느 message/turn에서 파생되었는지와 추출·모델 버전
- 관찰된 사실(Observed), 시스템이 조합한 신호(Derived), 직원이 확인한 사실(Confirmed), 생성 문장(Reconstructed)의 구분

현재 구현은 Phase B의 병행 출력에서 확장되어 Semantic Atom·Relation·Context Signal 저장, 핵심 `PROPOSED` Fact projection과 은행용 grounded 문장, 중앙 `analysis-result created`의 전체 의미 피처 표시까지 포함한다. DB migration과 FastAPI 계약은 확장되었지만 ML artifact·feature vector·threshold 경계는 변경하지 않는다. 전체 semantic key coverage, 다중 값 합계·편집, 요약·질문까지의 L6 검증은 아직 진행 중이다.

## 2. 현재 구현과의 경계

현재 v3.1 baseline은 `d2832c74`이며, 다음 영역은 frozen boundary로 취급한다.

- Window ML feature 이름·순서·개수·shape·window 로직·artifact
- 기존 Event/DiagnosisResult와 risk fusion 계약
- Context Panel의 기존 projection 및 visibility 규칙
- AI가 DB를 직접 수정하지 않고 General API가 검증·저장하는 규칙
- AI 생성 Fact는 `PROPOSED`에서 시작하고 직원 확인 후에만 `CONFIRMED`가 되는 규칙
- 통화·STT 원문에 대한 raw transcript, full transcript, raw_text, evidence span, verbatim sentence 및 민감 literal의 영구 저장 금지
- 서비스 내부 채팅·카드 답변은 출처 채널과 보존 정책을 명시하면 원문 저장 가능

새 계층은 기존 Event를 대체하지 않고 adapter로 병행 연결한다. ML 입력에는 새 필드를 넣지 않는다.

## 3. 전체 파이프라인

```text
RAW INPUT (통화 원문은 분석 시점에만 존재; 채팅/카드 답변은 정책상 저장 가능)
        |
        v
L0 Provenance ---------------- source/message/turn/버전/지문
        |
        v
L1 Semantic Atom ------------- 최소 의미 단위
        |
        v
L2 Expression Feature -------- lexical·speech-act·pragmatics
        |
        v
L3 Relation / Group / Entity - 인과·대상·참조·에피소드
        |
        v
L4 Derived Context Signal ---- 여러 atom을 조합한 위험 신호
        |
        v
L5 Context Fact -------------- PROPOSED -> CONFIRMED / REJECTED / SUPERSEDED
        |
        v
L6 Grounded Reconstruction --- summary/question/report/panel 문장
        |
        v
Reconstruction Validator ------ 근거 밖 생성 차단
```

각 단계는 입력·출력·근거 ID를 명시한다. 통화 원문 문자열은 다음 단계에 무제한 전달하지 않고 분석 메모리 안에서만 사용한다. 채팅·카드 원문은 허용된 visibility와 목적 범위에서만 전달한다.

## 4. L0 Provenance

저장 허용 provenance 예시는 다음과 같다.

```json
{
  "message_id": "MSG-00123",
  "turn_id": 17,
  "conversation_sequence": 31,
  "speaker": "CALLER",
  "source_channel": "CALL_STT",
  "source_fingerprint": "sha256:...",
  "extractor_run_id": "EXT-20260916-001",
  "schema_version": "semantic-context.v1",
  "extractor_version": "llm-semantic-v1",
  "prompt_version": "prompt-2026-09",
  "model_version": "gpt-4o-mini"
}
```

`source_fingerprint`는 동일 입력 재처리·중복 방지용이며 원문 복원용으로 사용하지 않는다. `message_id`, `turn_id`, sequence는 cross-turn 관계와 감사 추적에 필요하다.

## 5. L1 Semantic Atom

Semantic Atom은 문장이나 토큰이 아니라, 독립적으로 검증·수정 가능한 최소 의미 단위다. 하나의 발화에서 여러 Atom을 만들며, Atom 수보다 의미 회복 가능성을 우선한다.

초기 Atom class 후보:

```text
IDENTITY_CLAIM, ORGANIZATION_CLAIM, ROLE_CLAIM, STATE_CLAIM,
EVENT_CLAIM, ACTION_REQUEST, ACTION_INSTRUCTION, PROHIBITION,
QUESTION, WARNING, THREAT, PROMISE, JUSTIFICATION, CONDITION,
OBSERVED_ACTION, REPORTED_ACTION, CUSTOMER_RESPONSE,
DISCLOSURE_REQUEST, SECRECY_REQUEST, COMMUNICATION_CONTROL,
FINANCIAL_ACTION
```

모든 Atom은 최소한 다음 슬롯을 명시한다.

```text
speaker, subject, predicate, actor, target, object, destination,
action_state, modality, polarity, claim_status, source_provenance
```

예를 들어 “고객의 계좌가 범죄에 사용됐다”와 “안전계좌로 보내라”는 하나의 위험 신호가 아니라 각각 다음처럼 분리한다.

```text
A1: speaker=CALLER, subject=CUSTOMER_ACCOUNT,
    predicate=USED_IN, object=CRIME,
    atom_class=STATE_CLAIM, claim_status=CALLER_CLAIM

A2: speaker=CALLER, actor=CUSTOMER,
    predicate=TRANSFER_FUNDS, destination=CLAIMED_SAFE_ACCOUNT,
    atom_class=ACTION_INSTRUCTION, action_state=INSTRUCTED
```

## 6. L2 표현·화행·화용론 계층

동일한 행동 코드라도 표현 방식이 다르면 위험도가 달라질 수 있으므로 표현 특성을 별도 보존한다.

```text
speech_act
directive_strength
obligation
urgency
authority_pressure
fear_pressure
secrecy_pressure
isolation_pressure
financial_pressure
repetition_pressure
politeness_register
source_assertion_strength
modality
polarity
```

`fear_expression`(고객이 두려움을 표현)과 `fear_induction`(상대가 두려움을 유발)은 분리한다. `REQUESTED`, `INSTRUCTED`, `COMPLETED`를 confidence 하나로 합치지 않는다.

### Controlled lexical cue

원문 substring을 저장하지 않고, 의미를 보존하는 통제 어휘 코드만 저장한다.

```text
"즉시" / "지금" / "바로" -> URGENCY.IMMEDIATE
"안전계좌"               -> TERM.CLAIMED_SAFE_ACCOUNT
"반드시"                 -> OBLIGATION.STRONG
"압류" / "정지"          -> THREAT.ASSET_FREEZE
```

표현 수준과 정규화 수준을 함께 저장한다. 예컨대 `즉시`, `지금`, `바로`는 lexical cue에서는 구분하되 semantic 값은 모두 `IMMEDIATE`로 매핑한다.

## 7. 주장·상태·불확실성

다음 세 축을 하나의 `confidence`로 합치지 않는다.

```json
{
  "extraction_confidence": 0.97,
  "source_assertion_strength": "HIGH",
  "verification_status": "UNVERIFIED"
}
```

핵심 구분:

```text
CALLER_CLAIM   != SYSTEM_FACT
REQUESTED      != COMPLETED
UNKNOWN        != FALSE
```

정보가 없으면 구체적인 값을 추정하지 않고 `UNKNOWN` 또는 `MISSING`으로 남긴다.

## 8. L3 관계·그룹·엔터티

### 관계

초기 관계 후보는 `JUSTIFIES`, `CAUSES`, `RESULTS_IN`, `REQUIRES`, `CONDITIONAL_ON`, `PRECEDES`, `CO_OCCURS_WITH`, `ELABORATES`, `REFERS_TO`, `CONTRADICTS`, `SUPPORTS`, `TARGETS`, `PART_OF`, `RESPONDS_TO`, `CORRECTS`다.

관계에는 `source_atom_id`, `target_atom_id`, `relation_type`, `confidence`, `provenance`를 붙인다. 근거 없는 인과관계는 생성하지 않는다.

### 그룹

그룹은 Atom 간 관계 자체와 다르다. 여러 Atom을 하나의 사건·에피소드로 묶는다.

```text
utterance_group, conversation_episode, action_group,
fraud_scenario_group, verification_group
```

### 엔터티와 coreference

“그 사람”, “그 계좌”, “거기로” 같은 표현을 내부 registry ID로 연결하되 민감한 literal은 저장하지 않는다.

```text
E1=CALLER, E2=CUSTOMER, E3=CUSTOMER_ACCOUNT,
E4=CLAIMED_SAFE_ACCOUNT, E5=PROSECUTION_SERVICE
```

외부 계좌·전화번호 등은 `type=EXTERNAL_ACCOUNT`, `identifier_status=MASKED_OR_NOT_STORED`처럼 표현한다.

## 9. 행위·요구·통제 온톨로지

### Action state

```text
MENTIONED, REQUESTED, INSTRUCTED, PLANNED, ATTEMPTED,
COMPLETED, FAILED, CANCELLED, DENIED, UNKNOWN
```

고객이 “보냈다”고 말한 것은 자동 거래 완료가 아니라 `CUSTOMER_REPORTED_COMPLETED`로 남기고, 공식 확인 전에는 `verification_status=UNVERIFIED`로 유지한다.

### 주요 action code

```text
TRANSFER_FUNDS, WITHDRAW_CASH, OPEN_ACCOUNT, TAKE_LOAN,
INSTALL_APP, OPEN_URL, SHARE_SCREEN, DISCLOSE_OTP,
DISCLOSE_PASSWORD, PROVIDE_CARD_INFO, MAINTAIN_CALL,
END_CALL, AVOID_REPORTING, KEEP_SECRET, CONTACT_THIRD_PARTY,
MOVE_LOCATION
```

### OTP·인증정보

OTP는 일반 개인정보가 아니라 별도 `AUTHENTICATION_SECRET`로 분류한다.

```text
OTP, SECURITY_CODE, PASSWORD, PIN, CARD_CVC, CERTIFICATE_SECRET
```

“OTP가 뭔가요?”는 `QUESTION`, “OTP 번호를 불러주세요”는 `DISCLOSURE_REQUEST + OTP`다.

### 커뮤니케이션 통제·고립

```text
NO_END_CALL, NO_EXTERNAL_CONTACT, NO_REPORTING,
NO_FAMILY_DISCLOSURE, NO_BANK_CONTACT, NO_SEARCH, KEEP_SECRET
```

관찰된 금지 발화와 그로부터 도출된 `ISOLATION_CONTROL` 신호를 별도 객체로 유지한다.

### 위협

```text
ARREST_THREAT, ASSET_FREEZE_THREAT, LEGAL_ACTION_THREAT,
FINANCIAL_LOSS_THREAT, ACCOUNT_SUSPENSION_THREAT,
FAMILY_HARM_THREAT, INVESTIGATION_ESCALATION_THREAT
```

`THREAT=true` 하나만 저장하지 말고 유형·대상·조건·강도·근거 Atom을 저장한다.

## 10. L4 Context Signal

Context Signal은 Atom과 관계를 근거로 도출된 위험 패턴이다. 모든 Signal은 lineage를 가진다.

```json
{
  "signal_id": "SIG-020",
  "parent_family": "IMPERSONATION",
  "concept_code": "CLAIMED_AUTHORITY",
  "pattern_code": "PROSECUTION_IMPERSONATION",
  "derived_from_atoms": ["A1", "A2"],
  "target": "CUSTOMER",
  "relation": "CALLER_CLAIMS_TO_BE",
  "status": "PROPOSED",
  "severity": "HIGH",
  "confidence": 0.94,
  "visibility": "BANK_INTERNAL",
  "schema_version": "semantic-context.v1"
}
```

예시처럼 `claimed_organization`, `claimed_role`, `claim_content`, `requested_actions`, `cue_codes` 등 세부 속성을 signal에 포함할 수 있지만, 각각의 근거 Atom ID를 잃지 않는다.

## 11. L5 Fact와 revision

Fact는 사건에 표시할 수 있는 검증 단위다.

```text
AI extraction -> PROPOSED
직원 확인     -> CONFIRMED
잘못된 정보   -> REJECTED
정정된 버전   -> 새 revision + 기존 SUPERSEDED
```

Fact를 overwrite하지 않고 `fact_revision`, `fact_support`를 통해 이전 값·근거·검증자·시각을 보존한다. 동일 semantic fingerprint는 idempotent 처리하고, 서로 다른 주장은 `CONFLICT`로 남긴다.

권장 fingerprint 구성:

```text
hash(message_id + normalized_subject + predicate + normalized_object
     + modality + polarity)
```

confidence, model version, timestamp, extractor run ID는 fingerprint에 포함하지 않는다.

## 12. L6 Grounded Reconstruction

통화 기반 Summary, 확인 질문, 업무 카드, 보고서, Context Panel 문장은 저장된 구조화 정보만으로 생성한다. 채팅·카드 답변을 포함하는 경우에는 저장된 원문과 구조화 결과 중 해당 visibility가 허용한 필드만 사용한다.

```text
Atoms / Relations / Facts
        -> Content Plan
        -> Grounded Generation
        -> Claim-level Support Mapping
        -> Reconstruction Validator
```

Content Plan은 문장별 허용 claim과 supporting ID를 먼저 확정한다.

```json
{
  "statement_id": "ST-001",
  "supporting_atoms": ["A1", "A2"],
  "allowed_claims": [
    "CALLER_CLAIMED_PROSECUTION_ROLE",
    "ACCOUNT_CRIME_INVOLVEMENT_CLAIM",
    "CALLER_REQUESTED_TRANSFER"
  ]
}
```

### Validator가 차단해야 하는 변질

```text
CLAIMED -> VERIFIED
REQUESTED/INSTRUCTED -> COMPLETED
UNKNOWN -> 구체값
PARTIAL -> ALL_FUNDS
조건부 -> 확정
NEGATIVE -> POSITIVE
일반 역할/기관 -> 특정 역할/기관
근거 없는 위협·인과·목적 추가
```

### High-Fidelity Grounded Statement

현재 A파트의 문장화 문제는 문장이 없는 것이 아니라, 서로 다른 세부 Fact가 하나의 넓은 문장으로 합쳐지며 specificity가 손실될 수 있다는 점이다. 따라서 기본 정책은 `하나의 Fact 또는 독립된 의미 단위 = 하나의 직원용 문장`으로 한다.

문장화 시 다음 슬롯을 가능한 한 보존한다.

```text
actor / subject, predicate, target, destination,
action_state, modality, polarity, claim_status, verification_status,
amount_scope, amount_value_krw,
claimed_organization, claimed_role, claimed_purpose,
threat_type, communication_control, auth_secret_type,
urgency, obligation
```

서로 다른 predicate, action state, target, destination, polarity, modality, claim/verification status, 통제 유형, 위협 유형, 인증정보 유형, 금액은 저장된 Relation으로 연결할 근거가 없는 한 하나의 상위 표현으로 합치지 않는다. 예를 들어 `NO_FAMILY_DISCLOSURE`, `NO_BANK_CONTACT`, `NO_REPORTING`은 각각 “가족에게 알리지 말라고 요구한 정황입니다”, “은행에 연락하지 말라고 요구한 정황입니다”, “신고하지 말라고 요구한 정황입니다”처럼 별도 문장으로 투영한다.

문장화 내부 계약은 별도 DB schema가 아니라 다음과 같은 `Statement Plan` 개념으로 관리한다.

```json
{
  "statement_id": "ST-001",
  "fact_id": "FACT-001",
  "supporting_atom_ids": ["ATM-0005-LLM-0001"],
  "supporting_relation_ids": [],
  "semantic_key": "REQUESTED_ACTION",
  "actor": "CALLER",
  "predicate": "TRANSFER_FUNDS",
  "action_state": "REQUESTED",
  "polarity": "POSITIVE",
  "modality": "DIRECTIVE",
  "claim_status": "CALLER_CLAIM",
  "verification_status": "UNVERIFIED",
  "observed_lexical_codes": ["URGENCY.DANGJANG"],
  "allowed_observed_terms": ["당장"],
  "allowed_claims": ["CALLER_REQUESTED_TRANSFER"]
}
```

`observed_terms`는 원문 복원을 위한 데이터가 아니라 privacy-safe lexical evidence다. 실제 source에 존재하고 allowlist를 통과한 짧은 surface form만 사용할 수 있다. 전체 문장·긴 phrase·evidence span·토큰 dump·전화번호·계좌번호·OTP/비밀번호/PIN/CVC 값은 문장화 입력과 저장 결과에 포함하지 않는다. normalized code만 있을 때는 surface term을 새로 만들지 않는다.

### Action state·극성·확인 상태 문장 계약

```text
REQUESTED                     -> 요구했다 / 요청했다
INSTRUCTED                    -> 지시했다 / 하라고 했다
PLANNED                      -> 하려는 정황 / 계획
ATTEMPTED                    -> 시도했다
CUSTOMER_REPORTED_COMPLETED  -> 고객이 실제 수행했다고 진술했다
VERIFIED / CONFIRMED         -> 확인 정책을 통과한 경우에만 완료됐다
UNKNOWN                      -> 확인되지 않았다
DENIED / NEGATIVE            -> 하지 않았다고 진술했다
```

`REQUESTED → COMPLETED`, `CUSTOMER_REPORTED_COMPLETED → VERIFIED`, `UNKNOWN → TRUE/FALSE`, `NEGATIVE → POSITIVE` 변환은 금지한다.

### 세분화 문장 예시

| 저장된 의미 | 나쁜 투영 | High-Fidelity 투영 |
| --- | --- | --- |
| `TRANSFER_FUNDS`, `REQUESTED`, `5,000,000원` | 자금 이동 정황이 있습니다. | 상대방이 500만원 송금을 요구한 정황입니다. |
| `TRANSFER_FUNDS`, 고객 진술 완료, `3,000,000원` | 300만원 송금이 완료되었습니다. | 고객이 300만원을 송금했다고 진술했습니다. |
| `DISCLOSURE_REQUEST`, `auth_secret_type=OTP` | 인증정보 노출 정황입니다. | 상대방이 OTP 제공을 요구한 정황입니다. |
| `NO_FAMILY_DISCLOSURE` | 외부 연락이나 주변 상의를 제한한 정황입니다. | 상대방이 가족에게 알리지 말라고 요구한 정황입니다. |
| `observed_terms=당장`, `IMMEDIATE` | 긴급 처리를 재촉했습니다. | 상대방이 ‘당장’ 처리하라고 요구하며 즉시 행동을 재촉한 정황입니다. |
| `UNKNOWN`, `auth_secret_type=OTP` | 고객이 OTP를 제공했습니다. | OTP 제공 여부는 아직 확인되지 않았습니다. |

### 집계·중복 제거·관계 규칙

동일 actor·predicate·action state·target/destination·polarity/modality·verification status인 표현 차이만 하나로 합칠 수 있다. 서로 다른 송금 요구와 실제 송금, OTP 요구와 OTP 제공, 가족·은행·신고 연락 통제, 서로 다른 금액·기관·목적, `REQUESTED`와 `INSTRUCTED`, `UNKNOWN`과 `CONFIRMED`는 별도 Fact/문장으로 유지한다. 다중 Fact는 문장 수를 줄이기보다 UI row 또는 statement를 여러 개 생성하는 것을 우선한다.

Relation은 문장 장식이 아니라 연결 허가다. `JUSTIFIES(A1, A2)` 같은 Relation이 있을 때만 “계좌 연루를 주장하며 안전계좌 송금을 요구했다”처럼 연결할 수 있으며, Relation이 없으면 각 Fact를 별도 문장으로 표시한다. Context Signal의 상위 label만으로 구체적인 행동·대상·관계를 새로 만들어내지 않는다.

Context Signal은 복수 Atom을 조합한 내부 위험 신호이고, Context Fact는 직원이 검토·수정·확정할 사건 단위 정보다. Grounded Statement는 Fact 또는 명시적으로 허용된 Atom/Relation 조합의 직원용 projection이다. A파트는 피해·노출, 사칭·접촉 정보, 사기 정황, 사실·확인 현황의 Fact-preserving projection을 담당하며, 사건 전체 요약·Bank Brief·최종 보고서는 C파트 책임이다.

현재 중앙 `analysis-result created`는 저장된 의미 피처와 Atom 보완 결과를 직원용 문장으로 표시하고, 우측 Context Panel은 핵심 Fact를 동일한 grounded 문장 layer와 supporting lineage로 표시한다. 중앙 카드가 더 넓은 진단 피처를 보여주는 반면 패널은 수정·확정 가능한 Fact만 표시하므로, 전체 semantic key를 패널에 반영하는 L5 확장은 별도 작업으로 남아 있다.

## 13. 채널별 원문·개인정보 보관 규칙

원문 보관 여부는 내용이 아니라 출처 채널과 데이터 주체의 동의·내부 정책으로 결정한다.

### 통화·외부 STT 원문 (기본 비보관)

다음은 분석 시점에만 사용하고 영구 저장하지 않는다.

- raw/full transcript, raw_text
- 원문 evidence span, verbatim sentence, 복원 가능한 substring
- 이름·전화번호·계좌번호·OTP·비밀번호 등 민감 literal

대신 message/turn ID, 순서, source fingerprint, semantic code, 구조화 속성, 관계, masked entity reference, controlled lexical cue, 추출·모델 버전만 저장한다.

### 은행직원·고객 채팅 및 카드 답변 (원문 보관 가능)

서비스 안에서 은행직원 또는 고객이 직접 입력한 다음 데이터는 법무·개인정보 정책과 보존 기간이 허용하는 경우 원문을 저장할 수 있다.

- 채팅 메시지 본문
- 질문 카드에 대한 선택지 답변
- 질문 카드에 대한 직접 입력 답변
- 직원이 작성한 Fact 정정·확인 메모
- 업무 카드 결과와 고객 공유 답변

원문을 저장하더라도 다음 메타데이터를 반드시 함께 기록한다.

```text
source_channel = STAFF_CHAT | CUSTOMER_CHAT | QUESTION_CARD | ACTION_CARD
speaker / actor_type
message_id / turn_id / conversation_sequence
created_at / edited_at
visibility = CUSTOMER_VISIBLE | BANK_INTERNAL
revision / edited_by / audit_event_id
```

채팅 원문은 고객 화면과 은행 화면의 visibility를 넘겨 표시하지 않는다. 수정·삭제·보존기간 만료 정책과 감사 이력도 별도로 적용한다. 카드 답변 원문을 보관하더라도 AI가 이를 자동으로 `CONFIRMED` Fact로 승격하지 않으며, 구조화·검증 상태는 기존 Fact lifecycle을 따른다.

### 테스트·로그 규칙

통화 fixture에는 민감 문자열을 넣고 persistence와 로그에 남지 않는지 검사한다. 채팅·카드 fixture에는 원문 보관 허용 케이스와 visibility·revision을 검사한다. 모든 채널에서 `UNKNOWN`/`MISSING`을 사용해 정보 손실과 추정을 구분한다.

## 14. 권장 논리 데이터 모델

구현 시 다음 리소스를 검토한다(이번 단계에서는 migration하지 않는다).

```text
context_source
context_entity
semantic_atom
atom_expression_feature
semantic_relation
semantic_group
atom_group_membership
context_signal
signal_atom_support
context_fact
fact_revision
fact_support
reconstruction_record
reconstruction_support
```

기존 `facts`, `evidence`, `history`, `message_context_extractions`와의 매핑은 별도 adapter/마이그레이션 설계에서 확정한다.

## 15. 추출 단계와 구현 순서

```text
Pass 1  Semantic Atom extraction
Pass 2  Relation + domain signal derivation
Pass 3  Structural validation
Pass 4  PROPOSED Fact proposal
Pass 5  Grounded reconstruction (필요 시)
Pass 6  Reconstruction validation
```

권장 Phase:

- Phase A: 기존 Event/Context/ML/Case/Fact/Panel baseline fixture 고정
- Phase B: 기존 결과에 `semantic_atoms` 병행 출력
- Phase C: multi-atom·최소쌍·cross-turn decomposition 테스트
- Phase D: lexical/speech-act/pragmatics 계층 추가
- Phase E: relation·group·entity/coreference 추가
- Phase F: Atom 기반 Context Signal adapter
- Phase G: Fact lineage와 revision/conflict 연결
- Phase H: 구조화 정보만 이용한 reconstruction
- Phase I: claim-level validator와 distortion 차단
- Phase J: Panel visibility·semantic key mapping 검증

각 Phase는 이전 단계의 contract/fixture가 통과한 뒤 진행한다. ML feature vector와 기존 UI를 먼저 바꾸지 않는다.

현재 구현 위치:

- Phase B~F: Semantic Atom·Relation·Signal·Episode·Action Group·Entity Registry 생성 및 저장 연결 완료
- Phase G: 핵심 Atom·피처 → Fact projection과 Atom/Signal lineage 연결 완료, 전체 projection·revision/supersede/conflict는 미완료
- Phase H~I: 중앙 카드 전체 의미 피처의 직원용 표시와 Fact 단위 grounded 문장 plan 적용, supporting Atom 기반 세분화 문장 1차 적용, 전체 slot·요약·질문 grounded 검증은 미완료
- Phase J: 기존 7개 패널 섹션에 핵심 Fact 문장을 표시 중, 전체 의미 피처 매핑과 E2E 동일 revision 검증은 미완료

## 16. 평가 지표와 acceptance 기준

```text
Semantic Coverage
Specificity Preservation
Statement Specificity Preservation
Semantic Slot Preservation
Aggregation Loss Rate
Semantic Broadening Rate
Relation Preservation
Modality Preservation
Action-State Preservation
Polarity Preservation
Unknown Preservation
Lexical Cue Preservation
Observed-Term Preservation
Relation Faithfulness
Unsupported Lexicalization Rate
Unsupported Claim Rate (목표 0)
Contradiction Rate
```

필수 테스트 목록:

1. 한 문장 다중 Atom 분해
2. 여러 turn의 주장 누적·정정·충돌
3. OTP 질문과 OTP 공개 요구 구분
4. 기관·역할 specificity 보존
5. Requested/Instructed/Completed 구분
6. 부정·조건·긴급성·협박 보존
7. secrecy와 isolation 구분
8. UNKNOWN 보존
9. entity/coreference mapping
10. retry/idempotency·fingerprint 안정성
11. revision/supersede/conflict chain
12. 통화 raw-text·민감 literal 비보관
13. signal/fact lineage
14. grounded reconstruction과 unsupported claim rejection
15. Customer/BANK_INTERNAL visibility 차단
16. 기존 ML 이름·순서·shape·artifact·window·threshold 불변 확인

현재 1차 구현은 Fact가 명시적으로 참조하는 supporting Atom의 `auth_secret_type`, `destination`, `communication_control`, `urgency`, `action_state`, `observed_terms`를 문장화에 사용한다. OTP 요구·제공 진술·미확인, 안전계좌, 허용된 긴급성 lexical cue, 가족·은행·신고 연락 통제를 서로 다른 직원용 문장으로 투영한다. 전체 semantic slot 보존과 broad abstraction validator는 후속 구현 대상이다.

`Aggregation Loss Rate`는 서로 다른 Fact를 합치면서 개별 의미가 사라진 비율, `Semantic Broadening Rate`는 저장된 의미보다 넓은 표현으로 바뀐 비율, `Unsupported Lexicalization Rate`는 `observed_terms`에 없는 구체 표현을 새로 만든 비율이다. 세분화 문장화의 목표는 이 손실과 임의 확장을 0에 가깝게 유지하면서 semantic slot 보존율을 최대화하는 것이다.

## 17. Visibility와 Projection

Context Panel은 Atom dump가 아니라 Fact projection layer다. Atom·Relation이 생성되었다는 사실만으로 패널에 자동 표시하지 않으며, 직원이 확인·수정할 수 있는 Fact로 변환된 항목만 표시한다.

- `CUSTOMER_VISIBLE`: 고객에게 필요한 안전 안내와 확인된 진행 상태만 표시
- `BANK_INTERNAL`: 사칭 기관·역할, 위험 패턴, 압박 강도, 직원용 근거 문장과 확인 상태 표시
- 은행 직원 일반 화면에서는 `Atom`, `Relation`, `Context Signal`, raw predicate, feature code, 내부 ID와 모델 confidence를 표시하지 않는다.
- 개발자·감사 화면에서는 원본 구조화 결과와 lineage를 별도 조회·export할 수 있어야 한다.
- `BANK_INTERNAL` 정보가 고객 채널·고객용 AI 응답으로 유출되지 않도록 projection 단계에서 차단

권장 semantic key registry:

```text
CLAIMED_ORGANIZATION, CLAIMED_ROLE, CLAIMED_REASON, CLAIMED_EVENT,
REQUESTED_ACTION, INSTRUCTED_ACTION, REPORTED_ACTION, VERIFIED_ACTION,
THREAT_TYPE, URGENCY, OBLIGATION, COMMUNICATION_CONTROL,
SECRECY_REQUEST, AUTH_SECRET_REQUEST, FINANCIAL_DESTINATION,
AMOUNT_SCOPE, CLAIMED_PURPOSE, VERIFICATION_STATUS
```

## 18. 이번 문서의 결정과 보류 사항

확정:

- 통화·외부 STT 원문은 분석 시점에만 사용하고 장기 저장하지 않는다.
- 은행직원·고객 채팅과 카드 답변은 정책상 허용되는 경우 원문과 구조화 결과를 함께 저장한다.
- Atom → Signal → Fact → Reconstruction의 lineage를 보존한다.
- Observed/Derived/Confirmed/Reconstructed를 명시적으로 분리한다.
- 주장·행동 상태·검증 상태·confidence를 분리한다.
- AI Fact는 `PROPOSED`로 시작하고 General API가 검증·저장한다.
- ML feature/artifact/threshold 경계는 유지한다.
- 중앙 생성 결과 카드의 일반 직원 화면은 개발자용 코드 대신 의미 피처를 문장형으로 표시한다.
- 중앙 카드에서는 추출된 의미 피처를 가능한 한 모두 표시하고, 우측 패널에서는 동일 정보를 Fact 단위로 표시한다.
- 다중 요구 금액은 개별 값과 합계를 함께 보존·표시한다.

구현 전 추가 확인 필요:

- semantic key registry의 최종 enum 목록
- 기존 V2 Fact/evidence 테이블과 새 lineage의 구체 매핑
- 통화 원문 fingerprint 및 채팅 원문 보존 정책의 법무·개인정보 검토
- LLM 출력 schema와 모델별 JSON 강제 방식
- reconstruction validator의 차단 수준과 재시도 정책
- 고객/직원별 projection 허용 필드 및 감사 로그 보존 기간

## 19. 검증 명령과 산출물

현재 산출물은 이 Markdown 문서, `DiagnosisResult`의 privacy-safe 구조화 결과, 전용 DB 리소스, 핵심 Fact projection·grounded 문장 layer, 중앙 직원용 결과 카드다. DB migration과 Frontend는 이전 구현 단계에서 이미 변경된 상태이며, 이번 High-Fidelity 문서 업데이트에서는 추가 변경하지 않는다. ML artifact·benchmark 경계는 유지한다.

구현된 Phase B 범위:

- `backend/contracts/diagnosis.py`에 원문 없는 `SemanticAtom` 계약 추가
- `backend/ai_api/app/domains/diagnosis/semantic_atoms.py`에 기존 `ExtractedEvent` → Atom adapter 추가
- `DiagnosisResult.semantic_atoms`를 optional 병행 필드로 추가
- 진단 orchestration이 기존 결과와 함께 deterministic Atom을 반환
- Atom에는 evidence text/민감 literal을 복사하지 않고 turn·event lineage와 semantic fingerprint만 포함
- 기존 turn별 Event LLM 응답에 `semantic_atoms` 배열을 병행하도록 schema와 추출 지침 확장
- 실제 OpenAI 응답에서 사칭 기관·직책·통화 종료 금지·가족 알림 금지·전액 송금을 독립 Atom으로 분해하는 것을 확인
- LLM 응답 변동으로 핵심 Atom이 누락될 때 기존 Event가 확인한 신호만 privacy-safe Atom으로 보완하도록 병합
- 사칭 기관·직책·정확한 원화 금액 전용 필드를 계약에 추가하고 lexical cue는 허용 코드로 제한
- Relation/Context Signal은 원문 없이 Atom ID만 연결하는 결정적 builder로 시작하며 교차 턴 hallucination을 차단
- 사칭 기관·직책·송금·통신 통제가 같은 턴에 함께 존재할 때만 복합 Context Signal을 생성
- Episode는 동일 turn 원자 묶음으로, Action Group은 동일 predicate 묶음으로 시작한다. Entity registry는 명시적 entity code만 색인하며 자유문자 coreference를 추정하지 않는다.
- `JUSTIFIES`는 명시적 위협이 행동과 같은 턴에 있을 때, `REQUIRES`는 공개 요구와 인증정보 Atom이 함께 있을 때, `CAUSES`는 긴급성·통신통제와 행동이 함께 있을 때만 생성한다.
- 핵심 Atom·독립 맥락 피처는 `main.py`의 결정적 후보 생성으로 Context Fact에 투영하고, 동일 의미의 중복 Fact는 패널 projection에서 하나의 직원용 정황으로 합친다.
- `context_v3/grounded.py`의 Fact 문장 plan은 직원용 문장, 상태 라벨, supporting reference, 허용 semantic key를 함께 유지하며 `PROPOSED` Fact의 확정·완료 승격을 검증한다.
- 현재 단계에서는 Atom/Relation/Signal/Episode 결과를 `DiagnosisResult`와 privacy-safe 전용 DB 리소스에 보존하고, 핵심 Fact를 `context_v3/grounded.py`로 직원용 문장화해 중앙 `analysis-result created` 카드와 우측 Context Panel에서 소비한다. 고객 projection에는 `BANK_INTERNAL` 구조화 결과를 포함하지 않는다. 전체 의미 피처의 Fact projection, Fact revision/supersede/conflict, 사건 요약·확인 질문 grounded 검증과 완전한 E2E 동일 revision 검증은 후속 단계 대상이다.

검증 결과:

- Python compileall: 통과
- 선택 Diagnosis/General API 회귀 테스트: 16개 통과
- 기존 ML feature 이름·순서·shape·artifact·threshold: 변경 없음
- 모델 bundle 내부 threshold는 0.95로 보존하고, runtime 환경변수 `WINDOW_RISK_THRESHOLD=0.60`으로 판정 기준만 조정
- DB migration 016/017 적용 및 초기 Fact/lineage 저장 확인
- 핵심 Fact projection·grounded 문장·중복 제거 및 `PROPOSED` 상태 승격 차단 테스트 추가
- Frontend TypeScript typecheck 및 Vite production build: 통과
- benchmark 입력·ML artifact·threshold: 변경 없음

```powershell
# UTF-8 및 Markdown 확인
Get-Content MVP_v3/docs/now_md/A_HIGH_FIDELITY_SEMANTIC_CONTEXT_DESIGN.md -Encoding UTF8

# 문서 외 변경이 없는지 확인

## 문서·폴더 운영 규칙

- `now_md` 기준 문서 작업에서 `migrations/18` 폴더를 새로 만들지 않는다.
- 데이터베이스 migration이 필요한 경우에도 먼저 기존 migration 체계와 통합 담당자의 승인을 확인한다.
- 별도 migration 폴더가 필요하다고 판단되면 임의 생성하지 말고 작업을 중단한 뒤 사용자에게 확인한다.
git diff -- MVP_v3/backend MVP_v3/frontend replay_benchmark
git status --short
```

다음 구현 단계는 Phase A baseline fixture 고정이며, 해당 단계에서 처음으로 runtime read-only 검증을 시작한다.

## 20. Runtime threshold calibration

ML 학습 산출물과 feature vector는 변경하지 않고 판정 임계값만 운영 설정으로 분리한다.

```text
model bundle threshold: 0.95 (서명된 artifact 내부, 불변)
runtime threshold:      0.60 (MVP_v3/.env, 현재 적용값)
```

`WINDOW_RISK_THRESHOLD`가 없으면 bundle의 0.95를 fallback으로 사용한다. 값은 0 초과 1 이하의 확률이어야 하며, 잘못된 값은 서버 시작 후 첫 예측에서 명시적인 설정 오류로 거부한다. 응답의 `threshold_score`와 metadata에는 실제 runtime threshold를 기록해 KPI 비교 시 기준을 혼동하지 않도록 한다.

## 부록 A. LLM Context lexical/pragmatic 보강 결정 (2026-09-16)

현재 구현은 Semantic Atom에 기존 normalized `lexical_cues`와 별도로 `observed_terms`를 추가한다. `observed_terms`는 실제 transient source turn에서 allowlist로 선택한 짧은 핵심 표현만 저장하며, 각 항목은 `surface_form`, 선택적 `lemma`, `normalized_code`, `term_type`, `semantic_value`, `confidence`를 가진다. source 문장·긴 구문·일반 토큰 목록·전화번호·계좌번호·OTP 값은 persistence payload에 들어가지 않는다.

표현 계층은 Atom의 `speech_form_codes`와 `speech_act`, `directive_strength`, `obligation`, `urgency`를 함께 사용한다. `당장`과 `즉시`는 각각 `URGENCY.DANGJANG`, `URGENCY.JEUKSI`로 구분하면서 semantic value는 `IMMEDIATE`로 통합한다. `~하셔야 합니다`와 같은 문법은 raw span 대신 `DIRECTIVE.MUST_FORM` 같은 normalized code로 표현한다.

Case Context Feature observation은 Atom이 소유한 surface form을 복제하지 않고 `source_atom_ids`, `observed_lexical_codes`, `semantic_features`를 연결한다. 따라서 기존 Context code와 Atom의 세부 용어를 함께 조회할 수 있고, 기존 `lexical_cues`·DB JSON payload와도 하위 호환된다. 이 변경은 LLM Context branch 전용이며 frozen ML 입력과 Frontend를 변경하지 않는다. 기존 JSON 컬럼에 additive field만 저장하므로 별도 DB migration은 없다.

검증 기준은 실제 용어 보존, urgency lexical distinction, 안전계좌 의미 유지, OTP 유형 보존, 민감 literal·raw phrase·token dump 차단, hallucinated cue 차단, legacy normalized code 회귀, Context observation Atom lineage 연결이다. 현재 저장된 개발 문서는 `now_md`의 두 파일이며, 작업 프롬프트에 기재된 추가 문서 파일은 현재 working tree에서 확인되지 않았다.

## 21. 담당 범위와 Frontend 연결 원칙

이 파이프라인은 A파트의 담당 범위를 명확히 고정한다. Frontend는 기존 카드·패널 구조를 따르되, 데이터의 소유권과 생성 책임은 아래처럼 분리한다.

### A파트 — Context Signal Pipeline

- 통화·채팅 입력에서 사기 신호와 Fact 후보 추출
- Semantic Atom, Expression Feature, Relation, Context Signal 생성
- Fact/evidence/lineage/revision 구조 제공
- Context Panel의 `피해·노출`, `사칭·접촉 정보`, `사기 정황` 데이터 생성
- `사실·확인 현황`에 표시할 Fact 후보와 근거 제공
- 추출 결과를 frozen ML feature 입력 경계에 연결하고 runtime threshold 결과 제공

A파트의 결과는 AI가 직접 확정하지 않는다. AI가 생성한 Fact는 `PROPOSED`로 General API에 전달하고 직원 확인을 거쳐 `CONFIRMED`가 된다.

### B파트 — Customer Agent·Verification

- 고객에게 확인 질문 생성
- 질문 선택지, 다중 선택, 중복 방지, 답변 구조화
- 기관 확인 리스트와 확인 방법 추천(RAG 포함)
- 고객용·은행용 Copilot의 prompt, context, visibility
- A파트가 제공한 미확인 Fact와 질문 후보를 입력으로 사용

### C파트 — Action·Summary·Report

- 담당자 조치 기록과 대응 업무 추천(Work Card)
- 사건 요약과 은행 Brief
- 최종 종결 보고서
- 우측 패널의 `담당자 조치 및 결과`, `고객 공유 결과` 생성

### 통합 담당 — Orchestrator·공용 계약

- 전체 AI 호출 순서와 Case 반영 트랜잭션
- A/B/C 결과의 공용 DTO·상태·오류·idempotency 조정
- 복합 사건에서 호출할 AI와 순서를 결정하는 후속 Orchestrator

### 우측 패널 projection 소유권

```text
현재 사건 요약       -> C
피해·노출            -> A
사칭·접촉 정보       -> A
사기 정황            -> A
사실·확인 현황       -> A + B
담당자 조치 및 결과  -> C
고객 공유 결과       -> C 중심
```

Panel 구현 시 각 영역은 소유 파이프라인의 projection을 사용한다. A 영역을 C의 요약 문장으로 대체하지 않으며, B가 생성한 질문·확인 결과는 A의 Fact를 덮어쓰지 않고 별도 verification 상태와 근거로 연결한다. 중앙 카드와 우측 패널은 동일한 Case/Fact revision을 참조해 한쪽만 갱신되는 상태를 허용하지 않는다.
