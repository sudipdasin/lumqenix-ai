#!/usr/bin/env python3
"""Build tested Community ZIP, Linux .run, Debian .deb and checksums locally.

No GitHub Actions, CircleCI, network calls or root installation are used.
Requires an existing checkout with local Python test dependencies available.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(*args, cwd=ROOT, capture=False):
    return subprocess.run(
        [str(arg) for arg in args], cwd=cwd, check=True, text=True,
        capture_output=capture,
    )


def release_version():
    source = ROOT / "backend/app/version.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    candidates = [
        stmt.value.value for stmt in tree.body
        if isinstance(stmt, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "VERSION" for t in stmt.targets)
        and isinstance(stmt.value, ast.Constant)
        and isinstance(stmt.value.value, str)
    ]
    if len(candidates) != 1 or re.fullmatch(r"0[.]3[.]0-rc[.][0-9]+", candidates[0]) is None:
        raise ValueError("Only a single, valid Community RC version may be packaged")
    return candidates[0]


def ensure_clean_checkout():
    top = Path(run("git", "rev-parse", "--show-toplevel", capture=True).stdout.strip()).resolve()
    if top != ROOT.resolve():
        raise ValueError("Use a complete Lumqenix Git checkout")
    run("git", "diff", "--quiet")
    run("git", "diff", "--cached", "--quiet")


def build(output_dir):
    for executable in ("git", "bash", "dpkg-deb", "python3"):
        if shutil.which(executable) is None:
            raise RuntimeError("Missing offline build prerequisite: " + executable)
    ensure_clean_checkout()
    version = release_version()
    tag = "v" + version
    commit = run("git", "rev-parse", "HEAD", capture=True).stdout.strip()
    name = {
        "zip": f"lumqenix-community-{tag}-source.zip",
        "run": f"lumqenix-community-{tag}-linux-installer.run",
        "deb": f"lumqenix-community-{tag}-all.deb",
        "evidence": "local-release-evidence.json",
        "checksums": "SHA256SUMS",
    }
    output_dir = Path(output_dir).expanduser().resolve()
    for filename in name.values():
        destination = output_dir / filename
        if destination.exists() or destination.is_symlink():
            raise FileExistsError("Refusing to overwrite existing bundle asset: " + str(destination))

    # Offline fail-closed gates: no pip installs, hosted CI or network access.
    run("bash", ROOT / "scripts/verify-local.sh", "all")
    run(sys.executable, ROOT / "scripts/check_edition_boundary.py", "--root", ROOT)
    run(sys.executable, ROOT / "scripts/audit_publication.py", "--repo", ROOT, "--history")

    with tempfile.TemporaryDirectory(prefix="lumqenix-offline-bundle-") as temp:
        stage = Path(temp)
        run("git", "archive", "--format=zip", "--output=" + str(stage / name["zip"]), "HEAD")
        run(sys.executable, ROOT / "scripts/build-linux-installer.py",
            "--source-zip", stage / name["zip"], "--output", stage / name["run"],
            "--version", tag)
        run(sys.executable, ROOT / "scripts/build-deb.py",
            "--source-zip", stage / name["zip"], "--output", stage / name["deb"],
            "--version", tag)

        # Inspect actual produced bundles; never run networked installation.
        run(stage / name["run"], "--extract-only", "--prefix", stage / "run-extract")
        if not (stage / "run-extract" / tag / "LICENSE").is_file():
            raise RuntimeError("Linux .run extraction did not produce a valid source tree")
        run("dpkg-deb", "--info", stage / name["deb"], capture=True)
        run("dpkg-deb", "--extract", stage / name["deb"], stage / "deb-extract")
        launcher = stage / "deb-extract/usr/bin/lumqenix-community"
        if not launcher.is_file():
            raise RuntimeError("Debian package lacks the executable launcher")
        run("bash", "-n", launcher)
        actual = run("bash", launcher, "--version", capture=True).stdout.strip()
        if actual != "Lumqenix Community " + tag:
            raise RuntimeError("Unexpected Debian launcher version")

        evidence = {
            "version": version, "source_commit": commit,
            "distribution": "Community prerelease, locally packaged",
            "github_actions_run": False, "circleci_run": False,
            "gates": ["local regression suite", "local package smoke",
                      "Community source-boundary scan", "reachable-history audit",
                      "self-extracting installer smoke", "Debian package inspection"],
            "limitations": "Not a real-model quality certification, standalone binary or physical 4GB system validation",
        }
        (stage / name["evidence"]).write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        selected = [name[key] for key in ("zip", "run", "deb", "evidence")]
        lines = [hashlib.sha256((stage / file).read_bytes()).hexdigest() + "  " + file
                 for file in selected]
        (stage / name["checksums"]).write_text("\n".join(lines) + "\n", encoding="ascii")
        for line in lines:
            expected, filename = line.split("  ", 1)
            if hashlib.sha256((stage / filename).read_bytes()).hexdigest() != expected:
                raise RuntimeError("Local output checksum mismatch: " + filename)

        output_dir.mkdir(parents=True, exist_ok=True)
        for filename in name.values():
            # Recheck before copying; do not silently replace an older bundle.
            target = output_dir / filename
            if target.exists() or target.is_symlink():
                raise FileExistsError("Output appeared while building: " + str(target))
            temporary = target.with_name(target.name + ".partial")
            try:
                with (stage / filename).open("rb") as source, temporary.open("xb") as dest:
                    shutil.copyfileobj(source, dest)
                    dest.flush()
                    os.fsync(dest.fileno())
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
        return output_dir, commit, name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    destination, commit, names = build(args.output_dir)
    print("Verified local release bundle:", destination)
    print("Git commit:", commit)
    print("Assets:", ", ".join(names.values()))


if __name__ == "__main__":
    try:
        main()
    except (OSError, subprocess.CalledProcessError, ValueError, RuntimeError) as exc:
        raise SystemExit("Offline bundle failed: " + str(exc)) from exc
