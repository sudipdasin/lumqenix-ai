"""Reference provenance hashing must not load whole photos into memory."""
import hashlib
from pathlib import Path

from scripts.benchmark_quality_models import reference_sha256


def test_reference_sha256_streams_large_file(tmp_path, monkeypatch):
    source = tmp_path / "reference.bin"
    payload = b"lumqenix-quality-reference" * 140000
    source.write_bytes(payload)

    def forbid_read_bytes(self):
        raise AssertionError("whole-file reads are forbidden for reference provenance")

    monkeypatch.setattr(Path, "read_bytes", forbid_read_bytes)
    assert reference_sha256(source) == hashlib.sha256(payload).hexdigest()


def test_reference_sha256_empty_file(tmp_path):
    source = tmp_path / "empty.bin"
    source.touch()
    assert reference_sha256(source) == hashlib.sha256(b"").hexdigest()
