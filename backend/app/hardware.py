"""Report available ONNX execution providers; never claim GPU without a usable provider."""
from functools import lru_cache
import importlib.util

@lru_cache(maxsize=1)
def detect_hardware():
    result = {"cpu": True, "gpu": False, "providers": [], "recommended": "cpu",
              "onnxruntime_installed": False}
    if importlib.util.find_spec("onnxruntime") is None:
        return result
    try:
        import onnxruntime as ort
        providers = ort.get_available_providers()
        gpu_providers = [p for p in providers if p in (
            "CUDAExecutionProvider", "ROCMExecutionProvider",
            "DmlExecutionProvider", "CoreMLExecutionProvider",
            "OpenVINOExecutionProvider", "TensorrtExecutionProvider")]
        result.update(onnxruntime_installed=True, providers=providers,
                      gpu=bool(gpu_providers), recommended="gpu" if gpu_providers else "cpu")
    except Exception as exc:
        result["detection_error"] = type(exc).__name__
    return result
