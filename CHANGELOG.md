# Changelog

Versions follow Semantic Versioning: MAJOR.MINOR.PATCH. Until 1.0.0, APIs remain experimental.

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
