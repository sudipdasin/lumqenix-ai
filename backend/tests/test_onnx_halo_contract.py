"""Contract tests for ONNX halo tiling without downloading a model.

The fake session implements deterministic nearest-neighbor x2 output. This tests
tile seams, boundary cropping and output validation, not pretrained-model quality.
"""
from unittest.mock import patch

import numpy as np
import pytest
from PIL import Image

from app.onnx_upscale import upscale


class _IO:
    name = "pixels"


class _NearestSession:
    def __init__(self, *, malformed=False, nonfinite=False):
        self.malformed = malformed
        self.nonfinite = nonfinite
        self.calls = 0

    def get_inputs(self):
        return [_IO()]

    def get_outputs(self):
        return [_IO()]

    def run(self, outputs, feeds):
        self.calls += 1
        tensor = feeds["pixels"]
        result = np.repeat(np.repeat(tensor, 2, axis=2), 2, axis=3)
        if self.malformed:
            result = result[:, :, :-1, :]
        if self.nonfinite:
            result[0, 0, 0, 0] = np.nan
        return [result]


@pytest.mark.parametrize("size,tile,overlap", [
    ((35, 37), 32, 0),
    ((79, 65), 32, 8),
    ((129, 97), 64, 16),
    ((64, 64), 32, 15),
])
def test_halo_tiles_reconstruct_exact_nearest_neighbor(size, tile, overlap):
    width, height = size
    rng = np.random.default_rng(20261117)
    original = rng.integers(0, 256, (height, width, 3), dtype=np.uint8)
    fake = _NearestSession()
    with patch("app.onnx_upscale.model_path", return_value="/tmp/model.onnx"), patch(
        "app.onnx_upscale.configured_scale", return_value=2
    ), patch("app.onnx_upscale._session", return_value=fake):
        output, device = upscale(Image.fromarray(original), device="cpu", tile=tile, overlap=overlap)
    expected = np.repeat(np.repeat(original, 2, axis=0), 2, axis=1)
    # Conversion via float32 introduces at most one level of rounding.
    assert np.max(np.abs(np.asarray(output).astype(np.int16) - expected.astype(np.int16))) <= 1
    assert output.size == (width * 2, height * 2)
    assert device == "cpu"
    assert fake.calls == ((width + tile - 1) // tile) * ((height + tile - 1) // tile)


@pytest.mark.parametrize("failure,expected", [
    ({"malformed": True}, ValueError),
    ({"nonfinite": True}, RuntimeError),
])
def test_halo_tiles_reject_bad_model_outputs(failure, expected):
    fake = _NearestSession(**failure)
    with patch("app.onnx_upscale.model_path", return_value="/tmp/model.onnx"), patch(
        "app.onnx_upscale.configured_scale", return_value=2
    ), patch("app.onnx_upscale._session", return_value=fake):
        with pytest.raises(expected):
            upscale(Image.new("RGB", (40, 40)), device="cpu", tile=32, overlap=8)


@pytest.mark.parametrize("size,tile,overlap", [
    ((65, 47), 32, 0),
    ((103, 71), 32, 8),
    ((127, 95), 64, 16),
])
def test_optimized_core_conversion_matches_full_halo_conversion(size, tile, overlap):
    """Pixel-level reference against full-halo RGB conversion for x2 inference."""
    width, height = size
    rng = np.random.default_rng(7331)
    original = rng.integers(0, 256, (height, width, 3), dtype=np.uint8)
    fake = _NearestSession()
    with patch("app.onnx_upscale.model_path", return_value="/tmp/model.onnx"), patch(
        "app.onnx_upscale.configured_scale", return_value=2
    ), patch("app.onnx_upscale._session", return_value=fake):
        output, _ = upscale(Image.fromarray(original), device="cpu", tile=tile, overlap=overlap)
    reference = np.repeat(np.repeat(original.astype(np.float32) / 255.0, 2, axis=0), 2, axis=1)
    reference = np.clip(reference * 255.0, 0, 255).astype(np.uint8)
    np.testing.assert_array_equal(np.asarray(output), reference)
