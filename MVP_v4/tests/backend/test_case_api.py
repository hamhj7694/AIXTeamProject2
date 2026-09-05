import json
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.config import ROOT, Settings
from backend.contracts.case import ActorContext, ActorRole
from backend.database import database_engine
from backend.general_api.app.main import create_app, get_settings, require_server_actor
from backend.scripts.migrate import upgrade
from backend.contracts.ml import MlInferenceResult, MlPrediction
from backend.ai_api.app.domains.diagnosis.model_adapter import load_model_bundle


@pytest.fixture
def case_api():
    (ROOT / ".cache").mkdir(exist_ok=True)
    with TemporaryDirectory(dir=ROOT / ".cache") as directory:
        settings = Settings(app_env="test", database_url=f"sqlite:///{Path(directory).as_posix()}/case-api.db")
        upgrade(settings)
        current_actor = {"value": ActorContext(actor_id="staff-1", role=ActorRole.BANK_STAFF)}
        app = create_app()
        app.dependency_overrides[get_settings] = lambda: settings
        app.dependency_overrides[require_server_actor] = lambda: current_actor["value"]
        with TestClient(app) as client:
            yield client, settings, current_actor
        app.dependency_overrides.clear()


def create_staff_case(client, *, request_id=None):
    request_id = request_id or uuid4()
    response = client.post("/api/v4/cases", json={
        "client_request_id": str(request_id), "mode": "PREVENT", "customer_participant_id": "customer-1",
    })
    assert response.status_code == 201, response.text
    return request_id, response.json()


def test_case_create_uses_server_actor_and_retry_idempotency(case_api):
    client, _settings, actor = case_api
    request_id, first = create_staff_case(client)
    assert first["case"]["id"] == str(request_id)
    assert {item["role"] for item in first["participants"]} == {"CUSTOMER", "BANK_STAFF"}
    assert first["events"][0]["visibility"] == "CUSTOMER"

    retry = client.post("/api/v4/cases", json={
        "client_request_id": str(request_id), "mode": "PREVENT", "customer_participant_id": "customer-1",
    })
    assert retry.status_code == 201
    assert retry.json()["case"]["id"] == first["case"]["id"]

    # Neither body fields nor a query flag can impersonate a different actor or projection.
    actor["value"] = ActorContext(actor_id="customer-1", role=ActorRole.CUSTOMER)
    customer = client.get(f"/api/v4/cases/{request_id}?view=BANK_INTERNAL")
    assert customer.status_code == 200
    assert [item["participant_id"] for item in customer.json()["participants"]] == ["customer-1"]
    rejected = client.post("/api/v4/cases", json={
        "client_request_id": str(uuid4()), "customer_participant_id": "customer-1", "actor_role": "BANK_STAFF",
    })
    assert rejected.status_code == 422


def test_event_projection_hides_internal_and_ai_private_data(case_api):
    client, settings, actor = case_api
    case_id, created = create_staff_case(client)
    response = client.post(f"/api/v4/cases/{case_id}/events", json={
        "client_request_id": str(uuid4()), "expected_version": created["case"]["version"],
        "event_type": "ENTITY_CREATED", "entity_type": "TASK", "visibility": "BANK_INTERNAL",
        "payload": {"task_status": "TODO"},
    })
    assert response.status_code == 200, response.text
    assert response.json()["case"]["revision"] == 2

    # AI-private rows can exist from a server-only AI path, but neither customer nor staff gets them.
    engine = database_engine(settings)
    try:
        with engine.begin() as connection:
            connection.execute(text("""
                INSERT INTO case_events (id, case_id, visibility, event_type, entity_type, actor_role, actor_id,
                    case_revision, payload, created_by, updated_by)
                VALUES (:id, :case_id, 'AI_PRIVATE', 'ENTITY_CREATED', 'FACT', 'AI', 'ai-worker', 2, :payload, 'ai-worker', 'ai-worker')
            """), {"id": str(uuid4()), "case_id": str(case_id), "payload": json.dumps({"private": "hidden"})})
    finally:
        engine.dispose()

    actor["value"] = ActorContext(actor_id="customer-1", role=ActorRole.CUSTOMER)
    customer = client.get(f"/api/v4/cases/{case_id}")
    assert customer.status_code == 200
    assert {event["visibility"] for event in customer.json()["events"]} == {"CUSTOMER"}

    actor["value"] = ActorContext(actor_id="staff-1", role=ActorRole.BANK_STAFF)
    staff = client.get(f"/api/v4/cases/{case_id}")
    assert staff.status_code == 200
    assert {event["visibility"] for event in staff.json()["events"]} == {"CUSTOMER", "BANK_INTERNAL"}
    private_write = client.post(f"/api/v4/cases/{case_id}/events", json={
        "client_request_id": str(uuid4()), "expected_version": staff.json()["case"]["version"],
        "event_type": "ENTITY_CREATED", "entity_type": "FACT", "visibility": "AI_PRIVATE", "payload": {},
    })
    assert private_write.status_code == 403


def test_event_version_conflict_and_idempotency_conflict(case_api):
    client, _settings, _actor = case_api
    case_id, created = create_staff_case(client)
    event_request_id = uuid4()
    event = {
        "client_request_id": str(event_request_id), "expected_version": created["case"]["version"],
        "event_type": "ENTITY_UPDATED", "entity_type": "CASE", "visibility": "CUSTOMER", "payload": {"status": "ACTIVE"},
    }
    first = client.post(f"/api/v4/cases/{case_id}/events", json=event)
    assert first.status_code == 200, first.text
    assert first.json()["case"]["version"] == 2
    retry = client.post(f"/api/v4/cases/{case_id}/events", json=event)
    assert retry.status_code == 200
    assert retry.json()["case"]["version"] == 2

    stale = client.post(f"/api/v4/cases/{case_id}/events", json={
        **event, "client_request_id": str(uuid4()), "payload": {"status": "TRIAGE"},
    })
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "CASE_VERSION_CONFLICT"

    reuse = client.post(f"/api/v4/cases/{case_id}/events", json={**event, "payload": {"status": "DIFFERENT"}})
    assert reuse.status_code == 409
    assert reuse.json()["detail"]["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_delta_is_noop_for_same_fingerprint_and_returns_only_new_events(case_api):
    client, _settings, _actor = case_api
    case_id, created = create_staff_case(client)
    unchanged = client.get(f"/api/v4/cases/{case_id}/delta", params={
        "known_revision": 1, "known_fingerprint": created["case"]["fingerprint"],
    })
    assert unchanged.status_code == 200
    assert unchanged.json()["unchanged"] is True
    assert unchanged.json()["upserts"] == []
    event = client.post(f"/api/v4/cases/{case_id}/events", json={
        "client_request_id": str(uuid4()), "expected_version": 1, "event_type": "ENTITY_CREATED",
        "entity_type": "TASK", "visibility": "BANK_INTERNAL", "payload": {"task_status": "TODO"},
    })
    assert event.status_code == 200
    changed = client.get(f"/api/v4/cases/{case_id}/delta", params={"known_revision": 1})
    assert changed.status_code == 200
    assert changed.json()["unchanged"] is False
    assert {item["entity_type"] for item in changed.json()["upserts"]} >= {"CASE", "PARTICIPANT", "TASK"}


def test_missing_server_actor_and_nonparticipant_do_not_gain_case_access(case_api):
    client, _settings, actor = case_api
    case_id, _created = create_staff_case(client)
    app = client.app
    app.dependency_overrides.pop(require_server_actor)
    assert client.get(f"/api/v4/cases/{case_id}").status_code == 401
    app.dependency_overrides[require_server_actor] = lambda: actor["value"]
    actor["value"] = ActorContext(actor_id="other-customer", role=ActorRole.CUSTOMER)
    assert client.get(f"/api/v4/cases/{case_id}").status_code == 404


def test_ml_intake_records_structured_features_event_and_is_idempotent(case_api, monkeypatch):
    client, settings, _actor = case_api
    case_id, created = create_staff_case(client)
    features = {name: 0.0 for name in load_model_bundle()["model_features"]}
    features["unknown_feature"] = 1.0
    async def inference(_self, supplied):
        if "unknown_feature" in supplied:
            raise ValueError("INVALID_STRUCTURED_FEATURES")
        assert supplied == {key: value for key, value in features.items() if key != "unknown_feature"}
        return MlInferenceResult(prediction=MlPrediction(raw_ml_risk_score=98, final_risk_score=98, threshold_score=95,
            candidate_signal_count=1, guardrail_applied=False, label="PHISHING"), provenance={"model_version": "12_07_recall_first_v1.0", "artifact_sha256": "a" * 64})
    monkeypatch.setattr("backend.general_api.app.main.AiClient.infer_structured_features", inference)
    request = {"client_request_id": str(uuid4()), "expected_version": created["case"]["version"],
               "source_event_id": "telecom-1", "features": {key: value for key, value in features.items() if key != "unknown_feature"}}
    first = client.post(f"/api/v4/cases/{case_id}/intake/ml", json=request)
    assert first.status_code == 200, first.text
    assert first.json()["case"]["version"] == 2
    assert any(event["entity_type"] == "CONTEXT_FEATURE" for event in first.json()["events"])
    assert client.post(f"/api/v4/cases/{case_id}/intake/ml", json=request).json()["case"]["version"] == 2
    stale = client.post(f"/api/v4/cases/{case_id}/intake/ml", json={**request, "client_request_id": str(uuid4()), "source_event_id": "telecom-stale"})
    assert stale.status_code == 409
    bad = client.post(f"/api/v4/cases/{case_id}/intake/ml", json={**request, "client_request_id": str(uuid4()), "expected_version": 1, "source_event_id": "telecom-2", "features": features})
    assert bad.status_code == 422
    engine = database_engine(settings)
    try:
        with engine.connect() as connection:
            payload = connection.execute(text("SELECT payload FROM context_features WHERE case_id=:case_id"), {"case_id": str(case_id)}).scalar_one()
            assert "raw_text" not in str(payload) and "PHISHING" in str(payload)
    finally:
        engine.dispose()


def test_ml_intake_reports_ai_unavailable_without_case_write(case_api, monkeypatch):
    client, _settings, _actor = case_api
    case_id, _created = create_staff_case(client)
    async def unavailable(_self, _features):
        raise RuntimeError("ML_INFERENCE_UNAVAILABLE")
    monkeypatch.setattr("backend.general_api.app.main.AiClient.infer_structured_features", unavailable)
    response = client.post(f"/api/v4/cases/{case_id}/intake/ml", json={
        "client_request_id": str(uuid4()), "source_event_id": "telecom-unavailable", "features": {"x": 0.0},
    })
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "ML_INFERENCE_UNAVAILABLE"


def test_test_text_intake_is_transient_and_reuses_ml_persistence(case_api, monkeypatch):
    client, settings, _actor = case_api
    case_id, _created = create_staff_case(client)
    from backend.contracts.ml import MlInferenceResult, MlPrediction, TestTextFeatureResult
    async def extract(_self, text):
        assert text == "demo raw source"
        return TestTextFeatureResult(features={name: 0.0 for name in load_model_bundle()["model_features"]})
    async def infer(_self, _features):
        return MlInferenceResult(prediction=MlPrediction(raw_ml_risk_score=20, final_risk_score=20, threshold_score=95,
            candidate_signal_count=0, guardrail_applied=True, label="NORMAL"), provenance={"model_version": "test", "artifact_sha256": "a" * 64})
    monkeypatch.setattr("backend.general_api.app.main.AiClient.extract_test_text_features", extract)
    monkeypatch.setattr("backend.general_api.app.main.AiClient.infer_structured_features", infer)
    response = client.post(f"/api/v4/cases/{case_id}/intake/test-text", json={"client_request_id": str(uuid4()),
        "expected_version": 1, "source_event_id": "text-1", "text": "demo raw source"})
    assert response.status_code == 200
    engine = database_engine(settings)
    try:
        with engine.connect() as connection:
            assert "demo raw source" not in str(connection.execute(text("SELECT payload FROM context_features")).scalar_one())
    finally: engine.dispose()
