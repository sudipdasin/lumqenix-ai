"""Public hosted preview must not alter the installed local FastAPI app."""
from fastapi.testclient import TestClient

from app import main, preview_server


def test_public_preview_serves_same_origin_ui_and_status():
    client = TestClient(preview_server.app)
    page = client.get("/")
    assert page.status_code == 200
    assert "Lumqenix Studio Lite" in page.text
    assert "location.origin" in page.text
    assert client.get("/healthz").json()["status"] == "ok"
    api = client.get("/api/status")
    assert api.status_code == 200
    assert api.json()["edition"] == "community"
    assert api.headers.get("Cache-Control") == "no-store"
    assert api.headers.get("X-Content-Type-Options") == "nosniff"


def test_cloud_middleware_never_modifies_local_desktop_app():
    assert preview_server.app is not main.app
    assert all(getattr(r, "path", "") != "/" for r in main.app.routes)
    assert TestClient(main.app).get("/api/status").status_code == 200


def test_public_preview_rejects_oversize_request_before_processing():
    client = TestClient(preview_server.app)
    reply = client.post(
        "/api/analyze", data=b"fake",
        headers={"content-type": "application/octet-stream",
                 "content-length": str(10 * 1024 * 1024)},
    )
    assert reply.status_code == 413


def test_public_preview_rejects_unsupported_mutation():
    client = TestClient(preview_server.app)
    reply = client.post("/healthz", data=b"x")
    assert reply.status_code == 405


def test_public_preview_global_rate_limit(monkeypatch):
    preview_server._RECENT_POSTS.clear()
    monkeypatch.setattr(preview_server, "MAX_POSTS_PER_MINUTE", 1)
    client = TestClient(preview_server.app)
    try:
        first = client.post(
            "/api/analyze",
            files={"file": ("fake.jpg", b"bad image", "image/jpeg")},
        )
        assert first.status_code == 400
        second = client.post(
            "/api/analyze",
            files={"file": ("fake.jpg", b"bad image", "image/jpeg")},
        )
        assert second.status_code == 429
    finally:
        preview_server._RECENT_POSTS.clear()
