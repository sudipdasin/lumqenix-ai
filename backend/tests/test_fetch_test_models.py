"""Security regression tests for pinned pretrained model downloads."""
import hashlib
from pathlib import Path

import pytest

from scripts.fetch_test_models import MAX_MODEL_BYTES, download_model, validate_model_entry


def valid_entry(data=b"model"):
    return {
        "filename": "FSRCNN_x2.pb",
        "url": "https://raw.githubusercontent.com/example/repo/commit/model.pb",
        "sha256": hashlib.sha256(data).hexdigest(),
    }


@pytest.mark.parametrize("override", [
    {"filename": "../escape.pb"},
    {"filename": "model.pb/other"},
    {"filename": "bad space.pb"},
    {"url": "http://raw.githubusercontent.com/model.pb"},
    {"url": "https://evil.example/model.pb"},
    {"url": "https://user:pass@raw.githubusercontent.com/model.pb"},
    {"sha256": "invalid"},
])
def test_manifest_rejects_untrusted_entries(override):
    entry = valid_entry()
    entry.update(override)
    with pytest.raises(ValueError):
        validate_model_entry(entry)


def test_valid_manifest_entry():
    assert validate_model_entry(valid_entry())[0] == "FSRCNN_x2.pb"


def test_download_rejects_oversize_without_writing(monkeypatch, tmp_path):
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self, size):
            assert size == MAX_MODEL_BYTES + 1
            return b"x" * size
    monkeypatch.setattr("scripts.fetch_test_models.urllib.request.urlopen", lambda *a, **k: Response())
    with pytest.raises(RuntimeError, match="size"):
        download_model(valid_entry(), tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_checksum_mismatch_does_not_replace_existing_model(monkeypatch, tmp_path):
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self, size):
            return b"untrusted"
    monkeypatch.setattr("scripts.fetch_test_models.urllib.request.urlopen", lambda *a, **k: Response())
    target = tmp_path / "FSRCNN_x2.pb"
    target.write_bytes(b"previous-good-model")
    with pytest.raises(RuntimeError, match="checksum"):
        download_model(valid_entry(), tmp_path)
    assert target.read_bytes() == b"previous-good-model"


def test_verified_model_is_atomically_written(monkeypatch, tmp_path):
    payload = b"verified-model"
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self, size):
            return payload
    monkeypatch.setattr("scripts.fetch_test_models.urllib.request.urlopen", lambda *a, **k: Response())
    target = download_model(valid_entry(payload), tmp_path)
    assert target == tmp_path / "FSRCNN_x2.pb"
    assert target.read_bytes() == payload
    assert list(tmp_path.iterdir()) == [target]
