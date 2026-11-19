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
        "low_resolution_dimensions": [128, 128],
        "baseline_bicubic": {"mae_rgb": 10.0, "mse_rgb": 120.0, "psnr_rgb_db": 27.3},
        "models": {},
    }
    for name in ("fsrcnn", "espcn"):
        perf[name] = {"status": "ok", "model_sha256": hash_value,
                      "max_rss_bytes": 100 * 1024 ** 2, "warm_seconds": [0.2]}
        quality["models"][name] = {
            "execution": {"status": "ok", "model": name, "model_sha256": hash_value,
                          "input_dimensions": [128, 128], "output_dimensions": [256, 256],
                          "max_rss_bytes": 100 * 1024 ** 2, "warm_seconds": [0.2]},
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


def test_quality_summary_has_six_explicit_comparisons():
    result = validate_scene_bundle(*good_scene_bundle())
    rows = result["quality_summary"]
    assert len(rows) == 6
    assert {(row["scene"], row["model"]) for row in rows} == {
        (scene, model) for scene in ("textures", "edges", "smooth")
        for model in ("fsrcnn", "espcn")
    }
    assert all(row["mae_improvement_vs_bicubic"] == 1 for row in rows)
    assert all(row["psnr_delta_db_vs_bicubic"] == pytest.approx(0.8) for row in rows)


def test_quality_summary_reports_worse_than_bicubic_without_hiding_it():
    performance, reports, api = good_scene_bundle()
    reports["edges"]["models"]["fsrcnn"]["quality"]["prediction_metrics"]["mae_rgb"] = 15.0
    result = validate_scene_bundle(performance, reports, api)
    row = next(row for row in result["quality_summary"]
               if row["scene"] == "edges" and row["model"] == "fsrcnn")
    assert row["mae_improvement_vs_bicubic"] == -5.0
    assert row["beats_bicubic_on_mae"] is False


def test_missing_low_resolution_dimensions_rejected():
    performance, quality, api = good_documents()
    quality.pop("low_resolution_dimensions", None)
    with pytest.raises(EvidenceError):
        validate(performance, quality, api)


@pytest.mark.parametrize("mutate", [
    lambda p, q, a: q["edges"]["models"]["fsrcnn"]["execution"].update(max_rss_bytes=4 * 1024 ** 3),
    lambda p, q, a: q["smooth"]["models"]["espcn"]["execution"].update(warm_seconds=[]),
    lambda p, q, a: q["textures"]["models"]["fsrcnn"]["execution"].update(model="espcn"),
    lambda p, q, a: q["edges"]["models"]["espcn"]["execution"].update(output_dimensions=[128, 128]),
    lambda p, q, a: q["smooth"]["models"]["fsrcnn"]["execution"].update(warm_seconds=[float("nan")]),
])
def test_scene_worker_evidence_is_checked_independently(mutate):
    documents = list(deepcopy(good_scene_bundle()))
    mutate(*documents)
    with pytest.raises(EvidenceError):
        validate_scene_bundle(*documents)


@pytest.mark.parametrize("scene", ["edges", "smooth"])
@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), -float("inf"), True, "27.3"])
def test_nontexture_bicubic_psnr_must_be_finite_numeric(scene, invalid):
    performance, reports, api = good_scene_bundle()
    reports[scene]["baseline_bicubic"]["psnr_rgb_db"] = invalid
    for model in ("fsrcnn", "espcn"):
        reports[scene]["models"][model]["quality"]["baseline_metrics"]["psnr_rgb_db"] = invalid
    with pytest.raises(EvidenceError):
        validate_scene_bundle(performance, reports, api)


@pytest.mark.parametrize("mutate", [
    lambda p, q, a: q.__setitem__("edges", None),
    lambda p, q, a: q["edges"].__setitem__("models", None),
    lambda p, q, a: q["smooth"]["models"].__setitem__("fsrcnn", None),
    lambda p, q, a: q["edges"]["models"]["espcn"].__setitem__("execution", None),
    lambda p, q, a: q["smooth"]["models"]["fsrcnn"].__setitem__("quality", None),
    lambda p, q, a: q["edges"]["models"]["espcn"]["quality"].__setitem__("baseline_metrics", None),
])
def test_malformed_multiscene_evidence_fails_closed(mutate):
    documents = list(deepcopy(good_scene_bundle()))
    mutate(*documents)
    with pytest.raises(EvidenceError):
        validate_scene_bundle(*documents)
