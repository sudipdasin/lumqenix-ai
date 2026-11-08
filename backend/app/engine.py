"""Baseline CPU enhancement, deliberately not marketed as GAN/AI super-resolution."""
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

PRESETS = {"auto", "natural", "vivid", "restore", "cinematic", "portrait"}

def inspect(image: Image.Image) -> dict:
    rgb = np.asarray(image.convert("RGB"))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(gray.mean())
    return {"width": image.width, "height": image.height,
            "brightness": round(brightness, 1), "sharpness_score": round(sharpness, 1),
            "low_light": brightness < 85, "possibly_blurry": sharpness < 90}

def enhance(image: Image.Image, preset: str = "auto", scale: int = 2):
    if preset not in PRESETS: raise ValueError("Unknown preset")
    if scale not in (1, 2, 4): raise ValueError("Scale must be 1, 2, or 4")
    image = ImageOps.exif_transpose(image).convert("RGB")
    stats = inspect(image)
    if preset in ("auto", "restore"):
        image = ImageOps.autocontrast(image, cutoff=1)
    if preset == "auto":
        if stats["low_light"]: image = ImageEnhance.Brightness(image).enhance(1.18)
        image = ImageEnhance.Color(image).enhance(1.08)
        image = ImageEnhance.Sharpness(image).enhance(1.20)
    elif preset == "portrait":
        # Gentle portrait cleanup; avoid strong global sharpening and skin oversaturation.
        image = image.filter(ImageFilter.GaussianBlur(radius=0.25))
        image = ImageEnhance.Contrast(image).enhance(1.035)
        image = ImageEnhance.Color(image).enhance(1.02)
    elif preset == "natural": image = ImageEnhance.Sharpness(image).enhance(1.12)
    elif preset == "vivid":
        image = ImageEnhance.Color(image).enhance(1.35)
        image = ImageEnhance.Contrast(image).enhance(1.12)
    elif preset == "restore": image = image.filter(ImageFilter.MedianFilter(3))
    elif preset == "cinematic":
        image = ImageEnhance.Contrast(image).enhance(1.20)
        image = ImageEnhance.Color(image).enhance(1.12)
    if scale > 1:
        image = image.resize((image.width * scale, image.height * scale), Image.Resampling.LANCZOS)
    return image, stats
