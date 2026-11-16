"""Deterministic numerical contracts for paired-reference quality evaluation."""
import numpy as np
import pytest

from scripts.evaluate_quality import metrics, evaluate
from PIL import Image


def test_identical_image_has_zero_error_and_lossless_psnr():
    pixels = np.arange(3 * 8 * 8, dtype=np.uint8).reshape(8, 8, 3)
    result = metrics(pixels, pixels.copy())
    assert result == {"mse_rgb": 0.0, "mae_rgb": 0.0, "psnr_rgb_db": None, "lossless": True}


def test_known_constant_error_has_correct_psnr():
    reference = np.full((4, 5, 3), 100, dtype=np.uint8)
    prediction = np.full_like(reference, 90)
    result = metrics(reference, prediction)
    assert result["mse_rgb"] == 100
    assert result["mae_rgb"] == 10
    assert result["psnr_rgb_db"] == pytest.approx(28.130804, abs=0.000002)


def test_mismatched_dimensions_are_rejected():
    with pytest.raises(ValueError, match="dimensions mismatch"):
        metrics(np.zeros((4, 4, 3), dtype=np.uint8), np.zeros((5, 4, 3), dtype=np.uint8))


def test_reference_comparison_reports_baseline_delta(tmp_path):
    reference = tmp_path / "reference.png"
    predicted = tmp_path / "predicted.png"
    baseline = tmp_path / "baseline.png"
    Image.new("RGB", (8, 8), (120, 120, 120)).save(reference)
    Image.new("RGB", (8, 8), (119, 119, 119)).save(predicted)
    Image.new("RGB", (8, 8), (110, 110, 110)).save(baseline)
    result = evaluate(reference, predicted, baseline)
    assert result["dimensions"] == [8, 8]
    assert result["prediction_metrics"]["mae_rgb"] == 1
    assert result["baseline_metrics"]["mae_rgb"] == 10
    assert result["mae_improvement_vs_baseline"] == 9
