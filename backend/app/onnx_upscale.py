"""Optional ONNX super-resolution with halo-tiled inference.

Requires a compatible static-shape NCHW RGB float32 model with a single
NCHW output and integer spatial scale. Models are NOT downloaded automatically.
"""
from functools import lru_cache
from pathlib import Path
import os
import numpy as np
from PIL import Image
from .hardware import detect_hardware

MODEL_ENV = "LUMQENIX_ONNX_MODEL"
SCALE_ENV = "LUMQENIX_ONNX_SCALE"
GPU_PROVIDERS = ("CUDAExecutionProvider", "ROCMExecutionProvider",
                 "DmlExecutionProvider", "CoreMLExecutionProvider",
                 "OpenVINOExecutionProvider", "TensorrtExecutionProvider")

def model_path():
    raw = os.getenv(MODEL_ENV, "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser().resolve()
    if not path.is_file() or path.suffix.lower() != ".onnx":
        raise ValueError("LUMQENIX_ONNX_MODEL must point to an existing .onnx file")
    return path

def configured_scale():
    try:
        scale = int(os.getenv(SCALE_ENV, "4"))
    except ValueError:
        raise ValueError("LUMQENIX_ONNX_SCALE must be an integer")
    if scale not in (2, 4):
        raise ValueError("ONNX model scale must be 2 or 4")
    return scale

@lru_cache(maxsize=4)
def _session(path, device):
    import onnxruntime as ort
    available = ort.get_available_providers()
    if device == "gpu":
        providers = [p for p in GPU_PROVIDERS if p in available]
        if not providers:
            raise RuntimeError("No GPU ONNX execution provider available")
        providers += ["CPUExecutionProvider"] if "CPUExecutionProvider" in available else []
    else:
        providers = ["CPUExecutionProvider"]
        if "CPUExecutionProvider" not in available:
            raise RuntimeError("CPU ONNX execution provider unavailable")
    session = ort.InferenceSession(str(path), providers=providers)
    if len(session.get_inputs()) != 1 or len(session.get_outputs()) != 1:
        raise ValueError("Model must have one input and one output")
    shape = session.get_inputs()[0].shape
    if len(shape) != 4 or (isinstance(shape[1], int) and shape[1] != 3):
        raise ValueError("Model input must be NCHW RGB")
    return session

def upscale(image, device="auto", tile=128, overlap=16):
    if device not in ("auto", "cpu", "gpu"):
        raise ValueError("device must be auto, cpu, or gpu")
    if not 32 <= tile <= 512 or not 0 <= overlap <= 64 or overlap * 2 >= tile:
        raise ValueError("Invalid tile/overlap settings")
    path = model_path()
    if path is None:
        raise ValueError("No ONNX model configured")
    scale = configured_scale()
    actual = detect_hardware()["recommended"] if device == "auto" else device
    session = _session(str(path), actual)
    inp = session.get_inputs()[0]
    outname = session.get_outputs()[0].name
    arr = np.asarray(image.convert("RGB"), dtype=np.uint8)
    h, w, _ = arr.shape
    output = np.empty((h * scale, w * scale, 3), dtype=np.uint8)
    # The halo provides context; each central tile is copied exactly once.
    for y in range(0, h, tile):
        for x in range(0, w, tile):
            y0, y1 = max(0, y-overlap), min(h, y+tile+overlap)
            x0, x1 = max(0, x-overlap), min(w, x+tile+overlap)
            patch = arr[y0:y1, x0:x1]
            tensor = np.ascontiguousarray(patch.transpose(2,0,1)[None].astype(np.float32)/255.0)
            result = session.run([outname], {inp.name:tensor})[0]
            expected = (1,3,(y1-y0)*scale,(x1-x0)*scale)
            if result.shape != expected:
                raise ValueError(f"Model output {result.shape} does not match expected {expected}")
            rgb = np.clip(result[0].transpose(1,2,0)*255.0,0,255).astype(np.uint8)
            core_y0, core_x0 = (y-y0)*scale, (x-x0)*scale
            core_h, core_w = min(tile,h-y)*scale, min(tile,w-x)*scale
            output[y*scale:y*scale+core_h, x*scale:x*scale+core_w] = rgb[
                core_y0:core_y0+core_h,core_x0:core_x0+core_w]
    return Image.fromarray(output, "RGB"), actual
