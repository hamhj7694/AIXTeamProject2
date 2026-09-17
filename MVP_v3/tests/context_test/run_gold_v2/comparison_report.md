# CSR v3.0 vs v3.1 — Corrected / High-Fidelity Gold 재평가

## A. 평가 환경

| 항목 | 값 |
|---|---|
| Current branch | `v3.1-ham` |
| Current HEAD | `723e5b59691d00695616c656fdd66479d62f6bc9` |
| Official v3.0 source | detached worktree `071fb512ce42a570b0bcf585041eac6f31c2fb1c` |
| Dataset | 30 cases / 150 turns |
| Unique turn sequences | 2 |
| Scenario classes | HIGH 10 / MIXED 10 / LOW 10 |
| v3.0 raw source | `tests/context_test/baseline_v1/raw_results.json` |
| Evaluator | `tests/context_test/evaluate_gold_v2.py` |

Gold SHA-256:

- Canonical human: `b00830db969a5f132b2d2cab5c69783d2c9f25ad577ed4de1084a76cf8876f56`
- v3.0 corrected projection: `d2c0cc0bcd44227f7a0d3e325603a5b3b55cf1f8c373c82092c3d0a35d89ad10`
- v3.1 high-fidelity projection: `65c3338db6a931a48bde1d1137e783ab4505483648f8bc76ecb7c002797f0dcc`

## B. Historical Baseline v1 (audit only)

| Metric | Historical value |
|---|---:|
| Context Feature Recall | 0.4145 |
| Context Feature Precision | 0.4638 |
| Numeric Feature Recall | 0.2359 |
| Numeric Feature Precision | 0.4495 |
| Entity Recall | 0.7667 |
| Amount Recall | 0.9667 |
| Critical Fact Recall | 0.3137 |
| Fact Precision | 0.3475 |
| Semantic Similarity | 0.4679 |
| Contradiction | 7 |
| Hallucination | 76 |
| Hard Gate | FAIL |

These values are preserved and not recomputed with corrected gold.

## C. v3.0 Corrected-Gold result

The evaluator scores only five canonical facts with explicit v3.0 projection:
crime involvement claim, authentication-code request, transfer request/instruction,
safe-account destination, and urgency.

| Metric | ALL_CASES_WEIGHTED | UNIQUE_SEQUENCE_WEIGHTED | Status |
|---|---:|---:|---|
| Canonical comparable recall | 14.0% (14/100) | NOT_APPLICABLE | FULL_30_CASE_SCORE |
| Canonical comparable precision | 100.0% (14/14) | NOT_APPLICABLE | FULL_30_CASE_SCORE |
| Canonical comparable F1 | 24.6% | NOT_APPLICABLE | FULL_30_CASE_SCORE |

The second unique sequence (FACT-21..30) has no observed comparable canonical
facts, so a sequence-weighted recall is not defined rather than treated as zero.

Observed canonical facts intentionally excluded from the shared v3.0 score:
`call_control`, `isolation_family`, and `isolation_bank_staff`; the v3.0
projection does not preserve enough target semantics to score them apples-to-apples.

## D. v3.1 High-Fidelity result

`NOT_RUN`: no v3.1 30-case raw result artifact was found. The high-fidelity gold
file is present, but a single sample or a partial output is not promoted to a
full-case score.

## E. Safety / operation gates

| Gate | Status |
|---|---|
| Contradiction count | NOT_RUN in this projection audit |
| Critical hallucination | NOT_RUN |
| Unknown-to-known error | NOT_RUN |
| Auth request→shared error | NOT_RUN |
| Transfer requested→completed error | NOT_RUN |
| Privacy leak | NOT_RUN |
| ML contract unchanged | NOT_RUN |
| Overall HARD_GATE | NOT_RUN |

## F. Interpretation

- The 14.0% figure is a corrected-gold **shared projection audit**, not a
  full semantic quality score for every canonical atom.
- It must not be compared directly with the historical 0.4145 metric; the gold,
  denominator, and metric definition differ.
- v3.1 improvement delta is `NOT_RUN` until a full v3.1 30-case raw artifact is
  available under the same canonical evaluation contract.
- No production source, ML artifact, DB schema, or frozen historical baseline
  was modified by this evaluation.

## G. Reproduction

```powershell
MVP_v3\.venv\Scripts\python.exe tests/context_test/evaluate_gold_v2.py
```
