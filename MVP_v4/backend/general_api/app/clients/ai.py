import httpx

from backend.config import Settings
from backend.contracts.health import Health, Readiness


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
