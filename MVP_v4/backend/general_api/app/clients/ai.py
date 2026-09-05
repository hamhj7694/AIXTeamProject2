import httpx

from backend.config import Settings
from backend.contracts.health import Health, Readiness
from backend.contracts.ml import MlInferenceResult
from backend.contracts.ml import TestTextFeatureResult


class AiClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def readiness(self) -> str:
        try:
            async with httpx.AsyncClient(
                base_url=self.settings.ai_api_base_url,
                timeout=self.settings.ai_timeout_seconds, trust_env=False,
            ) as client:
                response = await client.get("/health")
                response.raise_for_status()
                health = Health.model_validate(response.json())
                if health.service != "csr-ai-api":
                    return "AI_SERVICE_MISMATCH"
                response = await client.get("/ready")
                result = Readiness.model_validate(response.json())
                if result.service != "csr-ai-api":
                    return "AI_SERVICE_MISMATCH"
                return "ok" if response.is_success and result.ready else "AI_NOT_READY"
        except Exception:
            return "AI_UNAVAILABLE_OR_INVALID_CONTRACT"

    async def infer_structured_features(self, features: dict[str, float]) -> MlInferenceResult:
        try:
            async with httpx.AsyncClient(base_url=self.settings.ai_api_base_url, timeout=self.settings.ai_timeout_seconds,
                                         trust_env=False) as client:
                response = await client.post("/intake/ml", json={"features": features})
            if response.status_code == 422:
                raise ValueError("INVALID_STRUCTURED_FEATURES")
            response.raise_for_status()
            return MlInferenceResult.model_validate(response.json())
        except ValueError:
            raise
        except Exception as error:
            raise RuntimeError("ML_INFERENCE_UNAVAILABLE") from error

    async def extract_test_text_features(self, text: str) -> TestTextFeatureResult:
        try:
            async with httpx.AsyncClient(base_url=self.settings.ai_api_base_url, timeout=self.settings.ai_timeout_seconds,
                                         trust_env=False) as client:
                response = await client.post("/intake/test-text", json={"text": text})
            response.raise_for_status()
            return TestTextFeatureResult.model_validate(response.json())
        except Exception as error:
            raise RuntimeError("TEST_TEXT_INTAKE_UNAVAILABLE") from error
