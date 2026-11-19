"""Publication scan must detect secrets even after deletion from current tree."""
from pathlib import Path
import importlib.util
import subprocess

SCAN = Path(__file__).resolve().parents[2] / "scripts" / "audit_publication.py"
spec = importlib.util.spec_from_file_location("audit_publication", SCAN)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_recognizes_token_and_private_key_without_printing_values():
    key = b"-----BEGIN " + b"RSA PRIVATE KEY-----"
    token = b"ghp_" + b"x" * 36
    findings = audit.scan_blob("src/config.py", key + b"\n" + token)
    assert "private-key header" in findings
    assert "GitHub access token" in findings
    assert "x" * 36 not in repr(findings)


def test_detects_sensitive_file_names():
    assert audit.scan_blob("configs/.env.production", b"")
    assert audit.scan_blob("keys/id_ed25519", b"")
    assert audit.scan_blob("data/server.key", b"")
    assert not audit.scan_blob("frontend/index.html", b"<html>safe</html>")


def test_history_catches_secret_removed_in_later_commit(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    def cmd(*args):
        return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
    cmd("init", "-q")
    cmd("config", "user.email", "test@example.invalid")
    cmd("config", "user.name", "Test")
    (repo / "config.txt").write_bytes(b"ghp_" + b"x" * 36)
    cmd("add", "config.txt")
    cmd("commit", "-qm", "add")
    (repo / "config.txt").write_text("clean")
    cmd("add", "config.txt")
    cmd("commit", "-qm", "remove")
    assert audit.audit(repo, history=False)["findings"] == []
    history = audit.audit(repo, history=True)
    assert any(x["reason"] == "GitHub access token" for x in history["findings"])
    assert not any("ghp_" in str(x) for x in history["findings"])
