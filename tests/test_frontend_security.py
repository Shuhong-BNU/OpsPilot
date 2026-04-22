from fastapi.testclient import TestClient

from app.main import app


def test_root_serves_hardened_frontend():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-security-policy"].startswith("default-src 'self'")
    assert "script-src 'self' https://cdnjs.cloudflare.com" in response.headers["content-security-policy"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"

    html = response.text
    assert html.count('integrity="sha384-') >= 4
    assert "dompurify" in html.lower()
    assert 'role="log"' in html
    assert 'aria-live="polite"' in html
