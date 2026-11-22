#!/usr/bin/env python3
"""Build a reproducible-ish no-maintainer-script Debian source-runtime package.

The package is architecture-independent Python/source (Architecture: all).
First launch installs Python wheels into a per-user virtualenv; it never runs
pip as root or during dpkg's installation/removal transactions.
"""
import argparse
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import tempfile
import zipfile

MAX_UNCOMPRESSED = 64 * 1024 * 1024
REQUIRED = {
    "LICENSE",
    "backend/app/main.py",
    "backend/app/version.py",
    "backend/requirements.txt",
    "frontend/index.html",
    "scripts/run-linux.sh",
    "scripts/run-deb.sh",
}


def validate_zip(source, expected_version):
    with zipfile.ZipFile(source) as archive:
        names = set()
        total = 0
        for entry in archive.infolist():
            name = entry.filename
            parts = PurePosixPath(name).parts
            if not name or name.startswith("/") or name.startswith("~") or ".." in parts or "\\" in name:
                raise ValueError("Unsafe archive path: " + name)
            if name in names:
                raise ValueError("Duplicate ZIP member: " + name)
            names.add(name)
            mode = entry.external_attr >> 16
            if stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR)):
                raise ValueError("Unsupported ZIP member type: " + name)
            total += entry.file_size
            if total > MAX_UNCOMPRESSED:
                raise ValueError("Archive expands beyond package limit")
        if not REQUIRED.issubset(names):
            raise ValueError("Incomplete source archive: " + ", ".join(sorted(REQUIRED - names)))
        if archive.testzip() is not None:
            raise ValueError("Corrupted source archive")
        reported_version = archive.read("backend/app/version.py").decode("utf-8")
        if f'VERSION = "{expected_version}"' not in reported_version:
            raise ValueError("Source archive version mismatch")


def build(source_zip, output, version):
    if not version.startswith("v0.3.0-rc.") or not version[10:].isdigit():
        raise ValueError("Unsupported release version")
    version_string = version[1:]
    dpkg_version = "0.3.0~rc" + version_string.rsplit(".", 1)[1] + "-1"
    validate_zip(source_zip, version_string)
    if shutil.which("dpkg-deb") is None:
        raise RuntimeError("dpkg-deb is required on this build runner")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="lumqenix-deb-") as staging_dir:
        root = Path(staging_dir) / "pkg"
        app = root / "opt/lumqenix-community"
        app.mkdir(parents=True)
        with zipfile.ZipFile(source_zip) as archive:
            archive.extractall(app)
        # No preinst/postinst/prerm/postrm: dpkg never executes arbitrary network setup.
        control = root / "DEBIAN/control"
        control.parent.mkdir(parents=True)
        control.write_text(
            "Package: lumqenix-community\n"
            f"Version: {dpkg_version}\n"
            "Architecture: all\n"
            "Maintainer: Lumqenix Community contributors <noreply@github.com>\n"
            "Section: graphics\nPriority: optional\n"
            "Depends: python3 (>= 3.10), python3-venv, python3-pip, ffmpeg, util-linux\n"
            "Homepage: https://github.com/sudipdasin/lumqenix-ai\n"
            "Description: Local CPU-first image and video enhancement studio (beta)\n"
            " Lumqenix Community ships a local browser interface and processing API.\n"
            " Python wheels install into the user's own virtualenv on first launch.\n"
            " Internet may be required once; no Python installation runs under dpkg.\n"
            " This is an experimental release candidate, not a standalone binary.\n",
            encoding="utf-8",
        )
        binary = root / "usr/bin/lumqenix-community"
        binary.parent.mkdir(parents=True, exist_ok=True)
        launcher = (app / "scripts/run-deb.sh").read_text(encoding="utf-8")
        if launcher.count("__LUMQENIX_VERSION__") != 1:
            raise ValueError("Unexpected Debian launcher version placeholder")
        binary.write_text(launcher.replace("__LUMQENIX_VERSION__", version), encoding="utf-8")
        binary.chmod(0o755)
        desktop = root / "usr/share/applications/lumqenix-community.desktop"
        desktop.parent.mkdir(parents=True, exist_ok=True)
        desktop.write_text(
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Version=1.0\n"
            "Name=Lumqenix Community\n"
            "Comment=Local CPU-first image and video enhancement studio\n"
            "Exec=lumqenix-community\n"
            "TryExec=lumqenix-community\n"
            "Icon=applications-graphics\n"
            "Terminal=true\n"
            "Categories=Graphics;AudioVideo;\n"
            "StartupNotify=false\n",
            encoding="utf-8",
        )
        doc = root / "usr/share/doc/lumqenix-community"
        doc.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(app / "LICENSE", doc / "copyright")
        # Sanitize permissions because source ZIP metadata can vary by platform.
        for path in root.rglob("*"):
            if path.is_file():
                path.chmod(0o755 if path == binary else 0o644)
            elif path.is_dir():
                path.chmod(0o755)
        temp_deb = Path(staging_dir) / output.name
        subprocess.run(
            ["dpkg-deb", "--root-owner-group", "--build", str(root), str(temp_deb)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if not temp_deb.is_file() or temp_deb.stat().st_size == 0:
            raise RuntimeError("Debian package was not created")
        temp_deb.replace(output)
    return dpkg_version


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-zip", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    print("Built Debian package:", args.output, "version:", build(args.source_zip, args.output, args.version))


if __name__ == "__main__":
    main()
