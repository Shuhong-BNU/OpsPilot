from fastapi.testclient import TestClient

from app.main import app
from app.services.aiops_service import aiops_service
from app.services.chat_service import chat_service


def login(client: TestClient, username: str, password: str) -> str:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_chat_requires_login():
    client = TestClient(app)
    response = client.post("/api/chat", json={"Id": "s1", "Question": "你好"})
    assert response.status_code == 401


def test_viewer_can_chat_but_cannot_access_aiops(monkeypatch):
    async def fake_chat(question, session_id, user):
        return {"answer": "ok", "route": {"intent": "simple_qa", "route": "simple_qa", "reason": "test"}}

    monkeypatch.setattr(chat_service, "chat", fake_chat)

    client = TestClient(app)
    token = login(client, "viewer", "viewer123")
    headers = {"Authorization": f"Bearer {token}"}

    chat_response = client.post(
        "/api/chat",
        json={"Id": "s1", "Question": "你好"},
        headers=headers,
    )
    aiops_response = client.post(
        "/api/aiops",
        json={"session_id": "s1"},
        headers=headers,
    )

    assert chat_response.status_code == 200
    assert aiops_response.status_code == 403


def test_operator_can_access_aiops(monkeypatch):
    async def fake_diagnose(session_id="default"):
        yield {
            "type": "complete",
            "diagnosis": {"report": "# report"},
        }

    monkeypatch.setattr(aiops_service, "diagnose", fake_diagnose)

    client = TestClient(app)
    token = login(client, "operator", "operator123")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/api/aiops", json={"session_id": "s2"}, headers=headers)

    assert response.status_code == 200
