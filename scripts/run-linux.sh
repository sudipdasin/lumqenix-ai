#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
# Optional absolute Python path for an already installed environment.
PY="${LUMQENIX_PYTHON:-$ROOT/.venv/bin/python}"
[[ -x "$PY" ]] || { echo "Run bash scripts/install-linux.sh first (or set LUMQENIX_PYTHON to an installed Python)" >&2; exit 1; }
# Optional CPU thread limits: OMP_NUM_THREADS, OPENBLAS_NUM_THREADS, MKL_NUM_THREADS.
exec "$PY" - "$ROOT" <<'PY'
import os
import signal
import socket
import subprocess
import sys
import time

if sys.version_info < (3, 10):
    raise SystemExit("Lumqenix requires Python 3.10+")
root = sys.argv[1]
children = []
stopping = None

def stop(signum, frame):
    global stopping
    stopping = signum

for signum in (signal.SIGINT, signal.SIGTERM):
    signal.signal(signum, stop)

def cleanup():
    # Each service owns a separate session; also stop any of its descendants.
    for child in children:
        try:
            os.killpg(child.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    deadline = time.monotonic() + 5
    while any(child.poll() is None for child in children) and time.monotonic() < deadline:
        time.sleep(.05)
    for child in children:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        child.wait()

def listening(port):
    with socket.socket() as sock:
        sock.settimeout(.1)
        return sock.connect_ex(("127.0.0.1", port)) == 0

try:
    # Check both fixed frontend/API ports before launching either service.
    for port in (8000, 8080):
        with socket.socket() as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError as exc:
                raise RuntimeError(f"Local port {port} unavailable: {exc}") from exc
    commands = [
        [sys.executable, "-m", "uvicorn", "app.main:app", "--app-dir", os.path.join(root, "backend"), "--host", "127.0.0.1", "--port", "8000", "--workers", "1"],
        [sys.executable, "-m", "http.server", "8080", "--bind", "127.0.0.1", "--directory", os.path.join(root, "frontend")],
    ]
    for command in commands:
        if stopping:
            raise SystemExit(128 + stopping)
        children.append(subprocess.Popen(command, cwd=root, start_new_session=True))
    deadline = time.monotonic() + 30
    while not stopping:
        if any(child.poll() is not None for child in children):
            raise RuntimeError("A Lumqenix service exited during startup; see its error above")
        if all(listening(port) for port in (8000, 8080)):
            # Catch startup bind failures before announcing readiness.
            time.sleep(.1)
            if any(child.poll() is not None for child in children):
                continue
            break
        if time.monotonic() >= deadline:
            raise RuntimeError("Lumqenix services did not start within 30 seconds")
        time.sleep(.05)
    if stopping:
        raise SystemExit(128 + stopping)
    print("Lumqenix: http://127.0.0.1:8080 (Ctrl+C to stop)", flush=True)
    while not stopping:
        if any(child.poll() is not None for child in children):
            raise RuntimeError("A Lumqenix service stopped; shutting down both services")
        time.sleep(.1)
    raise SystemExit(128 + stopping)
except (OSError, RuntimeError) as exc:
    print(f"Lumqenix launcher: {exc}", file=sys.stderr, flush=True)
    raise SystemExit(1)
finally:
    cleanup()
PY
