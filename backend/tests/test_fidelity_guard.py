"""Guarded portrait is an LR-consistency feature, not a face-fidelity guarantee."""
import io
from unittest.mock import Mock

import cv2
import numpy as np
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from app import fsrcnn, main
from app.fidelity_guard import guarded_blend


def image_bgr():
    y, x = np.indices((41, 57))
    return np.stack(((x * 7 + y * 5) % 256, (x * 3 + y * 11) % 256, (x + y * 7) % 256), -1).astype(np.uint8)


def cycle_error(low, high):
    down = cv2.resize(high, (low.shape[1], low.shape[0]), interpolation=cv2.INTER_AREA)
    return float(np.square(down.astype(np.float32) - low.astype(np.float32)).mean())


@pytest.mark.parametrize('strength', [0, 10, 25, 35, 60, 100])
def test_guard_never_worsens_input_reconstruction_against_bicubic(strength):
    low = image_bgr()
    bicubic = cv2.resize(low, (114, 82), interpolation=cv2.INTER_CUBIC)
    erroneous_model = np.full_like(bicubic, 30)
    output, weight, score = guarded_blend(low, erroneous_model, strength)
    assert output.shape == bicubic.shape
    assert output.dtype == np.uint8
    assert 0 <= weight <= strength / 100
    assert score == pytest.approx(cycle_error(low, output))
    assert score <= cycle_error(low, bicubic) + 1e-6
    if strength == 0:
        np.testing.assert_array_equal(output, bicubic)


def test_guard_prefers_neural_at_equal_cycle_error():
    low = image_bgr()
    bicubic = cv2.resize(low, (114, 82), interpolation=cv2.INTER_CUBIC)
    output, weight, _ = guarded_blend(low, bicubic, 100)
    assert weight == 1.0
    np.testing.assert_array_equal(output, bicubic)


@pytest.mark.parametrize('bad', [-1, 101, True, 1.5, '100'])
def test_guard_rejects_invalid_strength(bad):
    low = image_bgr()
    with pytest.raises(ValueError):
        guarded_blend(low, np.zeros((82, 114, 3), dtype=np.uint8), bad)


def test_guard_rejects_wrong_neural_shape_or_dtype():
    low = image_bgr()
    with pytest.raises(ValueError):
        guarded_blend(low, np.zeros((82, 113, 3), dtype=np.uint8))
    with pytest.raises(ValueError):
        guarded_blend(low, np.zeros((82, 114, 3), dtype=np.float32))


def test_opt_in_fsrcnn_v4_endpoint_and_legacy_versions_unmodified(monkeypatch):
    low = image_bgr()
    monkeypatch.setattr(main, 'fsrcnn_available', lambda: True)
    monkeypatch.setattr(fsrcnn, 'model_path', lambda: '/tmp/not-downloaded-in-this-test.pb')
    monkeypatch.setattr(main, 'fsrcnn_upscale', fsrcnn.upscale)
    monkeypatch.setattr(fsrcnn, '_model', lambda _: Mock(upsample=lambda _: np.zeros((82, 114, 3), dtype=np.uint8)))
    image = Image.fromarray(cv2.cvtColor(low, cv2.COLOR_BGR2RGB))
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    response = TestClient(main.app).post('/api/enhance/fsrcnn',
        files={'file': ('test.png', buffer.getvalue(), 'image/png')},
        data={'portrait': 'true', 'portrait_version': '4', 'strength': '35'})
    assert response.status_code == 200, response.text
    assert 'guarded' in response.headers['content-disposition']
    assert float(response.headers['x-lumqenix-guard-neural-weight']) <= .35
    with Image.open(io.BytesIO(response.content)) as result:
        assert result.size == (114, 82)
        prediction = cv2.cvtColor(np.asarray(result), cv2.COLOR_RGB2BGR)
    bicubic = cv2.resize(low, (114, 82), interpolation=cv2.INTER_CUBIC)
    assert cycle_error(low, prediction) <= cycle_error(low, bicubic) + 1e-6
    assert main.PROCESSING_LOCK.locked() is False


def test_portrait_v4_needs_valid_version_and_strength():
    response = TestClient(main.app).post('/api/enhance/fsrcnn', data={'portrait': 'true', 'portrait_version': '5'})
    assert response.status_code in (400, 422)
