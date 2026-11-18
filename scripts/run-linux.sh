#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
[[ -x "$PY" ]] || { echo "Run bash scripts/install-linux.sh first" >&2; exit 1; }
# API and static UI bind only to loopback. No remote exposure.
"$PY" -m uvicorn app.main:app --app-dir "$ROOT/backend" --host 127.0.0.1 --port 8000 --workers 1 &
API_PID=$!
"$PY" -m http.server 8080 --bind 127.0.0.1 --directory "$ROOT/frontend" &
UI_PID=$!
cleanup() { kill "$API_PID" "$UI_PID" 2>/dev/null || true; wait "$API_PID" "$UI_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
echo "Lumqenix beta: http://127.0.0.1:8080 (Ctrl+C to stop)"
wait -n "$API_PID" "$UI_PID"
