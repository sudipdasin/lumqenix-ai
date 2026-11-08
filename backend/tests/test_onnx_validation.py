import pytest
from PIL import Image
from app.onnx_upscale import upscale

def test_invalid_device_rejected():
    with pytest.raises(ValueError, match="device"):
        upscale(Image.new("RGB", (8,8)), device="invalid")

def test_invalid_tile_rejected():
    with pytest.raises(ValueError, match="tile"):
        upscale(Image.new("RGB", (8,8)), tile=10)

def test_no_model_configured(monkeypatch):
    monkeypatch.delenv("LUMQENIX_ONNX_MODEL", raising=False)
    with pytest.raises(ValueError, match="No ONNX model"):
        upscale(Image.new("RGB", (8,8)), device="cpu")
