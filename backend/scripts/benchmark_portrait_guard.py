"""Reproducible pretrained FSRCNN v4 LR-cycle check, not HR/identity evidence."""
import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import fsrcnn


def main():
    path = fsrcnn.model_path()
    if path is None or not fsrcnn.available():
        raise SystemExit('Real FSRCNN weights and OpenCV contrib are required')
    y, x = np.indices((48, 64))
    src = np.stack(((x * 7 + y * 3) % 256, (x * 2 + y * 11) % 256,
                    (x + y * 5) % 256), axis=-1).astype(np.uint8)
    image = Image.fromarray(cv2.cvtColor(src, cv2.COLOR_BGR2RGB))
    # Inference is performed on the actual pinned model, not a mock.
    result = fsrcnn.upscale(image, portrait='v4', strength=100)
    actual_bgr = cv2.cvtColor(np.asarray(result), cv2.COLOR_RGB2BGR)
    bicubic = cv2.resize(src, (128, 96), interpolation=cv2.INTER_CUBIC)

    def error(prediction):
        down = cv2.resize(prediction, (64, 48), interpolation=cv2.INTER_AREA)
        return float(np.mean(np.square(down.astype(np.float32) - src.astype(np.float32))))

    original = error(bicubic)
    guarded = error(actual_bgr)
    if guarded > original + 1e-6:
        raise SystemExit('Portrait guard exceeded bicubic LR-cycle error')
    weight = float(result.info['neural_weight'])
    if not 0 <= weight <= 1:
        raise SystemExit('Invalid model contribution from guard')
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    print(json.dumps({
        'mode': 'experimental-LR-cycle-v4',
        'input_dimensions': [64, 48],
        'output_dimensions': [128, 96],
        'model_sha256': digest,
        'baseline_bicubic_lr_cycle_mse': original,
        'guarded_lr_cycle_mse': guarded,
        'selected_neural_fraction': weight,
        'quality_claim': 'LR consistency only; no HR PSNR or facial-identity guarantee',
    }, indent=2))


if __name__ == '__main__':
    main()
