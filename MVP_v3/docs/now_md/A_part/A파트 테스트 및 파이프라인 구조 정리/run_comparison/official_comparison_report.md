# Official A-part v3.0 vs v3.1 comparison readiness

> **주의:** 이 문서는 현재 증거와 비교 준비 상태를 정리한 문서입니다. v3.0과 v3.1의 직접적인 개선율은 동일 조건 replay가 완료되기 전까지 계산하지 않습니다.

## Status

- Reference: `PASS` (30 cases)
- v3.0 evidence: `READY`
- v3.1 replay: `FULL_RAW_ARTIFACT_AVAILABLE`
- Hard gates: `PENDING_SEMANTIC_SCORING`
- Latency comparison: `NOT_RUN`

## v3.0 corrected-Gold baseline

| Metric | Result |
|---|---:|
| Cases | 30 |
| Comparable expected facts | 100 |
| True positives | 14 |
| False positives | 0 |
| False negatives | 86 |
| Comparable precision | 1.0 |
| Comparable recall | 0.14 |
| Comparable F1 | 0.24561403508771928 |
| Dataset turns | 150 |
| Unique turn sequences | 2 |

Non-comparable v3.0 keys: `call_control, isolation_bank_staff, isolation_family`.

### v3.0 feature-level live token baseline (기능별 토큰 기준)

| Feature (기능) | Avg total tokens (평균 총 토큰) | Avg calls (평균 호출) |
|---|---:|---:|
| case_creation_diagnosis | 3526.33 | 6.0 |
| bank_staff_chat_ai | 725.33 | 1.0 |
| customer_confirmation_question_ai | 869.0 | 1.0 |
| verification_ai | 877.33 | 1.0 |
| action_work_ai | 892.33 | 1.0 |
| customer_chat_ai | 1949.33 | 1.0 |
| final_report_ai | 815.0 | 1.0 |

## v3.1 live Raw Replay

| Metric | Result |
|---|---:|
| Cases | 30 / 30 successful |
| LLM calls | 210 |
| Input tokens | 416,078 |
| Output tokens | 61,215 |
| Total tokens | 477,293 |
| Avg tokens / case (케이스당 평균 토큰) | 15,909.77 |
| Avg calls / case (케이스당 평균 호출) | 7.00 |
| Latency P50 | 26,163.71 ms |
| Latency P95 | 34,062.66 ms |
| Latency MAX | 35,782.24 ms |
| Raw provider responses | 210 |

## Required semantic scorecard (비교 점수표)

| Metric | 한국어 의미 | v3.0 | v3.1 | 현재 상태 |
|---|---|---|---|---|
| Context Feature Precision / Recall / F1 | 문맥 피처 정확도·재현율·F1 | Gold audit 일부 | Raw output 있음 | Gold projection 필요 |
| Critical Fact Recall / Fact Precision | 핵심 사실 보존 재현율·정밀도 | Comparable audit 일부 | 미산출 | evaluator 필요 |
| Status / Polarity Accuracy | 상태·극성(요청/지시/완료, 긍정/부정) 보존 | 미산출 | 미산출 | 정답 projection 필요 |
| Relation Accuracy | 사⻊ 간 관계(원인·대상·순서) 정확도 | 미산출 | 미산출 | relation Gold 필요 |
| Evidence Grounding / Fact Lineage Completeness | 원문 근거 연결·사실 계보 완전성 | 미산출 | Raw evidence 구조 있음 | lineage evaluator 필요 |
| Correction Resolution Accuracy | 정정·부정 정보가 최종 결과에 반영되는 정확도 | 미산출 | 미산출 | correction fixture 필요 |
| Section Projection Accuracy | 결과 섹션에 올바른 사실이 배치되는지 | 미산출 | 미산출 | projection Gold 필요 |
| Critical Contradiction / Hallucination / Privacy Leak | 치명적 모순·환각·개인정보 유출 건수 | 미측정 | 미측정 | Hard Gate evaluator 필요 |
| Token / Calls / Latency | 비용·호출 수·응답시간 효율 | 일부 측정 | 측정 완료 | v3.0 동일 형식 필요 |

## Apples-to-apples comparison contract (동일 조건 비교 계약)

현재 v3.0 기능별 token baseline과 v3.1 30-case Diagnosis replay는 실행 단위가 달라 직접 비교하지 않는다.

| 비교축 | 동일하게 맞춰야 할 조건 | 현재 상태 |
|---|---|---|
| Case-level tokens/calls/latency (케이스 단위 비용·호출·지연) | 동일 30 cases·동일 turn text·동일 model·동일 provider·동일 환경·동일 반복 횟수 | v3.1 완료 / v3.0 동일 replay 필요 |
| Feature-level tokens/calls (기능별 비용·호출) | 동일 입력을 case_creation_diagnosis, bank_staff_chat_ai 등 같은 7개 기능에 각각 실행 | v3.0 기준만 있음 / v3.1 기능별 실행 필요 |
| Semantic scores (의미 점수) | 동일 canonical Gold와 동일 projection schema | v3.0 일부 / v3.1 Gold projection 필요 |
| Safety gates (안전 게이트) | 동일 critical case와 동일 0-tolerance 규칙 | 양쪽 모두 evaluator 필요 |

## Comparison coverage

| Area | v3.0 | v3.1 | Status |
|---|---|---|---|
| Corrected-Gold comparable facts | Measured | Raw output available | v3.1 scoring pending |
| Semantic/context projection | Partial corrected-Gold audit | Structured output captured | Projection Gold required |
| Safety hard gates | Not reconstructed by this audit | Not yet scored | Pending evaluator |
| Tokens/calls/latency | Existing v3.0 token artifact | Measured in this replay | Comparable cost table pending |

## What can and cannot be compared now

| Category | Current interpretation |
|---|---|
| v3.0 corrected-Gold scores | v3.0 baseline only; not yet a v3.1 comparison result |
| v3.1 Raw Replay | v3.1 evidence and operational-cost result only |
| v3.0 feature token baseline vs v3.1 case replay | **Not directly comparable** because execution units differ |
| Final improvement/regression claim | Blocked until same-case and same-feature replays are complete |

## Interpretation

The v3.1 artifact contains actual provider responses and per-call usage. It is valid evidence for v3.1 execution, but it must not be presented as a direct improvement over v3.0 yet. Final semantic, safety, and cost deltas require identical inputs, feature boundaries, model/provider/environment, repetition count, and the same Gold/evaluator.
