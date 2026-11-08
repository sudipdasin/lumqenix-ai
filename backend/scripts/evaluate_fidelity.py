"""Reference reconstruction on an operator-supplied image; no identity claim.

Downsample a known reference then compare reconstruction at equal dimensions.
This synthetic degradation does not represent all real damaged portraits.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import fsrcnn, espcn


def run(source_path, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(source_path) as image:
        reference = ImageOps.exif_transpose(image).convert('RGB')
        reference.thumbnail((512, 512), Image.Resampling.LANCZOS)
    reference = reference.crop((0, 0, reference.width // 2 * 2, reference.height // 2 * 2))
    low = reference.resize((reference.width // 2, reference.height // 2), Image.Resampling.LANCZOS)
    outputs = {'reference': reference, 'lanczos': low.resize(reference.size, Image.Resampling.LANCZOS),
               'fsrcnn': fsrcnn.upscale(low), 'espcn': espcn.upscale(low),
               'portrait-v2': fsrcnn.upscale(low, portrait=True)}
    for strength in (0, 35, 100):
        outputs[f'portrait-v3-{strength}'] = fsrcnn.upscale(low, portrait='v3', strength=strength)
    original = np.asarray(reference, dtype=np.float64)
    results = {'source_sha256': hashlib.sha256(source_path.read_bytes()).hexdigest(),
               'reference_dimensions': list(reference.size), 'metrics': {}}
    grid = Image.new('RGB', (reference.width * 4, (reference.height + 26) * 2), 'white')
    draw = ImageDraw.Draw(grid)
    for index, (name, image) in enumerate(outputs.items()):
        image.save(output_dir / (name + '.png'))
        x, y = index % 4 * reference.width, index // 4 * (reference.height + 26)
        grid.paste(image, (x, y + 26)); draw.text((x + 8, y + 5), name, fill='black')
        if name == 'reference':
            continue
        mse = float(np.mean((np.asarray(image, dtype=np.float64) - original) ** 2))
        results['metrics'][name] = {'psnr_db': round(10 * np.log10(255 ** 2 / mse), 4) if mse else None,
                                   'mae_rgb': round(float(np.abs(np.asarray(image, dtype=np.float64) - original).mean()), 4)}
    grid.save(output_dir / 'comparison.png')
    results['strength_zero_matches_baseline'] = bool(np.array_equal(np.asarray(outputs['portrait-v3-0']), np.asarray(outputs['fsrcnn'])))
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.input, args.output_dir), indent=2))
