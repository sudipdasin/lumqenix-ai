# Lumqenix AI — Community (Studio Lite)

Local image and video enhancement for CPU use. Current build: **0.3.0-dev.7**, an evidence-backed development build, not a production release candidate. See [CHANGELOG.md](CHANGELOG.md) and [validation evidence](benchmarks/VALIDATION.md).

## Editions and open-source participation

This repository contains the **Community edition**, licensed under the
[MIT License](LICENSE). Its free features run locally without an account or
Pro license. The planned commercial **Pro edition** uses a separate
**private** repository and consumes the Community core through a versioned
contract. Private algorithms, model assets, payment and signing secrets must
never be placed in public source or history.

The machine-readable `GET /api/edition` endpoint reports Community edition
identity and available-in-source capabilities (not whether optional neural
weights are installed). See [the dual-edition architecture](docs/COMMUNITY_PRO_STRATEGY.md),
[contributing](CONTRIBUTING.md), [security](SECURITY.md),
[third-party notices](docs/THIRD_PARTY_NOTICES.md), and
[publication checklist](docs/COMMUNITY_RELEASE_CHECKLIST.md).

The Community GitHub repository is **public**. Its development branch is not
a certified release candidate; full-history, dependency-rights, and artifact
audits remain open. The separate **Pro repository is private**, but a finished
commercial build and entitlement service are not yet available.

## Engines

| Engine | Behavior | Status |
| --- | --- | --- |
| Classic | Pillow/OpenCV filtering and Lanczos 1×/2×/4× | Automated API tests |
| FSRCNN | Pretrained neural 2× CPU inference | Real weights and API tested |
| ESPCN | Pretrained neural 2× CPU inference | Real weights and API tested |
| Portrait v2/v3 | FSRCNN with optional denoising and luminance sharpening | Experimental; filters can reduce fidelity |
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

Portrait v3 strength 0 is exactly baseline FSRCNN; higher strengths add filters, not new learned detail. Keep baseline available and inspect eyes, teeth, hair, skin texture, and color at equal output sizes.

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
- Video: finite known duration ≤60 seconds, processing timeout 180 seconds, buffered output ≤100 MiB; odd dimensions are padded to even dimensions.
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
