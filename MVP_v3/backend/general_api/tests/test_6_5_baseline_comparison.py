from scripts.build_6_5_baseline_comparison import build


def test_baseline_comparison_does_not_infer_missing_v3_1_scores() -> None:
    result = build(
        {"benchmark": "benchmark_v1.0", "metrics": {"risk_detection_f1_high_low": {"score": "66.7%"}}},
        {"quality_report": {"pipeline_counts": {"events": 5}, "audit": {"metrics": {"event_coverage": 1.0}}}},
    )
    assert result["v3_0"]["metrics"]["risk_detection_f1"] == "66.7%"
    assert result["v3_1"]["metrics"]["risk_detection_f1"] == "PENDING_HUMAN_ANNOTATION"
    assert result["v3_1"]["pipeline_counts"]["events"] == 5
