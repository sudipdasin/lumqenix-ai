# Project Continuity and Recovery — Lumqenix Community

## Verified baseline (2026-11-28)

- Public repository: `sudipdasin/lumqenix-ai`.
- `main`: `957a0e2f585a404a0ece141db8cdafb78988c2e5` (CI usage policy, 2026-11-25). Do **not** mistake this for the current beta work.
- Latest verified preview branch before this batch: `preview/v0.3.0-rc.6-beta` at `8d5c39d3f08f42cbfa3b8dae54bea5fec9b70865`.
- PR #40 integrated the previously Railway-tested image fidelity, public preview safety and Studio UX changes into that preview branch on 2026-11-26. The integration build reported 82 targeted Python tests passed, 1 skipped; it was not a complete product certification.
- The latest recorded successful Railway deployment was source `da52b022d2d67112d1d330835b299bae5687194d` (2026-11-26). Hosting state was reported SUCCESS by Railway metadata on 2026-11-28, but an independent live HTTP/browser recheck was not available in this session. **Do not claim this new batch is deployed.**

## Current development batch

- Isolated branch: `fix/rc6-preview-origin-syntax-20261128`, forked from the preview head above.
- Target: reject malformed and deceptive `Origin` headers with HTTP 403 rather than allowing URL parsing failures to cause HTTP 500 or permitting syntactically invalid origins.
- Files: `backend/app/preview_server.py`, `backend/tests/test_preview_security.py`, and this checkpoint.
- Local evidence: 13 isolated FastAPI/HTTPX Origin-guard reproduction cases passed on Python 3.13; an earlier five-case parser reproduction also passed. **These are not full-repository tests.** The environment could not clone GitHub, so the current branch's complete pytest suite, real-deployment regression, package build and physical low-RAM verification have not yet run.
- Note: the parser validates same-host `Origin` syntax, not trusted end-to-end HTTPS scheme. TLS may terminate at a reverse proxy; do not derive security conclusions from untrusted `X-Forwarded-Proto` without a validated trusted-proxy configuration.

## Operating and release gates

- **Never run, rerun, trigger or enable GitHub Actions or CircleCI** without explicit new owner approval. Do not increase cloud spending limits or start paid builds. Commits use `[skip ci]`, but that text alone is not the CI policy.
- Keep Community completely independent from private Pro code, credentials, dependencies, packages and model assets. The Pro `community.lock` may be behind current public `main`; update it only through isolated private review after verification, never through a public branch.
- Use small feature/fix branches, verify changes before merging to beta, and preserve `main` until explicit promotion approval and release gates pass. No final or stable release without owner instruction.
- Preserve Classic CPU image usability, source transparency, accurate capability disclosure, 4 GiB memory targets and the optional pretrained-model workflows. Do not claim that simple interpolation creates authentic lost detail, or that experimental portrait/ONNX modes certify fidelity.
- Public preview currently limits uploads and output size, uses a single-job lock, and disables video by default. Do not assume the local app and cloud preview have the same limits.
- Release artifacts require full reproducible local tests, source history/boundary review, package checks, compatible Linux VM/4 GiB evidence and user-visible image-quality comparisons.

## Restart checklist

1. Read the current `main`, `preview/v0.3.0-rc.6-beta`, and outstanding PR heads by exact SHA rather than relying on this historical snapshot.
2. Check the most recent Railway deployment commit and current live HTTP/browser evidence separately; do not deploy automatically.
3. Run `bash scripts/verify-local.sh tests` and `bash scripts/verify-local.sh package` from a clean complete checkout with already installed dependencies.
4. Verify `test_preview_security.py` against the real ASGI application under Python 3.10/3.12, including both malformed and valid same-origin cases.
5. Merge the isolated branch only after full tests and review; never merge to `main` as a shortcut. Record new SHA and test evidence at the next checkpoint.
6. Continue the priority roadmap: representative portrait and motion-quality A/B evidence, real-model comparisons, low-RAM/CPU benchmarks, verified Linux installation and appropriately gated Pro synchronization.
