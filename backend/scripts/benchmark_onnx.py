"""Small, safe ONNX super-resolution smoke benchmark for low-RAM laptops.

Usage:
  LUMQENIX_ONNX_MODEL=/path/model.onnx LUMQENIX_ONNX_SCALE=2 \
    python scripts/benchmark_onnx.py --input /path/image.jpg
"""
import argparse
import io
import sys
import time
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.onnx_upscale import upscale, model_path, configured_scale

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", default="/tmp/lumqenix-ai-benchmark.png", type=Path)
    parser.add_argument("--tile", type=int, default=64)
    parser.add_argument("--overlap", type=int, default=8)
    parser.add_argument("--max-input-side", type=int, default=256)
    args = parser.parse_args()
    if args.max_input_side < 32 or args.max_input_side > 512:
        parser.error("--max-input-side must be 32..512")
    if model_path() is None:
        parser.error("Set LUMQENIX_ONNX_MODEL to a compatible ONNX model")
    with Image.open(args.input) as source:
        source.thumbnail((args.max_input_side, args.max_input_side), Image.Resampling.LANCZOS)
        sample = source.convert("RGB")
    print(f"Input: {sample.width}x{sample.height}; model scale: {configured_scale()}x", flush=True)
    start = time.perf_counter()
    result, device = upscale(sample, device="cpu", tile=args.tile, overlap=args.overlap)
    seconds = time.perf_counter() - start
    result.save(args.output)
    print(f"Output: {result.width}x{result.height}; CPU time: {seconds:.2f}s; device: {device}")
    print(f"Saved: {args.output}")

if __name__ == "__main__":
    main()
