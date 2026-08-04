"""Execution and retention evidence for the four-condition coordination experiment."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
import shutil
from typing import Any, cast

from fastapi.testclient import TestClient
import pytest

import cybernetic_influence.api as api_module
from cybernetic_influence.api import create_app
from cybernetic_influence.experiments.coordination_experiment import (
    EXPERIMENT_CONDITIONS,
    EXPERIMENT_REPLICATES,
    EXPERIMENT_RUN_COUNT,
    CoordinationExperimentExecution,
    coordination_experiment_fixture,
    coordination_experiment_spec,
    coordination_live_probe_bindings,
    coordination_live_probe_fixture,
    run_scripted_coordination_experiment,
)
from cybernetic_influence.run_store import RunStore


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def executed_experiment(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[tuple[CoordinationExperimentExecution, Path]]:
    root = tmp_path_factory.mktemp("coordination_experiment_runs")
    yield run_scripted_coordination_experiment(root), root


def test_spec_freezes_four_conditions_and_two_replicates() -> None:
    specification = coordination_experiment_spec()

    assert [item.condition for item in specification.conditions] == list(
        EXPERIMENT_CONDITIONS
    )
    assert specification.replicates_per_condition == EXPERIMENT_REPLICATES
    assert specification.conditions[1].pressure_mode == "fixed"
    assert specification.conditions[2].pressure_mode == "adaptive"
    assert specification.conditions[3].authoritative_validation is True


def test_only_adaptive_conditions_expose_feedback_to_source_processes() -> None:
    fixed = coordination_experiment_fixture("fixed_heterogeneous_pressure")
    adaptive = coordination_experiment_fixture("adaptive_heterogeneous_pressure")
    fixed_specs = {item.active_system_id: item for item in fixed.runtime.active_specs}
    adaptive_specs = {
        item.active_system_id: item for item in adaptive.runtime.active_specs
    }

    for source_id in (
        "technical_pressure_source",
        "policy_pressure_source",
        "local_pressure_source",
    ):
        assert fixed_specs[source_id].observation_port_ids == []
        assert adaptive_specs[source_id].observation_port_ids == [
            f"{source_id}_feedback_in"
        ]
        assert "adaptive_followup" in " ".join(
            adaptive_specs[source_id].initial_representation_ids
        )


def test_live_probe_changes_people_not_experiment_mechanisms() -> None:
    model = "codex/gpt-5.6-luna"
    fixture = coordination_live_probe_fixture(
        "adaptive_pressure_with_stabilization",
        model=model,
        reasoning_effort="medium",
    )
    bindings = coordination_live_probe_bindings(
        fixture,
        trace_id_prefix="coordination-live-probe/test",
        model=model,
        reasoning_effort="medium",
    )
    specs = {item.active_system_id: item for item in fixture.runtime.active_specs}

    people = (
        "mission_coordinator",
        "technical_validation_lead",
        "sovereignty_policy_representative",
        "local_public_health_liaison",
        "partner_representative",
    )
    assert all(
        bindings[person_id].implementation.provider_bound for person_id in people
    )
    assert all(
        specs[person_id].implementation_id.startswith("native_coordination_")
        for person_id in people
    )
    assert all(
        getattr(bindings[person_id].implementation, "inner").model == model
        for person_id in people
    )
    for source_id in (
        "technical_pressure_source",
        "policy_pressure_source",
        "local_pressure_source",
    ):
        assert bindings[source_id].implementation.provider_bound is False
        assert bindings[source_id].implementation_id.startswith("scripted_adaptive_")
        assert specs[source_id].observation_port_ids == [f"{source_id}_feedback_in"]


def test_eight_runs_are_zero_provider_retained_and_evidence_reversible(
    executed_experiment: tuple[CoordinationExperimentExecution, Path],
) -> None:
    execution, root = executed_experiment
    readout = execution.readout

    assert len(readout.runs) == len(execution.retained_run_ids) == EXPERIMENT_RUN_COUNT
    assert readout.provider_calls == 0
    assert [
        (item.condition, item.replicate) for item in readout.runs
    ] == [
        (condition, replicate)
        for condition in EXPERIMENT_CONDITIONS
        for replicate in range(1, EXPERIMENT_REPLICATES + 1)
    ]
    by_condition = {
        condition: [item for item in readout.runs if item.condition == condition]
        for condition in EXPERIMENT_CONDITIONS
    }
    assert all(
        not item.adaptive_followup_event_ids
        for condition in ("baseline", "fixed_heterogeneous_pressure")
        for item in by_condition[condition]
    )
    assert all(
        item.adaptive_followup_event_ids
        for condition in (
            "adaptive_heterogeneous_pressure",
            "adaptive_pressure_with_stabilization",
        )
        for item in by_condition[condition]
    )
    assert all(
        not item.authoritative_validation_event_ids
        for condition in EXPERIMENT_CONDITIONS[:-1]
        for item in by_condition[condition]
    )
    assert all(
        item.authoritative_validation_event_ids
        for item in by_condition["adaptive_pressure_with_stabilization"]
    )

    store = RunStore(root)
    expected_readout = readout.model_dump(mode="json")
    for run_id in execution.retained_run_ids:
        first = cast(dict[str, Any], store.get(run_id))
        second = cast(dict[str, Any], store.get(run_id))
        assert first == second
        assert first["model_calls"] == 0
        assert first["cost"] == 0.0
        assert first["execution"] == "reference"
        assert first["coordination_experiment_readout"] == expected_readout
        assert "coordination_experiment_run_readout" in first
        assert "theory_analysis" in first
        assert any(
            boundary.get("activity")
            for boundary in cast(list[dict[str, Any]], first["boundaries"])
        )


def test_api_reopens_and_groups_the_retained_experiment(
    executed_experiment: tuple[CoordinationExperimentExecution, Path],
) -> None:
    execution, root = executed_experiment
    client = TestClient(create_app(ROOT / "web", root))

    reopened = client.get(
        f"/api/coordination-experiments/{execution.experiment_id}"
    )
    assert reopened.status_code == 200, reopened.text
    assert reopened.json() == execution.readout.model_dump(mode="json")
    history = client.get("/api/runs").json()["runs"]
    assert len(history) == EXPERIMENT_RUN_COUNT
    assert {
        item["coordination_experiment"]["experiment_id"] for item in history
    } == {execution.experiment_id}
    assert (
        client.get("/api/coordination-experiments/coordexp_invalid").status_code
        == 422
    )


def test_create_route_returns_the_validated_retained_readout_without_rerunning(
    executed_experiment: tuple[CoordinationExperimentExecution, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    execution, root = executed_experiment
    monkeypatch.setattr(
        api_module,
        "run_scripted_coordination_experiment",
        lambda _: execution,
    )
    response = TestClient(create_app(ROOT / "web", root)).post(
        "/api/coordination-experiments"
    )

    assert response.status_code == 200, response.text
    assert response.json() == execution.readout.model_dump(mode="json")


def test_api_rejects_an_incomplete_retained_matrix(
    executed_experiment: tuple[CoordinationExperimentExecution, Path],
    tmp_path: Path,
) -> None:
    execution, root = executed_experiment
    copied = tmp_path / "runs"
    shutil.copytree(root, copied)
    (copied / f"{execution.retained_run_ids[-1]}.json").unlink()

    response = TestClient(create_app(ROOT / "web", copied)).get(
        f"/api/coordination-experiments/{execution.experiment_id}"
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "retained coordination experiment is incomplete"


def test_delete_moves_all_eight_rows_to_recoverable_trash(
    executed_experiment: tuple[CoordinationExperimentExecution, Path],
    tmp_path: Path,
) -> None:
    execution, root = executed_experiment
    copied = tmp_path / "runs"
    shutil.copytree(root, copied)
    client = TestClient(create_app(ROOT / "web", copied))

    response = client.delete(
        f"/api/coordination-experiments/{execution.experiment_id}"
    )

    assert response.status_code == 200, response.text
    assert response.json()["trashed_run_count"] == EXPERIMENT_RUN_COUNT
    assert client.get("/api/runs").json()["runs"] == []
