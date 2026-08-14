from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from cybernetic_influence.general_simulation.authoring_models import (
    ComponentRequestV1,
    GeneralSimulationProposalV1,
    GeneralWorldRecordProposalV1,
    ResourceStockProposalV1,
    ResourceTransportProposalV1,
    StateEntryV1,
)
from cybernetic_influence.general_simulation.authoring import _diagnostics
from cybernetic_influence.general_simulation.compiler import (
    GeneralCompilationError,
    compile_general_simulation,
)
from cybernetic_influence.general_simulation.registry import (
    default_registry,
    resolve_request,
)


FIXTURES = Path("tests/fixtures/general_simulation")


def load_proposal(name: str) -> GeneralSimulationProposalV1:
    return GeneralSimulationProposalV1.model_validate_json(
        (FIXTURES / name).read_text(encoding="utf-8")
    )


@pytest.mark.parametrize(
    "fixture_name", ["port_coordination.json", "service_incident.json"]
)
def test_materially_different_domains_compile_through_same_registry(
    fixture_name: str,
) -> None:
    compiled = compile_general_simulation(load_proposal(fixture_name))

    assert compiled.coverage.approvable
    assert not compiled.coverage.blocking_request_ids
    assert compiled.world_spec.spec_id in {
        "relief_port_coordination",
        "service_incident_coordination",
    }
    assert compiled.registry_digest == compiled.coverage.registry_digest
    assert all(item.resolved_component_ref for item in compiled.coverage.items)
    assert {item.classification for item in compiled.coverage.items} <= {
        "exact",
        "coarse_llm",
    }
    assert compiled.configuration_graph["isolated_node_ids"] == []


def test_isolated_configured_record_blocks_authoring_approval() -> None:
    proposal = load_proposal("service_incident.json")
    proposal.world_records.append(
        GeneralWorldRecordProposalV1(
            record_id="unused_dashboard",
            kind="dashboard",
            label="Unused dashboard",
            public_state=[],
            hidden_state=[],
            visible_to_actor_ids=[],
        )
    )

    compiled = compile_general_simulation(proposal)
    diagnostics = _diagnostics(proposal, compiled)

    assert compiled.configuration_graph["isolated_node_ids"] == ["unused_dashboard"]
    assert any(item["code"] == "isolated_configured_node" for item in diagnostics)


def test_unknown_material_behavior_remains_visibly_unapprovable() -> None:
    proposal = load_proposal("service_incident.json")
    proposal.component_requests.append(
        ComponentRequestV1(
            request_id="quantum_prediction",
            subject_refs=["api_service"],
            behavior_description="Predict an unknowable quantum market trajectory.",
            required_reads=["api_service"],
            desired_effects=["Foretell exact future prices."],
            fidelity_need="exact",
            material_to_question=True,
        )
    )
    proposal.schedule[-1] = proposal.schedule[-1].model_copy(
        update={
            "active_component_request_ids": [
                *proposal.schedule[-1].active_component_request_ids,
                "quantum_prediction",
            ]
        }
    )

    compiled = compile_general_simulation(proposal)

    item = next(
        item for item in compiled.coverage.items if item.request_id == "quantum_prediction"
    )
    assert item.classification == "unsupported"
    assert item.blocking
    assert compiled.coverage.blocking_request_ids == ["quantum_prediction"]


def test_resource_transport_requires_declared_directed_route_and_custody() -> None:
    proposal = load_proposal("port_coordination.json")
    assert proposal.resource_extension is not None
    proposal.resource_extension.stocks.append(
        ResourceStockProposalV1(
            resource_id="received_fuel",
            quantity=0,
            custodian_id="port_coordinator",
            conserved=True,
        )
    )
    transport = ResourceTransportProposalV1(
        transport_id="move_dispatch_fuel",
        operator_ids=["trucking_dispatcher"],
        source_resource_id="dispatch_fuel",
        destination_resource_id="received_fuel",
        source_custodian_id="trucking_dispatcher",
        destination_custodian_id="port_coordinator",
        quantity=10,
        origin_place_id="outside_port",
        destination_place_id="port",
        allowed_route_ids=["main_bridge"],
        arrival_record_id="relief_cargo",
        arrival_quantity_key="received_fuel_quantity",
        usable_quantity_key="usable_fuel_quantity",
        arrival_minute_key="fuel_arrival_minute",
    )
    proposal.resource_transports.append(transport)
    assert proposal.spatial_extension is not None
    bridge = next(
        item
        for item in proposal.spatial_extension.links
        if item.link_id == "main_bridge"
    )
    bridge.public_state.append(StateEntryV1(key="travel_time_minutes", value=12))
    proposal.schedule[1] = proposal.schedule[1].model_copy(
        update={"active_transition_contract_ids": ["move_dispatch_fuel"]}
    )

    compile_general_simulation(proposal)

    proposal.resource_transports[0] = transport.model_copy(
        update={"origin_place_id": "port", "destination_place_id": "outside_port"}
    )
    with pytest.raises(GeneralCompilationError, match="directed endpoints"):
        compile_general_simulation(proposal)


@pytest.mark.parametrize(
    ("request_id", "description", "effects", "expected_ref"),
    [
        (
            "assess_outcome",
            "The incident commander assesses the post-recovery state.",
            ["Record an outcome assessment and remaining uncertainty."],
            "bounded_person_action@1",
        ),
        (
            "apply_recovery",
            "The service environment applies an approved bounded recovery attempt.",
            ["Change availability according to the validated outcome."],
            "joint_semantic_adjudication@1",
        ),
        (
            "joint_decision",
            "The response group jointly adjudicates whether to proceed using delivered claims.",
            ["Record one coordinated decision and its rationale."],
            "joint_semantic_adjudication@1",
        ),
        (
            "route_report",
            "Deliver recipient-specific radio reports containing a route blockage.",
            ["Preserve the apparent source and named recipients."],
            "information_delivery@1",
        ),
        (
            "floor_inspection",
            "The structural inspector attempts to inspect a damaged floor segment.",
            ["Retain the inspection result as canonical state."],
            "joint_semantic_adjudication@1",
        ),
        (
            "battery_consumption",
            "Account for finite forklift battery charge consumed by movement.",
            ["Decrease the conserved battery charge without going below zero."],
            "conserved_resources@1",
        ),
    ],
)
def test_registry_resolves_authentic_general_action_language(
    request_id: str,
    description: str,
    effects: list[str],
    expected_ref: str,
) -> None:
    request = ComponentRequestV1(
        request_id=request_id,
        subject_refs=(
            ["incident_commander", "api_service"]
            if request_id == "assess_outcome"
            else (
                ["incident_commander", "api_service"]
                if request_id == "floor_inspection"
                else ["api_service"]
            )
        ),
        behavior_description=description,
        required_reads=["api_service"],
        desired_effects=effects,
        fidelity_need="exact",
        material_to_question=True,
    )

    resolved, evidence = resolve_request(
        request, default_registry(), actor_ids={"incident_commander"}
    )

    assert resolved is not None, evidence
    assert resolved.ref == expected_ref


def test_invented_implementation_reference_is_rejected_by_authoring_schema() -> None:
    payload = json.loads((FIXTURES / "service_incident.json").read_text(encoding="utf-8"))
    payload["component_requests"][0]["implementation_ref"] = "malicious.module:run"

    with pytest.raises(ValidationError, match="implementation_ref"):
        GeneralSimulationProposalV1.model_validate(payload)


def test_overlapping_coarse_and_detailed_causal_ownership_is_rejected() -> None:
    proposal = load_proposal("service_incident.json")
    proposal.active_systems[0].causal_responsibility_tags = ["service_recovery"]
    proposal.active_systems[1].causal_responsibility_tags = ["service_recovery"]
    proposal.active_systems[1].representation_strategy = "coarse_surrogate"

    with pytest.raises(GeneralCompilationError, match="both detailed and coarse_surrogate"):
        compile_general_simulation(proposal)


def test_compiler_preserves_hidden_information_outside_actor_access() -> None:
    compiled = compile_general_simulation(load_proposal("service_incident.json"))
    database = compiled.world_spec.initial_state.records["database_service"]
    commander_access = next(
        item
        for item in compiled.world_spec.actor_access
        if item.actor_id == "incident_commander"
    )

    assert database.hidden_state["actual_cause"] == "expired_replication_credential"
    assert "database_service" in commander_access.record_ids
    assert "technical_credential_report" not in commander_access.representation_ids


def test_compiler_rejects_broken_semantic_references() -> None:
    proposal = load_proposal("service_incident.json")
    assert proposal.information_extension is not None
    proposal.information_extension.representations[0].recipient_ids = ["missing_actor"]

    with pytest.raises(GeneralCompilationError, match="unknown recipients"):
        compile_general_simulation(proposal)
