from fastapi import FastAPI
from fastapi.responses import JSONResponse

from backend.contracts.health import Health, Readiness
from backend.contracts.ml import MlInferenceRequest, MlInferenceResult, MlPreflight, MlPrediction
from backend.ai_api.app.domains.diagnosis.preflight import model_preflight
from backend.ai_api.app.domains.diagnosis.model_adapter import load_model_bundle, metadata, predict

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
