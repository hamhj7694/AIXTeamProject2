"""Privacy scan for A-part 6.5 artifacts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


_FORBIDDEN_KEYS = {"turns", "raw_text", "input_text", "evidence_text", "source_text"}
_SAFE_METADATA_KEYS = {
    "generated_at", "created_at", "updated_at", "detected_at_turn", "source_turn_id",
    "turn_id", "revision", "version", "count", "true_positive", "predicted", "expected",
}
_SENSITIVE = re.compile(r"(?:\d{4,}|\d{2,}[- ]\d{2,}|\b[A-Z]{2,}\s*\d{3,}\b)", re.IGNORECASE)


def scan(value: Any, path: str = "$", issues: list[str] | None = None, key: str = "") -> list[str]:
    issues = issues if issues is not None else []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if str(key) in _FORBIDDEN_KEYS:
                issues.append(f"FORBIDDEN_KEY:{child_path}")
            scan(child, child_path, issues, str(key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            scan(child, f"{path}[{index}]", issues, key)
    elif isinstance(value, str):
        if len(value) > 120:
            issues.append(f"LONG_STRING:{path}")
        if key not in _SAFE_METADATA_KEYS and _SENSITIVE.search(value):
            issues.append(f"SENSITIVE_LITERAL:{path}")
    return sorted(set(issues))


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan a 6.5 artifact for forbidden persistence")
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()
    data = json.loads(args.artifact.read_text(encoding="utf-8-sig"))
    issues = scan(data)
    result = {"artifact": str(args.artifact), "privacy_status": "PASS" if not issues else "FAIL", "issues": issues}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(1 if issues else 0)


if __name__ == "__main__":
    main()
