"""Regression tests for video workload preflight without external codecs."""
import pytest
from app.video_limits import validate_video_workload

@pytest.mark.parametrize("fps,duration,pixels", [
    ("30/1", 5, 640 * 480),
    ("30000/1001", 1, 640 * 480),
    (None, 0.5, 640 * 480),
])
def test_acceptable_video(fps, duration, pixels):
    validate_video_workload({"avg_frame_rate": fps}, duration, pixels)

@pytest.mark.parametrize("fps", ["abc", "1/0", "-1/1", "1000/1"])
def test_invalid_rate_rejected(fps):
    with pytest.raises(ValueError):
        validate_video_workload({"avg_frame_rate": fps}, 1, 640 * 480)

@pytest.mark.parametrize("fps,duration,pixels", [
    ("60/1", 60, 1920 * 1080),
    ("60/1", 40, 320 * 240),
    (None, 60, 640 * 480),
])
def test_extreme_workload_rejected(fps, duration, pixels):
    with pytest.raises(OverflowError):
        validate_video_workload({"avg_frame_rate": fps}, duration, pixels)

@pytest.mark.parametrize("duration", [-1, 0, float('nan'), float('inf'), '2', True])
def test_invalid_duration_rejected(duration):
    with pytest.raises(ValueError):
        validate_video_workload({'avg_frame_rate': '30/1'}, duration, 100)

@pytest.mark.parametrize("pixels", [-1, 0, 1.5, True, '500'])
def test_invalid_pixels_rejected(pixels):
    with pytest.raises(ValueError):
        validate_video_workload({'avg_frame_rate': '30/1'}, 1, pixels)

def test_both_rates_use_conservative_maximum():
    with pytest.raises(OverflowError):
        validate_video_workload({'avg_frame_rate': '1/1', 'r_frame_rate': '240/1'}, 10, 100)

def test_fallback_to_second_rate():
    validate_video_workload({'avg_frame_rate': '0/0', 'r_frame_rate': '24/1'}, 5, 320 * 240)

def test_unknown_rate_does_not_bypass_limits():
    with pytest.raises(OverflowError):
        validate_video_workload({}, 10, 320 * 240)

def test_bad_second_rate_cannot_hide_behind_valid_first_rate():
    with pytest.raises(ValueError):
        validate_video_workload({'avg_frame_rate': '24/1', 'r_frame_rate': 'broken'}, 1, 100)

@pytest.mark.parametrize("count", ["999999999999999999999", "-1", "1.5", "0", "12x", True, 1.5])
def test_invalid_declared_frame_count(count):
    with pytest.raises(ValueError):
        validate_video_workload({"avg_frame_rate": "24/1", "nb_frames": count}, 1, 100)


def test_vfr_declared_frames_cannot_bypass_frame_budget():
    with pytest.raises(OverflowError):
        validate_video_workload({"avg_frame_rate": "1/1", "nb_frames": "1801"}, 1, 100)


def test_vfr_declared_frames_cannot_bypass_sample_budget():
    with pytest.raises(OverflowError):
        validate_video_workload({"avg_frame_rate": "1/1", "nb_frames": "1500"}, 1, 400000)


def test_normal_declared_frame_count_is_accepted():
    validate_video_workload({"avg_frame_rate": "24/1", "nb_frames": "120"}, 5, 640 * 480)


def test_missing_declared_frame_count_is_accepted():
    validate_video_workload({"avg_frame_rate": "24/1", "nb_frames": "N/A"}, 5, 640 * 480)


def test_ffprobe_query_includes_declared_frame_count():
    """Guard the endpoint wiring: nb_frames must reach workload preflight."""
    from pathlib import Path
    import ast

    source = (Path(__file__).resolve().parents[1] / "app" / "main.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Attribute) and node.func.attr == "run"]
    ffprobe_commands = []
    for call in calls:
        if not call.args or not isinstance(call.args[0], ast.List):
            continue
        elements = call.args[0].elts
        if elements and isinstance(elements[0], ast.Constant) and elements[0].value == "ffprobe":
            ffprobe_commands.append([item.value for item in elements if isinstance(item, ast.Constant)])
    assert len(ffprobe_commands) == 1
    args = ffprobe_commands[0]
    entries = args[args.index("-show_entries") + 1]
    assert "nb_frames" in entries.split(":")[0].split("=")[1].split(",")


def test_declared_frame_count_rejected_even_when_fps_estimate_is_small():
    with pytest.raises(OverflowError):
        validate_video_workload({"avg_frame_rate": "1/1", "nb_frames": "1801"}, 1, 64 * 64)


@pytest.mark.parametrize("rate", [
    True, False, "9" * 10000, "١/٢", object(),
])
def test_untrusted_frame_rate_rejected_before_fraction_parsing(rate):
    with pytest.raises(ValueError, match="Invalid video frame rate"):
        validate_video_workload({"avg_frame_rate": rate}, 1, 640 * 480)


@pytest.mark.parametrize("rate", [24, 29.97, "30000/1001"])
def test_normal_numeric_frame_rate_metadata_remains_supported(rate):
    validate_video_workload({"avg_frame_rate": rate}, 1, 640 * 480)


def test_matroska_codec_timebase_does_not_reject_short_valid_video():
    # Reproduces real FFprobe metadata from FFV1/Matroska at 2 FPS.
    validate_video_workload({"avg_frame_rate": "2/1", "r_frame_rate": "1000/1"}, 0.5, 34 * 26)


def test_matroska_nominal_rate_is_conservatively_capped_for_budget():
    # The nominal rate is not discarded: 240 FPS * 10 s exceeds 1800 frames.
    with pytest.raises(OverflowError, match="Video workload"):
        validate_video_workload({"avg_frame_rate": "2/1", "r_frame_rate": "1000/1"}, 10, 34 * 26)


def test_unsupported_nominal_rate_without_valid_average_fails_closed():
    with pytest.raises(ValueError, match="Unsupported video frame rate"):
        validate_video_workload({"r_frame_rate": "1000/1"}, 0.5, 34 * 26)


@pytest.mark.parametrize("bad_nominal", [False, "0/1", "-2/1", "9" * 10000, object()])
def test_invalid_nominal_metadata_cannot_hide_behind_average(bad_nominal):
    with pytest.raises(ValueError):
        validate_video_workload({"avg_frame_rate": "2/1", "r_frame_rate": bad_nominal}, 0.5, 34 * 26)


def test_actual_declared_frames_still_override_optimistic_average():
    with pytest.raises(OverflowError, match="Video workload"):
        validate_video_workload({"avg_frame_rate": "2/1", "r_frame_rate": "1000/1", "nb_frames": "1801"}, 0.5, 34 * 26)


@pytest.mark.parametrize("metadata,reason", [
    ({"streams": [{"width": 64, "height": 64, "duration": "1", "avg_frame_rate": "1/1", "nb_frames": "1801"}]}, "frame count"),
    ({"streams": [{"width": 1920, "height": 1080, "duration": "4", "avg_frame_rate": "60/1"}]}, "total samples"),
    ({"streams": [{"width": 64, "height": 64, "duration": "10"}]}, "unknown frame rate"),
])
def test_endpoint_rejects_cpu_budget_before_ffmpeg(monkeypatch, metadata, reason):
    import json
    import subprocess
    from unittest.mock import Mock
    from fastapi.testclient import TestClient
    from app import main

    monkeypatch.setattr(main.shutil, "which", lambda binary: binary)
    probe = subprocess.CompletedProcess([], 0, stdout=json.dumps(metadata))
    run = Mock(return_value=probe)
    monkeypatch.setattr(main.subprocess, "run", run)
    response = TestClient(main.app).post(
        "/api/enhance/video", files={"file": ("input.mkv", b"sample", "video/x-matroska")},
        data={"preset": "natural", "scale": "1"},
    )
    assert response.status_code == 413, (reason, response.text)
    assert "workload" in response.json()["detail"].lower()
    run.assert_called_once()
    assert not main.PROCESSING_LOCK.locked()


def test_community_edition_api_remains_available_without_model_weights(monkeypatch):
    from fastapi.testclient import TestClient
    from app import main
    monkeypatch.delenv("LUMQENIX_FSRCNN_MODEL", raising=False)
    monkeypatch.delenv("LUMQENIX_ESPCN_MODEL", raising=False)
    response = TestClient(main.app).get("/api/edition")
    assert response.status_code == 200
    data = response.json()
    assert data["edition"] == "community"
    assert data["contract_version"] == 1
    assert data["proprietary_code_bundled"] is False
    assert "classic-video-enhancement" in data["capabilities"]
