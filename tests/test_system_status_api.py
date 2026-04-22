from fastapi.testclient import TestClient

from app.config import config
from app.core.milvus_client import milvus_manager
from app.main import app
from app.services.database_service import database_service
from app.services.runtime_status_service import runtime_status_service


def login(client: TestClient, username: str, password: str) -> str:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_system_status_requires_login():
    client = TestClient(app)
    response = client.get("/api/system/status")
    assert response.status_code == 401


def test_system_status_masks_key_and_reports_access_url(monkeypatch):
    monkeypatch.setattr(config, "host", "0.0.0.0")
    monkeypatch.setattr(config, "port", 9900)
    monkeypatch.setattr(config, "dashscope_api_key", "sk-1234567890abcd")
    monkeypatch.setattr(database_service, "health_check", lambda: True)
    monkeypatch.setattr(milvus_manager, "health_check", lambda: True)
    monkeypatch.setattr(
        runtime_status_service,
        "_probe_http_endpoint",
        lambda url: {
            "healthy": True,
            "status": "ready",
            "message": "HTTP 200",
            "url": url,
        },
    )

    client = TestClient(app)
    token = login(client, "viewer", "viewer123")
    response = client.get(
        "/api/system/status",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()["data"]

    assert payload["network"]["listen_url"] == "http://0.0.0.0:9900"
    assert payload["network"]["access_url"] == "http://localhost:9900"
    assert payload["providers"]["dashscope"]["configured"] is True
    assert payload["providers"]["dashscope"]["masked_key"] == "sk-****abcd"
    assert "sk-1234567890abcd" not in str(payload)
    assert payload["services"]["mcp_cls"]["healthy"] is True
    assert payload["services"]["sqlite"]["healthy"] is True
