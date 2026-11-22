#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${LUMQENIX_PYTHON:-$ROOT/.venv/bin/python}"
[[ -x "$PY" ]] || { echo "Run bash scripts/install-linux.sh first" >&2; exit 1; }
# Refuse to kill or bind unrelated services; never expose API on a public interface.
"$PY" - "$ROOT" <<'PY'
import socket
import sys
for port in (8000, 8080):
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError as exc:
            raise SystemExit(f"Local port {port} unavailable: {exc}")
PY
API_PID=""
UI_PID=""
cleanup() {
  trap - EXIT INT TERM
  [[ -z "$API_PID" ]] || kill "$API_PID" 2>/dev/null || true
  [[ -z "$UI_PID" ]] || kill "$UI_PID" 2>/dev/null || true
  [[ -z "$API_PID" ]] || wait "$API_PID" 2>/dev/null || true
  [[ -z "$UI_PID" ]] || wait "$UI_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM
"$PY" -m uvicorn app.main:app --app-dir "$ROOT/backend" --host 127.0.0.1 --port 8000 --workers 1 &
API_PID=$!
"$PY" -m http.server 8080 --bind 127.0.0.1 --directory "$ROOT/frontend" &
UI_PID=$!
echo "Lumqenix beta: http://127.0.0.1:8080 (Ctrl+C to stop)"
wait -n "$API_PID" "$UI_PID"
