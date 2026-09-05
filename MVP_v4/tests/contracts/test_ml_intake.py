from fastapi.testclient import TestClient

from backend.ai_api.app.main import app
from backend.ai_api.app.domains.diagnosis.model_adapter import load_model_bundle


def test_ai_ml_intake_runs_approved_adapter_for_normal_and_signal_features():
    features = {name: 0.0 for name in load_model_bundle()["model_features"]}
    with TestClient(app) as client:
        normal = client.post("/intake/ml", json={"features": features})
        assert normal.status_code == 200
        assert normal.json()["prediction"]["label"] == "NORMAL"
        assert normal.json()["provenance"]["artifact_sha256"]
        signal = dict(features)
        signal["imp_present"] = 1.0
        # The approved guardrail counts its own signal names; every model feature remains supplied.
        response = client.post("/intake/ml", json={"features": signal})
        assert response.status_code == 200


def test_ai_ml_intake_rejects_incomplete_or_unknown_feature_vectors():
    with TestClient(app) as client:
        assert client.post("/intake/ml", json={"features": {}}).status_code == 422
        assert client.post("/intake/ml", json={"features": {"not_approved": 1}}).status_code == 422
