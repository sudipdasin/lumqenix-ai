"""Restricted public preview: same-origin UI + CPU-only Community API.

Use this entrypoint only on a cloud host. The local app remains unchanged.
Upload restrictions are also enforced by main.read_limited and pixel preflight.
"""
from collections import deque
import os
from pathlib import Path
import threading
import time

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .main import app

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
RATE_WINDOW_SECONDS = 60
MAX_POSTS_PER_MINUTE = 20
_RECENT_POSTS = deque()
_RATE_LOCK = threading.Lock()


@app.middleware("http")
async def public_demo_request_guard(request: Request, call_next):
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        if request.url.path not in (
            "/api/analyze", "/api/enhance/image", "/api/enhance/onnx",
            "/api/enhance/espcn", "/api/enhance/fsrcnn", "/api/enhance/video",
        ) or request.method != "POST":
            return JSONResponse({"detail": "Unsupported preview write operation"}, status_code=405)
        # No trust in client-supplied forwarding headers. Protect global compute
        # capacity rather than using easily spoofed per-IP rate limits.
        raw = request.headers.get("content-length")
        if raw is not None:
            if not raw.isdecimal() or len(raw) > 12 or int(raw) > 9 * 1024 * 1024:
                return JSONResponse({"detail": "Preview upload limit: 8 MiB"}, status_code=413)
        with _RATE_LOCK:
            now = time.monotonic()
            while _RECENT_POSTS and now - _RECENT_POSTS[0] > RATE_WINDOW_SECONDS:
                _RECENT_POSTS.popleft()
            if len(_RECENT_POSTS) >= MAX_POSTS_PER_MINUTE:
                return JSONResponse({"detail": "Public demo is busy; try again in a minute"}, status_code=429)
            _RECENT_POSTS.append(now)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/healthz", include_in_schema=False)
def healthz():
    return {"status": "ok", "mode": "restricted-public-preview"}


# Register StaticFiles last: API and /healthz routes must take precedence.
app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="community-preview")
