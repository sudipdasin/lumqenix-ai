"""Reproducible local CPU/API latency and RSS smoke benchmark.

Run from backend/: python scripts/benchmark_api_cpu.py --runs 3
The peak RSS is process-wide and cumulative (ru_maxrss), not per-request memory.
"""
import argparse
import io
import json
import resource
import statistics
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import app  # noqa: E402


def peak_rss_mib():
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss / (1024 * 1024 if sys.platform == "darwin" else 1024)


def run_benchmark(width, height, runs, scale, preset):
    source = Image.new("RGB", (width, height))
    pixels = source.load()
    for y in range(height):
        for x in range(width):
            pixels[x, y] = ((x * 7 + y * 3) % 256, (x * 2 + y * 11) % 256, (x + y * 5) % 256)
    stream = io.BytesIO()
    source.save(stream, format="PNG")
    payload = stream.getvalue()
    client = TestClient(app)
    timings = []
    output_size = None
    for iteration in range(runs + 1):
        started = time.perf_counter()
        response = client.post(
            "/api/enhance/image",
            data={"preset": preset, "scale": str(scale)},
            files={"file": ("benchmark.png", payload, "image/png")},
        )
        elapsed = time.perf_counter() - started
        if response.status_code != 200:
            raise RuntimeError(f"Enhancement failed: HTTP {response.status_code}: {response.text[:300]}")
        with Image.open(io.BytesIO(response.content)) as output:
            output.load()
            expected = (width * scale, height * scale)
            if output.size != expected:
                raise RuntimeError(f"Wrong output dimensions: {output.size} != {expected}")
        if iteration:
            timings.append(elapsed)
        output_size = len(response.content)
    return {
        "mode": "classic",
        "preset": preset,
        "input_pixels": width * height,
        "scale": scale,
        "output_pixels": width * height * scale * scale,
        "warm_runs": runs,
        "warm_seconds_median": round(statistics.median(timings), 6),
        "warm_seconds_min": round(min(timings), 6),
        "warm_seconds_max": round(max(timings), 6),
        "peak_process_rss_mib": round(peak_rss_mib(), 2),
        "encoded_png_bytes": output_size,
        "note": "One untimed warmup; peak RSS is cumulative for the process.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--width", type=int, default=256)
    parser.add_argument("--height", type=int, default=256)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--scale", type=int, choices=(1, 2, 4), default=2)
    parser.add_argument("--preset", default="auto")
    args = parser.parse_args()
    if args.width <= 0 or args.height <= 0 or not 1 <= args.runs <= 100:
        parser.error("width, height must be positive and runs must be 1..100")
    if args.width * args.height * args.scale ** 2 > 12_000_000:
        parser.error("requested output exceeds the 12-million-pixel Lite limit")
    print(json.dumps(run_benchmark(args.width, args.height, args.runs, args.scale, args.preset), indent=2))


if __name__ == "__main__":
    main()
