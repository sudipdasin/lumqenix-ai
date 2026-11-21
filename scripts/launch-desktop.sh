#!/usr/bin/env bash
# Launch the installed Community application from a desktop entry.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  echo "Lumqenix is not installed. Run: bash $ROOT/scripts/install-linux.sh" >&2
  exit 1
fi
exec bash "$ROOT/scripts/run-linux.sh"
