"""Packet 21A0 contract and both-sign fixtures."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import replace
from typing import Any

import pytest
from pydantic import ValidationError

from cybernetic_influence.active_runtime import ActiveRuntimeCheckpoint
from cybernetic_influence.causal_core.models import state_digest
from cybernetic_influence.causal_core.replay import replay_committed_trajectory

from cybernetic_influence.scenarios.coordination_decision import (
    CONDITION_ENTITY_ID,
    DECISION_DEADLINE_DAY,
    DECISION_DEADLINE_TIME,
    EXTERNAL_RECEIVER_ID,
    MAX_CAUSAL_MOMENTS,
    MAX_PARTICIPANT_CALLS,
    MEETING_DAYS,
    MEETING_TIMES,
    PARTNERSHIP_BOUNDARY_ID,
    PERSON_IDS,
    PRESSURE_SOURCE_CARRIER_IDS,
    PRESSURE_SOURCE_IDS,
    PRESSURE_SOURCE_REPRESENTATION_IDS,
    SCENARIO_ID,
    SOURCE_BOUNDARY_ID,
    CommitmentRecord,
    COORDINATION_PERSON_DECISION_MODELS,
    CoordinationLlmDecision,
    CoordinationConditionConfig,
    CoordinationDecisionFixture,
    CoordinationRuntimePaused,
    DecisionProposal,
    IssueItem,
    LlmTerminalProposalPayload,
    MeetingSchedule,
    MeetingSlot,
    SourceDispositionRecord,
    VerificationItem,
    baseline_coordination_fixture,
    condition_independent_scenario_dump,
    coordination_decision_fixtures,
    coordination_native_bindings,
    coordination_runtime_fixture,
    heterogeneous_pressure_coordination_fixture,
    run_scripted_coordination,
    scenario_fingerprint,
    stabilization_coordination_fixture,
    validate_coordination_fixture_family,
    _normalized_coordination_payload,
)


def test_live_coordination_binds_only_people_to_provider_cognition() -> None:
    model = "openrouter/deepseek/deepseek-v4-flash"
    runtime = coordination_runtime_fixture(
        baseline_coordination_fixture(),
        model=model,
        reasoning_effort="none",
    )
    bindings = coordination_native_bindings(
        runtime,
        trace_id_prefix="coordination_live_contract",
        model=model,
        reasoning_effort="none",
    )

    assert all(
        bindings[person_id].implementation.provider_bound for person_id in PERSON_IDS
    )
    assert all(
        not bindings[process_id].implementation.provider_bound
        for process_id in (*PRESSURE_SOURCE_IDS, "meeting_clock")
    )
    assert {
        spec.active_system_id: spec.implementation_id
        for spec in runtime.active_specs
    } == {
        active_system_id: binding.implementation_id
        for active_system_id, binding in bindings.items()
    }


def test_live_coordination_terminal_action_retains_structured_gate_inputs() -> None:
    decision = CoordinationLlmDecision.model_validate(
        {
            "orientation": "The reviewed evidence and commitments support a decision.",
            "memory_update": "Retain the proposed terminal decision.",
            "actions": [
                {
                    "output_port_id": "terminal_proposal_out",
                    "representation_id": None,
                    "payload": {
                        "requested_status": "deploy_on_time",
                        "requested_scope": "full",
                        "evidence_refs": ["independent_calibration_response"],
                        "acknowledged_issue_ids": ["oversight_review"],
                        "active_partner_ids": list(PERSON_IDS),
                    },
                    "public_summary": "The coordinator proposed full deployment.",
                }
            ],
            "silence_reason": None,
        }
    )

    payload = decision.actions[0].payload
    assert isinstance(payload, LlmTerminalProposalPayload)
    assert payload.evidence_refs == ["independent_calibration_response"]
    assert payload.active_partner_ids == list(PERSON_IDS)
    normalized = _normalized_coordination_payload(
        "mission_coordinator",
        "terminal_proposal_out",
        payload.model_dump(mode="json"),
    )
    assert DecisionProposal.model_validate(normalized).proposed_by == (
        "mission_coordinator"
    )


def test_live_schema_rejects_simulator_owned_actor_identity() -> None:
    coordinator_model = COORDINATION_PERSON_DECISION_MODELS["mission_coordinator"]

    with pytest.raises(ValidationError):
        coordinator_model.model_validate(
            {
                "orientation": "The reviewed commitments support a proposal.",
                "memory_update": "Retain the reviewed proposal.",
                "actions": [
                    {
                        "output_port_id": "terminal_proposal_out",
                        "representation_id": None,
                        "payload": {
                            "proposal_id": "model_chosen_id",
                            "proposed_by": "partner_representative",
                            "requested_status": "scope_reduced",
                            "requested_scope": "reduced",
                            "evidence_refs": [],
                            "acknowledged_issue_ids": [],
                            "active_partner_ids": list(PERSON_IDS),
                        },
                        "public_summary": "The coordinator proposed reduced scope.",
                    }
                ],
                "silence_reason": None,
            }
        )


def test_live_person_schema_rejects_an_interface_owned_by_someone_else() -> None:
    partner_model = COORDINATION_PERSON_DECISION_MODELS["partner_representative"]

    with pytest.raises(ValidationError):
        partner_model.model_validate(
            {
                "orientation": "The group would benefit from another message.",
                "memory_update": "Retain the discussion.",
                "actions": [
                    {
                        "output_port_id": "alignment_message_out",
                        "representation_id": None,
                        "payload": {
                            "sender_id": "partner_representative",
                            "content": "Continue review.",
                        },
                        "public_summary": "The partner sent an alignment message.",
                    }
                ],
                "silence_reason": None,
            }
        )


def test_contract_three_arm_family_differs_only_by_reviewed_condition() -> None:
    fixtures = coordination_decision_fixtures()

    assert [fixture.condition.condition for fixture in fixtures] == [
        "baseline",
        "heterogeneous_pressure",
        "stabilization",
    ]
    assert len(
        {
            condition_independent_scenario_dump(fixture.scenario)
            for fixture in fixtures
        }
    ) == 1
    assert len({scenario_fingerprint(fixture.scenario) for fixture in fixtures}) == 3
    assert all(fixture.scenario.scenario_id == SCENARIO_ID for fixture in fixtures)


@pytest.mark.parametrize(
    ("builder", "expected_flags"),
    [
        (
            baseline_coordination_fixture,
            (False, False, False, False, False, False),
        ),
        (
            heterogeneous_pressure_coordination_fixture,
            (True, True, False, False, False, False),
        ),
        (
            stabilization_coordination_fixture,
            (True, True, True, True, True, True),
        ),
    ],
)
def test_contract_condition_is_compiled_without_deleting_world_components(
    builder: Callable[[], CoordinationDecisionFixture],
    expected_flags: tuple[bool, bool, bool, bool, bool, bool],
) -> None:
    fixture = builder()
    config = fixture.condition
    assert (
        config.pressure_sources_enabled,
        config.adaptive_follow_up_enabled,
        config.authoritative_validation_enabled,
        config.evidence_based_risk_admission_enabled,
        config.uncertainty_bounds_enabled,
        config.commitment_feedback_enabled,
    ) == expected_flags
    assert set(PRESSURE_SOURCE_IDS) <= set(fixture.scenario.initial_state.entities)
    assert set(PRESSURE_SOURCE_CARRIER_IDS) <= set(
        fixture.scenario.initial_state.carriers
    )
    assert set(PRESSURE_SOURCE_REPRESENTATION_IDS) <= set(
        fixture.scenario.initial_state.representations
    )
    condition_entity = fixture.scenario.initial_state.entities[CONDITION_ENTITY_ID]
    assert condition_entity.entity_kind == "mechanism_configuration"
    assert all(
        fact.visibility == "mechanism"
        for fact in condition_entity.attributes.values()
    )


def test_contract_people_schedule_topology_and_safety_bounds_are_reviewed() -> None:
    fixture = baseline_coordination_fixture()
    state = fixture.scenario.initial_state
    people = {
        entity_id
        for entity_id, entity in state.entities.items()
        if entity.entity_kind == "person"
    }

    assert people == set(PERSON_IDS)
    assert tuple(slot.modeled_day for slot in fixture.schedule.slots) == MEETING_DAYS
    assert all(tuple(slot.due_person_ids) == PERSON_IDS for slot in fixture.schedule.slots)
    assert fixture.schedule.deadline_day == DECISION_DEADLINE_DAY
    assert fixture.scenario.time_unit == "scenario_minute"
    assert fixture.scenario.timing_contract == "positive_duration"
    assert all(connection.delay > 0 for connection in state.connections.values())
    assert state.representations["technical_validation_dossier_copy"].carrier_id == (
        "dossier_carrier"
    )
    assert fixture.run_control_options.default_horizon == DECISION_DEADLINE_TIME
    assert fixture.run_control_options.max_causal_moments_cap == MAX_CAUSAL_MOMENTS
    assert fixture.run_control_options.max_participant_calls_cap == (
        MAX_PARTICIPANT_CALLS
    )
    assert {
        placement.place_id for placement in state.placements.values()
    } == {
        "partnership_hub",
        "source_operations_site",
        "external_registry_site",
    }


def test_contract_boundaries_are_execution_inert_and_have_reviewed_membership() -> None:
    fixture = baseline_coordination_fixture()
    state = fixture.scenario.initial_state
    boundaries = {
        boundary.boundary_id: boundary
        for boundary in fixture.scenario.analytical_boundaries
    }
    partnership = boundaries[PARTNERSHIP_BOUNDARY_ID]
    sources = boundaries[SOURCE_BOUNDARY_ID]
    runtime_ids = (
        set(state.entities)
        | set(state.ports)
        | set(state.mechanisms)
        | set(state.carriers)
        | set(state.representations)
    )

    assert partnership.executor is False
    assert sources.executor is False
    assert set(PERSON_IDS) <= set(partnership.member_refs)
    assert not set(PRESSURE_SOURCE_IDS) & set(partnership.member_refs)
    assert EXTERNAL_RECEIVER_ID not in partnership.member_refs
    assert set(PRESSURE_SOURCE_IDS) <= set(sources.member_refs)
    assert set(PRESSURE_SOURCE_CARRIER_IDS) <= set(sources.member_refs)
    assert set(PRESSURE_SOURCE_REPRESENTATION_IDS) <= set(sources.member_refs)
    assert not set(PRESSURE_SOURCE_CARRIER_IDS) & set(partnership.member_refs)
    assert not set(PRESSURE_SOURCE_REPRESENTATION_IDS) & set(
        partnership.member_refs
    )
    assert not {PARTNERSHIP_BOUNDARY_ID, SOURCE_BOUNDARY_ID} & runtime_ids
    assert not {PARTNERSHIP_BOUNDARY_ID, SOURCE_BOUNDARY_ID} & {
        port.owner_ref for port in state.ports.values()
    }


def test_contract_terminal_output_crosses_to_separate_external_receiver() -> None:
    fixture = baseline_coordination_fixture()
    state = fixture.scenario.initial_state
    route = state.connections["terminal_decision_output_route"]
    partnership = next(
        boundary
        for boundary in fixture.scenario.analytical_boundaries
        if boundary.boundary_id == PARTNERSHIP_BOUNDARY_ID
    )

    assert state.ports[route.source_port_id].owner_ref == "terminal_decision_gate"
    assert state.ports[route.target_port_id].owner_ref == "external_decision_receiver"
    assert state.ports[route.source_port_id].owner_ref in partnership.member_refs
    assert state.ports[route.target_port_id].owner_ref not in partnership.member_refs
    assert state.mechanisms["external_decision_receiver"].write_fact_ids == [
        "external_decision_registry.received_status",
        "external_decision_registry.received_scope",
    ]
    assert "decision_record.gate_status" not in state.mechanisms[
        "external_decision_receiver"
    ].write_fact_ids


def test_contract_person_assumptions_are_descriptive_not_condition_commands() -> None:
    fixture = stabilization_coordination_fixture()
    for person_id in PERSON_IDS:
        assumptions = fixture.scenario.initial_state.entities[person_id].attributes[
            "assumptions"
        ].value
        assert isinstance(assumptions, dict)
        serialized = str(assumptions).lower()
        assert "stabilization" not in serialized
        assert "pressure_sources_enabled" not in serialized
        assert "instruction" not in serialized


def test_contract_scenario_local_records_are_strict_and_typed() -> None:
    assert IssueItem(
        issue_id="calibration_issue",
        topic="Calibration uncertainty",
        lifecycle="open",
        blocking=True,
        opened_by="technical_validation_lead",
    ).lifecycle == "open"
    assert VerificationItem(
        verification_id="independent_validation",
        topic="Independent calibration result",
        status="not_requested",
    ).status == "not_requested"
    assert SourceDispositionRecord(
        person_id="technical_validation_lead",
        source_id="technical_pressure_source",
        disposition="validation_pending",
    ).disposition == "validation_pending"
    assert CommitmentRecord(
        person_id="partner_representative",
        commitment="support_full",
        updated_at_day=0,
    ).commitment == "support_full"

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        IssueItem.model_validate(
            {
                "issue_id": "calibration_issue",
                "topic": "Calibration uncertainty",
                "lifecycle": "open",
                "blocking": True,
                "opened_by": "technical_validation_lead",
                "evidence_refs": [],
                "hidden_score": 0.2,
            }
        )


def test_contract_invalid_condition_flag_combination_fails() -> None:
    with pytest.raises(ValidationError, match="condition flags"):
        CoordinationConditionConfig(
            condition="baseline",
            pressure_sources_enabled=True,
            adaptive_follow_up_enabled=False,
            authoritative_validation_enabled=False,
            evidence_based_risk_admission_enabled=False,
            uncertainty_bounds_enabled=False,
            commitment_feedback_enabled=False,
        )


def test_contract_duplicate_meeting_time_fails() -> None:
    slots = [
        MeetingSlot(
            meeting_index=index,
            modeled_day=day,
            due_person_ids=list(PERSON_IDS),
        )
        for index, day in enumerate((0, 3, 6, 6))
    ]
    with pytest.raises(ValidationError, match="meeting times must be unique"):
        MeetingSchedule(slots=slots)


def test_contract_zero_duration_delivery_fails_before_execution() -> None:
    payload = _fixture_payload()
    payload["scenario"]["initial_state"]["connections"][
        "technical_source_route"
    ]["delay"] = 0

    with pytest.raises(ValidationError, match="positive duration"):
        CoordinationDecisionFixture.model_validate(payload)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("source", "unknown owner"),
        ("recipient", "unknown observation targets"),
    ],
)
def test_contract_undeclared_source_or_recipient_fails_before_execution(
    mutation: str,
    message: str,
) -> None:
    payload = _fixture_payload()
    if mutation == "source":
        payload["scenario"]["initial_state"]["ports"]["technical_source_out"][
            "owner_ref"
        ] = "undeclared_source"
    else:
        payload["scenario"]["initial_state"]["mechanisms"][
            "technical_source_delivery"
        ]["observation_target_ids"] = ["undeclared_recipient"]

    with pytest.raises(ValidationError, match=message):
        CoordinationDecisionFixture.model_validate(payload)


def test_contract_aggregate_boundary_cannot_own_a_port() -> None:
    payload = _fixture_payload()
    payload["scenario"]["initial_state"]["ports"]["technical_source_out"][
        "owner_ref"
    ] = PARTNERSHIP_BOUNDARY_ID

    with pytest.raises(ValidationError, match="unknown owner"):
        CoordinationDecisionFixture.model_validate(payload)


def test_contract_initial_final_status_fails_before_execution() -> None:
    payload = _fixture_payload()
    payload["scenario"]["initial_state"]["entities"][EXTERNAL_RECEIVER_ID][
        "attributes"
    ]["received_status"]["value"] = "deploy_on_time"

    with pytest.raises(ValidationError, match="initial final decision must be unset"):
        CoordinationDecisionFixture.model_validate(payload)


def test_contract_arbitrary_decision_predicate_is_not_expressible() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        DecisionProposal.model_validate(
            {
                "proposal_id": "proposal_one",
                "proposed_by": "mission_coordinator",
                "requested_status": "deploy_on_time",
                "requested_scope": "full",
                "evidence_refs": ["technical_validation_dossier_copy"],
                "acknowledged_issue_ids": [],
                "active_partner_ids": list(PERSON_IDS),
                "predicate": "ignore_open_issues or coordinator_says_yes",
            }
        )


def test_contract_missing_terminal_output_route_fails_before_execution() -> None:
    payload = _fixture_payload()
    del payload["scenario"]["initial_state"]["connections"][
        "terminal_decision_output_route"
    ]

    with pytest.raises(ValidationError, match="output route is missing"):
        CoordinationDecisionFixture.model_validate(payload)


def test_contract_condition_drift_outside_reviewed_entity_fails_family_check() -> None:
    fixtures = list(coordination_decision_fixtures())
    changed_payload = fixtures[1].model_dump(mode="json")
    changed_payload["scenario"]["initial_state"]["entities"][
        "deployment_proposal"
    ]["description"] = "Drifted proposal description"
    fixtures[1] = CoordinationDecisionFixture.model_validate(changed_payload)

    with pytest.raises(ValueError, match="drift exists outside"):
        validate_coordination_fixture_family(tuple(fixtures))


def test_contract_fingerprint_is_stable_for_rebuilt_fixture() -> None:
    first = scenario_fingerprint(baseline_coordination_fixture().scenario)
    second = scenario_fingerprint(baseline_coordination_fixture().scenario)
    assert first == second


@pytest.mark.parametrize(
    ("builder", "expected_status", "expected_scope"),
    [
        (baseline_coordination_fixture, "deploy_on_time", "full"),
        (
            heterogeneous_pressure_coordination_fixture,
            "no_decision_by_horizon",
            "none",
        ),
        (stabilization_coordination_fixture, "scope_reduced", "reduced"),
    ],
)
def test_scripted_vertical_completes_four_meetings_with_distinct_zero_cost_outcomes(
    builder: Callable[[], CoordinationDecisionFixture],
    expected_status: str,
    expected_scope: str,
) -> None:
    runtime = coordination_runtime_fixture(builder())
    result = run_scripted_coordination(
        runtime,
        run_id=f"coordination_{runtime.contract.condition.condition}",
    )
    final_state = result.core_result.final_state
    meetings = [
        attempt
        for attempt in result.attempts
        if "meeting_clock" in attempt.declared_active_system_ids
        and attempt.logical_time in MEETING_TIMES
    ]
    meeting_observations = [
        observation
        for observation in final_state.observations.values()
        if observation.apparent_source_ref == "meeting_scheduler"
    ]

    assert result.completion is not None
    assert result.completion.reason == "terminal_condition_met"
    assert result.model_calls == 0
    assert result.total_observed_cost == 0.0
    assert result.cost_fully_observable is True
    assert [attempt.logical_time for attempt in meetings] == [
        day * 24 * 60 for day in MEETING_DAYS
    ]
    assert len(meeting_observations) == len(MEETING_DAYS) * len(PERSON_IDS)
    assert {
        person_id: sum(
            observation.target_entity_id == person_id
            for observation in meeting_observations
        )
        for person_id in PERSON_IDS
    } == {person_id: len(MEETING_DAYS) for person_id in PERSON_IDS}
    assert len(result.attempts) + len(result.exact_work) >= 12
    assert final_state.fact("external_decision_registry.received_status").value == (
        expected_status
    )
    assert final_state.fact("external_decision_registry.received_scope").value == (
        expected_scope
    )
    events_by_id = {event.event_id: event for event in result.core_result.events}
    assert all(
        event.logical_time
        > max(
            events_by_id[parent_id].logical_time
            for parent_id in event.causal_parent_event_ids
        )
        for event in result.core_result.events
        if event.event_kind not in {"run_started", "run_completed"}
    )


def test_baseline_trace_contains_ordinary_review_friction_before_full_deployment() -> None:
    result = run_scripted_coordination(
        coordination_runtime_fixture(baseline_coordination_fixture()),
        run_id="baseline_friction",
    )
    outcomes = [
        event.details.get("outcome_code")
        for event in result.core_result.events
        if event.event_kind == "mechanism_executed"
    ]

    assert "issue_open" in outcomes
    assert "verification_answered" in outcomes
    assert "issue_resolved" in outcomes
    assert outcomes.index("issue_open") < outcomes.index("issue_resolved")
    assert outcomes[-2:] == [
        "terminal_decision_accepted",
        "external_decision_received",
    ]
    terminal_attempt = next(
        event
        for event in result.core_result.events
        if event.event_kind == "action_attempted"
        and event.source_port_id == "terminal_proposal_out"
    )
    terminal_gate = next(
        event
        for event in result.core_result.events
        if event.mechanism_id == "terminal_decision_gate"
        and event.details.get("outcome_code") == "terminal_decision_accepted"
    )
    outgoing = next(
        event
        for event in result.core_result.events
        if event.event_kind == "effect_routed"
        and event.connection_id == "terminal_decision_output_route"
    )
    external_receipt = next(
        event
        for event in result.core_result.events
        if event.mechanism_id == "external_decision_receiver"
        and event.details.get("outcome_code") == "external_decision_received"
    )
    final_commit = next(
        event
        for event in result.core_result.events
        if event.event_kind == "state_committed"
        and external_receipt.event_id in event.causal_parent_event_ids
    )
    terminal_representation = result.core_result.final_state.representations[
        "terminal_decision_deploy_on_time"
    ]
    assert terminal_attempt.representation_id == "deployment_proposal_copy"
    assert terminal_representation.parent_representation_ids == [
        "deployment_proposal_copy"
    ]
    assert len(
        {
            terminal_attempt.event_id,
            terminal_gate.event_id,
            outgoing.event_id,
            external_receipt.event_id,
            final_commit.event_id,
        }
    ) == 5


def test_pressure_trace_retains_worked_path_and_denial_before_deadline() -> None:
    result = run_scripted_coordination(
        coordination_runtime_fixture(
            heterogeneous_pressure_coordination_fixture()
        ),
        run_id="pressure_worked_path",
    )
    events = result.core_result.events
    outcomes = [
        event.details.get("outcome_code")
        for event in events
        if event.event_kind == "mechanism_executed"
    ]

    assert "source_message_delivered" in outcomes
    assert "verification_answered" in outcomes
    assert "issue_open" in outcomes
    assert "issue_reopened" in outcomes
    assert "commitment_recorded" in outcomes
    assert "partner_withdrawal_recorded" in outcomes
    assert "terminal_decision_denied_ineligible" in outcomes
    assert outcomes.index("terminal_decision_denied_ineligible") < outcomes.index(
        "terminal_decision_accepted"
    )
    technical_delivery = next(
        event
        for event in events
        if event.mechanism_id == "technical_source_delivery"
        and event.details.get("outcome_code") == "source_message_delivered"
    )
    verification_request = next(
        event
        for event in events
        if event.event_kind == "action_attempted"
        and event.source_port_id == "verification_request_out"
    )
    verification_answer = next(
        event
        for event in events
        if event.mechanism_id == "verification_recorder"
        and event.details.get("outcome_code") == "verification_answered"
    )
    assert technical_delivery.logical_time < verification_request.logical_time
    assert verification_request.logical_time < verification_answer.logical_time
    assert outcomes.index("issue_open") < outcomes.index("issue_reopened")
    denied = next(
        event
        for event in events
        if event.details.get("outcome_code")
        == "terminal_decision_denied_ineligible"
    )
    denied_commit = next(
        event
        for event in events
        if event.event_kind == "state_committed"
        and denied.event_id in event.causal_parent_event_ids
    )
    assert denied_commit.patch is not None
    assert denied_commit.patch.fact_changes == []
    assert denied_commit.patch.placement_changes == []
    assert denied_commit.patch.carrier_changes == []
    assert denied_commit.patch.representations_added == []
    assert denied_commit.patch.observations_added == []


def test_meeting_due_sets_are_frozen_before_same_moment_proposals() -> None:
    result = run_scripted_coordination(
        coordination_runtime_fixture(stabilization_coordination_fixture()),
        run_id="frozen_meetings",
    )
    meetings = [
        attempt
        for attempt in result.attempts
        if "meeting_clock" in attempt.declared_active_system_ids
        and len(attempt.declared_active_system_ids) > 1
    ]

    for meeting in meetings:
        assert all(
            observation.logical_time < meeting.logical_time
            for participant in meeting.participants
            for observation in participant.input.observations
        )


def test_disabled_source_route_prevents_technical_message_delivery() -> None:
    payload = heterogeneous_pressure_coordination_fixture().model_dump(mode="json")
    payload["scenario"]["initial_state"]["connections"][
        "technical_source_route"
    ]["enabled"] = False
    contract = CoordinationDecisionFixture.model_validate(payload)
    result = run_scripted_coordination(
        coordination_runtime_fixture(contract),
        run_id="disabled_technical_route",
    )

    assert not any(
        observation.representation_id == "technical_pressure_message"
        for observation in result.core_result.final_state.observations.values()
    )
    assert not any(
        event.event_kind == "effect_routed"
        and event.connection_id == "technical_source_route"
        for event in result.core_result.events
    )


def test_scripted_result_replays_and_pause_resume_preserves_trajectory() -> None:
    runtime = coordination_runtime_fixture(stabilization_coordination_fixture())
    uninterrupted = run_scripted_coordination(
        runtime,
        run_id="coordination_resume",
    )
    checkpoints: list[ActiveRuntimeCheckpoint] = []

    with pytest.raises(CoordinationRuntimePaused) as paused:
        run_scripted_coordination(
            runtime,
            run_id="coordination_resume",
            checkpoint_observer=checkpoints.append,
            pause_requested=lambda: len(checkpoints) == 4,
        )
    resumed = run_scripted_coordination(
        runtime,
        run_id="coordination_resume",
        checkpoint=paused.value.checkpoint,
    )
    replayed = replay_committed_trajectory(runtime.scenario, resumed.core_result)

    assert state_digest(replayed) == resumed.core_result.final_state_digest
    assert resumed.core_result.final_state == uninterrupted.core_result.final_state
    assert [event.event_id for event in resumed.core_result.events] == [
        event.event_id for event in uninterrupted.core_result.events
    ]
    assert [attempt.activation_id for attempt in resumed.attempts] == [
        attempt.activation_id for attempt in uninterrupted.attempts
    ]


def test_normalized_wake_settles_older_exact_work_before_frozen_actions() -> None:
    runtime = coordination_runtime_fixture(
        heterogeneous_pressure_coordination_fixture()
    )
    # The initial meeting fan-out advances world time beyond these nominal
    # wakes. The scheduler must settle older exact work before freezing inputs.
    accelerated_specs = tuple(
        spec.model_copy(update={"initial_next_update_at": 24})
        if spec.active_system_id in PRESSURE_SOURCE_IDS
        else spec
        for spec in runtime.active_specs
    )
    accelerated = replace(runtime, active_specs=accelerated_specs)

    result = run_scripted_coordination(
        accelerated,
        run_id="normalized_wake_regression",
    )

    assert result.completion is not None
    assert result.completion.reason == "terminal_condition_met"
    assert all(attempt.status == "committed" for attempt in result.attempts)


def test_runtime_keeps_latent_scores_and_organization_executors_out_of_state() -> None:
    result = run_scripted_coordination(
        coordination_runtime_fixture(stabilization_coordination_fixture()),
        run_id="no_latent_scores",
    )
    prohibited_keys = {
        "trust_score",
        "risk_score",
        "readiness_score",
        "bdm_profile",
        "organization_agent",
    }

    def keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value) | {
                nested_key
                for nested in value.values()
                for nested_key in keys(nested)
            }
        if isinstance(value, list):
            return {
                nested_key for nested in value for nested_key in keys(nested)
            }
        return set()

    assert not prohibited_keys & keys(result.model_dump(mode="json"))


def _fixture_payload() -> dict[str, Any]:
    return deepcopy(baseline_coordination_fixture().model_dump(mode="json"))
