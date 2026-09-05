import pytest
from fastapi.testclient import TestClient

from backend.ai_api.app.main import app


def payload(values=None):
    return {"features": {"schema_version": "v1", "values": values or {"signal_count": 1}}, "prediction": {
        "raw_ml_risk_score": 96, "final_risk_score": 96, "threshold_score": 95,
        "candidate_signal_count": 1, "guardrail_applied": False, "label": "PHISHING"}}


def test_feature_only_reconstruction_has_no_text_input_or_output():
    with TestClient(app) as client:
        response = client.post("/reconstruct/features", json=payload())
    assert response.status_code == 200
    assert response.json() == {"route": "FEATURE_ONLY", "classification": "PHISHING", "risk_score": 96.0,
                               "candidate_signal_count": 1, "summary_code": "RISK_SIGNAL"}


@pytest.mark.parametrize("values", [{"raw_text": "forbidden"}, {"nested": {"transcript": "forbidden"}}])
def test_reconstruction_rejects_reconstructable_source_text(values):
    with TestClient(app) as client:
        assert client.post("/reconstruct/features", json=payload(values)).status_code == 422
