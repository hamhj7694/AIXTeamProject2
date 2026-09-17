# A파트 4~6단계 개발 진행 기록

작성일: 2026-09-16  
기준: 최신 `v3.1-ham` 작업 트리

## 이번 작업에서 반영한 내용

### 4단계: Fact 저장 경로

- Case 생성 후 진단 결과가 기존 Context V3 Fact seeding 경로로 전달된다.
- AI가 만든 Fact는 `PROPOSED` 상태로 시작하며 직원 검토만 `CONFIRMED`로 전환한다.
- revision, supersede, conflict, retry/idempotency 계약은 기존 구현과 테스트를 유지한다.
- Fact의 구조화 근거는 실제 `STRUCTURED_ATOM` ID를 참조한다.

### 5단계: 세부 Atom의 Fact 투영

새 파일 `backend/general_api/app/domains/cases/context_v3/atom_fact_projection.py`를 추가했다.

- 유효한 Semantic Atom 1개마다 검토 가능한 Fact 후보 1개를 만든다.
- 각 후보는 `atom_id`, predicate, action/claim 상태, 표현 특성, normalized observed lexical code를 보존한다.
- 여러 금액, 요구, 압박 정황은 서로 다른 Atom이면 별도 Fact로 유지한다.
- OTP 값, 계좌번호, 전화번호, 원문 문장과 같은 민감 literal/raw transcript는 저장하지 않는다.
- 기존 grouped candidate는 호환성을 위해 유지하고, 세부 후보를 additive하게 추가한다.

### 6단계: 직원용 문장화와 패널 표시

`panel.py`의 중복 기준을 `(section, grounded sentence, source_atom_id)`로 보강했다.

- 같은 Atom의 재시도 중복은 하나로 합친다.
- 서로 다른 Atom이 같은 문장 템플릿으로 렌더링되어도 각각 표시한다.
- 기존 Fact 상태, 근거, communication control 문장화 테스트를 유지한다.
- Frontend와 ML feature vector는 변경하지 않았다.

추가로 `grounded.py`에 Atom–Fact 정합성 검증을 추가했다.

- `REQUESTED`와 `INSTRUCTED`를 직원용 문장에서 구분한다.
- Atom의 `action_state`, `polarity`, `modality`, `claim_status`가 Fact와 다르면 투영을 거부한다.
- `NEGATIVE`·`CONDITIONAL` Atom에서 polarity가 누락되면 투영을 거부한다.
- 문장화 Plan에 semantic state와 표현 메타데이터를 남겨 후속 검증이 가능하다.
- UNKNOWN·CONDITIONAL 상태는 직원 문장에 확인 필요/조건부 안내를 덧붙인다.
- 근거 Atom과 다른 기관명·인증정보 종류를 문장에 삽입하는 broadening을 거부한다.
- 해당 상태와 broadening 회귀 테스트 5건을 추가했다.
- Atom의 역할·대상·행위·목적·금액 범위·위협 유형 등 추가 구조화 slot도 Fact value에 보존한다.

요약·확인 질문 경로에도 `case_support/grounding.py` 검증을 연결했다.

- Case Brief의 위험 근거는 Diagnosis Evidence의 `(turn, family, subtype, safe text)`와 일치해야 한다.
- 확인 질문은 현재 Brief의 미확인 항목만 대상으로 하며, 질문 유형에 허용된 이벤트 family만 근거로 참조한다.
- 관련 Case-support grounding 테스트 2건을 추가했다.
- `DENIED` 상태와 역할·대상·목적·금액범위·위협 등 Semantic slot 보존 테스트를 추가했다.

정량 품질 측정을 위해 `context_v3/quality_metrics.py`와 테스트를 추가했다.

- Semantic slot preservation rate
- Aggregation loss rate
- Semantic broadening rate
- Unsupported lexicalization rate

이 지표는 원문이나 surface phrase를 반환하지 않고 Atom ID·구조화 code·Fact lineage만 사용한다.

`find_slot_preservation_violations()`를 추가해 누락된 slot을 `atom_id:slot` 형식으로 식별한다.
또한 UNKNOWN·DENIED·NEGATIVE·CONDITIONAL 상태의 문장화와 정합성을 테스트로 고정했다.

## 검증 결과

```text
Atom Fact projection + Context V3 panel + vertical slice + Fact contract/endpoint tests
44 passed
```

추가 테스트:

- `backend/general_api/tests/test_atom_fact_projection.py`
- one-Fact-per-Atom
- multiple amount preservation
- Atom lineage preservation
- sensitive literal non-persistence

## 반영된 보완 및 남은 체크 항목

- [x] 우측 패널 헤더는 내부 revision 번호 대신 서버가 제공하는 Case `updated_at`을
  `YYYY. MM. DD. HH:MM 최종 반영` 형식으로 표시한다. projection 상태(`최신`, `갱신 중` 등)는 유지한다.

- `test_analyze_case.py`의 UTF-8 raw-call persistence fixture를 현재 정책에 맞게 정리했다.
  `input_text`와 전체 저장 JSON에 원문이 남지 않는 것, 허용 lexical cue는 보존되는 것,
  OTP 숫자 literal은 저장되지 않는 것을 검증한다.
- Stage 6 문장화 보완을 반영했다.
  `CUSTOMER_REPORTED_COMPLETED`를 `VERIFIED`로 승격하는 표현을 차단하고,
  `observed_terms`가 없을 때 OTP·기관명 같은 구체 surface를 임의 생성하지 않으며,
  명시된 supporting Atom/Fact를 Context Signal label보다 우선한다.
- 위 보완은 `test_grounded_semantic_validation.py`와
  `test_case_support_grounding.py`의 회귀 테스트로 고정했다.
- Relation이 없는 서로 다른 Fact를 `때문에`·`따라서`·`위해` 같은 인과·목적 표현으로
  결합하지 않도록 `validate_no_unlinked_fact_join`과 회귀 테스트를 추가했다.
- `모든 semantic slot이 문장화 전후 동일한지 검증`은 운영 직원용 화면 기능이 아니다.
  웹 UI/API에는 노출하지 않고, 내부 성능·회귀 테스트 및 JSON 품질 리포트 전용으로 유지한다.
- Stage 6의 전체 semantic slot preservation, Relation 부재 시 결합 금지 검증,
  revision/상충 처리, 실제 운영 데이터 backfill은 다음 작업으로 남아 있다.
- 실제 MySQL 데이터의 기존 Case를 backfill하려면 별도 migration/backfill 명령과 운영 승인 범위를 정해야 한다.

## 6.5단계 준비

1~6단계의 결과를 운영 웹에 추가 노출하지 않고 내부적으로 평가하기 위한 6.5단계를 정의했다.
추출 AI, 점검 AI, 최종 Feature/DB 저장, 의미 보존 문장화, Context Panel·Case Room E2E,
그리고 입력부터 Case Room 생성까지의 pipeline/lineage를 JSON·지표·도표로 관리한다.

- 설계: `A_6_5_TEST_AND_PIPELINE_DESIGN.md`
- 실행 체크리스트: `A파트 테스트 및 파이프라인 구조 정리/A_6_5_TEST_AND_PIPELINE_CHECKLIST.md`
- 결과 자료: `A파트 테스트 및 파이프라인 구조 정리/reports/`
- 6.5단계는 웹 UI/API 비노출이며, privacy-safe fixture와 자동·수동 평가 결과만 보관한다.
- `backend/scripts/export_context_quality_report.py`를 추가해 동일 실행에서
  개발자용 `developer-structure.json`과 한국어 보고서형 `human-review-report.md`를 생성한다.
  샘플은 `A파트 테스트 및 파이프라인 구조 정리/reports/sample-20260916/`에 생성했고,
  표·Mermaid 흐름도·구조 건수·점검 AI 상태를 함께 기록한다.
- `backend/scripts/evaluate_6_5_metrics.py`를 추가했다. 공식 Gold는 사용자가 제공한
  `fixtures/official_gold/` 3개 파일로 교체했으며, 정답 확정 후 Event·Atom·critical slot·Observed lexical code별
  Precision·Recall·F1을 산출한다.
- 구조 지표는 정답 annotation 없이도 산출하도록 보강했다. VP-18 샘플에서
  Event→Atom turn coverage `1.0`, Relation lineage rate `1.0`, Context Signal lineage rate `1.0`,
  privacy status `PASS`를 확인했고, 평가기 회귀 테스트 2건도 통과했다.
- `validate_6_5_artifact.py` privacy scan과 `compare_6_5_reports.py` 재현성 비교 도구를 추가했다.
  timestamp 숫자를 민감정보로 오탐하지 않도록 메타데이터 예외를 보완했고, VP-18 개발자 JSON scan은
  `PASS`로 확인했다. 두 도구의 회귀 테스트 2건도 통과했다.
- 6.5단계 회귀 묶음을 실행했다. General API 저장·패널·projection·평가 도구 21건,
  AI Atom·lexical·audit·safety 52건, transaction·transition·context display 25건이 통과했다.
  이 결과는 코드/계약 회귀 통과를 의미하며, 실제 정답 기반 정확도와 브라우저 E2E 완료를 의미하지 않는다.
- 이전에 생성했던 v3.1 partial gold seed와 검토용 정답 파일은 제거했다.
  현재는 `FACT_CONTEXT_GOLD_v3_0_CORRECTED.json`, `FACT_CONTEXT_GOLD_v3_1_HIGH_FIDELITY.json`,
  `FACT_CONTEXT_CANONICAL_HUMAN_GOLD_v1.json`만 공식 Gold로 취급한다.
- 6.5단계 마지막 산출물로 A파트 전체 종합 평가 보고서 템플릿을 추가했다.
  실제 annotation·정확도·오탐/미탐·DB·브라우저 E2E 결과가 채워지기 전에는 `DRAFT`로 유지하고,
  완료 조건 충족 후 한국어 공유용 `FINAL` 보고서로 갱신한다.
- 2026-09-17 AI API 실행 환경을 확인했다. `/readiness`는 `provider_configured: true`였지만,
  실제 1건 분석은 외부 provider 연결 `APIConnectionError`로 실패해 v3.1 live 결과는 생성되지 않았다.
  따라서 이번 실행을 정확도 점수로 기록하지 않고 provider 연결 대기로 남긴다.
- 사람이 확인할 수 있도록 `fixtures/human_review/`에 검토 안내, `review_queue.json`,
  대표 Case `FACT-01~03` 메모 파일을 정리했다. 원문은 복제하지 않고 benchmark 원본의 Case/turn 위치만 연결한다.
- v3.0 `core_metrics.json`과 v3.1 VP-18 구조 리포트를 결합하는
  `build_6_5_baseline_comparison.py`를 추가했다. 비교 불가능한 v3.1 정확도는
  `PENDING_HUMAN_ANNOTATION`으로 유지하고, baseline과 현재 구조 건수만 자동 보고한다.
- v3.0 benchmark 무결성 검증 결과는 Case 30건·atomic fact 270건이며,
  privacy-safe 분포 요약 JSON·한국어 보고서를 `reports/v3_0-benchmark-summary/`에 생성했다.

## 다음 순서

1. UTF-8 기반 raw persistence fixture 정리 및 전체 General API 회귀 테스트
2. 기존 DB Case에 대한 선택적 Atom→Fact backfill 설계
3. UNKNOWN/NEGATIVE/CONDITIONAL과 semantic slot preservation validator 보강
4. 실제 API 응답으로 `analysis-result created`와 bank panel의 E2E 확인
