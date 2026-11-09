"""Deterministic CPU smoke tests; no pretrained model weights required."""
import io
from unittest.mock import patch
import cv2
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
    for name, module in (("fsrcnn", fsrcnn), ("espcn", espcn)):
        if not os.environ.get("LUMQENIX_" + name.upper() + "_MODEL"):
            continue
        if not module.available():
            pytest.fail(name + " model path configured but unavailable")
        output = module.upscale(Image.new("RGB", (32, 32), (80, 100, 120)))
        assert output.size == (64, 64), name

def test_empty_video_upload():
    with patch("app.main.shutil.which", return_value="/usr/bin/ffmpeg"):
        result = client.post("/api/enhance/video", files={"file": ("empty.mp4", b"", "video/mp4")})
    assert result.status_code == 400
    assert "Empty video" in result.json()["detail"]

def test_video_probe_failure():
    from subprocess import CompletedProcess
    with patch("app.main.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
        "app.main.subprocess.run", return_value=CompletedProcess(["ffprobe"], 1, "", "bad input")
    ):
        result = client.post("/api/enhance/video", files={"file": ("broken.mp4", b"invalid", "video/mp4")})
    assert result.status_code == 422
    assert "video stream" in result.json()["detail"]

def test_video_probe_timeout():
    from subprocess import TimeoutExpired
    with patch("app.main.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
        "app.main.subprocess.run", side_effect=TimeoutExpired("ffprobe", 20)
    ):
        result = client.post("/api/enhance/video", files={"file": ("slow.mp4", b"invalid", "video/mp4")})
    assert result.status_code == 422
    assert "timed out" in result.json()["detail"]

def test_video_oversize_rejected_before_transcode():
    from subprocess import CompletedProcess
    with patch("app.main.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
        "app.main.subprocess.run", return_value=CompletedProcess(["ffprobe"], 0, "4000,3000\n", "")
    ) as runner:
        result = client.post("/api/enhance/video", files={"file": ("large.mp4", b"test", "video/mp4")}, data={"scale":"2"})
    assert result.status_code == 413
    assert runner.call_count == 1

def test_invalid_onnx_model_path_does_not_break_status(monkeypatch):
    monkeypatch.setenv("LUMQENIX_ONNX_MODEL", "/nonexistent/model.onnx")
    result = client.get("/api/status")
    assert result.status_code == 200
    assert result.json()["ai_model_configured"] is False

def test_invalid_onnx_scale_does_not_break_status(monkeypatch, tmp_path):
    model = tmp_path / "test.onnx"
    model.write_bytes(b"placeholder")
    monkeypatch.setenv("LUMQENIX_ONNX_MODEL", str(model))
    monkeypatch.setenv("LUMQENIX_ONNX_SCALE", "garbage")
    result = client.get("/api/status")
    assert result.status_code == 200
    assert result.json()["ai_model_configured"] is False

def test_invalid_onnx_configuration_returns_503(monkeypatch):
    monkeypatch.setenv("LUMQENIX_ONNX_MODEL", "/nonexistent/model.onnx")
    result = client.post("/api/enhance/onnx", files={"file": ("small.png", png(), "image/png")})
    assert result.status_code == 503
    assert "configuration invalid" in result.json()["detail"]

def test_onnx_unconfigured_returns_503(monkeypatch):
    monkeypatch.delenv("LUMQENIX_ONNX_MODEL", raising=False)
    result = client.post("/api/enhance/onnx", files={"file": ("small.png", png(), "image/png")})
    assert result.status_code == 503

def test_video_processing_lock_rejects_concurrent_job():
    from app.main import PROCESSING_LOCK
    assert PROCESSING_LOCK.acquire(blocking=False)
    try:
        with patch("app.main.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
            "app.main.subprocess.run"
        ) as runner:
            result = client.post("/api/enhance/video", files={"file": ("small.mp4", b"not-empty", "video/mp4")})
        assert result.status_code == 429
        runner.assert_not_called()
    finally:
        PROCESSING_LOCK.release()

def test_video_probe_failure_releases_processing_lock():
    from app.main import PROCESSING_LOCK
    from subprocess import CompletedProcess
    with patch("app.main.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
        "app.main.subprocess.run", return_value=CompletedProcess(["ffprobe"], 1, "", "bad input")
    ):
        result = client.post("/api/enhance/video", files={"file": ("bad.mp4", b"bad", "video/mp4")})
    assert result.status_code == 422
    assert PROCESSING_LOCK.acquire(blocking=False)
    PROCESSING_LOCK.release()

def test_opencv_contrib_super_resolution_module_installed():
    """The documented base install must include the neural CPU engine."""
    assert hasattr(cv2, "dnn_superres"), "Install opencv-contrib-python-headless, not opencv-python-headless"

def test_classic_rejects_oversized_output():
    result = client.post("/api/enhance/image", files={"file": ("large.png", png(2000, 1600), "image/png")}, data={"scale": "2"})
    assert result.status_code == 413
