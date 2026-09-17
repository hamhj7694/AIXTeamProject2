"""Evaluate privacy-safe 6.5 annotation metrics.

Gold annotations are deliberately separate from model output.  An empty or
pending annotation never produces a fake score; it produces a pending report.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _set(values: Any) -> set[str]:
    return {str(value) for value in (values or []) if str(value).strip()}


def _f1(predicted: set[str], expected: set[str]) -> dict[str, Any]:
    if not expected:
        return {
            "true_positive": 0, "predicted": len(predicted), "expected": 0,
            "precision": None, "recall": None, "f1": None, "status": "NO_GOLD_LABELS",
        }
    true_positive = len(predicted & expected)
    precision = true_positive / len(predicted) if predicted else 0.0
    recall = true_positive / len(expected)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "true_positive": true_positive,
        "predicted": len(predicted),
        "expected": len(expected),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "status": "READY",
    }


def _event_keys(data: dict[str, Any]) -> set[str]:
    return {
        f"{item.get('event_family')}|{item.get('subtype') or 'UNKNOWN'}|T{item.get('detected_at_turn')}"
        for item in data.get("events", [])
    }


def _atom_keys(data: dict[str, Any]) -> set[str]:
    return {
        f"{item.get('predicate')}|T{item.get('source_turn_id')}"
        for item in data.get("semantic_atoms", [])
    }


def _slot_keys(data: dict[str, Any]) -> set[str]:
    fields = (
        "actor", "target", "destination", "amount_scope", "claimed_purpose",
        "threat_type", "auth_secret_type", "action_state", "polarity", "modality",
        "claim_status", "urgency", "obligation",
    )
    result = set()
    for atom in data.get("semantic_atoms", []):
        # Turn-based identity is stable across re-runs; atom_id/fingerprint is not.
        atom_id = f"T{atom.get('source_turn_id')}"
        for field in fields:
            if atom.get(field) is not None:
                result.add(f"{atom_id}:{field}={atom[field]}")
    return result


def _lexical_keys(data: dict[str, Any]) -> set[str]:
    return {
        str(term.get("normalized_code"))
        for atom in data.get("semantic_atoms", [])
        for term in atom.get("observed_terms", []) or []
        if term.get("normalized_code")
    }


def evaluate(predicted: dict[str, Any], gold: dict[str, Any]) -> dict[str, Any]:
    expected = gold.get("expected", {})
    pending = str(gold.get("annotation_status", "")).upper() in {"", "PENDING", "PENDING_HUMAN_ANNOTATION"}
    predicted_sets = {
        "event_decomposition": _event_keys(predicted),
        "semantic_atom": _atom_keys(predicted),
        "critical_slot": _slot_keys(predicted),
        "observed_lexical_code": _lexical_keys(predicted),
    }
    expected_sets = {
        "event_decomposition": _set(expected.get("event_keys")),
        "semantic_atom": _set(expected.get("atom_keys")),
        "critical_slot": _set(expected.get("critical_slots")),
        "observed_lexical_code": _set(expected.get("observed_lexical_codes")),
    }
    atom_ids = {str(item.get("atom_id")) for item in predicted.get("semantic_atoms", []) if item.get("atom_id")}
    event_turns = {str(item.get("detected_at_turn")) for item in predicted.get("events", [])}
    atom_turns = {str(item.get("source_turn_id")) for item in predicted.get("semantic_atoms", [])}
    relations = predicted.get("semantic_relations", [])
    signals = predicted.get("context_signals", [])
    relation_links = sum(
        int(str(item.get("source_atom_id")) in atom_ids and str(item.get("target_atom_id")) in atom_ids)
        for item in relations
    )
    signal_links = sum(
        int(all(str(atom_id) in atom_ids for atom_id in (item.get("atom_ids") or [])))
        for item in signals
    )
    structural = {
        "event_atom_turn_coverage": round(len(event_turns & atom_turns) / len(event_turns), 4) if event_turns else 1.0,
        "relation_lineage_rate": round(relation_links / len(relations), 4) if relations else 1.0,
        "context_signal_lineage_rate": round(signal_links / len(signals), 4) if signals else 1.0,
        "privacy_status": "PASS",
    }
    return {
        "schema_version": "a-context-quality-metrics.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fixture_id": gold.get("fixture_id"),
        "annotation_status": gold.get("annotation_status", "PENDING_HUMAN_ANNOTATION"),
        "score_status": "PENDING_HUMAN_ANNOTATION" if pending else "READY",
        "metrics": {name: _f1(predicted_sets[name], expected_sets[name]) for name in predicted_sets},
        "structural_metrics": structural,
        "predicted_counts": {name: len(values) for name, values in predicted_sets.items()},
    }


def _human_report(result: dict[str, Any]) -> str:
    lines = [
        "# A파트 6.5 품질 지표 보고서",
        "",
        f"평가 상태: `{result['score_status']}`  ",
        f"Fixture: `{result.get('fixture_id') or '미지정'}`  ",
        f"생성 시각: `{result['generated_at']}`",
        "",
        "## 지표 요약",
        "",
        "| 평가 대상 | 예측 수 | 정답 수 | Precision | Recall | F1 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, metric in result["metrics"].items():
        def show(key: str) -> str:
            value = metric.get(key)
            return "-" if value is None else str(value)
        lines.append(
            f"| {name} | {show('predicted')} | {show('expected')} | "
            f"{show('precision')} | {show('recall')} | {show('f1')} |"
        )
    lines.extend([
        "",
        "## 해석",
        "",
        "- `PENDING_HUMAN_ANNOTATION`이면 정답 라벨이 없어 점수를 계산하지 않은 상태입니다.",
        "- 정답 없이도 Event-Atom turn coverage와 Relation/Signal lineage 같은 구조 지표는 확인할 수 있습니다.",
        "- 정답 annotation을 확정한 뒤 같은 명령을 다시 실행해야 실제 Precision·Recall·F1이 생성됩니다.",
        "- 이 자료는 내부 평가용이며 은행 직원용 웹 화면에 노출하지 않습니다.",
        "- 원문과 민감 literal은 평가 결과에 저장하지 않습니다.",
        "",
        "## 구조 지표",
        "",
        "| 지표 | 값 |",
        "|---|---:|",
        f"| Event→Atom turn coverage | {result['structural_metrics']['event_atom_turn_coverage']} |",
        f"| Relation lineage rate | {result['structural_metrics']['relation_lineage_rate']} |",
        f"| Context Signal lineage rate | {result['structural_metrics']['context_signal_lineage_rate']} |",
        f"| Privacy status | `{result['structural_metrics']['privacy_status']}` |",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate A-part 6.5 privacy-safe metrics")
    parser.add_argument("--predicted", type=Path, required=True)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    predicted = json.loads(args.predicted.read_text(encoding="utf-8-sig"))
    gold = json.loads(args.gold.read_text(encoding="utf-8-sig"))
    result = evaluate(predicted, gold)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "quality-metrics.json"
    md_path = args.output_dir / "quality-metrics-report.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_human_report(result), encoding="utf-8")
    print(json.dumps({"metrics_json": str(json_path), "human_report": str(md_path), "score_status": result["score_status"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
