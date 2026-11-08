"""Opt-in tests run real pretrained weights, never substituted networks."""
import io
import os
import numpy as np
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from app import espcn, fsrcnn
from app.main import app

@pytest.fixture
def source():
    y, x = np.indices((48, 64))
    return Image.fromarray(np.stack([(x * 4) % 256, (y * 5) % 256, ((x+y)*3) % 256], axis=-1).astype('uint8'))

@pytest.mark.parametrize('name,module', [('fsrcnn', fsrcnn), ('espcn', espcn)])
def test_pretrained_api(name, module, source):
    if not os.getenv('LUMQENIX_' + name.upper() + '_MODEL'):
        pytest.skip(name + ' pretrained weights not configured')
    assert module.available(), 'Configured pretrained model is unavailable'
    data = io.BytesIO()
    source.save(data, format='PNG')
    response = TestClient(app).post('/api/enhance/' + name, files={'file': ('sample.png', data.getvalue(), 'image/png')})
    assert response.status_code == 200, response.text
    actual = np.asarray(Image.open(io.BytesIO(response.content)))
    assert actual.shape == (96, 128, 3)
    assert actual.std() > 20
    expected = np.asarray(module.upscale(source))
    np.testing.assert_array_equal(actual, expected)

@pytest.mark.parametrize('strength', [0, 35, 100])
def test_pretrained_portrait_strength(source, strength):
    if not os.getenv('LUMQENIX_FSRCNN_MODEL'):
        pytest.skip('FSRCNN pretrained weights not configured')
    result = fsrcnn.upscale(source, portrait='v3', strength=strength)
    assert result.size == (128, 96)
    if strength == 0:
        np.testing.assert_array_equal(np.asarray(result), np.asarray(fsrcnn.upscale(source)))
    else:
        assert np.asarray(result).std() > 20

@pytest.mark.parametrize('version,strength', [(2,35), (3,0), (3,35), (3,100)])
def test_pretrained_portrait_api(source, version, strength):
    if not os.getenv('LUMQENIX_FSRCNN_MODEL'):
        pytest.skip('FSRCNN pretrained weights not configured')
    data = io.BytesIO()
    source.save(data, format='PNG')
    response = TestClient(app).post('/api/enhance/fsrcnn',
        files={'file': ('portrait.png', data.getvalue(), 'image/png')},
        data={'portrait':'true', 'portrait_version':version, 'strength':strength})
    assert response.status_code == 200, response.text
    expected = fsrcnn.upscale(source, portrait=True if version == 2 else 'v3', strength=strength)
    np.testing.assert_array_equal(np.asarray(Image.open(io.BytesIO(response.content))), np.asarray(expected))
