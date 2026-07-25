"""Focused proof for the first approved authored scenario template."""

from __future__ import annotations

from cybernetic_influence.authoring import (
    AuthoringCompilationError,
    ScenarioDraftProposal,
    compile_resource_request,
)
from cybernetic_influence.causal_core.replay import replay_committed_trajectory


def _proposal(*, resource_available: bool = True) -> ScenarioDraftProposal:
    return ScenarioDraftProposal.model_validate(
        {
            "scenario_id": "equipment_checkout",
            "title": "Equipment checkout desk",
            "description": (
                "An employee requests a laptop for fieldwork. A clerk receives the "
                "request through the configured ticket route, and an exact reservation "
                "gate checks eligibility and availability."
            ),
            "people": [
                {
                    "entity_id": "employee",
                    "label": "Ari",
                    "position": "field researcher",
                    "disposition": "careful about preparing for fieldwork",
                    "memories": ["Ari needs a laptop for the next field visit."],
                },
                {
                    "entity_id": "clerk",
                    "label": "Mina",
                    "position": "equipment desk clerk",
                    "disposition": "attentive to the request record and copied policy",
                    "memories": ["Mina recognizes the desk's current equipment process."],
                },
            ],
            "objects": [
                {
                    "entity_id": "laptop_12",
                    "entity_kind": "laptop",
                    "label": "Laptop 12",
                    "description": "A concrete laptop that may be reserved.",
                }
            ],
            "information": [
                {
                    "information_id": "eligibility_policy",
                    "label": "Eligibility policy copy",
                    "content": "Field researchers may reserve an available laptop.",
                }
            ],
            "places": [
                {
                    "place_id": "field_office",
                    "label": "Field office",
                    "description": "Ari's current office.",
                },
                {
                    "place_id": "equipment_desk",
                    "label": "Equipment desk",
                    "description": "The clerk's desk and laptop storage.",
                },
            ],
            "spatial_links": [
                {
                    "spatial_link_id": "office_hallway",
                    "endpoint_a_place_id": "field_office",
                    "endpoint_b_place_id": "equipment_desk",
                    "description": "A hallway connects the two rooms.",
                }
            ],
            "placements": {
                "employee": "field_office",
                "clerk": "equipment_desk",
                "laptop_12": "equipment_desk",
            },
            "timing_assumptions": [
                {"name": "request_delivery", "minutes": 2, "basis": "authored estimate"},
                {"name": "decision_delivery", "minutes": 3, "basis": "authored estimate"},
                {"name": "result_delivery", "minutes": 1, "basis": "authored estimate"},
            ],
            "workflow": {
                "template_id": "resource_request_v1",
                "requester_id": "employee",
                "reviewer_id": "clerk",
                "request_id": "laptop_request_1",
                "resource_id": "laptop_12",
                "policy_information_id": "eligibility_policy",
                "eligible_requester_ids": ["employee"],
                "resource_available": resource_available,
                "request_delivery_minutes": 2,
                "decision_delivery_minutes": 3,
                "result_delivery_minutes": 1,
            },
            "analytical_boundaries": [
                {
                    "boundary_id": "field_support_view",
                    "label": "Field support analytical view",
                    "description": "An execution-inert analytical grouping of the people and laptop.",
                    "member_refs": ["employee", "clerk", "laptop_12", "laptop_request_1"],
                }
            ],
            "fidelity_questions": [
                "Did the request travel only through the configured ticket route?",
                "Did the exact gate deny an unavailable laptop even after a review attempt?",
                "Did the analytical boundary remain execution-inert?",
            ],
        }
    )


def test_compiler_builds_a_reviewable_timed_exact_scenario() -> None:
    compiled = compile_resource_request(_proposal())
    scenario = compiled.scenario

    assert scenario.timing_contract == "positive_duration"
    assert scenario.time_unit == "minute"
    assert scenario.initial_state.spatial_links["office_hallway"]
    assert scenario.initial_state.entities["eligibility_policy"].entity_kind == (
        "information_document"
    )
    assert set(scenario.initial_state.connections) == {
        "request_route",
        "decision_route",
        "requester_result_route",
    }
    assert all(item.executor is False for item in scenario.analytical_boundaries)
    assert compiled.proposal_digest == compile_resource_request(_proposal()).proposal_digest


def test_scripted_template_reserves_available_resource_and_replays() -> None:
    compiled = compile_resource_request(_proposal())
    result = compiled.run_scripted(run_id="equipment_checkout_available")

    assert result.model_calls == 0
    assert result.total_observed_cost == 0.0
    assert result.core_result.final_state.fact("laptop_12.availability").value == "reserved"
    assert result.core_result.final_state.fact("laptop_request_1.status").value == "reserved"
    assert replay_committed_trajectory(compiled.scenario, result.core_result) == result.core_result.final_state
    assert [attempt.declared_active_system_ids for attempt in result.attempts] == [
        ["requester"],
        ["reviewer"],
    ]


def test_exact_gate_denies_unavailable_resource_after_reviewer_attempt() -> None:
    compiled = compile_resource_request(_proposal(resource_available=False))
    result = compiled.run_scripted(run_id="equipment_checkout_unavailable")

    assert result.core_result.final_state.fact("laptop_12.availability").value == "unavailable"
    assert result.core_result.final_state.fact("laptop_request_1.status").value == "denied_unavailable"
    assert any(
        event.mechanism_id == "exact_reservation_gate"
        and "denied_unavailable" in event.summary
        for event in result.core_result.events
    )


def test_compiler_rejects_unknown_boundary_referent() -> None:
    proposal = _proposal().model_copy(deep=True)
    proposal.analytical_boundaries[0].member_refs.append("department_mind")

    try:
        compile_resource_request(proposal)
    except AuthoringCompilationError as error:
        assert "unknown members" in str(error)
    else:
        raise AssertionError("unknown analytical-boundary member was accepted")


def test_compiler_rejects_runtime_id_collisions_and_timing_drift() -> None:
    collision = _proposal().model_copy(deep=True)
    collision.objects[0].entity_id = "exact_reservation_gate"
    collision.workflow.resource_id = "exact_reservation_gate"
    try:
        compile_resource_request(collision)
    except AuthoringCompilationError as error:
        assert "runtime ids" in str(error)
    else:
        raise AssertionError("runtime id collision was accepted")

    drift = _proposal().model_copy(deep=True)
    drift.timing_assumptions[0].minutes = 7
    try:
        compile_resource_request(drift)
    except AuthoringCompilationError as error:
        assert "timing assumption" in str(error)
    else:
        raise AssertionError("timing drift was accepted")
