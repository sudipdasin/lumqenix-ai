#!/usr/bin/env python3
"""Build and verify deterministic, source-only Lumqenix Community previews."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable


ARCHIVE_ROOT_PREFIX = "lumqenix-community-"
MANIFEST_NAME = "RELEASE-MANIFEST.json"
MAX_ARCHIVE_BYTES = 128 * 1024 * 1024
MAX_TOTAL_UNCOMPRESSED_BYTES = 256 * 1024 * 1024
MAX_MEMBERS = 10_000
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)

_SECRET_SUFFIXES = {
    ".pem", ".key", ".p12", ".pfx", ".pk8", ".keystore", ".jks",
    ".secret", ".secrets", ".token", ".credentials",
}
_WEIGHT_SUFFIXES = {
    ".onnx", ".pt", ".pth", ".ckpt", ".safetensors", ".engine",
    ".plan", ".weights", ".tflite", ".gguf", ".pb",
}
_EXCLUDED_PARTS = {
    ".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", ".tox", "node_modules",
}


class PreviewError(ValueError):
    """An unsafe or inconsistent preview source/archive was found."""


@dataclass(frozen=True)
class SourceFile:
    path: str
    data: bytes
    executable: bool


def _git(repo: Path, *args: str) -> bytes:
    try:
        return subprocess.run(
            ["git", "-C", str(repo), *args], check=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", b"")
        if isinstance(detail, bytes):
            detail = detail.decode("utf-8", "replace").strip()
        raise PreviewError(f"git {' '.join(args)} failed: {detail or exc}") from exc


def _validate_path(raw_path: str) -> PurePosixPath:
    if not raw_path or "\x00" in raw_path or "\\" in raw_path:
        raise PreviewError(f"unsafe tracked path: {raw_path!r}")
    path = PurePosixPath(raw_path)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in raw_path.split("/")):
        raise PreviewError(f"unsafe tracked path: {raw_path!r}")
    lower_parts = [part.lower() for part in path.parts]
    name = path.name.lower()
    if name == ".env" or name.startswith(".env.") or name.endswith(tuple(_SECRET_SUFFIXES)):
        raise PreviewError(f"refusing secret-like tracked file: {raw_path}")
    if any(part in _EXCLUDED_PARTS for part in lower_parts):
        return path
    if name.endswith(tuple(_WEIGHT_SUFFIXES)):
        raise PreviewError(f"refusing pretrained-weight or model artifact: {raw_path}")
    if any(part in {"site-packages", "dist-packages"} for part in lower_parts):
        raise PreviewError(f"refusing bundled dependency tree: {raw_path}")
    return path


def _read_head_files(repo: Path, commit: str) -> list[SourceFile]:
    records = _git(repo, "ls-tree", "-rz", "--full-tree", commit).split(b"\0")
    files: list[SourceFile] = []
    for record in records:
        if not record:
            continue
        try:
            metadata, path_bytes = record.split(b"\t", 1)
            mode, object_type, _object_id = metadata.decode("ascii").split()
            path = path_bytes.decode("utf-8", "strict")
        except (ValueError, UnicodeDecodeError) as exc:
            raise PreviewError("HEAD contains an unsupported Git path or tree entry") from exc
        posix = _validate_path(path)
        if object_type != "blob" or mode not in {"100644", "100755"}:
            raise PreviewError(f"refusing non-regular tracked entry: {path}")
        if any(part.lower() in _EXCLUDED_PARTS for part in posix.parts):
            continue
        data = _git(repo, "show", f"{commit}:{path}")
        executable = mode == "100755"
        if path.endswith(".sh") and not executable:
            # Shell entrypoints in a source archive remain directly runnable.
            executable = True
        files.append(SourceFile(path, data, executable))
    if not files:
        raise PreviewError("HEAD has no eligible Community source files")
    return sorted(files, key=lambda item: item.path)


def _version_from_source(files: Iterable[SourceFile]) -> str:
    matches = [entry for entry in files if entry.path == "backend/app/version.py"]
    if len(matches) != 1:
        raise PreviewError("HEAD must contain backend/app/version.py")
    try:
        tree = ast.parse(matches[0].data.decode("utf-8"), filename=matches[0].path)
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise PreviewError("backend/app/version.py is not valid UTF-8 Python") from exc
    values = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "VERSION" for target in node.targets
        ):
            try:
                values.append(ast.literal_eval(node.value))
            except (ValueError, TypeError) as exc:
                raise PreviewError("VERSION must be a literal string") from exc
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "VERSION":
            try:
                values.append(ast.literal_eval(node.value))
            except (ValueError, TypeError) as exc:
                raise PreviewError("VERSION must be a literal string") from exc
    if len(values) != 1 or not isinstance(values[0], str) or not re.fullmatch(r"[0-9A-Za-z][0-9A-Za-z.+-]*", values[0]):
        raise PreviewError("VERSION must be one safe literal semantic version")
    return values[0]


def _zip_info(name: str, executable: bool, *, directory: bool = False) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
    info.create_system = 3
    info.compress_type = zipfile.ZIP_DEFLATED
    mode = (0o755 if executable else 0o644) | (0o040000 if directory else 0o100000)
    info.external_attr = mode << 16
    if directory:
        info.external_attr |= 0x10
    return info


def build_preview(repo: Path, output_dir: Path) -> tuple[Path, Path, Path]:
    """Build artifacts from the repository's current HEAD, never the worktree."""
    repo = repo.resolve()
    commit = _git(repo, "rev-parse", "HEAD").decode("ascii").strip()
    files = _read_head_files(repo, commit)
    version = _version_from_source(files)
    root_name = f"{ARCHIVE_ROOT_PREFIX}{version}"
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / f"{root_name}.zip"
    manifest = {
        "format": 1,
        "product": "Lumqenix Community",
        "version": version,
        "source_commit": commit,
        "files": [
            {"path": item.path, "size": len(item.data), "sha256": hashlib.sha256(item.data).hexdigest()}
            for item in files
        ],
    }
    manifest_data = (json.dumps(manifest, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9, strict_timestamps=True) as zf:
        zf.writestr(_zip_info(f"{root_name}/", False, directory=True), b"")
        for item in files:
            zf.writestr(_zip_info(f"{root_name}/{item.path}", item.executable), item.data)
        zf.writestr(_zip_info(f"{root_name}/{MANIFEST_NAME}", False), manifest_data)
    archive_hash = _sha256_file(archive)
    sums_path = output_dir / "SHA256SUMS"
    sums_path.write_text(f"{archive_hash}  {archive.name}\n", encoding="ascii", newline="\n")
    provenance_path = output_dir / "provenance.json"
    provenance = {
        "format": 1,
        "archive": archive.name,
        "archive_sha256": archive_hash,
        "source_commit": commit,
        "version": version,
        "manifest": f"{root_name}/{MANIFEST_NAME}",
        "source_file_count": len(files),
    }
    provenance_path.write_text(json.dumps(provenance, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    return archive, sums_path, provenance_path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_archive_member(name: str) -> tuple[str, str]:
    if "\\" in name or "\x00" in name:
        raise PreviewError(f"unsafe archive member: {name!r}")
    normalized = name[:-1] if name.endswith("/") else name
    parts = normalized.split("/")
    if not normalized or any(part in {"", ".", ".."} for part in parts):
        raise PreviewError(f"unsafe archive member: {name!r}")
    if len(parts) < 2 or not parts[0].startswith(ARCHIVE_ROOT_PREFIX):
        raise PreviewError(f"unexpected archive layout: {name!r}")
    relative_path = PurePosixPath("/".join(parts[1:]))
    if any(part.lower() in _EXCLUDED_PARTS for part in relative_path.parts):
        raise PreviewError(f"refusing excluded archive member: {name!r}")
    _validate_path("/".join(parts[1:]))
    return parts[0], "/".join(parts[1:])


def verify_preview(archive: Path, expected_sha256: str) -> dict:
    """Verify outer checksum and every manifest-described byte in a preview ZIP."""
    archive = archive.resolve()
    if not re.fullmatch(r"[a-fA-F0-9]{64}", expected_sha256):
        raise PreviewError("expected SHA-256 must be exactly 64 hexadecimal characters")
    if archive.stat().st_size > MAX_ARCHIVE_BYTES:
        raise PreviewError("archive exceeds the compressed size limit")
    actual_hash = _sha256_file(archive)
    if actual_hash.lower() != expected_sha256.lower():
        raise PreviewError("archive SHA-256 does not match the expected checksum")
    try:
        with zipfile.ZipFile(archive, "r") as zf:
            infos = zf.infolist()
            if len(infos) > MAX_MEMBERS:
                raise PreviewError("archive contains too many members")
            if sum(info.file_size for info in infos) > MAX_TOTAL_UNCOMPRESSED_BYTES:
                raise PreviewError("archive exceeds the uncompressed size limit")
            roots: set[str] = set()
            members: dict[str, zipfile.ZipInfo] = {}
            directories: set[str] = set()
            for info in infos:
                if info.is_dir():
                    directory_name = info.filename[:-1]
                    if not directory_name or "\\" in directory_name or "\x00" in directory_name:
                        raise PreviewError(f"unsafe archive directory: {info.filename!r}")
                    parts = directory_name.split("/")
                    if any(part in {"", ".", ".."} for part in parts):
                        raise PreviewError(f"unsafe archive directory: {info.filename!r}")
                    if len(parts) == 1 and parts[0].startswith(ARCHIVE_ROOT_PREFIX):
                        root, relative = parts[0], ""
                    else:
                        root, relative = _safe_archive_member(directory_name)
                    roots.add(root)
                    directories.add(relative)
                    continue
                root, relative = _safe_archive_member(info.filename)
                roots.add(root)
                if relative in members:
                    raise PreviewError(f"duplicate archive member: {relative}")
                # Reject Unix symlink and other non-regular file entries.
                unix_mode = info.external_attr >> 16
                if unix_mode and (unix_mode & 0o170000) not in {0, 0o100000}:
                    raise PreviewError(f"non-regular archive member: {relative}")
                members[relative] = info
            if len(roots) != 1:
                raise PreviewError("archive must contain one versioned top-level directory")
            root = next(iter(roots))
            if not re.fullmatch(re.escape(ARCHIVE_ROOT_PREFIX) + r"[0-9A-Za-z][0-9A-Za-z.+-]*", root):
                raise PreviewError("archive root has an invalid version")
            manifest_path = f"{root}/{MANIFEST_NAME}"
            manifest_rel = MANIFEST_NAME
            if manifest_rel not in members:
                raise PreviewError("archive is missing RELEASE-MANIFEST.json")
            manifest = json.loads(zf.read(members[manifest_rel]).decode("utf-8"))
            if not isinstance(manifest, dict) or manifest.get("format") != 1 or manifest.get("version") != root[len(ARCHIVE_ROOT_PREFIX):]:
                raise PreviewError("manifest format or version does not match archive root")
            if not re.fullmatch(r"[0-9a-f]{40,64}", manifest.get("source_commit", "")):
                raise PreviewError("manifest has an invalid source commit")
            entries = manifest.get("files")
            if not isinstance(entries, list):
                raise PreviewError("manifest files must be a list")
            expected_files = {}
            for entry in entries:
                if not isinstance(entry, dict):
                    raise PreviewError("manifest contains an invalid file entry")
                rel = entry.get("path")
                if not isinstance(rel, str):
                    raise PreviewError("manifest contains an invalid file path")
                if any(part.lower() in _EXCLUDED_PARTS for part in PurePosixPath(rel).parts):
                    raise PreviewError(f"manifest references excluded source path: {rel}")
                _validate_path(rel)
                if rel in expected_files or rel == MANIFEST_NAME:
                    raise PreviewError(f"duplicate or reserved manifest path: {rel}")
                expected_files[rel] = entry
            if set(members) != set(expected_files) | {manifest_rel}:
                raise PreviewError("archive members do not match the release manifest")
            required_directories = {""}
            for rel in set(expected_files) | {manifest_rel}:
                pieces = rel.split("/")
                required_directories.update("/".join(pieces[:index]) for index in range(1, len(pieces)))
            if directories - {""} - required_directories:
                raise PreviewError("archive contains unexpected directories")
            for rel, entry in expected_files.items():
                data = zf.read(members[rel])
                if entry.get("size") != len(data) or entry.get("sha256") != hashlib.sha256(data).hexdigest():
                    raise PreviewError(f"manifest integrity check failed: {rel}")
            return manifest
    except (zipfile.BadZipFile, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        if isinstance(exc, PreviewError):
            raise
        raise PreviewError(f"invalid preview archive: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--verify", metavar="ARCHIVE", type=Path, help="verify a downloaded ZIP")
    parser.add_argument("--sha256", help="expected archive SHA-256 (required with --verify)")
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="Git repository (default: current directory)")
    parser.add_argument("--output-dir", type=Path, default=Path("dist"), help="artifact directory (default: dist)")
    args = parser.parse_args(argv)
    try:
        if args.verify:
            if not args.sha256:
                parser.error("--sha256 is required with --verify")
            manifest = verify_preview(args.verify, args.sha256)
            print(f"Verified Lumqenix Community {manifest['version']} ({len(manifest['files'])} files)")
        else:
            if args.sha256:
                parser.error("--sha256 is only valid with --verify")
            archive, sums, provenance = build_preview(args.repo, args.output_dir)
            print(f"Built {archive}\nChecksum: {sums}\nProvenance: {provenance}")
    except (PreviewError, OSError) as exc:
        print(f"preview error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
