"""Live preview security/limit contracts without hosted CI."""
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import main, preview_server


def test_live_home_has_strict_browser_response_headers():
    response = TestClient(preview_server.app).get("/")
    assert response.status_code == 200
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Cross-Origin-Resource-Policy"] == "same-origin"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert "connect-src 'self'" in response.headers["Content-Security-Policy"]


def test_live_preview_rejects_cross_origin_form_requests():
    response = TestClient(preview_server.app).post(
        "/api/analyze", headers={"Origin": "https://unrelated.example"},
        files={"file": ("example.jpg", b"invalid", "image/jpeg")},
    )
    assert response.status_code == 403
    assert "Cross-site" in response.json()["detail"]


@pytest.mark.parametrize("origin", [
    "http://[",
    "http://testserver:99999",
    "http://testserver/extra",
    "http://testserver?bad=1",
    "http://testserver#fragment",
    "http://testserver.evil.example",
    "ftp://testserver",
    "null",
])
def test_preview_rejects_invalid_origin_without_server_error(origin):
    preview_server._RECENT_POSTS.clear()
    try:
        reply = TestClient(preview_server.app).post(
            "/api/analyze", headers={"Origin": origin},
            files={"file": ("bad.png", b"not an image", "image/png")},
        )
        assert reply.status_code == 403, (origin, reply.text)
        assert reply.json()["detail"] == "Cross-site processing is disabled"
    finally:
        preview_server._RECENT_POSTS.clear()


def test_origin_parser_rejects_invalid_ascii_controls_and_accepts_case_insensitive_host():
    matches = preview_server._origin_matches_host
    assert not matches("http://testserver\r", "testserver")
    assert not matches("http://testserver\n", "testserver")
    assert not matches("http://testserver ", "testserver")
    assert matches("HTTPS://TESTSERVER".lower(), "testserver")
    assert matches("http://testserver", "testserver")


def test_live_preview_allows_same_origin_form_requests():
    response = TestClient(preview_server.app).post(
        "/api/analyze", headers={"Origin": "http://testserver"},
        files={"file": ("invalid.jpg", b"invalid", "image/jpeg")},
    )
    assert response.status_code == 400


def test_live_rate_limiter_returns_retry_after(monkeypatch):
    preview_server._RECENT_POSTS.clear()
    monkeypatch.setattr(preview_server, "MAX_POSTS_PER_MINUTE", 0)
    try:
        response = TestClient(preview_server.app).post(
            "/api/analyze",
            files={"file": ("bad.jpg", b"x", "image/jpeg")},
        )
        assert response.status_code == 429
        assert response.headers["Retry-After"] == "60"
    finally:
        preview_server._RECENT_POSTS.clear()


def test_cloud_upload_error_displays_active_limit(monkeypatch):
    monkeypatch.setattr(main, "MAX_UPLOAD", 1024 * 1024)
    response = TestClient(main.app).post(
        "/api/analyze",
        files={"file": ("large.png", b"x" * (1024 * 1024 + 1), "image/png")},
    )
    assert response.status_code == 413
    assert "1 MiB" in response.json()["detail"]


def test_cloud_output_cap_message_does_not_claim_desktop_limit(monkeypatch):
    monkeypatch.setattr(main, "PUBLIC_PREVIEW", True)
    monkeypatch.setattr(main, "LITE_MAX_PIXELS", 2_500_000)
    image = Image.new("RGB", (900, 800), (70, 90, 120))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    response = TestClient(main.app).post(
        "/api/enhance/image",
        files={"file": ("big.png", buffer.getvalue(), "image/png")},
        data={"preset": "natural", "scale": 2},
    )
    assert response.status_code == 413
    assert "2.5 million pixels" in response.json()["detail"]
