"""Direct gates for exact mechanics, replay, and protected agent input."""

from __future__ import annotations

from dataclasses import replace
import json

import pytest

from cybernetic_influence.active_runtime import (
    ActiveSystemBinding,
    ActiveStepResult,
    ActiveSystemInput,
    ParticipantContractError,
    ScriptedActiveSystem,
    UpdateScheduleDirective,
)
from cybernetic_influence.active_runtime.llm import render_llm_prompts
from cybernetic_influence.causal_core.engine import (
    CausalSession,
    ExactMechanismBinding,
    MechanismContractError,
)
from cybernetic_influence.causal_core.fixtures import authentication_fixture
from cybernetic_influence.causal_core.models import (
    ActionAttempt,
    CausalState,
    MechanismOutcome,
    PlacementDraft,
)
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
    run_event_driven_service_desk,
    run_service_desk,
    service_desk_arm_configurations,
    service_desk_fixture,
    service_desk_personas,
    service_desk_scripted_bindings,
)


def _crossing_attempt_after_badge(
    session: CausalSession,
    *,
    action_prefix: str,
) -> ActionAttempt:
    """Advance through badge presentation and return the resulting crossing attempt."""
    session.advance(
        ActionAttempt(
            action_id=f"{action_prefix}_badge",
            actor_entity_id="technician",
            output_port_id="technician_badge_out",
            representation_id="technician_badge",
            public_summary="Technician presented a badge.",
        )
    )
    access_observation = next(
        observation
        for observation in session.state.observations.values()
        if observation.via_port_id == "technician_access_result_in"
    )
    return ActionAttempt(
        action_id=f"{action_prefix}_crossing",
        actor_entity_id="technician",
        output_port_id="technician_cross_out",
        representation_id=access_observation.representation_id,
        payload=CrossingRequest().model_dump(mode="json"),
        logical_time=1,
        public_summary="Technician attempted crossing.",
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
        multirate=False,
    )
    result = run_service_desk(
        fixture,
        service_desk_scripted_bindings(fixture),
        run_id="service_desk_replay_gate",
    )
    replayed = replay_committed_trajectory(fixture.scenario, result.core_result)
    assert replayed == result.core_result.final_state


def test_event_driven_service_desk_groups_simultaneous_triggers_from_one_state() -> None:
    fixture = service_desk_fixture(
        service_desk_arm_configurations()[0],
        cognition_profile="position_context",
        reasoning_effort="medium",
    )
    result = run_event_driven_service_desk(
        fixture,
        service_desk_scripted_bindings(fixture),
        run_id="service_desk_event_driven_gate",
    )
    joint = next(
        attempt
        for attempt in result.attempts
        if attempt.declared_active_system_ids == ["supervisor", "triager"]
    )
    assert joint.declared_active_system_ids == ["supervisor", "triager"]
    observations = {
        participant.requested_active_system_id: {
            observation.via_port_id
            for observation in participant.input.observations
        }
        for participant in joint.participants
    }
    assert observations == {
        "supervisor": {"supervisor_remediation_in"},
        "triager": {"triager_customer_feedback_in"},
    }
    assert all(
        participant.input.activation_id == joint.activation_id
        and participant.input.logical_time == joint.logical_time
        for participant in joint.participants
    )
    autonomous_joint = next(
        attempt
        for attempt in result.attempts
        if attempt.declared_active_system_ids
        == ["remediation_process", "triager"]
    )
    assert autonomous_joint.logical_time == 1
    assert all(
        participant.input.observations == []
        and [
            cause.kind for cause in participant.input.activation_causes
        ]
        == ["internal_wake"]
        for participant in autonomous_joint.participants
    )
    assert len(
        {
            participant.input.logical_time
            for participant in autonomous_joint.participants
        }
    ) == 1
    process_attempts = [
        participant
        for attempt in result.attempts
        for participant in attempt.participants
        if participant.requested_active_system_id
        == "remediation_process"
    ]
    assert len(process_attempts) == 3
    assert all(not participant.call_evidence for participant in process_attempts)
    assert result.final_states["remediation_process"].next_update_at is None
    assert result.core_result.final_state.fact(
        "incident_17.status"
    ).value == "closed_confirmed"


def test_multirate_scheduler_rejects_nonfuture_process_update() -> None:
    fixture = service_desk_fixture(
        service_desk_arm_configurations()[0],
        cognition_profile="position_context",
        reasoning_effort="medium",
    )
    bindings = service_desk_scripted_bindings(fixture)
    original = bindings["triager"]

    def bad_schedule(active_input: ActiveSystemInput) -> ActiveStepResult:
        result = ActiveStepResult.model_validate(
            original.implementation.step(active_input)
        )
        proposal = result.proposal.model_copy(
            update={
                "update_schedule": UpdateScheduleDirective(
                    mode="schedule",
                    next_update_at=0,
                )
            }
        )
        return result.model_copy(update={"proposal": proposal})

    bindings["triager"] = ActiveSystemBinding(
        original.implementation_id,
        ScriptedActiveSystem(
            original.implementation_id,
            bad_schedule,
        ),
    )
    with pytest.raises(
        ParticipantContractError,
        match="scheduled a non-future update",
    ):
        run_event_driven_service_desk(
            fixture,
            bindings,
            run_id="service_desk_bad_internal_schedule",
        )
def test_future_delivery_waits_for_its_recorded_arrival_time() -> None:
    fixture = service_desk_fixture(
        service_desk_arm_configurations()[0],
        cognition_profile="position_context",
        reasoning_effort="medium",
    )
    scenario = fixture.scenario.model_copy(deep=True)
    scenario.initial_state.connections[
        "specialist_to_remediation"
    ].delay = 5
    delayed_fixture = replace(fixture, scenario=scenario)
    result = run_event_driven_service_desk(
        delayed_fixture,
        service_desk_scripted_bindings(delayed_fixture),
        run_id="service_desk_delayed_remediation",
    )
    first_process = next(
        participant
        for attempt in result.attempts
        for participant in attempt.participants
        if participant.requested_active_system_id
        == "remediation_process"
    )
    assert first_process.input.logical_time == 5
    assert [
        observation.logical_time
        for observation in first_process.input.observations
    ] == [5]
    assert all(
        observation.logical_time <= participant.input.logical_time
        for attempt in result.attempts
        for participant in attempt.participants
        for observation in participant.input.observations
    )


def test_mechanism_credentials_do_not_enter_agent_prompts() -> None:
    fixture = service_desk_fixture(
        service_desk_arm_configurations()[0],
        cognition_profile="position_context",
        reasoning_effort="medium",
        multirate=False,
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


def test_physical_crossing_commits_one_replayable_spatial_change() -> None:
    fixture = physical_access_fixture(physical_access_arm_configurations()[0])
    result = run_physical_access(
        fixture,
        physical_access_scripted_bindings(fixture),
        run_id="physical_spatial_change_gate",
    )
    placement_changes = [
        change
        for event in result.core_result.events
        if event.patch is not None
        for change in event.patch.placement_changes
    ]
    assert [
        (
            change.entity_id,
            change.before_place_id,
            change.after_place_id,
            change.via_spatial_link_id,
        )
        for change in placement_changes
    ] == [
        (
            "technician",
            "hallway",
            "equipment_room",
            "equipment_room_threshold",
        )
    ]
    assert (
        result.core_result.final_state.placements["technician"].place_id
        == "equipment_room"
    )
    assert (
        replay_committed_trajectory(fixture.scenario, result.core_result)
        == result.core_result.final_state
    )

    for arm in physical_access_arm_configurations()[1:]:
        denied_fixture = physical_access_fixture(arm)
        denied = run_physical_access(
            denied_fixture,
            physical_access_scripted_bindings(denied_fixture),
            run_id=f"physical_no_spatial_change_{arm.arm_id}",
        )
        assert (
            denied.core_result.final_state.placements["technician"].place_id
            == "hallway"
        )
        assert not any(
            event.patch is not None and event.patch.placement_changes
            for event in denied.core_result.events
        )


def test_spatial_contract_rejects_cycles_and_unknown_links() -> None:
    fixture = physical_access_fixture(physical_access_arm_configurations()[0])
    cyclic_state = fixture.scenario.initial_state.model_copy(deep=True)
    cyclic_state.places["maintenance_facility"].parent_place_id = "hallway"
    with pytest.raises(ValueError, match="containment contains a cycle"):
        CausalState.model_validate(cyclic_state.model_dump(mode="json"))

    unknown_link_state = fixture.scenario.initial_state.model_copy(deep=True)
    unknown_link_state.mechanisms[
        "exact_threshold_crossing"
    ].read_spatial_link_ids.append("missing_threshold")
    with pytest.raises(ValueError, match="unknown readable spatial links"):
        CausalState.model_validate(unknown_link_state.model_dump(mode="json"))


@pytest.mark.parametrize(
    ("destination_place_id", "spatial_link_id", "error"),
    [
        ("equipment_room", "undeclared_link", "undeclared spatial link"),
        (
            "maintenance_facility",
            "equipment_room_threshold",
            "does not cross the declared spatial link",
        ),
    ],
)
def test_spatial_contract_rejects_forged_crossing_geometry(
    destination_place_id: str,
    spatial_link_id: str,
    error: str,
) -> None:
    fixture = physical_access_fixture(physical_access_arm_configurations()[0])
    original = fixture.exact_bindings["exact_threshold_crossing"]
    bindings = dict(fixture.exact_bindings)
    bindings["exact_threshold_crossing"] = ExactMechanismBinding(
        implementation_id=original.implementation_id,
        handler=lambda context: MechanismOutcome(
            outcome_code="forged_crossing",
            placement_updates=[
                PlacementDraft(
                    entity_id="technician",
                    destination_place_id=destination_place_id,
                    via_spatial_link_id=spatial_link_id,
                )
            ],
        ),
        invariant_checkers=original.invariant_checkers,
    )
    session = CausalSession(
        fixture.scenario,
        bindings,
        run_id=f"forged_spatial_geometry_{spatial_link_id}",
    )
    crossing_attempt = _crossing_attempt_after_badge(
        session,
        action_prefix=f"forged_{spatial_link_id}",
    )
    with pytest.raises(MechanismContractError, match=error):
        session.advance(crossing_attempt)
    assert session.state.placements["technician"].place_id == "hallway"


def test_spatial_contract_rejects_undeclared_placement_write() -> None:
    fixture = physical_access_fixture(physical_access_arm_configurations()[0])
    scenario = fixture.scenario.model_copy(deep=True)
    scenario.initial_state.mechanisms[
        "exact_threshold_crossing"
    ].write_placement_entity_ids = []
    session = CausalSession(
        scenario,
        fixture.exact_bindings,
        run_id="undeclared_placement_write_gate",
    )
    crossing_attempt = _crossing_attempt_after_badge(
        session,
        action_prefix="undeclared_placement_write",
    )
    with pytest.raises(
        MechanismContractError,
        match="undeclared placement writes",
    ):
        session.advance(crossing_attempt)
    assert session.state.placements["technician"].place_id == "hallway"


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
    assert session.state.placements["technician"].place_id == "hallway"
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
