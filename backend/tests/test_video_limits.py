"""Regression tests for video workload preflight without external codecs."""
import pytest
from app.video_limits import validate_video_workload


@pytest.mark.parametrize("fps,duration,pixels", [
    ("30/1", 5, 640 * 480),
    ("30000/1001", 1, 640 * 480),
    (None, 5, 640 * 480),
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
])
def test_extreme_workload_rejected(fps, duration, pixels):
    with pytest.raises(OverflowError):
        validate_video_workload({"avg_frame_rate": fps}, duration, pixels)
