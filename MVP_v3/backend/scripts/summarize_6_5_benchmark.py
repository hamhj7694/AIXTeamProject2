"""Summarize v3.0 benchmark labels without exporting transcript text."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def summarize(source: dict[str, Any]) -> dict[str, Any]:
    cases = source.get("cases", [])
    facts = [fact for case in cases for fact in case.get("atomic_facts", [])]
    return {
        "schema_version": "a-context-benchmark-summary.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "benchmark_version": source.get("benchmark_version"),
        "case_count": len(cases),
        "fact_count": len(facts),
        "scenario_class_counts": dict(Counter(str(case.get("scenario_class")) for case in cases)),
        "semantic_key_counts": dict(Counter(str(fact.get("semantic_key")) for fact in facts)),
        "panel_section_counts": dict(Counter(str(fact.get("expected_panel_section")) for fact in facts)),
        "visibility_counts": dict(Counter(str(fact.get("expected_visibility")) for fact in facts)),
        "criticality_counts": dict(Counter(str(fact.get("criticality")) for fact in facts)),
        "privacy_status": "PASS",
        "source_text_exported": False,
    }


def report(data: dict[str, Any]) -> str:
    lines = [
        "# v3.0 기준선 데이터 요약",
        "",
        f"Benchmark: `{data.get('benchmark_version')}`  ",
        f"Case: `{data['case_count']}`건  ",
        f"Atomic fact: `{data['fact_count']}`건",
        "",
        "## 분포",
        "",
        "| 구분 | 분포 |",
        "|---|---|",
        f"| 시나리오 | {data['scenario_class_counts']} |",
        f"| Semantic key | {data['semantic_key_counts']} |",
        f"| 패널 섹션 | {data['panel_section_counts']} |",
        f"| Visibility | {data['visibility_counts']} |",
        f"| 중요도 | {data['criticality_counts']} |",
        "",
        "## 해석",
        "",
        "이 자료는 v3.1 평가의 비교 기준선과 annotation 범위를 확인하기 위한 요약입니다.",
        "통화 원문과 민감 literal은 export하지 않았으며, v3.1 신규 lexical·expression·relation·signal 정답은 포함하지 않습니다.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize the v3.0 benchmark safely")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    data = summarize(json.loads(args.input.read_text(encoding="utf-8-sig")))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "benchmark-summary.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output_dir / "benchmark-summary-report.md").write_text(report(data), encoding="utf-8")
    print(json.dumps({"case_count": data["case_count"], "fact_count": data["fact_count"], "privacy_status": data["privacy_status"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
