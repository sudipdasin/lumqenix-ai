"""Compare a source portrait with an upscaled result at matched dimensions.

Requires numpy and opencv-python. This is a diagnostic, not a ground-truth
perceptual-quality benchmark. Sharpness increases can reflect noise or halos.
Usage: python scripts/compare_images.py original.jpg enhanced.png
"""
import argparse
import json
from pathlib import Path
import cv2
import numpy as np

def analyze(source, result):
    original = cv2.imread(str(source), cv2.IMREAD_COLOR)
    enhanced = cv2.imread(str(result), cv2.IMREAD_COLOR)
    if original is None or enhanced is None:
        raise ValueError("Could not read one or both images")
    h,w = original.shape[:2]
    hh,ww = enhanced.shape[:2]
    matched = cv2.resize(enhanced,(w,h),interpolation=cv2.INTER_AREA)
    gray1=cv2.cvtColor(original,cv2.COLOR_BGR2GRAY)
    gray2=cv2.cvtColor(matched,cv2.COLOR_BGR2GRAY)
    sharp1=float(cv2.Laplacian(gray1,cv2.CV_64F).var())
    sharp2=float(cv2.Laplacian(gray2,cv2.CV_64F).var())
    diff=original.astype(np.float32)-matched.astype(np.float32)
    mae=float(np.mean(np.abs(diff)))
    mse=float(np.mean(diff*diff))
    psnr=float(10*np.log10(255*255/mse)) if mse>0 else None
    return {
      "source_dimensions":[w,h], "result_dimensions":[ww,hh],
      "width_scale":round(ww/w,3),"height_scale":round(hh/h,3),
      "source_bytes":source.stat().st_size,"result_bytes":result.stat().st_size,
      "matched_laplacian_variance_original":round(sharp1,3),
      "matched_laplacian_variance_enhanced":round(sharp2,3),
      "matched_sharpness_change_percent":round((sharp2/sharp1-1)*100,2) if sharp1 else None,
      "matched_rgb_mae_0_to_255":round(mae,3),
      "matched_psnr_db":round(psnr,3) if psnr is not None else None,
      "warning":"No high-resolution ground truth. Metrics cannot establish detail recovery, identity fidelity, or perceptual improvement."
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("source",type=Path)
    p.add_argument("result",type=Path)
    args=p.parse_args()
    print(json.dumps(analyze(args.source,args.result),indent=2))

if __name__=="__main__":
    main()
