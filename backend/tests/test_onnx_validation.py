import pytest
from PIL import Image
from app.onnx_upscale import upscale

def test_invalid_device_rejected():
    with pytest.raises(ValueError, match="device"):
        upscale(Image.new("RGB", (8,8)), device="invalid")

def test_invalid_tile_rejected():
    with pytest.raises(ValueError, match="tile"):
        upscale(Image.new("RGB", (8,8)), tile=10)

def test_no_model_configured(monkeypatch):
    monkeypatch.delenv("LUMQENIX_ONNX_MODEL", raising=False)
    with pytest.raises(ValueError, match="No ONNX model"):
        upscale(Image.new("RGB", (8,8)), device="cpu")

@pytest.mark.parametrize('failure', ['nonfinite', 'runtime'])
def test_bad_inference_is_controlled(monkeypatch, tmp_path, failure):
    import numpy as np
    from types import SimpleNamespace
    from app import onnx_upscale as engine
    path = tmp_path / 'model.onnx'
    path.write_bytes(b'model-placeholder')
    monkeypatch.setenv('LUMQENIX_ONNX_MODEL', str(path))
    monkeypatch.setenv('LUMQENIX_ONNX_SCALE', '2')
    class Session:
        def get_inputs(self):
            return [SimpleNamespace(name='input')]
        def get_outputs(self):
            return [SimpleNamespace(name='output')]
        def run(self, names, inputs):
            if failure == 'runtime':
                raise Exception('provider failure')
            return [np.full((1, 3, 16, 16), np.nan, dtype=np.float32)]
    monkeypatch.setattr(engine, '_session', lambda *args: Session())
    with pytest.raises(RuntimeError, match='non-finite|inference failed'):
        engine.upscale(Image.new('RGB', (8,8)), device='cpu')
