import io
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError
from .engine import enhance, inspect, PRESETS

app = FastAPI(title="Lumqenix API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"], allow_methods=["*"], allow_headers=["*"])
MAX_UPLOAD = 50 * 1024 * 1024
MAX_PIXELS = 32_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS

@app.get("/api/status")
def status():
    return {"status":"ok", "hardware":"cpu", "ai_model_loaded":False,
            "ffmpeg_available":bool(shutil.which("ffmpeg")), "presets":sorted(PRESETS)}

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
            if image.width * image.height * scale * scale > MAX_PIXELS: raise HTTPException(413, "Output too large")
            result, _ = enhance(image, preset, scale)
        output = io.BytesIO()
        result.save(output, format="PNG", optimize=True)
        return Response(content=output.getvalue(), media_type="image/png", headers={"Content-Disposition":"attachment; filename=enhanced.png"})
    except (UnidentifiedImageError, OSError, ValueError): raise HTTPException(400, "Unsupported or invalid image")

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
            if width * height * scale * scale > MAX_PIXELS: raise ValueError()
        except ValueError: raise HTTPException(400,"Invalid video or oversized output")
        filters = {"auto":"eq=contrast=1.05:saturation=1.08,unsharp=3:3:0.4", "natural":"unsharp=3:3:0.3", "vivid":"eq=contrast=1.1:saturation=1.3", "restore":"hqdn3d=2:1.5:3:2,unsharp=3:3:0.3", "cinematic":"eq=contrast=1.16:saturation=1.1"}
        vf = filters[preset] + f",scale=iw*{scale}:ih*{scale}:flags=lanczos,format=yuv420p"
        try:
            subprocess.run(["ffmpeg","-nostdin","-v","error","-y","-i",str(src),"-vf",vf,"-c:v","libx264","-preset","veryfast","-crf","19","-c:a","aac","-movflags","+faststart",str(dst)],check=True,timeout=180,capture_output=True)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired): raise HTTPException(422,"Video processing failed or timed out")
        return Response(content=dst.read_bytes(),media_type="video/mp4",headers={"Content-Disposition":"attachment; filename=enhanced.mp4"})
