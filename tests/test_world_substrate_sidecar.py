"""The public Waltzman host keeps Cybernetic and World Substrate side by side."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

from fastapi.testclient import TestClient

from cybernetic_influence.api import (
    _inline_script_csp_hashes_with_srcdoc_documents,
    create_app,
)

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ROOT = ROOT / "public" / "waltzman"
CYBERNETIC_PAGE = PUBLIC_ROOT / "index.html"
WORLD_SUBSTRATE_PAGE = PUBLIC_ROOT / "world-substrate.html"
WORLD_SUBSTRATE_REVISION = PUBLIC_ROOT / "world-substrate-revision.json"


def test_existing_cybernetic_root_is_unchanged_while_sidecar_is_available(tmp_path: Path) -> None:
    client = TestClient(
        create_app(web_root=PUBLIC_ROOT, run_root=tmp_path / "runs", allow_inline_styles=True)
    )
    root = client.get("/")
    sidecar = client.get("/world-substrate/")
    assert root.status_code == 200
    assert root.content == CYBERNETIC_PAGE.read_bytes()
    assert sidecar.status_code == 200
    assert sidecar.content == WORLD_SUBSTRATE_PAGE.read_bytes()
    assert "Waltzman Coordination Lab" in sidecar.text
    assert client.get("/world-substrate").status_code == 200


def test_sidecar_revision_pins_exact_world_substrate_artifact(tmp_path: Path) -> None:
    client = TestClient(
        create_app(web_root=PUBLIC_ROOT, run_root=tmp_path / "runs", allow_inline_styles=True)
    )
    response = client.get("/world-substrate/revision.json")
    assert response.status_code == 200
    record = response.json()
    actual = hashlib.sha256(WORLD_SUBSTRATE_PAGE.read_bytes()).hexdigest()
    assert record["source_revision"] == "27164359bd63e5f6c1cd193f0d970c8847ddc9cb"
    assert record["source_sha256"] == actual
    assert record["route"] == "/world-substrate/"


def test_sidecar_csp_allows_only_exact_outer_and_srcdoc_script_hashes(tmp_path: Path) -> None:
    client = TestClient(
        create_app(web_root=PUBLIC_ROOT, run_root=tmp_path / "runs", allow_inline_styles=True)
    )
    sidecar = client.get("/world-substrate/")
    policy = sidecar.headers["content-security-policy"]
    expected = _inline_script_csp_hashes_with_srcdoc_documents(WORLD_SUBSTRATE_PAGE)
    assert expected.count("'sha256-") == 3
    for source in expected.split():
        assert source in policy
    assert "script-src 'self' 'unsafe-inline'" not in policy


def test_sidecar_checker_accepts_committed_snapshot() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_world_substrate_sidecar.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    record = json.loads(WORLD_SUBSTRATE_REVISION.read_text())
    assert record["source_sha256"] in completed.stdout
