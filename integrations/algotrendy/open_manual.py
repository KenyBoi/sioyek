#!/usr/bin/env python3
"""Verify and open a pinned AlgoTrendy manual artifact.

This launcher intentionally has no shell evaluation and accepts no selected PDF
text. It is suitable for a Sioyek ``new_command`` binding.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_manifest(path: Path) -> dict[str, str]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read manifest: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("manifest must be a JSON object")
    required = ("artifact", "source_repository", "source_revision", "sha256")
    missing = [key for key in required if not isinstance(value.get(key), str)]
    if missing:
        raise ValueError(f"manifest missing string fields: {', '.join(missing)}")
    if not SHA256_RE.fullmatch(value["sha256"]):
        raise ValueError("manifest sha256 must be 64 lowercase hexadecimal characters")
    if not re.fullmatch(r"[0-9a-f]{40}", value["source_revision"]):
        raise ValueError("manifest source_revision must be a 40-character commit SHA")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--sioyek", type=Path, required=True)
    args = parser.parse_args()

    if not args.pdf.is_file():
        print(f"manual blocked: PDF not found: {args.pdf}", file=sys.stderr)
        return 2
    if not args.manifest.is_file():
        print(f"manual blocked: manifest not found: {args.manifest}", file=sys.stderr)
        return 2
    if not args.sioyek.is_file():
        print(f"manual blocked: Sioyek executable not found: {args.sioyek}", file=sys.stderr)
        return 2

    try:
        manifest = _parse_manifest(args.manifest)
        actual_sha256 = _sha256(args.pdf)
    except (OSError, ValueError) as exc:
        print(f"manual blocked: {exc}", file=sys.stderr)
        return 2

    if actual_sha256 != manifest["sha256"]:
        print(
            "manual blocked: checksum mismatch "
            f"(expected {manifest['sha256']}, observed {actual_sha256})",
            file=sys.stderr,
        )
        return 3

    try:
        completed = subprocess.run([str(args.sioyek), str(args.pdf)], check=False)
    except OSError as exc:
        print(f"manual blocked: could not launch Sioyek: {exc}", file=sys.stderr)
        return 4
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
