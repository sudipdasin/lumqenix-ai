# Changelog

## v0.3.0-rc.5 — Linux installer and CI delivery candidate (2026-11-22)
- Build a SHA-256 verified, self-extracting Linux `.run` installer from the exact source ZIP and publish both as GitHub Releases assets only after same-commit CI gates pass.
- Install into versioned per-user directories, refuse overwrites, validate archive paths/symlinks/duplicates and enforce an expansion cap; optional XDG desktop-menu integration with safe removal.
- Add eleven offline installer security and lifecycle regressions, carry forward desktop integration regressions, and require Linux packaging smoke tests for the generated executable archive.
- Harden model-weight fetching: allowlisted HTTPS host, safe filenames, download size bounds, verified atomic replacement and regression tests.
- Preserve CPU-first/real-model quality and 4 GiB RSS gating from the successfully validated RC4 predecessor. **Not a fully standalone binary, physical low-memory certification, or stable v1 release.**
- Keep Community-only assets on the public channel; private Pro source and credentials remain excluded.


## v0.3.0-rc.4 — Experimental portrait consistency and evidence hardening (2026-11-21)
- Add opt-in FSRCNN Portrait Guard v4, selecting a bounded neural/bicubic blend by source-image reconstruction-cycle MSE. A bicubic candidate always participates, so the selected result cannot score worse on the defined LR-cycle metric than the local bicubic baseline; this does **not** imply higher-resolution fidelity or facial-identity improvement.
- Preserve default Portrait v2/v3 behavior and current CPU video workload protections; add explicit v4 UI selection and report the chosen neural contribution in an API response header.
- Add local and configured-real-model regression tests for guarded inference, plus reproducible pinned-weight CPU benchmark artifacts for v4 versus bicubic LR consistency.
- Strengthen release evidence against malformed, non-RGB, misdimensioned or truncated PNG artifacts, internal symlink aliases and excessively large claimed image data; stream SHA-256 in 1 MiB chunks instead of reading entire images into memory.
- Publish only after all four Python lanes, actual FFmpeg/video tests, frontend, security boundary/history checks, model/evidence and exact-commit Linux installer smoke pass; no production/stable or verified face-identity claims.


## v0.3.0-rc.3 — CPU video workload and release reliability candidate (2026-11-20)
- Restore previously validated FFprobe frame-rate, nominal-rate and declared-frame-count preflight on the RC2 video path, preserving its independent 60-second FFmpeg output clamp.
- Reject excessive video compute requests (1,800 estimated frames or 450 million estimated output samples) before encoding on constrained Community CPUs, including missing FPS, variable-frame-rate discrepancies and malformed values.
- Restore the stable Community edition API contract (`GET /api/edition`), with no dependency on private Pro assets.
- Add endpoint-level regression tests proving CPU-budget rejection happens before FFmpeg runs and the processing lock is released.
- Decouple four Python CI lanes from repeated FFmpeg system-package installations; keep real H.264 processing in a mandatory dedicated job. Require exact-commit Linux install/package, history, neural and quality evidence gates before experimental prerelease publication.
- Release is conditional on passing the exact commit's CI; representative portrait identity quality, dependency/legal audit, and a physical 4 GB RAM machine remain outstanding. This is not a stable final release.


## v0.3.0-rc.2 — Beta preview candidate (2026-11-19)
- Introduce a separate RC2 preview branch without overwriting RC1.
- Harden multi-scene release-evidence parsing against malformed report structures and add six regression cases.
- Update beta source ZIP artifact name, version metadata, and installation references.
- Release qualification remains pending: real-model, Linux CI, and 4 GiB RAM benchmarks must be executed and verified; no stable release is claimed.


## v0.3.0-rc.1 — Beta preview (2026-11-18)
- Experimental preview branch `preview/v0.3.0-rc.1-beta` created from the reliability development branch; backend version set to `0.3.0-rc.1`.
- Includes CPU-first image/video enhancement, optional pretrained FSRCNN/ESPCN inference, ONNX tiling, reproducible quality comparisons, and CI release-evidence validation.
- **Not production certified:** the available GitHub status reported CircleCI `error` for recent development commits, and the complete release gates have not been independently confirmed passing. Model quality superiority, face fidelity, and 4 GiB performance are not certified.
- Preview publication does not merge into `main` or certify a stable release. Run only in a trusted local testing environment.


## Unreleased — Reject stale pretrained benchmark output (2026-11-17)
- Remove prior model output before launching each worker, preventing a previous PNG from being accepted as fresh evidence.
- Report output cleanup errors per model and continue independent model evaluation.
- Add regression coverage for a worker reporting success without producing a new image.
- **Verification pending:** seven-lane CI and real-model benchmarks must pass before release promotion.

## Unreleased — Isolate pretrained worker launch errors (2026-11-17)
- Record Python worker process launch errors as per-model failures, allowing the other model to be attempted.
- Add a regression test simulating missing worker executable for both FSRCNN and ESPCN.
- **Verification pending:** commits require the seven-lane CI matrix; no model-quality or 4 GiB RAM performance claims.

## Unreleased — Repair pretrained benchmark syntax (2026-11-17)
- Replace accidentally serialized literal `\n` tokens in the model worker validation call with real Python newlines.
- Diagnosed from seven-lane CI run 44016485419: five jobs failed because Python could not compile `backend/scripts/benchmark_models.py`; frontend and CPU API benchmark succeeded.
- **Verification:** source fix committed; fresh CI verification pending. No version promotion.

## Unreleased — Validate pretrained benchmark evidence (2026-11-17)
- Verify each isolated model worker reports the expected model, 2x dimensions, exact warm-run count, positive finite timings, and a decodable RGB PNG at the declared output path.
- Convert inconsistent worker success reports into explicit failed benchmark records instead of accepting incomplete evidence.
- Add ten focused regression cases for valid, malformed, corrupt, and inconsistent evidence.
- **Verification:** source and tests committed; new seven-lane CI pending. Previous head 54e5209 passed CI. No version promotion.

## Unreleased — Stream real-reference provenance hashing (2026-11-17)
- Replace whole-file `read_bytes()` SHA-256 hashing of operator-supplied photographs with 1 MiB streaming chunks, preventing a second file-sized allocation during paired-quality benchmarking.
- Add regression checks for multi-megabyte inputs and empty files; forbid whole-file reads in the test.
- **Verification:** code and tests committed; fresh seven-lane CI pending. This is a benchmark memory-safety improvement, not evidence of better enhancement quality. No version promotion.

## Unreleased — Operator-supplied real-image reconstruction benchmark (2026-11-17)
- Add optional `--reference-image` to the pretrained FSRCNN/ESPCN paired-quality benchmark. EXIF-correct and center-crop a supplied image to 256x256, downsample to 128x128, then evaluate both models against the real reference and bicubic baseline.
- Record SHA-256 of the original reference bytes and distinguish operator-reference from synthetic-texture datasets. Preserve the original synthetic CI benchmark by default.
- Add regression tests for reference dimensions, provenance, missing minimum resolution, and synthetic fallback.
- **Verification:** changes committed; fresh CI and genuine pretrained-image results pending. These reconstruction metrics do not establish portrait identity preservation or perceptual quality. No version promotion.

## Unreleased — Paired model/bicubic divergence metrics (2026-11-17)
- Add prediction-versus-bicubic MAE/MSE/PSNR and model PSNR improvement relative to bicubic to real pretrained quality reports, exposing no-op outputs and regressions without claiming portrait fidelity.
- Add regression coverage for nonidentical outputs and lossless-reference PSNR edge cases.
- **Verification:** source and tests committed; new seven-lane CI outcome pending. No version promotion.

## Unreleased — Verify pretrained visual evidence integrity (2026-11-17)
- Validate all five paired comparison PNG files exist, decode, have expected RGB dimensions, and contain nonempty data before uploading the quality artifact.
- Record each image's SHA256, byte length, and dimensions in a machine-readable manifest alongside the quality report; keep the existing seven CI jobs.
- **Verification:** CI change committed; new workflow outcome and manifest artifact not yet confirmed. The preceding commit `947f7d6` passed all seven jobs and uploaded the pretrained quality artifact. No version promotion or claim of improved portrait fidelity.

## Unreleased — Preserve visual pretrained-model evidence (2026-11-17)
- Extend the existing seven-lane CI quality artifact to include the paired high-resolution reference, low-resolution input, bicubic baseline, and actual FSRCNN/ESPCN output PNGs alongside the metrics JSON.
- This enables direct visual inspection of enhancement artifacts and repeatable side-by-side comparisons without claiming that synthetic texture fidelity measures portrait identity.
- **Verification:** artifact upload change committed; fresh CI artifact availability and image contents pending verification. Version unchanged.

## Unreleased — Repair quality benchmark imports (2026-11-17)
- Fix pytest collection of `scripts.benchmark_quality_models` by using package-relative imports when imported as a module while retaining direct CLI script execution imports.
- Root cause: GitHub Actions run 43968060998 failed in five test/video jobs with `ModuleNotFoundError: No module named 'benchmark_models'`; the frontend and CPU image benchmark lanes succeeded.
- **Verification:** GitHub Actions failure logs inspected; fix committed, new CI execution pending. No version promotion.

## Unreleased — Real pretrained CPU benchmark CI evidence (2026-11-17)
- Extend the existing Python 3.12 neural CI matrix job (without adding an eighth job) to run both downloaded pretrained FSRCNN and ESPCN weights on deterministic 128×128 textured input in separate CPU processes.
- Validate model SHA256 presence, exact 2× output dimensions, two positive warm timings, and measured process peak RSS below 4 GiB; upload a machine-readable JSON artifact even when validation fails.
- **Verification:** the preceding seven-job workflow at commit `99d0b33` completed successfully (GitHub Actions run 43949177956). The new benchmark change is committed but its execution and performance values are pending. GitHub-hosted CPU measurements do not certify a 4 GB Intel laptop or portrait fidelity.

## Unreleased — Restore real-video CI prerequisites (2026-11-17)
- GitHub Actions run 43943712224 failed in four test-matrix jobs and the FFmpeg integration job at the H.264 encoder prerequisite, while frontend and CPU benchmark jobs passed.
- Explicitly install `ffmpeg` and `libavcodec-extra` before prerequisite checks in those five jobs; print the encoder list for diagnostics if the host image still lacks `libx264`.
- **Verification:** workflow change committed; subsequent CI result pending. No version promotion or claim of passing real-video tests.

Versions follow Semantic Versioning: MAJOR.MINOR.PATCH. Until 1.0.0, APIs remain experimental.

## Unreleased — Turbo multi-scene release evidence gate (2026-11-18)
- Close a release-validation gap: all three real-model quality JSON artifacts (textures, edges, smooth) are now uploaded and required by the cross-job release gate. Previously only the texture report was checked, so missing edge/gradient evidence could go unnoticed.
- Add `validate_scene_bundle` to verify all six model-scene combinations, expected dimensions, consistent model hashes, finite reconstruction metrics and scene-specific bicubic baselines. Add eight regression cases including missing-scene and tampered-evidence rejection.
- **Verification status:** changes committed; GitHub Actions results not yet confirmed. This checks measurement integrity, not perceptual superiority or face identity.

## Unreleased — Strict multi-scene memory evidence gate (2026-11-18)
- Make all three synthetic reconstruction scenes mandatory in the release-evidence CLI, eliminating the optional single-scene bypass.
- Validate every individual pretrained model execution for correct model identity, LR/HR dimensions, finite warm timings, and peak RSS below 4 GiB across all six scene/model combinations. Add five negative regression cases.
- GitHub combined commit status currently reports a CircleCI Pipeline `error` context; no GitHub Actions workflow runs were returned by the available commit-run lookup. This is not a passing release signal and requires CI investigation.
- **Validation:** changes committed; full suite and real-model runs not independently verified. No release promotion.

## Unreleased — Turbo evidence comparison report (2026-11-18)
- Extend release-evidence validation with an explicit six-row model-by-scene comparison of pretrained FSRCNN/ESPCN reconstruction versus bicubic, including signed MAE improvements and PSNR deltas. Negative results remain visible and are not disguised as successes.
- Require low-resolution reference dimensions in the primary evidence gate; add three regression tests for six-way summary, negative improvement, and missing dimensions.
- Persist the combined release evidence JSON as a dedicated CI artifact; make artifact discovery use the GitHub Actions glob matching the benchmark artifact names.
- **Validation status:** code committed; actual full GitHub Actions execution and model comparison numbers remain unverified. No release promotion.

## Unreleased — Multi-scene pretrained quality evaluation (2026-11-17)
- Extend deterministic paired-reference quality evaluation from one texture scene to three independent scenes: textures, hard edges, and smooth gradients. All use genuine pretrained FSRCNN and ESPCN inference in the Python 3.12 neural CI lane.
- Upload separate machine-readable quality reports for each scene. Add two tests for deterministic scene differences and rejection of unsupported scene identifiers.
- Fix quality benchmark import handling so direct script execution and pytest imports both work.
- **Verification:** code and CI wiring committed; end-to-end CI and model measurements still require confirmation. Synthetic scenes do not establish natural-photo or face fidelity.

## Unreleased — Cross-job release evidence gate (2026-11-17)
- Add a dedicated eighth GitHub Actions job to download and cross-check actual pretrained CPU performance, paired-reference quality, and image API benchmark artifacts.
- Fail closed on missing or inconsistent evidence, model SHA-256 mismatches, invalid quality numbers, and process RSS at or above 4 GiB. Add eight pass/failure regression cases.
- Fix quality benchmark imports for both direct execution and pytest module imports.
- **Verification:** committed, but GitHub Actions execution and end-to-end artifact gate results have not yet been observed. This gate validates evidence completeness; it does not certify perceptual superiority or facial fidelity.

## Unreleased — Real-model reconstruction quality integration (2026-11-17)
- Add `backend/scripts/benchmark_quality_models.py`: generate deterministic HR texture reference, bicubic-downsample to LR, run actual pretrained FSRCNN and ESPCN in isolated CPU processes, and compare reconstructed HR against bicubic using RGB PSNR, MAE and MSE.
- Integrate the real-model quality report into the existing Python 3.12 neural CI lane with JSON validation and an uploadable artifact. Add two dataset/report contract tests.
- **Verification:** implementation and CI configuration committed; no executed CI report or quantitative improvement claim yet. The synthetic dataset is not a facial-fidelity or perceptual benchmark and does not require models to beat bicubic.

## Unreleased — Paired-image objective quality evaluation (2026-11-17)
- Introduce `backend/scripts/evaluate_quality.py` for reproducible full-reference RGB MSE, MAE and PSNR measurement, optional bicubic-baseline comparison, and JSON output. Lossless comparisons use a null PSNR rather than invalid JSON infinity.
- Add four numerical regression tests: identical images, known PSNR, dimension mismatch, and baseline improvement arithmetic.
- This is an evaluation foundation, **not** evidence of perceptual enhancement or facial identity preservation. Model-generated paired-image benchmarks and complete CI results remain pending.

## Unreleased — ONNX core-only halo conversion (2026-11-17)
- Optimize tiled ONNX super-resolution to convert only each tile's central output region from float32 NCHW to uint8 RGB. Halo pixels remain inference context and are no longer converted unnecessarily.
- Add three exact-pixel reference regressions for the optimized path, including irregular dimensions and overlap variants.
- Four isolated numerical equivalence checks passed locally; full repository CI, real-model image quality and end-to-end memory benchmarks remain pending.

## Unreleased — Neural tile-seam contract regression suite (2026-11-17)
- Add six ONNX tiled-inference regression cases covering non-divisible dimensions, zero/positive halo, maximum permitted overlap, tile counts, exact nearest-neighbor reconstruction, malformed tensor shapes and non-finite output.
- These deterministic fake-session tests validate halo stitching independently of model downloads. They do **not** establish real-model image quality or performance; those require separate pretrained-model runs.
- **Verification:** test source committed to development branch; GitHub CI results pending.

## Unreleased — Benchmark output-format validation (2026-11-17)
- Validate that the CPU image API benchmark returns a genuine PNG image rather than merely decodable output with expected dimensions.
- Add the output format to the machine-readable benchmark JSON and require PNG in the CI acceptance gate.
- **Verification:** changes committed; current CI run not verified. No version promotion.

## Unreleased — CPU benchmark acceptance gate (2026-11-17)
- Validate JSON benchmark shape, output dimensions, successful PNG encoding, finite positive latency measurements, and consistent latency ordering in the CPU benchmark CI job.
- Fail the benchmark job if measured peak process RSS reaches 4 GiB. This is a smoke budget on GitHub-hosted Linux, not proof of 4 GB laptop compatibility or a real-model quality threshold.
- **Verification:** checks committed; new CI outcome pending.

## Unreleased — Automated CPU benchmark CI lane (2026-11-17)
- Add a seventh independent GitHub Actions job that installs the backend, executes the deterministic image API CPU benchmark, prints JSON metrics and uploads the JSON artifact.
- The benchmark is deliberately independent of Python compatibility, neural inference, frontend checks and real-video integration jobs, enabling concurrent execution.
- **Verification:** workflow committed, execution and measurements pending; do not interpret GitHub-hosted runner measurements as results on a 4 GB Intel laptop.

## Unreleased — Reproducible CPU endpoint benchmarking (2026-11-17)
- Add `backend/scripts/benchmark_api_cpu.py` to exercise the actual classic image-enhancement HTTP endpoint with generated deterministic input, validate output dimensions, and report warm latency plus process peak RSS in JSON.
- Run with `cd backend && python scripts/benchmark_api_cpu.py --runs 3`; results reflect the execution host, not the target Intel laptop.
- **Verification:** benchmark script committed; no execution result is claimed for this commit. Real pretrained-model and facial-fidelity benchmarks remain separate outstanding work.

## Unreleased — Accurate video readiness status (2026-11-16)
- Report video processing availability only when both FFmpeg and FFprobe are present, matching the video endpoint's requirements.
- Add positive and negative readiness regression tests.
- **Verification:** committed, new tests not yet executed; no version promotion.

## Unreleased — Parallel CI milestone acceleration (2026-11-16)
- Separate frontend JavaScript syntax checks from the four-job Python CPU/neural matrix so frontend validation runs concurrently.
- Add a dedicated real-FFmpeg integration lane that installs backend dependencies, verifies H.264 encoding tools, executes the full pytest suite, and retains JUnit output even on failures.
- Existing four Python 3.10/3.12 neural/classic matrix jobs remain; this workflow now defines six independently scheduled jobs.
- **Verification:** CI workflow committed; no successful run of the new six-job configuration has been established. This is an acceleration checkpoint, not a production release.

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
