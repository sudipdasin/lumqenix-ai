"""Conservative CPU video workload estimator for constrained Community installs.

Untrusted ffprobe metadata is checked before FFmpeg processing. Missing FPS is
estimated conservatively from the supported 240 FPS maximum, never accepted as
an unlimited workload. The limit is a compute budget, not a RAM guarantee.
"""
from fractions import Fraction
import math

MAX_ESTIMATED_OUTPUT_SAMPLES = 450_000_000
MAX_ESTIMATED_FRAMES = 1800
MAX_SUPPORTED_FPS = 240


def _parse_rate(value):
    if value is None or value == "" or value == "N/A" or value == "0/0":
        return None
    try:
        fps = Fraction(str(value))
    except (TypeError, ValueError, ZeroDivisionError, OverflowError) as exc:
        raise ValueError("Invalid video frame rate") from exc
    if fps <= 0 or fps > MAX_SUPPORTED_FPS:
        raise ValueError("Unsupported video frame rate")
    return fps


def validate_video_workload(stream: dict, duration: float, output_pixels: int) -> None:
    """Reject videos whose upper-bound frame/pixel work exceeds the Lite budget.

    When both FPS fields are available, use the larger valid rate. Missing FPS
    uses a conservative 240 FPS ceiling rather than silently bypassing limits.
    """
    if not isinstance(stream, dict):
        raise ValueError("Invalid video stream metadata")
    if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0:
        raise ValueError("Invalid video duration")
    if isinstance(output_pixels, bool) or not isinstance(output_pixels, int) or output_pixels <= 0:
        raise ValueError("Invalid output pixel count")
    rates = [_parse_rate(stream.get(key)) for key in ("avg_frame_rate", "r_frame_rate")]
    known = [rate for rate in rates if rate is not None]
    fps = max(known) if known else Fraction(MAX_SUPPORTED_FPS, 1)
    # Early bounds avoid huge multiplications for untrusted metadata.
    if duration > MAX_ESTIMATED_FRAMES / float(fps):
        raise OverflowError("Video workload exceeds Lite CPU budget")
    frames = math.ceil(float(fps) * duration)
    if frames > MAX_ESTIMATED_FRAMES or frames * output_pixels > MAX_ESTIMATED_OUTPUT_SAMPLES:
        raise OverflowError("Video workload exceeds Lite CPU budget")
    # A container can advertise a low average FPS while reporting many actual
    # frames (variable-frame-rate content or inconsistent metadata). Treat the
    # explicit frame count as an additional lower bound, never a replacement for
    # the conservative FPS-derived estimate.
    declared_frames = stream.get("nb_frames")
    if declared_frames not in (None, "", "N/A"):
        if isinstance(declared_frames, bool) or not isinstance(declared_frames, (int, str)):
            raise ValueError("Invalid video frame count")
        digits = str(declared_frames)
        if not digits.isascii() or not digits.isdecimal() or len(digits) > 12:
            raise ValueError("Invalid video frame count")
        declared = int(digits)
        if declared <= 0:
            raise ValueError("Invalid video frame count")
        if declared > MAX_ESTIMATED_FRAMES or declared * output_pixels > MAX_ESTIMATED_OUTPUT_SAMPLES:
            raise OverflowError("Video workload exceeds Lite CPU budget")
