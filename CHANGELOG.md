# Changelog

Versions follow Semantic Versioning: MAJOR.MINOR.PATCH. Until 1.0.0, APIs remain experimental.

## Unreleased — Local FFmpeg command smoke validation (2026-11-16)
- Executed FFmpeg locally against a generated 64×48, 1-second H.264 test clip using the application's auto filter chain and 2× scaling.
- FFprobe confirmed a 128×96 encoded MP4 output (5,258 bytes). This validates the encoder/filter command on the test host, **not** the FastAPI endpoint or the full repository test suite.
- The real-video CI prerequisite gate remains committed; its latest matrix result is not verified in this session.

## Unreleased — Enforce real-video CI prerequisites (2026-11-16)
- Require FFmpeg, FFprobe, and the libx264 encoder in every CPU CI matrix job so generated-video integration tests cannot silently skip due to missing tools.
- **Verification:** workflow committed; new CI execution not yet confirmed.

## Unreleased — Real FFmpeg integration coverage (2026-11-16)
- Add an end-to-end generated-video test that runs actual FFmpeg and FFprobe, exercises the HTTP enhancement endpoint, and checks the encoded MP4 output dimensions.
- Skip only if FFmpeg/FFprobe or libx264 are unavailable; no pretrained-model or portrait-quality claim is implied by this test.
- **Verification:** committed; CI execution of this new test is pending. The preceding commit c1a949a passed all four CPU CI jobs (Python 3.10/3.12, with/without neural dependencies); the Python 3.12 neural job reported 125 passed, 2 skipped, 1 warning.

## Unreleased — Temporary-directory creation failure
- Convert video temporary-directory creation OSError into HTTP 503 rather than an uncaught server exception.
- Add a regression test asserting lock release and no subprocess launch on temporary-directory creation failure.
- **Verification:** committed, full repository test suite not run in this session.

## Unreleased — Repair bounded-reader regression coverage (2026-11-15)
- Update the encoded-video permission-error regression to patch `Path.open('rb')`, matching the current bounded stream reader instead of the obsolete `Path.read_bytes()` path.
- This fixes a test that would otherwise exercise the successful read path and fail its HTTP 503 assertion.
- **Verification:** static source inspection confirms the mismatch and replacement; pytest and real-model benchmarks were not executed in this run. No version promotion.

## Unreleased — Bounded enhanced-video reads (2026-11-14)
- Replace unrestricted `Path.read_bytes()` with a bounded binary read of at most `MAX_VIDEO_OUTPUT + 1` bytes, limiting transient allocation when an MP4 grows after the initial size check.
- Preserve HTTP 413 for oversized outputs and HTTP 422 for empty outputs; adapt the existing growth/empty-read regression tests and add an explicit bounded-read-size test.
- **Verification:** source and test changes committed; full pytest and CI not verified. GitHub combined statuses and PR-triggered workflow query returned no records for the new commit; this does not rule out push-triggered workflows. Version remains `0.3.0-dev.7`.

## Unreleased — Malformed upload stream resilience (2026-11-13)
- Reject upload stream reads returning non-bytes (including `None`, text, or mutable byte arrays) with HTTP 503 instead of uncaught exceptions or invalid payloads.
- Add regression coverage for three malformed stream return types.
- **Verification:** five isolated upload-reader cases executed successfully in a standalone Python harness; repository pytest and CI not confirmed. Version remains 0.3.0-dev.7.

## Unreleased — FFprobe failure regression coverage
- Add tests for non-finite video duration and nonzero ffprobe exit status; both must reject the upload before encoding.
- **Verification:** tests committed but not executed in this run; no version milestone advancement.

## Unreleased — Closed upload stream handling
- Convert closed upload stream read failures (`ValueError`) to HTTP 503.
- Add regression coverage for closed in-memory upload streams.
- **Verification:** test added but not executed; no version advancement.

## Unreleased — Video inspection regression coverage
- Add three tests for ffprobe timeouts, malformed metadata, and videos exceeding the 60-second Lite duration limit.
- Assert inspection failures release the processing lock and do not invoke FFmpeg encoding.
- **Verification:** tests committed, not executed in this session; development version remains 0.3.0-dev.7.

## Unreleased — Dependency verification
- Run `python -m pip check` in each GitHub Actions CPU smoke matrix job after installing dependencies, so incompatible installed distributions fail before the test suite.
- GitHub commit status and pull-request workflow-run queries returned no checks for the prior development head; those queries do not establish that push-triggered CI has or has not run.
- **Verification:** workflow change committed; execution of the updated CI matrix is not confirmed.

## Unreleased — MP4 output race safeguards
- Reject enhanced video that becomes empty after the initial filesystem size check; add a regression test for empty post-stat reads.
- Three isolated MP4 size/empty-output logic checks passed locally; full repository pytest and the new regression tests remain unverified.

## Unreleased — MP4 output size race safeguard
- Recheck enhanced MP4 byte length after reading, preventing a file that grows between stat and read from bypassing the response-size limit.
- Add regression test simulating a small stat size but oversized read result.
- **Verification:** new regression test not executed; version remains 0.3.0-dev.7 pending full-suite validation.

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
