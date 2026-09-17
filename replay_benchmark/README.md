# CSR Official Replay Benchmark

This directory is deliberately separate from `MVP_v3` production code.  It
contains the frozen, version-neutral benchmark and its replay evidence only.

## Freeze protocol

1. Run `python bootstrap_benchmark.py` once to materialize the deterministic
   v1.0 gold fixtures.
2. Run `python evaluator.py freeze` and review `BENCHMARK_MANIFEST.json`.
3. Do not edit a frozen dataset.  A correction requires a new benchmark
   version and a new directory.
4. Replay a source tree with `python replay.py run --label v3_0 --source ...`.

`replay.py` never imports or changes application source.  It records source
capability evidence and environment blockers.  Live quality measurements
require a configured isolated DB and an AI provider; unavailable measures are
written as `NOT RUN`, never as zero.

The v3.0 reference is fixed to
`071fb512ce42a570b0bcf585041eac6f31c2fb1c`.
