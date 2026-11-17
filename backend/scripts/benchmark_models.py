"""Benchmark local FSRCNN and ESPCN x2 models in isolated CPU processes.

Models are never downloaded. Configure LUMQENIX_FSRCNN_MODEL and/or
LUMQENIX_ESPCN_MODEL with paths to trusted .pb files before running.
"""
import argparse
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import time
from pathlib import Path


MODEL_ENV = {"fsrcnn": "LUMQENIX_FSRCNN_MODEL", "espcn": "LUMQENIX_ESPCN_MODEL"}


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as model_file:
        for chunk in iter(lambda: model_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_version(package):
    try:
        from importlib.metadata import PackageNotFoundError, version
        try:
            return version(package)
        except PackageNotFoundError:
            return None
    except ImportError:  # Python < 3.8
        return None


def worker(model_name, input_path, output_path, repeats):
    """Run inside one child process so peak RSS is model-specific."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from PIL import Image, ImageOps
    import cv2
    import numpy as np
    from app import fsrcnn, espcn

    module = fsrcnn if model_name == "fsrcnn" else espcn
    env_path = os.environ.get(MODEL_ENV[model_name], "").strip()
    model_path = Path(env_path).expanduser() if env_path else None
    try:
        model_path = model_path.resolve() if model_path else None
    except OSError:
        model_path = None

    base = {
        "model": model_name,
        "model_file": str(model_path) if model_path else None,
        "model_sha256": sha256_file(model_path) if model_path and model_path.is_file() else None,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count_logical": os.cpu_count(),
        "thread_environment": {key: os.environ.get(key) for key in (
            "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"
        )},
        "packages": {
            "opencv": cv2.__version__,
            "numpy": np.__version__,
            "pillow": package_version("Pillow"),
        },
    }
    if not model_path or not model_path.is_file():
        base.update(status="unavailable", reason="model file is not configured or does not exist")
        return base
    if not module.available():
        base.update(status="unavailable", reason="OpenCV contrib dnn_superres is unavailable")
        return base

    try:
        with Image.open(input_path) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
        base["input_dimensions"] = list(image.size)

        start = time.perf_counter()
        output = module.upscale(image.copy())
        cold_seconds = time.perf_counter() - start
        base["opencv_threads"] = cv2.getNumThreads()
        warm_seconds = []
        for _ in range(repeats):
            start = time.perf_counter()
            output = module.upscale(image.copy())
            warm_seconds.append(time.perf_counter() - start)
        output.save(output_path)

        rss_bytes = None
        rss_status = "unavailable"
        try:
            import resource
            max_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            # getrusage reports bytes on macOS, KiB on Linux and other BSDs.
            rss_bytes = int(max_rss if sys.platform == "darwin" else max_rss * 1024)
            rss_status = "ok"
        except (ImportError, AttributeError, OSError):
            pass

        base.update(
            status="ok",
            cold_seconds=round(cold_seconds, 6),
            seconds=round(cold_seconds, 6),
            warm_seconds=[round(value, 6) for value in warm_seconds],
            warm_mean_seconds=round(sum(warm_seconds) / len(warm_seconds), 6),
            output_dimensions=list(output.size),
            output_file=str(output_path),
            max_rss_bytes=rss_bytes,
            max_rss_status=rss_status,
        )
    except Exception as exc:
        base.update(status="failed", error=f"{type(exc).__name__}: {exc}")
    return base


def validate_worker_result(result, name, input_path, output_path, repeats):
    """Reject incomplete or implausible success reports before publishing evidence."""
    if not isinstance(result, dict):
        return {"status": "failed", "error": "worker returned a non-object JSON value"}
    if result.get("status") != "ok":
        return result
    try:
        with __import__("PIL.Image", fromlist=["Image"]).open(input_path) as image:
            width, height = image.size
        expected = [width * 2, height * 2]
        if result.get("model") != name:
            raise ValueError("model identity mismatch")
        if result.get("input_dimensions") != [width, height]:
            raise ValueError("input dimensions mismatch")
        if result.get("output_dimensions") != expected:
            raise ValueError("output dimensions mismatch")
        if len(result.get("warm_seconds", [])) != repeats:
            raise ValueError("warm repetition count mismatch")
        timings = [result.get("cold_seconds"), *result["warm_seconds"]]
        if any(not isinstance(t, (int, float)) or not math.isfinite(t) or t <= 0 for t in timings):
            raise ValueError("nonpositive or nonfinite timing")
        if result.get("output_file") != str(output_path) or not output_path.is_file():
            raise ValueError("missing or mismatched output image")
        with __import__("PIL.Image", fromlist=["Image"]).open(output_path) as image:
            image.verify()
        with __import__("PIL.Image", fromlist=["Image"]).open(output_path) as image:
            if list(image.size) != expected or image.mode != "RGB":
                raise ValueError("output image dimensions or mode mismatch")
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return {"status": "failed", "error": f"invalid worker evidence: {exc}"}
    return result


def run(input_path, output_dir, repeats=3, timeout=180, require_models=False):
    output_dir.mkdir(parents=True, exist_ok=True)
    results = {}
    for name in MODEL_ENV:
        env_path = os.environ.get(MODEL_ENV[name], "").strip()
        model_file = Path(env_path).expanduser() if env_path else None
        is_configured = bool(model_file and model_file.is_file() and model_file.suffix.lower() == ".pb")
        if not is_configured:
            results[name] = {
                "status": "unavailable",
                "reason": "model file is not configured or does not exist",
                "model_file": str(model_file) if model_file else None,
                "model_sha256": None,
            }
            continue

        output_path = output_dir / f"{name}-2x.png"
        # Never allow a previous run's image to validate a new worker report.
        try:
            output_path.unlink(missing_ok=True)
        except OSError as exc:
            results[name] = {"status": "failed", "error": f"cannot clear stale output: {exc}"}
            continue
        command = [
            sys.executable, str(Path(__file__).resolve()), "--_worker", name,
            "--input", str(input_path), "--_output", str(output_path),
            "--repeats", str(repeats),
        ]
        try:
            completed = subprocess.run(
                command, capture_output=True, text=True, timeout=timeout,
                check=False, env=os.environ.copy(),
            )
            if completed.returncode != 0:
                results[name] = {
                    "status": "failed",
                    "error": (completed.stderr.strip() or completed.stdout.strip() or
                              f"worker exited with code {completed.returncode}"),
                }
                continue
            try:
                results[name] = validate_worker_result(
                    json.loads(completed.stdout), name, input_path, output_path, repeats
                )
            except json.JSONDecodeError as exc:
                results[name] = {"status": "failed", "error": f"invalid worker output: {exc}"}
        except subprocess.TimeoutExpired:
            results[name] = {"status": "failed", "error": f"benchmark timed out after {timeout} seconds"}
        except OSError as exc:
            # A failed worker launch must be recorded, not abort the entire benchmark.
            results[name] = {"status": "failed", "error": f"worker launch failed: {type(exc).__name__}: {exc}"}

    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("/tmp/lumqenix-model-benchmark"))
    parser.add_argument("--repeats", type=int, default=3, help="warm runs per model (default: 3)")
    parser.add_argument("--timeout", type=int, default=180, help="seconds allowed per model process")
    parser.add_argument("--require-models", action="store_true", help="exit nonzero if a model file is missing")
    parser.add_argument("--_worker", choices=tuple(MODEL_ENV), help=argparse.SUPPRESS)
    parser.add_argument("--_output", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args._worker:
        print(json.dumps(worker(args._worker, args.input, args._output, args.repeats)))
        return 0
    if not args.input.is_file():
        parser.error("Input image does not exist")
    if args.repeats < 1:
        parser.error("--repeats must be at least 1")
    if args.timeout < 1:
        parser.error("--timeout must be at least 1")

    missing = [name for name, env_name in MODEL_ENV.items()
               if not os.environ.get(env_name, "").strip()
               or not Path(os.environ[env_name]).expanduser().is_file()
               or Path(os.environ[env_name]).suffix.lower() != ".pb"]
    results = run(args.input, args.output_dir, args.repeats, args.timeout, args.require_models)
    print(json.dumps(results, indent=2))
    if args.require_models and (missing or any(result.get("status") != "ok" for result in results.values())):
        return 1
    return 1 if any(result.get("status") == "failed" for result in results.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
