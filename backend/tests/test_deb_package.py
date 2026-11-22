"""Debian source-package build and safety regressions (no network or root needed)."""
import importlib.util
from pathlib import Path
import shutil
import stat
import subprocess
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/build-deb.py"
spec = importlib.util.spec_from_file_location("build_deb", SCRIPT)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


@pytest.fixture
def source_zip(tmp_path):
    zip_path = tmp_path / "community.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        for name in sorted(builder.REQUIRED):
            data = (
                'VERSION = "0.3.0-rc.6"\n'
                if name == "backend/app/version.py" else
                '#!/usr/bin/env bash\nVERSION="__LUMQENIX_VERSION__"\nif [[ "${1:-}" == "--version" ]]; then echo "Lumqenix Community $VERSION"; fi\n'
                if name == "scripts/run-deb.sh" else
                "# synthetic test fixture\n"
            )
            archive.writestr(name, data)
    return zip_path


def test_build_deb_has_valid_control_and_expected_paths(source_zip, tmp_path):
    if shutil.which("dpkg-deb") is None:
        pytest.skip("dpkg-deb not installed on this host")
    package = tmp_path / "lumqenix-community_0.3.0~rc6-1_all.deb"
    assert builder.build(source_zip, package, "v0.3.0-rc.6") == "0.3.0~rc6-1"
    assert package.stat().st_size > 0
    info = subprocess.check_output(["dpkg-deb", "--info", str(package)], text=True)
    assert "Package: lumqenix-community" in info
    assert "Version: 0.3.0~rc6-1" in info
    assert "Architecture: all" in info
    assert "Depends:" in info and "python3-venv" in info
    unpack = tmp_path / "unpack"
    subprocess.run(["dpkg-deb", "--extract", str(package), str(unpack)], check=True)
    binary = unpack / "usr/bin/lumqenix-community"
    assert binary.is_file() and binary.stat().st_mode & stat.S_IXUSR
    assert "v0.3.0-rc.6" in binary.read_text()
    assert "__LUMQENIX_VERSION__" not in binary.read_text()
    assert (unpack / "usr/share/applications/lumqenix-community.desktop").is_file()
    assert (unpack / "opt/lumqenix-community/backend/requirements.txt").is_file()
    assert (unpack / "usr/share/doc/lumqenix-community/copyright").is_file()
    result = subprocess.run(["bash", str(binary), "--version"], capture_output=True, text=True)
    assert result.returncode == 0 and "v0.3.0-rc.6" in result.stdout
    assert subprocess.run(["bash", "-n", str(binary)]).returncode == 0


@pytest.mark.parametrize("bad_name", ["../escape", "/etc/passwd", "foo/../../escape", "foo\\bad"])
def test_rejects_unsafe_zip_member(source_zip, tmp_path, bad_name):
    with zipfile.ZipFile(source_zip, "a") as archive:
        archive.writestr(bad_name, b"bad")
    with pytest.raises(ValueError, match="Unsafe archive"):
        builder.build(source_zip, tmp_path / "unsafe.deb", "v0.3.0-rc.6")
    assert not (tmp_path / "unsafe.deb").exists()


def test_rejects_wrong_version(source_zip, tmp_path):
    with pytest.raises(ValueError, match="version mismatch"):
        builder.build(source_zip, tmp_path / "wrong.deb", "v0.3.0-rc.7")


def test_rejects_duplicate_members(source_zip, tmp_path):
    with pytest.warns(UserWarning), zipfile.ZipFile(source_zip, "a") as archive:
        archive.writestr("LICENSE", "overridden")
    with pytest.raises(ValueError, match="Duplicate"):
        builder.build(source_zip, tmp_path / "duplicated.deb", "v0.3.0-rc.6")


def test_rejects_zip_symlinks(source_zip, tmp_path):
    member = zipfile.ZipInfo("evil-link")
    member.create_system = 3
    member.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(source_zip, "a") as archive:
        archive.writestr(member, "/etc/shadow")
    with pytest.raises(ValueError, match="Unsupported"):
        builder.build(source_zip, tmp_path / "symlink.deb", "v0.3.0-rc.6")


def test_bad_version_fails_before_writing(source_zip, tmp_path):
    with pytest.raises(ValueError, match="Unsupported"):
        builder.build(source_zip, tmp_path / "bad.deb", "v1.0.0")
    assert not (tmp_path / "bad.deb").exists()
