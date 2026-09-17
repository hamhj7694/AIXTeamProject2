"""Single entry point for the official A-part v3.0/v3.1 comparison.

This runner is intentionally honest about missing artifacts. It validates the
current canonical reference, loads the existing v3.0 evidence, records the
unique-sequence artifact, and evaluates v3.1 only when a structured raw replay
is supplied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = next((p for p in Path(__file__).resolve().parents if (p / "replay_benchmark").is_dir()), Path.cwd())
A_PART = next((p for p in (ROOT / "MVP_v3/docs/now_md/A_part").glob("*") if p.is_dir()), ROOT / "MVP_v3/docs/now_md/A_part")
REFERENCE = A_PART / "fixtures/official_gold/FACT_CONTEXT_CANONICAL_REFERENCE_WITH_EVIDENCE_v1.json"
BENCHMARK = ROOT / "replay_benchmark/fact_context_cases.json"
V30_METRICS = ROOT / "MVP_v3/tests/context_test/run_gold_v2/metrics.json"
V30_TOKEN = ROOT / "MVP_v3/tests/context_test/run_comparison/comparison_metrics.json"
V30_UNIQUE = A_PART / "run_comparison/v30_unique_sequence_metrics.json"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def reference_check() -> dict[str, Any]:
    reference = load(REFERENCE)
    actual_hash = hashlib.sha256(BENCHMARK.read_bytes()).hexdigest()
    return {"status": "PASS" if actual_hash == reference.get("source_file_sha256") else "FAIL",
            "reference_status": reference.get("annotation_status"), "case_count": len(reference.get("cases", [])),
            "source_hash_match": actual_hash == reference.get("source_file_sha256")}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v31-output", type=Path)
    parser.add_argument("--output-dir", type=Path, default=A_PART / "run_comparison")
    args = parser.parse_args()
    v31_ready = False
    v31_summary: dict[str, Any] = {}
    if args.v31_output and args.v31_output.exists():
        try:
            candidate = load(args.v31_output)
            cases = candidate.get("cases", [])
            v31_ready = candidate.get("case_count", 0) > 0 and all(case.get("status") == "LIVE" for case in cases)
            if cases:
                latencies = sorted(float(case.get("latency_ms", 0)) for case in cases)
                rank95 = max(1, int(len(latencies) * 0.95 + 0.999999)) - 1
                v31_summary = {
                    "case_count": len(cases),
                    "live_cases": sum(case.get("status") == "LIVE" for case in cases),
                    "error_cases": sum(case.get("status") != "LIVE" for case in cases),
                    "llm_call_count": sum(int(case.get("llm_call_count", 0)) for case in cases),
                    "input_tokens": sum(int(case.get("usage", {}).get("input_tokens", 0)) for case in cases),
                    "output_tokens": sum(int(case.get("usage", {}).get("output_tokens", 0)) for case in cases),
                    "total_tokens": sum(int(case.get("usage", {}).get("total_tokens", 0)) for case in cases),
                    "avg_total_tokens_per_case": round(sum(int(case.get("usage", {}).get("total_tokens", 0)) for case in cases) / len(cases), 2),
                    "avg_calls_per_case": round(sum(int(case.get("llm_call_count", 0)) for case in cases) / len(cases), 2),
                    "latency_ms": {"p50": latencies[len(latencies) // 2], "p95": latencies[rank95], "max": latencies[-1]},
                    "raw_provider_output_count": len(candidate.get("raw_provider_outputs", [])),
                }
        except (OSError, json.JSONDecodeError):
            v31_ready = False
    v30_data = load(V30_METRICS) if V30_METRICS.exists() else {}
    v30_token_data = load(V30_TOKEN) if V30_TOKEN.exists() else {}
    result: dict[str, Any] = {
        "schema_version": "official-a-part-comparison.v1",
        "reference": reference_check(),
        "v3_0": {"status": "READY" if V30_METRICS.exists() else "NOT_RUN",
                 "metrics_path": str(V30_METRICS) if V30_METRICS.exists() else None,
                 "baseline_metrics": v30_data.get("v3_0", {}),
                 "dataset_profile": v30_data.get("dataset_profile", {}),
                 "token_baseline": v30_token_data.get("v3_0_token_baseline", {}),
                 "unique_sequence": load(V30_UNIQUE) if V30_UNIQUE.exists() else {"status": "NOT_RUN"}},
        "v3_1": {"status": "FULL_RAW_ARTIFACT_AVAILABLE" if v31_ready else ("ARTIFACT_PRESENT_BUT_INCOMPLETE" if args.v31_output and args.v31_output.exists() else "NOT_RUN"),
                 "raw_output_path": str(args.v31_output) if args.v31_output and args.v31_output.exists() else None,
                 "replay_summary": v31_summary},
        "hard_gates": {"status": "PENDING_SEMANTIC_SCORING" if v31_ready else "PENDING_RAW_REPLAY"},
        "latency": {"status": "NOT_RUN", "reason": "Requires successful provider replay for both versions"},
        "projection_gold": {"status": "MISSING_FROM_CHECKOUT", "reference_path": str(REFERENCE)},
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "official_comparison_metrics.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# Official A-part v3.0 vs v3.1 comparison readiness", "", "> **주의:** 이 문서는 현재 증거와 비교 준비 상태를 정리한 문서입니다. v3.0과 v3.1의 직접적인 개선율은 동일 조건 replay가 완료되기 전까지 계산하지 않습니다.", "", "## Status", "",
             f"- Reference: `{result['reference']['status']}` ({result['reference']['case_count']} cases)",
             f"- v3.0 evidence: `{result['v3_0']['status']}`",
             f"- v3.1 replay: `{result['v3_1']['status']}`",
             f"- Hard gates: `{result['hard_gates']['status']}`",
             f"- Latency comparison: `{result['latency']['status']}`", ""]
    baseline = result["v3_0"].get("baseline_metrics", {})
    sample = baseline.get("sample_weighted", {})
    profile = result["v3_0"].get("dataset_profile", {})
    lines += ["## v3.0 corrected-Gold baseline", "", "| Metric | Result |", "|---|---:|",
              f"| Cases | {baseline.get('case_count', profile.get('case_count', 'n/a'))} |",
              f"| Comparable expected facts | {sample.get('comparable_expected', 'n/a')} |",
              f"| True positives | {sample.get('tp', 'n/a')} |",
              f"| False positives | {sample.get('fp', 'n/a')} |",
              f"| False negatives | {sample.get('fn', 'n/a')} |",
              f"| Comparable precision | {sample.get('canonical_comparable_precision', 'n/a')} |",
              f"| Comparable recall | {sample.get('canonical_comparable_recall', 'n/a')} |",
              f"| Comparable F1 | {sample.get('canonical_comparable_f1', 'n/a')} |",
              f"| Dataset turns | {profile.get('turn_count', 'n/a')} |",
              f"| Unique turn sequences | {profile.get('unique_turn_sequence_count', 'n/a')} |", "",
              f"Non-comparable v3.0 keys: `{', '.join(baseline.get('non_comparable_observed_fact_keys', [])) or 'none'}`.", ""]
    token_baseline = result["v3_0"].get("token_baseline", {}).get("features", {})
    if token_baseline:
        lines += ["### v3.0 feature-level live token baseline (\uAE30\uB2A5\uBCC4 \uD1A0\uD070 \uAE30\uC900)", "", "| Feature (\uAE30\uB2A5) | Avg total tokens (\uD3C9\uADE0 \uCD1D \uD1A0\uD070) | Avg calls (\uD3C9\uADE0 \uD638\uCD9C) |", "|---|---:|---:|"]
        for name, values in token_baseline.items():
            lines.append(f"| {name} | {values.get('avg_total_tokens', 'n/a')} | {values.get('avg_calls', 'n/a')} |")
        lines.append("")
    summary = result["v3_1"].get("replay_summary", {})
    if summary:
        latency = summary.get("latency_ms", {})
        lines += ["## v3.1 live Raw Replay", "", "| Metric | Result |", "|---|---:|",
                  f"| Cases | {summary.get('live_cases', 0)} / {summary.get('case_count', 0)} successful |",
                  f"| LLM calls | {summary.get('llm_call_count', 0):,} |",
                  f"| Input tokens | {summary.get('input_tokens', 0):,} |",
                  f"| Output tokens | {summary.get('output_tokens', 0):,} |",
                  f"| Total tokens | {summary.get('total_tokens', 0):,} |",
                  f"| Avg tokens / case (\uCF00\uC774\uC2A4\uB2F9 \uD3C9\uADE0 \uD1A0\uD070) | {summary.get('avg_total_tokens_per_case', 0):,.2f} |",
                  f"| Avg calls / case (\uCF00\uC774\uC2A4\uB2F9 \uD3C9\uADE0 \uD638\uCD9C) | {summary.get('avg_calls_per_case', 0):,.2f} |",
                  f"| Latency P50 | {latency.get('p50', 0):,.2f} ms |",
                  f"| Latency P95 | {latency.get('p95', 0):,.2f} ms |",
                  f"| Latency MAX | {latency.get('max', 0):,.2f} ms |",
                  f"| Raw provider responses | {summary.get('raw_provider_output_count', 0):,} |", ""]
    lines += ["## Required semantic scorecard (\uBE44\uAD50 \uC810\uC218\uD45C)", "", "| Metric | \uD55C\uAD6D\uC5B4 \uC758\uBBF8 | v3.0 | v3.1 | \uD604\uC7AC \uC0C1\uD0DC |", "|---|---|---|---|---|",
              "| Context Feature Precision / Recall / F1 | \uBB38\uB9E5 \uD53C\uCC98 \uC815\uD655\uB3C4\u00B7\uC7AC\uD604\uC728\u00B7F1 | Gold audit \uC77C\uBD80 | Raw output \uC788\uC74C | Gold projection \uD544\uC694 |",
              "| Critical Fact Recall / Fact Precision | \uD575\uC2EC \uC0AC\uC2E4 \uBCF4\uC874 \uC7AC\uD604\uC728\u00B7\uC815\uBC00\uB3C4 | Comparable audit \uC77C\uBD80 | \uBBF8\uC0B0\uCD9C | evaluator \uD544\uC694 |",
              "| Status / Polarity Accuracy | \uC0C1\uD0DC\u00B7\uADF9\uC131(\uC694\uCCAD/\uC9C0\uC2DC/\uC644\uB8CC, \uAE0D\uC815/\uBD80\uC815) \uBCF4\uC874 | \uBBF8\uC0B0\uCD9C | \uBBF8\uC0B0\uCD9C | \uC815\uB2F5 projection \uD544\uC694 |",
              "| Relation Accuracy | \uC0AC\u2ECA \uAC04 \uAD00\uACC4(\uC6D0\uC778\u00B7\uB300\uC0C1\u00B7\uC21C\uC11C) \uC815\uD655\uB3C4 | \uBBF8\uC0B0\uCD9C | \uBBF8\uC0B0\uCD9C | relation Gold \uD544\uC694 |",
              "| Evidence Grounding / Fact Lineage Completeness | \uC6D0\uBB38 \uADFC\uAC70 \uC5F0\uACB0\u00B7\uC0AC\uC2E4 \uACC4\uBCF4 \uC644\uC804\uC131 | \uBBF8\uC0B0\uCD9C | Raw evidence \uAD6C\uC870 \uC788\uC74C | lineage evaluator \uD544\uC694 |",
              "| Correction Resolution Accuracy | \uC815\uC815\u00B7\uBD80\uC815 \uC815\uBCF4\uAC00 \uCD5C\uC885 \uACB0\uACFC\uC5D0 \uBC18\uC601\uB418\uB294 \uC815\uD655\uB3C4 | \uBBF8\uC0B0\uCD9C | \uBBF8\uC0B0\uCD9C | correction fixture \uD544\uC694 |",
              "| Section Projection Accuracy | \uACB0\uACFC \uC139\uC158\uC5D0 \uC62C\uBC14\uB978 \uC0AC\uC2E4\uC774 \uBC30\uCE58\uB418\uB294\uC9C0 | \uBBF8\uC0B0\uCD9C | \uBBF8\uC0B0\uCD9C | projection Gold \uD544\uC694 |",
              "| Critical Contradiction / Hallucination / Privacy Leak | \uCE58\uBA85\uC801 \uBAA8\uC21C\u00B7\uD658\uAC01\u00B7\uAC1C\uC778\uC815\uBCF4 \uC720\uCD9C \uAC74\uC218 | \uBBF8\uCE21\uC815 | \uBBF8\uCE21\uC815 | Hard Gate evaluator \uD544\uC694 |",
              "| Token / Calls / Latency | \uBE44\uC6A9\u00B7\uD638\uCD9C \uC218\u00B7\uC751\uB2F5\uC2DC\uAC04 \uD6A8\uC728 | \uC77C\uBD80 \uCE21\uC815 | \uCE21\uC815 \uC644\uB8CC | v3.0 \uB3D9\uC77C \uD615\uC2DD \uD544\uC694 |", "",
              "## Apples-to-apples comparison contract (동일 조건 비교 계약)", "",
              "현재 v3.0 기능별 token baseline과 v3.1 30-case Diagnosis replay는 실행 단위가 달라 직접 비교하지 않는다.", "",
              "| 비교축 | 동일하게 맞춰야 할 조건 | 현재 상태 |",
              "|---|---|---|",
              "| Case-level tokens/calls/latency (케이스 단위 비용·호출·지연) | 동일 30 cases·동일 turn text·동일 model·동일 provider·동일 환경·동일 반복 횟수 | v3.1 완료 / v3.0 동일 replay 필요 |",
              "| Feature-level tokens/calls (기능별 비용·호출) | 동일 입력을 case_creation_diagnosis, bank_staff_chat_ai 등 같은 7개 기능에 각각 실행 | v3.0 기준만 있음 / v3.1 기능별 실행 필요 |",
              "| Semantic scores (의미 점수) | 동일 canonical Gold와 동일 projection schema | v3.0 일부 / v3.1 Gold projection 필요 |",
              "| Safety gates (안전 게이트) | 동일 critical case와 동일 0-tolerance 규칙 | 양쪽 모두 evaluator 필요 |", "",
              "## Comparison coverage", "", "| Area | v3.0 | v3.1 | Status |", "|---|---|---|---|",
              "| Corrected-Gold comparable facts | Measured | Raw output available | v3.1 scoring pending |",
              "| Semantic/context projection | Partial corrected-Gold audit | Structured output captured | Projection Gold required |",
              "| Safety hard gates | Not reconstructed by this audit | Not yet scored | Pending evaluator |",
              "| Tokens/calls/latency | Existing v3.0 token artifact | Measured in this replay | Comparable cost table pending |", "", 
              "## What can and cannot be compared now", "", "| Category | Current interpretation |", "|---|---|",
              "| v3.0 corrected-Gold scores | v3.0 baseline only; not yet a v3.1 comparison result |",
              "| v3.1 Raw Replay | v3.1 evidence and operational-cost result only |",
              "| v3.0 feature token baseline vs v3.1 case replay | **Not directly comparable** because execution units differ |",
              "| Final improvement/regression claim | Blocked until same-case and same-feature replays are complete |", "",
              "## Interpretation", "", "The v3.1 artifact contains actual provider responses and per-call usage. It is valid evidence for v3.1 execution, but it must not be presented as a direct improvement over v3.0 yet. Final semantic, safety, and cost deltas require identical inputs, feature boundaries, model/provider/environment, repetition count, and the same Gold/evaluator."]
    (args.output_dir / "official_comparison_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"output_dir": str(args.output_dir), "v3_1": result["v3_1"]["status"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
