"""Validate real-model CI evidence without inventing quality improvements.

Usage:
  python scripts/validate_release_evidence.py --performance pretrained-cpu-benchmark.json \
      --quality pretrained-quality.json --quality-edges pretrained-quality-edges.json \\\n      --quality-smooth pretrained-quality-smooth.json --api cpu-benchmark.json

This gate checks evidence completeness and 4 GiB process budgets, not that
models outperform bicubic or preserve identity. Those require external criteria.
"""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path


class EvidenceError(ValueError):
    pass


def positive(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EvidenceError(f"{name}: expected numeric value")
    if not math.isfinite(value) or value <= 0:
        raise EvidenceError(f"{name}: expected finite positive value")
    return value


def validate(performance, quality, api):
    if api.get("output_format") != "PNG":
        raise EvidenceError("CPU API output is not confirmed PNG")
    positive(api.get("peak_process_rss_mib"), "api peak RSS")
    if api["peak_process_rss_mib"] >= 4096:
        raise EvidenceError("CPU API exceeds 4 GiB RSS")
    positive(api.get("warm_seconds_median"), "api latency")
    if quality.get("dataset") != "deterministic-synthetic-textures-v1":
        raise EvidenceError("Unexpected quality dataset")
    if quality.get("reference_dimensions") != [256, 256]:
        raise EvidenceError("Unexpected HR reference dimensions")
    baseline = quality.get("baseline_bicubic")
    if not isinstance(baseline, dict):
        raise EvidenceError("Invalid bicubic baseline measurements")
    positive(baseline.get("mae_rgb"), "bicubic MAE")
    positive(baseline.get("mse_rgb"), "bicubic MSE")
    baseline_psnr = baseline.get("psnr_rgb_db")
    if baseline_psnr is not None and (isinstance(baseline_psnr, bool) or not isinstance(baseline_psnr, (int, float)) or not math.isfinite(baseline_psnr)):
        raise EvidenceError("bicubic PSNR: expected finite numeric value")
    if quality.get("low_resolution_dimensions") != [128, 128]:
        raise EvidenceError("Unexpected LR reference dimensions")
    for name in ("fsrcnn", "espcn"):
        perf = performance.get(name, {})
        model = quality.get("models", {}).get(name, {})
        if perf.get("status") != "ok" or model.get("execution", {}).get("status") != "ok":
            raise EvidenceError(f"{name}: pretrained execution evidence missing")
        if perf.get("model_sha256") != model["execution"].get("model_sha256"):
            raise EvidenceError(f"{name}: model hashes differ between benchmarks")
        if not isinstance(perf["model_sha256"], str) or re.fullmatch(r"[0-9a-fA-F]{64}", perf["model_sha256"]) is None:
            raise EvidenceError(f"{name}: invalid model hash")
        positive(perf.get("max_rss_bytes"), f"{name} peak RSS")
        if perf["max_rss_bytes"] >= 4 * 1024 ** 3:
            raise EvidenceError(f"{name}: process exceeds 4 GiB RSS")
        for t in perf.get("warm_seconds", []):
            positive(t, f"{name} latency")
        if not perf.get("warm_seconds"):
            raise EvidenceError(f"{name}: missing warm latency")
        measures = model.get("quality", {})
        if measures.get("dimensions") != [256, 256]:
            raise EvidenceError(f"{name}: unexpected output dimensions")
        for label in ("prediction_metrics", "baseline_metrics"):
            m = measures.get(label, {})
            if isinstance(m.get("mae_rgb"), bool) or not isinstance(m.get("mae_rgb"), (float, int)) or not math.isfinite(m["mae_rgb"]) or m["mae_rgb"] < 0:
                raise EvidenceError(f"{name}: invalid {label} MAE")
            if isinstance(m.get("mse_rgb"), bool) or not isinstance(m.get("mse_rgb"), (float, int)) or not math.isfinite(m["mse_rgb"]) or m["mse_rgb"] < 0:
                raise EvidenceError(f"{name}: invalid {label} MSE")
            if label == "baseline_metrics":
                for metric in ("mae_rgb", "mse_rgb"):
                    if not math.isclose(m[metric], baseline[metric], rel_tol=0, abs_tol=1e-9):
                        raise EvidenceError(f"{name}: bicubic {metric} disagrees with shared reference")
            psnr = m.get("psnr_rgb_db")
            if psnr is not None and (isinstance(psnr, bool) or not isinstance(psnr, (int, float)) or not math.isfinite(psnr)):
                raise EvidenceError(f"{name}: invalid {label} PSNR")
            if label == "baseline_metrics" and psnr != baseline_psnr:
                raise EvidenceError(f"{name}: bicubic PSNR disagrees with shared reference")
    return {"evidence_complete": True, "model_count": 2,
            "memory_budget_mib": 4096,
            "quality_claim": "measurement only; no superiority or facial-fidelity claim"}



SCENES = ("textures", "edges", "smooth")


def validate_scene_bundle(performance, reports, api):
    """Require all three independent real-model scenes, not just textures."""
    if not isinstance(reports, dict) or set(reports) != set(SCENES):
        raise EvidenceError(f"Expected quality scenes {SCENES}, received {sorted(reports) if isinstance(reports, dict) else type(reports).__name__}")
    for scene in SCENES:
        if not isinstance(reports[scene], dict):
            raise EvidenceError(f"{scene}: invalid quality report")
    baseline_result = validate(performance, reports["textures"], api)
    for scene in SCENES:
        report = reports[scene]
        if not isinstance(report.get("models"), dict):
            raise EvidenceError(f"{scene}: missing model evidence map")
        expected = f"deterministic-synthetic-{scene}-v1"
        if report.get("dataset") != expected:
            raise EvidenceError(f"{scene}: unexpected dataset identifier")
        if report.get("reference_dimensions") != [256, 256]:
            raise EvidenceError(f"{scene}: invalid HR dimensions")
        if report.get("low_resolution_dimensions") != [128, 128]:
            raise EvidenceError(f"{scene}: invalid LR dimensions")
        baseline = report.get("baseline_bicubic")
        if not isinstance(baseline, dict):
            raise EvidenceError(f"{scene}: missing bicubic baseline measurements")
        positive(baseline.get("mae_rgb"), f"{scene} bicubic MAE")
        positive(baseline.get("mse_rgb"), f"{scene} bicubic MSE")
        scene_psnr = baseline.get("psnr_rgb_db")
        if (scene_psnr is not None and
                (isinstance(scene_psnr, bool) or not isinstance(scene_psnr, (int, float)) or
                 not math.isfinite(scene_psnr))):
            raise EvidenceError(f"{scene}: invalid bicubic PSNR")
        for name in ("fsrcnn", "espcn"):
            entry = report["models"].get(name)
            if not isinstance(entry, dict):
                raise EvidenceError(f"{scene}/{name}: invalid model evidence")
            execution = entry.get("execution")
            if not isinstance(execution, dict):
                raise EvidenceError(f"{scene}/{name}: invalid worker evidence")
            if execution.get("status") != "ok":
                raise EvidenceError(f"{scene}/{name}: missing real-model execution")
            if execution.get("model") != name:
                raise EvidenceError(f"{scene}/{name}: wrong worker model identity")
            if execution.get("input_dimensions") != [128, 128] or execution.get("output_dimensions") != [256, 256]:
                raise EvidenceError(f"{scene}/{name}: worker image dimensions mismatch")
            positive(execution.get("max_rss_bytes"), f"{scene}/{name} peak RSS")
            if execution["max_rss_bytes"] >= 4 * 1024 ** 3:
                raise EvidenceError(f"{scene}/{name}: process exceeds 4 GiB RSS")
            warm = execution.get("warm_seconds")
            if not isinstance(warm, list) or not warm:
                raise EvidenceError(f"{scene}/{name}: missing warm timing evidence")
            for duration in warm:
                positive(duration, f"{scene}/{name} warm timing")
            model_hash = performance.get(name, {}).get("model_sha256")
            if execution.get("model_sha256") != model_hash:
                raise EvidenceError(f"{scene}/{name}: model hash mismatch")
            quality = entry.get("quality")
            if not isinstance(quality, dict):
                raise EvidenceError(f"{scene}/{name}: missing quality measurements")
            if quality.get("dimensions") != [256, 256]:
                raise EvidenceError(f"{scene}/{name}: invalid prediction dimensions")
            for label in ("prediction_metrics", "baseline_metrics"):
                m = quality.get(label)
                if not isinstance(m, dict):
                    raise EvidenceError(f"{scene}/{name}: missing {label}")
                for key in ("mae_rgb", "mse_rgb"):
                    value = m.get(key)
                    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                        raise EvidenceError(f"{scene}/{name}/{label}: invalid {key}")
                psnr = m.get("psnr_rgb_db")
                if psnr is not None and (isinstance(psnr, bool) or not isinstance(psnr, (int, float)) or not math.isfinite(psnr)):
                    raise EvidenceError(f"{scene}/{name}/{label}: invalid PSNR")
            for key in ("mae_rgb", "mse_rgb", "psnr_rgb_db"):
                if quality["baseline_metrics"].get(key) != baseline.get(key):
                    raise EvidenceError(f"{scene}/{name}: baseline {key} mismatch")
    baseline_result["scenes_verified"] = list(SCENES)
    baseline_result["quality_summary"] = summarize_quality(reports)
    baseline_result["model_scene_combinations"] = len(SCENES) * 2
    return baseline_result



def summarize_quality(reports):
    """Record objective differences without imposing unsupported superiority claims."""
    rows = []
    for scene in SCENES:
        report = reports[scene]
        baseline = report["baseline_bicubic"]
        for model in ("fsrcnn", "espcn"):
            predicted = report["models"][model]["quality"]["prediction_metrics"]
            improvement = round(baseline["mae_rgb"] - predicted["mae_rgb"], 6)
            baseline_psnr = baseline["psnr_rgb_db"]
            prediction_psnr = predicted["psnr_rgb_db"]
            psnr_delta = (round(prediction_psnr - baseline_psnr, 6)
                          if baseline_psnr is not None and prediction_psnr is not None else None)
            rows.append({
                "scene": scene, "model": model,
                "mae_improvement_vs_bicubic": improvement,
                "psnr_delta_db_vs_bicubic": psnr_delta,
                "beats_bicubic_on_mae": improvement > 0,
            })
    return rows


def validate_image_manifest(manifest, images_dir=None):
    """Validate paired-image metadata; image bytes must also be checked at capture time."""
    if manifest.get("dataset") != "deterministic-synthetic-textures-v1":
        raise EvidenceError("Paired-image manifest dataset mismatch")
    expected = {
        "reference-hr.png": [256, 256],
        "input-lr.png": [128, 128],
        "bicubic-2x.png": [256, 256],
        "models/fsrcnn-2x.png": [256, 256],
        "models/espcn-2x.png": [256, 256],
    }
    images = manifest.get("images")
    if not isinstance(images, dict) or set(images) != set(expected):
        raise EvidenceError("Paired-image manifest missing or unexpected images")
    for name, dimensions in expected.items():
        entry = images[name]
        if not isinstance(entry, dict) or entry.get("dimensions") != dimensions:
            raise EvidenceError(f"{name}: invalid manifest dimensions")
        digest = entry.get("sha256")
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-fA-F]{64}", digest) is None:
            raise EvidenceError(f"{name}: invalid SHA256")
        size = entry.get("bytes")
        if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
            raise EvidenceError(f"{name}: invalid byte length")
        if images_dir is not None:
            root = Path(images_dir).resolve()
            file_path = (root / name).resolve()
            if not file_path.is_relative_to(root) or not file_path.is_file():
                raise EvidenceError(f"{name}: paired image file missing or unsafe")
            actual = file_path.read_bytes()
            if len(actual) != size or hashlib.sha256(actual).hexdigest().lower() != digest.lower():
                raise EvidenceError(f"{name}: paired image bytes do not match manifest")
    return {"paired_images_verified": len(expected)}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--performance", type=Path, required=True)
    parser.add_argument("--quality", type=Path, required=True)
    parser.add_argument("--api", type=Path, required=True)
    parser.add_argument("--quality-edges", type=Path, required=True)
    parser.add_argument("--quality-smooth", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--images-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        documents = [json.loads(path.read_text()) for path in (args.performance, args.quality, args.api)]
        reports = {"textures": documents[1],
                   "edges": json.loads(args.quality_edges.read_text()),
                   "smooth": json.loads(args.quality_smooth.read_text())}
        result = validate_scene_bundle(documents[0], reports, documents[2])
        result.update(validate_image_manifest(json.loads(args.manifest.read_text()), args.images_dir))
        print(json.dumps(result, indent=2))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"Release evidence gate failed: {exc}\n")


if __name__ == "__main__":
    main()
