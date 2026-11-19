"""Exercise the Linux launcher as a real process, including signals and failures."""
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request

import pytest

SOURCE = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="Linux source scripts")


@pytest.fixture
def checkout(tmp_path):
    root = tmp_path / "source preview with spaces"
    (root / "scripts").mkdir(parents=True)
    (root / "backend").mkdir()
    (root / "frontend").mkdir()
    (root / "frontend" / "index.html").write_text("preview ready")
    (root / "backend" / "requirements.txt").write_text("")
    for name in ("run", "install", "uninstall"):
        shutil.copy2(SOURCE / "scripts" / f"{name}-linux.sh", root / "scripts")
    # A real HTTP child replaces only the API dependency, keeping launcher/process
    # behavior independent of optional runtime packages and model downloads.
    (root / "uvicorn.py").write_text('''
import http.server, os, sys, threading
if os.environ.get("TEST_API_FAIL"):
    raise SystemExit(7)
if os.environ.get("TEST_API_DIE"):
    threading.Timer(1, lambda: os._exit(9)).start()
port = int(sys.argv[sys.argv.index("--port") + 1])
http.server.ThreadingHTTPServer(("127.0.0.1", port), http.server.SimpleHTTPRequestHandler).serve_forever()
''')
    return root


def available():
    for port in (8000, 8080):
        with socket.socket() as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                pytest.skip(f"launcher test requires free localhost port {port}")


def launch(root, **extra):
    return subprocess.Popen(
        ["bash", str(root / "scripts/run-linux.sh")],
        env={**os.environ, "LUMQENIX_PYTHON": sys.executable, **extra},
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )


def wait_ready(process):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if process.poll() is not None:
            pytest.fail(process.communicate()[0])
        try:
            with urllib.request.urlopen("http://127.0.0.1:8080", timeout=.2) as response:
                if b"preview ready" in response.read():
                    # Let supervisor finish its readiness check.
                    time.sleep(.2)
                    return
        except OSError:
            pass
        time.sleep(.05)
    pytest.fail("launcher did not start")


def assert_ports_released():
    # TCP TIME_WAIT is permitted; a live listener is not.
    for port in (8000, 8080):
        with socket.socket() as sock:
            sock.settimeout(.2)
            assert sock.connect_ex(("127.0.0.1", port)) != 0


@pytest.mark.parametrize("signum", [signal.SIGINT, signal.SIGTERM])
def test_launch_with_spaces_and_signal_cleanup(checkout, signum):
    available()
    process = launch(checkout)
    try:
        wait_ready(process)
        process.send_signal(signum)
        output, _ = process.communicate(timeout=10)
        assert process.returncode == 128 + signum, output
        assert "Lumqenix: http://127.0.0.1:8080" in output
        assert_ports_released()
    finally:
        if process.poll() is None:
            process.terminate()
            process.communicate(timeout=10)


@pytest.mark.parametrize("port", [8000, 8080])
def test_occupied_port_preserves_existing_listener(checkout, port):
    available()
    with socket.socket() as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", port))
        listener.listen()
        process = launch(checkout)
        output, _ = process.communicate(timeout=10)
        assert process.returncode == 1
        assert f"Local port {port} unavailable" in output
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            pass
    assert_ports_released()


@pytest.mark.parametrize("failure", ["TEST_API_FAIL", "TEST_API_DIE"])
def test_child_failure_stops_other_service(checkout, failure):
    available()
    process = launch(checkout, **{failure: "1"})
    try:
        output, _ = process.communicate(timeout=10)
        assert process.returncode == 1, output
        assert "Lumqenix launcher:" in output
        assert_ports_released()
    finally:
        if process.poll() is None:
            process.terminate()
            process.communicate(timeout=10)


@pytest.mark.parametrize("script", ["install", "uninstall"])
@pytest.mark.parametrize("kind", ["unmarked", "symlink", "marker_symlink"])
def test_environment_safety(checkout, tmp_path, script, kind):
    target = tmp_path / "user environment"
    target.mkdir()
    precious = target / "keep.txt"
    precious.write_text("keep")
    venv = checkout / ".venv"
    if kind == "symlink":
        venv.symlink_to(target, target_is_directory=True)
    else:
        venv.mkdir()
        if kind == "marker_symlink":
            marker_target = tmp_path / "forged-marker"
            marker_target.write_text(str(checkout.resolve()) + "\n")
            (venv / ".lumqenix-source-preview").symlink_to(marker_target)
    result = subprocess.run(["bash", str(checkout / "scripts" / f"{script}-linux.sh")], capture_output=True, text=True)
    assert result.returncode != 0
    assert "Refusing" in result.stderr
    assert precious.read_text() == "keep"
    assert venv.exists()


def test_install_repeat_and_uninstall_keeps_source(checkout):
    # Empty requirements exercise real venv creation/reuse without network access.
    env = {**os.environ, "PIP_NO_INDEX": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1"}
    install = ["bash", str(checkout / "scripts/install-linux.sh")]
    for _ in range(2):
        result = subprocess.run(install, env=env, capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, result.stdout + result.stderr
    marker = checkout / ".venv/.lumqenix-source-preview"
    assert marker.read_text() == str(checkout.resolve()) + "\n"
    keep = checkout / "user-model.bin"
    keep.write_bytes(b"model")
    uninstall = ["bash", str(checkout / "scripts/uninstall-linux.sh")]
    for _ in range(2):
        result = subprocess.run(uninstall, capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, result.stderr
    assert not (checkout / ".venv").exists()
    assert keep.read_bytes() == b"model"
    assert (checkout / "backend/requirements.txt").exists()
