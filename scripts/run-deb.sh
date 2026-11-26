#!/usr/bin/env bash
# Entry point for Debian/Ubuntu packages. No pip invocation runs as root.
set -Eeuo pipefail
APP_ROOT="/opt/lumqenix-community"
VERSION="__LUMQENIX_VERSION__"
umask 077

case "${1:-}" in
  --version) printf 'Lumqenix Community %s\n' "$VERSION"; exit 0 ;;
  --help|-h)
    printf 'Usage: lumqenix-community [--version|--doctor|--install-deps|--help]\n'
    printf 'Launches the locally hosted interface at http://127.0.0.1:8080\n'
    exit 0 ;;
esac

# Installing Python packages as root would defeat the rootless package design.
if (( EUID == 0 )); then
  echo "Refusing privileged launch. Run lumqenix-community without sudo." >&2
  exit 1
fi

command -v python3 >/dev/null || { echo "Python 3.10+ required" >&2; exit 1; }
python3 - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit("Lumqenix requires Python 3.10+")
PY

DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/lumqenix-community"
VENV="$DATA_DIR/venv-$VERSION"
READY="$VENV/.lumqenix-ready"
REQUIREMENTS="$APP_ROOT/backend/requirements.txt"
if [[ "${1:-}" == "--doctor" ]]; then
  printf 'Lumqenix Community %s\n' "$VERSION"
  test -r "$REQUIREMENTS" || { echo "Packaged application files missing" >&2; exit 1; }
  for command in ffmpeg ffprobe flock; do
    if command -v "$command" >/dev/null; then
      printf '%s: available\n' "$command"
    else
      printf '%s: missing\n' "$command"
    fi
  done
  if [[ -f "$READY" ]]; then echo 'Python environment: initialized'; else echo 'Python environment: needs setup'; fi
  exit 0
fi
if [[ -n "${1:-}" && "$1" != "--install-deps" ]]; then
  echo "Unexpected argument: $1" >&2
  exit 2
fi
[[ -r "$REQUIREMENTS" ]] || { echo "Missing installed application files: $REQUIREMENTS" >&2; exit 1; }
command -v flock >/dev/null || { echo "flock (util-linux) required" >&2; exit 1; }
mkdir -p "$DATA_DIR"
exec 9>"$DATA_DIR/.install.lock"
flock -w 180 9 || { echo 'Python environment is being installed by another process' >&2; exit 1; }
if [[ ! -x "$VENV/bin/python" || ! -f "$READY" ]]; then
  echo 'Setting up Lumqenix Python packages in your home directory (internet may be required)...'
  python3 -m venv "$VENV"
  "$VENV/bin/python" -m pip install --disable-pip-version-check -r "$REQUIREMENTS"
  "$VENV/bin/python" -m pip check
  touch "$READY"
fi
flock -u 9
exec 9>&-
if [[ "${1:-}" == "--install-deps" ]]; then
  echo 'Lumqenix Python dependencies installed.'
  exit 0
fi
exec env LUMQENIX_PYTHON="$VENV/bin/python" bash "$APP_ROOT/scripts/run-linux.sh"
