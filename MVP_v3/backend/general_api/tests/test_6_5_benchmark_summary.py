from scripts.summarize_6_5_benchmark import summarize


def test_benchmark_summary_keeps_counts_but_not_source_text() -> None:
    result = summarize({
        "benchmark_version": "benchmark_v1.0",
        "cases": [{
            "case_id": "FACT-01", "scenario_class": "HIGH",
            "turns": [{"turn": 1, "text": "원문"}],
            "atomic_facts": [{
                "semantic_key": "transfer_requested", "expected_panel_section": "FRAUD_INDICATORS",
                "expected_visibility": "BANK_INTERNAL", "criticality": "HIGH",
            }],
        }],
    })
    assert result["case_count"] == 1
    assert result["fact_count"] == 1
    assert result["source_text_exported"] is False
    assert "원문" not in str(result)
