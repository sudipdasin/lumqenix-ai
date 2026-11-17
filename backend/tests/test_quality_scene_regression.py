"""Regression coverage for the synthetic and real-reference quality scenes."""
from pathlib import Path
import sys

import numpy as np
from PIL import Image
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from benchmark_quality_models import make_pair


@pytest.mark.parametrize("scene", ["textures", "edges", "smooth"])
def test_scene_pair_has_valid_dimensions_and_reproducible_pixels(tmp_path, scene):
    first = make_pair(tmp_path / "first", scene=scene)
    second = make_pair(tmp_path / "second", scene=scene)
    for left, right, expected_size in zip(
        first, second, [(256, 256), (128, 128), (256, 256)]
    ):
        with Image.open(left) as a, Image.open(right) as b:
            assert a.mode == b.mode == "RGB"
            assert a.size == b.size == expected_size
            np.testing.assert_array_equal(np.asarray(a), np.asarray(b))


def test_distinct_scenes_produce_distinct_reference_images(tmp_path):
    arrays = []
    for scene in ("textures", "edges", "smooth"):
        hr, _, _ = make_pair(tmp_path / scene, scene=scene)
        with Image.open(hr) as image:
            arrays.append(np.asarray(image).copy())
    assert not np.array_equal(arrays[0], arrays[1])
    assert not np.array_equal(arrays[1], arrays[2])
    assert not np.array_equal(arrays[0], arrays[2])


def test_unknown_scene_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="Unknown benchmark scene"):
        make_pair(tmp_path / "invalid", scene="typo")


def test_real_reference_preserves_rgb_dimensions(tmp_path):
    source = tmp_path / "reference.png"
    Image.new("RGB", (300, 400), (30, 100, 210)).save(source)
    for scene in ("textures", "edges", "smooth"):
        hr, lr, bicubic = make_pair(tmp_path / scene, source, scene=scene)
        for path, size in ((hr, (256, 256)), (lr, (128, 128)), (bicubic, (256, 256))):
            with Image.open(path) as image:
                assert image.mode == "RGB"
                assert image.size == size


def test_undersized_real_reference_rejected(tmp_path):
    source = tmp_path / "small.png"
    Image.new("RGB", (255, 300)).save(source)
    with pytest.raises(ValueError, match="at least 256x256"):
        make_pair(tmp_path / "output", source)
