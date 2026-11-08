"""Optional pretrained FSRCNN x2 via OpenCV contrib dnn_superres.

A compatible, trusted FSRCNN_x2.pb file must be supplied by the operator.
No model is downloaded and no untrained model is substituted.
"""
from functools import lru_cache
from pathlib import Path
import os
import cv2
import numpy as np
from PIL import Image, ImageOps

MODEL_ENV = "LUMQENIX_FSRCNN_MODEL"
MAX_INPUT_PIXELS = 512 * 512

def model_path():
    raw = os.environ.get(MODEL_ENV, "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser().resolve()
    if not path.is_file() or path.suffix.lower() != ".pb":
        raise ValueError("LUMQENIX_FSRCNN_MODEL must point to an existing .pb file")
    return path

def available():
    return bool(model_path()) and hasattr(cv2, "dnn_superres")

@lru_cache(maxsize=1)
def _model(path):
    if not hasattr(cv2, "dnn_superres"):
        raise RuntimeError("OpenCV dnn_superres unavailable; install compatible opencv-contrib-python-headless in an isolated environment")
    cv2.setNumThreads(2)
    sr = cv2.dnn_superres.DnnSuperResImpl_create()
    sr.readModel(path)
    sr.setModel("fsrcnn", 2)
    return sr

def upscale(image, portrait=False, strength=35):
    if not isinstance(strength, int) or not 0 <= strength <= 100:
        raise ValueError('Portrait strength must be between 0 and 100')
    path = model_path()
    if path is None:
        raise RuntimeError("FSRCNN model not configured: set LUMQENIX_FSRCNN_MODEL")
    image = ImageOps.exif_transpose(image).convert("RGB")
    if image.width * image.height > MAX_INPUT_PIXELS:
        raise ValueError("FSRCNN Lite input limit: 262144 pixels (512 x 512 equivalent)")
    bgr = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
    if portrait == 'v3' and strength == 0:
        portrait = False
    if portrait:
        # Gentle edge-preserving cleanup BEFORE neural inference.
        sigma = 12 if portrait is True else 4 + strength * 0.08
        bgr = cv2.bilateralFilter(bgr, d=5, sigmaColor=sigma, sigmaSpace=3)
    result = _model(str(path)).upsample(bgr)
    if portrait:
        # Small luminance-only unsharp mask; preserve chroma and avoid harsh halos.
        lab = cv2.cvtColor(result, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        blurred = cv2.GaussianBlur(l, (0, 0), 0.65)
        amount = 0.12 if portrait is True else 0.02 + strength * 0.0006
        boosted = cv2.addWeighted(l, 1.0 + amount, blurred, -amount, 0)
        result = cv2.cvtColor(cv2.merge((boosted, a, b)), cv2.COLOR_LAB2BGR)
    if result.shape[:2] != (image.height * 2, image.width * 2):
        raise RuntimeError("FSRCNN model returned unexpected dimensions")
    return Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
