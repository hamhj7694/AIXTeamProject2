=== NOTION UPDATE PAYLOAD ===

평가 기준:
- Current branch: `v3.1-ham`
- Current HEAD: `723e5b59691d00695616c656fdd66479d62f6bc9`
- Official v3.0 source: `071fb512ce42a570b0bcf585041eac6f31c2fb1c`
- Dataset: 30 cases / 150 turns / 2 unique turn sequences
- Scenario class: HIGH 10 / MIXED 10 / LOW 10
- Canonical gold SHA: `b00830db969a5f132b2d2cab5c69783d2c9f25ad577ed4de1084a76cf8876f56`
- v3.0 corrected gold SHA: `d2c0cc0bcd44227f7a0d3e325603a5b3b55cf1f8c373c82092c3d0a35d89ad10`
- v3.1 high-fidelity gold SHA: `65c3338db6a931a48bde1d1137e783ab4505483648f8bc76ecb7c002797f0dcc`

[Historical Baseline v1 — audit only]
- Context Feature Recall: 0.4145
- Context Feature Precision: 0.4638
- Numeric Feature Recall: 0.2359
- Numeric Feature Precision: 0.4495
- Entity Recall: 0.7667
- Amount Recall: 0.9667
- Critical Fact Recall: 0.3137
- Fact Precision: 0.3475
- Semantic Similarity: 0.4679
- Contradiction: 7
- Hallucination: 76
- Hard Gate: FAIL

[v3.0 Corrected Gold — comparable projection]
- Canonical comparable recall: 14.0% (14/100), ALL_CASES_WEIGHTED
- Canonical comparable precision: 100.0% (14/14), ALL_CASES_WEIGHTED
- Canonical comparable F1: 24.6%
- UNIQUE_SEQUENCE_WEIGHTED: NOT_APPLICABLE (second sequence has no observed comparable facts)
- Excluded from shared score: call_control, isolation_family, isolation_bank_staff (v3.0 projection loses target semantics)

[v3.1 High-Fidelity]
- Status: NOT_RUN
- Reason: no full 30-case v3.1 raw result artifact found
- Do not convert a partial sample into a full-case score

[Safety]
- Contradiction / critical hallucination / unknown-to-known / auth-request-to-shared / transfer-request-to-completed / privacy-leak gates: NOT_RUN in this projection audit
- Overall HARD_GATE: NOT_RUN

[Interpretation]
- 14.0% is a corrected-gold shared projection audit, not a universal semantic quality score.
- It is not directly comparable to historical Baseline v1 because gold and denominator changed.
- v3.1 delta is NOT_RUN until the full v3.1 artifact is available under the same contract.

[Artifacts]
- `MVP_v3/tests/context_test/run_gold_v2/comparison_report.md`
- `MVP_v3/tests/context_test/run_gold_v2/metrics.json`
- `MVP_v3/tests/context_test/run_gold_v2/case_results.json`
- `MVP_v3/tests/context_test/run_gold_v2/dataset_profile.json`

=== END NOTION UPDATE PAYLOAD ===
