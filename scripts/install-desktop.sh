#!/usr/bin/env bash
# Install a per-user Linux desktop menu entry without root privileges.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APPLICATIONS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
DEST="$APPLICATIONS/lumqenix-community.desktop"
[[ -x "$ROOT/.venv/bin/python" ]] || { echo "Install Lumqenix first: bash scripts/install-linux.sh" >&2; exit 1; }
[[ "$ROOT" != *$'\n'* ]] || { echo "Unsupported installation path" >&2; exit 1; }
mkdir -p "$APPLICATIONS"
TMP="$(mktemp "$APPLICATIONS/.lumqenix.XXXXXXXX")"
trap 'rm -f "$TMP"' EXIT
# Desktop entry values must escape backslashes, double quotes and dollar signs.
python3 - "$ROOT" "$TMP" <<'PY'
from pathlib import Path
import sys
root = sys.argv[1]
def quote(value):
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"').replace('$', '\\$').replace('`', '\\`') + '"'
entry = (
    "[Desktop Entry]\nType=Application\nVersion=1.0\n"
    "Name=Lumqenix Community\nComment=Local image and video enhancement studio\n"
    "Categories=Graphics;Video;\nTerminal=true\n"
    "Exec=" + quote("bash " + root + "/scripts/launch-desktop.sh") + "\n"
    "Path=" + root.replace('\\', '\\\\') + "\n"
)
Path(sys.argv[2]).write_text(entry, encoding="utf-8")
PY
chmod 0644 "$TMP"
mv -f "$TMP" "$DEST"
echo "Installed desktop menu shortcut: $DEST"
