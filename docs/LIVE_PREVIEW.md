# Lumqenix Community — bounded live preview

**Deployment:** Railway service from `development/rc6-live-preview-20261126` (later the verified integration branch). This is a public **experimental** preview, not a stable release, anonymous batch-hosting service, or full standalone Pro installation.

The service runs FastAPI and the existing Studio Lite frontend on the same origin. Public compute safety: a single processing job at a time, global request rate limit, 8 MiB media input, constrained output pixels, 2 OpenCV threads, and disabled remote video processing unless explicitly enabled after FFmpeg and capacity checks. Optional pretrained neural models are not included and their menu choices show unavailable when the corresponding model is missing. No uploaded media is intentionally saved outside the processing request; video temporary directories are cleaned up. Uploads are processed on the **remote server**, not on the user's machine. Do not upload sensitive or confidential media to public preview deployments.

Health endpoint: `GET /healthz`; API status: `GET /api/status`. Start command and build settings are in `railway.json`. **No GitHub Actions or CircleCI is necessary or authorized.**

This live service is a validation stage for CPU-baseline functionality. Real pretrained portrait quality, actual video work, 4 GB RAM certification and complete distro compatibility must be separately verified before stable release.
