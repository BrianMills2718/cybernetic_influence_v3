"""Direct integrity and private-permission gates for retained evidence."""

from __future__ import annotations

import json
from collections.abc import Mapping
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


def test_cost_baselines_only_use_comparable_observed_live_runs(tmp_path: Path) -> None:
    store = RunStore(tmp_path)
    configuration = {
        "model": "openrouter/deepseek/deepseek-v4-flash",
        "agent_reasoning_effort": "none",
        "narrator_reasoning_effort": "none",
    }
    for run_id, cost in (("run_aaaaaaaaaaaa", 0.004), ("run_bbbbbbbbbbbb", 0.006)):
        store.save(
            {
                "run_id": run_id,
                "status": "completed",
                "execution": "live",
                "cost_fully_observable": True,
                "cost": cost,
                "scenario": "service_desk",
                "arm": "baseline",
                "llm_configuration": configuration,
            }
        )
    store.save(
        {
            "run_id": "run_cccccccccccc",
            "status": "completed",
            "execution": "scripted",
            "cost_fully_observable": True,
            "cost": 0.0,
        }
    )

    assert store.cost_baselines() == [
        {
            "scenario": "service_desk",
            "arm": "baseline",
            "model": "openrouter/deepseek/deepseek-v4-flash",
            "agent_reasoning_effort": "none",
            "narrator_reasoning_effort": "none",
            "sample_count": 2,
            "median_cost": 0.005,
            "minimum_cost": 0.004,
            "maximum_cost": 0.006,
        }
    ]


def test_restart_invalidates_only_interrupted_post_run_measurement(
    tmp_path: Path,
) -> None:
    store = RunStore(tmp_path)
    store.save(
        {
            "run_id": "run_dddddddddddd",
            "status": "completed",
            "scenario": "coordination_decision",
            "story": {"headline": "World outcome retained"},
            "coordination_measurement_status": "running",
        }
    )

    changed = store.mark_incomplete_interrupted()
    retained = store.get("run_dddddddddddd")

    assert changed == 1
    assert retained["status"] == "completed"
    assert retained["story"] == {"headline": "World outcome retained"}
    assert retained["coordination_measurement_status"] == "invalid"
    failure = retained["coordination_measurement_failure"]
    assert isinstance(failure, Mapping)
    assert failure["error_type"] == "InterruptedMeasurement"


def test_restart_preserves_world_when_narration_resume_is_interrupted(
    tmp_path: Path,
) -> None:
    store = RunStore(tmp_path)
    store.save(
        {
            "run_id": "run_ffffffffffff",
            "status": "narrating",
            "story": {"headline": "World outcome retained"},
            "cost_fully_observable": True,
            "narration_resume": {
                "status": "running",
                "world_replayed": False,
            },
        }
    )

    changed = store.mark_incomplete_interrupted()
    retained = store.get("run_ffffffffffff")

    assert changed == 1
    assert retained["status"] == "completed"
    assert retained["story"] == {"headline": "World outcome retained"}
    assert retained["cost_fully_observable"] is False
    narration = retained["narration"]
    assert isinstance(narration, Mapping)
    failure_boundary = narration["failure_boundary"]
    assert isinstance(failure_boundary, Mapping)
    assert failure_boundary["kind"] == "interrupted_narration_resume"
    narration_resume = retained["narration_resume"]
    assert isinstance(narration_resume, Mapping)
    assert narration_resume["status"] == "failed"
    assert narration_resume["world_replayed"] is False


def test_run_summary_marks_only_measurements_that_need_validation(
    tmp_path: Path,
) -> None:
    store = RunStore(tmp_path)
    store.save(
        {
            "run_id": "run_eeeeeeeeeeee",
            "status": "completed",
            "scenario": "coordination_decision",
            "coordination_measurement": {"retained": "artifact"},
        }
    )

    summaries, corrupt = store.list_runs()

    assert corrupt == []
    assert summaries[0]["coordination_measurement_status"] == "needs_validation"
