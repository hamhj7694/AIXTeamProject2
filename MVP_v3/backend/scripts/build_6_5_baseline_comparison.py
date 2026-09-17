"""Build a v3.0 baseline vs v3.1 current-status comparison report."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _value(metrics: dict[str, Any], key: str) -> str:
    item = metrics.get(key, {})
    if "score" in item:
        return str(item["score"])
    if "value" in item:
        return str(item["value"])
    return "NOT AVAILABLE"


def build(baseline: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    base_metrics = baseline.get("metrics", {})
    current_quality = current.get("quality_report", {})
    current_counts = current_quality.get("pipeline_counts", {})
    return {
        "schema_version": "a-context-baseline-comparison.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "comparison_policy": "v3.0 comparable metrics are shown beside v3.1; unavailable v3.1 scores are not inferred",
        "v3_0": {
            "benchmark": baseline.get("benchmark"),
            "commit": baseline.get("commit"),
            "metrics": {
                "context_feature_recall": _value(base_metrics, "critical_signal_fact_recall"),
                "risk_detection_f1": _value(base_metrics, "risk_detection_f1_high_low"),
                "negation_accuracy": _value(base_metrics, "negation_accuracy"),
                "contradiction": "7 cases (historical baseline)",
                "hallucination": "76 cases (historical baseline)",
            },
        },
        "v3_1": {
            "status": "STRUCTURAL_ONLY_PENDING_GOLD_AND_LIVE_RUN",
            "pipeline_counts": current_counts,
            "metrics": {
                "context_feature_recall": "PENDING_HUMAN_ANNOTATION",
                "risk_detection_f1": "PENDING_HUMAN_ANNOTATION",
                "negation_accuracy": "PENDING_HUMAN_ANNOTATION",
                "contradiction": "PENDING_HUMAN_ANNOTATION",
                "hallucination": "PENDING_HUMAN_ANNOTATION",
            },
            "structural_metrics": current_quality.get("audit", {}).get("metrics", {}),
        },
    }


def report(data: dict[str, Any]) -> str:
    old = data["v3_0"]["metrics"]
    new = data["v3_1"]["metrics"]
    counts = data["v3_1"].get("pipeline_counts", {})
    lines = [
        "# v3.0 Baseline · v3.1 A파트 비교 보고서",
        "",
        "v3.0의 과거 성능 수치와 v3.1의 현재 구조 상태를 나란히 비교한 내부 자료입니다.",
        "측정하지 않은 v3.1 수치는 0점으로 간주하지 않고 `PENDING_HUMAN_ANNOTATION`으로 표시합니다.",
        "",
        "## 비교표",
        "",
        "| 지표 | v3.0 Baseline | v3.1 현재 |",
        "|---|---:|---:|",
        f"| Context Feature Recall | {old['context_feature_recall']} | {new['context_feature_recall']} |",
        f"| Risk Detection F1 | {old['risk_detection_f1']} | {new['risk_detection_f1']} |",
        f"| Negation Accuracy | {old['negation_accuracy']} | {new['negation_accuracy']} |",
        f"| Contradiction | {old['contradiction']} | {new['contradiction']} |",
        f"| Hallucination | {old['hallucination']} | {new['hallucination']} |",
        "",
        "## v3.1 현재 구조 건수",
        "",
        "| 구조 | 건수 |",
        "|---|---:|",
    ]
    for key, value in counts.items():
        lines.append(f"| {key} | {value} |")
    lines.extend([
        "",
        "## 해석",
        "",
        "- v3.0 수치는 비교 기준선이며 v3.1의 공식 점수가 아닙니다.",
        "- v3.1 신규 Atom·Observed Term·Relation·Context Signal은 v3.0에 없으므로 별도 annotation이 필요합니다.",
        "- v3.1 정확도 산출 후 같은 표의 `PENDING` 값을 실제 수치로 교체합니다.",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build v3.0 vs v3.1 comparison report")
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text(encoding="utf-8-sig"))
    current = json.loads(args.current.read_text(encoding="utf-8-sig"))
    data = build(baseline, current)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "v3_0_vs_v3_1.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output_dir / "v3_0_vs_v3_1-report.md").write_text(report(data), encoding="utf-8")
    print(json.dumps({"status": data["v3_1"]["status"], "output_dir": str(args.output_dir)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
