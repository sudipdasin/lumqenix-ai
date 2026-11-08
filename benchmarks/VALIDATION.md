# Validation — 0.3.0-dev.1

Executed 9 November 2026 (Asia/Kolkata). Source baseline: `b8ec056d28143bdeb1396f4e4d63f7b2595e4c2f`. Changes are a development build; no release candidate or final release is certified.

## Automated evidence

- Local Linux x86_64, Python 3.12.14: **102 passed** with OpenCV contrib, both actual pretrained models, ONNX Runtime, generated test graph, and FFmpeg.
- Separate classic-only Python 3.12 environment: **88 passed, 14 skipped**; skips explicitly cover missing neural/ONNX dependencies and weights.
- Generated ONNX graph tests exercise real CPU runtime, EXIF rotations, and tiled equality on non-divisible image dimensions. The graph uses nearest-neighbor Resize and has no learned weights; this is not evidence of pretrained ONNX enhancement quality.
- Real FSRCNN and ESPCN tests exercise API output versus direct model output, textured color input, Portrait v3 strengths 0/35/100, and strength-zero exact equivalence.
- Real multistream FFmpeg regression verifies encoding uses the inspected first video stream rather than a larger default stream; decoder and encoder threads are each limited to two.
- Real FFmpeg test processes an odd-size 33×25 video at 1× and probes the resulting 34×26 H.264 output.
- Concurrency test gates active inference and checks status plus immediate HTTP 429 from another job.
- Regression suite covers all classic presets/scales, invalid input, upload/pixel limits, decompression bombs, duration metadata, failed/timed-out video processes, and lock release after failures.
- Python compilation and frontend `node --check` executed successfully.
- One upstream Starlette/httpx deprecation warning was observed; tests still passed.
- Updated GitHub Actions matrix: Python 3.10 and 3.12, each classic and real-model environments. Final matrix result is recorded in the pull request; this document does not assume unobserved CI success.

## CPU measurements

See `cpu-portrait-512.json`, `cpu-texture-512.json`, and `environment-py312.txt`. Each model runs in a fresh process, one cold run and three warm runs, two OpenCV threads. Input 512×512; output 1024×1024. These are hosted CPU results, not the user's laptop.

| Model | Cold inference | Warm mean | Process peak RSS |
| --- | ---: | ---: | ---: |
| FSRCNN x2 | 0.302031 s | 0.198295 s | 406.64 MiB |
| ESPCN x2 | 0.228245 s | 0.145142 s | 310.05 MiB |

Timing excludes output PNG encoding. RSS includes imports, model loading, and output saving. CPU model/governor and background load were not controlled; three repeats establish a small reproducible sample, not a performance guarantee. The source image is scikit-image's NASA astronaut fixture, SHA256 `88431cd9653ccd539741b555fb0a46b61558b301d4110412b5bc28b5e3ea6cb5`, available at:
https://raw.githubusercontent.com/scikit-image/scikit-image/v0.25.2/skimage/data/astronaut.png

`memory-2gib.json` records FSRCNN, ESPCN at maximum neural pixel area and a classic 2000×1500→4000×3000 (12M output pixels) run sequentially with both neural caches retained. All completed under Linux RLIMIT_AS of 2 GiB, with OPENBLAS_NUM_THREADS=1 and OMP_NUM_THREADS=2; cumulative process peak RSS was 564.87 MiB. This limits virtual address space, not total system memory, and excludes the browser, HTTP buffers, OS, and FFmpeg. It does not certify physical 4 GB compatibility.

## Portrait reconstruction

`fidelity-astronaut.json` records a 512×512 reference downsampled to 256×256 using Lanczos, then reconstructed to 512×512. Reproduce with `scripts/evaluate_fidelity.py` and the source image above. Model weights are pinned by commit and SHA256 in `backend/models/pretrained.json`.

| Engine | PSNR (higher is better) | RGB MAE (lower is better) |
| --- | ---: | ---: |
| Lanczos | 31.0302 dB | 3.4972 |
| FSRCNN | 31.5632 dB | 3.4441 |
| ESPCN | 31.5511 dB | 3.4750 |
| Portrait v2 | 31.4145 dB | 3.6975 |
| Portrait v3, strength 35 | 31.4644 dB | 3.6256 |
| Portrait v3, strength 100 | 31.4085 dB | 3.6964 |

The generated comparison grid was visually inspected at matched dimensions. All outputs lose fine hair/skin detail relative to the reference; no observed gross face deformation on this single fixture. Portrait filtering softens texture and is not a demonstrated improvement over baseline FSRCNN. Keep filters optional; defaults were not increased. Strength zero exactly equals baseline FSRCNN.

One synthetic degradation of one portrait is insufficient to establish identity preservation, quality on damaged photos, broad demographic performance, or user preference. No model or face-reconstruction quality is claimed from mocked tests.

## Open release gates and risks

1. Physical target laptop with 4 GB RAM: measure browser + server + OS + FFmpeg, worst accepted inputs, swaps and sustained load.
2. Representative consented user portraits: inspect identity, skin, eyes, teeth, hair, halos, color, and ringing at matched sizes.
3. Pretrained compatible ONNX evaluation, Windows and optional GPU execution remain unverified. ONNX remains experimental.
4. Local single-user deployment only; per-process admission does not limit upload parsing or cross-worker memory. Arbitrary neural models may exceed memory despite tile limits.
5. Video duration/output limits are safeguards, not hard disk/CPU isolation; output disk usage is checked after encoding. Untrusted inputs and public traffic need resource isolation and ingress limits.

These gates prevent describing this build as production-ready. No final release or release tag was created.
