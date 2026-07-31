"""Zero-provider execution evidence for Packet 22A1."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest

from cybernetic_influence.analysis.composite_agency import CONTROL_ID
from cybernetic_influence.causal_core.models import FactState
from cybernetic_influence.experiments.composite_agency import (
    CompositeAssayExecution,
    composite_experiment_fixture,
    run_scripted_composite_assay,
    validate_matched_configuration,
)
from cybernetic_influence.run_store import RunStore


@pytest.fixture(scope="module")
def executed_assay(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[tuple[CompositeAssayExecution, Path]]:
    root = tmp_path_factory.mktemp("composite_assay_runs")
    yield run_scripted_composite_assay(root), root


def test_five_rows_are_zero_cost_retained_and_reopenable(
    executed_assay: tuple[CompositeAssayExecution, Path],
) -> None:
    execution, root = executed_assay

    assert [item.perturbation_id for item in execution.run_refs] == [
        "matched_control",
        "member_replacement",
        "route_interruption",
        "feedback_interruption",
        "external_risk",
    ]
    assert len(execution.readouts) == len(execution.retained_run_ids) == 5
    assert execution.assay_id.startswith("assay_")
    store = RunStore(root)
    for row_index, run_id in enumerate(execution.retained_run_ids):
        first = cast(dict[str, Any], store.get(run_id))
        second = cast(dict[str, Any], store.get(run_id))
        assert first == second
        assert first["model_calls"] == 0
        assert first["cost"] == 0.0
        assert first["execution"] == "reference"
        assert first["configuration_diff"]["unexpected_refs"] == []
        assert "composite_control_readout" in first
        assert "theory_analysis" in first
        assert first["composite_assay"] == {
            "schema_version": 1,
            "assay_id": execution.assay_id,
            "row_index": row_index,
            "row_count": 5,
            "provider_calls": 0,
        }


def test_rows_exercise_distinct_concrete_paths(
    executed_assay: tuple[CompositeAssayExecution, Path],
) -> None:
    execution, root = executed_assay
    by_row = {item.perturbation_id: item for item in execution.readouts}

    assert by_row[CONTROL_ID].exact_values["capability_satisfied"] is True
    assert by_row["member_replacement"].exact_values["member_replacements"] == [
        {
            "position_id": "technical_validation_lead",
            "person_instance_id": "technical_validation_lead_replacement",
        }
    ]
    route = by_row["route_interruption"].exact_values
    assert route["capability_satisfied"] is True
    assert route["alternate_routes_used"]
    feedback = by_row["feedback_interruption"].exact_values
    assert feedback["capability_satisfied"] is False
    assert feedback["terminal_outcome"] == "no_decision_by_horizon"
    assert feedback["recovery"] == "not_observed"
    shock = by_row["external_risk"]
    assert shock.coded_patterns[0].pattern_id == "rational_caution"
    assert shock.coded_patterns[0].direction == "present"

    store = RunStore(root)
    route_doc = cast(dict[str, Any], store.get(execution.retained_run_ids[2]))
    route_events = route_doc["events"]
    assert any(
        item.get("connection_id") == "terminal_proposal_alternate_route"
        for item in route_events
    )
    feedback_doc = cast(dict[str, Any], store.get(execution.retained_run_ids[3]))
    assert sum(
        item.get("details", {}).get("outcome_code")
        == "verification_feedback_interrupted"
        for item in feedback_doc["events"]
    ) == 5
    shock_doc = cast(dict[str, Any], store.get(execution.retained_run_ids[4]))
    assert any(
        item.get("connection_id") == "external_risk_route"
        for item in shock_doc["events"]
    )


def test_member_replacement_preserves_position_interfaces_but_changes_behavior(
    executed_assay: tuple[CompositeAssayExecution, Path],
) -> None:
    execution, root = executed_assay
    store = RunStore(root)
    control = cast(dict[str, Any], store.get(execution.retained_run_ids[0]))
    replacement = cast(dict[str, Any], store.get(execution.retained_run_ids[1]))

    assert replacement["configuration_diff"][
        "initial_configuration_changed_refs"
    ] == ["technical_validation_lead"]
    control_requests = [
        item
        for item in control["events"]
        if item.get("event_kind") == "action_attempted"
        and item.get("source_port_id") == "verification_request_out"
    ]
    replacement_requests = [
        item
        for item in replacement["events"]
        if item.get("event_kind") == "action_attempted"
        and item.get("source_port_id") == "verification_request_out"
    ]
    assert replacement_requests[0]["logical_time"] < control_requests[0]["logical_time"]


def test_undeclared_configuration_change_fails_loud() -> None:
    control = composite_experiment_fixture(CONTROL_ID, None)
    state = control.scenario.initial_state.model_copy(deep=True)
    coordinator = state.entities["mission_coordinator"]
    attributes = dict(coordinator.attributes)
    attributes["undeclared_test_change"] = FactState(value=True)
    state.entities["mission_coordinator"] = coordinator.model_copy(
        update={"attributes": attributes}
    )
    scenario = control.scenario.model_copy(update={"initial_state": state})
    contract = control.runtime.contract.model_copy(update={"scenario": scenario})
    runtime = replace(control.runtime, contract=contract)
    changed = replace(control, runtime=runtime)

    with pytest.raises(ValueError, match="undeclared scenario references"):
        validate_matched_configuration(control, changed)
