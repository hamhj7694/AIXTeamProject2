import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.ai_api.app.main import app as ai_app
from backend.contracts.health import Health
from backend.general_api.app.main import app as general_app


@pytest.mark.parametrize("app,path,service", [(ai_app, "/health", "csr-ai-api"), (general_app, "/api/v4/health", "csr-general-api")])
def test_health_contract(app, path, service):
    with TestClient(app) as client:
        response = client.get(path)
        assert response.status_code == 200
        result = Health.model_validate(response.json())
        assert result.service == service


def test_ai_liveness_does_not_claim_inference_readiness():
    with TestClient(ai_app) as client:
        response = client.get("/ready")
        assert response.status_code == 503
        assert response.json()["ready"] is False
        assert response.json()["checks"] == {"ml": "ok", "conversational": "NOT_IMPLEMENTED", "text_intake": "NOT_IMPLEMENTED"}


def test_ml_readiness_runs_real_model():
    from backend.contracts.ml import MlPreflight
    with TestClient(ai_app) as client:
        response = client.get("/ready/ml")
        assert response.status_code == 200
        result = MlPreflight.model_validate(response.json())
        assert result.checks["zero_features"].label == "NORMAL"
        assert not result.checks["signal_features"].guardrail_applied


def test_corrupt_model_readiness_is_503_without_path_disclosure(monkeypatch):
    from backend.ai_api.app.domains.diagnosis import model_adapter
    monkeypatch.setattr(model_adapter, "EXPECTED_SHA256", "0" * 64)
    with TestClient(ai_app) as client:
        for path in ("/ready/ml", "/ready"):
            response = client.get(path)
            assert response.status_code == 503
            assert response.json()["checks"]["ml"] == "ML_PREFLIGHT_FAILED"
            assert "WINDOW_LOGISTIC" not in response.text


def test_health_rejects_unexpected_fields():
    with pytest.raises(ValidationError):
        Health.model_validate({"service": "csr-ai-api", "secret": "not-a-real-secret"})
