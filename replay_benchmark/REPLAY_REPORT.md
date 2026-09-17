# CSR Official Replay Benchmark v1.0

Benchmark frozen: **YES** (`BENCHMARK_FROZEN`)

The dataset was frozen before either version replay. It contains 30 cases, 270
Atomic Facts, 20 chat prompts, 15 question states, 10 E2E cases, and no RAG
queries because an official corpus is not implemented in the evaluated
versions. RAG is therefore `NOT IMPLEMENTED`, not a zero score.

## Version manifests

| Version | SHA | Status | AI/DB runtime | Evidence |
|---|---|---|---|---|
| v3.0 | `071fb512ce42a570b0bcf585041eac6f31c2fb1c` | FINAL reference | AI key unavailable; Docker/MySQL unavailable | `results/v3_0/manifest.json` |
| v3.1 | `d2832c742a44551aab3bf11e3bfd246939c5d2c7` | PRELIMINARY | AI key unavailable; Docker/MySQL unavailable | `results/v3_1_preliminary/manifest.json` |

The v3.1 SHA is the current worktree snapshot at replay time. It is not a
final v3.1 release result.

## Capability comparison

| Capability | v3.0 | v3.1 preliminary | Evidence |
|---|---|---|---|
| Case creation | IMPLEMENTED | IMPLEMENTED | per-version manifest |
| Message persistence | IMPLEMENTED | IMPLEMENTED | per-version manifest |
| Generic bounded message Fact extraction | NOT IMPLEMENTED | IMPLEMENTED | per-version manifest |
| Context V2 | IMPLEMENTED | IMPLEMENTED | per-version manifest |
| Context V3 | NOT IMPLEMENTED | IMPLEMENTED | per-version manifest |
| Case-local lexical RAG | IMPLEMENTED | IMPLEMENTED | per-version manifest |
| Official-source RAG | NOT IMPLEMENTED | NOT IMPLEMENTED | no corpus in either tree |
| Final report export | IMPLEMENTED | IMPLEMENTED | per-version manifest |

## Quality metrics

Fact Precision/Recall/F1, critical recall, DB→Fact→Context→Panel→AI survival,
chat quality, question quality, ML pattern metrics, report claim support, and
latency/token/cost are `NOT RUN` for both versions. The required live AI key,
isolated database, and scored response fixtures are unavailable in this
environment. The CSV/JSON result files contain the explicit status and reason;
no missing measurement was converted to zero.

## Hard gates and screenshots

Hard gates are recorded in each `hard_gates.json` as static replay only. Browser
screenshots and rendered reports are `NOT RUN` because no browser/E2E runtime
was available.

## Reproducibility

- Dataset hashes: `BENCHMARK_MANIFEST.json`, and each version's `dataset_hash.txt`.
- Evaluator hash: `BENCHMARK_MANIFEST.json`, and each version's `evaluator_hash.txt`.
- Replay implementation: `bootstrap_benchmark.py`, `evaluator.py`, `replay.py`.
- Production source was not modified by benchmark execution.
