# CSR A파트 — v3.0 vs v3.1 비교 기준표

상태: **평가 계약/현재 증거 통합본**  
목적: v3.1을 “피처를 더 많이 추출했는가”가 아니라, **핵심 사실의 정확한 보존·의미 보존·근거 추적·안전성·운영 비용**으로 v3.0과 비교하기 위한 기준을 고정한다.

## 1. 기준과 주의사항

| 항목 | 기준 |
|---|---|
| v3.0 source | official commit `071fb512ce42a570b0bcf585041eac6f31c2fb1c` |
| v3.1 current worktree | branch `v3.1-ham`, current HEAD는 실행 시점에 기록 |
| Dataset | `benchmark_v1.0`, 30 cases / 150 turns |
| Dataset shape | HIGH 10 / MIXED 10 / LOW 10, unique sequence 2개 |
| Canonical source of truth | `FACT_CONTEXT_CANONICAL_HUMAN_GOLD_v1.json` |
| v3.0 projection | `FACT_CONTEXT_GOLD_v3_0_CORRECTED.json` |
| v3.1 projection | `FACT_CONTEXT_GOLD_v3_1_HIGH_FIDELITY.json` |
| Historical v1 | audit/archive only; corrected Gold와 직접 delta 금지 |

`NOT RUN`, `N/A`, `BLOCKED`는 0점이 아니다. Gold·분모·출력 계약이 다른 지표는
`COMPARABLE`로 분류하지 않고 delta를 계산하지 않는다.

## 2. 한눈에 보는 현재 결과

| 영역 | 지표 | v3.0 현재 증거 | v3.1 A파트 현재 증거 | 비교 상태 |
|---|---|---:|---:|---|
| 피처 추출 | Context Feature Recall | Historical 41.45%; corrected projection comparable recall 14.0% | 30-case 정답 점수 미집계 | **재집계 필요** |
| 피처 추출 | Context Feature Precision | Historical 46.38%; corrected projection comparable precision 100.0% | 30-case 정답 점수 미집계 | **재집계 필요** |
| 피처 추출 | Context Feature F1 | Historical 약 45.0%; corrected projection F1 24.6% | 미집계 | **재집계 필요** |
| 재맥락화 | Critical Fact Recall | Historical 31.37% | 미집계 | **동일 canonical slot 필요** |
| 재맥락화 | Fact Precision | Historical 34.75% | 미집계 | **동일 canonical slot 필요** |
| 의미 보존 | Status / Polarity Accuracy | 미집계 | annotation 계약 추가됨 | **v3.1 신규 + v3.0 재평가 필요** |
| 의미 보존 | Relation Accuracy | v3.0 relation 구조 없음 | 샘플 relation 2개, VP-18 lineage sample 1.0 | **v3.1-only / sample** |
| 추적성 | Evidence Grounding / Fact Lineage | v3.0 evidence projection만 존재 | VP-18 Event→Atom coverage 1.0, Relation lineage 1.0 | **구조 비교 가능, full score 필요** |
| 패널 | Section Projection Accuracy | v3.0 panel contract 기준 존재 | A파트 projection 구현/회귀 증거, full annotation 미집계 | **재집계 필요** |
| 안전성 | Contradiction | Historical 7건 | hard gate 계약 추가, v3.1 full 결과 미집계 | **재평가 필요** |
| 안전성 | Hallucination | Historical 76건 | hard gate 계약 추가, full 결과 미집계 | **재평가 필요** |
| 안전성 | Critical Safety Error Rate | 미집계 | 계약 추가됨 | **신규 공통 metric** |
| 효율 | Token / Calls | 7기능 평균 total 9,654.67 / 12 calls | v3.1 측정 필요 | **동일 fixture 계측 필요** |
| 효율 | Token per Correct Critical Fact | 미계산 | 계약 추가됨 | **v3.1 신규 비교축** |
| 효율 | Latency P50/P95/MAX | 미측정 | 미측정 | **계측 필요** |
| 운영 | Pipeline Completion Rate | DB/E2E 미측정 | 구조 pipeline sample만 확인 | **DB/E2E 필요** |

### 해석상 핵심

현재 실제로 바로 비교 가능한 것은 **동일 canonical projection으로 재계산된 v3.0 지표**,
기존 Historical v1의 audit 값, 그리고 v3.1의 구조적 lineage/privacy 증거입니다.
v3.1의 구조 sample 수치를 30-case 품질 점수처럼 표시하면 안 됩니다.

## 3. 최종 발표용 6개 비교축

### 3.1 피처 추출

| 지표 | 정의 | v3.0 | v3.1 판정 기준 |
|---|---|---|---|
| Context Feature Recall | Gold canonical signal 중 보존된 비율 | corrected projection 14.0%* | 동일 canonical signal set의 TP/expected |
| Context Feature Precision | 출력 signal 중 Gold/source로 지지되는 비율 | corrected projection 100.0%* | unsupported signal 제외/분리 |
| Context Feature F1 | 위 P/R 조화평균 | 24.6%* | 동일 분모에서만 비교 |
| Category Macro F1 | case 또는 category별 F1의 동일 가중 평균 | 미집계 | HIGH/MIXED/LOW와 semantic category별 병기 |

`*` v3.0 corrected projection audit은 v3.0이 보존하는 5개 canonical 항목만 포함한다.

### 3.2 재맥락화

| 지표 | 정의 | 필수 안전 규칙 |
|---|---|---|
| Critical Fact Recall | critical canonical fact 보존 비율 | missing과 UNKNOWN을 구분 |
| Fact Precision | 출력 fact 중 Gold/source 근거가 있는 비율 | unsupported fact 별도 count |
| Semantic Similarity | 보조 지표 | contradiction이 있으면 고득점으로 상쇄하지 않음 |
| Critical slot coverage | critical slot별 보존 여부 | case pass/fail과 함께 기록 |

### 3.3 의미 보존

| 지표 | v3.0 비교 가능성 | v3.1 평가 |
|---|---|---|
| Status/Polarity Accuracy | v3.0 raw output에 매핑 가능한 subset만 | CLAIMED/REQUESTED/INSTRUCTED/COMPLETED/NEGATIVE/UNKNOWN |
| Relation Accuracy | 직접 비교 불가; v3.0은 relation 계약 없음 | JUSTIFIES / CONDITION_FOR / PRESSURE_SUPPORTS |
| Correction Resolution Accuracy | 기존 v3.0 경로 확인 필요 | 정정 전후 fact 상태와 revision 비교 |
| Unknown Preservation | canonical UNKNOWN/MISSING을 구체값으로 만들지 않는지 | `unknown_to_known_hallucination_count` 별도 |

### 3.4 안전성

| Hard gate | 권장 기준 |
|---|---:|
| Critical contradiction | 0건 |
| Critical hallucination | 0건 |
| Privacy leak | 0건 |
| Auth request → shared 혼동 | 0건 |
| Transfer requested/instructed → completed 혼동 | 0건 |
| UNKNOWN → 구체값 hallucination | 0건 |
| ML contract 변경 | 없음 |

하나라도 실패하면 `HARD_GATE = FAIL`이며 평균 점수로 상쇄하지 않는다.

### 3.5 추적·정정

| 지표 | 산식/판정 |
|---|---|
| Evidence Grounding Rate | valid source ref / extracted items |
| Fact Lineage Completeness | Fact가 Atom·source turn·status를 모두 추적하는 비율 |
| Relation Lineage Completeness | relation 양끝 Atom과 근거가 연결된 비율 |
| Correction Resolution Accuracy | 정정 fixture에서 이전 fact가 superseded/resolved되고 최신 상태가 맞는 비율 |
| Section Projection Accuracy | 올바른 panel section·visibility로 투영된 비율 |

### 3.6 효율

| 지표 | 산식/주의 |
|---|---|
| Input / Output / Total tokens | OpenAI usage metadata 실제값 |
| LLM call count | 한 사용자 action 전체의 모든 LLM call 합산 |
| Latency P50/P95/MAX | 동일 fixture·동일 provider 조건에서 측정 |
| Token per Correct Critical Fact | total tokens / correct critical facts; 분모 0이면 N/A |
| Pipeline Completion Rate | 시작 fixture 중 최종 Case/Context/Projection까지 완료한 비율 |

v3.0 token baseline: 7개 기능을 한 번씩 실행할 때 평균 **9,654.67 total tokens / 12 calls**.
기능별 평균은 기존 [TOKEN_USAGE_REPORT.md](../../../../../replay_benchmark/results/v3_0_token_usage_20260916/TOKEN_USAGE_REPORT.md)를 참조한다.

## 4. v3.0와 v3.1의 비교 가능성 분류

| 분류 | 항목 |
|---|---|
| COMPARABLE | canonical semantic recall/precision, critical fact recall, fact precision, status/polarity subset, contradiction/hallucination count, token/call/latency |
| REDEFINED | v3.0 feature recall을 v3.1 Atom/Signal recall로 대체할 때는 동일 canonical projection을 함께 제공 |
| V3_1_ONLY | Atom observed-term fidelity, relation accuracy, speech-act/urgency/modality, context-signal lineage, correction resolution |
| LEGACY_ONLY | Historical feature inventory, old embedding similarity/amount recall 정의 |
| NOT_APPLICABLE | Gold에 explicit amount/entity가 없는 항목의 exact amount/entity recall |
| NOT_RUN | full v3.1 30-case result, DB persistence, browser E2E, P50/P95 latency |

## 5. 현재 A파트 진행 상태

완료 또는 확인된 증거:

- 공식 Gold 3종이 `fixtures/official_gold/`에 존재
- v3.0 corrected projection audit artifact 생성
- v3.1 high-fidelity schema에 Atom·observed term·expression·relation·signal 정의 존재
- 샘플 기준 Event→Atom coverage, Relation lineage, Context Signal lineage 확인
- privacy scan sample `PASS`
- A파트 평가/파이프라인 회귀 테스트 묶음 존재

아직 발표 수치로 확정하면 안 되는 항목:

- v3.1 full 30-case canonical precision/recall/F1
- v3.1 critical safety gate 결과
- correction fixture 결과
- full section projection accuracy
- DB persistence / pipeline completion E2E
- latency P50/P95/MAX
- v3.1 token per correct critical fact

## 6. 권장 실행 순서

1. 동일 30-case input으로 v3.1 raw structured output을 고정한다.
2. canonical mapping과 high-fidelity mapping을 동시에 적용한다.
3. ALL_CASES_WEIGHTED와 UNIQUE_SEQUENCE_WEIGHTED를 모두 계산한다.
4. case/category macro F1을 별도로 계산한다.
5. correction·negation·requested/instructed/completed fixture를 별도 case pass/fail로 판정한다.
6. hard gate를 평균 점수보다 먼저 판정한다.
7. 동일 fixture 3회 실행해 평균·표준편차·repeat consistency를 기록한다.
8. token/call/latency와 `token_per_correct_critical_fact`를 마지막에 결합한다.

## 7. 결론

현재 단계에서 확정 가능한 결론은 다음과 같다.

> v3.1은 v3.0에 없던 Atom·Relation·Context Signal·lineage·correction 평가면을 제공한다.
> 그러나 구조가 추가된 것과 품질이 개선된 것은 동일하지 않으므로, full 30-case Gold 재평가와
> hard gate·비용 계측이 완료되기 전에는 “v3.1이 개선됐다”고 단정하지 않는다.

최종 발표에서는 **정확성 → 의미 보존 → 안전성 → 추적성/정정 → 효율** 순서로 표를 배치하고,
미측정 항목은 반드시 `N/A / NOT RUN / BLOCKED` 중 하나로 표시한다.
## 2026-09-17 Documentation reconciliation

The four A-part documents now share the same evidence-backed status. The comparison is intentionally asymmetric until v3.1 produces the same raw 30-case artifact as v3.0.

| Workstream | Status | Evidence / next action |
|---|---|---|
| v3.0 corrected-Gold audit | DONE | 14.0% recall, 100.0% precision, 24.6% F1 |
| v3.0 token baseline | DONE | 7 features x 3 runs; 9,654.67 total tokens and 12 calls average |
| v3.1 sample structural checks | DONE (SAMPLE) | Event/Atom/Relation/lineage sample only; not a full score |
| v3.1 full 30-case quality score | NOT RUN | Freeze raw output, then run both Gold mappings |
| Safety hard gates | NOT RUN | Contradiction, hallucination, privacy suite pending |
| DB / pipeline / browser E2E | BLOCKED / NOT RUN | Requires controlled live execution and artifacts |
| v3.1 efficiency comparison | NOT RUN | Repeat token, call, latency, and token-per-critical-fact runs |

See the synchronized checklists and report addendum in:
- `A_IMPLEMENTATION_CHECKLIST.md`
- `A_6_5_TEST_AND_PIPELINE_CHECKLIST.md`
- `A_6_5_FINAL_A_PART_COMPREHENSIVE_REPORT.md`

No pending item above should be represented as a completed v3.1 improvement in Notion.

### 6.5 dependency rule

The full 6.5 checklist does not have to be completed before every intermediate
measurement. The split is:

| Measurement | Can run before all 6.5 items? | Required for publishable v3.1 comparison |
|---|---|---|
| v3.0 baseline / token replay | Yes | Yes, already available |
| Schema and evaluator dry-run | Yes | No, diagnostic only |
| v3.1 atom precision/recall/F1 | After structured output exists | Yes |
| Status/polarity/correction/relation/lineage | After high-fidelity output and Gold mapping exist | Yes |
| Safety hard gates | After dedicated safety fixtures exist | Yes |
| DB/pipeline/browser E2E | After controlled live environment exists | Yes for FINAL report |

### Unified evaluator

The executable comparison entry point is `compare_v30_v31.py` in this folder.
It can be run now to validate the v3.0 artifacts and will keep v3.1 as
`NOT_RUN` until a structured 30-case result is supplied:

```powershell
python "MVP_v3/docs/now_md/A_part/A파트 테스트 및 파이프라인 구조 정리/compare_v30_v31.py"
python "MVP_v3/docs/now_md/A_part/A파트 테스트 및 파이프라인 구조 정리/compare_v30_v31.py" --v31-output path/to/v3_1_structured_output.json
```
