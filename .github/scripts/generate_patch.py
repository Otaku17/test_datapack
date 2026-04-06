#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def safe_extract(zip_path: Path, dest: Path) -> None:
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            member_path = dest / member.filename
            resolved = member_path.resolve()
            if not str(resolved).startswith(str(dest.resolve())):
                raise RuntimeError(f"Unsafe path in zip: {member.filename}")
        zf.extractall(dest)


def list_files(root: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for path in root.rglob("*"):
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            files[rel] = path
    return files


def is_probably_executable(path: Path) -> bool:
    suffix = path.suffix.lower()
    return suffix in {".exe", ".dll", ".so", ".dylib", ".sh", ".bat", ".cmd"}


def normalize_permissions(src: Path, zi: zipfile.ZipInfo) -> zipfile.ZipInfo:
    mode = stat.S_IFREG | (0o755 if is_probably_executable(src) else 0o644)
    zi.external_attr = mode << 16
    return zi


def build_patch(old_dir: Path, new_dir: Path, output_zip: Path, from_version: str, to_version: str) -> None:
    old_files = list_files(old_dir)
    new_files = list_files(new_dir)

    added: list[str] = []
    modified: list[str] = []
    deleted: list[str] = []

    for rel, new_path in new_files.items():
        old_path = old_files.get(rel)
        if old_path is None:
            added.append(rel)
        else:
            if sha256_file(old_path) != sha256_file(new_path):
                modified.append(rel)

    for rel in old_files:
        if rel not in new_files:
            deleted.append(rel)

    manifest = {
        "from": from_version,
        "to": to_version,
        "added": sorted(added),
        "modified": sorted(modified),
        "deleted": sorted(deleted),
        "file_count": {
            "added": len(added),
            "modified": len(modified),
            "deleted": len(deleted),
        },
    }

    output_zip.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for rel in sorted(added + modified):
            src = new_files[rel]
            arcname = f"files/{rel}"
            zi = zipfile.ZipInfo.from_file(src, arcname=arcname)
            zi = normalize_permissions(src, zi)
            with src.open("rb") as f:
                zf.writestr(zi, f.read())

        manifest_bytes = json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8")
        zi = zipfile.ZipInfo("manifest.json")
        zi.external_attr = (stat.S_IFREG | 0o644) << 16
        zf.writestr(zi, manifest_bytes)

    print(json.dumps(manifest, indent=2, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate file-based patch zip from two release zips.")
    parser.add_argument("--old-zip", required=True, help="Path to previous full release zip")
    parser.add_argument("--new-zip", required=True, help="Path to current full release zip")
    parser.add_argument("--from-version", required=True, help="Previous version/tag")
    parser.add_argument("--to-version", required=True, help="Current version/tag")
    parser.add_argument("--output", required=True, help="Output patch zip path")
    args = parser.parse_args()

    old_zip = Path(args.old_zip).resolve()
    new_zip = Path(args.new_zip).resolve()
    output_zip = Path(args.output).resolve()

    if not old_zip.is_file():
        raise FileNotFoundError(f"Missing old zip: {old_zip}")
    if not new_zip.is_file():
        raise FileNotFoundError(f"Missing new zip: {new_zip}")

    with tempfile.TemporaryDirectory(prefix="patchgen-") as tmp:
        tmp_root = Path(tmp)
        old_dir = tmp_root / "old"
        new_dir = tmp_root / "new"
        old_dir.mkdir(parents=True, exist_ok=True)
        new_dir.mkdir(parents=True, exist_ok=True)

        safe_extract(old_zip, old_dir)
        safe_extract(new_zip, new_dir)

        build_patch(
            old_dir=old_dir,
            new_dir=new_dir,
            output_zip=output_zip,
            from_version=args.from_version,
            to_version=args.to_version,
        )


if __name__ == "__main__":
    main()