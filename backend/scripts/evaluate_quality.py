"""Paired-image super-resolution quality metrics, with a bicubic baseline.

Evaluate reference HR and predicted x2 HR PNGs without claiming perceptual quality.
The RGB PSNR/MAE metrics are deterministic; they are not a face-identity metric.

Usage:
  python scripts/evaluate_quality.py --reference hr.png --prediction model.png \
    --baseline bicubic.png --output quality.json
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps


def load_rgb(path):
    with Image.open(path) as image:
        return np.asarray(ImageOps.exif_transpose(image).convert("RGB"), dtype=np.uint8)


def metrics(reference, prediction):
    if reference.shape != prediction.shape:
        raise ValueError(f"Image dimensions mismatch: {reference.shape} vs {prediction.shape}")
    if reference.ndim != 3 or reference.shape[2] != 3 or not reference.size:
        raise ValueError("Expected nonempty RGB images")
    delta = reference.astype(np.float64) - prediction.astype(np.float64)
    mse = float(np.mean(np.square(delta)))
    mae = float(np.mean(np.abs(delta)))
    return {
        "mse_rgb": round(mse, 6),
        "mae_rgb": round(mae, 6),
        "psnr_rgb_db": None if mse == 0 else round(10.0 * math.log10(255.0 ** 2 / mse), 6),
        "lossless": mse == 0,
    }


def evaluate(reference_path, prediction_path, baseline_path=None):
    reference = load_rgb(reference_path)
    prediction = load_rgb(prediction_path)
    result = {
        "reference": str(reference_path),
        "prediction": str(prediction_path),
        "dimensions": [int(reference.shape[1]), int(reference.shape[0])],
        "prediction_metrics": metrics(reference, prediction),
    }
    if baseline_path is not None:
        baseline = load_rgb(baseline_path)
        result["baseline"] = str(baseline_path)
        result["baseline_metrics"] = metrics(reference, baseline)
        result["mae_improvement_vs_baseline"] = round(
            result["baseline_metrics"]["mae_rgb"] - result["prediction_metrics"]["mae_rgb"], 6
        )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--prediction", type=Path, required=True)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = evaluate(args.reference, args.prediction, args.baseline)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    payload = json.dumps(result, indent=2, allow_nan=False)
    if args.output:
        args.output.write_text(payload + "\n")
    else:
        print(payload)


if __name__ == "__main__":
    main()
