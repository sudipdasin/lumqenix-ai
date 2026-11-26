"""Local-only release builder contracts: no CI and fail-closed packaging."""
import importlib.util
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/build_offline_release.py"
spec = importlib.util.spec_from_file_location("lumqenix_offline_bundle", SCRIPT)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


@pytest.mark.parametrize("version,valid", [
    ("0.3.0-rc.6", True),
    ("0.3.0-rc.12", True),
    ("1.0.0", False),
    ("0.3.0-rc.6;rm", False),
    ("0.3.0-rc.6\nOTHER", False),
])
def test_release_version_is_strict(tmp_path, monkeypatch, version, valid):
    (tmp_path / "backend/app").mkdir(parents=True)
    (tmp_path / "backend/app/version.py").write_text(f"VERSION = {version!r}\n")
    monkeypatch.setattr(builder, "ROOT", tmp_path)
    if valid:
        assert builder.release_version() == version
    else:
        with pytest.raises(ValueError):
            builder.release_version()


def test_existing_bundle_cannot_be_overwritten(tmp_path, monkeypatch):
    monkeypatch.setattr(builder, "ROOT", tmp_path)
    monkeypatch.setattr(builder, "ensure_clean_checkout", lambda: None)
    monkeypatch.setattr(builder, "release_version", lambda: "0.3.0-rc.6")
    monkeypatch.setattr(builder, "run", lambda *args, **kwargs: SimpleNamespace(stdout="a" * 40))
    destination = tmp_path / "dist"
    destination.mkdir()
    old = destination / "lumqenix-community-v0.3.0-rc.6-all.deb"
    old.write_bytes(b"preserve old package")
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        builder.build(destination)
    assert old.read_bytes() == b"preserve old package"


def test_missing_packaging_prerequisite_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(builder.shutil, "which",
                        lambda executable: None if executable == "dpkg-deb" else "/usr/bin/" + executable)
    with pytest.raises(RuntimeError, match="dpkg-deb"):
        builder.build(tmp_path)


def test_dirty_checkout_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(builder, "ROOT", tmp_path)
    calls = []
    def fake_run(*args, **kwargs):
        calls.append(args)
        if args[1:] == ("rev-parse", "--show-toplevel"):
            return SimpleNamespace(stdout=str(tmp_path) + "\n")
        if args[1:] == ("diff", "--quiet"):
            raise subprocess.CalledProcessError(1, args)
        return SimpleNamespace(stdout="")
    monkeypatch.setattr(builder, "run", fake_run)
    with pytest.raises(subprocess.CalledProcessError):
        builder.ensure_clean_checkout()
    assert ("git", "diff", "--quiet") in calls


def test_builder_has_no_remote_ci_dispatch_calls():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "verify-local.sh" in source
    assert "check_edition_boundary.py" in source
    assert "audit_publication.py" in source
    assert "github_actions_run" in source and "circleci_run" in source
    assert "gh workflow run" not in source
    assert "circleci trigger" not in source
