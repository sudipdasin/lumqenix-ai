"""Reject malformed FFprobe dimensions before FFmpeg starts or CPU costs accrue."""
import json
import subprocess
from unittest.mock import Mock

import pytest

from app.video_limits import validate_video_dimensions


@pytest.mark.parametrize("width,height,expected", [
    (64, 48, (64, 48)),
    ("64", "48", (64, 48)),
    ("00064", 48, (64, 48)),
    (16384, 1, (16384, 1)),
])
def test_video_dimensions_accept_exact_integer_geometry(width, height, expected):
    assert validate_video_dimensions({"width": width, "height": height}) == expected


@pytest.mark.parametrize("bad", [
    True, False, 64.1, 64.0, None, "64.5", "-64", "+64",
    "٤٢", "9" * 100, 0, -1, 16385, {}, [],
])
def test_video_dimensions_reject_malformed_metadata(bad):
    with pytest.raises(ValueError):
        validate_video_dimensions({"width": bad, "height": 48})
    with pytest.raises(ValueError):
        validate_video_dimensions({"width": 64, "height": bad})


def test_video_dimensions_reject_non_mapping_stream():
    with pytest.raises(ValueError):
        validate_video_dimensions(["width", "height"])


@pytest.mark.parametrize("bad_geometry", [
    {"width": 21.9, "height": 10},
    {"width": True, "height": 10},
    {"width": 64, "height": "١٢"},
    {"width": 16385, "height": 1},
])
def test_api_rejects_bad_probe_geometry_before_ffmpeg(monkeypatch, bad_geometry):
    from fastapi.testclient import TestClient
    from app import main

    monkeypatch.setattr(main.shutil, "which", lambda tool: "/usr/bin/" + tool)
    probe = subprocess.CompletedProcess(
        ["ffprobe"], 0,
        stdout=json.dumps({"streams": [{**bad_geometry, "duration": "1",
                                       "avg_frame_rate": "24/1"}]}),
    )
    mocked = Mock(return_value=probe)
    monkeypatch.setattr(main.subprocess, "run", mocked)
    response = TestClient(main.app).post(
        "/api/enhance/video",
        files={"file": ("invalid.mkv", b"fake video", "video/x-matroska")},
        data={"preset": "natural", "scale": 1},
    )
    assert response.status_code == 422, response.text
    mocked.assert_called_once()
    assert mocked.call_args.args[0][0] == "ffprobe"
    assert not main.PROCESSING_LOCK.locked()
