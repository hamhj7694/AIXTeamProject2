from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from backend.config import Settings
from backend.contracts.case import ActorContext, CaseProjection, CreateCaseRequest, CreateEventRequest
from backend.contracts.health import Health, Readiness
from backend.database import database_readiness
from backend.general_api.app.clients.ai import AiClient
from backend.general_api.app.domains.cases.repository import (
    CaseAccessDenied, CaseNotFound, CaseRepository, IdempotencyConflict, VersionConflict,
)


def get_settings() -> Settings:
    return Settings.from_environment()


def require_server_actor(request: Request) -> ActorContext:
    """Only trusted authentication middleware may attach this request state."""
    actor = getattr(request.state, "csr_actor", None)
    if isinstance(actor, ActorContext):
        return actor
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "SERVER_ACTOR_REQUIRED"})


def _case_error(error: Exception) -> None:
    if isinstance(error, CaseNotFound):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "CASE_NOT_FOUND"}) from None
    if isinstance(error, CaseAccessDenied):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "CASE_ACCESS_DENIED"}) from None
    if isinstance(error, VersionConflict):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": "CASE_VERSION_CONFLICT"}) from None
    if isinstance(error, IdempotencyConflict):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": "IDEMPOTENCY_KEY_REUSED"}) from None
    raise error


def create_app() -> FastAPI:
    app = FastAPI(title="CSR General API", version="4.0.0")

    @app.get("/api/v4/health", response_model=Health)
    def health() -> Health:
        return Health(service="csr-general-api")

    @app.get("/api/v4/ready", response_model=Readiness, responses={503: {"model": Readiness}})
    async def ready() -> JSONResponse:
        settings = get_settings()
        checks = {
            "database": await run_in_threadpool(database_readiness, settings),
            "ai": await AiClient(settings).readiness(),
        }
        result = Readiness(service="csr-general-api", ready=all(v == "ok" for v in checks.values()), checks=checks)
        return JSONResponse(status_code=200 if result.ready else 503, content=result.model_dump())

    @app.post("/api/v4/cases", response_model=CaseProjection, status_code=status.HTTP_201_CREATED)
    def create_case(request: CreateCaseRequest, actor: ActorContext = Depends(require_server_actor),
                    settings: Settings = Depends(get_settings)) -> JSONResponse:
        repository = CaseRepository(settings)
        try:
            projection = repository.create_case(actor, request)
        except Exception as error:
            _case_error(error)
            raise
        finally:
            repository.close()
        return JSONResponse(status_code=status.HTTP_201_CREATED, content=projection.model_dump(mode="json"))

    @app.get("/api/v4/cases/{case_id}", response_model=CaseProjection)
    def get_case(case_id: str, actor: ActorContext = Depends(require_server_actor),
                 settings: Settings = Depends(get_settings)) -> CaseProjection:
        from uuid import UUID
        try:
            parsed_id = UUID(case_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "CASE_NOT_FOUND"}) from None
        repository = CaseRepository(settings)
        try:
            return repository.projection(parsed_id, actor)
        except Exception as error:
            _case_error(error)
            raise
        finally:
            repository.close()

    @app.post("/api/v4/cases/{case_id}/events", response_model=CaseProjection)
    def append_case_event(case_id: str, request: CreateEventRequest,
                          actor: ActorContext = Depends(require_server_actor),
                          settings: Settings = Depends(get_settings)) -> CaseProjection:
        from uuid import UUID
        try:
            parsed_id = UUID(case_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "CASE_NOT_FOUND"}) from None
        repository = CaseRepository(settings)
        try:
            return repository.append_event(parsed_id, actor, request)
        except Exception as error:
            _case_error(error)
            raise
        finally:
            repository.close()

    return app


app = create_app()
