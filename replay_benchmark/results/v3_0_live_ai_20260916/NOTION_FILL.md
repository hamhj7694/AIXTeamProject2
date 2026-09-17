# NOTION_FILL — CSR v3.0 공식 Baseline

기준: 공식 v3.0 commit `071fb512ce42a570b0bcf585041eac6f31c2fb1c`  
Benchmark: `benchmark_v1.0`  
Provider: OpenAI  
Model: `gpt-4o-mini`

## KPI summary

| Metric | v3.0 score | Numerator / denominator | Tier | Status / interpretation |
|---|---:|---:|---|---|
| Provider smoke test | PASS | 1 / 1 | LIVE | `LIVE_AI_READY` |
| Live event extraction availability | 100.0% | 150 / 150 turns | LIVE | 30/30 cases; 0 provider warnings |
| Critical Signal / Fact Recall | NOT RUN | — | LIVE | No official event-to-atomic-fact scorer |
| AI Extraction Precision / Recall / F1 | N/A | — | N/A | v3.0 output event schema와 gold atomic fact의 공식 매핑 부재 |
| Risk Detection HIGH recall | 100.0% | 10 / 10 | LOGIC | deterministic local fallback; LIVE AI 품질 아님 |
| Risk Detection HIGH/LOW precision | 50.0% | 10 / 20 | LOGIC | TP=10, FP=10, FN=0, TN=0 |
| Risk Detection HIGH/LOW F1 | 66.7% | TP=10, FP=10, FN=0 | LOGIC | HIGH/LOW subset; MIXED 제외 |
| Question Duplicate Rate | 0.0% | 0 / 30 | LOGIC | production planner; 15 states |
| Critical Question Coverage | 100.0% | 30 / 30 | LOGIC | supplied UNKNOWN_CRITICAL slots |
| Negation Accuracy | 100.0% | 3 / 3 | LOGIC | production answer structurer |
| AI API regression | 100.0% | 126 / 126 | REGRESSION | regression evidence, quality score 아님 |
| General API non-MySQL regression | 100.0% | 146 / 146 | REGRESSION | regression evidence, quality score 아님 |
| DB Context Survival | BLOCKED | — | BLOCKED | MySQL/Docker 미실행 |

## 기능별 OpenAI token usage (v3.0)

동일한 고정 fixture를 3회 반복하여 실제 provider usage metadata를 합산한 평균입니다. 입력/출력/전체 token은 기능 실행 1회 기준입니다.

| 기능 | 평균 input | 평균 output | 평균 total | 평균 LLM calls | Runs | Status |
|---|---:|---:|---:|---:|---:|---|
| Case Creation / Diagnosis | 3,001.33 | 525.00 | 3,526.33 | 6.00 | 3 | LIVE |
| Bank Staff Chat AI | 533.00 | 192.33 | 725.33 | 1.00 | 3 | LIVE |
| Customer Confirmation Question AI | 736.00 | 133.00 | 869.00 | 1.00 | 3 | LIVE |
| Verification AI | 737.00 | 140.33 | 877.33 | 1.00 | 3 | LIVE |
| Action / Work AI | 736.00 | 156.33 | 892.33 | 1.00 | 3 | LIVE |
| Customer Chat AI | 1,843.00 | 106.33 | 1,949.33 | 1.00 | 3 | LIVE |
| Final Report AI | 574.00 | 241.00 | 815.00 | 1.00 | 3 | LIVE |

측정 총합(7개 기능을 한 번씩 실행하는 시나리오 기준): 평균 total 9,654.67 tokens, provider call 12.00회. Case Creation은 event extraction 5회와 context extraction 1회를 포함합니다.

## Measurement boundary

- LIVE replay: 30/30 cases, 150/150 turns, provider warnings 0.
- Token usage: 별도 production-route harness가 필요하며 아직 수치화하지 않음.
- Chat Task Success / Role Isolation: 별도 chat replay 미실행.
- RAG: `N/A / NOT IMPLEMENTED` (frozen benchmark query 0건).
- `NOT RUN`, `N/A`, `BLOCKED`는 0점으로 환산하지 않음.

## Evidence

- `runtime_status.json`
- `LIVE_AI_REPORT.md`
- `../v3_0_core_metrics_20260916/CORE_METRICS_REPORT.md`
- `../v3_0_live_20260916/LIVE_REPLAY_REPORT.md`
- `../v3_0_token_usage_20260916/token_usage_runs.json`
- `../v3_0_token_usage_20260916/token_usage_calls.json`

## Change guard

Production source modified: NO  
Benchmark Gold/evaluator modified: NO  
Commit: NONE  
Push: NONE
