"""Pre-publication audit for tracked and reachable-history Git blobs.

This is a high-confidence *screen*, not proof that a repository contains no
secrets/PII/licensing problems. It does not inspect unreachable Git objects,
external artifacts, third-party licensing, or generated downloads.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

MAX_BLOB_BYTES = 2 * 1024 * 1024
PATTERNS = (
    ("private-key header", re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("GitHub access token", re.compile(rb"\b(?:gh[pousr]_[a-zA-Z0-9]{36,}|github_pat_[a-zA-Z0-9_]{60,})\b")),
    ("AWS access key", re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("Stripe secret key", re.compile(rb"\bsk_live_[a-zA-Z0-9]{20,}\b")),
)
BLOCKED_SUFFIXES = (".pem", ".p12", ".pfx", ".key")
BLOCKED_NAMES = {"id_rsa", "id_ed25519", ".env", ".env.local", "credentials.json", "service-account.json"}


def git(repo: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True, timeout=60).stdout


def blob_references(repo: Path, history: bool):
    if history:
        lines = git(repo, "rev-list", "--objects", "--all").splitlines()
        for line in lines:
            parts = line.split(b" ", 1)
            if len(parts) == 2:
                yield parts[0].decode("ascii"), parts[1].decode("utf-8", "replace")
    else:
        for row in git(repo, "ls-files", "--stage", "-z").split(b"\0"):
            if row:
                metadata, path = row.split(b"\t", 1)
                fields = metadata.split()
                if fields[2] == b"0":
                    yield fields[1].decode("ascii"), path.decode("utf-8", "replace")


def scan_blob(path: str, data: bytes) -> list[str]:
    filename = Path(path).name.lower()
    reasons = []
    if filename in BLOCKED_NAMES or filename.startswith(".env.") or filename.endswith(BLOCKED_SUFFIXES):
        reasons.append("sensitive filename (manual review required)")
    for label, pattern in PATTERNS:
        if pattern.search(data):
            reasons.append(label)
    return reasons


def audit(repo: Path, history: bool = False) -> dict[str, object]:
    scanned = 0
    results = set()
    seen = set()
    for oid, path in blob_references(repo, history):
        # File names can be ambiguous if the same Git object appears at multiple paths.
        kind = git(repo, "cat-file", "-t", oid).decode().strip()
        if kind != "blob":
            continue
        identity = (oid, path)
        if identity in seen:
            continue
        seen.add(identity)
        scanned += 1
        size = int(git(repo, "cat-file", "-s", oid).decode())
        if size > MAX_BLOB_BYTES:
            results.add((path, "blob over 2 MiB: manual inspection required"))
            continue
        for finding in scan_blob(path, git(repo, "cat-file", "blob", oid)):
            results.add((path, finding))
    return {"scope": "reachable-history" if history else "tracked-current",
            "blobs_checked": scanned,
            "findings": [{"path": p, "reason": reason} for p, reason in sorted(results)],
            "limitations": "Not a full secret, PII, copyright, or external-artifact audit"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--history", action="store_true")
    args = parser.parse_args()
    try:
        report = audit(args.repo, history=args.history)
    except (OSError, ValueError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        parser.exit(2, f"Publication audit could not complete: {type(exc).__name__}\n")
    print(json.dumps(report, indent=2))
    return 1 if report["findings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
