"""Linux desktop integration regression tests, without modifying the real user menu."""
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def test_desktop_install_requires_local_environment(tmp_path):
    home = tmp_path / "xdg"
    result = subprocess.run(
        ["bash", str(ROOT / "scripts/install-desktop.sh")],
        env={**os.environ, "XDG_DATA_HOME": str(home)},
        text=True, capture_output=True,
    )
    if not (ROOT / ".venv/bin/python").is_file():
        assert result.returncode != 0
        assert not (home / "applications/lumqenix-community.desktop").exists()


def test_desktop_entry_generated_in_isolated_home(tmp_path):
    # The installer must never write to the actual user's XDG applications.
    # A dummy executable suffices because the script only checks installation.
    import shutil
    import tempfile
    with tempfile.TemporaryDirectory(prefix="lumqenix-desktop-") as folder:
        isolated = Path(folder)
        (isolated / "scripts").mkdir()
        (isolated / ".venv/bin").mkdir(parents=True)
        shutil.copy2(ROOT / "scripts/install-desktop.sh", isolated / "scripts/install-desktop.sh")
        (isolated / ".venv/bin/python").write_text("#!/bin/sh\nexit 0\n")
        (isolated / ".venv/bin/python").chmod(0o755)
        xdg = tmp_path / "xdg"
        env = {**os.environ, "XDG_DATA_HOME": str(xdg)}
        first = subprocess.run(["bash", str(isolated / "scripts/install-desktop.sh")],
                               env=env, text=True, capture_output=True)
        assert first.returncode == 0, first.stderr
        entry = xdg / "applications/lumqenix-community.desktop"
        text = entry.read_text()
        assert text.startswith("[Desktop Entry]\n")
        assert "Type=Application\n" in text
        assert "Terminal=true\n" in text
        assert "Exec=bash " in text
        assert str(isolated / "scripts/launch-desktop.sh") in text
        second = subprocess.run(["bash", str(isolated / "scripts/install-desktop.sh")],
                                env=env, text=True, capture_output=True)
        assert second.returncode == 0, second.stderr
        assert entry.read_text() == text
        assert entry.stat().st_mode & 0o777 == 0o644
