#!/usr/bin/env bash
# Remove only Lumqenix's per-user desktop menu shortcut.
set -Eeuo pipefail
APPLICATIONS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
DEST="$APPLICATIONS/lumqenix-community.desktop"
if [[ -L "$DEST" ]]; then
  echo "Refusing to remove symlinked desktop entry: $DEST" >&2
  exit 1
fi
if [[ -f "$DEST" ]]; then
  grep -q '^Name=Lumqenix Community$' "$DEST" || {
    echo "Refusing to remove an unrecognized desktop entry: $DEST" >&2
    exit 1
  }
  rm -- "$DEST"
  echo "Removed Lumqenix desktop shortcut"
else
  echo "No Lumqenix desktop shortcut is installed"
fi
