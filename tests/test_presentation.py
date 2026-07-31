"""Adversarial gates for analyst visibility and temporal truth."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from cybernetic_influence.api import create_app
from cybernetic_influence.active_runtime import ActiveRuntimeResult
from cybernetic_influence.causal_core.models import (
    AnalyticalBoundary,
    CausalEvent,
    CausalState,
    EntityState,
    FactChange,
    StatePatch,
)
from cybernetic_influence.presentation import (
    BoundaryProjectionError,
    _temporal_states,
    _analyst_animation_cues,
    analyst_edges,
    analyst_event,
    analyst_graph_diagnostics,
    boundary_activity_event_index,
    clip_boundary_activity_projection,
    project_boundary_activity,
    service_desk_summary,
)
from cybernetic_influence.scenarios.coordination_decision import (
    PARTNERSHIP_BOUNDARY_ID,
    CoordinationRuntimeFixture,
    baseline_coordination_fixture,
    coordination_decision_fixtures,
    coordination_runtime_fixture,
    run_scripted_coordination,
    stabilization_coordination_fixture,
)
from cybernetic_influence.scenarios.physical_access import (
    physical_access_arm_configurations,
    physical_access_fixture,
)
from cybernetic_influence.scenarios.purchase_payment import (
    purchase_payment_arm_configurations,
    purchase_payment_fixture,
)
from cybernetic_influence.scenarios.service_desk import (
    service_desk_arm_configurations,
    service_desk_fixture,
)


ROOT = Path(__file__).resolve().parents[1]
TRIAGER_CANARY = "triager_route_key_17"
SUPERVISOR_CANARY = "supervisor_close_key_17"
BADGE_CANARY = "equipment_badge_key_41"


def test_configured_graph_explains_active_and_analytical_only_nodes() -> None:
    scenario = stabilization_coordination_fixture().scenario
    diagnostics = analyst_graph_diagnostics(
        scenario.initial_state,
        scenario.analytical_boundaries,
    )
    edge_kinds = {
        str(edge["kind"]) for edge in analyst_edges(scenario.initial_state)
    }

    assert diagnostics["warnings"] == []
    assert diagnostics["counts"] == {
        "causal": 51,
        "analytical_only": 3,
        "spatial_only": 0,
        "unused": 0,
    }
    classifications = diagnostics["node_classification"]
    assert isinstance(classifications, dict)
    assert classifications["meeting_schedule"] == "causal"
    assert classifications["coordination_platform"] == "causal"
    assert classifications["decision_goal"] == "analytical_only"
    assert {
        "mechanism_read",
        "mechanism_write",
        "mechanism_substrate",
        "observation_target",
    } <= edge_kinds


def test_configured_graph_warns_about_only_unexplained_isolation() -> None:
    scenario = stabilization_coordination_fixture().scenario
    state = scenario.initial_state.model_copy(
        update={
            "entities": {
                **scenario.initial_state.entities,
                "unused_rock": EntityState(
                    entity_id="unused_rock",
                    entity_kind="physical_object",
                    description="A deliberately unexplained lint fixture.",
                ),
            }
        }
    )

    diagnostics = analyst_graph_diagnostics(
        state,
        scenario.analytical_boundaries,
    )

    counts = diagnostics["counts"]
    assert isinstance(counts, dict)
    assert counts["unused"] == 1
    assert diagnostics["warnings"] == [
        {
            "code": "unexplained_isolated_node",
            "node_id": "unused_rock",
            "message": (
                "Unused Rock has no configured causal, spatial, or analytical "
                "relationship."
            ),
        }
    ]


def test_every_built_in_scenario_arm_explains_each_configured_node() -> None:
    scenarios = [
        *(
            service_desk_fixture(arm).scenario
            for arm in service_desk_arm_configurations()
        ),
        *(
            physical_access_fixture(arm).scenario
            for arm in physical_access_arm_configurations()
        ),
        *(
            purchase_payment_fixture(arm).scenario
            for arm in purchase_payment_arm_configurations()
        ),
        *(fixture.scenario for fixture in coordination_decision_fixtures()),
    ]

    warnings_by_scenario = {
        scenario.scenario_id: analyst_graph_diagnostics(
            scenario.initial_state,
            scenario.analytical_boundaries,
        )["warnings"]
        for scenario in scenarios
    }

    assert len(scenarios) == 12
    assert warnings_by_scenario == {
        scenario.scenario_id: [] for scenario in scenarios
    }


@lru_cache(maxsize=2)
def _coordination_run(
    *, stabilization: bool = True
) -> tuple[
    CoordinationRuntimeFixture,
    ActiveRuntimeResult,
    AnalyticalBoundary,
]:
    contract = (
        stabilization_coordination_fixture()
        if stabilization
        else baseline_coordination_fixture()
    )
    fixture = coordination_runtime_fixture(contract)
    result = run_scripted_coordination(fixture, run_id="boundary_projection_gate")
    boundary = next(
        item
        for item in fixture.scenario.analytical_boundaries
        if item.boundary_id == PARTNERSHIP_BOUNDARY_ID
    )
    return fixture, result, boundary


def _coordination_activity(
    *, stabilization: bool = True
) -> tuple[
    CoordinationRuntimeFixture,
    ActiveRuntimeResult,
    dict[str, CausalState],
    AnalyticalBoundary,
]:
    fixture, result, boundary = _coordination_run(stabilization=stabilization)
    return (
        fixture,
        result,
        _temporal_states(fixture.scenario.initial_state, result.core_result.events),
        boundary,
    )


def test_boundary_activity_retains_input_internal_output_and_external_result() -> None:
    _, result, states, boundary = _coordination_activity()
    activity = project_boundary_activity(
        boundary,
        states,
        result.core_result.events,
    )
    completed = next(item for item in activity.episodes if item.status == "completed")
    crossing_by_id = {item.crossing_id: item for item in activity.crossings}

    assert completed.input_crossing_ids
    assert crossing_by_id[completed.input_crossing_ids[0]].direction == "incoming"
    assert completed.output_crossing_id is not None
    assert crossing_by_id[completed.output_crossing_id].direction == "outgoing"
    assert len(completed.contributing_member_ids) >= 4
    assert "mission_coordinator" in completed.contributing_member_ids
    assert "terminal_decision_gate" in completed.contributing_member_ids
    external = {
        event.event_id: event
        for event in result.core_result.events
        if event.event_id in completed.external_result_event_ids
    }
    assert {event.event_kind for event in external.values()} == {
        "mechanism_executed",
        "state_committed",
    }
    assert {event.mechanism_id for event in external.values()} == {
        "external_decision_receiver"
    }


def test_boundary_activity_prefix_exposes_no_future_output_or_result() -> None:
    _, result, states, boundary = _coordination_activity()
    full = project_boundary_activity(boundary, states, result.core_result.events)
    output = next(item for item in full.crossings if item.direction == "outgoing")
    prefix = project_boundary_activity(
        boundary,
        states,
        result.core_result.events,
        through_sequence=output.sequence - 1,
    )
    by_id = {event.event_id: event for event in result.core_result.events}

    assert all(item.direction == "incoming" for item in prefix.crossings)
    assert all(item.status == "in_progress" for item in prefix.episodes)
    assert all(item.output_crossing_id is None for item in prefix.episodes)
    assert all(item.external_result_event_ids == [] for item in prefix.episodes)
    assert all(
        by_id[event_id].sequence < output.sequence
        for item in prefix.episodes
        for event_id in item.internal_event_ids
    )


def test_retained_boundary_activity_clips_exactly_at_selected_event() -> None:
    _, result, states, boundary = _coordination_activity()
    full = project_boundary_activity(boundary, states, result.core_result.events)
    event_index = boundary_activity_event_index(
        boundary, states, result.core_result.events
    )
    events = [
        analyst_event(event)
        for event in result.core_result.events
    ]
    output = next(item for item in full.crossings if item.direction == "outgoing")

    before = clip_boundary_activity_projection(
        full,
        events,
        event_index,
        through_sequence=output.sequence - 1,
    )
    at_output = clip_boundary_activity_projection(
        full,
        events,
        event_index,
        through_sequence=output.sequence,
    )
    final = clip_boundary_activity_projection(
        full,
        events,
        event_index,
        through_sequence=result.core_result.events[-1].sequence,
    )

    assert not any(item.direction == "outgoing" for item in before.crossings)
    assert all(item.status == "in_progress" for item in before.episodes)
    direct_before = project_boundary_activity(
        boundary,
        states,
        result.core_result.events,
        through_sequence=output.sequence - 1,
    )
    assert {
        item.episode_id: item.contributing_member_ids for item in before.episodes
    } == {
        item.episode_id: item.contributing_member_ids
        for item in direct_before.episodes
    }
    completed_at_output = next(
        item for item in at_output.episodes if item.status == "completed"
    )
    assert completed_at_output.output_crossing_id == output.crossing_id
    assert completed_at_output.external_result_event_ids == []
    assert next(
        item for item in final.episodes if item.status == "completed"
    ).external_result_event_ids


def test_configured_or_internal_routes_do_not_invent_crossings() -> None:
    fixture, result, states, boundary = _coordination_activity(stabilization=False)
    activity = project_boundary_activity(boundary, states, result.core_result.events)
    crossing_events = {item.event_id for item in activity.crossings}
    internal_route_events = {
        event.event_id
        for event in result.core_result.events
        if event.event_kind == "effect_routed"
        and event.connection_id == "verification_request_route"
    }

    assert not any(item.direction == "incoming" for item in activity.crossings)
    autonomous = next(item for item in activity.episodes if item.status == "completed")
    assert autonomous.input_crossing_ids == []
    assert autonomous.output_crossing_id is not None
    assert not internal_route_events & crossing_events
    assert "technical_source_route" in result.core_result.final_state.connections

    focus_only_events = [
        event.model_copy(update={"focus_ids": [boundary.member_refs[0]]})
        for event in result.core_result.events
    ]
    focus_only = project_boundary_activity(
        boundary,
        states,
        focus_only_events,
    )
    assert focus_only.crossings == activity.crossings

    source_boundary = next(
        item
        for item in fixture.scenario.analytical_boundaries
        if item.boundary_id != PARTNERSHIP_BOUNDARY_ID
    )
    source_activity = project_boundary_activity(
        source_boundary,
        states,
        result.core_result.events,
    )
    crossing_event_ids = {item.event_id for item in source_activity.crossings}
    terminal_route_event_ids = {
        event.event_id
        for event in result.core_result.events
        if event.connection_id == "terminal_decision_output_route"
    }
    assert not crossing_event_ids & terminal_route_event_ids


@pytest.mark.parametrize(
    "mutation",
    ["duplicate", "unknown_parent", "unknown_port", "unknown_route", "cross_run"],
)
def test_boundary_activity_rejects_corrupt_retained_evidence(mutation: str) -> None:
    _, result, states, boundary = _coordination_activity()
    events = list(result.core_result.events)
    routed_index = next(
        index for index, event in enumerate(events) if event.event_kind == "effect_routed"
    )
    if mutation == "duplicate":
        events.insert(routed_index + 1, events[routed_index])
    elif mutation == "unknown_parent":
        events[routed_index] = events[routed_index].model_copy(
            update={"causal_parent_event_ids": ["event_999999"]}
        )
    elif mutation == "unknown_port":
        events[routed_index] = events[routed_index].model_copy(
            update={"target_port_id": "unknown_port"}
        )
    elif mutation == "unknown_route":
        events[routed_index] = events[routed_index].model_copy(
            update={"connection_id": "unknown_route"}
        )
    else:
        events[routed_index] = events[routed_index].model_copy(
            update={"run_id": "another_run"}
        )

    with pytest.raises(BoundaryProjectionError):
        project_boundary_activity(boundary, states, events)


def test_boundary_activity_rejects_unknown_member() -> None:
    _, result, states, boundary = _coordination_activity()
    corrupt = boundary.model_copy(
        update={"member_refs": [*boundary.member_refs, "unknown_member"]}
    )
    with pytest.raises(BoundaryProjectionError, match="unknown members"):
        project_boundary_activity(corrupt, states, result.core_result.events)


def test_boundary_activity_rejects_direct_outside_mutation_even_with_output() -> None:
    _, result, states, boundary = _coordination_activity()
    changed_members = [
        item for item in boundary.member_refs if item != "decision_record"
    ]
    corrupt = boundary.model_copy(update={"member_refs": changed_members})

    with pytest.raises(
        BoundaryProjectionError,
        match="directly mutates nonmember-owned state",
    ):
        project_boundary_activity(corrupt, states, result.core_result.events)


def test_mechanism_credentials_never_cross_analyst_boundary(tmp_path: Path) -> None:
    body = TestClient(create_app(ROOT / "web", tmp_path)).post(
        "/api/runs",
        json={"arm_id": "baseline", "execution": "scripted"},
    ).json()
    encoded = json.dumps(body)
    assert TRIAGER_CANARY not in encoded
    assert SUPERVISOR_CANARY not in encoded

    authority = next(node for node in body["nodes"] if node["id"] == "credential_authority")
    assert authority["state"]["triager_verifier"] == {
        "visibility": "mechanism",
        "redacted": True,
    }
    credential = next(
        node for node in body["nodes"] if node["id"] == "triager_routing_credential"
    )
    assert credential["state"]["redacted"] is True
    assert "content" not in credential["state"]
    assert "content_hash" not in credential["state"]
    protected_action = next(
        action
        for trace in body["traces"]
        for action in trace["actions"]
        if action["representation_id"] == "triager_routing_credential"
    )
    assert protected_action["payload"] == "[redacted]"


def test_physical_badge_never_crosses_analyst_boundary(tmp_path: Path) -> None:
    body = TestClient(create_app(ROOT / "web", tmp_path)).post(
        "/api/runs",
        json={
            "scenario": "physical_access",
            "arm_id": "authorized_access",
            "execution": "scripted",
        },
    ).json()
    encoded = json.dumps(body)
    assert BADGE_CANARY not in encoded
    badge = next(node for node in body["nodes"] if node["id"] == "technician_badge")
    assert badge["state"] == {
        "representation_id": "technician_badge",
        "encoding": "application/vnd.cybernetic.badge-presentation+json",
        "visibility": "mechanism",
        "redacted": True,
    }
    policy_event = next(
        event
        for event in body["timeline"]
        if event["kind"] == "mechanism_executed"
        and event["focus_ids"]
        and "access_policy_copy" in event["focus_ids"]
    )
    assert policy_event["state_revision"] >= 1


def test_exact_mechanism_playback_cue_distinguishes_retained_denial() -> None:
    from cybernetic_influence.scenarios.physical_access import (
        physical_access_arm_configurations,
        physical_access_fixture,
        physical_access_scripted_bindings,
        run_physical_access,
    )

    arm = next(
        item
        for item in physical_access_arm_configurations()
        if item.arm_id == "authorization_absent"
    )
    fixture = physical_access_fixture(arm)
    result = run_physical_access(
        fixture,
        physical_access_scripted_bindings(fixture),
        run_id="presentation_denied_cue",
    )
    denied = next(
        event
        for event in result.core_result.events
        if event.event_kind == "mechanism_executed"
        and "denied" in str(event.details.get("outcome_code"))
    )
    cues = _analyst_animation_cues(denied, result.core_result.final_state)
    assert cues[0]["kind"] == "mechanism_denied"
    assert cues[0]["event_id"] == denied.event_id


def test_analytical_boundary_is_temporal_reversible_and_evidence_linked(
    tmp_path: Path,
) -> None:
    body = TestClient(create_app(ROOT / "web", tmp_path)).post(
        "/api/runs",
        json={
            "scenario": "physical_access",
            "arm_id": "authorized_access",
            "execution": "scripted",
        },
    ).json()
    assert len(body["boundaries"]) == 1
    boundary = body["boundaries"][0]
    assert boundary["executor"] is False
    assert boundary["kind"] == "analytical_boundary"

    exact_edge_ids = {
        edge["id"] for edge in body["edges"] if edge["kind"] == "connection"
    }
    binding_edges = [
        edge for edge in body["edges"] if edge["kind"] == "mechanism_binding"
    ]
    assert binding_edges
    assert all(edge["target"].startswith("exact_") for edge in binding_edges)
    assert all(
        set(edge["exact_route_ids"]) <= exact_edge_ids for edge in binding_edges
    )
    location_edges = [
        edge for edge in body["edges"] if edge["kind"] == "information_location"
    ]
    assert any(
        edge["source"] == "technician"
        and edge["target"] == "technician_badge"
        for edge in location_edges
    )
    assert all(edge["exact_route_ids"] == [] for edge in location_edges)
    for revision, aggregate in boundary["snapshots"].items():
        exact_node_ids = {
            node["id"] for node in body["snapshots"][revision]
        }
        assert set(aggregate["member_ids"]) <= exact_node_ids
        route_sets = [
            set(aggregate["internal_route_ids"]),
            set(aggregate["inbound_route_ids"]),
            set(aggregate["outbound_route_ids"]),
        ]
        assert all(route_set <= exact_edge_ids for route_set in route_sets)
        assert not route_sets[0] & route_sets[1]
        assert not route_sets[0] & route_sets[2]
        assert not route_sets[1] & route_sets[2]

    initial = boundary["snapshots"]["0"]
    final_revision = str(body["timeline"][-1]["state_revision"])
    final = boundary["snapshots"][final_revision]
    assert not any(
        member_id.startswith("delivered_event_")
        for member_id in initial["member_ids"]
    )
    assert any(
        member_id.startswith("delivered_event_")
        for member_id in final["member_ids"]
    )
    linked_event_ids = {
        event["event_id"]
        for event in body["timeline"]
        if boundary["id"] in event["boundary_ids"]
    }
    assert set(boundary["trace_event_ids"]) == linked_event_ids


def test_analytical_boundary_never_enters_runtime_authority() -> None:
    from cybernetic_influence.scenarios.physical_access import (
        physical_access_arm_configurations,
        physical_access_fixture,
        physical_access_scripted_bindings,
        run_physical_access,
    )

    fixture = physical_access_fixture(physical_access_arm_configurations()[0])
    boundary = fixture.scenario.analytical_boundaries[0]
    boundary_id = boundary.boundary_id
    state = fixture.scenario.initial_state
    assert boundary_id not in state.entities
    assert boundary_id not in state.mechanisms
    assert boundary_id not in state.ports
    assert boundary_id not in state.carriers
    assert boundary_id not in state.connections
    assert all(port.owner_ref != boundary_id for port in state.ports.values())
    assert all(carrier.owner_ref != boundary_id for carrier in state.carriers.values())

    result = run_physical_access(
        fixture,
        physical_access_scripted_bindings(fixture),
        run_id="boundary_execution_inert_gate",
    )
    for event in result.core_result.events:
        assert event.actor_entity_id != boundary_id
        assert event.mechanism_id != boundary_id
        assert event.source_port_id != boundary_id
        assert event.target_port_id != boundary_id
        if event.patch is not None:
            assert boundary_id not in json.dumps(event.patch.model_dump(mode="json"))


def test_selected_revision_contains_no_future_world_state(tmp_path: Path) -> None:
    body = TestClient(create_app(ROOT / "web", tmp_path)).post(
        "/api/runs",
        json={"arm_id": "baseline", "execution": "scripted"},
    ).json()

    first_action = next(event for event in body["timeline"] if event["kind"] == "action_attempted")
    initial_nodes = body["snapshots"][str(first_action["state_revision"])]
    initial_incident = next(node for node in initial_nodes if node["id"] == "incident_17")
    assert initial_incident["state"]["status"]["value"] == "new"

    assignment_commit = next(
        event
        for event in body["timeline"]
        if event["kind"] == "state_committed"
        and "ticket_routing" in event["summary"]
    )
    assigned_nodes = body["snapshots"][str(assignment_commit["state_revision"])]
    assigned_incident = next(node for node in assigned_nodes if node["id"] == "incident_17")
    assert assigned_incident["state"]["status"]["value"] == "assigned"

    final_incident = next(node for node in body["nodes"] if node["id"] == "incident_17")
    assert final_incident["state"]["status"]["value"] == "closed_confirmed"


def test_timeline_events_link_to_exact_activation_not_only_time(tmp_path: Path) -> None:
    body = TestClient(create_app(ROOT / "web", tmp_path)).post(
        "/api/runs",
        json={"arm_id": "speed_priority", "execution": "scripted"},
    ).json()
    trace_activations = {trace["activation"] for trace in body["traces"]}
    for event in body["timeline"]:
        if event["activation"] is not None and not str(event["activation"]).startswith("exact_work_"):
            assert event["activation"] in trace_activations
    assert all(
        step["activation"] is not None
        for step in body["story"]["steps"]
    )


def test_realized_trajectory_is_a_typed_projection_of_the_exact_trace(
    tmp_path: Path,
) -> None:
    body = TestClient(create_app(ROOT / "web", tmp_path)).post(
        "/api/runs",
        json={"arm_id": "baseline", "execution": "scripted"},
    ).json()
    trajectory = body["trajectory"]
    assert {node["id"] for node in trajectory["nodes"]} == {
        event["event_id"] for event in body["timeline"]
    }
    by_id = {event["event_id"]: event for event in body["timeline"]}
    assert all(
        by_id[edge["target"]]["logical_time"]
        > by_id[edge["source"]]["logical_time"]
        for edge in trajectory["edges"]
        if by_id[edge["target"]]["kind"] != "run_completed"
    )
    timed = [node for node in trajectory["nodes"] if node["timing"] is not None]
    assert timed
    assert all(node["timing"]["duration"] > 0 for node in timed)
    assert all(node["timing"]["minimum_duration"] == 1 for node in timed)
    assert all(node["timing"]["serialization_delay"] >= 0 for node in timed)
    assert any(
        node["timing"]["serialization_delay"] > 0 for node in timed
    )


def test_narrative_is_derived_from_open_remediated_and_closed_outcomes() -> None:
    open_summary = service_desk_summary(
        "baseline",
        {
            "final_status": "assigned",
            "remediation_activation": None,
            "confirmed_closure_activation": None,
            "denied_closure_attempt_count": 0,
        },
    )
    assert "without remediation or confirmed closure" in open_summary
    assert "safely closed" not in open_summary

    remediated_summary = service_desk_summary(
        "no_direct_path",
        {
            "final_status": "remediated",
            "remediation_activation": 4,
            "confirmed_closure_activation": None,
            "denied_closure_attempt_count": 0,
        },
    )
    assert "without confirmed closure" in remediated_summary

    closed_summary = service_desk_summary(
        "speed_priority",
        {
            "final_status": "closed_confirmed",
            "remediation_activation": 1,
            "confirmed_closure_activation": 5,
            "denied_closure_attempt_count": 1,
        },
    )
    assert "safely closed after confirmation" in closed_summary
    assert "denied 1 premature closure attempt" in closed_summary


def test_mechanism_fact_changes_are_redacted_from_raw_event_projection() -> None:
    event = CausalEvent(
        run_id="protected_patch_gate",
        event_id="event_000001",
        sequence=1,
        event_kind="state_committed",
        logical_time=0,
        state_revision=1,
        causal_parent_event_ids=["event_000000"],
        summary="Committed protected state.",
        variance_source="exact",
        mechanism_id="exact_gate",
        effect_id="effect_000000",
        target_port_id="gate_input",
        patch=StatePatch(
            before_revision=0,
            after_revision=1,
            before_logical_time=0,
            after_logical_time=0,
            before_digest="a" * 64,
            after_digest="b" * 64,
            fact_changes=[
                FactChange(
                    fact_id="gate.verifier",
                    visibility="mechanism",
                    before="old-secret",
                    after="new-secret",
                )
            ],
        ),
    )
    projected = analyst_event(event)
    encoded = json.dumps(projected)
    assert "old-secret" not in encoded
    assert "new-secret" not in encoded
    patch = projected["patch"]
    assert isinstance(patch, dict)
    fact_changes = patch["fact_changes"]
    assert isinstance(fact_changes, list)
    change = fact_changes[0]
    assert isinstance(change, dict)
    assert change["before"] == "[redacted]"
    assert change["after"] == "[redacted]"
