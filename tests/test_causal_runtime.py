"""Direct gates for exact mechanics, replay, and protected agent input."""

from __future__ import annotations

from dataclasses import replace
import json

import pytest

from cybernetic_influence.active_runtime import (
    ActiveBudgetError,
    ActiveRuntimeCheckpoint,
    ActiveRuntimeConfig,
    ActiveSystemBinding,
    ActiveStepResult,
    ActiveSystemInput,
    ParticipantContractError,
    ModelCallEvidence,
    ScriptedActiveSystem,
    UpdateScheduleDirective,
)
from cybernetic_influence.active_runtime.llm import render_llm_prompts
from cybernetic_influence.api import _checkpoint_progress_projection
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
    canonical_record_digest,
)
from cybernetic_influence.causal_core.projection import project_graph
from cybernetic_influence.presentation import (
    analyst_moments,
    analyst_timeline,
    _temporal_states,
)
from cybernetic_influence.causal_core.replay import replay_committed_trajectory
from cybernetic_influence.scenarios.physical_access import (
    CrossingRequest,
    TECHNICIAN_PERSONA,
    build_physical_access_readout,
    physical_access_arm_configurations,
    physical_access_fixture,
    physical_access_native_bindings,
    physical_access_scripted_bindings,
    run_physical_access,
)
from cybernetic_influence.scenarios.service_desk import (
    RuntimePaused,
    run_event_driven_service_desk,
    run_service_desk,
    service_desk_arm_configurations,
    service_desk_fixture,
    service_desk_native_bindings,
    service_desk_personas,
    service_desk_scripted_bindings,
)
from cybernetic_influence.scenarios.purchase_payment import (
    purchase_payment_arm_configurations,
    purchase_payment_fixture,
    purchase_payment_native_bindings,
)


ALTERNATE_MODEL = "openrouter/deepseek/deepseek-v4-flash"


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


def test_nondefault_model_is_bound_into_every_scenario_implementation_id() -> None:
    service = service_desk_fixture(
        service_desk_arm_configurations()[0],
        cognition_profile="position_context",
        model=ALTERNATE_MODEL,
        reasoning_effort="medium",
    )
    physical = physical_access_fixture(
        physical_access_arm_configurations()[0],
        model=ALTERNATE_MODEL,
        reasoning_effort="medium",
    )
    purchase = purchase_payment_fixture(
        purchase_payment_arm_configurations()[0],
        model=ALTERNATE_MODEL,
        reasoning_effort="medium",
    )
    registries = [
        (
            service.active_specs,
            service_desk_native_bindings(
                service,
                trace_id_prefix="alternate-service",
                model=ALTERNATE_MODEL,
                reasoning_effort="medium",
            ),
        ),
        (
            physical.active_specs,
            physical_access_native_bindings(
                physical,
                trace_id_prefix="alternate-physical",
                model=ALTERNATE_MODEL,
                reasoning_effort="medium",
            ),
        ),
        (
            purchase.active_specs,
            purchase_payment_native_bindings(
                purchase,
                trace_id_prefix="alternate-purchase",
                model=ALTERNATE_MODEL,
                reasoning_effort="medium",
            ),
        ),
    ]
    assert all(
        bindings[spec.active_system_id].implementation_id
        == spec.implementation_id
        for specs, bindings in registries
        for spec in specs
    )


def test_provider_call_requires_full_ceiling_but_retains_prior_spend() -> None:
    fixture = physical_access_fixture(
        physical_access_arm_configurations()[0]
    )
    scripted = physical_access_scripted_bindings(fixture)["technician"]
    calls = 0

    class CostedProvider:
        implementation_id = scripted.implementation_id
        provider_bound = True

        def step(self, active_input: ActiveSystemInput) -> ActiveStepResult:
            nonlocal calls
            calls += 1
            result = ActiveStepResult.model_validate(
                scripted.implementation.step(active_input)
            )
            evidence = ModelCallEvidence(
                status="completed",
                trace_id=f"budget-test/{calls}",
                model="test/provider",
                task="budget_test",
                reasoning_effort="medium",
                system_prompt="test system",
                user_prompt="test user",
                structured_output={"orientation": "test"},
                cost=0.01,
                cost_source="test",
            )
            return result.model_copy(update={"call_evidence": [evidence]})

    checkpoints: list[ActiveRuntimeCheckpoint] = []
    with pytest.raises(
        ActiveBudgetError,
        match="cannot fit per-call ceiling",
    ):
        run_physical_access(
            fixture,
            {
                "technician": ActiveSystemBinding(
                    scripted.implementation_id,
                    CostedProvider(),
                )
            },
            run_id="budget_admission_gate",
            runtime_config=ActiveRuntimeConfig(
                per_call_budget=0.05,
                per_run_budget=0.055,
                max_actions_per_system=1,
                max_observations_per_system=8,
                max_private_state_bytes=16_384,
            ),
            checkpoint_observer=checkpoints.append,
        )
    assert calls == 1
    assert checkpoints[-1].total_observed_cost == pytest.approx(0.01)
    assert checkpoints[-1].attempts[0].status == "committed"
    assert checkpoints[-1].attempts[-1].status == "failed"
    progress = _checkpoint_progress_projection(checkpoints[-1])
    assert progress["model_calls"] == 1
    assert progress["cost"] == pytest.approx(0.01)
    assert progress["progress"] == {
        "completed_attempts": 1,
        "failed_attempts": 1,
        "logical_time": 0,
    }


def test_event_driven_service_desk_preserves_frozen_due_sets_with_positive_time() -> None:
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
        if attempt.declared_active_system_ids == ["specialist", "supervisor"]
    )
    assert joint.declared_active_system_ids == ["specialist", "supervisor"]
    observations = {
        participant.requested_active_system_id: {
            observation.via_port_id
            for observation in participant.input.observations
        }
        for participant in joint.participants
    }
    assert observations == {
        "specialist": {"specialist_ticket_details_in"},
        "supervisor": {"supervisor_remediation_in"},
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
    assert autonomous_joint.logical_time > 0
    process = next(
        participant
        for participant in autonomous_joint.participants
        if participant.requested_active_system_id == "remediation_process"
    )
    triager = next(
        participant
        for participant in autonomous_joint.participants
        if participant.requested_active_system_id == "triager"
    )
    assert process.input.observations == []
    assert [cause.kind for cause in process.input.activation_causes] == ["internal_wake"]
    assert {observation.via_port_id for observation in triager.input.observations} == {
        "triager_detail_request_in"
    }
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
    world_events = [
        event
        for event in result.core_result.events
        if event.event_kind not in {"run_started", "run_completed"}
    ]
    by_id = {event.event_id: event for event in result.core_result.events}
    assert all(
        event.logical_time > max(by_id[parent].logical_time for parent in event.causal_parent_event_ids)
        for event in world_events
    )
    for event in world_events:
        timing = event.details.get("timing")
        assert isinstance(timing, dict)
        duration = timing.get("duration")
        assert isinstance(duration, int)
        assert duration > 0


def test_event_driven_service_desk_resumes_one_validated_prefix_without_duplicates() -> None:
    fixture = service_desk_fixture(
        service_desk_arm_configurations()[0],
        cognition_profile="position_context",
        reasoning_effort="medium",
    )
    bindings = service_desk_scripted_bindings(fixture)
    observed: list[ActiveRuntimeCheckpoint] = []

    with pytest.raises(RuntimePaused) as paused:
        run_event_driven_service_desk(
            fixture,
            bindings,
            run_id="service_desk_pause_resume_gate",
            checkpoint_observer=observed.append,
            pause_requested=lambda: len(observed) == 3,
        )

    checkpoint = paused.value.checkpoint
    assert checkpoint == observed[-1]
    assert len(checkpoint.attempts) == 3

    resumed = run_event_driven_service_desk(
        fixture,
        bindings,
        run_id="service_desk_pause_resume_gate",
        checkpoint=checkpoint,
    )
    uninterrupted = run_event_driven_service_desk(
        fixture,
        bindings,
        run_id="service_desk_pause_resume_reference",
    )

    assert [attempt.activation_id for attempt in resumed.attempts] == [
        attempt.activation_id for attempt in uninterrupted.attempts
    ]
    assert [event.event_id for event in resumed.core_result.events] == [
        event.event_id for event in uninterrupted.core_result.events
    ]
    assert resumed.core_result.final_state == uninterrupted.core_result.final_state


def test_event_driven_checkpoint_retains_future_route_work() -> None:
    fixture = service_desk_fixture(
        service_desk_arm_configurations()[0],
        cognition_profile="position_context",
        reasoning_effort="medium",
    )
    scenario = fixture.scenario.model_copy(deep=True)
    scenario.initial_state.connections["routing_to_specialist"].delay = 300
    scenario.initial_state.connections["triager_direct_to_specialist"].delay = 300
    delayed_fixture = replace(fixture, scenario=scenario)
    bindings = service_desk_scripted_bindings(delayed_fixture)

    observed: list[ActiveRuntimeCheckpoint] = []
    with pytest.raises(RuntimePaused) as paused:
        run_event_driven_service_desk(
            delayed_fixture,
            bindings,
            run_id="service_desk_pending_route_checkpoint",
            checkpoint_observer=observed.append,
            pause_requested=lambda: len(observed) == 2,
        )

    checkpoint = paused.value.checkpoint
    scheduled_work = checkpoint.core_checkpoint.scheduled_work
    assert scheduled_work
    assert {item.due_at for item in scheduled_work} == {2, 4}
    assert all(item.work_kind == "effect" for item in scheduled_work)

    resumed = run_event_driven_service_desk(
        delayed_fixture,
        bindings,
        run_id="service_desk_pending_route_checkpoint",
        checkpoint=checkpoint,
    )
    specialist_attempt = next(
        participant
        for attempt in resumed.attempts
        for participant in attempt.participants
        if participant.requested_active_system_id == "specialist"
    )
    assert specialist_attempt.input.logical_time == 307
    assert resumed.core_result.final_state.fact("incident_17.status").value == "closed_confirmed"
    timeline = analyst_timeline(
        resumed,
        _temporal_states(delayed_fixture.scenario.initial_state, resumed.core_result.events),
    )
    moments = analyst_moments(resumed, timeline)
    assert any(
        moment["activation"] == "exact_work_000000"
        and moment["logical_time"] == 2
        and moment["participants"] == ["exact_mechanisms"]
        for moment in moments
    )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("target_port_id", "triager_detail_request_in", "incompatible ports"),
        ("route_delay", 17, "connection"),
        ("due_at", 17, "due time"),
    ],
)
def test_restore_rejects_tampered_pending_delivery_topology(
    field: str, value: object, message: str
) -> None:
    fixture = service_desk_fixture(
        service_desk_arm_configurations()[0],
        cognition_profile="position_context",
        reasoning_effort="medium",
    )
    scenario = fixture.scenario.model_copy(deep=True)
    scenario.initial_state.connections["routing_to_specialist"].delay = 300
    scenario.initial_state.connections["triager_direct_to_specialist"].delay = 300
    delayed_fixture = replace(fixture, scenario=scenario)
    observed: list[ActiveRuntimeCheckpoint] = []
    exact = CausalSession(
        delayed_fixture.scenario,
        delayed_fixture.exact_bindings,
        run_id="service_desk_tampered_route_checkpoint",
    )
    exact.advance(
        ActionAttempt(
            action_id="tampered_route_action",
            actor_entity_id="triager",
            output_port_id="triager_route_out",
            representation_id="triager_routing_credential",
            payload={},
            logical_time=0,
            public_summary="Triager attempted authenticated ticket assignment.",
        ),
        drain_through=6,
    )
    payload = exact.checkpoint().model_dump(mode="json")
    payload["scheduled_work"][0][field] = value
    if field == "due_at":
        payload["scheduled_work"][0]["effect"]["logical_time"] = value
    payload.pop("record_digest")
    payload["record_digest"] = canonical_record_digest(payload)
    corrupt = type(exact.checkpoint()).model_validate(payload)

    with pytest.raises(ValueError, match=message):
        CausalSession.restore(
            delayed_fixture.scenario,
            delayed_fixture.exact_bindings,
            corrupt,
        )


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
    remediation_route = next(
        event
        for event in result.core_result.events
        if event.connection_id == "specialist_to_remediation"
    )
    emission = next(
        event
        for event in result.core_result.events
        if event.event_id == remediation_route.causal_parent_event_ids[0]
    )
    assert remediation_route.logical_time - emission.logical_time >= 5
    assert [
        observation.logical_time
        for observation in first_process.input.observations
    ] == [first_process.input.logical_time]
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
