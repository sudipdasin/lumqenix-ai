"""Ensure benchmark output evidence is fresh for each worker invocation."""
import sys
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import benchmark_models


def test_stale_output_cannot_validate_new_worker(tmp_path, monkeypatch):
    source = tmp_path / "source.png"
    Image.new("RGB", (12, 10), "red").save(source)
    output_dir = tmp_path / "results"
    output_dir.mkdir()
    stale = output_dir / "fsrcnn-2x.png"
    Image.new("RGB", (24, 20), "blue").save(stale)
    model = tmp_path / "test.pb"
    model.write_bytes(b"test fixture, not a real model")
    monkeypatch.setenv("LUMQENIX_FSRCNN_MODEL", str(model))
    monkeypatch.delenv("LUMQENIX_ESPCN_MODEL", raising=False)

    def fake_worker(*args, **kwargs):
        assert not stale.exists()
        return SimpleNamespace(returncode=0, stderr="", stdout=(
            '{"status":"ok","model":"fsrcnn","input_dimensions":[12,10],'
            '"output_dimensions":[24,20],"cold_seconds":0.1,'
            '"warm_seconds":[0.1],"output_file":' + __import__("json").dumps(str(stale)) + '}'
        ))

    monkeypatch.setattr(benchmark_models.subprocess, "run", fake_worker)
    results = benchmark_models.run(source, output_dir, repeats=1)
    assert results["fsrcnn"]["status"] == "failed"
    assert "missing or mismatched output image" in results["fsrcnn"]["error"]
    assert results["espcn"]["status"] == "unavailable"


def test_unconfigured_model_removes_stale_evidence(tmp_path, monkeypatch):
    source = tmp_path / "source.png"
    Image.new("RGB", (12, 10), "red").save(source)
    output_dir = tmp_path / "results"
    output_dir.mkdir()
    stale_fsrcnn = output_dir / "fsrcnn-2x.png"
    stale_espcn = output_dir / "espcn-2x.png"
    Image.new("RGB", (24, 20), "blue").save(stale_fsrcnn)
    Image.new("RGB", (24, 20), "blue").save(stale_espcn)
    monkeypatch.delenv("LUMQENIX_FSRCNN_MODEL", raising=False)
    monkeypatch.delenv("LUMQENIX_ESPCN_MODEL", raising=False)

    def unexpected_worker(*args, **kwargs):
        raise AssertionError("worker must not run for unconfigured models")

    monkeypatch.setattr(benchmark_models.subprocess, "run", unexpected_worker)
    results = benchmark_models.run(source, output_dir, repeats=1)
    assert results["fsrcnn"]["status"] == "unavailable"
    assert results["espcn"]["status"] == "unavailable"
    assert not stale_fsrcnn.exists()
    assert not stale_espcn.exists()
