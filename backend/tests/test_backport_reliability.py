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

def test_video_output_cap_rejected_before_loading(monkeypatch):
    from app import main
    def runner(args, **kwargs):
        if args[0] == "ffprobe":
            return CompletedProcess(args, 0, '{"streams":[{"width":32,"height":24}],"format":{"duration":"1"}}', "")
        Path(args[-1]).write_bytes(b"oversized")
        return CompletedProcess(args, 0, b"", b"")
    monkeypatch.setattr(main, "MAX_VIDEO_OUTPUT", 4)
    with patch("app.main.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
        "app.main.subprocess.run", side_effect=runner
    ):
        response = client.post("/api/enhance/video", files={"file": ("video.mp4", b"video", "video/mp4")})
    assert response.status_code == 413

def test_video_output_within_cap_returns_mp4(monkeypatch):
    from app import main
    def runner(args, **kwargs):
        if args[0] == "ffprobe":
            return CompletedProcess(args, 0, '{"streams":[{"width":32,"height":24}],"format":{"duration":"1"}}', "")
        Path(args[-1]).write_bytes(b"mp4data")
        return CompletedProcess(args, 0, b"", b"")
    monkeypatch.setattr(main, "MAX_VIDEO_OUTPUT", 7)
    with patch("app.main.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
        "app.main.subprocess.run", side_effect=runner
    ):
        response = client.post("/api/enhance/video", files={"file": ("video.mp4", b"video", "video/mp4")})
    assert response.status_code == 200
    assert response.content == b"mp4data"
    assert response.headers["content-type"].startswith("video/mp4")

def test_empty_video_upload_rejected_before_ffprobe():
    with patch("app.main.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
        "app.main.subprocess.run"
    ) as run:
        response = client.post("/api/enhance/video", files={"file": ("empty.mp4", b"", "video/mp4")})
    assert response.status_code == 400
    run.assert_not_called()

def test_encoded_video_read_failure_returns_503():
    def runner(args, **kwargs):
        if args[0] == "ffprobe":
            return CompletedProcess(args, 0, '{"streams":[{"width":32,"height":24}],"format":{"duration":"1"}}', "")
        Path(args[-1]).write_bytes(b"mp4data")
        return CompletedProcess(args, 0, b"", b"")
    original_read = Path.read_bytes
    def read_with_failure(path):
        if path.name == "enhanced.mp4":
            raise PermissionError("cannot read encoded video")
        return original_read(path)
    with patch("app.main.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
        "app.main.subprocess.run", side_effect=runner
    ), patch.object(Path, "read_bytes", read_with_failure):
        response = client.post("/api/enhance/video", files={"file": ("video.mp4", b"video", "video/mp4")})
    assert response.status_code == 503
    assert "could not be read" in response.json()["detail"]

def test_video_lock_released_after_encoder_failure():
    from app.main import PROCESSING_LOCK
    def runner(args, **kwargs):
        if args[0] == "ffprobe":
            return CompletedProcess(args, 0, '{"streams":[{"width":32,"height":24}],"format":{"duration":"1"}}', "")
        raise FileNotFoundError("ffmpeg")
    with patch("app.main.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
        "app.main.subprocess.run", side_effect=runner
    ):
        response = client.post("/api/enhance/video", files={"file": ("video.mp4", b"video", "video/mp4")})
    assert response.status_code == 503
    assert not PROCESSING_LOCK.locked()

def test_video_missing_after_encoder_returns_422():
    def runner(args, **kwargs):
        if args[0] == "ffprobe":
            return CompletedProcess(args, 0, '{"streams":[{"width":32,"height":24}],"format":{"duration":"1"}}', "")
        return CompletedProcess(args, 0, b"", b"")
    with patch("app.main.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
        "app.main.subprocess.run", side_effect=runner
    ):
        response = client.post("/api/enhance/video", files={"file": ("video.mp4", b"video", "video/mp4")})
    assert response.status_code == 422
    assert "produced no output" in response.json()["detail"]

def test_video_staging_write_error_returns_503_and_unlocks():
    from app.main import PROCESSING_LOCK
    with patch("app.main.shutil.which", return_value="/usr/bin/ffmpeg"), patch.object(
        Path, "write_bytes", side_effect=PermissionError("disk is read-only")
    ), patch("app.main.subprocess.run") as run:
        response = client.post("/api/enhance/video", files={"file": ("video.mp4", b"video", "video/mp4")})
    assert response.status_code == 503
    assert "staging failed" in response.json()["detail"]
    assert not PROCESSING_LOCK.locked()
    run.assert_not_called()

def test_upload_read_failure_returns_503():
    from app.main import read_limited
    from fastapi import HTTPException
    from types import SimpleNamespace
    class FailingFile:
        def read(self, size):
            raise OSError("temporary upload is unreadable")
    try:
        read_limited(SimpleNamespace(file=FailingFile()))
    except HTTPException as exc:
        assert exc.status_code == 503
        assert "could not be read" in exc.detail
    else:
        raise AssertionError("Expected HTTP 503 for failed upload read")

def test_upload_limit_boundary(monkeypatch):
    from app import main
    from types import SimpleNamespace
    monkeypatch.setattr(main, "MAX_UPLOAD", 4)
    assert main.read_limited(SimpleNamespace(file=io.BytesIO(b"1234"))) == b"1234"
    try:
        main.read_limited(SimpleNamespace(file=io.BytesIO(b"12345")))
    except Exception as exc:
        from fastapi import HTTPException
        assert isinstance(exc, HTTPException)
        assert exc.status_code == 413
    else:
        raise AssertionError("Expected HTTP 413 for oversized upload")

def test_video_output_cap_rechecked_after_read(monkeypatch):
    from app import main
    def runner(args, **kwargs):
        if args[0] == "ffprobe":
            return CompletedProcess(args, 0, '{"streams":[{"width":32,"height":24}],"format":{"duration":"1"}}', "")
        Path(args[-1]).write_bytes(b"ok")
        return CompletedProcess(args, 0, b"", b"")
    original_read = Path.read_bytes
    def enlarged_read(path):
        if path.name == "enhanced.mp4":
            return b"larger-than-stat"
        return original_read(path)
    monkeypatch.setattr(main, "MAX_VIDEO_OUTPUT", 4)
    with patch("app.main.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
        "app.main.subprocess.run", side_effect=runner
    ), patch.object(Path, "read_bytes", enlarged_read):
        response = client.post("/api/enhance/video", files={"file": ("video.mp4", b"video", "video/mp4")})
    assert response.status_code == 413

def test_video_output_empty_after_stat_returns_422():
    def runner(args, **kwargs):
        if args[0] == "ffprobe":
            return CompletedProcess(args, 0, '{"streams":[{"width":32,"height":24}],"format":{"duration":"1"}}', "")
        Path(args[-1]).write_bytes(b"mp4")
        return CompletedProcess(args, 0, b"", b"")
    original_read = Path.read_bytes
    def empty_read(path):
        if path.name == "enhanced.mp4":
            return b""
        return original_read(path)
    with patch("app.main.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
        "app.main.subprocess.run", side_effect=runner
    ), patch.object(Path, "read_bytes", empty_read):
        response = client.post("/api/enhance/video", files={"file": ("video.mp4", b"video", "video/mp4")})
    assert response.status_code == 422
    assert "produced no output" in response.json()["detail"]

def test_ffprobe_timeout_returns_422_and_releases_lock():
    from app.main import PROCESSING_LOCK
    from subprocess import TimeoutExpired
    with patch("app.main.shutil.which", return_value="/usr/bin/ffprobe"), patch(
        "app.main.subprocess.run", side_effect=TimeoutExpired("ffprobe", 20)
    ):
        response = client.post("/api/enhance/video", files={"file": ("video.mp4", b"video", "video/mp4")})
    assert response.status_code == 422
    assert "timed out" in response.json()["detail"]
    assert not PROCESSING_LOCK.locked()

def test_invalid_ffprobe_metadata_returns_422_without_encoding():
    with patch("app.main.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
        "app.main.subprocess.run", return_value=CompletedProcess(["ffprobe"], 0, '{"streams":[]}', "")
    ) as run:
        response = client.post("/api/enhance/video", files={"file": ("video.mp4", b"video", "video/mp4")})
    assert response.status_code == 422
    assert run.call_count == 1

def test_video_duration_over_limit_returns_413_without_encoding():
    with patch("app.main.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
        "app.main.subprocess.run", return_value=CompletedProcess(["ffprobe"], 0, '{"streams":[{"width":32,"height":24}],"format":{"duration":"61"}}', "")
    ) as run:
        response = client.post("/api/enhance/video", files={"file": ("video.mp4", b"video", "video/mp4")})
    assert response.status_code == 413
    assert run.call_count == 1

def test_closed_upload_stream_returns_503():
    from app.main import read_limited
    from fastapi import HTTPException
    from types import SimpleNamespace
    stream = io.BytesIO(b"payload")
    stream.close()
    try:
        read_limited(SimpleNamespace(file=stream))
    except HTTPException as exc:
        assert exc.status_code == 503
        assert exc.detail == "Uploaded file could not be read"
    else:
        raise AssertionError("Expected HTTP 503 for a closed upload stream")
