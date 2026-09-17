"""Legacy converter for historical compatibility tests only.

It must not be used as the current official Gold source. The official files
live under docs/now_md/.../fixtures/official_gold/.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


_PREDICATE = {
    "claimed_organization": "CLAIMS_ORGANIZATION",
    "claimed_role": "CLAIMS_ROLE",
    "transfer_requested": "TRANSFER_FUNDS",
    "transfer_amount": "TRANSFER_FUNDS",
    "otp_shared": "DISCLOSE_OTP",
    "password_shared": "DISCLOSE_PASSWORD",
    "remote_app_requested": "INSTALL_APP",
    "isolation_family": "COMMUNICATION_CONTROL",
    "isolation_bank_staff": "COMMUNICATION_CONTROL",
}

_FIELD = {
    "claimed_organization": "claimed_organization",
    "claimed_role": "claimed_role",
    "transfer_amount": "amount_value_krw",
    "transfer_requested": "action_state",
    "otp_shared": "polarity",
    "password_shared": "polarity",
    "remote_app_requested": "action_state",
    "isolation_family": "communication_control",
    "isolation_bank_staff": "communication_control",
}


def _value(fact: dict[str, Any]) -> Any:
    key = fact["semantic_key"]
    value = fact.get("gold_value")
    if key in {"otp_shared", "password_shared"}:
        return "POSITIVE" if value is True else "NEGATIVE"
    if key in {"transfer_requested", "remote_app_requested"}:
        return "REQUESTED" if value is True else "UNKNOWN"
    return value


def convert(source: dict[str, Any]) -> list[dict[str, Any]]:
    converted = []
    for case in source.get("cases", []):
        atom_keys: set[str] = set()
        critical_slots: set[str] = set()
        panel_expectations = []
        for fact in case.get("atomic_facts", []):
            key = str(fact.get("semantic_key"))
            predicate = _PREDICATE.get(key)
            field = _FIELD.get(key)
            turn = fact.get("source_turn")
            if not predicate or not field:
                continue
            atom_keys.add(f"{predicate}|T{turn}")
            critical_slots.add(f"T{turn}:{field}={_value(fact)}")
            panel_expectations.append({
                "semantic_key": key,
                "source_turn": turn,
                "expected_panel_section": fact.get("expected_panel_section"),
                "expected_visibility": fact.get("expected_visibility"),
            })
        converted.append({
            "schema_version": "a-context-gold-annotation.v1",
            "fixture_id": case.get("case_id"),
            "annotation_status": "IMPORTED_V3_0_PARTIAL_GOLD",
            "source_benchmark": "benchmark_v1.0",
            "source_policy": "v3.0 atomic facts are reusable baseline labels; v3.1 lexical/expression labels require review",
            "expected": {
                "event_keys": [],
                "atom_keys": sorted(atom_keys),
                "critical_slots": sorted(critical_slots),
                "observed_lexical_codes": [],
            },
            "panel_expectations": panel_expectations,
            "new_v3_1_labels_pending": [
                "observed_lexical_codes", "expression_features", "relation_keys", "context_signal_keys",
            ],
        })
    return converted


def main() -> None:
    parser = argparse.ArgumentParser(description="Import v3.0 gold facts as v3.1 annotation seeds")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    source = json.loads(args.input.read_text(encoding="utf-8-sig"))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for item in convert(source):
        path = args.output_dir / f"{item['fixture_id']}.json"
        path.write_text(json.dumps(item, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        outputs.append(str(path))
    print(json.dumps({"count": len(outputs), "outputs": outputs}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
