"""Subprocess launch failures should not abort independent pretrained model lanes."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import benchmark_models


def test_worker_launch_error_is_recorded_and_next_model_still_runs(tmp_path, monkeypatch):
    source = tmp_path / "source.png"
    source.write_bytes(b"placeholder: worker launch fails before image decoding")
    for name, env in benchmark_models.MODEL_ENV.items():
        model = tmp_path / f"{name}.pb"
        model.write_bytes(b"placeholder model")
        monkeypatch.setenv(env, str(model))

    calls = []

    def failed_launch(command, **kwargs):
        calls.append(command)
        raise FileNotFoundError("python executable unavailable")

    monkeypatch.setattr(benchmark_models.subprocess, "run", failed_launch)
    results = benchmark_models.run(source, tmp_path / "results", repeats=1, timeout=1)
    assert len(calls) == len(benchmark_models.MODEL_ENV)
    assert set(results) == set(benchmark_models.MODEL_ENV)
    for result in results.values():
        assert result["status"] == "failed"
        assert "worker launch failed: FileNotFoundError" in result["error"]
