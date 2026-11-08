"""Real runtime plumbing tests; generated nearest-neighbor graph is not pretrained."""
import numpy as np
import pytest
from PIL import Image, ImageOps
from app import onnx_upscale as engine

@pytest.fixture
def model(monkeypatch, tmp_path):
    onnx = pytest.importorskip('onnx')
    pytest.importorskip('onnxruntime')
    from onnx import helper, TensorProto, numpy_helper
    graph = helper.make_graph([
        helper.make_node('Resize', ['input', '', 'scales'], ['output'], mode='nearest', coordinate_transformation_mode='asymmetric', nearest_mode='floor')
    ], 'nearest2x', [helper.make_tensor_value_info('input', TensorProto.FLOAT, [1,3,'h','w'])],
       [helper.make_tensor_value_info('output', TensorProto.FLOAT, [1,3,'oh','ow'])],
       [numpy_helper.from_array(np.array([1,1,2,2], dtype=np.float32), 'scales')])
    network = helper.make_model(graph, opset_imports=[helper.make_opsetid('', 13)], ir_version=8)
    path = tmp_path / 'resize.onnx'
    onnx.save(network, path)
    monkeypatch.setenv('LUMQENIX_ONNX_MODEL', str(path))
    monkeypatch.setenv('LUMQENIX_ONNX_SCALE', '2')
    engine._session.cache_clear()
    yield path
    engine._session.cache_clear()

@pytest.mark.parametrize('orientation', [1,6,8])
def test_real_runtime_tiles_and_orientation(model, orientation):
    pixels = np.random.default_rng(42).integers(0, 256, (59,77,3), dtype=np.uint8)
    image = Image.fromarray(pixels)
    image.getexif()[274] = orientation
    expected = np.asarray(ImageOps.exif_transpose(image)).repeat(2, axis=0).repeat(2, axis=1)
    output, device = engine.upscale(image, device='cpu', tile=32, overlap=8)
    np.testing.assert_array_equal(np.asarray(output), expected)
    assert device == 'cpu'

def test_corrupt_model_maps_load_failure(model):
    model.write_bytes(b'broken model')
    with pytest.raises(RuntimeError, match='Could not load'):
        engine.upscale(Image.new('RGB', (8,8)), device='cpu')
