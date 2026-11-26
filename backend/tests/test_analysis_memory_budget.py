"""Bounded-quality-analysis memory regression tests (no pretrained models)."""
import numpy as np
from PIL import Image

from app import engine


def test_large_image_analyzed_on_a_bounded_sample(monkeypatch):
    observed = []
    original = engine.cv2.cvtColor

    def tracking_conversion(array, conversion):
        observed.append(array.shape)
        return original(array, conversion)

    monkeypatch.setattr(engine.cv2, "cvtColor", tracking_conversion)
    image = Image.new("RGB", (3000, 1600), (90, 100, 110))
    result = engine.inspect(image)
    assert (result["width"], result["height"]) == image.size
    assert result["analysis_sample_width"] <= 1024
    assert result["analysis_sample_height"] <= 1024
    assert observed and observed[0][0] <= 1024 and observed[0][1] <= 1024
    assert image.size == (3000, 1600)


def test_small_image_keeps_full_resolution_analysis():
    image = Image.new("RGB", (48, 32), (10, 20, 30))
    result = engine.inspect(image)
    assert result["analysis_sample_width"] == 48
    assert result["analysis_sample_height"] == 32
    assert result["width"] == 48
    assert result["height"] == 32


def test_analysis_remains_exif_correct_when_sampling_large_images():
    import io

    image = Image.new("RGB", (1800, 1200), (30, 40, 50))
    exif = Image.Exif()
    exif[274] = 6
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=exif)
    buffer.seek(0)
    with Image.open(buffer) as photo:
        result = engine.inspect(photo)
        assert (result["width"], result["height"]) == (1200, 1800)
        assert max(result["analysis_sample_width"], result["analysis_sample_height"]) <= 1024


def test_scaled_analysis_makes_no_untrained_ai_quality_claims():
    result = engine.inspect(Image.new("RGB", (32, 20), (100, 100, 100)))
    assert "possibly_blurry" in result
    assert "low_light" in result
    assert "super_resolution" not in result
