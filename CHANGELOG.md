# Changelog

Versions follow Semantic Versioning: MAJOR.MINOR.PATCH. Until 1.0.0, APIs remain experimental.

## 0.3.0-dev.7 — Upload reader resilience
- Convert OSError when reading uploaded files into controlled HTTP 503 across API endpoints.
- Add regression tests for unreadable uploads and exact/oversized upload limit boundaries.
- **Verification:** three isolated upload-reader logic cases executed and passed; repository pytest and CI not yet verified.

## 0.3.0-dev.6 — Temporary video staging resilience
- Catch filesystem errors while staging the uploaded video, return HTTP 503 and always release the single-job processing lock.
- Add regression coverage for permission-denied staging, no FFmpeg subprocess launch, and lock recovery.
- **Verification:** new test committed, not yet executed; CI and target-hardware validation remain pending.

## 0.3.0-dev.5 — Video failure recovery regression coverage
- Add regression checks that the single-job processing lock is released when FFmpeg fails to launch, and that missing output after FFmpeg returns success produces HTTP 422.
- **Verification:** new tests are committed but have not been executed in this session; CI status remains unconfirmed. Not a release candidate.

## 0.3.0-dev.4 — Encoded video read resilience
- Convert missing output files to HTTP 422 and unreadable encoded video output to HTTP 503, without exposing a server traceback.
- Add a regression test simulating permission-denied output reads after successful FFmpeg execution.
- **Verification:** committed but new test and CI remain unverified; not a release candidate.

## 0.3.0-dev.3 — Video input and output boundary coverage
- Reject empty video uploads with HTTP 400 before acquiring the processing lock or launching FFmpeg.
- Add three regression tests for empty uploads, oversized enhanced MP4 responses and output exactly at the configured size limit.
- **Verification:** changes committed; CI and newly added tests not yet confirmed passing. Not a release candidate.

## 0.3.0-dev.2 — ONNX and FFmpeg regression hardening
- Validate ONNX model readiness and invalid model configuration rather than reporting any configured path as ready.
- Handle ffprobe/ffmpeg executable launch errors as HTTP 503 and missing encoded video as HTTP 422.
- Add five targeted regression tests for ONNX readiness, invalid ONNX configuration, and FFmpeg failure cases.
- **Verification:** new changes are committed but have not yet been rerun; 102-pass evidence applies to 0.3.0-dev.1 only. Not a release candidate.

## 0.3.0-dev.1 — Reliability and real-model validation
- Run blocking API work in the worker pool; status remains responsive and concurrent jobs receive HTTP 429.
- Hold processing admission through image encoding, analysis, and complete video processing.
- Return HTTP 413 for Pillow decompression bombs.
- Restrict Lite video to validated durations up to 60 seconds, pad odd dimensions for H.264, bound buffered output to 100 MiB, map the inspected video stream explicitly, and limit decoder/encoder threads.
- Respect EXIF orientation in ONNX, reject incompatible static-spatial/float models and non-finite output, and map runtime failures to controlled errors.
- Cache at most one ONNX session to reduce retained model memory.
- Add explicit checksum-verified downloads of pinned FSRCNN/ESPCN test weights, real-model API/portrait tests, real ONNX runtime plumbing tests, and real FFmpeg coverage.
- Add Python 3.10/3.12 CI matrix with separate classic and pretrained-model environments.
- Benchmark models in isolated processes with cold/warm timings, independent RSS, provenance, and environment metadata.
- Add reproducible portrait reconstruction evaluation and checked-in measurements under `benchmarks/`.
- **Verification:** local Python 3.12 tests and real FSRCNN/ESPCN inference executed; see `benchmarks/VALIDATION.md` for exact evidence and limitations.
- **Not a release candidate yet:** physical 4 GB target-laptop validation and representative user-portrait A/B review remain open; pretrained ONNX enhancement is not validated by the generated graph test.

## 0.2.3 — Development build
- Add optional real-model FSRCNN/ESPCN inference checks when weights are configured.
- Add CPU benchmark script reporting model runtime, dimensions, output path, and process peak RSS.
- Add frontend JavaScript syntax validation to CI.
- Improve invalid-video, oversized-video, and ffprobe timeout handling.
- **Verification:** GitHub workflow status and real ESPCN model inference are not yet confirmed.

## 0.2.2 — Development build
- Return HTTP 413 before invoking FSRCNN or ESPCN for images above the neural Lite input cap.
- Validate neural input before taking the CPU processing lock.
- Add regression tests for oversized inputs, invalid image data, and invalid FSRCNN configuration.
- **Verification:** CI and end-to-end pretrained ESPCN inference remain unconfirmed.

## 0.2.1 — Development build
- Prevent invalid FSRCNN model paths from crashing `/api/status`.
- Add deterministic smoke tests for status, classic upscaling, neural endpoint routing, invalid inputs, and mocked ESPCN output.
- Add GitHub Actions CPU smoke-test workflow.
- **Verification:** tests are committed, but CI results and physical-device end-to-end validation have not yet been confirmed. Not a release candidate.

## 0.2.0 — Development build
- Add optional ESPCN 2x neural engine with independent model path and Lite input cap.
- Add ESPCN readiness and frontend selection.
- Preserve FSRCNN, Portrait v2/v3, classic CPU, and ONNX modes.
- Centralize API version reporting.

## Earlier experimental milestones (unversioned)
- FSRCNN x2 CPU integration and real model inference.
- Portrait v2 and v3 adjustable restoration.
- Conventional CPU image/video processing and comparison script.

## Release-candidate gates
- Automated test workflow passes on supported Python versions.
- Real pretrained ESPCN model loads and successfully processes a sample image.
- All exposed modes are tested through the browser/API, including invalid inputs and Lite limits.
- CPU and memory usage verified on target low-memory laptop.
- Visual A/B evaluation checks facial fidelity and avoids claiming ground-truth detail recovery.
