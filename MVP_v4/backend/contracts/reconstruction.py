"""Feature-only reconstruction boundary. Raw source material is intentionally unrepresentable."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.contracts.case import StructuredFeaturePayload
from backend.contracts.ml import MlPrediction


class FeatureReconstructionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    features: StructuredFeaturePayload
    prediction: MlPrediction


class FeatureReconstruction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    route: Literal["FEATURE_ONLY"] = "FEATURE_ONLY"
    classification: Literal["NORMAL", "PHISHING"]
    risk_score: float = Field(ge=0, le=100)
    candidate_signal_count: int = Field(ge=0)
    summary_code: Literal["NO_SIGNAL", "RISK_SIGNAL"]
