from scripts.import_v3_0_gold_annotations import convert


def test_v3_0_import_creates_partial_v3_1_gold_without_transcript() -> None:
    result = convert({"cases": [{
        "case_id": "FACT-01",
        "turns": [{"turn": 1, "text": "비보관 원문"}],
        "atomic_facts": [{
            "semantic_key": "transfer_amount", "gold_value": 3500000,
            "source_turn": 4, "expected_panel_section": "LOSS_EXPOSURE",
            "expected_visibility": "BANK_INTERNAL",
        }],
    }]})[0]

    assert result["annotation_status"] == "IMPORTED_V3_0_PARTIAL_GOLD"
    assert result["expected"]["atom_keys"] == ["TRANSFER_FUNDS|T4"]
    assert result["expected"]["critical_slots"] == ["T4:amount_value_krw=3500000"]
    assert "비보관 원문" not in str(result)
