from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class MlPrediction(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    raw_ml_risk_score: float = Field(ge=0, le=100)
    final_risk_score: float = Field(ge=0, le=100)
    threshold_score: float = Field(gt=0, lt=100)
    candidate_signal_count: int = Field(ge=0)
    guardrail_applied: bool
    label: Literal["NORMAL", "PHISHING"]


class MlPreflight(BaseModel):
    model_config = ConfigDict(extra="forbid")
    service: Literal["csr-ai-api"] = "csr-ai-api"
    capability: Literal["structured_feature_ml"] = "structured_feature_ml"
    ready: Literal[True] = True
    artifact_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    model_status: str
    model_version: str
    sklearn_version: Literal["1.6.1"] = "1.6.1"
    feature_count: int = Field(gt=0)
    checks: dict[str, MlPrediction]


class MlInferenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    features: dict[str, float]


class MlInferenceResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prediction: MlPrediction
    provenance: dict[str, Any]


class TestTextFeatureRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=2000)


class TestTextFeatureResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    features: dict[str, float]
