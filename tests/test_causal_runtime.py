"""Direct gates for exact mechanics, replay, and protected agent input."""

from __future__ import annotations

import json

import pytest

from cybernetic_influence.active_runtime.llm import render_llm_prompts
from cybernetic_influence.causal_core.engine import CausalSession
from cybernetic_influence.causal_core.fixtures import authentication_fixture
from cybernetic_influence.causal_core.models import ActionAttempt
from cybernetic_influence.causal_core.projection import project_graph
from cybernetic_influence.causal_core.replay import replay_committed_trajectory
from cybernetic_influence.scenarios.physical_access import (
    CrossingRequest,
    TECHNICIAN_PERSONA,
    build_physical_access_readout,
    physical_access_arm_configurations,
    physical_access_fixture,
    physical_access_scripted_bindings,
    run_physical_access,
)
from cybernetic_influence.scenarios.service_desk import (
    run_service_desk,
    service_desk_arm_configurations,
    service_desk_fixture,
    service_desk_personas,
    service_desk_scripted_bindings,
)


def test_exact_authentication_accepts_equality_and_rejects_inequality() -> None:
    accepted = authentication_fixture(candidate="correct_horse_battery").run(
        run_id="authentication_accepted"
    )
    assert accepted.final_state.fact("auth_service.session_active").value is True
    assert accepted.final_state.fact("auth_service.failure_count").value == 0

    denied = authentication_fixture(candidate="wrong").run(
        run_id="authentication_denied"
    )
    assert denied.final_state.fact("auth_service.session_active").value is False
    assert denied.final_state.fact("auth_service.failure_count").value == 1


def test_service_desk_replay_reconstructs_exact_final_state() -> None:
    fixture = service_desk_fixture(
        service_desk_arm_configurations()[0],
        cognition_profile="position_context",
        reasoning_effort="medium",
    )
    result = run_service_desk(
        fixture,
        service_desk_scripted_bindings(fixture),
        run_id="service_desk_replay_gate",
    )
    replayed = replay_committed_trajectory(fixture.scenario, result.core_result)
    assert replayed == result.core_result.final_state


def test_mechanism_credentials_do_not_enter_agent_prompts() -> None:
    fixture = service_desk_fixture(
        service_desk_arm_configurations()[0],
        cognition_profile="position_context",
        reasoning_effort="medium",
    )
    result = run_service_desk(
        fixture,
        service_desk_scripted_bindings(fixture),
        run_id="service_desk_prompt_gate",
    )
    personas = service_desk_personas("position_context")
    for attempt in result.attempts:
        for participant in attempt.participants:
            system, user = render_llm_prompts(
                participant.input,
                persona=personas[participant.requested_active_system_id],
            )
            rendered = system + user
            assert "triager_route_key_17" not in rendered
            assert "supervisor_close_key_17" not in rendered


def test_physical_access_separates_policy_and_physical_capability() -> None:
    readouts = {}
    for arm in physical_access_arm_configurations():
        fixture = physical_access_fixture(arm)
        result = run_physical_access(
            fixture,
            physical_access_scripted_bindings(fixture),
            run_id=f"physical_{arm.arm_id}",
        )
        readouts[arm.arm_id] = build_physical_access_readout(result)
        assert (
            replay_committed_trajectory(fixture.scenario, result.core_result)
            == result.core_result.final_state
        )

    assert readouts["authorized_access"].entered is True
    assert readouts["authorization_absent"].authentication == "authenticated"
    assert readouts["authorization_absent"].authorization == "denied_policy"
    assert readouts["authorization_absent"].entered is False
    assert readouts["latch_jammed"].authorization == "authorized"
    assert readouts["latch_jammed"].latch_result == "denied_latch_jammed"
    assert readouts["latch_jammed"].entered is False


def test_policy_is_a_declared_representation_read_and_badge_stays_out_of_prompt() -> None:
    fixture = physical_access_fixture(physical_access_arm_configurations()[0])
    result = run_physical_access(
        fixture,
        physical_access_scripted_bindings(fixture),
        run_id="physical_policy_read_gate",
    )
    authorization_event = next(
        event
        for event in result.core_result.events
        if event.mechanism_id == "exact_policy_authorization"
        and event.event_kind == "mechanism_executed"
    )
    assert authorization_event.read_representation_ids == ["access_policy_copy"]

    for attempt in result.attempts:
        participant = attempt.participants[0]
        system, user = render_llm_prompts(
            participant.input,
            persona=TECHNICIAN_PERSONA,
        )
        assert "equipment_badge_key_41" not in system + user

    graph = project_graph(fixture.scenario, result.core_result)
    graph_json = graph.model_dump(mode="json")
    assert "equipment_badge_key_41" not in json.dumps(graph_json)
    badge_node = next(
        node
        for node in graph_json["nodes"]
        if node["node_id"] == "representation:technician_badge"
    )
    assert badge_node["properties"]["redacted"] is True
    assert "content_hash" not in badge_node["properties"]
    assert any(
        edge["edge_kind"] == "reads_representation"
        and edge["target_node_id"] == "representation:access_policy_copy"
        for edge in graph_json["edges"]
    )


def test_crossing_attempt_cannot_turn_policy_denial_into_physical_entry() -> None:
    fixture = physical_access_fixture(physical_access_arm_configurations()[1])
    session = CausalSession(
        fixture.scenario,
        fixture.exact_bindings,
        run_id="forced_crossing_gate",
    )
    session.advance(
        ActionAttempt(
            action_id="present_badge",
            actor_entity_id="technician",
            output_port_id="technician_badge_out",
            representation_id="technician_badge",
            public_summary="Technician presented a badge.",
        )
    )
    state = session.state
    access_observation = next(
        observation
        for observation in state.observations.values()
        if observation.via_port_id == "technician_access_result_in"
    )
    assert access_observation.representation_id is not None
    session.advance(
        ActionAttempt(
            action_id="force_crossing",
            actor_entity_id="technician",
            output_port_id="technician_cross_out",
            representation_id=access_observation.representation_id,
            payload=CrossingRequest().model_dump(mode="json"),
            logical_time=1,
            public_summary="Technician attempted crossing after denial.",
        )
    )
    assert session.state.fact("technician.location").value == "hallway"
    assert any(
        "crossing_denied" in event.summary
        for event in session.events
        if event.event_kind == "mechanism_executed"
    )


def test_forged_badge_cannot_inherit_policy_authorization() -> None:
    fixture = physical_access_fixture(
        physical_access_arm_configurations()[0],
        badge_candidate="forged_badge",
    )
    result = run_physical_access(
        fixture,
        physical_access_scripted_bindings(fixture),
        run_id="forged_badge_gate",
    )
    readout = build_physical_access_readout(result)
    assert readout.authentication == "denied"
    assert readout.authorization == "denied_authentication"
    assert readout.latch_result == "denied_authentication"
    assert readout.entered is False

    broken_state = fixture.scenario.initial_state.model_copy(deep=True)
    del broken_state.representations["access_policy_copy"]
    with pytest.raises(
        ValueError,
        match="unknown readable representations",
    ):
        broken_state.__class__.model_validate(
            broken_state.model_dump(mode="json")
        )
