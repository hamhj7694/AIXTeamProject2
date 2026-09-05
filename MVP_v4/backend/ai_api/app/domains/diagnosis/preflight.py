"""Two synthetic, non-personal feature vectors; actual local model inference only."""
from backend.contracts.ml import MlPrediction, MlPreflight
from .model_adapter import EXPECTED_SHA256, load_model_bundle, predict


def model_preflight() -> MlPreflight:
    bundle = load_model_bundle()
    zero = MlPrediction.model_validate(predict({}))
    if not zero.guardrail_applied or zero.label != "NORMAL" or zero.final_risk_score >= zero.threshold_score:
        raise ValueError("Zero-feature guardrail preflight failed")
    signals = {name: 1.0 for name in bundle["guardrail_signal_features"]}
    if not signals:
        raise ValueError("Model is missing guardrail signal features")
    active = MlPrediction.model_validate(predict(signals))
    if active.guardrail_applied or active.candidate_signal_count != len(signals):
        raise ValueError("Signal-feature inference preflight failed")
    return MlPreflight(
        artifact_sha256=EXPECTED_SHA256,
        model_status=str(bundle["model_status"]), model_version=str(bundle["model_version"]),
        feature_count=len(bundle["model_features"]), checks={"zero_features": zero, "signal_features": active},
    )
