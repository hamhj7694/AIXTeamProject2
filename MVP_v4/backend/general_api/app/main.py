from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from backend.config import Settings
from backend.contracts.health import Health, Readiness
from backend.database import database_readiness
from backend.general_api.app.clients.ai import AiClient


def create_app() -> FastAPI:
    app = FastAPI(title="CSR General API", version="4.0.0")

    @app.get("/api/v4/health", response_model=Health)
    def health() -> Health:
        return Health(service="csr-general-api")

    @app.get("/api/v4/ready", response_model=Readiness, responses={503: {"model": Readiness}})
    async def ready() -> JSONResponse:
        settings = Settings.from_environment()
        checks = {
            "database": await run_in_threadpool(database_readiness, settings),
            "ai": await AiClient(settings).readiness(),
        }
        result = Readiness(service="csr-general-api", ready=all(v == "ok" for v in checks.values()), checks=checks)
        return JSONResponse(status_code=200 if result.ready else 503, content=result.model_dump())

    return app


app = create_app()
