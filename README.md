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
