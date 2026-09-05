from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from backend.config import Settings
from backend.contracts.case import ActorContext, ActorRole, BankCaseWorkspace, CaseDelta, CaseListItem, CaseProjection, CreateCaseRequest, CreateEventRequest, CreateMlIntakeRequest, CreateTestTextIntakeRequest
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

    @app.middleware("http")
    async def test_actor_only(request: Request, call_next):
        # Test transport support only. Production never derives authority from client headers.
        if Settings.from_environment().app_env == "test":
            actor_id, actor_role = request.headers.get("X-CSR-Test-Actor-ID"), request.headers.get("X-CSR-Test-Actor-Role")
            if actor_id and actor_role:
                try:
                    request.state.csr_actor = ActorContext(actor_id=actor_id, role=ActorRole(actor_role))
                except ValueError:
                    pass
        return await call_next(request)

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

    @app.get("/api/v4/cases", response_model=list[CaseListItem])
    def list_cases(actor: ActorContext = Depends(require_server_actor),
                   settings: Settings = Depends(get_settings)) -> list[CaseListItem]:
        repository = CaseRepository(settings)
        try:
            return repository.list_bank_cases(actor)
        except Exception as error:
            _case_error(error)
            raise
        finally:
            repository.close()

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

    @app.get("/api/v4/cases/{case_id}/workspace", response_model=BankCaseWorkspace)
    def get_bank_workspace(case_id: str, actor: ActorContext = Depends(require_server_actor),
                           settings: Settings = Depends(get_settings)) -> BankCaseWorkspace:
        from uuid import UUID
        try:
            parsed_id = UUID(case_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "CASE_NOT_FOUND"}) from None
        repository = CaseRepository(settings)
        try:
            return repository.bank_workspace(parsed_id, actor)
        except Exception as error:
            _case_error(error)
            raise
        finally:
            repository.close()

    @app.get("/api/v4/cases/{case_id}/delta", response_model=CaseDelta)
    def get_case_delta(case_id: str, known_revision: int = Query(default=0, ge=0),
                       known_fingerprint: str | None = Query(default=None, pattern=r"^[a-f0-9]{64}$"),
                       actor: ActorContext = Depends(require_server_actor),
                       settings: Settings = Depends(get_settings)) -> CaseDelta:
        from uuid import UUID
        try:
            parsed_id = UUID(case_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "CASE_NOT_FOUND"}) from None
        repository = CaseRepository(settings)
        try:
            return repository.delta(parsed_id, actor, known_revision, known_fingerprint)
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

    @app.post("/api/v4/cases/{case_id}/intake/ml", response_model=CaseProjection)
    async def intake_ml(case_id: str, request: CreateMlIntakeRequest,
                        actor: ActorContext = Depends(require_server_actor),
                        settings: Settings = Depends(get_settings)) -> CaseProjection:
        from uuid import UUID
        try:
            parsed_id = UUID(case_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "CASE_NOT_FOUND"}) from None
        try:
            inference = await AiClient(settings).infer_structured_features(request.features)
        except ValueError:
            raise HTTPException(status_code=422, detail={"code": "INVALID_STRUCTURED_FEATURES"}) from None
        except RuntimeError:
            raise HTTPException(status_code=503, detail={"code": "ML_INFERENCE_UNAVAILABLE"}) from None
        repository = CaseRepository(settings)
        try:
            return repository.record_ml_intake(parsed_id, actor, request,
                                                inference.prediction.model_dump(), inference.provenance)
        except Exception as error:
            _case_error(error)
            raise
        finally:
            repository.close()

    @app.post("/api/v4/cases/{case_id}/intake/test-text", response_model=CaseProjection)
    async def intake_test_text(case_id: str, request: CreateTestTextIntakeRequest,
                               actor: ActorContext = Depends(require_server_actor),
                               settings: Settings = Depends(get_settings)) -> CaseProjection:
        from uuid import UUID
        if settings.app_env != "test":
            raise HTTPException(status_code=404, detail={"code": "TEST_TEXT_INTAKE_DISABLED"})
        try:
            parsed_id = UUID(case_id)
            features = (await AiClient(settings).extract_test_text_features(request.text)).features
            inference = await AiClient(settings).infer_structured_features(features)
        except ValueError:
            raise HTTPException(status_code=422, detail={"code": "INVALID_STRUCTURED_FEATURES"}) from None
        except RuntimeError:
            raise HTTPException(status_code=503, detail={"code": "TEST_TEXT_INTAKE_UNAVAILABLE"}) from None
        repository = CaseRepository(settings)
        try:
            return repository.record_ml_intake(parsed_id, actor, CreateMlIntakeRequest(
                client_request_id=request.client_request_id, expected_version=request.expected_version,
                source_event_id=request.source_event_id, features=features), inference.prediction.model_dump(), inference.provenance)
        except Exception as error:
            _case_error(error)
            raise
        finally:
            repository.close()

    return app


app = create_app()
