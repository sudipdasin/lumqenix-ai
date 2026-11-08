"""Benchmark actual FSRCNN and ESPCN models on the same image.

Requires the isolated OpenCV-contrib environment and configured pretrained weights.
No scores are fabricated if a model is unavailable.
Usage:
  python scripts/benchmark_models.py --input /path/to/portrait.png --output-dir /tmp/lumqenix-benchmark
"""
import argparse
import json
import os
import resource
import time
from pathlib import Path
from PIL import Image
from app import fsrcnn, espcn

def run(input_path, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    results = {}
    for name, module in (("fsrcnn", fsrcnn), ("espcn", espcn)):
        if not module.available():
            results[name] = {"status": "unavailable", "reason": "model path or OpenCV contrib missing"}
            continue
        with Image.open(input_path) as source:
            t0 = time.perf_counter()
            try:
                output = module.upscale(source)
            except Exception as exc:
                results[name] = {"status": "failed", "error": str(exc)}
                continue
            elapsed = time.perf_counter() - t0
        path = output_dir / f"{name}-2x.png"
        output.save(path)
        results[name] = {
            "status": "ok",
            "seconds": round(elapsed, 4),
            "output_dimensions": list(output.size),
            "output_file": str(path),
            "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        }
    return results

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("/tmp/lumqenix-model-benchmark"))
    args = parser.parse_args()
    if not args.input.is_file():
        parser.error("Input image does not exist")
    print(json.dumps(run(args.input, args.output_dir), indent=2))

if __name__ == "__main__":
    main()
