"""Real-media duration rejection: metadata and endpoint agree on >60 seconds."""
import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient

from app.main import MAX_VIDEO_DURATION, app


def test_real_video_over_duration_limit_is_rejected(tmp_path):
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        pytest.skip("FFmpeg/ffprobe not installed on this runner")
    encoders = subprocess.run(
        [ffmpeg, "-hide_banner", "-encoders"],
        capture_output=True, text=True, timeout=15,
    )
    if encoders.returncode != 0 or "libx264" not in encoders.stdout:
        pytest.skip("FFmpeg libx264 encoder not available")

    # One frame per second at tiny resolution keeps this inexpensive in CPU CI.
    source = tmp_path / "over-limit.mp4"
    subprocess.run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
         "-f", "lavfi", "-i", "color=c=blue:s=16x16:r=1",
         "-t", str(MAX_VIDEO_DURATION + 2), "-an",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source)],
        check=True, capture_output=True, timeout=40,
    )
    probe = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(source)],
        check=True, capture_output=True, text=True, timeout=15,
    )
    assert float(probe.stdout.strip()) > MAX_VIDEO_DURATION

    response = TestClient(app).post(
        "/api/enhance/video",
        files={"file": ("over-limit.mp4", source.read_bytes(), "video/mp4")},
        data={"preset": "natural", "scale": "2"},
    )
    assert response.status_code == 413, response.text
    assert "duration limit" in response.json()["detail"].lower()
