# v3.0 Core Benchmark Metrics

Official commit: `071fb512ce42a570b0bcf585041eac6f31c2fb1c`  
Benchmark: `benchmark_v1.0`  
Benchmark modified: NO

## KPI summary

| Metric | v3.0 Score | Numerator / Denominator | Tier | Status |
|---|---:|---:|---|---|
| Critical Signal / Fact Recall | NOT RUN | NOT RUN / 270 | BLOCKED | Provider/DB unavailable |
| AI Extraction F1 | N/A | N/A | N/A | Generic extractor absent in v3.0 |
| Risk Detection Quality (HIGH recall) | 100.0% | 10 / 10 | LOGIC | Local fallback; HIGH subset |
| Risk Detection HIGH/LOW F1 | 66.7% | TP 10, FP 10, FN 0 | LOGIC | MIXED excluded |
| Chat Task Success | NOT RUN | NOT RUN / 60 | BLOCKED | Provider connection unavailable |
| Role Isolation | NOT RUN | NOT RUN | BLOCKED | Provider connection unavailable |
| Question Duplicate Rate | 0.0% | 0 / 30 | LOGIC | Production planner |
| Critical Question Coverage | 100.0% | 30 / 30 | LOGIC | Production planner |
| Context Survival | NOT RUN | NOT RUN / 270 | BLOCKED | DB/provider unavailable |
| Correction Accuracy | N/A | N/A | N/A | 350→300 path absent in v3.0 |
| Negation Accuracy | 100.0% | 3 / 3 | LOGIC | Production answer structurer |

## Interpretation

- `LOGIC` values are direct calls to v3.0 production domain functions without
  external AI or persistence; they are not live AI quality scores.
- `NOT IMPLEMENTED` and `BLOCKED` are not zeroes.
- The local fallback predicted PHISHING for all 30 cases, including LOW cases;
  this is why HIGH/LOW precision is only 50.0% and why the result is not an
  overall accuracy claim.
