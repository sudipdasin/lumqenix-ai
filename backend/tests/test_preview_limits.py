"""Public-preview caps remain isolated from the installed Linux edition."""
from app.preview_limits import settings_for_environment


def test_desktop_limits_remain_unchanged():
    limits = settings_for_environment({})
    assert not limits.public_preview
    assert limits.video_enabled
    assert limits.max_upload == 50 * 1024 * 1024
    assert limits.max_video_duration == 60
    assert limits.max_image_pixels == 32_000_000
    assert limits.lite_max_output_pixels == 12_000_000


def test_cloud_limits_fail_closed():
    limits = settings_for_environment({"LUMQENIX_PUBLIC_PREVIEW": "1"})
    assert limits.public_preview
    assert not limits.video_enabled
    assert limits.max_upload == 8 * 1024 * 1024
    assert limits.max_video_duration == 12
    assert limits.max_image_pixels == 5_000_000
    assert limits.lite_max_output_pixels == 2_500_000


def test_unrecognized_nonempty_cloud_flag_defaults_to_restricted():
    assert settings_for_environment({"LUMQENIX_PUBLIC_PREVIEW": "maybe"}).public_preview
    assert not settings_for_environment({"LUMQENIX_PUBLIC_PREVIEW": "yes"}).video_enabled


def test_cloud_video_requires_explicit_post_validation_flag():
    env = {"LUMQENIX_PUBLIC_PREVIEW": "1"}
    assert not settings_for_environment({**env, "LUMQENIX_PREVIEW_VIDEO": "1"}).video_enabled
    assert settings_for_environment({
        **env, "LUMQENIX_PREVIEW_VIDEO": "ALLOW_VIDEO_AFTER_VALIDATION"
    }).video_enabled


def test_explicit_disabled_cloud_flags_keep_desktop_limits():
    for value in ("0", "false", "off", "no"):
        assert not settings_for_environment({"LUMQENIX_PUBLIC_PREVIEW": value}).public_preview
