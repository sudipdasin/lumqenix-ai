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
            return CompletedProcess(args, 0, '{"streams":[{"width":64,"height":48}],"format":{"duration":"1"}}' if Path(args[-1]).name == "enhanced.mp4" else '{"streams":[{"width":32,"height":24}],"format":{"duration":"1"}}', "")
        raise FileNotFoundError("ffmpeg")
    with patch("app.main.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
        "app.main.subprocess.run", side_effect=runner
    ):
        response = client.post("/api/enhance/video", files={"file": ("video.mp4", b"video", "video/mp4")})
    assert response.status_code == 503

def test_missing_encoded_video_returns_422():
    def runner(args, **kwargs):
        if args[0] == "ffprobe":
            return CompletedProcess(args, 0, '{"streams":[{"width":64,"height":48}],"format":{"duration":"1"}}' if Path(args[-1]).name == "enhanced.mp4" else '{"streams":[{"width":32,"height":24}],"format":{"duration":"1"}}', "")
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
            return CompletedProcess(args, 0, '{"streams":[{"width":64,"height":48}],"format":{"duration":"1"}}' if Path(args[-1]).name == "enhanced.mp4" else '{"streams":[{"width":32,"height":24}],"format":{"duration":"1"}}', "")
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
            return CompletedProcess(args, 0, '{"streams":[{"width":64,"height":48}],"format":{"duration":"1"}}' if Path(args[-1]).name == "enhanced.mp4" else '{"streams":[{"width":32,"height":24}],"format":{"duration":"1"}}', "")
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
            return CompletedProcess(args, 0, '{"streams":[{"width":64,"height":48}],"format":{"duration":"1"}}' if Path(args[-1]).name == "enhanced.mp4" else '{"streams":[{"width":32,"height":24}],"format":{"duration":"1"}}', "")
        Path(args[-1]).write_bytes(b"mp4data")
        return CompletedProcess(args, 0, b"", b"")
    original_open = Path.open
    def open_with_failure(path, *args, **kwargs):
        if path.name == "enhanced.mp4" and args and args[0] == "rb":
            raise PermissionError("cannot read encoded video")
        return original_open(path, *args, **kwargs)
    with patch("app.main.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
        "app.main.subprocess.run", side_effect=runner
    ), patch.object(Path, "open", open_with_failure):
        response = client.post("/api/enhance/video", files={"file": ("video.mp4", b"video", "video/mp4")})
    assert response.status_code == 503
    assert "could not be read" in response.json()["detail"]

def test_video_lock_released_after_encoder_failure():
    from app.main import PROCESSING_LOCK
    def runner(args, **kwargs):
        if args[0] == "ffprobe":
            return CompletedProcess(args, 0, '{"streams":[{"width":64,"height":48}],"format":{"duration":"1"}}' if Path(args[-1]).name == "enhanced.mp4" else '{"streams":[{"width":32,"height":24}],"format":{"duration":"1"}}', "")
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
            return CompletedProcess(args, 0, '{"streams":[{"width":64,"height":48}],"format":{"duration":"1"}}' if Path(args[-1]).name == "enhanced.mp4" else '{"streams":[{"width":32,"height":24}],"format":{"duration":"1"}}', "")
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
            return CompletedProcess(args, 0, '{"streams":[{"width":64,"height":48}],"format":{"duration":"1"}}' if Path(args[-1]).name == "enhanced.mp4" else '{"streams":[{"width":32,"height":24}],"format":{"duration":"1"}}', "")
        Path(args[-1]).write_bytes(b"ok")
        return CompletedProcess(args, 0, b"", b"")
    original_open = Path.open
    def enlarged_open(path, *args, **kwargs):
        if path.name == "enhanced.mp4" and args and args[0] == "rb":
            return io.BytesIO(b"larger-than-stat")
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(main, "MAX_VIDEO_OUTPUT", 4)
    with patch("app.main.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
        "app.main.subprocess.run", side_effect=runner
    ), patch.object(Path, "open", enlarged_open):
        response = client.post("/api/enhance/video", files={"file": ("video.mp4", b"video", "video/mp4")})
    assert response.status_code == 413

def test_video_output_empty_after_stat_returns_422():
    def runner(args, **kwargs):
        if args[0] == "ffprobe":
            return CompletedProcess(args, 0, '{"streams":[{"width":64,"height":48}],"format":{"duration":"1"}}' if Path(args[-1]).name == "enhanced.mp4" else '{"streams":[{"width":32,"height":24}],"format":{"duration":"1"}}', "")
        Path(args[-1]).write_bytes(b"mp4")
        return CompletedProcess(args, 0, b"", b"")
    original_open = Path.open
    def empty_open(path, *args, **kwargs):
        if path.name == "enhanced.mp4" and args and args[0] == "rb":
            return io.BytesIO(b"")
        return original_open(path, *args, **kwargs)
    with patch("app.main.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
        "app.main.subprocess.run", side_effect=runner
    ), patch.object(Path, "open", empty_open):
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

def test_nonfinite_video_duration_rejected_without_encoding():
    """NaN duration from ffprobe must not reach the encoder."""
    with patch("app.main.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
        "app.main.subprocess.run",
        return_value=CompletedProcess(["ffprobe"], 0,
            '{"streams":[{"width":32,"height":24}],"format":{"duration":"NaN"}}', "")
    ) as run:
        response = client.post("/api/enhance/video", files={"file": ("video.mp4", b"video", "video/mp4")})
    assert response.status_code == 422
    assert run.call_count == 1

def test_ffprobe_nonzero_exit_rejected_without_encoding():
    """Malformed videos should not trigger an encoding attempt."""
    with patch("app.main.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
        "app.main.subprocess.run",
        return_value=CompletedProcess(["ffprobe"], 1, "", "invalid input")
    ) as run:
        response = client.post("/api/enhance/video", files={"file": ("video.mp4", b"video", "video/mp4")})
    assert response.status_code == 422
    assert run.call_count == 1

def test_upload_stream_nonbytes_result_returns_503():
    """Broken upload streams must not turn into uncaught TypeError or bad data."""
    from types import SimpleNamespace
    from fastapi import HTTPException
    from app.main import read_limited

    class InvalidStream:
        def __init__(self, value):
            self.value = value

        def read(self, size):
            return self.value

    for value in (None, "not binary", bytearray(b"binary-like")):
        try:
            read_limited(SimpleNamespace(file=InvalidStream(value)))
        except HTTPException as exc:
            assert exc.status_code == 503
            assert exc.detail == "Uploaded file could not be read"
        else:
            raise AssertionError(f"Expected HTTP 503 for {type(value).__name__}")

def test_video_output_read_is_bounded_after_stat(monkeypatch):
    """The MP4 reader must request at most limit+1 bytes, not read the whole file."""
    from app import main
    def runner(args, **kwargs):
        if args[0] == "ffprobe":
            return CompletedProcess(args, 0, '{"streams":[{"width":64,"height":48}],"format":{"duration":"1"}}' if Path(args[-1]).name == "enhanced.mp4" else '{"streams":[{"width":32,"height":24}],"format":{"duration":"1"}}', "")
        Path(args[-1]).write_bytes(b"ok")
        return CompletedProcess(args, 0, b"", b"")
    class RecordingStream(io.BytesIO):
        def read(self, size=-1):
            assert size == 5
            return super().read(size)
    original_open = Path.open
    def bounded_open(path, *args, **kwargs):
        if path.name == "enhanced.mp4" and args and args[0] == "rb":
            return RecordingStream(b"12345" + b"x" * 100)
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(main, "MAX_VIDEO_OUTPUT", 4)
    with patch("app.main.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
        "app.main.subprocess.run", side_effect=runner
    ), patch.object(Path, "open", bounded_open):
        response = client.post("/api/enhance/video", files={"file": ("video.mp4", b"video", "video/mp4")})
    assert response.status_code == 413

def test_video_temp_directory_creation_failure_returns_503_and_unlocks():
    """Temporary disk exhaustion must not leave the processing lock held."""
    from app.main import PROCESSING_LOCK
    with patch("app.main.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
        "app.main.tempfile.TemporaryDirectory", side_effect=OSError("no space left")
    ), patch("app.main.subprocess.run") as run:
        response = client.post("/api/enhance/video", files={"file": ("video.mp4", b"video", "video/mp4")})
    assert response.status_code == 503
    assert "temporary directory unavailable" in response.json()["detail"]
    assert not PROCESSING_LOCK.locked()
    run.assert_not_called()

def test_status_requires_both_video_tools():
    """Do not advertise usable video mode when FFprobe is missing."""
    def only_ffmpeg(name):
        return "/usr/bin/ffmpeg" if name == "ffmpeg" else None
    with patch("app.main.shutil.which", side_effect=only_ffmpeg):
        response = client.get("/api/status")
    assert response.status_code == 200
    assert response.json()["ffmpeg_available"] is False

def test_status_reports_video_tools_when_both_exist():
    with patch("app.main.shutil.which", return_value="/usr/bin/tool"):
        response = client.get("/api/status")
    assert response.status_code == 200
    assert response.json()["ffmpeg_available"] is True

def test_video_rejects_wrong_encoded_dimensions_and_releases_lock():
    """An otherwise decodable output must not pass when scaling is incorrect."""
    from app.main import PROCESSING_LOCK
    calls = []
    def runner(args, **kwargs):
        calls.append(args)
        if args[0] == "ffprobe":
            # The source is 32x24 and scale=2 requires 64x48; deliberately
            # report the source dimensions for the encoded output as well.
            return CompletedProcess(args, 0, '{"streams":[{"width":32,"height":24}],"format":{"duration":"1"}}', "")
        if args[0] == "ffmpeg" and "-y" in args:
            Path(args[-1]).write_bytes(b"mp4data")
        return CompletedProcess(args, 0, b"", b"")
    with patch("app.main.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
        "app.main.subprocess.run", side_effect=runner
    ):
        response = client.post("/api/enhance/video", files={"file": ("video.mp4", b"video", "video/mp4")})
    assert response.status_code == 422
    assert "dimensions do not match" in response.json()["detail"]
    assert sum(args[0] == "ffprobe" for args in calls) == 2
    assert not any(args[0] == "ffmpeg" and "-frames:v" in args for args in calls)
    assert not PROCESSING_LOCK.locked()


def test_video_oversized_encoded_file_skips_verification(monkeypatch):
    """Reject oversized output before FFprobe or decode consumes more CPU."""
    from app import main
    calls = []
    def runner(args, **kwargs):
        calls.append(args)
        if args[0] == "ffprobe":
            return CompletedProcess(args, 0, '{"streams":[{"width":32,"height":24}],"format":{"duration":"1"}}', "")
        if args[0] == "ffmpeg" and "-y" in args:
            Path(args[-1]).write_bytes(b"12345")
        return CompletedProcess(args, 0, b"", b"")
    monkeypatch.setattr(main, "MAX_VIDEO_OUTPUT", 4)
    with patch("app.main.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
        "app.main.subprocess.run", side_effect=runner
    ):
        response = client.post("/api/enhance/video", files={"file": ("video.mp4", b"video", "video/mp4")})
    assert response.status_code == 413
    assert sum(args[0] == "ffprobe" for args in calls) == 1
    assert not any(args[0] == "ffmpeg" and "-frames:v" in args for args in calls)
    assert not main.PROCESSING_LOCK.locked()
