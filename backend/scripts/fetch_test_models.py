"""Explicit test-only download of pinned pretrained weights, verified before use."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((Path(__file__).resolve().parents[1] / 'models/pretrained.json').read_text())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for item in manifest.values():
        with urllib.request.urlopen(item['url'], timeout=30) as response:
            data = response.read(2 * 1024 * 1024 + 1)
        if hashlib.sha256(data).hexdigest() != item['sha256']:
            raise RuntimeError('Pretrained model checksum mismatch: ' + item['filename'])
        target = args.output_dir / item['filename']
        target.write_bytes(data)
        print(target)


if __name__ == '__main__':
    main()
