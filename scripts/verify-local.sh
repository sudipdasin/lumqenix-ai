#!/usr/bin/env bash
# Zero-CI, zero-network local checks for Lumqenix Community.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-quick}"
case "$MODE" in quick|tests|package|all) ;; *) echo "Usage: bash scripts/verify-local.sh [quick|tests|package|all]" >&2; exit 2 ;; esac
PY="$ROOT/.venv/bin/python"
[[ -x "$PY" ]] || PY="$(command -v python3 || true)"
[[ -n "$PY" && -x "$PY" ]] || { echo 'Python 3 required' >&2; exit 1; }
"$PY" - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit('Python 3.10+ required')
PY
quick() {
  echo 'Checking shell syntax, Python compilation and release source...'
  while IFS= read -r -d '' path; do bash -n "$path"; done < <(find "$ROOT/scripts" -maxdepth 1 -name '*.sh' -print0)
  "$PY" -m compileall -q "$ROOT/backend/app" "$ROOT/backend/scripts" "$ROOT/backend/tests" "$ROOT/scripts"
  test -s "$ROOT/LICENSE"
  test -s "$ROOT/backend/requirements.txt"
  test -s "$ROOT/frontend/index.html"
  if command -v node >/dev/null; then
    "$PY" - "$ROOT/frontend/index.html" <<'PY' | node --check
import pathlib, sys
text = pathlib.Path(sys.argv[1]).read_text(encoding='utf-8')
if '<script>' not in text or '</script>' not in text:
    raise SystemExit('Frontend inline JavaScript missing')
print(text.split('<script>',1)[1].split('</script>',1)[0])
PY
  else
    echo 'Note: Node.js not installed; frontend syntax check skipped'
  fi
  echo 'Quick local checks passed.'
}
tests() {
  echo 'Running regression tests with existing local dependencies (no pip/network)...'
  (cd "$ROOT/backend" && "$PY" -m pytest -q tests)
}
package() {
  echo 'Building and inspecting local Linux packages (no root/network)...'
  command -v dpkg-deb >/dev/null || { echo 'dpkg-deb not found' >&2; exit 1; }
  command -v git >/dev/null || { echo 'git not found' >&2; exit 1; }
  VERSION="$("$PY" - "$ROOT/backend/app/version.py" <<'PY'
import ast, pathlib, sys
mod=ast.parse(pathlib.Path(sys.argv[1]).read_text())
vals=[node.value.value for node in mod.body if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='VERSION' for t in node.targets) and isinstance(node.value,ast.Constant) and isinstance(node.value.value,str)]
if len(vals)!=1: raise SystemExit('Unable to determine release version')
print(vals[0])
PY
)"
  TEMP="$(mktemp -d -t lumqenix-local-XXXXXX)"
  trap 'rm -rf -- "$TEMP"' RETURN
  git -C "$ROOT" archive --format=zip --output="$TEMP/source.zip" HEAD
  test -s "$TEMP/source.zip"
  "$PY" "$ROOT/scripts/build-deb.py" --source-zip "$TEMP/source.zip" --output "$TEMP/lumqenix-community.deb" --version "v$VERSION"
  dpkg-deb --info "$TEMP/lumqenix-community.deb"
  dpkg-deb --extract "$TEMP/lumqenix-community.deb" "$TEMP/extracted"
  test -s "$TEMP/extracted/usr/bin/lumqenix-community"
  test -s "$TEMP/extracted/usr/share/applications/lumqenix-community.desktop"
  bash -n "$TEMP/extracted/usr/bin/lumqenix-community"
  bash "$TEMP/extracted/usr/bin/lumqenix-community" --version | grep -F "v$VERSION"
  sha256sum "$TEMP/lumqenix-community.deb"
  echo 'Debian package layout and launcher checks passed (no system installation).'
}
case "$MODE" in
  quick) quick ;;
  tests) quick; tests ;;
  package) quick; package ;;
  all) quick; tests; package ;;
esac
