"""Real-reference benchmark preprocessing; model inference is tested separately."""
import hashlib

import numpy as np
import pytest
from PIL import Image

from scripts.benchmark_quality_models import make_pair, run_quality


def test_reference_image_preserves_provenance_and_dimensions(tmp_path, monkeypatch):
    source = tmp_path / "portrait.png"
    pixels = np.zeros((300, 400, 3), dtype=np.uint8)
    pixels[:, :, 0] = np.arange(400, dtype=np.uint16)[None, :] % 256
    pixels[:, :, 1] = 110
    Image.fromarray(pixels).save(source)
    output = tmp_path / "quality"
    hr, lr, bicubic = make_pair(output, source)
    assert Image.open(hr).size == (256, 256)
    assert Image.open(lr).size == (128, 128)
    assert Image.open(bicubic).size == (256, 256)

    def fake_run(input_path, output_dir, **kwargs):
        output_dir.mkdir(parents=True, exist_ok=True)
        for name in ("fsrcnn", "espcn"):
            Image.open(input_path).resize((256, 256)).save(output_dir / f"{name}-2x.png")
        return {name: {"status": "ok"} for name in ("fsrcnn", "espcn")}

    monkeypatch.setattr("scripts.benchmark_quality_models.run", fake_run)
    result = run_quality(output, reference_path=source)
    assert result["dataset"] == "operator-reference-v1"
    assert result["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert all(result["models"][name]["quality"]["dimensions"] == [256, 256]
               for name in ("fsrcnn", "espcn"))


def test_small_reference_rejected(tmp_path):
    source = tmp_path / "small.png"
    Image.new("RGB", (255, 512)).save(source)
    with pytest.raises(ValueError, match="at least 256x256"):
        make_pair(tmp_path / "out", source)


def test_default_synthetic_pair_unchanged(tmp_path):
    hr, lr, bicubic = make_pair(tmp_path / "default")
    assert Image.open(hr).size == (256, 256)
    assert Image.open(lr).size == (128, 128)
    assert Image.open(bicubic).size == (256, 256)
