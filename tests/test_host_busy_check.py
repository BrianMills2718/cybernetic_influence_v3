"""The in-flight-work gate must actually see a live run.

This gate is the only thing standing between a scheduled restart and a user's
running simulation. It has already failed that job three times in this project's
history, each time by restarting the service while work was executing, so its
behaviour is pinned here rather than left to inspection.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load() -> ModuleType:
    path = REPO_ROOT / "scripts" / "host_busy_check.py"
    spec = importlib.util.spec_from_file_location("host_busy_check", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["host_busy_check"] = module
    spec.loader.exec_module(module)
    return module


def _write(path: Path, document: dict[str, object], age_seconds: float = 0.0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document))
    if age_seconds:
        stamp = time.time() - age_seconds
        os.utime(path, (stamp, stamp))


def test_idle_store_reports_nothing(tmp_path: Path) -> None:
    assert _load().busy_reasons(str(tmp_path)) == []


@pytest.mark.parametrize("status", ["running", "narrating", "pause_requested"])
def test_active_run_blocks(tmp_path: Path, status: str) -> None:
    _write(tmp_path / "runs" / "run_abc.json", {"status": status})
    reasons = _load().busy_reasons(str(tmp_path))
    assert len(reasons) == 1
    assert "run_abc.json" in reasons[0] and status in reasons[0]


def test_finished_run_does_not_block(tmp_path: Path) -> None:
    _write(tmp_path / "runs" / "run_abc.json", {"status": "complete"})
    assert _load().busy_reasons(str(tmp_path)) == []


def test_stale_running_run_does_not_block(tmp_path: Path) -> None:
    """An hour-old 'running' file is a crashed run, not work in flight."""
    _write(tmp_path / "runs" / "run_old.json", {"status": "running"}, age_seconds=7200)
    assert _load().busy_reasons(str(tmp_path)) == []


def test_fresh_unresolved_draft_blocks(tmp_path: Path) -> None:
    """An authoring job in flight is only visible as a fresh, empty draft."""
    _write(tmp_path / "authoring_drafts" / "draft_1.json", {"status": "draft"})
    reasons = _load().busy_reasons(str(tmp_path))
    assert len(reasons) == 1
    assert "draft_1.json" in reasons[0]


def test_draft_with_attempts_does_not_block(tmp_path: Path) -> None:
    _write(
        tmp_path / "authoring_drafts" / "draft_1.json",
        {"status": "draft", "attempts": [{"error": "nope"}]},
    )
    assert _load().busy_reasons(str(tmp_path)) == []


def test_completed_draft_does_not_block(tmp_path: Path) -> None:
    _write(
        tmp_path / "authoring_drafts" / "draft_1.json",
        {"status": "draft", "proposal": {"title": "done"}},
    )
    assert _load().busy_reasons(str(tmp_path)) == []


def test_unreadable_file_does_not_block(tmp_path: Path) -> None:
    """A corrupt file must not wedge the gate closed forever."""
    path = tmp_path / "runs" / "run_bad.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json")
    assert _load().busy_reasons(str(tmp_path)) == []
