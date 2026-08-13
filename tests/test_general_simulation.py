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
    PatchOperation,
    Precondition,
    SemanticActionIntent,
    TypedTarget,
    WorldTransaction,
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
