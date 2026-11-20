"""Real FFmpeg integration smoke test using generated, non-proprietary video.

Unlike subprocess-mocked endpoint tests, this exercises ffprobe, the filter graph,
libx264 encoding and the MP4 response. Skips only when required binaries/codecs
are absent from the test host.
"""
import io
import json
import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_real_ffmpeg_video_roundtrip(tmp_path):
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        pytest.skip("FFmpeg/ffprobe not installed on this runner")
    codecs = subprocess.run(
        [ffmpeg, "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=15
    )
    if codecs.returncode != 0 or "libx264" not in codecs.stdout:
        pytest.skip("FFmpeg libx264 encoder not available")
    source = tmp_path / "generated.mp4"
    subprocess.run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
         "-f", "lavfi", "-i", "testsrc2=size=32x24:rate=5",
         "-t", "1", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
         str(source)],
        check=True, capture_output=True, timeout=30,
    )
    response = TestClient(app).post(
        "/api/enhance/video",
        files={"file": ("generated.mp4", source.read_bytes(), "video/mp4")},
        data={"preset": "natural", "scale": "2"},
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("video/mp4")
    assert response.content
    output = tmp_path / "enhanced.mp4"
    output.write_bytes(response.content)
    probe = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height:format=duration", "-of", "json", str(output)],
        check=True, capture_output=True, text=True, timeout=20,
    )
    stream = json.loads(probe.stdout)["streams"][0]
    assert (stream["width"], stream["height"]) == (64, 48)

    # Measure the encoded MP4 rather than trusting the constructed FFmpeg command.
    # The one-second generated input must remain finite and bounded after processing.
    duration = float(json.loads(probe.stdout)["format"]["duration"])
    assert 0 < duration <= 1.5, f"Unexpected encoded output duration: {duration}"
