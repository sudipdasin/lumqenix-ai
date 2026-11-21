"""Regression guard for FFmpeg duration enforcement independent of probe metadata."""
import json
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient
from app import main


def test_video_ffmpeg_command_caps_output_duration(monkeypatch):
    monkeypatch.setattr(main.shutil, "which", lambda name: name)
    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)
        if command[0] == "ffprobe":
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({
                "streams": [{"width": 32, "height": 24}], "format": {"duration": "1"}
            }))
        Path(command[-1]).write_bytes(b"mock video output")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(main.subprocess, "run", fake_run)
    response = TestClient(main.app).post(
        "/api/enhance/video",
        files={"file": ("sample.mp4", b"placeholder", "video/mp4")},
        data={"preset": "natural", "scale": "1"},
    )
    assert response.status_code == 200
    ffmpeg = next(cmd for cmd in commands if cmd[0] == "ffmpeg")
    assert "-t" in ffmpeg
    assert ffmpeg[ffmpeg.index("-t") + 1] == str(main.MAX_VIDEO_DURATION)
    assert "-fs" in ffmpeg
    assert ffmpeg[ffmpeg.index("-fs") + 1] == str(main.MAX_VIDEO_OUTPUT)
    assert not main.PROCESSING_LOCK.locked()
