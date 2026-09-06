from __future__ import annotations

import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import run_validation as rv


def test_sample_suite_has_required_coverage() -> None:
    samples = json.loads(rv.SAMPLES_PATH.read_text(encoding="utf-8"))
    assert len(samples) >= 20
    assert len({sample["sample_id"] for sample in samples}) == len(samples)
    assert all(sample["transcript"].strip() for sample in samples)
    assert all(sample["critical_facts"] for sample in samples)
    assert all(sample["reference_brief"].strip() for sample in samples)
    assert any(any(code.startswith("NORMAL_") for code in sample["expected_context_codes"]) for sample in samples)
    assert any(sample.get("amounts_krw") for sample in samples)


def test_runtime_feature_layer_counts_are_not_mixed() -> None:
    inventory = rv.build_inventory()
    assert (inventory["Extractor 후보"] == "O").sum() == 152
    assert (inventory["ML 입력 여부"] == "O").sum() == 23
    assert len(rv.CONTEXT_FIELDS) == 12
    assert len(rv.SIGNAL_FIELDS) == 7
    assert not inventory.loc[inventory["ML 입력 여부"] == "O", "LLM 입력 여부"].eq("O").any()


def test_completed_results_match_sample_suite() -> None:
    result_path = rv.RESULT_DIR / "context_reconstruction_results.json"
    assert result_path.exists()
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    samples = json.loads(rv.SAMPLES_PATH.read_text(encoding="utf-8"))
    assert len(payload["records"]) == len(samples)
    assert {record["sample_id"] for record in payload["records"]} == {sample["sample_id"] for sample in samples}
    assert all(record["status"] == "OK" for record in payload["records"])
    assert all(record["B_ml_selected_feature_count"] == 23 for record in payload["records"])
    assert all(record["C_context_schema_field_count"] == 12 for record in payload["records"])
    assert all(record["F_storage_boundary"]["database_write_performed"] is False for record in payload["records"])
