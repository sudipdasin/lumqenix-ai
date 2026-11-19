# Lumqenix Community 0.3.0-dev.8 — Linux source preview

A downloadable, verified **development prerelease** for local Linux testing and feedback. This is not a stable release, certified RC, standalone binary or bundled-model distribution.

## What improves

- Portable, no-root installation into an isolated local environment; one command starts the localhost Studio and API.
- Supervised startup, occupied-port detection and shutdown cleanup; safe removal of only the installer's marked environment.
- Deterministic source archive, per-file manifest, source commit provenance and SHA256 checksums; downloaded archives can be verified before use.
- Integrates downloaded paired-image hash validation into the real-model release evidence gate while preserving Community edition contracts and conservative video workload budgets.
- Publication waits for Python 3.10/3.12 tests, actual pretrained FSRCNN/ESPCN runs, real FFmpeg tests, frontend checks, CPU measurements, source-boundary checks, and install/start/enhance/stop checks from the extracted archive.

## Download and run

Download the source ZIP, `SHA256SUMS` and `provenance.json` from this release. Check the SHA256 before extraction. Follow `docs/LINUX_PREVIEW.md` in the source for install, launch and uninstall commands. Python 3.10+, Linux, and internet access for dependency installation are required. FFmpeg/ffprobe are optional system prerequisites for video. No root privileges are needed for the app.

Pretrained weights and optional ONNX dependencies are not bundled. The classic engine works immediately after installation; configuring genuine FSRCNN/ESPCN weights is documented in README. Private Pro code and credentials are not distributed.

## Evidence and limits

The attached `release-evidence.json` contains objective reconstruction differences for textures, edges and smooth gradients against bicubic, plus real-model process timing/memory validation. Negative quality differences remain visible. Synthetic reconstruction is not a facial-fidelity certification. The workflow run linked in the release establishes the exact tested source commit and actual successful checks.

Physical 4 GB target-laptop validation, broader portrait A/B review, pretrained ONNX compatibility, Windows/GPU and public multi-user service deployment remain unverified. Hosted-runner memory figures do not certify total laptop memory. This preview is for local single-user evaluation; report OS, CPU/RAM, input/output dimensions, selected engine, timing, and artifacts without uploading sensitive photos publicly.
