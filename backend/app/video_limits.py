"""Conservative CPU video workload estimator for constrained Community installs."""
from fractions import Fraction
import math

MAX_ESTIMATED_OUTPUT_SAMPLES = 450_000_000
MAX_ESTIMATED_FRAMES = 1800


def validate_video_workload(stream: dict, duration: float, output_pixels: int) -> None:
    """Reject extreme video workloads before starting expensive FFmpeg transcoding.

    FPS metadata may be missing or unreliable. A missing FPS is handled by
    FFmpeg's existing execution timeout, rather than falsely rejecting files.
    """
    rate = stream.get("avg_frame_rate") or stream.get("r_frame_rate")
    if rate in (None, "", "N/A", "0/0"):
        return
    try:
        fps = Fraction(str(rate))
    except (ValueError, ZeroDivisionError, OverflowError) as exc:
        raise ValueError("Invalid video frame rate") from exc
    if fps <= 0 or fps > 240:
        raise ValueError("Unsupported video frame rate")
    frames = math.ceil(float(fps) * duration)
    if frames > MAX_ESTIMATED_FRAMES or frames * output_pixels > MAX_ESTIMATED_OUTPUT_SAMPLES:
        raise OverflowError("Video workload exceeds Lite CPU budget")
