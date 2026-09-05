import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from backend.config import ROOT
from backend.ai_api.app.domains.diagnosis import model_adapter as adapter
from backend.ai_api.app.domains.diagnosis.preflight import model_preflight


def test_approved_local_artifact_and_frozen_model_contract():
    path = adapter.model_path()
    assert path == ROOT / "backend/models" / adapter.MODEL_FILENAME
    assert hashlib.sha256(path.read_bytes()).hexdigest() == adapter.EXPECTED_SHA256
    bundle = adapter.load_model_bundle()
    assert len(bundle["model_features"]) == 23
    assert bundle["threshold"] == pytest.approx(0.95)
    assert bundle["model_status"] == "EXPERIMENTAL_SAMPLE"


def test_actual_inference_matches_approved_numerical_baseline():
    result = model_preflight()
    zero, active = result.checks["zero_features"], result.checks["signal_features"]
    assert zero.raw_ml_risk_score == pytest.approx(29.02943331672428, abs=1e-8)
    assert zero.final_risk_score == 20
    assert zero.label == "NORMAL"
    assert active.raw_ml_risk_score == pytest.approx(97.60035508086297, abs=1e-8)
    assert active.final_risk_score == active.raw_ml_risk_score
    assert active.label == "PHISHING"
    assert active.candidate_signal_count == 91


def test_input_order_and_omitted_zeros_do_not_change_feature_alignment():
    bundle = adapter.load_model_bundle()
    names = sorted(set(bundle["model_features"]) | set(bundle["guardrail_signal_features"]))
    first = {name: float(i % 2) for i, name in enumerate(names)}
    before = first.copy()
    reversed_values = dict(reversed(list(first.items())))
    sparse = {name: value for name, value in first.items() if value}
    assert adapter.predict(first) == adapter.predict(reversed_values) == adapter.predict(sparse)
    assert first == before


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), "1", True])
def test_invalid_feature_values_rejected(value):
    name = adapter.load_model_bundle()["model_features"][0]
    with pytest.raises(ValueError, match="finite numbers"):
        adapter.predict({name: value})


def test_unknown_feature_rejected():
    with pytest.raises(ValueError, match="Unknown"):
        adapter.predict({"unregistered_feature": 1.0})


def test_hash_checked_even_after_successful_cached_load(monkeypatch):
    adapter.load_model_bundle()
    monkeypatch.setattr(adapter, "EXPECTED_SHA256", "0" * 64)
    with pytest.raises(ValueError, match="SHA-256"):
        adapter.load_model_bundle()


def test_wrong_sklearn_version_rejected(monkeypatch):
    monkeypatch.setattr(adapter.sklearn, "__version__", "0.0.0")
    with pytest.raises(RuntimeError, match="1.6.1"):
        adapter.load_model_bundle()


def test_missing_artifact_never_uses_external_fallback(monkeypatch):
    (ROOT / ".cache").mkdir(exist_ok=True)
    with TemporaryDirectory(dir=ROOT / ".cache") as directory:
        monkeypatch.setattr(adapter, "ROOT", Path(directory))
        with pytest.raises(FileNotFoundError):
            adapter.load_model_bundle()


def test_legacy_model_override_is_not_read(monkeypatch):
    # A variable name is not a runtime path input. No real env file is created/read.
    monkeypatch.setenv("WINDOW_MODEL_PATH", "../unapproved.pkl")
    assert adapter.model_path() == ROOT / "backend/models" / adapter.MODEL_FILENAME


def test_deserializer_receives_verified_bytes_not_file_path(monkeypatch):
    artifact = adapter.model_path().read_bytes()
    adapter._deserialize_verified_artifact.cache_clear()
    original = adapter.joblib.load
    received = []

    def checked_load(stream):
        assert not isinstance(stream, (str, Path))
        received.append(stream.getvalue())
        return original(stream)

    monkeypatch.setattr(adapter.joblib, "load", checked_load)
    adapter.load_model_bundle()
    assert received == [artifact]
