"""Quality benchmark integration contracts independent of model downloads."""
from unittest.mock import patch

from PIL import Image

from scripts.benchmark_quality_models import make_pair, run_quality


def test_quality_dataset_is_reproducible_and_dimensions_match(tmp_path):
    hr, lr, bicubic = make_pair(tmp_path)
    assert Image.open(hr).size == (256, 256)
    assert Image.open(lr).size == (128, 128)
    assert Image.open(bicubic).size == (256, 256)
    before = hr.read_bytes()
    make_pair(tmp_path)
    assert hr.read_bytes() == before


def test_quality_report_includes_real_baseline_and_model_failures(tmp_path):
    unavailable = {
        "fsrcnn": {"status": "unavailable", "reason": "test"},
        "espcn": {"status": "unavailable", "reason": "test"},
    }
    with patch("scripts.benchmark_quality_models.run", return_value=unavailable) as model_run:
        report = run_quality(tmp_path)
    assert report["reference_dimensions"] == [256, 256]
    assert report["baseline_bicubic"]["mae_rgb"] > 0
    assert set(report["models"]) == {"fsrcnn", "espcn"}
    assert all("quality" not in item for item in report["models"].values())
    assert model_run.call_args.kwargs["require_models"] is True


def test_edge_and_smooth_scenes_are_distinct_and_deterministic(tmp_path):
    edge_dir = tmp_path / "edges"
    smooth_dir = tmp_path / "smooth"
    edge_hr, _, _ = make_pair(edge_dir, scene="edges")
    smooth_hr, _, _ = make_pair(smooth_dir, scene="smooth")
    assert edge_hr.read_bytes() != smooth_hr.read_bytes()
    before = edge_hr.read_bytes()
    make_pair(edge_dir, scene="edges")
    assert edge_hr.read_bytes() == before


def test_unknown_quality_scene_fails_closed(tmp_path):
    import pytest
    with pytest.raises(ValueError, match="Unknown benchmark scene"):
        make_pair(tmp_path, scene="unverified")
