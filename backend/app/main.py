import io
import json
import math
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
MAX_VIDEO_OUTPUT = 100 * 1024 * 1024
MAX_VIDEO_DURATION = 60
MAX_PIXELS = 32_000_000
LITE_MAX_PIXELS = 12_000_000
PROCESSING_LOCK = threading.Lock()
Image.MAX_IMAGE_PIXELS = MAX_PIXELS

@app.get("/api/status")
def status():
    try:
        onnx_ready = model_path() is not None and configured_scale() in (2, 4)
    except ValueError:
        onnx_ready = False
    return {"status":"ok", "version": VERSION, "hardware":detect_hardware(), "ai_model_configured":onnx_ready,
            "fsrcnn_available":fsrcnn_available(), "espcn_available":espcn_available(),
            "ffmpeg_available":bool(shutil.which("ffmpeg") and shutil.which("ffprobe")), "presets":sorted(PRESETS), "lite_mode": True, "lite_max_output_pixels":LITE_MAX_PIXELS}

@app.get("/api/brand")
def brand():
    path = Path(__file__).resolve().parents[2] / "config" / "brand.json"
    return json.loads(path.read_text())

def read_limited(file: UploadFile):
    try:
        content = file.file.read(MAX_UPLOAD + 1)
    except (OSError, ValueError) as exc:
        raise HTTPException(503, "Uploaded file could not be read") from exc
    if not isinstance(content, bytes):
        raise HTTPException(503, "Uploaded file could not be read")
    if len(content) > MAX_UPLOAD: raise HTTPException(413, "File exceeds 50 MB")
    return content

@app.post("/api/analyze")
def analyze(file: UploadFile = File(...)):
    data = read_limited(file)
    if not PROCESSING_LOCK.acquire(blocking=False):
        raise HTTPException(429, "Another job is processing; try again shortly")
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.width * image.height > MAX_PIXELS: raise HTTPException(413, "Image too large")
            return inspect(image)
    except Image.DecompressionBombError as exc:
        raise HTTPException(413, "Image too large") from exc
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(400, "Unsupported or invalid image")
    finally:
        PROCESSING_LOCK.release()

@app.post("/api/enhance/image")
def enhance_image(file: UploadFile = File(...), preset: str = Form("auto"), scale: int = Form(2)):
    if preset not in PRESETS or scale not in (1,2,4): raise HTTPException(400, "Invalid preset or scale")
    try:
        data = read_limited(file)
        with Image.open(io.BytesIO(data)) as image:
            if image.width * image.height * scale * scale > LITE_MAX_PIXELS: raise HTTPException(413, "Lite mode output limit: 12 million pixels. Use a smaller image or lower scale.")
            if not PROCESSING_LOCK.acquire(blocking=False): raise HTTPException(429, "Another job is processing; try again shortly")
            try:
                result, _ = enhance(image, preset, scale)
                output = io.BytesIO()
                result.save(output, format="PNG", optimize=True)
                return Response(content=output.getvalue(), media_type="image/png", headers={"Content-Disposition":"attachment; filename=enhanced.png"})
            finally:
                PROCESSING_LOCK.release()
    except Image.DecompressionBombError as exc:
        raise HTTPException(413, "Image too large") from exc
    except (UnidentifiedImageError, OSError, ValueError): raise HTTPException(400, "Unsupported or invalid image")

@app.post("/api/enhance/onnx")
def enhance_onnx(file: UploadFile = File(...), device: str = Form("auto"),
                       tile: int = Form(128), overlap: int = Form(16)):
    """Optional AI super-resolution; model must be configured by server operator."""
    if device not in ("auto", "cpu", "gpu") or not 32 <= tile <= 512 or not 0 <= overlap <= 64 or overlap*2 >= tile:
        raise HTTPException(400, "Invalid device, tile or overlap")
    try:
        try:
            path = model_path()
            scale = configured_scale()
        except ValueError as exc:
            raise HTTPException(503, f"ONNX configuration invalid: {exc}") from exc
        if path is None:
            raise HTTPException(503, "ONNX model not configured")
        data = read_limited(file)
        with Image.open(io.BytesIO(data)) as image:
            if image.width * image.height * scale * scale > LITE_MAX_PIXELS:
                raise HTTPException(413, "Lite mode output limit: 12 million pixels")
            if not PROCESSING_LOCK.acquire(blocking=False): raise HTTPException(429, "Another job is processing; try again shortly")
            try:
                result, used_device = onnx_upscale(image, device, tile, overlap)
                output = io.BytesIO()
                result.save(output, format="PNG")
                return Response(content=output.getvalue(), media_type="image/png",
                                headers={"Content-Disposition":"attachment; filename=ai-upscaled.png",
                                         "X-Lumqenix-Device":used_device})
            finally:
                PROCESSING_LOCK.release()
    except HTTPException:
        raise
    except Image.DecompressionBombError as exc:
        raise HTTPException(413, "Image too large") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(400, str(exc))
    except (RuntimeError, ImportError) as exc:
        raise HTTPException(503, str(exc))


@app.post("/api/enhance/fsrcnn")
def enhance_fsrcnn(file: UploadFile = File(...), portrait: bool = Form(False),
                         portrait_version: int = Form(2), strength: int = Form(35)):
    """Pretrained FSRCNN 2x on CPU, restricted to small images in Lite mode."""
    if portrait_version not in (2, 3) or not 0 <= strength <= 100:
        raise HTTPException(400, "Invalid portrait version or strength")
    if not fsrcnn_available():
        raise HTTPException(503, "FSRCNN unavailable: configure model and OpenCV contrib")
    data = read_limited(file)
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.width * image.height > 512 * 512:
                raise HTTPException(413, "Neural Lite input limit: 262144 pixels")
    except Image.DecompressionBombError as exc:
        raise HTTPException(413, "Image too large") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(400, "Unsupported or invalid image") from exc
    if not PROCESSING_LOCK.acquire(blocking=False):
        raise HTTPException(429, "Another job is processing; try again shortly")
    try:
        with Image.open(io.BytesIO(data)) as image:
            result = fsrcnn_upscale(image, portrait=("v3" if portrait and portrait_version == 3 else portrait), strength=strength)
        output = io.BytesIO()
        result.save(output, format="PNG")
        return Response(content=output.getvalue(), media_type="image/png",
                        headers={"Content-Disposition": "attachment; filename=" + ("fsrcnn-portrait-v3-2x.png" if portrait and portrait_version == 3 else "fsrcnn-portrait-2x.png" if portrait else "fsrcnn-2x.png")})
    except HTTPException:
        raise
    except Image.DecompressionBombError as exc:
        raise HTTPException(413, "Image too large") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(400, str(exc))
    except (RuntimeError, cv2.error) as exc:
        raise HTTPException(503, str(exc))
    finally:
        PROCESSING_LOCK.release()

@app.post("/api/enhance/espcn")
def enhance_espcn(file: UploadFile = File(...)):
    """Experimental pretrained ESPCN x2 CPU mode."""
    if not espcn_available():
        raise HTTPException(503, "ESPCN unavailable: configure LUMQENIX_ESPCN_MODEL")
    data = read_limited(file)
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.width * image.height > 512 * 512:
                raise HTTPException(413, "Neural Lite input limit: 262144 pixels")
    except Image.DecompressionBombError as exc:
        raise HTTPException(413, "Image too large") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(400, "Unsupported or invalid image") from exc
    if not PROCESSING_LOCK.acquire(blocking=False):
        raise HTTPException(429, "Another job is processing; try again shortly")
    try:
        with Image.open(io.BytesIO(data)) as image:
            result = espcn_upscale(image)
        output = io.BytesIO()
        result.save(output, format="PNG")
        return Response(content=output.getvalue(), media_type="image/png",
                        headers={"Content-Disposition": "attachment; filename=espcn-2x.png"})
    except HTTPException:
        raise
    except Image.DecompressionBombError as exc:
        raise HTTPException(413, "Image too large") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(400, str(exc))
    except (RuntimeError, cv2.error) as exc:
        raise HTTPException(503, str(exc))
    finally:
        PROCESSING_LOCK.release()

@app.post("/api/enhance/video")
def enhance_video(file: UploadFile = File(...), preset: str = Form("auto"), scale: int = Form(2)):
    if preset not in PRESETS or scale not in (1,2,4): raise HTTPException(400, "Invalid preset or scale")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"): raise HTTPException(503, "FFmpeg and ffprobe required")
    data = read_limited(file)
    if not data:
        raise HTTPException(400, "Empty video upload")
    if not PROCESSING_LOCK.acquire(blocking=False):
        raise HTTPException(429, "Another job is processing; try again shortly")
    try:
        try:
            temp_dir = tempfile.TemporaryDirectory()
        except OSError as exc:
            raise HTTPException(503, "Video temporary directory unavailable") from exc
        with temp_dir as tmp:
            src, dst = Path(tmp)/"source", Path(tmp)/"enhanced.mp4"
            try:
                src.write_bytes(data)
            except OSError as exc:
                raise HTTPException(503, "Video staging failed") from exc
            try:
                probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                                        "-show_entries", "stream=width,height,duration:format=duration",
                                        "-of", "json", str(src)], capture_output=True, text=True, timeout=20)
                if probe.returncode != 0:
                    raise HTTPException(422, "Could not read video stream")
                metadata = json.loads(probe.stdout)
                stream = metadata["streams"][0]
                width, height = int(stream["width"]), int(stream["height"])
                raw_duration = metadata.get("format", {}).get("duration")
                if raw_duration in (None, "N/A"):
                    raw_duration = stream.get("duration")
                duration = float(raw_duration)
                if width <= 0 or height <= 0 or not math.isfinite(duration) or duration <= 0:
                    raise ValueError("Invalid video dimensions or duration")
                if duration > MAX_VIDEO_DURATION:
                    raise HTTPException(413, "Lite mode video duration limit: 60 seconds")
                output_width = (width * scale + 1) // 2 * 2
                output_height = (height * scale + 1) // 2 * 2
                if output_width * output_height > LITE_MAX_PIXELS:
                    raise HTTPException(413, "Lite mode output limit: 12 million pixels")
            except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError):
                raise HTTPException(422, "Invalid video dimensions or duration")
            except subprocess.TimeoutExpired:
                raise HTTPException(422, "Video inspection timed out")
            except OSError as exc:
                raise HTTPException(503, "Video inspection tool could not start") from exc
            filters = {"auto":"eq=contrast=1.05:saturation=1.08,unsharp=3:3:0.4", "natural":"unsharp=3:3:0.3", "vivid":"eq=contrast=1.1:saturation=1.3", "restore":"hqdn3d=2:1.5:3:2,unsharp=3:3:0.3", "cinematic":"eq=contrast=1.16:saturation=1.1", "portrait":"hqdn3d=1:1:2:2,eq=contrast=1.03:saturation=1.02"}
            vf = filters[preset] + f",scale=iw*{scale}:ih*{scale}:flags=lanczos,pad=ceil(iw/2)*2:ceil(ih/2)*2,format=yuv420p"
            try:
                subprocess.run(["ffmpeg","-threads","2","-filter_threads","2","-nostdin","-v","error","-y","-i",str(src),"-map","0:v:0","-map","0:a:0?","-vf",vf,"-c:v","libx264","-threads","2","-preset","veryfast","-crf","19","-t",str(MAX_VIDEO_DURATION),"-c:a","aac","-movflags","+faststart",str(dst)],check=True,timeout=180,capture_output=True)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                raise HTTPException(422,"Video processing failed or timed out")
            except OSError as exc:
                raise HTTPException(503, "Video processing tool could not start") from exc
            try:
                output_size = dst.stat().st_size
                if output_size == 0:
                    raise HTTPException(422, "Video processing produced no output")
                if output_size > MAX_VIDEO_OUTPUT:
                    raise HTTPException(413, "Video output exceeds 100 MB")
                with dst.open("rb") as output_stream:
                    video_bytes = output_stream.read(MAX_VIDEO_OUTPUT + 1)
                if not video_bytes:
                    raise HTTPException(422, "Video processing produced no output")
                if len(video_bytes) > MAX_VIDEO_OUTPUT:
                    raise HTTPException(413, "Video output exceeds 100 MB")
            except FileNotFoundError as exc:
                raise HTTPException(422, "Video processing produced no output") from exc
            except OSError as exc:
                raise HTTPException(503, "Enhanced video could not be read") from exc
            return Response(content=video_bytes,media_type="video/mp4",headers={"Content-Disposition":"attachment; filename=enhanced.mp4"})
    finally:
        PROCESSING_LOCK.release()
