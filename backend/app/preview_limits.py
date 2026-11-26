"""Safe, transparent CPU and upload budgets for public Lumqenix previews.

The local desktop app retains its established limits. A cloud host must set
LUMQENIX_PUBLIC_PREVIEW=1; previews start with video processing disabled.
"""
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class Limits:
    public_preview: bool
    max_upload: int
    max_video_output: int
    max_video_duration: int
    max_image_pixels: int
    lite_max_output_pixels: int
    video_enabled: bool


def settings_for_environment(environment: Mapping[str, str]) -> Limits:
    raw = environment.get("LUMQENIX_PUBLIC_PREVIEW", "")
    # A nonempty value other than explicit "0" or "false" is fail-closed.
    public = bool(raw) and raw.strip().lower() not in ("0", "false", "off", "no")
    enable_video = environment.get("LUMQENIX_PREVIEW_VIDEO", "") == "ALLOW_VIDEO_AFTER_VALIDATION"
    if public:
        return Limits(
            public_preview=True,
            max_upload=8 * 1024 * 1024,
            max_video_output=24 * 1024 * 1024,
            max_video_duration=12,
            max_image_pixels=5_000_000,
            lite_max_output_pixels=2_500_000,
            video_enabled=enable_video,
        )
    return Limits(
        public_preview=False,
        max_upload=50 * 1024 * 1024,
        max_video_output=100 * 1024 * 1024,
        max_video_duration=60,
        max_image_pixels=32_000_000,
        lite_max_output_pixels=12_000_000,
        video_enabled=True,
    )
