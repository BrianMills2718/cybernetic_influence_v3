"""Direct integrity and private-permission gates for retained evidence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cybernetic_influence.run_store import RunCorruptError, RunStore


def test_store_uses_private_modes_and_recoverable_private_trash(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    store = RunStore(root)
    stored = store.save({"run_id": "run_aaaaaaaaaaaa", "status": "completed"})
    retained = root / "run_aaaaaaaaaaaa.json"
    assert stored["storage_schema_version"] == 1
    assert root.stat().st_mode & 0o777 == 0o700
    assert retained.stat().st_mode & 0o777 == 0o600

    trashed = store.trash("run_aaaaaaaaaaaa")
    assert trashed.parent.stat().st_mode & 0o777 == 0o700
    assert trashed.stat().st_mode & 0o777 == 0o600


def test_filename_and_document_identity_must_match(tmp_path: Path) -> None:
    store = RunStore(tmp_path)
    store.save({"run_id": "run_aaaaaaaaaaaa", "status": "completed"})
    path = tmp_path / "run_aaaaaaaaaaaa.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["run_id"] = "run_bbbbbbbbbbbb"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(RunCorruptError):
        store.get("run_aaaaaaaaaaaa")
    summaries, corrupt = store.list_runs()
    assert summaries == []
    assert corrupt == ["run_aaaaaaaaaaaa.json"]
