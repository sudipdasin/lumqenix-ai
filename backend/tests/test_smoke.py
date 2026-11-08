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
