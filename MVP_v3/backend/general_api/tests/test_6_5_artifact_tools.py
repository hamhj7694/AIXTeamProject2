from scripts.compare_6_5_reports import compare
from scripts.validate_6_5_artifact import scan


def test_artifact_scan_rejects_raw_and_sensitive_values() -> None:
    issues = scan({"turns": ["hidden"], "value": "OTP 583921"})
    assert any(item.startswith("FORBIDDEN_KEY") for item in issues)
    assert any(item.startswith("SENSITIVE_LITERAL") for item in issues)


def test_report_compare_returns_fingerprint_and_count_delta() -> None:
    first = {"semantic_atoms": [{"fingerprint": "a"}], "quality_report": {"pipeline_counts": {"events": 1}}}
    second = {"semantic_atoms": [{"fingerprint": "b"}], "quality_report": {"pipeline_counts": {"events": 2}}}
    result = compare(first, second)
    assert result["atom_fingerprints"]["added"] == ["b"]
    assert result["atom_fingerprints"]["removed"] == ["a"]
    assert result["pipeline_count_delta"]["events"] == 1
