"""Packet 21A0 contract and both-sign fixtures."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any

import pytest
from pydantic import ValidationError

from cybernetic_influence.scenarios.coordination_decision import (
    CONDITION_ENTITY_ID,
    DECISION_DEADLINE_DAY,
    EXTERNAL_RECEIVER_ID,
    MAX_CAUSAL_MOMENTS,
    MAX_PARTICIPANT_CALLS,
    MEETING_DAYS,
    PARTNERSHIP_BOUNDARY_ID,
    PERSON_IDS,
    PRESSURE_SOURCE_CARRIER_IDS,
    PRESSURE_SOURCE_IDS,
    PRESSURE_SOURCE_REPRESENTATION_IDS,
    SCENARIO_ID,
    SOURCE_BOUNDARY_ID,
    CommitmentRecord,
    CoordinationConditionConfig,
    CoordinationDecisionFixture,
    DecisionProposal,
    IssueItem,
    MeetingSchedule,
    MeetingSlot,
    SourceDispositionRecord,
    VerificationItem,
    baseline_coordination_fixture,
    condition_independent_scenario_dump,
    coordination_decision_fixtures,
    heterogeneous_pressure_coordination_fixture,
    scenario_fingerprint,
    stabilization_coordination_fixture,
    validate_coordination_fixture_family,
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
    assert fixture.scenario.time_unit == "scenario_day"
    assert fixture.scenario.timing_contract == "positive_duration"
    assert all(connection.delay > 0 for connection in state.connections.values())
    assert state.representations["technical_validation_dossier_copy"].carrier_id == (
        "dossier_carrier"
    )
    assert fixture.run_control_options.default_horizon == DECISION_DEADLINE_DAY
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


def _fixture_payload() -> dict[str, Any]:
    return deepcopy(baseline_coordination_fixture().model_dump(mode="json"))
