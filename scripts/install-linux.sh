#!/usr/bin/env bash
# Install the Linux source preview locally; no root or model downloads.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
command -v python3 >/dev/null || { echo "Python 3.10+ is required" >&2; exit 1; }
python3 - "$ROOT" <<'PY'
import pathlib
import sys
if sys.version_info < (3, 10):
    raise SystemExit("Lumqenix requires Python 3.10+")
root = pathlib.Path(sys.argv[1])
venv = root / ".venv"
marker = venv / ".lumqenix-source-preview"
if venv.is_symlink():
    raise SystemExit("Refusing symlink .venv; choose a checkout without an existing environment")
if venv.exists():
    if not venv.is_dir() or marker.is_symlink() or not marker.is_file() or marker.read_text() != str(root) + "\n":
        raise SystemExit("Refusing to overwrite an environment not created by this installer")
else:
    venv.mkdir()
    marker.write_text(str(root) + "\n")
PY
python3 -m venv "$ROOT/.venv"
"$ROOT/.venv/bin/python" -m pip install -r "$ROOT/backend/requirements.txt"
"$ROOT/.venv/bin/python" -m pip check
command -v ffmpeg >/dev/null || echo "Note: FFmpeg is missing; video enhancement will be unavailable."
command -v ffprobe >/dev/null || echo "Note: ffprobe is missing; video enhancement will be unavailable."
printf 'Installed Lumqenix locally. Launch with: bash "%s/scripts/run-linux.sh"\n' "$ROOT"
