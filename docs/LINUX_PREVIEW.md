# Lumqenix Community Linux source preview

The downloadable preview is a source archive for local evaluation. It is a
development prerelease, not a stable release, certified production build, or
standalone application. Installation creates a Python virtual environment and
downloads Python packages from the package index. Linux, Python 3.10 or newer,
and internet access are required. FFmpeg and ffprobe are optional and enable
video workflows.

## Verify and extract

Download the versioned source ZIP, `SHA256SUMS`, and `provenance.json` from the
same GitHub release. Check the published checksum before extracting:

```bash
sha256sum -c SHA256SUMS
```

The repository also includes a verifier that checks the supplied SHA-256,
archive paths and types, versioned root folder, exact manifest file set, and
every listed file size and SHA-256. Run it before extraction, substituting the
checksum copied from the release's `SHA256SUMS` file:

```bash
python3 scripts/build_preview.py --verify lumqenix-community-0.3.0-dev.8.zip \
  --sha256 PASTE_THE_64_CHARACTER_SHA256_HERE
```

Extract the verified ZIP and enter its `lumqenix-community-0.3.0-dev.8`
directory. Keep the archive, checksum and provenance file together for later
reference. The manifest records each source file's size and hash plus the exact
source commit and version. No Python packages, pretrained weights, or private
Pro code are bundled.

## Install, run, and remove

From the extracted source directory:

```bash
bash scripts/install-linux.sh
bash scripts/run-linux.sh
```

Open <http://127.0.0.1:8080>. The app binds the Studio and API to localhost.
Press Ctrl+C in the launcher terminal to stop both services. When finished,
remove the environment created by the installer:

```bash
bash scripts/uninstall-linux.sh
```

Uninstall removes only the marked `.venv` inside the source directory. It keeps
the source tree, any user-provided models, and other files. It does not remove
Python packages from the system. The installer and launcher do not require root
privileges. If installation is interrupted, rerun the installer; it refuses to
replace an unrelated `.venv`.

The classic engine is ready after install. Genuine FSRCNN/ESPCN enhancement
requires separately obtained compatible model weights; these are not included.
Read the model configuration notes in the main README before adding weights.

## Preview limits

This archive is intended for local, single-user evaluation. It is not evidence
of stable release quality or physical 4 GB laptop certification. Hosted runner
memory measurements do not certify total laptop memory. Windows, GPU use,
pretrained ONNX model compatibility, and public multi-user deployment are not
verified by this preview. Enhancement can change image detail and cannot
guarantee recovery of authentic missing detail.
