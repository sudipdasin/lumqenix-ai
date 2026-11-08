"""API resource limits, lock lifecycle, and threadpool regression coverage."""
import io
import json
import threading
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import main

client = TestClient(main.app)
IMAGE_ENDPOINTS = ["analyze", "enhance/image", "enhance/onnx", "enhance/fsrcnn", "enhance/espcn"]


@pytest.fixture
def upload():
    output = io.BytesIO()
    Image.new("RGB", (32, 24), (80, 110, 140)).save(output, format="PNG")
    return {"file": ("image.png", output.getvalue(), "image/png")}


@pytest.fixture
def neural_models(monkeypatch):
    monkeypatch.setattr(main, "model_path", lambda: Path("model.onnx"))
    monkeypatch.setattr(main, "configured_scale", lambda: 2)
    monkeypatch.setattr(main, "fsrcnn_available", lambda: True)
    monkeypatch.setattr(main, "espcn_available", lambda: True)
    monkeypatch.setattr(main, "onnx_upscale", lambda image, *args: (image.copy(), "cpu"))
    monkeypatch.setattr(main, "fsrcnn_upscale", lambda image, **kwargs: image.copy())
    monkeypatch.setattr(main, "espcn_upscale", lambda image: image.copy())


def test_brand_matches_shipped_configuration():
    expected = json.loads((Path(main.__file__).resolve().parents[2] / "config" / "brand.json").read_text())
    response = client.get("/api/brand")
    assert response.status_code == 200
    assert response.json() == expected


@pytest.mark.parametrize("preset", sorted(main.PRESETS))
@pytest.mark.parametrize("scale", [1, 2, 4])
def test_every_classic_preset_and_scale(preset, scale, upload):
    response = client.post("/api/enhance/image", files=upload, data={"preset": preset, "scale": scale})
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "image/png"
    with Image.open(io.BytesIO(response.content)) as output:
        output.load()
        assert output.size == (32 * scale, 24 * scale)


@pytest.mark.parametrize("endpoint", IMAGE_ENDPOINTS)
def test_decompression_bombs_return_413(endpoint, upload, neural_models, monkeypatch):
    # Exercise Pillow's real bomb detection without allocating a giant image.
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1)
    response = client.post("/api/" + endpoint, files=upload)
    assert response.status_code == 413, response.text
    assert not main.PROCESSING_LOCK.locked()


@pytest.mark.parametrize("endpoint", IMAGE_ENDPOINTS)
def test_busy_job_returns_429(endpoint, upload, neural_models):
    assert main.PROCESSING_LOCK.acquire(blocking=False)
    try:
        response = client.post("/api/" + endpoint, files=upload)
        assert response.status_code == 429, response.text
        assert main.PROCESSING_LOCK.locked()
    finally:
        main.PROCESSING_LOCK.release()


@pytest.mark.parametrize("endpoint,operation", [
    ("analyze", "inspect"), ("enhance/image", "enhance"),
    ("enhance/onnx", "onnx_upscale"), ("enhance/fsrcnn", "fsrcnn_upscale"),
    ("enhance/espcn", "espcn_upscale"),
])
def test_processing_failure_releases_lock(endpoint, operation, upload, neural_models, monkeypatch):
    def fail(*args, **kwargs):
        assert main.PROCESSING_LOCK.locked()
        raise ValueError("invalid image data")
    monkeypatch.setattr(main, operation, fail)
    response = client.post("/api/" + endpoint, files=upload)
    assert response.status_code == 400
    assert not main.PROCESSING_LOCK.locked()


@pytest.mark.parametrize("endpoint", IMAGE_ENDPOINTS[1:])
@pytest.mark.parametrize("failure", [False, True])
def test_encoding_holds_lock_and_releases_it(endpoint, failure, upload, neural_models, monkeypatch):
    original_save = Image.Image.save
    encoded = Mock()
    def save(image, *args, **kwargs):
        assert main.PROCESSING_LOCK.locked()
        encoded()
        if failure:
            raise OSError("encoding failed")
        return original_save(image, *args, **kwargs)
    monkeypatch.setattr(Image.Image, "save", save)
    response = client.post("/api/" + endpoint, files=upload)
    assert response.status_code == (400 if failure else 200), response.text
    encoded.assert_called_once()
    assert not main.PROCESSING_LOCK.locked()


def test_processing_does_not_block_status_or_busy_response(upload, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    def slow_enhance(image, *args):
        entered.set()
        assert release.wait(5), "test did not release processing"
        return image.copy(), {}
    monkeypatch.setattr(main, "enhance", slow_enhance)
    monkeypatch.setattr(main, "detect_hardware", lambda: {})
    with TestClient(main.app) as concurrent_client:
        result = []
        worker = threading.Thread(target=lambda: result.append(concurrent_client.post("/api/enhance/image", files=upload)))
        worker.start()
        try:
            assert entered.wait(3), "processing did not begin"
            # On an async blocking endpoint this timer releases the event loop;
            # the response then arrives only after processing has ended.
            timer = threading.Timer(2, release.set)
            timer.start()
            try:
                assert concurrent_client.get("/api/status").status_code == 200
                assert not release.is_set(), "status waited for image processing"
                busy = concurrent_client.post("/api/enhance/image", files=upload)
                assert busy.status_code == 429
                assert not release.is_set(), "busy response waited for processing"
            finally:
                timer.cancel()
        finally:
            release.set()
            worker.join(timeout=5)
        assert not worker.is_alive()
        assert result[0].status_code == 200
    assert not main.PROCESSING_LOCK.locked()


@pytest.mark.parametrize("endpoint", IMAGE_ENDPOINTS + ["enhance/video"])
def test_processing_routes_use_threadpool(endpoint):
    import inspect
    route = next(route for route in main.app.routes if getattr(route, "path", None) == "/api/" + endpoint)
    assert not inspect.iscoroutinefunction(route.endpoint)


def test_upload_reader_stops_at_limit(monkeypatch):
    from fastapi import HTTPException, UploadFile
    monkeypatch.setattr(main, "MAX_UPLOAD", 10)
    stream = io.BytesIO(b"x" * 100)
    with pytest.raises(HTTPException) as error:
        main.read_limited(UploadFile(file=stream))
    assert error.value.status_code == 413
    assert stream.tell() == 11


@pytest.mark.parametrize("busy", [False, True])
def test_video_lock_is_preserved_when_busy_and_released_on_failure(upload, monkeypatch, busy):
    import subprocess
    monkeypatch.setattr(main.shutil, "which", lambda binary: "/usr/bin/" + binary)
    def run(command, **kwargs):
        if command[0] == "ffprobe":
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"streams": [{"width": 32, "height": 24, "duration": "1"}]}))
        assert main.PROCESSING_LOCK.locked()
        raise subprocess.CalledProcessError(1, command)
    monkeypatch.setattr(main.subprocess, "run", run)
    if busy:
        assert main.PROCESSING_LOCK.acquire(blocking=False)
    try:
        response = client.post("/api/enhance/video", files=upload)
        assert response.status_code == (429 if busy else 422), response.text
        assert main.PROCESSING_LOCK.locked() == busy
    finally:
        if busy:
            main.PROCESSING_LOCK.release()


@pytest.mark.parametrize("metadata,expected", [
    ({"streams": [{"width": 32, "height": 24}]}, 422),
    ({"streams": [{"width": 32, "height": 24, "duration": "N/A"}]}, 422),
    *[({"streams": [{"width": 32, "height": 24, "duration": value}]}, expected)
      for value, expected in [("nan", 422), ("inf", 422), ("0", 422), ("-1", 422), ("61", 413)]],
    ({"streams": []}, 422),
    ([], 422),
    ({"streams": [None]}, 422),
    ({"streams": [{"width": 32, "height": 24, "duration": "1"}], "format": {"duration": "61"}}, 413),
    ({"streams": [{"width": 0, "height": 24, "duration": "1"}]}, 422),
    ({"streams": [{"width": 1, "height": 3, "duration": "1"}]}, 413),
])
def test_video_rejects_invalid_or_oversized_metadata(metadata, expected, upload, monkeypatch):
    import subprocess
    monkeypatch.setattr(main.shutil, "which", lambda binary: binary)
    monkeypatch.setattr(main, "LITE_MAX_PIXELS", 7)
    run = Mock(return_value=subprocess.CompletedProcess([], 0, stdout=json.dumps(metadata)))
    monkeypatch.setattr(main.subprocess, "run", run)
    response = client.post("/api/enhance/video", files=upload, data={"scale": 1})
    assert response.status_code == expected, response.text
    run.assert_called_once()
    assert not main.PROCESSING_LOCK.locked()


@pytest.mark.parametrize("stage", ["ffprobe", "ffmpeg"])
def test_video_timeouts_release_lock(stage, upload, monkeypatch):
    import subprocess
    monkeypatch.setattr(main.shutil, "which", lambda binary: binary)
    def run(command, **kwargs):
        assert main.PROCESSING_LOCK.locked()
        if command[0] == stage:
            raise subprocess.TimeoutExpired(command, 1)
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"streams": [{"width": 32, "height": 24}], "format": {"duration": "1"}}))
    monkeypatch.setattr(main.subprocess, "run", run)
    response = client.post("/api/enhance/video", files=upload)
    assert response.status_code == 422
    assert not main.PROCESSING_LOCK.locked()


def test_video_output_cap_checked_before_read(upload, monkeypatch):
    import subprocess
    monkeypatch.setattr(main.shutil, "which", lambda binary: binary)
    monkeypatch.setattr(main, "MAX_VIDEO_OUTPUT", 3)
    def run(command, **kwargs):
        if command[0] == "ffprobe":
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"streams": [{"width": 32, "height": 24, "duration": "1"}]}))
        Path(command[-1]).write_bytes(b"large output")
        return subprocess.CompletedProcess(command, 0)
    monkeypatch.setattr(main.subprocess, "run", run)
    # A capped response must never allocate the resulting file into memory.
    monkeypatch.setattr(Path, "read_bytes", Mock(side_effect=AssertionError("oversized file was read")))
    response = client.post("/api/enhance/video", files=upload)
    assert response.status_code == 413
    assert not main.PROCESSING_LOCK.locked()


def test_real_ffmpeg_accepts_odd_dimensions_and_pads_output(tmp_path):
    import shutil
    import subprocess
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("FFmpeg integration requires ffmpeg and ffprobe")
    source = tmp_path / "odd.mkv"
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i",
                    "testsrc=size=33x25:rate=2", "-t", "0.5", "-c:v", "ffv1", str(source)],
                   check=True, capture_output=True, timeout=20)
    response = client.post("/api/enhance/video", files={"file": ("odd.mkv", source.read_bytes(), "video/x-matroska")}, data={"preset": "natural", "scale": 1})
    assert response.status_code == 200, response.text
    output = tmp_path / "enhanced.mp4"
    output.write_bytes(response.content)
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", str(output)], check=True, capture_output=True, text=True, timeout=20)
    stream = json.loads(probe.stdout)["streams"][0]
    assert (stream["width"], stream["height"]) == (34, 26)
    assert response.headers["content-type"] == "video/mp4"
    assert not main.PROCESSING_LOCK.locked()


def test_real_ffmpeg_processes_the_probed_stream(tmp_path, monkeypatch):
    import shutil
    import subprocess
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("FFmpeg integration requires ffmpeg and ffprobe")
    source = tmp_path / "multiple.mkv"
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error",
                    "-f", "lavfi", "-i", "testsrc=size=32x24:rate=2",
                    "-f", "lavfi", "-i", "testsrc=size=128x96:rate=2",
                    "-map", "0:v:0", "-map", "1:v:0", "-t", "0.5",
                    "-c:v", "ffv1", "-disposition:v:0", "0",
                    "-disposition:v:1", "default", str(source)],
                   check=True, capture_output=True, timeout=20)
    monkeypatch.setattr(main, "LITE_MAX_PIXELS", 1000)
    response = client.post("/api/enhance/video", files={"file": ("multiple.mkv", source.read_bytes(), "video/x-matroska")}, data={"preset": "natural", "scale": 1})
    assert response.status_code == 200, response.text
    output = tmp_path / "first-stream.mp4"
    output.write_bytes(response.content)
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height", "-of", "json", str(output)], check=True, capture_output=True, text=True, timeout=20)
    assert [(stream["width"], stream["height"]) for stream in json.loads(probe.stdout)["streams"]] == [(32, 24)]
    assert not main.PROCESSING_LOCK.locked()
