"""Compare two privacy-safe 6.5 developer reports for reproducibility."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _fingerprints(data: dict[str, Any]) -> set[str]:
    return {
        str(atom.get("fingerprint") or atom.get("atom_id"))
        for atom in data.get("semantic_atoms", [])
        if atom.get("fingerprint") or atom.get("atom_id")
    }


def compare(first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    first_atoms = _fingerprints(first)
    second_atoms = _fingerprints(second)
    first_counts = (first.get("quality_report") or {}).get("pipeline_counts", {})
    second_counts = (second.get("quality_report") or {}).get("pipeline_counts", {})
    return {
        "schema_version": "a-context-reproducibility-diff.v1",
        "atom_fingerprints": {
            "added": sorted(second_atoms - first_atoms),
            "removed": sorted(first_atoms - second_atoms),
            "unchanged": len(first_atoms & second_atoms),
        },
        "pipeline_count_delta": {
            key: second_counts.get(key, 0) - first_counts.get(key, 0)
            for key in sorted(set(first_counts) | set(second_counts))
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two 6.5 developer reports")
    parser.add_argument("first", type=Path)
    parser.add_argument("second", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    first = json.loads(args.first.read_text(encoding="utf-8-sig"))
    second = json.loads(args.second.read_text(encoding="utf-8-sig"))
    result = compare(first, second)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
