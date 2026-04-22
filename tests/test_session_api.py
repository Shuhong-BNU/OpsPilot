from fastapi.testclient import TestClient

from app.main import app
from app.services.auth_service import auth_service
from app.services.session_service import session_service


def login(client: TestClient, username: str, password: str) -> str:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_delete_session_is_idempotent():
    client = TestClient(app)
    token = login(client, "viewer", "viewer123")
    headers = {"Authorization": f"Bearer {token}"}

    viewer = auth_service.authenticate("viewer", "viewer123")
    assert viewer is not None
    session_service.ensure_session("session-test", viewer["id"], title="test")

    first = client.delete("/api/sessions/session-test", headers=headers)
    second = client.delete("/api/sessions/session-test", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["data"]["deleted"] is True
    assert second.json()["data"]["deleted"] is False
