from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from cybernetic_influence.general_simulation.concordia_runtime import (
    _prepare_world,
    _simulation,
    _strict_checkpoint,
    _world,
    bridge_port_spec,
    run_bridge_port_vertical,
)
from cybernetic_influence.general_simulation.models import (
    ActorDecision,
    Assimilation,
    Consequence,
    ResourceStock,
    ResourceTransformationContract,
    ResourceTransportContract,
    SensingTransitionContract,
    PatchOperation,
    Precondition,
    SemanticActionIntent,
    TypedTarget,
    WorldTransaction,
    WorldRecord,
)
from cybernetic_influence.general_simulation.world import CanonicalWorld, state_hash


def structured_stub(
    model: str,
    messages: list[dict[str, str]],
    *,
    response_model: type[Any],
    **kwargs: Any,
) -> tuple[Any, Any]:
    del model, kwargs
    if response_model is ActorDecision:
        context = json.loads(messages[-1]["content"].split("\n", 1)[1])
        return (
            ActorDecision(
                assimilation=Assimilation(
                    attended_observation_ids=[
                        "representation:bridge_notice",
                        "consequence:temporary-route-open",
                    ],
                    memory_additions=["A temporary route is reported operational."],
                    memory_revisions=[],
                    provenance_links=["consequence:temporary-route-open"],
                    interpretation="Use the material alternative rather than the bridge.",
                ),
                intent=SemanticActionIntent(
                    intent_id="move-via-temporary-route",
                    actor_id="worker",
                    base_revision=context["base_revision"],
                    action=(
                        "Escort the fuel truck through the temporary depot and "
                        "service route into the port."
                    ),
                    target_refs=[
                        "worker",
                        "fuel_truck",
                        "outside_to_depot",
                        "depot_to_port",
                    ],
                    purpose="Deliver fuel to the port.",
                    expected_effect="Worker and truck reach the port.",
                    stated_rationale="The reported alternative route is operational.",
                ),
            ),
            SimpleNamespace(provider="test-stub"),
        )
    payload = json.loads(messages[-1]["content"])
    return (
        WorldTransaction(
            transaction_id="tx-move-port",
            base_revision=payload["world"]["revision"],
            authority_id="port_semantic_adjudicator",
            intent_ids=[payload["intent"]["intent_id"]],
            operations=[
                PatchOperation(
                    operation="rebind",
                    target=TypedTarget(
                        record_type="placement", record_id=record_id, field="place_id"
                    ),
                    value="port",
                )
                for record_id in ("worker", "fuel_truck")
            ],
            preconditions=[],
            consequences=[
                Consequence(
                    consequence_id="arrival",
                    recipient_id="worker",
                    content="You and the fuel truck arrived at the port.",
                    apparent_source="direct observation",
                )
            ],
            evidence_refs=[payload["intent"]["intent_id"]],
            stated_rationale="The operational alternative path supports movement.",
        ),
        SimpleNamespace(provider="test-stub"),
    )


def test_world_rejects_destroyed_route_then_accepts_dynamic_topology() -> None:
    simulation = _simulation(bridge_port_spec(), structured_stub)
    world = _world(simulation)

    _prepare_world(world)

    assert [item.validation.accepted for item in world.evidence] == [False, True]
    assert world.state.revision == 1
    assert "temporary_depot" in world.state.places
    assert world.operational_path_exists("outside_port", "port")


def test_actor_context_never_contains_hidden_sabotage_cause() -> None:
    world = _world(_simulation(bridge_port_spec(), structured_stub))
    _prepare_world(world)

    assert "sabotage" not in world.actor_context("worker").model_dump_json().lower()


def _contract_world() -> CanonicalWorld:
    spec = bridge_port_spec()
    authority = next(
        item for item in spec.authorities if item.authority_id == "port_semantic_adjudicator"
    )
    authority.patch_grammar.allowed_record_types = ["record", "resource"]
    spec.initial_state.routes["main_bridge"].operational = True
    spec.initial_state.routes["main_bridge"].public_state["travel_time_minutes"] = 75
    spec.initial_state.records["material_truth"] = WorldRecord(
        record_id="material_truth",
        kind="material",
        label="Material truth",
        hidden_state={"quality": "usable"},
    )
    spec.initial_state.records["quality_finding"] = WorldRecord(
        record_id="quality_finding", kind="finding", label="Quality finding"
    )
    spec.initial_state.records["finished_inventory"] = WorldRecord(
        record_id="finished_inventory",
        kind="inventory",
        label="Finished inventory",
        state={"quantity": 0},
    )
    spec.initial_state.records["arrival"] = WorldRecord(
        record_id="arrival",
        kind="arrival",
        label="Arrival",
        state={"quantity": 0, "usable_quantity": 0, "arrival_minute": None},
    )
    spec.initial_state.resources = {
        "raw_a": ResourceStock(resource_id="raw_a", quantity=600, custodian_id="worker"),
        "raw_b": ResourceStock(resource_id="raw_b", quantity=600, custodian_id="worker"),
        "finished": ResourceStock(resource_id="finished", quantity=0, custodian_id="worker"),
        "delivered": ResourceStock(resource_id="delivered", quantity=0, custodian_id="worker"),
    }
    spec.sensing_contracts = [
        SensingTransitionContract(
            contract_id="inspect_quality",
            subject_type="record",
            subject_id="material_truth",
            observer_ids=["worker"],
            hidden_to_output_fields={"quality": "quality"},
            output_record_id="quality_finding",
            result_recipient_ids=["worker"],
        )
    ]
    spec.resource_transformation_contracts = [
        ResourceTransformationContract(
            contract_id="produce",
            operator_ids=["worker"],
            input_resource_quantities={"raw_a": 500, "raw_b": 500},
            output_resource_id="finished",
            output_quantity=500,
            maximum_batches=1,
            public_inventory_record_id="finished_inventory",
        )
    ]
    spec.resource_transport_contracts = [
        ResourceTransportContract(
            contract_id="deliver",
            operator_ids=["worker"],
            source_resource_id="finished",
            destination_resource_id="delivered",
            quantity=500,
            origin_place_id="outside_port",
            destination_place_id="port",
            allowed_route_ids=["main_bridge"],
            arrival_record_id="arrival",
            arrival_quantity_key="quantity",
            usable_quantity_key="usable_quantity",
            arrival_minute_key="arrival_minute",
        )
    ]
    return CanonicalWorld(spec)


def _contract_intent(*contract_ids: str) -> SemanticActionIntent:
    return SemanticActionIntent(
        intent_id="bounded_attempt",
        actor_id="worker",
        base_revision=0,
        action="Inspect, produce, and deliver one bounded batch.",
        target_refs=["quality_finding", "finished_inventory", "arrival"],
        purpose="Exercise declared mechanics.",
        expected_effect="A bounded delivery may occur.",
        stated_rationale="The attempt uses only configured contracts.",
        transition_contract_ids=list(contract_ids),
    )


def test_omitted_nullable_precondition_value_is_an_explicit_null_guard() -> None:
    precondition = Precondition.model_validate(
        {
            "target": {
                "record_type": "record",
                "record_id": "dispatch_authorization",
                "field": "state.status",
            }
        }
    )

    assert precondition.expected is None
    assert precondition.comparison == "equals"


def _contract_transaction(*, delivered_quantity: int = 500) -> WorldTransaction:
    return WorldTransaction(
        transaction_id="contract_transition",
        base_revision=0,
        authority_id="port_semantic_adjudicator",
        intent_ids=["bounded_attempt"],
        operations=[
            PatchOperation(operation="replace", target=TypedTarget(record_type="record", record_id="quality_finding", field="state.quality"), value="usable"),
            PatchOperation(operation="replace", target=TypedTarget(record_type="resource", record_id="raw_a", field="quantity"), value=100),
            PatchOperation(operation="replace", target=TypedTarget(record_type="resource", record_id="raw_b", field="quantity"), value=100),
            PatchOperation(operation="replace", target=TypedTarget(record_type="resource", record_id="finished", field="quantity"), value=500),
            PatchOperation(operation="replace", target=TypedTarget(record_type="record", record_id="finished_inventory", field="state.quantity"), value=500),
            PatchOperation(operation="replace", target=TypedTarget(record_type="resource", record_id="finished", field="quantity"), value=0),
            PatchOperation(operation="replace", target=TypedTarget(record_type="resource", record_id="delivered", field="quantity"), value=delivered_quantity),
            PatchOperation(operation="replace", target=TypedTarget(record_type="record", record_id="arrival", field="state.quantity"), value=500),
            PatchOperation(operation="replace", target=TypedTarget(record_type="record", record_id="arrival", field="state.usable_quantity"), value=500),
            PatchOperation(operation="replace", target=TypedTarget(record_type="record", record_id="arrival", field="state.arrival_minute"), value=135),
        ],
        preconditions=[
            Precondition(target=TypedTarget(record_type="route", record_id="main_bridge", field="operational"), expected=True)
        ],
        consequences=[],
        evidence_refs=["bounded_attempt", "main_bridge"],
        stated_rationale="Every material mutation is covered by a selected contract.",
    )


def test_declared_contracts_license_complete_transition_and_retain_attribution() -> None:
    spec = _contract_world().spec
    semantic = next(
        item
        for item in spec.authorities
        if item.authority_id == "port_semantic_adjudicator"
    )
    semantic.patch_grammar.allowed_operations = []
    semantic.patch_grammar.allowed_record_types = []
    world = CanonicalWorld(spec)
    intent = _contract_intent("inspect_quality", "produce", "deliver")

    result = world.validate_and_commit(
        _contract_transaction(), intents=[intent], current_minute=60
    )

    assert result.accepted
    evidence = world.evidence[-1]
    assert {item.contract_id for item in evidence.operation_attributions} == {
        "inspect_quality",
        "produce",
        "deliver",
    }
    assert all(
        item.classification == "exact_contract"
        for item in evidence.operation_attributions
    )


def test_exact_transport_requires_compiled_status_and_capacity_guards() -> None:
    base = _contract_world()
    spec = base.spec
    spec.initial_state.records["dispatch_authorization"] = WorldRecord(
        record_id="dispatch_authorization",
        kind="authorization",
        label="Dispatch authorization",
        state={"status": "cleared"},
    )
    spec.initial_state.resources["fuel"] = ResourceStock(
        resource_id="fuel", quantity=20, custodian_id="worker"
    )
    spec.resource_transport_contracts[0] = spec.resource_transport_contracts[
        0
    ].model_copy(
        update={
            "required_preconditions": [
                Precondition(
                    target=TypedTarget(
                        record_type="record",
                        record_id="dispatch_authorization",
                        field="state.status",
                    ),
                    expected="cleared",
                ),
                Precondition(
                    target=TypedTarget(
                        record_type="resource", record_id="fuel", field="quantity"
                    ),
                    comparison="greater_than_or_equal",
                    expected=10,
                ),
            ]
        }
    )
    intent = _contract_intent("inspect_quality", "produce", "deliver")

    missing = CanonicalWorld(spec)
    rejected = missing.validate_and_commit(
        _contract_transaction(), intents=[intent], current_minute=60
    )
    assert not rejected.accepted
    assert any("not licensed by a complete declared transition contract" in item for item in rejected.errors)

    guarded = CanonicalWorld(spec)
    transaction = _contract_transaction().model_copy(
        update={
            "preconditions": [
                *_contract_transaction().preconditions,
                *spec.resource_transport_contracts[0].required_preconditions,
            ]
        }
    )
    accepted = guarded.validate_and_commit(
        transaction, intents=[intent], current_minute=60
    )
    assert accepted.accepted

    insufficient_spec = spec.model_copy(deep=True)
    insufficient_spec.initial_state.resources["fuel"] = insufficient_spec.initial_state.resources[
        "fuel"
    ].model_copy(update={"quantity": 5})
    insufficient = CanonicalWorld(insufficient_spec)
    failed = insufficient.validate_and_commit(
        transaction, intents=[intent], current_minute=60
    )
    assert not failed.accepted
    assert any("greater_than_or_equal 10" in item for item in failed.errors)


def test_sensing_contract_can_guard_not_yet_created_finding_with_null_precondition() -> None:
    world = _contract_world()
    intent = _contract_intent("inspect_quality")
    transaction = WorldTransaction(
        transaction_id="inspect_once",
        base_revision=0,
        authority_id="port_semantic_adjudicator",
        intent_ids=[intent.intent_id],
        operations=[
            PatchOperation(
                operation="replace",
                target=TypedTarget(
                    record_type="record",
                    record_id="quality_finding",
                    field="state.quality",
                ),
                value="usable",
            )
        ],
        preconditions=[
            Precondition(
                target=TypedTarget(
                    record_type="record",
                    record_id="quality_finding",
                    field="state.quality",
                ),
                expected=None,
            )
        ],
        consequences=[],
        evidence_refs=[intent.intent_id],
        stated_rationale="The finding has not already been recorded.",
    )

    result = world.validate_and_commit(
        transaction, intents=[intent], current_minute=60
    )

    assert result.accepted
    assert world.state.records["quality_finding"].state["quality"] == "usable"


def test_contract_owned_quantity_change_fails_without_complete_declared_transport() -> None:
    world = _contract_world()
    intent = _contract_intent("inspect_quality", "produce", "deliver")

    result = world.validate_and_commit(
        _contract_transaction(delivered_quantity=501),
        intents=[intent],
        current_minute=60,
    )

    assert not result.accepted
    assert any("not licensed by a complete declared transition contract" in error for error in result.errors)


def test_contract_owned_change_fails_when_actor_did_not_select_contract() -> None:
    world = _contract_world()
    intent = _contract_intent("inspect_quality", "produce")

    result = world.validate_and_commit(
        _contract_transaction(), intents=[intent], current_minute=60
    )

    assert not result.accepted
    assert any("not licensed by a complete declared transition contract" in error for error in result.errors)


def test_world_supports_typed_nested_state_fields() -> None:
    spec = bridge_port_spec()
    spec.initial_state.records["fuel_truck"].state["status"] = "available"
    authority = next(
        item for item in spec.authorities if item.authority_id == "port_deterministic_mechanics"
    )
    authority.patch_grammar.allowed_record_types.append("record")
    world = CanonicalWorld(spec)

    result = world.validate_and_commit(
        WorldTransaction(
            transaction_id="nested-state-update",
            base_revision=0,
            authority_id=authority.authority_id,
            intent_ids=["fixture"],
            operations=[
                PatchOperation(
                    operation="replace",
                    target=TypedTarget(
                        record_type="record",
                        record_id="fuel_truck",
                        field="state.status",
                    ),
                    value="assigned",
                )
            ],
            preconditions=[
                Precondition(
                    target=TypedTarget(
                        record_type="record",
                        record_id="fuel_truck",
                        field="state.status",
                    ),
                    expected="available",
                )
            ],
            consequences=[],
            evidence_refs=["fixture"],
            stated_rationale="Exercise a semantic nested state field.",
        )
    )

    assert result.accepted
    assert world.state.records["fuel_truck"].state["status"] == "assigned"


def test_create_operation_derives_redundant_identity_from_typed_target() -> None:
    spec = bridge_port_spec()
    authority = next(
        item for item in spec.authorities if item.authority_id == "port_semantic_adjudicator"
    )
    authority.patch_grammar.allowed_operations.append("create")
    authority.patch_grammar.allowed_record_types.append("record")
    world = CanonicalWorld(spec)

    result = world.validate_and_commit(
        WorldTransaction(
            transaction_id="create-derived-identity",
            base_revision=0,
            authority_id=authority.authority_id,
            intent_ids=["fixture"],
            operations=[
                PatchOperation(
                    operation="create",
                    target=TypedTarget(record_type="record", record_id="inspection_order"),
                    value={
                        "kind": "operational_instruction",
                        "label": "Inspect the alternate route",
                        "state": {"status": "pending"},
                    },
                )
            ],
            preconditions=[],
            consequences=[],
            evidence_refs=["fixture"],
            stated_rationale="The typed target owns canonical identity.",
        )
    )

    assert result.accepted
    assert world.state.records["inspection_order"].record_id == "inspection_order"


def test_strict_checkpoint_rejects_missing_canonical_world() -> None:
    simulation = _simulation(bridge_port_spec(), structured_stub)
    checkpoint = simulation.make_checkpoint_data()
    del checkpoint["game_masters"]["world_game_master"]["components"][
        "context_components"
    ]["canonical_world"]

    with pytest.raises(ValueError, match="invalid or incomplete"):
        _strict_checkpoint(checkpoint, bridge_port_spec())


@pytest.mark.parametrize(
    ("authority_id", "operation"),
    [
        (
            "port_deterministic_mechanics",
            PatchOperation(
                operation="rebind",
                target=TypedTarget(
                    record_type="placement", record_id="missing_truck", field="place_id"
                ),
                value="port",
            ),
        ),
        (
            "port_semantic_adjudicator",
            PatchOperation(
                operation="create",
                target=TypedTarget(record_type="route", record_id="unauthorized_route"),
                value={
                    "route_id": "unauthorized_route",
                    "origin_id": "outside_port",
                    "destination_id": "port",
                    "operational": True,
                },
            ),
        ),
        (
            "port_deterministic_mechanics",
            PatchOperation(
                operation="create",
                target=TypedTarget(record_type="route", record_id="dangling_route"),
                value={
                    "route_id": "dangling_route",
                    "origin_id": "missing_place",
                    "destination_id": "port",
                    "operational": True,
                },
            ),
        ),
        (
            "port_deterministic_mechanics",
            PatchOperation(
                operation="replace",
                target=TypedTarget(
                    record_type="resource", record_id="truck_fuel", field="quantity"
                ),
                value=-1.0,
            ),
        ),
    ],
)
def test_invalid_transaction_is_rejected_without_partial_mutation(
    authority_id: str, operation: PatchOperation
) -> None:
    world = _world(_simulation(bridge_port_spec(), structured_stub))
    before = state_hash(world.state)
    result = world.validate_and_commit(
        WorldTransaction(
            transaction_id=f"invalid-{operation.target.record_id}",
            base_revision=world.state.revision,
            authority_id=authority_id,
            intent_ids=["negative-control"],
            operations=[operation],
            preconditions=[],
            consequences=[],
            evidence_refs=["negative-control"],
            stated_rationale="Negative control.",
        )
    )

    assert not result.accepted
    assert state_hash(world.state) == before


def test_duplicate_consequence_id_is_rejected_atomically() -> None:
    world = _world(_simulation(bridge_port_spec(), structured_stub))
    _prepare_world(world)
    before = state_hash(world.state)

    result = world.validate_and_commit(
        WorldTransaction(
            transaction_id="duplicate-outbox-id",
            base_revision=world.state.revision,
            authority_id="port_semantic_adjudicator",
            intent_ids=["negative-control"],
            operations=[],
            preconditions=[],
            consequences=[
                Consequence(
                    consequence_id="temporary-route-open",
                    recipient_id="worker",
                    content="This proposed text must never be delivered.",
                    apparent_source="adjudicator",
                )
            ],
            evidence_refs=["negative-control"],
            stated_rationale="Negative control.",
        )
    )

    assert not result.accepted
    assert state_hash(world.state) == before


def test_stock_concordia_vertical_restores_and_commits_open_action() -> None:
    result = run_bridge_port_vertical(structured_stub)

    assert result.checkpoint_hash == result.restored_checkpoint_hash
    assert result.final_state.placements["worker"].place_id == "port"
    assert result.final_state.placements["fuel_truck"].place_id == "port"
    assert [item.validation.accepted for item in result.transition_evidence] == [
        False,
        True,
        True,
    ]
    assert [item.role for item in result.model_calls] == ["actor", "adjudicator"]
    assert result.adoption.simulation_class == "concordia.prefabs.simulation.generic.Simulation"
    assert result.adoption.engine_class == "concordia.environment.engines.sequential.Sequential"
    assert result.adoption.actor_selection_component.endswith(
        "next_acting.NextActingInFixedOrder"
    )
    assert "resolve" in result.adoption.lifecycle_events
    assert result.adoption.lifecycle_events.count("make_observation") == 2
    assert result.adoption.forbidden_runtime_imports == []
    assert "sabotage" not in json.dumps(
        [item.model_dump(mode="json") for item in result.actor_contexts]
    ).lower()
    assert result.actor_contexts[-1].private_memory == [
        "A temporary route is reported operational."
    ]
    assert any(
        observation.content
        == "Canonical world revision 2 committed: worker is at port; fuel_truck is at port."
        for observation in result.actor_contexts[-1].observations
    )


def test_concordia_adapter_does_not_import_legacy_project_runtimes() -> None:
    package = Path("src/cybernetic_influence/general_simulation")
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(package.glob("*.py"))
    )

    assert "CausalSession" not in source
    assert "ActiveRuntimeSession" not in source
    assert "active_runtime" not in source
    assert 'return ",".join(actor_ids)' not in source
