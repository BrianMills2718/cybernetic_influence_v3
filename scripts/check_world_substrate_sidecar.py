#!/usr/bin/env python3
"""Verify the pinned World Substrate living-world sidecar before publication."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ROOT = ROOT / "public" / "waltzman"
HTML = PUBLIC_ROOT / "world-substrate.html"
REVISION = PUBLIC_ROOT / "world-substrate-revision.json"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_show(repo: Path, revision: str, path: str) -> bytes:
    return subprocess.check_output(
        ["git", "-C", str(repo), "show", f"{revision}:{path}"]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-repo", type=Path)
    args = parser.parse_args()

    record = json.loads(REVISION.read_text(encoding="utf-8"))
    if record.get("schema_version") != "cybernetic-influence-world-substrate-sidecar/v1":
        raise SystemExit("invalid World Substrate sidecar revision schema")
    revision = record.get("source_revision")
    if not isinstance(revision, str) or re.fullmatch(r"[0-9a-f]{40}", revision) is None:
        raise SystemExit("World Substrate sidecar source_revision must be a full git SHA")
    if record.get("route") != "/world-substrate/":
        raise SystemExit("World Substrate sidecar route must remain /world-substrate/")

    markup = HTML.read_bytes()
    actual = sha256(markup)
    if actual != record.get("source_sha256"):
        raise SystemExit(f"World Substrate sidecar hash mismatch: {actual}")
    text = markup.decode("utf-8")
    for marker in ("World Substrate", "Waltzman Coordination Lab", "Baseline", "Intervention"):
        if marker not in text:
            raise SystemExit(f"World Substrate sidecar is missing marker: {marker}")
    if re.search(r"<script[^>]+src=", text, re.IGNORECASE):
        raise SystemExit("World Substrate sidecar must remain self-contained (external script found)")
    if re.search(r"<link[^>]+rel=['\"]stylesheet", text, re.IGNORECASE):
        raise SystemExit("World Substrate sidecar must remain self-contained (external stylesheet found)")

    if args.source_repo is not None:
        source_repo = args.source_repo.resolve()
        source_path = str(record["source_path"])
        if sha256(git_show(source_repo, revision, source_path)) != actual:
            raise SystemExit("pinned sidecar does not match the named World Substrate source revision")
        manifest_path = str(record["source_manifest_path"])
        manifest_hash = sha256(git_show(source_repo, revision, manifest_path))
        if manifest_hash != record.get("source_manifest_sha256"):
            raise SystemExit("pinned World Substrate manifest hash does not match source revision")

    print(f"World Substrate sidecar check passed: {revision} {actual}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
