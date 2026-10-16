"""Exploratory five-slot semantic-presence scoring for the CSR A-part replay.

This is *not* the 6.5 Event/Atom/Slot evaluator. It reads the existing
AI-assisted canonical reference and the archived 30-case v3.1 live replay;
it neither calls an LLM nor creates human-confirmed gold labels.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SLOT_KEYS = (
    "crime_involvement_claim",
    "auth_code_disclosure_requested",
    "transfer_requested_or_instructed",
    "safe_account_destination_claimed",
    "urgency",
)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def predicted_slot_presence(structured: dict[str, Any]) -> dict[str, bool]:
    """Explicit, versioned v3.1 projection rules; not a model-based judge."""
    features = structured.get("case_context_features") or {}
    atoms = structured.get("semantic_atoms") or []
    claims = set(features.get("claim_codes") or [])
    requests = set(features.get("requested_action_codes") or [])
    tactics = set(features.get("manipulation_tactic_codes") or [])
    return {
        "crime_involvement_claim": "CLAIM_CRIME_INVOLVEMENT" in claims,
        "auth_code_disclosure_requested": "REQUEST_AUTH_INFO" in requests,
        "transfer_requested_or_instructed": "REQUEST_TRANSFER" in requests,
        "safe_account_destination_claimed": any(
            item.get("source_turn_id") == 4
            and item.get("destination") == "CLAIMED_SAFE_ACCOUNT"
            for item in atoms
        ),
        "urgency": "TACTIC_URGENCY" in tactics,
    }


def expected_slot_presence(gold_case: dict[str, Any]) -> dict[str, bool]:
    summary = gold_case.get("canonical_summary") or {}
    missing = [key for key in SLOT_KEYS if key not in summary]
    if missing:
        raise ValueError(f"Missing canonical reference keys: {missing}")
    # Binary "was this positive claim present?" is intentionally narrower
    # than preservation of VERIFIED/UNKNOWN/MISSING or action-state semantics.
    return {
        key: (
            summary[key].get("value") == "IMMEDIATE"
            if key == "urgency"
            else summary[key].get("value") is True
        )
        for key in SLOT_KEYS
    }


def score(replay: dict[str, Any], reference: dict[str, Any]) -> dict[str, Any]:
    predicted_cases = replay.get("cases") or []
    gold_cases = reference.get("cases") or []
    by_id = {item["case_id"]: item for item in gold_cases}
    if len(by_id) != len(gold_cases):
        raise ValueError("Duplicate canonical reference case IDs")
    if len(predicted_cases) != len(gold_cases):
        raise ValueError("Replay and reference case counts differ")
    if {item["case_id"] for item in predicted_cases} != set(by_id):
        raise ValueError("Replay case IDs do not match canonical reference")

    counts = {key: {"tp": 0, "fp": 0, "fn": 0, "tn": 0} for key in SLOT_KEYS}
    per_case = []
    for item in predicted_cases:
        case_id = item["case_id"]
        if item.get("status") != "LIVE" or item.get("error"):
            raise ValueError(f"{case_id}: not a successful live replay")
        predicted = predicted_slot_presence(item.get("structured_output") or {})
        expected = expected_slot_presence(by_id[case_id])
        for key in SLOT_KEYS:
            p, g = predicted[key], expected[key]
            counts[key]["tp" if p and g else
                        "fp" if p and not g else
                        "fn" if not p and g else "tn"] += 1
        per_case.append({
            "case_id": case_id,
            "prediction": predicted,
            "reference": expected,
        })

    total = {key: sum(row[key] for row in counts.values())
             for key in ("tp", "fp", "fn", "tn")}
    tp, fp, fn = total["tp"], total["fp"], total["fn"]
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "evaluation_type": "AI_ASSISTED_EXPLORATORY_NOT_HUMAN_SIGNED",
        "metric_family": "FIVE_CANONICAL_SLOT_BINARY_PRESENCE_V1",
        "comparison_to_v3_0": "NOT_SAME_SCORER_DO_NOT_CALCULATE_DELTA",
        "gold_annotation_status": reference.get("annotation_status"),
        "replay_status": replay.get("status"),
        "case_count": len(predicted_cases),
        "reference_slot_count": len(predicted_cases) * len(SLOT_KEYS),
        "positive_reference_count": tp + fn,
        "predicted_positive_count": tp + fp,
        "counts_by_slot": counts,
        "totals": total,
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "f1": round(f1, 6),
        "per_case": per_case,
        "limitations": [
            "AI-assisted canonical reference is not a fully human-verified gold set.",
            "30 case IDs reuse only two unique five-turn source sequences.",
            "Presence scoring ignores some evidence, polarity, status and nuanced omissions.",
            "Different evaluator/projection from historical v3.0 corrected-Gold score.",
            "Scores do not replace pending event/atom/critical-slot 6.5 metrics.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay", required=True, type=Path)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = score(read_json(args.replay), read_json(args.reference))
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")


if __name__ == "__main__":
    main()
