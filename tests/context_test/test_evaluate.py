from __future__ import annotations

import json
import math
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from evaluate import evaluate_payload, metric_delta


def test_baseline_is_reproducible_and_feature_schema_is_stable():
    payload = json.loads((HERE / "baseline_v1" / "raw_results.json").read_text(encoding="utf-8"))
    result = evaluate_payload(payload)
    metrics = result["metrics"]
    assert metrics["sample_count"] == 30
    assert math.isclose(metrics["context_feature_recall"], 0.414486531986532)
    assert metrics["critical_fact_recall"] == 0.31373015873015875
    assert metrics["contradiction_count"] == 7
    assert metrics["hallucination_count"] == 76
    assert metrics["hard_gate_status"] == "FAIL"
    assert metrics["numeric_candidate_feature_count"] == 152
    assert metrics["ml_selected_feature_count"] == 23
    assert metrics["numeric_feature_schema_consistency"] == 1.0
    assert metrics["ml_selected_order_consistency"] == 1.0
    assert metrics["case_projection_success_rate"] == 1.0
    assert metrics["no_database_write_rate"] == 1.0


def test_comparison_keeps_direction_and_non_numeric_values():
    result = metric_delta({"recall": 0.4, "gate": "FAIL"}, {"recall": 0.7, "gate": "PASS"})
    assert round(result["recall"]["delta"], 6) == 0.3
    assert result["gate"]["delta"] is None
