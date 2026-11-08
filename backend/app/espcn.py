"""Optional pretrained ESPCN x2, using OpenCV contrib on CPU."""
from functools import lru_cache
from pathlib import Path
import os
import cv2
import numpy as np
from PIL import Image, ImageOps

MAX_INPUT_PIXELS = 512 * 512

def model_path():
    raw = os.getenv("LUMQENIX_ESPCN_MODEL", "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser().resolve()
    if not path.is_file() or path.suffix.lower() != ".pb":
        raise ValueError("LUMQENIX_ESPCN_MODEL must reference an existing .pb model")
    return path

def available():
    try:
        return model_path() is not None and hasattr(cv2, "dnn_superres")
    except ValueError:
        return False

@lru_cache(maxsize=1)
def _model(path):
    if not hasattr(cv2, "dnn_superres"):
        raise RuntimeError("OpenCV contrib dnn_superres is unavailable")
    cv2.setNumThreads(2)
    sr = cv2.dnn_superres.DnnSuperResImpl_create()
    sr.readModel(path)
    sr.setModel("espcn", 2)
    return sr

def upscale(image):
    path = model_path()
    if path is None:
        raise RuntimeError("ESPCN model not configured")
    rgb = ImageOps.exif_transpose(image).convert("RGB")
    if rgb.width * rgb.height > MAX_INPUT_PIXELS:
        raise ValueError("ESPCN Lite input limit: 262144 pixels")
    bgr = cv2.cvtColor(np.asarray(rgb), cv2.COLOR_RGB2BGR)
    result = _model(str(path)).upsample(bgr)
    if result.shape[:2] != (rgb.height * 2, rgb.width * 2):
        raise RuntimeError("ESPCN returned unexpected dimensions")
    return Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
