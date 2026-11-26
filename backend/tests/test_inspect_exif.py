"""Analysis must use the same visible EXIF geometry as image enhancement."""
import io

import pytest
from PIL import Image

from app.engine import enhance, inspect


def oriented_jpeg(orientation: int):
    original = Image.new("RGB", (19, 11), (35, 75, 115))
    exif = Image.Exif()
    exif[274] = orientation
    data = io.BytesIO()
    original.save(data, format="JPEG", exif=exif)
    data.seek(0)
    return Image.open(data)


@pytest.mark.parametrize("orientation,expected", [
    (1, (19, 11)),
    (3, (19, 11)),
    (6, (11, 19)),
    (8, (11, 19)),
])
def test_analysis_reports_display_oriented_dimensions(orientation, expected):
    with oriented_jpeg(orientation) as image:
        before = image.size
        result = inspect(image)
        assert (result["width"], result["height"]) == expected
        assert image.size == before
        assert result["brightness"] >= 0


@pytest.mark.parametrize("orientation", [6, 8])
def test_image_enhancement_and_analysis_use_matching_geometry(orientation):
    with oriented_jpeg(orientation) as image:
        metadata = inspect(image)
        enhanced, _ = enhance(image, "natural", 2)
        assert enhanced.size == (metadata["width"] * 2, metadata["height"] * 2)


def test_analyze_endpoint_reports_display_orientation():
    from fastapi.testclient import TestClient
    from app.main import app

    with oriented_jpeg(6) as image:
        # Use original JPEG bytes, not the decoder's current file offset.
        encoded = image.fp.getvalue()
    response = TestClient(app).post(
        "/api/analyze",
        files={"file": ("oriented.jpg", encoded, "image/jpeg")},
    )
    assert response.status_code == 200, response.text
    assert (response.json()["width"], response.json()["height"]) == (11, 19)
