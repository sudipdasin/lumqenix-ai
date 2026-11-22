"""Unit-level regression checks for the optional LR-cycle consistency primitive.

These tests do not claim perceptual quality, facial identity preservation, or
real pretrained-model performance. Endpoint integration is a separate change.
"""
import cv2
import numpy as np
import pytest

from app.fidelity_guard import guarded_blend


def sample():
    y, x = np.indices((41, 57))
    return np.stack(((x * 7 + y * 5) % 256,
                     (x * 3 + y * 11) % 256,
                     (x + y * 7) % 256), -1).astype(np.uint8)


def cycle_mse(low, high):
    reduced = cv2.resize(high, (low.shape[1], low.shape[0]), interpolation=cv2.INTER_AREA)
    return float(np.square(reduced.astype(np.float32) - low.astype(np.float32)).mean())


@pytest.mark.parametrize("strength", [0, 10, 25, 35, 60, 100])
def test_cycle_score_not_worse_than_bicubic(strength):
    low = sample()
    bicubic = cv2.resize(low, (114, 82), interpolation=cv2.INTER_CUBIC)
    corrupted_prediction = np.full_like(bicubic, 30)
    output, weight, score = guarded_blend(low, corrupted_prediction, strength)
    assert output.shape == bicubic.shape
    assert output.dtype == np.uint8
    assert 0 <= weight <= strength / 100
    assert score == pytest.approx(cycle_mse(low, output), abs=1e-6)
    assert score <= cycle_mse(low, bicubic) + 1e-6
    if strength == 0:
        np.testing.assert_array_equal(output, bicubic)


def test_tie_prefers_neural():
    low = sample()
    bicubic = cv2.resize(low, (114, 82), interpolation=cv2.INTER_CUBIC)
    output, weight, _ = guarded_blend(low, bicubic, 100)
    assert weight == 1.0
    np.testing.assert_array_equal(output, bicubic)


@pytest.mark.parametrize("invalid", [-1, 101, True, 1.5, "100"])
def test_invalid_strength_rejected(invalid):
    with pytest.raises(ValueError):
        guarded_blend(sample(), np.zeros((82, 114, 3), dtype=np.uint8), invalid)


def test_invalid_prediction_rejected():
    low = sample()
    for invalid in (np.zeros((82, 113, 3), dtype=np.uint8),
                    np.zeros((82, 114, 3), dtype=np.float32)):
        with pytest.raises(ValueError):
            guarded_blend(low, invalid)


def test_invalid_low_resolution_rejected():
    with pytest.raises(ValueError):
        guarded_blend(np.zeros((41, 57), dtype=np.uint8),
                      np.zeros((82, 114, 3), dtype=np.uint8))


@pytest.mark.parametrize("shape", [(0, 8, 3), (8, 0, 3), (0, 0, 3)])
def test_empty_images_raise_value_error(shape):
    low = np.zeros(shape, dtype=np.uint8)
    high = np.zeros((shape[0] * 2, shape[1] * 2, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="nonempty"):
        guarded_blend(low, high)
