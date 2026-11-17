"""Validate real-model benchmark evidence without running pretrained inference."""
import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from benchmark_models import validate_worker_result


@pytest.fixture
def evidence(tmp_path):
    source = tmp_path / "source.png"
    output = tmp_path / "fsrcnn-2x.png"
    Image.new("RGB", (12, 10), "red").save(source)
    Image.new("RGB", (24, 20), "blue").save(output)
    report = {
        "status": "ok", "model": "fsrcnn",
        "input_dimensions": [12, 10], "output_dimensions": [24, 20],
        "cold_seconds": 0.12, "warm_seconds": [0.08, 0.09],
        "output_file": str(output),
    }
    return source, output, report


def check(evidence, report):
    source, output, _ = evidence
    return validate_worker_result(report, "fsrcnn", source, output, 2)


def test_valid_evidence(evidence):
    assert check(evidence, evidence[2])["status"] == "ok"


@pytest.mark.parametrize("field,value", [
    ("model", "espcn"),
    ("output_dimensions", [12, 10]),
    ("input_dimensions", [1, 1]),
    ("warm_seconds", [0.1]),
    ("cold_seconds", True),
    ("warm_seconds", [0.1, False]),
    ("cold_seconds", float("nan")),
    ("warm_seconds", [0.1, -0.2]),
    ("output_file", "/nonexistent/benchmark.png"),
])
def test_invalid_worker_report_rejected(evidence, field, value):
    report = dict(evidence[2], **{field: value})
    assert check(evidence, report)["status"] == "failed"


def test_corrupt_output_rejected(evidence):
    evidence[1].write_bytes(b"not a png")
    assert check(evidence, evidence[2])["status"] == "failed"


def test_non_object_report_rejected(evidence):
    assert check(evidence, ["ok"])["status"] == "failed"
