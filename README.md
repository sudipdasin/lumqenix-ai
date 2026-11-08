# Lumqenix AI — Milestone 1 (CPU baseline)

A locally runnable prototype for image and video enhancement. **This release does not contain a GAN, learned upscaler, temporal AI restoration, or true HDR encoding.** It uses conventional Pillow/OpenCV image filters, Lanczos scaling, and FFmpeg video filters. Branding is provisional and centralized in `config/brand.json`.

## Requirements
- Python 3.10+
- FFmpeg and ffprobe on PATH (video only)

## Start
```bash
cd backend
python -m venv .venv
source .venv/bin/activate # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

In another terminal from the repository root:
```bash
python -m http.server 8080 --directory frontend
```
Open http://localhost:8080. API docs: http://localhost:8000/docs.

## Endpoints
- `GET /api/status` — CPU and FFmpeg availability
- `GET /api/brand` — configurable product identity
- `POST /api/analyze` — image brightness and sharpness heuristic
- `POST /api/enhance/image` — image enhancement; form: file, preset, scale
- `POST /api/enhance/video` — video enhancement; form: file, preset, scale

## Limitations and next steps
- Prototype uses synchronous video processing, max 50 MB upload, 180-second processing timeout; not suited to production traffic.
- Video currently re-encodes audio to AAC; original audio streams are not preserved losslessly.
- Video analysis is limited to basic metadata; no scene-aware or temporal AI logic yet.
- Add a queued job system, secure upload storage, real hardware detection, ONNX Runtime/Real-ESRGAN, tiling, and model licensing review before production.
- For deployment add authentication, rate limits, strict video duration limits, and resource isolation.

## Milestone 2: optional ONNX AI super-resolution

Install optional dependencies from the `backend` directory:

```bash
pip install -r requirements-onnx.txt
pip install pytest
```

Provide a **trusted, compatible** NCHW RGB float32 ONNX super-resolution model with one input and one output, normalized [0,1] tensors, and 2x or 4x output scale. The model must support the variable spatial tile sizes used by this prototype. Model weights are not included or downloaded automatically; review licensing and model provenance before use.

```bash
export LUMQENIX_ONNX_MODEL=/absolute/path/to/model.onnx
export LUMQENIX_ONNX_SCALE=4
uvicorn app.main:app --reload --port 8000
```

Use `GET /api/status` to inspect available ONNX providers. Upload an image to `POST /api/enhance/onnx` with optional form fields `device=auto|cpu|gpu`, `tile=128`, `overlap=16`. The API returns PNG. Explicit GPU mode errors when no supported provider is present. Auto mode chooses a reported provider but does **not** guarantee a functioning GPU or automatically retry CPU after a GPU runtime failure.

**Current constraints:** Only images use ONNX; video remains FFmpeg-based. Model compatibility is not automatically established, and some models require fixed tile dimensions, special normalization, or different output layouts. Overlap mitigates tile seams but does not guarantee seam-free results. This is not yet a production-ready or fully tested neural pipeline.

Run unit tests: `cd backend && python -m pytest tests -q`.

## Milestone 3: Lite mode and before/after interface

The default Lite configuration targets older dual-core machines with approximately 4 GB RAM. The backend caps image/video output at **12 million pixels**, rejects simultaneous processing requests with HTTP 429, and limits FFmpeg threads to two. This is a conservative prototype cap, not a full system-memory monitor. Existing large 2x tests may now receive HTTP 413: reduce input dimensions or select 1x.

The browser interface now offers a gentle **Portrait Restore** classic preset, original/enhanced image comparison, input/output dimensions, and an **AI super-resolution** option. The AI option is available only when the server has been configured with a compatible ONNX model; no model weights are bundled. AI mode defaults to CPU, tile 64, overlap 8. This version does **not** integrate or distribute Real-ESRGAN weights, nor does it guarantee compatibility with any particular ONNX export.

Update a local checkout with `git pull`, stop and restart Uvicorn, and hard-refresh the browser (Ctrl+Shift+R). On a shared Windows/Linux NTFS partition, use a Python environment located on the Linux filesystem.

**Testing status:** Files were committed through GitHub. Full end-to-end runtime and neural-model inference testing on the user's laptop remain outstanding.

## Milestone 4: low-memory neural inference preparation

The optional ONNX runner now limits CPU inference to at most two intra-op threads, uses sequential execution, and crops tiles from Pillow instead of allocating an additional full-size RGB NumPy array. These changes reduce some memory overhead but do not guarantee that arbitrary neural models will fit within 4 GB RAM.

**No neural model weights are bundled or automatically downloaded.** To evaluate a trusted compatible ONNX model, first install `onnxruntime` in an isolated environment (avoid changing a working shared AI environment without a backup), then set `LUMQENIX_ONNX_MODEL` and `LUMQENIX_ONNX_SCALE`. Start with:

```bash
cd backend
LUMQENIX_ONNX_MODEL=/absolute/path/model.onnx LUMQENIX_ONNX_SCALE=2 \
  python scripts/benchmark_onnx.py --input "/path/to/portrait.jpg" \
  --tile 64 --overlap 8 --max-input-side 256
```

The benchmark always requests CPU and writes `/tmp/lumqenix-ai-benchmark.png` by default. Model must accept variable NCHW RGB float32 [0,1] patches and produce the configured spatial upscale factor. Models using fixed input shapes, mean/std normalization, alternate channel orders or different output ranges are **not** supported by this adapter. Benchmarks have not yet been run on the target laptop.

A potential alternative for low-RAM experimentation is OpenCV's FSRCNN x2 model, but it uses a TensorFlow `.pb` format and OpenCV's contrib `dnn_superres` interface; it cannot be used directly with the ONNX endpoint. See the official OpenCV dnn_superres documentation for that separate route.
