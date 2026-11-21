"""Fetch pinned pretrained test weights with bounded downloads and atomic writes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import urllib.parse
import urllib.request

MAX_MODEL_BYTES = 2 * 1024 * 1024


def validate_model_entry(item):
    if not isinstance(item, dict):
        raise ValueError("Invalid pretrained model manifest entry")
    name = item.get("filename")
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_-]+[.]pb", name):
        raise ValueError("Unsafe pretrained model filename")
    url = item.get("url")
    parsed = urllib.parse.urlparse(url) if isinstance(url, str) else None
    if parsed is None or parsed.scheme != "https" or parsed.hostname != "raw.githubusercontent.com" or parsed.username or parsed.password:
        raise ValueError("Untrusted pretrained model URL")
    digest = item.get("sha256")
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-fA-F]{64}", digest) is None:
        raise ValueError("Invalid pretrained model SHA-256")
    return name, url, digest.lower()


def download_model(item, output_dir):
    name, url, digest = validate_model_entry(item)
    target = output_dir / name
    with urllib.request.urlopen(url, timeout=30) as response:
        data = response.read(MAX_MODEL_BYTES + 1)
    if not data or len(data) > MAX_MODEL_BYTES:
        raise RuntimeError("Pretrained model size outside allowed bounds: " + name)
    if hashlib.sha256(data).hexdigest() != digest:
        raise RuntimeError("Pretrained model checksum mismatch: " + name)
    fd, tmp_name = tempfile.mkstemp(prefix=".model-", suffix=".tmp", dir=output_dir)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp_name, target)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((Path(__file__).resolve().parents[1] / "models/pretrained.json").read_text())
    if not isinstance(manifest, dict) or set(manifest) != {"fsrcnn", "espcn"}:
        raise ValueError("Unexpected pretrained model manifest")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for item in manifest.values():
        print(download_model(item, args.output_dir))


if __name__ == "__main__":
    main()
