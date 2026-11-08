import io
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
import os
import threading
import cv2
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError
from .engine import enhance, inspect, PRESETS
from .hardware import detect_hardware
from .onnx_upscale import upscale as onnx_upscale, model_path, configured_scale
from .fsrcnn import upscale as fsrcnn_upscale, model_path as fsrcnn_model_path, available as fsrcnn_available
from .espcn import upscale as espcn_upscale, available as espcn_available
from .version import VERSION

app = FastAPI(title="Lumqenix API", version=VERSION)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"], allow_methods=["*"], allow_headers=["*"])
MAX_UPLOAD = 50 * 1024 * 1024
MAX_PIXELS = 32_000_000
LITE_MAX_PIXELS = 12_000_000
PROCESSING_LOCK = threading.Lock()
Image.MAX_IMAGE_PIXELS = MAX_PIXELS

@app.get("/api/status")
def status():
    return {"status":"ok", "version": VERSION, "hardware":detect_hardware(), "ai_model_configured":bool(__import__("os").getenv("LUMQENIX_ONNX_MODEL")),
            "fsrcnn_available":fsrcnn_available(), "espcn_available":espcn_available(),
            "ffmpeg_available":bool(shutil.which("ffmpeg")), "presets":sorted(PRESETS), "lite_mode": True, "lite_max_output_pixels":LITE_MAX_PIXELS}

@app.get("/api/brand")
def brand():
    path = Path(__file__).resolve().parents[2] / "config" / "brand.json"
    return json.loads(path.read_text())

async def read_limited(file: UploadFile):
    content = await file.read(MAX_UPLOAD + 1)
    if len(content) > MAX_UPLOAD: raise HTTPException(413, "File exceeds 50 MB")
    return content

@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):
    try:
        data = await read_limited(file)
        with Image.open(io.BytesIO(data)) as image:
            if image.width * image.height > MAX_PIXELS: raise HTTPException(413, "Image too large")
            return inspect(image)
    except (UnidentifiedImageError, OSError, ValueError): raise HTTPException(400, "Unsupported or invalid image")

@app.post("/api/enhance/image")
async def enhance_image(file: UploadFile = File(...), preset: str = Form("auto"), scale: int = Form(2)):
    if preset not in PRESETS or scale not in (1,2,4): raise HTTPException(400, "Invalid preset or scale")
    try:
        data = await read_limited(file)
        with Image.open(io.BytesIO(data)) as image:
            if image.width * image.height * scale * scale > LITE_MAX_PIXELS: raise HTTPException(413, "Lite mode output limit: 12 million pixels. Use a smaller image or lower scale.")
            if not PROCESSING_LOCK.acquire(blocking=False): raise HTTPException(429, "Another job is processing; try again shortly")
            try:
                result, _ = enhance(image, preset, scale)
            finally:
                PROCESSING_LOCK.release()
        output = io.BytesIO()
        result.save(output, format="PNG", optimize=True)
        return Response(content=output.getvalue(), media_type="image/png", headers={"Content-Disposition":"attachment; filename=enhanced.png"})
    except (UnidentifiedImageError, OSError, ValueError): raise HTTPException(400, "Unsupported or invalid image")

@app.post("/api/enhance/onnx")
async def enhance_onnx(file: UploadFile = File(...), device: str = Form("auto"),
                       tile: int = Form(128), overlap: int = Form(16)):
    """Optional AI super-resolution; model must be configured by server operator."""
    if device not in ("auto", "cpu", "gpu") or not 32 <= tile <= 512 or not 0 <= overlap <= 64 or overlap*2 >= tile:
        raise HTTPException(400, "Invalid device, tile or overlap")
    try:
        path = model_path()
        if path is None:
            raise HTTPException(503, "ONNX model not configured")
        scale = configured_scale()
        data = await read_limited(file)
        with Image.open(io.BytesIO(data)) as image:
            if image.width * image.height * scale * scale > LITE_MAX_PIXELS:
                raise HTTPException(413, "Lite mode output limit: 12 million pixels")
            if not PROCESSING_LOCK.acquire(blocking=False): raise HTTPException(429, "Another job is processing; try again shortly")
            try:
                result, used_device = onnx_upscale(image, device, tile, overlap)
            finally:
                PROCESSING_LOCK.release()
        output = io.BytesIO()
        result.save(output, format="PNG")
        return Response(content=output.getvalue(), media_type="image/png",
                        headers={"Content-Disposition":"attachment; filename=ai-upscaled.png",
                                 "X-Lumqenix-Device":used_device})
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(400, str(exc))
    except (RuntimeError, ImportError) as exc:
        raise HTTPException(503, str(exc))


@app.post("/api/enhance/fsrcnn")
async def enhance_fsrcnn(file: UploadFile = File(...), portrait: bool = Form(False),
                         portrait_version: int = Form(2), strength: int = Form(35)):
    """Pretrained FSRCNN 2x on CPU, restricted to small images in Lite mode."""
    if portrait_version not in (2, 3) or not 0 <= strength <= 100:
        raise HTTPException(400, "Invalid portrait version or strength")
    if not fsrcnn_available():
        raise HTTPException(503, "FSRCNN unavailable: configure model and OpenCV contrib")
    if not PROCESSING_LOCK.acquire(blocking=False):
        raise HTTPException(429, "Another job is processing; try again shortly")
    try:
        data = await read_limited(file)
        with Image.open(io.BytesIO(data)) as image:
            result = fsrcnn_upscale(image, portrait=("v3" if portrait and portrait_version == 3 else portrait), strength=strength)
        output = io.BytesIO()
        result.save(output, format="PNG")
        return Response(content=output.getvalue(), media_type="image/png",
                        headers={"Content-Disposition": "attachment; filename=" + ("fsrcnn-portrait-v3-2x.png" if portrait and portrait_version == 3 else "fsrcnn-portrait-2x.png" if portrait else "fsrcnn-2x.png")})
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(400, str(exc))
    except (RuntimeError, cv2.error) as exc:
        raise HTTPException(503, str(exc))
    finally:
        PROCESSING_LOCK.release()

@app.post("/api/enhance/espcn")
async def enhance_espcn(file: UploadFile = File(...)):
    """Experimental pretrained ESPCN x2 CPU mode."""
    if not espcn_available():
        raise HTTPException(503, "ESPCN unavailable: configure LUMQENIX_ESPCN_MODEL")
    if not PROCESSING_LOCK.acquire(blocking=False):
        raise HTTPException(429, "Another job is processing; try again shortly")
    try:
        data = await read_limited(file)
        with Image.open(io.BytesIO(data)) as image:
            result = espcn_upscale(image)
        output = io.BytesIO()
        result.save(output, format="PNG")
        return Response(content=output.getvalue(), media_type="image/png",
                        headers={"Content-Disposition": "attachment; filename=espcn-2x.png"})
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(400, str(exc))
    except (RuntimeError, cv2.error) as exc:
        raise HTTPException(503, str(exc))
    finally:
        PROCESSING_LOCK.release()

@app.post("/api/enhance/video")
async def enhance_video(file: UploadFile = File(...), preset: str = Form("auto"), scale: int = Form(2)):
    if preset not in PRESETS or scale not in (1,2,4): raise HTTPException(400, "Invalid preset or scale")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"): raise HTTPException(503, "FFmpeg and ffprobe required")
    data = await read_limited(file)
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = Path(tmp)/"source", Path(tmp)/"enhanced.mp4"
        src.write_bytes(data)
        probe = subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height","-of","csv=p=0",str(src)],capture_output=True,text=True,timeout=20)
        try:
            width,height = map(int,probe.stdout.strip().split(","))
            if width * height * scale * scale > LITE_MAX_PIXELS: raise ValueError()
        except ValueError: raise HTTPException(400,"Invalid video or oversized output")
        filters = {"auto":"eq=contrast=1.05:saturation=1.08,unsharp=3:3:0.4", "natural":"unsharp=3:3:0.3", "vivid":"eq=contrast=1.1:saturation=1.3", "restore":"hqdn3d=2:1.5:3:2,unsharp=3:3:0.3", "cinematic":"eq=contrast=1.16:saturation=1.1", "portrait":"hqdn3d=1:1:2:2,eq=contrast=1.03:saturation=1.02"}
        vf = filters[preset] + f",scale=iw*{scale}:ih*{scale}:flags=lanczos,format=yuv420p"
        if not PROCESSING_LOCK.acquire(blocking=False): raise HTTPException(429, "Another job is processing; try again shortly")
        try:
            subprocess.run(["ffmpeg","-threads","2","-filter_threads","2","-nostdin","-v","error","-y","-i",str(src),"-vf",vf,"-c:v","libx264","-preset","veryfast","-crf","19","-c:a","aac","-movflags","+faststart",str(dst)],check=True,timeout=180,capture_output=True)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired): raise HTTPException(422,"Video processing failed or timed out")
        finally:
            PROCESSING_LOCK.release()
        return Response(content=dst.read_bytes(),media_type="video/mp4",headers={"Content-Disposition":"attachment; filename=enhanced.mp4"})
