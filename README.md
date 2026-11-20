# Lumqenix AI — Studio Lite

Local image and video enhancement for CPU use. Preview candidate build: **0.3.0-rc.4 (beta preview)**. This is an **experimental prerelease candidate**, not a production-certified release. The main branch remains unchanged. CI and real-model quality gates must be reviewed before production use. See [CHANGELOG.md](CHANGELOG.md) and [validation evidence](benchmarks/VALIDATION.md).

## Linux beta preview — install and feedback

**Release channel:** `preview/v0.3.0-rc.4-beta`. This is a source-installable beta, **not a verified production binary**. On Linux with Python 3.10+:

```bash
git clone --branch preview/v0.3.0-rc.4-beta https://github.com/sudipdasin/lumqenix-ai.git
cd lumqenix-ai
bash scripts/install-linux.sh
bash scripts/run-linux.sh
```

Open http://127.0.0.1:8080. The installer uses a local `.venv` without root permissions. FFmpeg and ffprobe must be installed separately for video processing. Stop with Ctrl+C. To remove the local installation, delete the cloned directory; no system service is installed. No pretrained weights are included by default.

**Artifact verification:** Successful GitHub Actions preview runs produce a source ZIP and a matching `.sha256` checksum file. In the download directory, run `sha256sum -c lumqenix-community-v0.3.0-rc.4-source.zip.sha256` before extracting the CI artifact. The GitHub branch ZIP linked above is a separate automatically generated archive and is **not** covered by that CI checksum. Do not treat an artifact as validated until the workflow run has passed.

**Distribution note:** the Community repository is public, and tagged beta releases provide verified source ZIP assets once the exact-commit CI and packaging gates pass. This branch is an RC3 candidate, not a native installer or stable release. Do not expose the local API to the public internet.

Report sanitized bugs and suggestions through [GitHub Issues](https://github.com/sudipdasin/lumqenix-ai/issues/new/choose). Never upload private photos, personal paths, credentials, or sensitive media. Contributions are welcome subject to the repository's MIT license.

## Engines

| Engine | Behavior | Status |
| --- | --- | --- |
| Classic | Pillow/OpenCV filtering and Lanczos 1×/2×/4× | Automated API tests |
| FSRCNN | Pretrained neural 2× CPU inference | Real weights and API tested |
| ESPCN | Pretrained neural 2× CPU inference | Real weights and API tested |
| Portrait v2/v3 | FSRCNN with optional denoising and luminance sharpening | Experimental; filters can reduce fidelity |
| Portrait Guard v4 | Optional FSRCNN/bicubic blend minimizing input downsampling-cycle MSE | Experimental LR-consistency safeguard, not proof of facial fidelity |
| ONNX | Optional tiled 2×/4× neural adapter | Real runtime plumbing tested; no pretrained ONNX model certified |
| Video | FFmpeg filtering, Lanczos scaling, H.264/AAC output | Real short-video API test |

No GAN, newly trained face model, temporal neural restoration, or true HDR encoding is included. Enhancement cannot guarantee recovery of authentic missing detail.

## Run locally

Requires Python 3.10+ and FFmpeg/ffprobe for video. Use a separate virtual environment and bind the API to localhost. Run **one Uvicorn worker**: processing admission is per process.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

On Windows activate `.venv\Scripts\activate`. From the repository root, serve Studio:

```bash
python -m http.server 8080 --bind 127.0.0.1 --directory frontend
```

Open http://localhost:8080; API docs: http://127.0.0.1:8000/docs. Branding is in `config/brand.json`.

## Optional pretrained CPU engines

Install only **one OpenCV wheel** in this environment. After installing base requirements, replace the standard headless wheel with contrib:

```bash
python -m pip uninstall -y opencv-python-headless
python -m pip install 'opencv-contrib-python-headless>=4.9,<5'
```

Weights are not bundled or downloaded during application startup. To explicitly fetch the pinned upstream FSRCNN and ESPCN **test** models, with SHA256 verification:

```bash
python scripts/fetch_test_models.py --output-dir /tmp/lumqenix-models
export LUMQENIX_FSRCNN_MODEL=/tmp/lumqenix-models/FSRCNN_x2.pb
export LUMQENIX_ESPCN_MODEL=/tmp/lumqenix-models/ESPCN_x2.pb
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

PowerShell users should set `$env:LUMQENIX_FSRCNN_MODEL` and `$env:LUMQENIX_ESPCN_MODEL` instead of `export`, and choose a suitable local model directory. Model provenance and hashes live in `backend/models/pretrained.json`. Review upstream licensing before distributing weights.

Portrait v3 strength 0 is exactly baseline FSRCNN; higher strengths add filters, not new learned detail. Portrait Guard v4 strength 0 gives bicubic; higher strength allows more neural detail only when it does not increase the measured downsampling-cycle error versus bicubic. This proxy is not a ground-truth high-resolution or facial-identity metric. Keep baseline available and inspect eyes, teeth, hair, skin texture, and color at equal output sizes.

## Optional ONNX adapter

Install `onnxruntime>=1.18,<2` alongside your chosen OpenCV wheel. Supply a trusted model with a single NCHW RGB float32 input normalized to [0,1], batch 1 or dynamic batch, dynamic spatial dimensions, and one output at 2× or 4× scale.

```bash
export LUMQENIX_ONNX_MODEL=/absolute/path/model.onnx
export LUMQENIX_ONNX_SCALE=2
```

Static spatial shapes, alternate channel order/normalization, and arbitrary model exports are unsupported. GPU providers are optional and unverified; automatic CPU retry after GPU failure is not implemented. `/api/status` configuration flags do not certify that model weights load correctly. The generated nearest-neighbor ONNX test checks runtime plumbing and tile assembly, **not pretrained enhancement quality**.

## Limits and API

- Upload limit: 50 MiB; output limit: 12 million pixels.
- FSRCNN/ESPCN input: at most 262,144 pixels (512×512 equivalent); two OpenCV threads.
- Video: finite known duration ≤60 seconds, processing timeout 180 seconds, buffered output ≤100 MiB; odd dimensions are padded to even dimensions. Conservatively reject excess workload beyond 1,800 estimated frames or 450 million estimated output samples; malformed FFprobe FPS/frame-count metadata is rejected before FFmpeg encoding.
- One analysis/enhancement job per process; overlapping jobs receive HTTP 429. Status remains responsive.
- Invalid input returns 400/422, oversize input 413, and unavailable engines 503.

| Endpoint | Form fields |
| --- | --- |
| `GET /api/status`, `GET /api/brand` | None |
| `POST /api/analyze` | `file` |
| `POST /api/enhance/image` | `file`, `preset`, `scale=1|2|4` |
| `POST /api/enhance/fsrcnn` | `file`, `portrait`, `portrait_version=2|3`, `strength=0..100` |
| `POST /api/enhance/espcn` | `file` |
| `POST /api/enhance/onnx` | `file`, `device=auto|cpu|gpu`, `tile`, `overlap` |
| `POST /api/enhance/video` | `file`, `preset`, `scale=1|2|4` |

Presets: auto, natural, vivid, restore, cinematic, portrait. Video re-encodes audio to AAC.

## Tests and reproducible measurements

```bash
cd backend
python -m pip install pytest httpx
python -m pytest -q tests
# Optional generated-graph ONNX runtime tests:
python -m pip install 'onnxruntime>=1.18,<2' onnx
# With contrib and both pretrained model environment variables configured:
python scripts/benchmark_models.py --input /path/to/portrait.png --output-dir /tmp/lumqenix-benchmark --repeats 3 --require-models
python scripts/evaluate_fidelity.py --input /path/to/reference.png --output-dir /tmp/lumqenix-fidelity
```

Missing real weights are explicitly skipped in tests. CI runs Python 3.10/3.12 with classic and real pretrained model environments. Benchmarks report cold inference, three warm runs, model hashes, environment, and isolated process peak RSS; times exclude PNG encoding. Reference evaluation downsamples a known image and measures reconstruction at matching dimensions. It does not establish facial identity preservation on real degraded inputs.

## Remaining release gates

Physical 4 GB laptop validation, representative user-portrait A/B approval, and a compatible pretrained ONNX model evaluation remain open. Windows, GPU execution, long-duration video quality, hostile traffic, and multi-user deployment are unverified. The process lock does not bound multipart upload parsing or total host/browser memory. This application is intended for local single-user use; a public service needs a separate deployment and resource-isolation design. No final release is published.
