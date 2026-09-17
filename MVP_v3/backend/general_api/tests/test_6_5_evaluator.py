from scripts.evaluate_6_5_metrics import evaluate


def test_6_5_evaluator_reports_structural_metrics_without_gold_labels() -> None:
    predicted = {
        "events": [{"event_family": "ACTION_REQUEST", "subtype": "AUTH_INFO", "detected_at_turn": 1}],
        "semantic_atoms": [{"atom_id": "a1", "predicate": "DISCLOSE_OTP", "source_turn_id": 1}],
        "semantic_relations": [],
        "context_signals": [],
    }
    gold = {"fixture_id": "sample", "annotation_status": "PENDING_HUMAN_ANNOTATION", "expected": {}}

    result = evaluate(predicted, gold)

    assert result["score_status"] == "PENDING_HUMAN_ANNOTATION"
    assert result["structural_metrics"]["event_atom_turn_coverage"] == 1.0
    assert result["structural_metrics"]["privacy_status"] == "PASS"
    assert result["metrics"]["semantic_atom"]["f1"] is None


def test_6_5_evaluator_calculates_f1_only_from_explicit_gold() -> None:
    predicted = {
        "events": [{"event_family": "ACTION_REQUEST", "subtype": "AUTH_INFO", "detected_at_turn": 1}],
        "semantic_atoms": [{"atom_id": "a1", "predicate": "DISCLOSE_OTP", "source_turn_id": 1}],
    }
    gold = {
        "fixture_id": "sample", "annotation_status": "CONFIRMED",
        "expected": {
            "event_keys": ["ACTION_REQUEST|AUTH_INFO|T1"],
            "atom_keys": ["DISCLOSE_OTP|T1"],
        },
    }

    result = evaluate(predicted, gold)

    assert result["score_status"] == "READY"
    assert result["metrics"]["event_decomposition"]["f1"] == 1.0
    assert result["metrics"]["semantic_atom"]["f1"] == 1.0
