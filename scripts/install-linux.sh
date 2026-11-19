#!/usr/bin/env bash
# Local Linux beta installer. No root access or system modification required.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
command -v python3 >/dev/null || { echo "Python 3 is required" >&2; exit 1; }
python3 - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit("Lumqenix requires Python 3.10+")
PY
command -v ffmpeg >/dev/null || echo "Note: FFmpeg is missing; video enhancement will be unavailable."
command -v ffprobe >/dev/null || echo "Note: ffprobe is missing; video enhancement will be unavailable."
python3 -m venv "$ROOT/.venv"
"$ROOT/.venv/bin/python" -m pip install --upgrade pip
"$ROOT/.venv/bin/python" -m pip install -r "$ROOT/backend/requirements.txt"
"$ROOT/.venv/bin/python" -m pip check
echo "Installed Lumqenix locally. Launch with: $ROOT/scripts/run-linux.sh"
