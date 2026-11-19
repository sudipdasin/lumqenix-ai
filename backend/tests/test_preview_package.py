"""Contract tests for deterministic, source-only preview packaging."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[2]
BUILDER_PATH = REPO / "scripts" / "build_preview.py"
SPEC = importlib.util.spec_from_file_location("build_preview", BUILDER_PATH)
assert SPEC and SPEC.loader
builder = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = builder
SPEC.loader.exec_module(builder)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, stdout=subprocess.PIPE)


def _fixture_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "source"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "preview-test@example.invalid")
    _git(repo, "config", "user.name", "Preview Test")
    files = {
        "backend/app/version.py": 'VERSION = "0.3.0-dev.8"\n',
        "README.md": "Community preview source\n",
        "LICENSE": "License text\n",
        "scripts/run.sh": "#!/bin/sh\necho hi\n",
        "backend/tests/test_sample.py": "def test_example():\n    assert True\n",
        "benchmarks/CPU.json": '{"case": "cpu"}\n',
    }
    for name, text in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    (repo / "scripts/run.sh").chmod(0o755)
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "fixture")
    return repo


def _checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_build_is_deterministic_and_emits_checksum_and_provenance(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    first = builder.build_preview(repo, tmp_path / "out-one")
    second = builder.build_preview(repo, tmp_path / "out-two")

    assert first[0].read_bytes() == second[0].read_bytes()
    assert first[1].read_text() == second[1].read_text()
    assert first[2].read_text() == second[2].read_text()
    provenance = json.loads(first[2].read_text())
    assert provenance["version"] == "0.3.0-dev.8"
    assert provenance["archive_sha256"] == _checksum(first[0])
    assert first[1].read_text() == f"{_checksum(first[0])}  {first[0].name}\n"
    with zipfile.ZipFile(first[0]) as archive:
        script = archive.getinfo("lumqenix-community-0.3.0-dev.8/scripts/run.sh")
        assert (script.external_attr >> 16) & 0o111


def test_manifest_integrity_and_checksum_verification(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    archive, _sums, _provenance = builder.build_preview(repo, tmp_path / "dist")
    manifest = builder.verify_preview(archive, _checksum(archive))
    assert manifest["source_commit"] == subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()
    assert {entry["path"] for entry in manifest["files"]} >= {
        "LICENSE", "README.md", "backend/app/version.py", "benchmarks/CPU.json",
    }
    with pytest.raises(builder.PreviewError, match="does not match"):
        builder.verify_preview(archive, "0" * 64)


@pytest.mark.parametrize("bad_path", ["keys/deploy.pem", ".env.production", "weights/model.onnx", "weights/model.pb"])
def test_builder_rejects_unsafe_or_sensitive_tracked_paths(tmp_path: Path, bad_path: str) -> None:
    repo = _fixture_repo(tmp_path)
    bad = repo / bad_path
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text("not for release", encoding="utf-8")
    _git(repo, "add", "-f", bad_path)
    _git(repo, "commit", "-qm", "unsafe tracked source")
    with pytest.raises(builder.PreviewError):
        builder.build_preview(repo, tmp_path / "dist")


@pytest.mark.parametrize("bad_path", ["../escape", "/absolute", "a\\b"])
def test_builder_path_policy_rejects_unsafe_names(bad_path: str) -> None:
    with pytest.raises(builder.PreviewError, match="unsafe tracked path"):
        builder._validate_path(bad_path)


def test_builder_rejects_tracked_symlinks(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    (repo / "unsafe-link").symlink_to("README.md")
    _git(repo, "add", "unsafe-link")
    _git(repo, "commit", "-qm", "tracked symlink")
    with pytest.raises(builder.PreviewError, match="non-regular"):
        builder.build_preview(repo, tmp_path / "dist")


def test_builder_reads_head_not_uncommitted_worktree_and_rejects_bad_version(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    (repo / "README.md").write_text("uncommitted mutation\n", encoding="utf-8")
    archive, _sums, _provenance = builder.build_preview(repo, tmp_path / "dist")
    with zipfile.ZipFile(archive) as zf:
        assert zf.read("lumqenix-community-0.3.0-dev.8/README.md") == b"Community preview source\n"

    (repo / "backend/app/version.py").write_text('VERSION = make_version()\n', encoding="utf-8")
    _git(repo, "add", "backend/app/version.py")
    _git(repo, "commit", "-qm", "invalid version declaration")
    with pytest.raises(builder.PreviewError, match="literal string"):
        builder.build_preview(repo, tmp_path / "invalid")


def test_verifier_rejects_unsafe_and_unmanifested_archive_members(tmp_path: Path) -> None:
    malicious = tmp_path / "malicious.zip"
    with zipfile.ZipFile(malicious, "w") as zf:
        zf.writestr("lumqenix-community-1.2/../escape.txt", "escape")
    with pytest.raises(builder.PreviewError, match="unsafe"):
        builder.verify_preview(malicious, _checksum(malicious))

    symlink = tmp_path / "symlink.zip"
    with zipfile.ZipFile(symlink, "w") as zf:
        info = zipfile.ZipInfo("lumqenix-community-1.2/source.py")
        info.create_system = 3
        info.external_attr = (0o120777 << 16)
        zf.writestr(info, "../../outside")
    with pytest.raises(builder.PreviewError, match="non-regular"):
        builder.verify_preview(symlink, _checksum(symlink))


def test_verifier_checks_manifest_hashes_and_exact_file_set(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    original, _sums, _provenance = builder.build_preview(repo, tmp_path / "dist")
    altered = tmp_path / "altered.zip"
    with zipfile.ZipFile(original) as source, zipfile.ZipFile(altered, "w", zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            data = source.read(info.filename)
            if info.filename.endswith("README.md"):
                data = b"tampered\n"
            target.writestr(info, data)
    with pytest.raises(builder.PreviewError, match="integrity check failed"):
        builder.verify_preview(altered, _checksum(altered))
