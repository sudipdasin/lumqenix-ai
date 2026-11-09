"""Reliability regression tests for backports to the 0.3 development branch."""
import io
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image
from app.main import app

client = TestClient(app)

def png():
    buffer = io.BytesIO()
    Image.new("RGB", (16, 16)).save(buffer, format="PNG")
    return buffer.getvalue()

def test_invalid_onnx_path_is_not_reported_ready(monkeypatch):
    monkeypatch.setenv("LUMQENIX_ONNX_MODEL", "/nonexistent/lumqenix.onnx")
    response = client.get("/api/status")
    assert response.status_code == 200
    assert response.json()["ai_model_configured"] is False

def test_invalid_onnx_path_returns_503(monkeypatch):
    monkeypatch.setenv("LUMQENIX_ONNX_MODEL", "/nonexistent/lumqenix.onnx")
    response = client.post("/api/enhance/onnx", files={"file": ("input.png", png(), "image/png")})
    assert response.status_code == 503
    assert "configuration invalid" in response.json()["detail"]

def test_ffprobe_launch_error_returns_503():
    with patch("app.main.shutil.which", return_value="/usr/bin/ffprobe"), patch(
        "app.main.subprocess.run", side_effect=FileNotFoundError("ffprobe")
    ):
        response = client.post("/api/enhance/video", files={"file": ("video.mp4", b"video", "video/mp4")})
    assert response.status_code == 503

def test_ffmpeg_launch_error_returns_503():
    def runner(args, **kwargs):
        if args[0] == "ffprobe":
            return CompletedProcess(args, 0, '{"streams":[{"width":32,"height":24}],"format":{"duration":"1"}}', "")
        raise FileNotFoundError("ffmpeg")
    with patch("app.main.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
        "app.main.subprocess.run", side_effect=runner
    ):
        response = client.post("/api/enhance/video", files={"file": ("video.mp4", b"video", "video/mp4")})
    assert response.status_code == 503

def test_missing_encoded_video_returns_422():
    def runner(args, **kwargs):
        if args[0] == "ffprobe":
            return CompletedProcess(args, 0, '{"streams":[{"width":32,"height":24}],"format":{"duration":"1"}}', "")
        return CompletedProcess(args, 0, b"", b"")
    with patch("app.main.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
        "app.main.subprocess.run", side_effect=runner
    ):
        response = client.post("/api/enhance/video", files={"file": ("video.mp4", b"video", "video/mp4")})
    assert response.status_code == 422
