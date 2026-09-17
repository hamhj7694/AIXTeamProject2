"""Compute the v3.0 corrected-Gold score once per unique turn sequence."""
from __future__ import annotations

import json
from pathlib import Path

_HERE = Path(__file__).resolve()
ROOT = next((p for p in (_HERE, *_HERE.parents) if (p / "replay_benchmark").is_dir()), _HERE.parents[-1])
_A_PART = next((p for p in (ROOT / "MVP_v3/docs/now_md/A_part").glob("*") if p.is_dir()), ROOT / "MVP_v3/docs/now_md/A_part")
CASE_RESULTS = ROOT / "MVP_v3/tests/context_test/run_gold_v2/case_results.json"
PROFILE = ROOT / "MVP_v3/tests/context_test/run_gold_v2/dataset_profile.json"
OUT = _A_PART / "run_comparison/v30_unique_sequence_metrics.json"


def score(tp: int, predicted: int, expected: int) -> dict[str, float | int | None]:
    precision = tp / predicted if predicted else 0.0
    recall = tp / expected if expected else None
    f1 = 2 * precision * recall / (precision + recall) if recall is not None and precision + recall else None
    return {"tp": tp, "predicted": predicted, "expected": expected,
            "precision": round(precision, 6), "recall": None if recall is None else round(recall, 6),
            "f1": None if f1 is None else round(f1, 6)}


def main() -> None:
    rows = json.loads(CASE_RESULTS.read_text(encoding="utf-8"))
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    by_case = {str(row["case_id"]): row for row in rows}
    sequence_scores = []
    for sequence in profile["sequences"]:
        members = [by_case[cid] for cid in sequence["member_case_ids"] if cid in by_case]
        tp = predicted = expected = 0
        for row in members:
            for item in row.get("comparable", {}).values():
                expected += int(bool(item.get("expected")))
                predicted += int(bool(item.get("found")))
                tp += int(bool(item.get("expected")) and bool(item.get("found")))
        metrics = score(tp, predicted, expected)
        sequence_scores.append({"sequence_hash": sequence["sequence_hash"], "member_count": len(members),
                                "status": "NOT_APPLICABLE" if expected == 0 else "SCORED", "metrics": metrics})
    macro = {}
    for name in ("precision", "recall", "f1"):
        values = [x["metrics"][name] for x in sequence_scores if x["status"] == "SCORED" and x["metrics"][name] is not None]
        macro[name] = round(sum(values) / len(values), 6) if values else None
    result = {"status": "PARTIAL_NA" if any(x["status"] == "NOT_APPLICABLE" for x in sequence_scores) else "READY",
              "weighting": "UNIQUE_SEQUENCE_MACRO", "sequence_count": len(sequence_scores),
              "scored_sequence_count": sum(x["status"] == "SCORED" for x in sequence_scores),
              "sequence_macro": macro, "sequences": sequence_scores}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
