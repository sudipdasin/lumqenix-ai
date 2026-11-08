"""Deterministic CPU smoke tests; no pretrained model weights required."""
import io
from unittest.mock import patch
import cv2
import numpy as np
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app
from app.version import VERSION

client = TestClient(app)

def png(w=32, h=24):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (110, 130, 150)).save(buf, format="PNG")
    return buf.getvalue()

def test_version_status():
    result = client.get("/api/status")
    assert result.status_code == 200
    assert result.json()["version"] == VERSION
    assert result.json()["status"] == "ok"

def test_classic_upscale():
    result = client.post("/api/enhance/image", files={"file": ("small.png", png(), "image/png")}, data={"preset":"natural","scale":"2"})
    assert result.status_code == 200, result.text
    with Image.open(io.BytesIO(result.content)) as image:
        assert image.size == (64, 48)

def test_classic_rejects_invalid_scale():
    result = client.post("/api/enhance/image", files={"file": ("small.png", png(), "image/png")}, data={"preset":"natural","scale":"3"})
    assert result.status_code == 400

def test_espcn_requires_model():
    with patch("app.main.espcn_available", return_value=False):
        result = client.post("/api/enhance/espcn", files={"file": ("small.png", png(), "image/png")})
    assert result.status_code == 503

def test_fsrcnn_invalid_strength():
    result = client.post("/api/enhance/fsrcnn", files={"file": ("small.png", png(), "image/png")}, data={"portrait":"true","portrait_version":"3","strength":"101"})
    assert result.status_code == 400

def test_espcn_endpoint_with_stub():
    def fake_upscale(image):
        return image.convert("RGB").resize((image.width*2, image.height*2))
    with patch("app.main.espcn_available", return_value=True), patch("app.main.espcn_upscale", side_effect=fake_upscale):
        result = client.post("/api/enhance/espcn", files={"file": ("small.png", png(), "image/png")})
    assert result.status_code == 200, result.text
    with Image.open(io.BytesIO(result.content)) as image:
        assert image.size == (64, 48)

def test_fsrcnn_v3_endpoint_with_stub():
    def fake_upscale(image, portrait=False, strength=35):
        assert portrait == "v3" and strength == 35
        return image.convert("RGB").resize((image.width*2, image.height*2))
    with patch("app.main.fsrcnn_available", return_value=True), patch("app.main.fsrcnn_upscale", side_effect=fake_upscale):
        result = client.post("/api/enhance/fsrcnn", files={"file": ("small.png", png(), "image/png")}, data={"portrait":"true","portrait_version":"3","strength":"35"})
    assert result.status_code == 200, result.text
    assert "v3" in result.headers["content-disposition"]
    with Image.open(io.BytesIO(result.content)) as image:
        assert image.size == (64, 48)

def test_espcn_engine_model_stub(monkeypatch, tmp_path):
    from app import espcn
    path = tmp_path / "ESPCN_x2.pb"
    path.write_bytes(b"stub")
    monkeypatch.setenv("LUMQENIX_ESPCN_MODEL", str(path))
    class FakeNetwork:
        def upsample(self, img):
            return cv2.resize(img, None, fx=2, fy=2)
    with patch("app.espcn._model", return_value=FakeNetwork()):
        output = espcn.upscale(Image.new("RGB", (20, 16)))
    assert output.size == (40, 32)

def test_espcn_rejects_oversized_image_before_inference():
    with patch("app.main.espcn_available", return_value=True), patch("app.main.espcn_upscale") as model:
        result = client.post("/api/enhance/espcn", files={"file": ("large.png", png(513, 512), "image/png")})
    assert result.status_code == 413, result.text
    model.assert_not_called()

def test_fsrcnn_rejects_oversized_image_before_inference():
    with patch("app.main.fsrcnn_available", return_value=True), patch("app.main.fsrcnn_upscale") as model:
        result = client.post("/api/enhance/fsrcnn", files={"file": ("large.png", png(513, 512), "image/png")})
    assert result.status_code == 413, result.text
    model.assert_not_called()

def test_espcn_rejects_invalid_image():
    with patch("app.main.espcn_available", return_value=True):
        result = client.post("/api/enhance/espcn", files={"file": ("bad.png", b"not an image", "image/png")})
    assert result.status_code == 400

def test_fsrcnn_invalid_path_does_not_crash_status(monkeypatch):
    monkeypatch.setenv("LUMQENIX_FSRCNN_MODEL", "/missing/model.pb")
    result = client.get("/api/status")
    assert result.status_code == 200
    assert result.json()["fsrcnn_available"] is False

def test_real_neural_model_when_configured():
    """Optional integration test: configure both model paths for real inference."""
    import os
    import pytest
    from app import fsrcnn, espcn
    if not any(os.environ.get("LUMQENIX_" + name + "_MODEL") for name in ("FSRCNN", "ESPCN")):
        pytest.skip("Pretrained weights not configured")
    for name, module in (("fsrcnn", fsrcnn), ("espcn", espcn)):
        if not os.environ.get("LUMQENIX_" + name.upper() + "_MODEL"):
            continue
        if not module.available():
            pytest.fail(name + " model path configured but unavailable")
        output = module.upscale(Image.new("RGB", (32, 32), (80, 100, 120)))
        assert output.size == (64, 64), name
