"""Evidence-backed v3.0 vs v3.1 comparison evaluator.

This evaluator never invents a v3.1 score.  It consumes a structured v3.1
artifact when one is supplied and otherwise emits NOT_RUN for v3.1 while still
summarising the existing v3.0 corrected-Gold and token baselines.

Accepted v3.1 case shapes are intentionally tolerant: ``semantic_atoms`` or
``atoms`` (and ``facts`` as a fallback) may be used, with ``atom_key`` or a
predicate/turn pair identifying an atom.  This lets the evaluator sit between
the current extractor output and the final high-fidelity schema.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve()
ROOT = next((p for p in (_HERE, *_HERE.parents) if (p / "replay_benchmark").is_dir()), _HERE.parents[-1])
A_PART_DIR = next(
    (p for p in (ROOT / "MVP_v3/docs/now_md/A_part").glob("*" ) if p.is_dir() and "A파트" in p.name),
    ROOT / "MVP_v3/docs/now_md/A_part",
)
DEFAULT_GOLD = next(
    (ROOT / "MVP_v3/docs/now_md/A_part").glob("*/fixtures/official_gold/FACT_CONTEXT_GOLD_v3_1_HIGH_FIDELITY.json"),
    ROOT / "replay_benchmark/fact_context_cases.json",
)
DEFAULT_V30 = ROOT / "MVP_v3/tests/context_test/run_gold_v2/metrics.json"
DEFAULT_TOKENS = ROOT / "replay_benchmark/results/v3_0_token_usage_20260916/token_usage_runs.json"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def f1(tp: int, predicted: int, expected: int) -> dict[str, Any]:
    precision = tp / predicted if predicted else 0.0
    recall = tp / expected if expected else None
    score = 2 * precision * recall / (precision + recall) if recall is not None and precision + recall else 0.0
    return {"tp": tp, "predicted": predicted, "expected": expected,
            "precision": round(precision, 6), "recall": None if recall is None else round(recall, 6),
            "f1": round(score, 6) if recall is not None else None}


def atom_key(atom: dict[str, Any]) -> str | None:
    key = atom.get("atom_key") or atom.get("semantic_key") or atom.get("fact_id")
    if key:
        return str(key)
    semantic = atom.get("semantic") or atom
    predicate = semantic.get("predicate") or atom.get("predicate")
    turn = atom.get("turn", atom.get("source_turn_id", atom.get("source_turn")))
    if predicate is None or turn is None:
        return None
    return f"{predicate}|T{turn}" if not str(turn).startswith("T") else f"{predicate}|{turn}"


def predicted_atoms(case: dict[str, Any]) -> list[dict[str, Any]]:
    for field in ("semantic_atoms", "atoms", "facts", "atomic_facts"):
        value = case.get(field)
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]
    return []


def gold_atoms(case: dict[str, Any]) -> list[dict[str, Any]]:
    return [x for x in case.get("atoms", case.get("atomic_facts", [])) if isinstance(x, dict)]


def metric_for_case(gold: dict[str, Any], pred: dict[str, Any]) -> dict[str, Any]:
    expected = {k for a in gold_atoms(gold) if (k := atom_key(a))}
    actual = {k for a in predicted_atoms(pred) if (k := atom_key(a))}
    return {"case_id": gold.get("case_id", pred.get("case_id")), "scenario_class": gold.get("source_scenario_class", gold.get("scenario_class")),
            "metrics": f1(len(expected & actual), len(actual), len(expected)),
            "expected_atom_count": len(expected), "predicted_atom_count": len(actual),
            "missing_atoms": sorted(expected - actual), "unexpected_atoms": sorted(actual - expected)}


def evaluate_v31(gold: dict[str, Any], output: Path | None) -> dict[str, Any]:
    if output is None or not output.exists():
        return {"status": "NOT_RUN", "reason": "No v3.1 structured 30-case artifact supplied", "case_count": 0}
    raw = load(output)
    cases = raw.get("cases", raw) if isinstance(raw, dict) else raw
    if not isinstance(cases, list):
        return {"status": "INVALID_ARTIFACT", "reason": "Expected a cases array", "path": str(output)}
    by_id = {str(c.get("case_id")): c for c in cases if isinstance(c, dict) and c.get("case_id")}
    rows = [metric_for_case(g, by_id[g.get("case_id")]) for g in gold.get("cases", []) if g.get("case_id") in by_id]
    if len(rows) != len(gold.get("cases", [])):
        return {"status": "INCOMPLETE_ARTIFACT", "case_count": len(rows), "expected_case_count": len(gold.get("cases", [])), "path": str(output)}
    total = f1(sum(r["metrics"]["tp"] for r in rows), sum(r["metrics"]["predicted"] for r in rows), sum(r["metrics"]["expected"] for r in rows))
    macro = sum(r["metrics"]["f1"] for r in rows) / len(rows) if rows else None
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get("scenario_class") or "UNKNOWN")].append(row)
    category_macro = {name: round(sum(x["metrics"]["f1"] for x in values) / len(values), 6) for name, values in groups.items()}
    return {"status": "FULL_30_CASE_SCORE", "case_count": len(rows), "micro_atom_metrics": total,
            "case_macro_f1": round(macro, 6) if macro is not None else None, "category_macro_f1": category_macro, "cases": rows}


def token_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"status": "NOT_RUN"}
    rows = load(path)
    by_feature: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_feature[str(row.get("feature", "UNKNOWN"))].append(row)
    result = {}
    for feature, values in by_feature.items():
        live = [x for x in values if x.get("status") == "LIVE"]
        result[feature] = {"runs": len(values), "live_runs": len(live),
                           "avg_total_tokens": round(sum(x.get("total_tokens", 0) for x in live) / len(live), 2) if live else None,
                           "avg_calls": round(sum(x.get("llm_call_count", 0) for x in live) / len(live), 2) if live else None}
    return {"status": "READY", "features": result}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v31-output", type=Path)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--v30-metrics", type=Path, default=DEFAULT_V30)
    parser.add_argument("--token-runs", type=Path, default=DEFAULT_TOKENS)
    parser.add_argument("--output-dir", type=Path, default=A_PART_DIR / "run_comparison")
    args = parser.parse_args()
    gold = load(args.gold)
    v30 = load(args.v30_metrics) if args.v30_metrics.exists() else {"status": "NOT_FOUND"}
    result = {"comparison_version": "v3.0-v3.1-a-part.v1", "gold_path": str(args.gold),
              "v3_0": {"status": "READY" if args.v30_metrics.exists() else "NOT_FOUND", "metrics": v30},
              "v3_1": evaluate_v31(gold, args.v31_output), "v3_0_token_baseline": token_summary(args.token_runs),
              "hard_gates": {"status": "NOT_RUN", "reason": "Requires dedicated safety fixture outputs"}}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "comparison_metrics.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# v3.0 vs v3.1 A-part comparison", "", f"- v3.0: `{result['v3_0']['status']}`", f"- v3.1: `{result['v3_1']['status']}`", f"- hard gates: `{result['hard_gates']['status']}`", ""]
    if result["v3_1"].get("micro_atom_metrics"):
        m = result["v3_1"]["micro_atom_metrics"]
        lines += ["| Metric | Value |", "|---|---:|", f"| Atom precision | {m['precision']} |", f"| Atom recall | {m['recall']} |", f"| Atom F1 | {m['f1']} |", f"| Case macro F1 | {result['v3_1']['case_macro_f1']} |"]
    else:
        lines.append("v3.1 full score is NOT RUN until a structured 30-case output artifact is supplied.")
    (args.output_dir / "comparison_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"output_dir": str(args.output_dir), "v3_1_status": result["v3_1"]["status"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
