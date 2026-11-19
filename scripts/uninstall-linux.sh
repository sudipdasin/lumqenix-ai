#!/usr/bin/env bash
# Remove only the local environment marked by install-linux.sh. Keep user data.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
python3 - "$ROOT" <<'PY'
import pathlib
import shutil
import sys
root = pathlib.Path(sys.argv[1])
venv = root / ".venv"
marker = venv / ".lumqenix-source-preview"
if venv.is_symlink():
    raise SystemExit("Refusing to remove symlink .venv")
if not venv.exists():
    print("No local Lumqenix environment to remove")
    raise SystemExit(0)
if not venv.is_dir() or marker.is_symlink() or not marker.is_file() or marker.read_text() != str(root) + "\n":
    raise SystemExit("Refusing to remove an environment not created by this installer")
shutil.rmtree(venv)
print("Removed local Lumqenix environment; source, models, and user data kept")
PY
