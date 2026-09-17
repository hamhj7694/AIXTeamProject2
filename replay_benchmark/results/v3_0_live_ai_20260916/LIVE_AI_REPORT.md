# v3.0 LIVE AI Replay

Official commit: `071fb512ce42a570b0bcf585041eac6f31c2fb1c`  
Benchmark: `benchmark_v1.0`  
Provider model: `gpt-4o-mini`  
Provider status: `LIVE_AI_READY`

## Runtime verification

| Check | Result |
|---|---:|
| Cases executed | 30 / 30 |
| Cases with LIVE status | 30 / 30 (100.0%) |
| Cases with provider warnings | 0 / 30 |
| Successful turn extraction records | 150 / 150 |
| API key written to output | NO |
| Official v3.0 worktree commit | exact match |
| Frozen benchmark/evaluator modified | NO |

The raw structured output is in `runtime_status.json`. It contains event
objects and no API credential. The replay made no production-source or DB
changes.

## KPI status

| Metric | Result | Tier | Status |
|---|---:|---|---|
| Provider smoke test | PASS | LIVE | `LIVE_AI_READY` |
| Live event extraction availability | 150 / 150 | LIVE | 100.0% |
| AI structured extraction Precision / Recall / F1 | N/A | LIVE | No frozen scorer maps event schema to atomic-fact gold |
| Critical Signal / Fact Recall | NOT RUN | LIVE | Requires an official event-to-fact evaluator |
| Chat Task Success | NOT RUN | LIVE | Separate chat replay was not part of this runner |
| Role Isolation | NOT RUN | LIVE | Separate chat replay was not part of this runner |
| Question Duplicate Rate | NOT RUN | LIVE | Separate question-state replay not run |
| Critical Question Coverage | NOT RUN | LIVE | Separate question-state replay not run |
| Negation Accuracy | NOT RUN | LIVE | No official scoring pass in this runner |
| DB Context Survival | BLOCKED | BLOCKED | MySQL/Docker-backed replay not run |

`N/A`, `NOT RUN`, and `BLOCKED` are intentionally not converted to zero.
The existing deterministic LOGIC results remain in the prior baseline report
and are not relabeled as LIVE AI results.

## Evidence

- `runtime_status.json`
- `../v3_0_live_20260916/LIVE_REPLAY_REPORT.md`
- frozen benchmark files and evaluator (hash-checked by the runner)
