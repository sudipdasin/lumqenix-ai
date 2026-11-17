"""Regression coverage for paired-reference benchmark comparison metrics."""
import numpy as np
from PIL import Image

from scripts.evaluate_quality import evaluate


def test_prediction_vs_bicubic_and_psnr_delta(tmp_path):
    reference = np.full((8, 8, 3), 100, dtype=np.uint8)
    baseline = np.full((8, 8, 3), 80, dtype=np.uint8)
    prediction = np.full((8, 8, 3), 90, dtype=np.uint8)
    paths = [tmp_path / name for name in ("reference.png", "prediction.png", "baseline.png")]
    for path, pixels in zip(paths, (reference, prediction, baseline)):
        Image.fromarray(pixels, "RGB").save(path)
    result = evaluate(*paths)
    assert result["prediction_vs_baseline"]["mae_rgb"] == 10
    assert result["prediction_vs_baseline"]["mse_rgb"] == 100
    assert result["mae_improvement_vs_baseline"] == 10
    assert result["psnr_improvement_vs_baseline_db"] > 6


def test_identical_reference_has_undefined_psnr_delta(tmp_path):
    pixels = np.full((8, 8, 3), 100, dtype=np.uint8)
    baseline = np.full((8, 8, 3), 80, dtype=np.uint8)
    paths = [tmp_path / name for name in ("reference.png", "prediction.png", "baseline.png")]
    for path, image in zip(paths, (pixels, pixels, baseline)):
        Image.fromarray(image, "RGB").save(path)
    result = evaluate(*paths)
    assert result["prediction_metrics"]["lossless"]
    assert result["psnr_improvement_vs_baseline_db"] is None
    assert result["prediction_vs_baseline"]["mae_rgb"] == 20
