from fastapi.testclient import TestClient

from backend.ai_api.app.main import app
from backend.config import Settings


def test_test_text_adapter_is_test_only_and_never_echoes_source(monkeypatch):
    monkeypatch.setattr("backend.ai_api.app.main.Settings.from_environment", lambda: Settings(app_env="test"))
    with TestClient(app) as client:
        response = client.post("/intake/test-text", json={"text": "검찰 긴급 송금 인증"})
    assert response.status_code == 200
    assert response.json()["features"]["money_transfer_present"] == 1
    assert "검찰" not in response.text


def test_test_text_adapter_is_not_available_outside_test(monkeypatch):
    monkeypatch.setattr("backend.ai_api.app.main.Settings.from_environment", lambda: Settings(app_env="development"))
    with TestClient(app) as client:
        assert client.post("/intake/test-text", json={"text": "x"}).status_code == 404
