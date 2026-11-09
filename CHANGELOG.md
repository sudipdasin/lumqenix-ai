# Changelog

Versions follow Semantic Versioning: MAJOR.MINOR.PATCH. Until 1.0.0, APIs remain experimental.

## 0.2.7 — Development build
- Replace base OpenCV headless dependency with OpenCV contrib headless so FSRCNN/ESPCN `dnn_superres` can actually be imported in a fresh install.
- Add dependency and classic output-limit regression checks.
- Ensure frontend backend-connection indicator handles non-2xx status responses.
- **Verification:** GitHub CI and real-model performance tests are still pending; not a release candidate.

## 0.2.6 — Development build
- Hold the global processing lock throughout video probing, encoding, and reading the completed output, preventing overlapping CPU-intensive jobs.
- Add concurrency and lock-release regression tests for video processing.
- **Verification:** tests committed; CI and real-device execution not yet confirmed. Not a release candidate.

## 0.2.5 — Development build
- Validate ONNX model path and scale in API readiness instead of assuming an environment variable means a usable model.
- Return HTTP 503 for invalid ONNX configuration, avoiding an internal-server error.
- Add regression tests for missing/invalid model paths and invalid scale.
- **Verification:** tests committed but execution and target-device testing remain unconfirmed; not a release candidate.

## 0.2.4 — Development build
- Reject empty video uploads with a clear 400 response.
- Reject missing or empty transcoder output rather than returning an invalid MP4.
- Add regression tests for empty video, probe failure, probe timeout, and oversized video.
- **Verification:** test execution and real-device benchmarks remain outstanding; not a release candidate.

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
