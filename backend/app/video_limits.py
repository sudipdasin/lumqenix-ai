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

MAX_VIDEO_AXIS = 16384


def validate_video_dimensions(stream: dict) -> tuple[int, int]:
    """Parse untrusted ffprobe dimensions without lossy coercion or booleans.

    Reject JSON floating-point dimensions (int(64.5) would incorrectly
    truncate them) and extremely large/unusual numeric values before FFmpeg.
    """
    if not isinstance(stream, dict):
        raise ValueError("Invalid video stream metadata")
    dimensions = []
    for key in ("width", "height"):
        value = stream.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, str)):
            raise ValueError("Invalid video dimensions")
        raw = str(value)
        if not raw.isascii() or not raw.isdecimal() or len(raw) > 10:
            raise ValueError("Invalid video dimensions")
        number = int(raw)
        if number <= 0 or number > MAX_VIDEO_AXIS:
            raise ValueError("Unsupported video dimensions")
        dimensions.append(number)
    return dimensions[0], dimensions[1]



def _parse_rate(value, *, clamp_nominal=False):
    if value is None or value == "" or value == "N/A" or value == "0/0":
        return None
    # ffprobe metadata is untrusted: bound parsing cost and reject booleans,
    # non-ASCII digits and arbitrarily large rational numerators/denominators.
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError("Invalid video frame rate")
    raw = str(value)
    if len(raw) > 64 or not raw.isascii():
        raise ValueError("Invalid video frame rate")
    try:
        fps = Fraction(raw)
    except (TypeError, ValueError, ZeroDivisionError, OverflowError) as exc:
        raise ValueError("Invalid video frame rate") from exc
    if fps <= 0:
        raise ValueError("Unsupported video frame rate")
    if fps > MAX_SUPPORTED_FPS:
        if clamp_nominal:
            # Matroska/FFV1 can advertise a 1000 fps codec timebase even
            # though average frame rate is 2 fps. Budget the supported
            # maximum when an independent valid average is present.
            return Fraction(MAX_SUPPORTED_FPS, 1)
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
    average_rate = _parse_rate(stream.get("avg_frame_rate"))
    nominal_rate = _parse_rate(stream.get("r_frame_rate"), clamp_nominal=average_rate is not None)
    rates = [average_rate, nominal_rate]
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
