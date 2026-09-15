"""Minimal cached evaluator for feature extraction and context reconstruction runs."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parent
COUNT_METRICS = {"contradiction_count", "hallucination_count"}
BOOLEAN_METRICS = {"amount_exact_match"}
CORE_METRICS = (
    "context_feature_recall", "context_feature_precision",
    "numeric_feature_recall", "numeric_feature_precision",
    "entity_recall", "entity_precision", "amount_recall", "amount_precision",
    "amount_exact_match", "critical_fact_recall", "fact_precision",
    "semantic_similarity", "contradiction_count", "hallucination_count",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def percentile(values: list[float], percentile_value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile_value
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _mean(records: list[dict[str, Any]], key: str) -> float:
    values = [float(record[key]) for record in records if isinstance(record.get(key), (int, float, bool))]
    return mean(values) if values else 0.0


def evaluate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    records = payload.get("records", [])
    successful = [record for record in records if record.get("status") == "OK"]
    metric_rows = [record.get("G_metrics", {}) for record in successful]
    metrics: dict[str, Any] = {}
    for key in CORE_METRICS:
        values = [row[key] for row in metric_rows if isinstance(row.get(key), (int, float, bool))]
        if not values:
            continue
        metrics[key] = sum(float(value) for value in values) if key in COUNT_METRICS else mean(float(value) for value in values)

    runtimes = [float(record["runtime_seconds"]) for record in successful if isinstance(record.get("runtime_seconds"), (int, float))]
    candidate_key_sets = [set(record.get("A_extractor_candidate_features", {})) for record in successful]
    selected_orders = [list(record.get("B_ml_selected_features", {})) for record in successful]
    context_codes = sorted({code for record in successful for code in record.get("C_active_context_codes", [])})
    first_candidates = candidate_key_sets[0] if candidate_key_sets else set()
    first_selected = selected_orders[0] if selected_orders else []

    metrics.update({
        "sample_count": len(records),
        "successful_sample_count": len(successful),
        "run_success_rate": len(successful) / len(records) if records else 0.0,
        "case_projection_success_rate": _mean([
            {"value": bool(record.get("F_storage_projection", {}).get("case_id"))} for record in successful
        ], "value"),
        "no_database_write_rate": _mean([
            {"value": record.get("F_storage_boundary", {}).get("database_write_performed") is False}
            for record in successful
        ], "value"),
        "numeric_candidate_feature_count": len(first_candidates),
        "numeric_feature_schema_consistency": (
            sum(keys == first_candidates for keys in candidate_key_sets) / len(candidate_key_sets)
            if candidate_key_sets else 0.0
        ),
        "ml_selected_feature_count": len(first_selected),
        "ml_selected_order_consistency": (
            sum(order == first_selected for order in selected_orders) / len(selected_orders)
            if selected_orders else 0.0
        ),
        "mean_active_numeric_feature_count": _mean(successful, "A_active_feature_count"),
        "mean_active_context_code_count": _mean(successful, "C_active_context_code_count"),
        "context_schema_field_count": _mean(successful, "C_context_schema_field_count"),
        "latency_seconds_mean": mean(runtimes) if runtimes else 0.0,
        "latency_seconds_p50": percentile(runtimes, 0.50),
        "latency_seconds_p95": percentile(runtimes, 0.95),
    })
    metrics["hard_gate_status"] = "PASS" if (
        metrics.get("contradiction_count", 0) == 0 and metrics.get("hallucination_count", 0) == 0
    ) else "FAIL"

    return {
        "metrics": metrics,
        "feature_profile": {
            "numeric_candidate_features": sorted(first_candidates),
            "numeric_candidate_value_types": {
                key: sorted({type(record.get("A_extractor_candidate_features", {}).get(key)).__name__ for record in successful})
                for key in sorted(first_candidates)
            },
            "ml_selected_features_in_order": first_selected,
            "observed_context_codes": context_codes,
        },
        "sample_metrics": [
            {"sample_id": record.get("sample_id"), "category": record.get("category"), **record.get("G_metrics", {})}
            for record in records
        ],
    }


def metric_delta(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in sorted(set(baseline) | set(candidate)):
        before, after = baseline.get(key), candidate.get(key)
        result[key] = {
            "baseline": before,
            "candidate": after,
            "delta": after - before if isinstance(before, (int, float)) and isinstance(after, (int, float)) else None,
        }
    return result


def write_outputs(result: dict[str, Any], source: Path, output: Path, compare_to: Path | None) -> None:
    output.mkdir(parents=True, exist_ok=False)
    (output / "metrics.json").write_text(json.dumps(result["metrics"], ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "feature_profile.json").write_text(json.dumps(result["feature_profile"], ensure_ascii=False, indent=2), encoding="utf-8")
    rows = result["sample_metrics"]
    columns = sorted({key for row in rows for key, value in row.items() if not isinstance(value, (dict, list))})
    with (output / "sample_metrics.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in columns})

    comparison = None
    if compare_to:
        baseline = json.loads(compare_to.read_text(encoding="utf-8"))
        comparison = metric_delta(baseline, result["metrics"])
        (output / "comparison.json").write_text(json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8")

    report = [
        "# Context Test Report", "", f"- Input: `{source}`", f"- Input SHA-256: `{sha256(source)}`",
        f"- Samples: {result['metrics']['sample_count']}",
        f"- Hard gate: **{result['metrics']['hard_gate_status']}**", "", "## Metrics", "",
        "| Metric | Value |", "|---|---:|",
        *[f"| {key} | {value} |" for key, value in sorted(result["metrics"].items())],
    ]
    if comparison is not None:
        report.extend(["", "## Baseline comparison", "", "| Metric | Baseline | Candidate | Delta |", "|---|---:|---:|---:|"])
        report.extend(
            f"| {key} | {values['baseline']} | {values['candidate']} | {values['delta']} |"
            for key, values in comparison.items()
        )
    (output / "REPORT.md").write_text("\n".join(report), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate cached Context feature/reconstruction results")
    parser.add_argument("--input", type=Path, default=ROOT / "baseline_v1" / "raw_results.json")
    parser.add_argument("--output", type=Path, required=True, help="Must be a new directory; existing results are never overwritten")
    parser.add_argument("--compare-to", type=Path, default=ROOT / "baseline_v1" / "metrics.json")
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = evaluate_payload(payload)
    write_outputs(result, args.input, args.output, args.compare_to)
    print(json.dumps({"output": str(args.output), **result["metrics"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

