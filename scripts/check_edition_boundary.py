"""Block proprietary paths from the Community repository (tracked files only)."""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

FORBIDDEN = (
    "proprietary/", "premium/", "private/", "commercial/", "secrets/",
    "licenses/keys/", "models/proprietary/", "backend/models/proprietary/",
    "frontend/pro/", "frontend/premium/", "backend/app/pro/",
    "backend/app/premium/",
)


def forbidden_paths(paths: list[str]) -> list[str]:
    bad = []
    for path in paths:
        clean = path.replace(chr(92), "/")
        if clean.startswith("/") or ".." in clean.split("/"):
            bad.append(path)
            continue
        if any(clean.casefold().startswith(prefix) for prefix in FORBIDDEN):
            bad.append(path)
    return bad


def tracked_files(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        check=True, capture_output=True,
    )
    return [
        item.decode("utf-8", "surrogateescape")
        for item in result.stdout.split(bytes([0])) if item
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        bad = forbidden_paths(tracked_files(args.root))
    except (OSError, subprocess.CalledProcessError) as exc:
        parser.exit(2, f"Cannot inspect tracked files: {exc}\n")
    if bad:
        print("BLOCKED: proprietary or unsafe paths tracked in community repository:")
        for path in bad:
            print(f"  {path}")
        return 1
    print("PASS: no forbidden proprietary paths tracked (history/secrets not audited)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
