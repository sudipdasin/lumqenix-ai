# Reproduce measurements

Run from `backend/` in the isolated contrib environment described in README. The exact tested Python 3.12 packages are in `benchmarks/environment-py312.txt`; the application supports broader version ranges.

```bash
python scripts/fetch_test_models.py --output-dir /tmp/lumqenix-models
export LUMQENIX_FSRCNN_MODEL=/tmp/lumqenix-models/FSRCNN_x2.pb
export LUMQENIX_ESPCN_MODEL=/tmp/lumqenix-models/ESPCN_x2.pb
curl -fL https://raw.githubusercontent.com/scikit-image/scikit-image/v0.25.2/skimage/data/astronaut.png -o /tmp/lumqenix-astronaut.png
printf '88431cd9653ccd539741b555fb0a46b61558b301d4110412b5bc28b5e3ea6cb5  /tmp/lumqenix-astronaut.png\n' | sha256sum -c -
python scripts/benchmark_models.py --input /tmp/lumqenix-astronaut.png --output-dir /tmp/lumqenix-benchmark --repeats 3 --require-models
python scripts/evaluate_fidelity.py --input /tmp/lumqenix-astronaut.png --output-dir /tmp/lumqenix-fidelity
python -m pytest -q tests
```

Repeat the sequential 2 GiB virtual-address-limit experiment on Linux, from `backend/`:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 python - <<'PY'
import json, resource, time
resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
from PIL import Image
from app import fsrcnn, espcn
from app.engine import enhance
results = []
for name, operation, source in (
    ('fsrcnn', fsrcnn.upscale, Image.open('/tmp/lumqenix-astronaut.png')),
    ('espcn', espcn.upscale, Image.open('/tmp/lumqenix-astronaut.png')),
    ('classic', lambda im: enhance(im, 'auto', 2)[0], Image.new('RGB', (2000, 1500))),
):
    start = time.perf_counter()
    output = operation(source)
    results.append({'name': name, 'output': output.size, 'seconds': time.perf_counter() - start})
print(json.dumps({'cases': results, 'peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}, indent=2))
PY
```

Virtual address space and RSS describe a process, not total laptop memory. Do not treat this run as physical 4 GB laptop validation. Peak RSS of separate neural benchmarks includes initialization and PNG saving; inference times exclude encoding. Timing will vary by CPU and load.
