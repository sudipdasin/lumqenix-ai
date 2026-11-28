"""Restricted public preview: same-origin UI + CPU-only Community API.

Use this entrypoint only on a cloud host. The local app remains unchanged.
Upload restrictions are also enforced by main.read_limited and pixel preflight.
"""
from collections import deque
from pathlib import Path
import threading
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import main as community

# Do not attach public rate limiting to the local app's shared FastAPI instance:
# the regular desktop API and its regression suite must remain unaffected.
app = FastAPI(title="Lumqenix Community Public Preview", version=community.VERSION,
              docs_url=None, redoc_url=None, openapi_url=None)
app.router.routes.extend(
    route for route in community.app.router.routes
    if getattr(route, "path", "").startswith("/api/")
)

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
RATE_WINDOW_SECONDS = 60
MAX_POSTS_PER_MINUTE = 20
_RECENT_POSTS = deque()
_RATE_LOCK = threading.Lock()


def _origin_matches_host(origin: str, host: str) -> bool:
    """Reject malformed browser Origin values without trusting proxy headers.

    TLS may terminate upstream, so enforce same-host syntax here rather than
    comparing the request scheme from an untrusted forwarding header.
    """
    from urllib.parse import urlsplit

    if not origin or any(ord(char) < 33 or ord(char) > 126 for char in origin):
        return False
    try:
        parsed = urlsplit(origin)
        _ = parsed.port  # Invalid ports and malformed IPv6 must fail closed.
    except ValueError:
        return False
    return (
        parsed.scheme in ("http", "https")
        and parsed.hostname is not None
        and parsed.netloc.lower() == host.lower()
        and not parsed.path
        and not parsed.query
        and not parsed.fragment
    )


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
        # Cross-site HTML forms can send requests despite response CORS rules.
        # No cookies are used; reject foreign browser origins to conserve CPU.
        origin = request.headers.get("origin")
        if origin and not _origin_matches_host(origin, request.headers.get("host", "")):
            return JSONResponse({"detail": "Cross-site processing is disabled"}, status_code=403)
        raw = request.headers.get("content-length")
        if raw is None:
            return JSONResponse({"detail": "Content-Length required for preview uploads"}, status_code=411)
        if raw is not None:
            if not raw.isdecimal() or len(raw) > 12 or int(raw) > 9 * 1024 * 1024:
                return JSONResponse({"detail": "Preview upload limit: 8 MiB"}, status_code=413)
        with _RATE_LOCK:
            now = time.monotonic()
            while _RECENT_POSTS and now - _RECENT_POSTS[0] > RATE_WINDOW_SECONDS:
                _RECENT_POSTS.popleft()
            if len(_RECENT_POSTS) >= MAX_POSTS_PER_MINUTE:
                return JSONResponse({"detail": "Public demo is busy; try again in a minute"}, status_code=429, headers={"Retry-After": "60"})
            _RECENT_POSTS.append(now)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' blob: data:; "
        "connect-src 'self'; script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; object-src 'none'; "
        "base-uri 'none'; frame-ancestors 'none'"
    )
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/healthz", include_in_schema=False)
def healthz():
    return {"status": "ok", "mode": "restricted-public-preview"}


# Register StaticFiles last: API and /healthz routes must take precedence.
app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="community-preview")
