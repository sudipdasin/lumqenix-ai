# Build Lumqenix Linux release files without hosted CI

**Owner restriction (2026-11-25):** Do not use GitHub Actions or CircleCI without explicit approval. This process runs entirely on your own Linux computer; it never dispatches either service.

From a complete Git checkout of the Community preview branch, with Python 3.10+, `dpkg-deb`, Git, Bash and existing local Python test dependencies:

```bash
python3 scripts/build_offline_release.py --output-dir dist
```

The command requires a clean *tracked* Git checkout. Before packaging, it executes `scripts/verify-local.sh all`, the Community edition-boundary check, and the complete reachable-history publication audit. If a prerequisite or test fails, **no release bundle is published**.

On success, `dist/` contains a Community source ZIP, a verified source-based Linux `.run` installer, a Debian `.deb` package, `local-release-evidence.json`, and `SHA256SUMS`. Verify it with:

```bash
cd dist
sha256sum -c SHA256SUMS
```

The script additionally checks actual .run extraction and .deb file structure/version. It refuses to overwrite an existing bundle; use a new output directory for a newer version.

**Limits:** The package is architecture-independent source/Python, not a fully offline compiled executable. The first launch still requires locally installed Python dependencies or network access to obtain them. Test coverage may skip optional pretrained neural models if prerequisites are unavailable. A successful local run is **not** evidence of superiority over bicubic, photographic identity preservation, performance on a physical 4 GB Linux machine, or distro-wide compatibility. These files are not uploaded to GitHub Releases automatically; direct publication requires a supported uploader and sufficient verification evidence.

Private Pro modules and secrets must not be included in public Community packages.
