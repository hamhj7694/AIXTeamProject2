# v3.0 Live Replay Baseline (partial)

`LIVE_AI_BLOCKED: PROVIDER_CONNECTION_UNAVAILABLE`

## A. Verification

- Commit: `071fb512ce42a570b0bcf585041eac6f31c2fb1c`
- Benchmark: `benchmark_v1.0`
- Benchmark frozen: YES
- Dataset/evaluator hashes: match frozen manifest
- Live AI: credential was present but the provider call returned `APIConnectionError`
- Benchmark DB: NO
- Existing user DB touched: NO

## B. Runtime setup

The v3.0 detached worktree was inspected and no production source was changed.
Docker was attempted through the repository Compose configuration, but the
Docker daemon was unavailable. No MySQL database was created or reset. The
full General API suite was stopped when its MySQL integration path waited for
the unavailable DB; the non-MySQL suite was executed separately.

## C. Executed deterministic evidence

| Suite | Numerator | Denominator | Score |
|---|---:|---:|---:|
| AI API regression | 126 | 126 | 100.0% |
| General API non-MySQL regression | 146 | 146 | 100.0% |

These are regression-test results, not AI quality scores.

The v3.0 ML artifact was verified without changing it:

- model: Logistic `12_07_recall_first_v1.0`
- feature version: `v2.2`
- threshold: `0.95`
- artifact SHA-256: `662db2a9351dc4ca2c453776ae6f45750e465234cc9abcecc65b58a6b047c5fc`

## D. Benchmark quality metrics

Fact Precision/Recall/F1, Critical Fact metrics, DB→Fact→Context→Panel→AI
funnel, correction/negation/workflow replay, 20-prompt live chat, 15-state
question replay, pattern metrics, report claim metrics, and latency/token/cost
are `NOT RUN`. They require the live AI provider and/or isolated MySQL-backed
application execution. They were not converted to zero.

Official RAG is `N/A / NOT IMPLEMENTED` because the frozen benchmark contains
zero official RAG queries and v3.0 has no official-source corpus.

## E. Evidence

- `runtime_status.json`
- `manifest.json`
- `dataset_hash.txt`
- `evaluator_hash.txt`
- `ai_api_pytest.xml`
- `general_api_non_mysql_pytest.xml`
- `deterministic_ml.json`
- `metrics.json`
- `hard_gates.json`
- `fact_results.csv`, `chat_results.csv`, `question_results.csv`, `ml_results.csv`, `e2e_results.csv`

Browser screenshots and rendered report files: `NOT RUN`.
