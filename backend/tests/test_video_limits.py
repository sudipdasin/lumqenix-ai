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
