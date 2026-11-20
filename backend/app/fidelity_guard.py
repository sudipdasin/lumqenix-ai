"""Experimental LR-consistency guard; not an HR fidelity or face-ID guarantee.

Compare neural/bicubic blends against the actual source after 2x downsampling.
The zero-neural bicubic option is always tested, so this proxy metric cannot
regress versus the local bicubic reconstruction of the input. This metric is
NOT ground-truth high-resolution PSNR and may choose an inferior HR image.
"""
import cv2
import numpy as np


CANDIDATE_WEIGHTS = (0.0, 0.25, 0.5, 0.75, 1.0)


def guarded_blend(low_res_bgr, neural_bgr, strength=35):
    """Return (BGR 2x result, neural_fraction, LR_cycle_MSE)."""
    if isinstance(strength, bool) or not isinstance(strength, int) or not 0 <= strength <= 100:
        raise ValueError("Guard strength must be an integer from 0 through 100")
    if (not isinstance(low_res_bgr, np.ndarray) or not isinstance(neural_bgr, np.ndarray)
            or low_res_bgr.dtype != np.uint8 or neural_bgr.dtype != np.uint8
            or low_res_bgr.ndim != 3 or low_res_bgr.shape[2] != 3
            or neural_bgr.shape != (low_res_bgr.shape[0] * 2, low_res_bgr.shape[1] * 2, 3)):
        raise ValueError("Guard requires uint8 BGR input and an exact 2x BGR prediction")
    height, width = low_res_bgr.shape[:2]
    bicubic = cv2.resize(low_res_bgr, (width * 2, height * 2), interpolation=cv2.INTER_CUBIC)
    original = low_res_bgr.astype(np.int16)
    best = bicubic
    best_weight = 0.0
    best_mse = float("inf")
    for weight in CANDIDATE_WEIGHTS:
        if weight * 100 > strength:
            continue
        candidate = bicubic if weight == 0 else cv2.addWeighted(neural_bgr, weight, bicubic, 1 - weight, 0)
        reduced = cv2.resize(candidate, (width, height), interpolation=cv2.INTER_AREA)
        error = reduced.astype(np.int16) - original
        mse = float(np.mean(np.square(error.astype(np.float32))))
        if mse < best_mse - 1e-9 or (abs(mse - best_mse) <= 1e-9 and weight > best_weight):
            best, best_weight, best_mse = candidate, weight, mse
    return best, best_weight, best_mse
