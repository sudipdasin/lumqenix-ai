"""Offline regression tests for the Community Linux .run installer."""
import importlib.util
from pathlib import Path
import stat
import subprocess
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/build-linux-installer.py"
spec = importlib.util.spec_from_file_location("build_linux_installer", SCRIPT)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


def archive(tmp_path, *, extra=(), missing=()):
    path = tmp_path / "source.zip"
    with zipfile.ZipFile(path, "w") as z:
        for name in sorted(installer.REQUIRED - set(missing)):
            z.writestr(name, "test:" + name)
        for name in extra:
            z.writestr(name, "extra")
    return path


def test_linux_installer_extracts_verified_sources(tmp_path):
    source = archive(tmp_path)
    output = tmp_path / "lumqenix.run"
    digest = installer.build(source, output, "v0.3.0-rc.5")
    assert len(digest) == 64
    assert output.stat().st_mode & stat.S_IXUSR
    assert subprocess.run(["bash", "-n", str(output)]).returncode == 0
    installed = tmp_path / "installed"
    proc = subprocess.run([str(output), "--extract-only", "--prefix", str(installed)],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert (installed / "v0.3.0-rc.5/scripts/run-linux.sh").exists()
    assert not list(installed.glob(".lumqenix-staging-*"))


def test_repeat_install_does_not_overwrite(tmp_path):
    output = tmp_path / "lumqenix.run"
    installer.build(archive(tmp_path), output, "v0.3.0-rc.5")
    prefix = tmp_path / "install"
    first = subprocess.run([str(output), "--extract-only", "--prefix", str(prefix)])
    assert first.returncode == 0
    sentinel = prefix / "v0.3.0-rc.5/sentinel.txt"
    sentinel.write_text("keep")
    second = subprocess.run([str(output), "--extract-only", "--prefix", str(prefix)],
                            capture_output=True)
    assert second.returncode != 0
    assert sentinel.read_text() == "keep"


def test_tampered_installer_rejected_before_extract(tmp_path):
    output = tmp_path / "lumqenix.run"
    installer.build(archive(tmp_path), output, "v0.3.0-rc.5")
    with output.open("ab") as stream:
        stream.write(b"modified")
    prefix = tmp_path / "install"
    result = subprocess.run([str(output), "--extract-only", "--prefix", str(prefix)],
                            capture_output=True, text=True)
    assert result.returncode != 0
    assert "checksum mismatch" in result.stderr
    assert not prefix.exists()


@pytest.mark.parametrize("bad_name", ["../escaped", "/absolute/file", "nested/../../escape", "bad\\name"])
def test_builder_rejects_path_traversal(tmp_path, bad_name):
    source = archive(tmp_path, extra=(bad_name,))
    with pytest.raises(ValueError, match="Unsafe ZIP"):
        installer.build(source, tmp_path / "installer.run", "v0.3.0-rc.5")
    assert not (tmp_path / "installer.run").exists()


def test_builder_rejects_missing_project_file(tmp_path):
    source = archive(tmp_path, missing=("LICENSE",))
    with pytest.raises(ValueError, match="Missing project"):
        installer.build(source, tmp_path / "installer.run", "v0.3.0-rc.5")


def test_builder_rejects_duplicate_member(tmp_path):
    source = archive(tmp_path)
    with pytest.warns(UserWarning), zipfile.ZipFile(source, "a") as z:
        z.writestr("LICENSE", "malicious override")
    with pytest.raises(ValueError, match="Duplicate ZIP"):
        installer.build(source, tmp_path / "installer.run", "v0.3.0-rc.5")


def test_builder_rejects_symlinks(tmp_path):
    source = archive(tmp_path)
    symlink = zipfile.ZipInfo("symlink")
    symlink.create_system = 3
    symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(source, "a") as z:
        z.writestr(symlink, "../../escape")
    with pytest.raises(ValueError, match="Symlink ZIP"):
        installer.build(source, tmp_path / "installer.run", "v0.3.0-rc.5")


def test_builder_rejects_unsupported_version(tmp_path):
    with pytest.raises(ValueError, match="Invalid release"):
        installer.build(archive(tmp_path), tmp_path / "bad.run", "v1.0.0;rm")
