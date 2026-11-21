#!/usr/bin/env python3
"""Create a hash-checked, self-extracting Linux Community installer (.run).

A .run installer still requires Python 3.10+, and pip/network access unless the
application environment is already provided. It is NOT a compiled standalone app.
"""
import argparse
import hashlib
import io
import os
from pathlib import Path, PurePosixPath
import re
import stat
import zipfile

REQUIRED = frozenset({
    'LICENSE', 'backend/app/version.py', 'frontend/index.html',
    'scripts/install-linux.sh', 'scripts/run-linux.sh',
    'scripts/install-desktop.sh', 'scripts/uninstall-desktop.sh',
})
MAX_EXTRACTED_BYTES = 64 * 1024 * 1024
MARKER = b'\n__LUMQENIX_EMBEDDED_ZIP_PAYLOAD__\n'

# Bash only reads the Python here-doc up to PYCODE; 'exit' prevents executing
# the binary bytes that follow the marker.
STUB = r'''#!/usr/bin/env bash
set -Eeuo pipefail
command -v python3 >/dev/null || { echo 'Python 3.10+ is required' >&2; exit 1; }
python3 - "$0" "$@" <<'PYCODE'
import argparse
import hashlib
import io
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile

EXPECTED_SHA = '__SHA256__'
VERSION = '__VERSION__'
MARKER = b'\n__LUMQENIX_EMBEDDED_ZIP_PAYLOAD__\n'
REQUIRED = {'LICENSE', 'backend/app/version.py', 'frontend/index.html', 'scripts/install-linux.sh', 'scripts/run-linux.sh', 'scripts/install-desktop.sh', 'scripts/uninstall-desktop.sh'}


def safe_members(zfile):
    names = set()
    size = 0
    for item in zfile.infolist():
        parts = PurePosixPath(item.filename).parts
        if not parts or item.filename.startswith('/') or '..' in parts or '\\' in item.filename or item.filename.startswith('~'):
            raise ValueError('Unsafe archive member')
        if item.filename in names:
            raise ValueError('Duplicate archive member')
        names.add(item.filename)
        mode = item.external_attr >> 16
        if stat.S_ISLNK(mode):
            raise ValueError('Symlink in source archive')
        size += item.file_size
        if size > 64 * 1024 * 1024:
            raise ValueError('Excessive archive expansion')
    if not REQUIRED.issubset(names):
        raise ValueError('Missing required project files: ' + ', '.join(sorted(REQUIRED - names)))


def main():
    if sys.version_info < (3, 10) or not sys.platform.startswith('linux'):
        raise SystemExit('Requires Linux and Python 3.10+')
    parser = argparse.ArgumentParser(description='Lumqenix Community verified Linux beta installer')
    parser.add_argument('--prefix', type=Path, default=Path.home() / '.local/share/lumqenix-community')
    parser.add_argument('--extract-only', action='store_true', help='Extract without pip installation (CI/test mode)')
    parser.add_argument('--no-desktop', action='store_true', help='Do not create user desktop menu entry')
    args = parser.parse_args(sys.argv[2:])
    target = args.prefix.expanduser().resolve() / VERSION
    if target.exists() or target.is_symlink():
        raise SystemExit('Refusing to overwrite existing installation: ' + str(target))
    payload = Path(sys.argv[1]).read_bytes().partition(MARKER)[2]
    if not payload or hashlib.sha256(payload).hexdigest() != EXPECTED_SHA:
        raise SystemExit('Installer payload checksum mismatch: no files installed')
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as source:
            safe_members(source)
            root = target.parent
            root.mkdir(parents=True, exist_ok=True)
            staging = Path(tempfile.mkdtemp(prefix='.lumqenix-staging-', dir=root))
            try:
                source.extractall(staging)
                if target.exists() or target.is_symlink():
                    raise FileExistsError('Target appeared during staging')
                staging.rename(target)
            finally:
                if staging.exists():
                    shutil.rmtree(staging)
        print('Verified SHA-256 and extracted to:', target)
        if not args.extract_only:
            subprocess.run(['bash', str(target / 'scripts/install-linux.sh')], check=True)
            if not args.no_desktop:
                subprocess.run(['bash', str(target / 'scripts/install-desktop.sh')], check=True)
            print('Launch using: bash ' + str(target / 'scripts/run-linux.sh'))
    except (OSError, ValueError, zipfile.BadZipFile, subprocess.CalledProcessError) as exc:
        raise SystemExit('Lumqenix installation failed: ' + str(exc)) from exc

if __name__ == '__main__':
    main()
PYCODE
exit $?
__LUMQENIX_EMBEDDED_ZIP_PAYLOAD__
'''


def check_zip(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members = archive.infolist()
        names = set()
        total = 0
        for item in members:
            parts = PurePosixPath(item.filename).parts
            if not parts or item.filename.startswith('/') or '..' in parts or '\\' in item.filename or item.filename.startswith('~'):
                raise ValueError('Unsafe ZIP member: ' + item.filename)
            if item.filename in names:
                raise ValueError('Duplicate ZIP member: ' + item.filename)
            names.add(item.filename)
            if stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError('Symlink ZIP member: ' + item.filename)
            total += item.file_size
            if total > MAX_EXTRACTED_BYTES:
                raise ValueError('ZIP expands beyond 64 MiB limit')
        if not REQUIRED.issubset(names):
            raise ValueError('Missing project files: ' + ', '.join(sorted(REQUIRED - names)))
        if archive.testzip() is not None:
            raise ValueError('Corrupted ZIP member')


def build(source_zip, output, version):
    if not re.fullmatch(r'v0[.]3[.]0-rc[.][0-9]+', version):
        raise ValueError('Invalid release version')
    data = source_zip.read_bytes()
    check_zip(data)
    digest = hashlib.sha256(data).hexdigest()
    stub = STUB.replace('__SHA256__', digest).replace('__VERSION__', version).encode('utf-8')
    assert stub.endswith(MARKER)
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_name(output.name + '.partial')
    try:
        with temp.open('wb') as stream:
            stream.write(stub)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        temp.chmod(0o755)
        temp.replace(output)
    finally:
        if temp.exists():
            temp.unlink()
    return digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-zip', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--version', required=True)
    args = parser.parse_args()
    print('Verified embedded source ZIP SHA-256:', build(args.source_zip, args.output, args.version))
    print('Built Linux installer:', args.output)


if __name__ == '__main__':
    main()
