"""End-to-end paired-reference quality benchmark using actual pretrained CPU models.

Construct deterministic 256x256 HR textures, downsample to 128x128 LR, run
FSRCNN and ESPCN through the isolated-process benchmark harness, then compare
each 2x prediction against both HR reference and bicubic interpolation.
This is synthetic reconstruction fidelity, not perceptual or face-identity quality.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

if __package__:
    from .benchmark_models import run
    from .evaluate_quality import evaluate
else:
    from benchmark_models import run
    from evaluate_quality import evaluate


def reference_sha256(path):
    """Hash operator images in bounded chunks without allocating the full file."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def make_pair(directory, reference_path=None, scene="textures"):
    """Prepare a deterministic synthetic scene or a real RGB reference pair."""
    if scene not in ("textures", "edges", "smooth"):
        raise ValueError(f"Unknown benchmark scene: {scene}")
    directory.mkdir(parents=True, exist_ok=True)
    if reference_path is None:
        yy, xx = np.indices((256, 256))
        if scene == "textures":
            checker = ((xx // 8 + yy // 8) % 2) * 40
            reference = np.stack((
                (xx * 3 + yy * 2 + checker) % 256,
                (xx + yy * 4 + checker) % 256,
                (xx * 2 + yy * 3 + checker) % 256,
            ), axis=-1).astype(np.uint8)
        elif scene == "edges":
            mask = ((xx > yy) ^ ((xx // 16) % 2 == 0))
            reference = np.stack((
                mask * 255, ((xx // 4) % 2) * 255,
                ((yy // 4) % 2) * 255,
            ), axis=-1).astype(np.uint8)
        else:
            reference = np.stack((
                xx, yy, xx // 2 + yy // 2,
            ), axis=-1).astype(np.uint8)
        hr = Image.fromarray(reference, "RGB")
    else:
        with Image.open(reference_path) as source:
            corrected = ImageOps.exif_transpose(source)
            if corrected.width < 256 or corrected.height < 256:
                raise ValueError("Reference image must be at least 256x256 pixels")
            hr = ImageOps.fit(corrected.convert("RGB"), (256, 256), method=Image.Resampling.LANCZOS)
    lr = hr.resize((128, 128), Image.Resampling.BICUBIC)
    bicubic = lr.resize((256, 256), Image.Resampling.BICUBIC)
    hr_path, lr_path, bicubic_path = (directory / name for name in
                                        ("reference-hr.png", "input-lr.png", "bicubic-2x.png"))
    hr.save(hr_path)
    lr.save(lr_path)
    bicubic.save(bicubic_path)
    return hr_path, lr_path, bicubic_path


def run_quality(output_dir, repeats=2, timeout=180, reference_path=None, scene="textures"):
    hr, lr, bicubic = make_pair(output_dir, reference_path, scene=scene)
    model_dir = output_dir / "models"
    performance = run(lr, model_dir, repeats=repeats, timeout=timeout, require_models=True)
    baseline = evaluate(hr, bicubic)["prediction_metrics"]
    result = {
        "dataset": "operator-reference-v1" if reference_path is not None else f"deterministic-synthetic-{scene}-v1",
        "source_sha256": reference_sha256(reference_path) if reference_path is not None else None,
        "reference_dimensions": [256, 256],
        "low_resolution_dimensions": [128, 128],
        "baseline_bicubic": baseline,
        "models": {},
    }
    for name in ("fsrcnn", "espcn"):
        execution = performance[name]
        entry = {"execution": execution}
        if execution.get("status") == "ok":
            entry["quality"] = evaluate(hr, model_dir / f"{name}-2x.png", bicubic)
        result["models"][name] = entry
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--require-models", action="store_true")
    parser.add_argument("--scene", choices=("textures", "edges", "smooth"), default="textures")
    parser.add_argument("--reference-image", type=Path, help="Operator-supplied real reference image (at least 256x256)")
    args = parser.parse_args()
    if args.repeats < 1 or args.timeout < 1:
        parser.error("repeats and timeout must be positive")
    results = run_quality(args.output_dir, args.repeats, args.timeout, args.reference_image, scene=args.scene)
    print(json.dumps(results, indent=2, allow_nan=False))
    if args.require_models and any(
        results["models"][name]["execution"].get("status") != "ok"
        for name in ("fsrcnn", "espcn")
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
