from fastapi import FastAPI
from fastapi.responses import JSONResponse

from backend.contracts.health import Health, Readiness
from backend.contracts.ml import MlInferenceRequest, MlInferenceResult, MlPreflight, MlPrediction, TestTextFeatureRequest, TestTextFeatureResult
from backend.config import Settings
from backend.ai_api.app.domains.diagnosis.preflight import model_preflight
from backend.ai_api.app.domains.diagnosis.model_adapter import load_model_bundle, metadata, predict
from backend.contracts.reconstruction import FeatureReconstruction, FeatureReconstructionRequest

app = FastAPI(title="CSR AI API", version="4.0.0")


@app.get("/health", response_model=Health)
def health() -> Health:
    return Health(service="csr-ai-api")


@app.get("/ready", response_model=Readiness, responses={503: {"model": Readiness}})
def ready() -> JSONResponse:
    try:
        model_preflight()
        ml = "ok"
    except Exception:
        ml = "ML_PREFLIGHT_FAILED"
    # A local model is not a conversational engine. Product readiness stays explicit.
    result = Readiness(service="csr-ai-api", ready=False,
                       checks={"ml": ml, "conversational": "NOT_IMPLEMENTED", "text_intake": "NOT_IMPLEMENTED"})
    return JSONResponse(status_code=503, content=result.model_dump())


@app.get("/ready/ml", response_model=MlPreflight, responses={503: {"model": Readiness}})
def ml_ready() -> MlPreflight | JSONResponse:
    try:
        return model_preflight()
    except Exception:
        result = Readiness(service="csr-ai-api", ready=False, checks={"ml": "ML_PREFLIGHT_FAILED"})
        return JSONResponse(status_code=503, content=result.model_dump())


@app.post("/intake/ml", response_model=MlInferenceResult, responses={503: {"model": Readiness}})
def ml_intake(request: MlInferenceRequest) -> MlInferenceResult | JSONResponse:
    if set(request.features) != set(load_model_bundle()["model_features"]):
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail={"code": "REQUIRED_FEATURES_MISSING_OR_UNKNOWN"})
    try:
        return MlInferenceResult(prediction=MlPrediction.model_validate(predict(request.features)), provenance=metadata("structured_feature_event"))
    except ValueError as error:
        # Validation failures are caller errors and never expose model paths.
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail={"code": "INVALID_STRUCTURED_FEATURES"}) from error
    except Exception:
        result = Readiness(service="csr-ai-api", ready=False, checks={"ml": "ML_INFERENCE_UNAVAILABLE"})
        return JSONResponse(status_code=503, content=result.model_dump())


@app.post("/intake/test-text", response_model=TestTextFeatureResult)
def test_text_features(request: TestTextFeatureRequest) -> TestTextFeatureResult:
    from fastapi import HTTPException
    if Settings.from_environment().app_env != "test":
        raise HTTPException(status_code=404, detail={"code": "TEST_TEXT_INTAKE_DISABLED"})
    text = request.text.lower()
    features = {name: 0.0 for name in load_model_bundle()["model_features"]}
    if any(word in text for word in ("검찰", "police", "prosecutor", "은행")): features["imp_present"] = 1.0
    if any(word in text for word in ("긴급", "urgent")): features["strategy_urgency_present"] = 1.0
    if any(word in text for word in ("송금", "transfer", "입금")): features["money_movement_present"] = features["money_transfer_present"] = 1.0
    if any(word in text for word in ("인증", "password", "비밀번호")): features["action_sensitive_info_present"] = 1.0
    features["signal_family_count"] = float(sum(value != 0 for value in features.values()))
    return TestTextFeatureResult(features=features)


@app.post("/reconstruct/features", response_model=FeatureReconstruction)
def reconstruct_features(request: FeatureReconstructionRequest) -> FeatureReconstruction:
    """Deterministic context handoff; no raw source or paid LLM is present on this route."""
    prediction = request.prediction
    return FeatureReconstruction(classification=prediction.label, risk_score=prediction.final_risk_score,
                                 candidate_signal_count=prediction.candidate_signal_count,
                                 summary_code="RISK_SIGNAL" if prediction.label == "PHISHING" else "NO_SIGNAL")
