# A파트 6.5단계 테스트·품질 평가·파이프라인 설계

작성일: 2026-09-16  
기준: 최신 `v3.1-ham` 작업 트리

## 1. 목적과 경계

6.5단계는 A파트 Context Pipeline을 은행 직원용 화면에 노출하기 위한 기능 단계가 아니다.
1~6단계가 만든 결과를 재현하고, 누락·오탐·의미 변형·저장 실패·패널 연결 실패를 측정하는 내부 품질 단계다.

운영 웹 UI/API에는 평가 원시 결과, 내부 점수, confusion matrix, 개발자용 code label을 노출하지 않는다.
필요한 직원용 결과는 6단계의 grounded 문장과 기존 Context Panel 계약을 통해서만 제공한다.

## 2. 평가 대상과 데이터 흐름

```text
입력 텍스트/STT(처리 중에만 사용)
  → Event 추출
  → Semantic Atom + Observed Term + Expression Feature
  → Semantic Relation / Context Signal / Episode
  → DiagnosisResult 저장
  → Atom/Signal 기반 Fact projection
  → Grounded Statement 문장화
  → 기존 Context Panel 섹션 반영
  → Case Room 생성 및 API/E2E 확인
```

각 단계는 `stage_input`, `stage_output`, `lineage`, `metrics`, `privacy_check`를 평가한다.
원문은 fixture 실행 중에만 사용하고, export JSON에는 원문·raw span·긴 phrase·민감 identifier를 포함하지 않는다.

## 3. 산출물 규격

모든 산출물은 `schema_version`, `generated_at`, `fixture_set`, `code_revision`, `privacy_status`를 갖는다.

### 3.1 구조 JSON

개발자 조회용 JSON에는 다음을 포함한다.

- Event 요약 식별자와 turn 범위
- Semantic Atom의 normalized semantic slots
- allowlist 기반 `observed_terms`의 surface/lemma/normalized code
- expression/pragmatic feature
- Relation·Signal과 source Atom ID
- Fact·Grounded Statement와 source Atom ID
- 상태·polarity·modality·claim status
- 누락·오탐·보존 위반 issue code

다음은 저장하지 않는다.

- 통화 원문, 전체 문장, evidence span, token dump
- 전화번호·계좌번호·주민번호·OTP 실제 값·PIN·비밀번호·CVC

### 3.2 도표 자료

- 단계별 건수 funnel: Event → Atom → Relation/Signal → Fact → Statement → Panel
- Atom slot coverage heatmap
- lexical cue 보존율과 unsupported lexicalization 비율
- audit confusion matrix
- targeted re-extraction 전후 회복률
- panel section별 projection coverage
- 처리 시간·실패율·재시도율

## 4. 지표 정의

### 추출 AI

`precision`, `recall`, `F1`은 annotation과 비교해 Atom class, predicate, critical slot, observed lexical code별로 산출한다.
특히 기관·역할·인증정보 종류·송금 대상·금액 범위·긴급성·압박·고립·action state를 critical slot으로 관리한다.

### 점검 AI

발동 조건은 다음 중 하나 이상이다.

- 필수 slot 누락 또는 혼합 Atom
- source에 없는 observed term
- 민감 literal 또는 raw phrase persistence 위험
- orphan Relation/Signal lineage
- 다중 금액·요구·주장 aggregation loss
- Atom/Fact/Statement 간 state·polarity·modality 불일치

점검 결과는 `PASS`, `NEEDS_REVIEW`, `REEXTRACTION_REQUIRED`로 분리한다.
오탐·미탐은 사람 annotation을 기준으로 confusion matrix를 만들고,
targeted re-extraction 후 실제 누락이 회복되었는지와 불필요한 변경이 발생했는지를 별도로 측정한다.

### 저장·문장화·패널

- `DB persistence success rate`: 결과 리소스가 transaction 단위로 모두 저장된 비율
- `idempotency duplicate rate`: 같은 fingerprint 재처리에서 중복 생성된 비율
- `semantic slot preservation`: Atom의 평가 대상 slot이 Fact·Statement에 보존된 비율
- `semantic fidelity`: annotation의 의미 상태와 grounded statement의 의미 상태 일치율
- `unsupported lexicalization rate`: Atom에 없는 구체 용어가 문장에 추가된 비율
- `panel projection coverage`: 직원용 Fact가 올바른 기존 섹션에 표시된 비율
- `case-room E2E success rate`: 입력부터 Case Room 및 패널 API 응답까지 성공한 비율

## 5. 성능·품질 판정 원칙

단일 총점으로 품질을 숨기지 않는다. 최소한 추출, 감사, 저장, 문장화, 패널 연동 지표를 분리해 기록한다.
critical slot 누락, 민감정보 유출, 상태 승격, 잘못된 Relation 생성은 평균 점수와 무관하게 실패로 판정한다.

사람이 확인할 항목은 annotation의 정답성, 오탐·미탐 분류, 직원용 문장의 자연스러움과 패널 배치다.
그 외 반복 가능한 검사는 자동 테스트와 JSON 리포트로 수행한다.

## 6. 파일 보관 규칙

실행 체크리스트·fixture 계약·JSON schema·도표 원본·평가 결과는
`A파트 테스트 및 파이프라인 구조 정리/`에 모은다.
결과 파일에는 날짜와 fixture/code revision을 포함하고, 원문이 들어간 디버그 파일은 보관하지 않는다.

## 7. v3.0 기준선 재사용

사용자가 제공한 `fixtures/official_gold/`의 3개 파일을 공식 Gold로 사용한다.
최종 판정 우선순위는 `FACT_CONTEXT_CANONICAL_HUMAN_GOLD_v1.json`,
v3.1 구조 평가에는 `FACT_CONTEXT_GOLD_v3_1_HIGH_FIDELITY.json`,
v3.0 비교에는 `FACT_CONTEXT_GOLD_v3_0_CORRECTED.json`이다.

`replay_benchmark/fact_context_cases.json`은 원문 source reference이며 Gold 정답지로 취급하지 않는다.
이전 partial gold 산출물은 제거했고, legacy 변환기는 기존 호환성 테스트 외의 새 평가에서 사용하지 않는다.
