from __future__ import annotations

import hashlib
import io
import math
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
import sklearn

from backend.config import ROOT, internal_path


MODEL_FILENAME = "WINDOW_LOGISTIC_DASHBOARD_EXPERIMENTAL_SAMPLE_v1.pkl"
EXPECTED_SHA256 = "662db2a9351dc4ca2c453776ae6f45750e465234cc9abcecc65b58a6b047c5fc"


def model_path() -> Path:
    # No environment override: only this application's approved artifact is loadable.
    return internal_path(str(ROOT / "backend" / "models" / MODEL_FILENAME))


def load_model_bundle() -> dict[str, Any]:
    if sklearn.__version__ != "1.6.1":
        raise RuntimeError("ML 모델은 V4 전용 환경의 scikit-learn 1.6.1이 필요합니다.")
    path = model_path()
    if not path.exists():
        raise FileNotFoundError(f"Window 모델을 찾을 수 없습니다: {path}")
    artifact = path.read_bytes()
    digest = hashlib.sha256(artifact).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError("Window 모델 SHA-256이 승인된 파일과 다릅니다.")
    return _deserialize_verified_artifact(artifact)


@lru_cache(maxsize=1)
def _deserialize_verified_artifact(artifact: bytes) -> dict[str, Any]:
    # Deserialize the exact verified bytes; no second file open between hash and load.
    bundle = joblib.load(io.BytesIO(artifact))
    required = {
        "model", "model_features", "threshold", "guardrail_signal_features",
        "guardrail", "target_mapping", "model_status", "source_run", "model_version",
    }
    missing = sorted(required - set(bundle))
    if missing:
        raise KeyError(f"Window 모델 bundle 필수 항목 누락: {missing}")
    names = list(bundle["model_features"])
    if not names or len(names) != len(set(names)):
        raise ValueError("Invalid model feature order")
    if not math.isfinite(float(bundle["threshold"])) or not 0 < float(bundle["threshold"]) < 1:
        raise ValueError("Invalid model threshold")
    return bundle


def predict(features: dict[str, float]) -> dict[str, Any]:
    bundle = load_model_bundle()
    model_features = list(bundle["model_features"])
    allowed = set(model_features) | set(bundle["guardrail_signal_features"])
    if set(features) - allowed:
        raise ValueError("Unknown ML feature names")
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
           for value in features.values()):
        raise ValueError("ML features must be finite numbers")
    frame = pd.DataFrame([{name: features.get(name, 0) for name in model_features}], columns=model_features)
    raw_probability = float(bundle["model"].predict_proba(frame)[:, 1][0])
    if not math.isfinite(raw_probability) or not 0 <= raw_probability <= 1:
        raise ValueError("Invalid ML probability")
    threshold = float(bundle["threshold"])
    signal_count = sum(float(features.get(name, 0) or 0) != 0 for name in bundle["guardrail_signal_features"])
    final_probability = raw_probability
    guardrail_applied = signal_count == 0
    if guardrail_applied:
        guardrail = bundle["guardrail"]
        cap = float(guardrail.get("zero_feature_cap_score", 20.0)) / 100.0
        margin = float(guardrail.get("threshold_margin", 0.01))
        final_probability = min(raw_probability, cap, max(0.0, threshold - margin))
    return {
        "raw_ml_risk_score": raw_probability * 100,
        "final_risk_score": final_probability * 100,
        "threshold_score": threshold * 100,
        "candidate_signal_count": signal_count,
        "guardrail_applied": guardrail_applied,
        "label": "PHISHING" if final_probability >= threshold else "NORMAL",
    }


def metadata(extractor_model: str) -> dict[str, Any]:
    bundle = load_model_bundle()
    return {
        "model_name": bundle.get("model_name", "Window Logistic"),
        "model_version": bundle["model_version"],
        "model_status": bundle["model_status"],
        "feature_version": bundle.get("feature_version"),
        "source_run": bundle["source_run"],
        "threshold": float(bundle["threshold"]),
        "extractor_model": extractor_model,
        "artifact_sha256": EXPECTED_SHA256,
    }
