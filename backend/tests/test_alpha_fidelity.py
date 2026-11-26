"""Fidelity regression: classic presets must not erase source transparency."""
import io

import pytest
from PIL import Image

from app.engine import PRESETS, enhance
from fastapi.testclient import TestClient
from app.main import app


def translucent_image():
    image = Image.new("RGBA", (16, 12), (88, 140, 205, 255))
    for x in range(16):
        for y in range(12):
            image.putpixel((x, y), (88, 140, 205, x * 17))
    return image


@pytest.mark.parametrize("preset", sorted(PRESETS))
def test_presets_preserve_original_alpha_at_scale_one(preset):
    source = translucent_image()
    original_alpha = source.getchannel("A").tobytes()
    result, _ = enhance(source, preset, 1)
    assert result.mode == "RGBA"
    assert result.size == source.size
    assert result.getchannel("A").tobytes() == original_alpha
    assert source.getchannel("A").tobytes() == original_alpha


@pytest.mark.parametrize("scale", [2, 4])
def test_transparency_scales_with_image(scale):
    image = Image.new("RGBA", (10, 8), (20, 80, 190, 0))
    for x in range(3, 7):
        for y in range(2, 6):
            image.putpixel((x, y), (20, 80, 190, 255))
    result, _ = enhance(image, "natural", scale)
    assert result.mode == "RGBA"
    assert result.size == (10 * scale, 8 * scale)
    alpha = result.getchannel("A")
    assert alpha.getextrema() == (0, 255)
    assert result.getpixel((0, 0))[3] == 0
    assert result.getpixel((5 * scale, 4 * scale))[3] == 255


def test_palette_png_transparency_preserved():
    image = Image.new("P", (12, 10), 0)
    image.putpalette([0, 0, 0, 240, 80, 50] + [0] * (256 * 3 - 6))
    image.info["transparency"] = 0
    for x in range(4, 8):
        for y in range(3, 7):
            image.putpixel((x, y), 1)
    out, _ = enhance(image, "vivid", 1)
    assert out.mode == "RGBA"
    assert out.getpixel((0, 0))[3] == 0
    assert out.getpixel((5, 5))[3] == 255


def test_real_api_preserves_alpha_in_downloaded_png():
    src = translucent_image()
    data = io.BytesIO()
    src.save(data, "PNG")
    response = TestClient(app).post(
        "/api/enhance/image",
        files={"file": ("overlay.png", data.getvalue(), "image/png")},
        data={"preset": "natural", "scale": 1},
    )
    assert response.status_code == 200, response.text
    with Image.open(io.BytesIO(response.content)) as output:
        assert output.mode == "RGBA"
        assert output.getchannel("A").tobytes() == src.getchannel("A").tobytes()


def test_photo_processing_retains_rgb_without_fake_alpha():
    image = Image.new("RGB", (20, 14), (76, 124, 187))
    output, _ = enhance(image, "portrait", 2)
    assert output.mode == "RGB"
    assert output.size == (40, 28)
