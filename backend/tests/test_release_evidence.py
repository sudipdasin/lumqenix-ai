"""Release evidence gate regression tests: no fabricated passes."""
from copy import deepcopy

import pytest

from scripts.validate_release_evidence import EvidenceError, validate, validate_scene_bundle


def good_documents():
    hash_value = "a" * 64
    perf = {}
    quality = {
        "dataset": "deterministic-synthetic-textures-v1",
        "reference_dimensions": [256, 256],
        "baseline_bicubic": {"mae_rgb": 10.0, "mse_rgb": 120.0, "psnr_rgb_db": 27.3},
        "models": {},
    }
    for name in ("fsrcnn", "espcn"):
        perf[name] = {"status": "ok", "model_sha256": hash_value,
                      "max_rss_bytes": 100 * 1024 ** 2, "warm_seconds": [0.2]}
        quality["models"][name] = {
            "execution": {"status": "ok", "model_sha256": hash_value},
            "quality": {"dimensions": [256, 256],
                        "prediction_metrics": {"mae_rgb": 9.0, "mse_rgb": 100.0, "psnr_rgb_db": 28.1},
                        "baseline_metrics": {"mae_rgb": 10.0, "mse_rgb": 120.0, "psnr_rgb_db": 27.3}},
        }
    api = {"output_format": "PNG", "peak_process_rss_mib": 200.0,
           "warm_seconds_median": 0.5}
    return perf, quality, api


def test_complete_evidence_passes():
    assert validate(*good_documents())["evidence_complete"] is True


@pytest.mark.parametrize("mutate", [
    lambda p, q, a: a.update(output_format="JPEG"),
    lambda p, q, a: a.update(peak_process_rss_mib=4096),
    lambda p, q, a: p["fsrcnn"].update(status="unavailable"),
    lambda p, q, a: p["espcn"].update(max_rss_bytes=4 * 1024 ** 3),
    lambda p, q, a: q["models"]["fsrcnn"]["execution"].update(model_sha256="b" * 64),
    lambda p, q, a: q["models"]["espcn"]["quality"]["prediction_metrics"].update(mae_rgb=float("nan")),
    lambda p, q, a: q.update(reference_dimensions=[128, 128]),
    lambda p, q, a: p["fsrcnn"].update(model_sha256="z" * 64),
    lambda p, q, a: q["models"]["fsrcnn"]["quality"]["baseline_metrics"].update(mae_rgb=11.0),
    lambda p, q, a: q["models"]["espcn"]["quality"]["baseline_metrics"].update(mae_rgb=9.0),
    lambda p, q, a: q["models"]["fsrcnn"]["quality"]["prediction_metrics"].update(mae_rgb=True),
    lambda p, q, a: q["models"]["espcn"]["quality"]["baseline_metrics"].update(mse_rgb=False),
    lambda p, q, a: q["models"]["fsrcnn"]["quality"]["prediction_metrics"].update(psnr_rgb_db=True),
    lambda p, q, a: q["models"]["fsrcnn"]["quality"]["baseline_metrics"].update(mse_rgb=121.0),
    lambda p, q, a: q["models"]["espcn"]["quality"]["baseline_metrics"].update(psnr_rgb_db=26.3),
    lambda p, q, a: q["baseline_bicubic"].update(mse_rgb=False),
    lambda p, q, a: q["baseline_bicubic"].update(psnr_rgb_db=float("nan")),
])
def test_bad_evidence_is_rejected(mutate):
    documents = list(deepcopy(good_documents()))
    mutate(*documents)
    with pytest.raises(EvidenceError):
        validate(*documents)


def good_scene_bundle():
    performance, texture, api = good_documents()
    reports = {}
    for scene in ("textures", "edges", "smooth"):
        report = deepcopy(texture)
        report["dataset"] = f"deterministic-synthetic-{scene}-v1"
        report["low_resolution_dimensions"] = [128, 128]
        reports[scene] = report
    return performance, reports, api


def test_six_model_scene_combinations_are_required():
    result = validate_scene_bundle(*good_scene_bundle())
    assert result["model_scene_combinations"] == 6
    assert result["scenes_verified"] == ["textures", "edges", "smooth"]


@pytest.mark.parametrize("mutate", [
    lambda p, q, a: q.pop("edges"),
    lambda p, q, a: q["smooth"].update(dataset="deterministic-synthetic-textures-v1"),
    lambda p, q, a: q["edges"]["models"]["fsrcnn"]["execution"].update(status="unavailable"),
    lambda p, q, a: q["smooth"]["models"]["espcn"]["execution"].update(model_sha256="b" * 64),
    lambda p, q, a: q["edges"]["models"]["espcn"]["quality"]["prediction_metrics"].update(mae_rgb=float("nan")),
    lambda p, q, a: q["smooth"]["models"]["fsrcnn"]["quality"]["baseline_metrics"].update(mse_rgb=999.0),
    lambda p, q, a: q["edges"].update(low_resolution_dimensions=[256, 256]),
])
def test_multiscene_evidence_fails_closed(mutate):
    documents = list(deepcopy(good_scene_bundle()))
    mutate(*documents)
    with pytest.raises(EvidenceError):
        validate_scene_bundle(*documents)
