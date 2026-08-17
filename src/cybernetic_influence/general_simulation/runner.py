"""General group execution on stock Concordia's simultaneous engine."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, cast

import numpy as np
from concordia.agents import entity_agent
from concordia.associative_memory import basic_associative_memory
from concordia.components.game_master import next_acting as concordia_next_acting
from concordia.environment.engines import simultaneous
from concordia.language_model import language_model, no_language_model
from concordia.prefabs.simulation import generic
from concordia.typing import entity as entity_lib
from concordia.typing import entity_component, prefab
from pydantic import TypeAdapter

from cybernetic_influence.llm_backend import CODEX_LUNA_MODEL

from .authoring_models import (
    GeneralPersonDraft,
    GeneralSimulationProposalV1,
    ScheduledMomentProposalV1,
)
from .compiler import CompiledGeneralSimulationV1, CompiledGeneralSimulationV2
from .contracts_v2 import ScenarioSpecV2
from .concordia_runtime import (
    ACTOR_CONTEXT_COMPONENT,
    CONCORDIA_REVISION,
    INBOX_COMPONENT,
    WORLD_COMPONENT,
    ActorContextComponent,
    InboxComponent,
    MemoryViewComponent,
    StructuredCall,
    _call_model,
    _structured_call,
)
from .models import (
    ActorContext,
    ActorDecision,
    Assimilation,
    AdoptionReceipt,
    GeneralGroupSimulationResult,
    GeneralGroupSimulationResultV2,
    GeneralMomentEvidence,
    ModelCallReceipt,
    PatchOperation,
    Precondition,
    SemanticActionIntent,
    TransitionAuthoritySpec,
    TypedTarget,
    WorldTransaction,
    WorldTransactionProposal,
)
from .world import CanonicalWorld


ProgressObserver = Callable[[dict[str, Any], dict[str, Any]], None]
CompiledGeneralSimulation = CompiledGeneralSimulationV1 | CompiledGeneralSimulationV2
ScenarioContract = GeneralSimulationProposalV1 | ScenarioSpecV2


def _compiled_scenario(compiled: CompiledGeneralSimulation) -> ScenarioContract:
    return compiled.scenario if isinstance(compiled, CompiledGeneralSimulationV2) else compiled.proposal


def _compiled_schedule(
    compiled: CompiledGeneralSimulation,
) -> list[ScheduledMomentProposalV1]:
    return (
        compiled.run_spec.scheduled_moments
        if isinstance(compiled, CompiledGeneralSimulationV2)
        else compiled.proposal.schedule
    )


def _normalize_existing_target(
    target: TypedTarget,
    world: CanonicalWorld,
    *,
    correction_context: str,
    corrections: list[str],
) -> TypedTarget:
    containers: dict[str, Mapping[str, object]] = {
        "record": world.state.records,
        "place": world.state.places,
        "placement": world.state.placements,
        "route": world.state.routes,
        "representation": world.state.representations,
        "resource": world.state.resources,
    }
    if target.record_id in containers[target.record_type]:
        return target
    matching_types = [
        record_type
        for record_type, records in containers.items()
        if target.record_id in records
    ]
    if len(matching_types) != 1:
        return target
    corrected_type = matching_types[0]
    corrections.append(
        f"{correction_context} target {target.record_id} normalized from "
        f"{target.record_type} to {corrected_type}"
    )
    return target.model_copy(update={"record_type": corrected_type})


def _normalize_record_state_field(
    target: TypedTarget,
    world: CanonicalWorld,
    *,
    correction_context: str,
    corrections: list[str],
) -> TypedTarget:
    if (
        target.record_type != "record"
        or target.field is None
        or target.field.startswith(("state.", "hidden_state."))
    ):
        return target
    record = world.state.records.get(target.record_id)
    if record is None or target.field not in record.state:
        return target
    corrected_field = f"state.{target.field}"
    corrections.append(
        f"{correction_context} target {target.record_id} field normalized from "
        f"{target.field} to {corrected_field}"
    )
    return target.model_copy(update={"field": corrected_field})


def _normalize_target(
    target: TypedTarget,
    world: CanonicalWorld,
    *,
    correction_context: str,
    corrections: list[str],
) -> TypedTarget:
    typed = _normalize_existing_target(
        target,
        world,
        correction_context=correction_context,
        corrections=corrections,
    )
    return _normalize_record_state_field(
        typed,
        world,
        correction_context=correction_context,
        corrections=corrections,
    )


def _normalize_transaction_targets(
    transaction: WorldTransaction,
    world: CanonicalWorld,
    corrections: list[str],
) -> WorldTransaction:
    operations = []
    for operation in transaction.operations:
        if (
            operation.operation == "create"
            and operation.target.record_type == "record"
            and isinstance(operation.value, dict)
            and "evidence_refs" in operation.value
        ):
            value = dict(operation.value)
            value.pop("evidence_refs", None)
            corrections.append(
                f"create-record evidence_refs retained at transaction level for {operation.target.record_id}"
            )
            operations.append(operation.model_copy(update={"value": value}))
            continue
        normalized = (
            operation
            if operation.operation == "create" and operation.target.field is None
            else operation.model_copy(
                update={
                    "target": _normalize_target(
                        operation.target,
                        world,
                        correction_context="operation",
                        corrections=corrections,
                    )
                }
            )
        )
        if (
            normalized.operation == "create"
            and normalized.target.field is not None
            and normalized.target.record_id
            in getattr(world.state, f"{normalized.target.record_type}s")
        ):
            if (
                normalized.target.record_type == "record"
                and "." not in normalized.target.field
                and normalized.target.field
                not in {
                    "record_id",
                    "kind",
                    "label",
                    "state",
                    "hidden_state",
                    "visible_to_actor_ids",
                }
            ):
                corrected_field = f"state.{normalized.target.field}"
                corrections.append(
                    f"operation target {normalized.target.record_id} field normalized "
                    f"from {normalized.target.field} to {corrected_field}"
                )
                normalized = normalized.model_copy(
                    update={
                        "target": normalized.target.model_copy(
                            update={"field": corrected_field}
                        )
                    }
                )
            corrections.append(
                "field-scoped create normalized to replace for existing "
                f"{normalized.target.record_type} {normalized.target.record_id}"
            )
            normalized = normalized.model_copy(update={"operation": "replace"})
        if (
            normalized.operation == "replace"
            and normalized.target.record_type == "record"
            and normalized.target.field == "state"
            and isinstance(normalized.value, dict)
        ):
            record = world.state.records.get(normalized.target.record_id)
            proposed_fields = set(normalized.value)
            if (
                record is not None
                and proposed_fields
                and set(record.state) <= proposed_fields
            ):
                corrections.append(
                    "whole record-state replacement expanded into typed fields "
                    f"for {normalized.target.record_id}"
                )
                operations.extend(
                    normalized.model_copy(
                        update={
                            "target": normalized.target.model_copy(
                                update={"field": f"state.{field}"}
                            ),
                            "value": value,
                        }
                    )
                    for field, value in normalized.value.items()
                )
                continue
        operations.append(normalized)
    preconditions = [
        precondition.model_copy(
            update={
                "target": _normalize_target(
                    precondition.target,
                    world,
                    correction_context="precondition",
                    corrections=corrections,
                )
            }
        )
        for precondition in transaction.preconditions
    ]
    return transaction.model_copy(
        update={"operations": operations, "preconditions": preconditions}
    )


def _inject_selected_contract_preconditions(
    transaction: WorldTransaction,
    *,
    intents: list[SemanticActionIntent],
    world: CanonicalWorld,
    corrections: list[str],
) -> WorldTransaction:
    """Attach trusted exact guards selected by actor intents.

    The adjudicator may restate these guards, but omission cannot weaken the
    compiled contract. Canonical validation still decides whether each guard
    passes against the frozen world revision.
    """

    selected_ids = {
        contract_id
        for intent in intents
        for contract_id in intent.transition_contract_ids
    }
    required = [
        precondition
        for contract in world.spec.resource_transport_contracts
        if contract.contract_id in selected_ids
        for precondition in contract.required_preconditions
    ]
    existing = {
        item.model_dump_json(exclude_none=False)
        for item in transaction.preconditions
    }
    additions = [
        item for item in required if item.model_dump_json(exclude_none=False) not in existing
    ]
    if not additions:
        return transaction
    corrections.append(
        "trusted exact contract preconditions injected: "
        + ", ".join(
            f"{item.target.record_type}:{item.target.record_id}:{item.target.field}"
            for item in additions
        )
    )
    return transaction.model_copy(
        update={"preconditions": [*transaction.preconditions, *additions]}
    )


def _materialize_unambiguous_exact_transformations(
    transaction: WorldTransaction,
    *,
    intents: list[SemanticActionIntent],
    world: CanonicalWorld,
    corrections: list[str],
) -> WorldTransaction:
    """Render a selected exact transformation from its trusted contract.

    The actor still decides whether to attempt a contract, and the LLM
    authority still reconciles coarse effects and communications. Once a
    selected exact transformation has an unambiguous batch count, however, its
    arithmetic and public inventory mirrors are mechanism-owned rather than
    prose-owned.

    One-batch contracts are intrinsically unambiguous. For a multi-batch
    contract, the adjudicator must propose a consistent input or output delta
    from which the batch count can be recovered. Overlapping exact transforms
    remain with the adjudicator until an explicit conflict policy exists.
    """

    selected_by_contract: dict[str, list[SemanticActionIntent]] = {}
    for intent in intents:
        for contract_id in intent.transition_contract_ids:
            selected_by_contract.setdefault(contract_id, []).append(intent)

    def controlled_targets(contract_id: str) -> set[tuple[str, str, str]]:
        contract = next(
            item
            for item in world.spec.resource_transformation_contracts
            if item.contract_id == contract_id
        )
        return {
            *{
                ("resource", resource_id, "quantity")
                for resource_id in contract.input_resource_quantities
            },
            ("resource", contract.output_resource_id, "quantity"),
            *{
                (
                    "record",
                    contract.public_inventory_record_id,
                    f"state.{field}",
                )
                for field in contract.public_inventory_input_fields.values()
            },
            (
                "record",
                contract.public_inventory_record_id,
                f"state.{contract.public_inventory_output_field}",
            ),
        }

    selected_contracts = [
        contract
        for contract in world.spec.resource_transformation_contracts
        if any(
            intent.actor_id in contract.operator_ids
            for intent in selected_by_contract.get(contract.contract_id, [])
        )
    ]
    target_owners: dict[tuple[str, str, str], list[str]] = {}
    for contract in selected_contracts:
        for target_key in controlled_targets(contract.contract_id):
            target_owners.setdefault(target_key, []).append(contract.contract_id)

    retained_operations = list(transaction.operations)
    added_operations: list[PatchOperation] = []
    added_preconditions: list[Precondition] = []
    materialized_ids: list[str] = []
    for contract in selected_contracts:
        targets = controlled_targets(contract.contract_id)
        if any(len(target_owners[target]) > 1 for target in targets):
            continue

        batch_candidates: set[int] = set()
        for operation in transaction.operations:
            if (
                operation.operation != "replace"
                or isinstance(operation.value, bool)
                or not isinstance(operation.value, (int, float))
            ):
                continue
            operation_target = operation.target
            if (
                operation_target.record_type == "resource"
                and operation_target.record_id == contract.output_resource_id
                and operation_target.field == "quantity"
            ):
                current = world.state.resources[operation_target.record_id].quantity
                delta = float(operation.value) - current
                candidate = round(delta / contract.output_quantity)
                if (
                    1 <= candidate <= contract.maximum_batches
                    and abs(delta - candidate * contract.output_quantity) <= 1e-9
                ):
                    batch_candidates.add(candidate)
            if (
                operation_target.record_type == "resource"
                and operation_target.record_id in contract.input_resource_quantities
                and operation_target.field == "quantity"
            ):
                current = world.state.resources[operation_target.record_id].quantity
                quantity = contract.input_resource_quantities[operation_target.record_id]
                delta = current - float(operation.value)
                candidate = round(delta / quantity)
                if (
                    1 <= candidate <= contract.maximum_batches
                    and abs(delta - candidate * quantity) <= 1e-9
                ):
                    batch_candidates.add(candidate)

        requested_batches: set[int] = set()
        for intent in selected_by_contract[contract.contract_id]:
            arguments = intent.transition_contract_arguments.get(contract.contract_id)
            if not arguments:
                continue
            candidate_batches = arguments.get("batches")
            if isinstance(candidate_batches, int) and not isinstance(
                candidate_batches, bool
            ):
                requested_batches.add(candidate_batches)
        batches: int | None
        if len(requested_batches) == 1:
            batches = next(iter(requested_batches))
        elif contract.maximum_batches == 1 and not requested_batches:
            # Compatibility for retained/reference decisions created before explicit
            # contract arguments became mandatory for new model outputs.
            batches = 1
        elif len(batch_candidates) == 1:
            batches = next(iter(batch_candidates))
        else:
            batches = None
        if batches is None:
            continue

        retained_operations = [
            operation
            for operation in retained_operations
            if (
                operation.target.record_type,
                operation.target.record_id,
                operation.target.field or "",
            )
            not in targets
        ]
        resulting_inputs: dict[str, float] = {}
        for resource_id, per_batch in contract.input_resource_quantities.items():
            required = per_batch * batches
            current = world.state.resources[resource_id].quantity
            resulting_inputs[resource_id] = current - required
            added_preconditions.append(
                Precondition(
                    target=TypedTarget(
                        record_type="resource",
                        record_id=resource_id,
                        field="quantity",
                    ),
                    comparison="greater_than_or_equal",
                    expected=required,
                )
            )
            added_operations.append(
                PatchOperation(
                    operation="replace",
                    target=TypedTarget(
                        record_type="resource",
                        record_id=resource_id,
                        field="quantity",
                    ),
                    value=resulting_inputs[resource_id],
                )
            )
        output = world.state.resources[contract.output_resource_id]
        resulting_output = output.quantity + contract.output_quantity * batches
        added_operations.append(
            PatchOperation(
                operation="replace",
                target=TypedTarget(
                    record_type="resource",
                    record_id=contract.output_resource_id,
                    field="quantity",
                ),
                value=resulting_output,
            )
        )
        for resource_id, field in contract.public_inventory_input_fields.items():
            added_operations.append(
                PatchOperation(
                    operation="replace",
                    target=TypedTarget(
                        record_type="record",
                        record_id=contract.public_inventory_record_id,
                        field=f"state.{field}",
                    ),
                    value=resulting_inputs[resource_id],
                )
            )
        added_operations.append(
            PatchOperation(
                operation="replace",
                target=TypedTarget(
                    record_type="record",
                    record_id=contract.public_inventory_record_id,
                    field=f"state.{contract.public_inventory_output_field}",
                ),
                value=resulting_output,
            )
        )
        materialized_ids.append(contract.contract_id)

    if not materialized_ids:
        return transaction
    existing_preconditions = {
        item.model_dump_json(exclude_none=False) for item in transaction.preconditions
    }
    unique_preconditions = [
        item
        for item in added_preconditions
        if item.model_dump_json(exclude_none=False) not in existing_preconditions
    ]
    corrections.append(
        "trusted runtime materialized selected exact transformation contracts: "
        + ", ".join(materialized_ids)
    )
    return transaction.model_copy(
        update={
            "operations": [*retained_operations, *added_operations],
            "preconditions": [*transaction.preconditions, *unique_preconditions],
        }
    )


def _materialize_unambiguous_exact_transports(
    transaction: WorldTransaction,
    *,
    intents: list[SemanticActionIntent],
    world: CanonicalWorld,
    current_minute: int,
    corrections: list[str],
) -> WorldTransaction:
    """Render selected parameterized transport attempts from trusted contracts."""

    retained_operations = list(transaction.operations)
    additions: list[PatchOperation] = []
    preconditions = list(transaction.preconditions)
    materialized: list[str] = []
    for contract in world.spec.resource_transport_contracts:
        selected = [
            intent
            for intent in intents
            if contract.contract_id in intent.transition_contract_ids
            and intent.actor_id in contract.operator_ids
        ]
        attempts: set[tuple[float, str]] = set()
        for intent in selected:
            arguments = intent.transition_contract_arguments.get(contract.contract_id)
            if not arguments:
                continue
            attempted_quantity = arguments.get("quantity")
            attempted_route = arguments.get("route_id")
            if (
                isinstance(attempted_quantity, (int, float))
                and not isinstance(attempted_quantity, bool)
                and isinstance(attempted_route, str)
            ):
                attempts.add((float(attempted_quantity), attempted_route))
        if len(attempts) != 1:
            continue
        quantity, route_id = next(iter(attempts))
        if not 0 < quantity <= contract.quantity or route_id not in contract.allowed_route_ids:
            continue
        route = world.state.routes[route_id]
        travel_time = route.public_state.get("travel_time_minutes")
        if not isinstance(travel_time, (int, float)):
            continue

        target_keys = {
            ("resource", contract.source_resource_id, "quantity"),
            ("resource", contract.destination_resource_id, "quantity"),
            ("record", contract.arrival_record_id, f"state.{contract.arrival_quantity_key}"),
            ("record", contract.arrival_record_id, f"state.{contract.usable_quantity_key}"),
            ("record", contract.arrival_record_id, f"state.{contract.arrival_minute_key}"),
        }
        retained_operations = [
            operation
            for operation in retained_operations
            if (
                operation.target.record_type,
                operation.target.record_id,
                operation.target.field or "",
            )
            not in target_keys
        ]
        source = world.state.resources[contract.source_resource_id]
        destination = world.state.resources[contract.destination_resource_id]
        additions.extend(
            [
                PatchOperation(
                    operation="replace",
                    target=TypedTarget(
                        record_type="resource",
                        record_id=contract.source_resource_id,
                        field="quantity",
                    ),
                    value=source.quantity - quantity,
                ),
                PatchOperation(
                    operation="replace",
                    target=TypedTarget(
                        record_type="resource",
                        record_id=contract.destination_resource_id,
                        field="quantity",
                    ),
                    value=destination.quantity + quantity,
                ),
                PatchOperation(
                    operation="replace",
                    target=TypedTarget(
                        record_type="record",
                        record_id=contract.arrival_record_id,
                        field=f"state.{contract.arrival_quantity_key}",
                    ),
                    value=quantity,
                ),
                PatchOperation(
                    operation="replace",
                    target=TypedTarget(
                        record_type="record",
                        record_id=contract.arrival_record_id,
                        field=f"state.{contract.usable_quantity_key}",
                    ),
                    value=quantity,
                ),
                PatchOperation(
                    operation="replace",
                    target=TypedTarget(
                        record_type="record",
                        record_id=contract.arrival_record_id,
                        field=f"state.{contract.arrival_minute_key}",
                    ),
                    value=current_minute + float(travel_time),
                ),
            ]
        )
        preconditions.extend(
            [
                Precondition(
                    target=TypedTarget(
                        record_type="resource",
                        record_id=contract.source_resource_id,
                        field="quantity",
                    ),
                    comparison="greater_than_or_equal",
                    expected=quantity,
                ),
                Precondition(
                    target=TypedTarget(
                        record_type="route", record_id=route_id, field="operational"
                    ),
                    expected=True,
                ),
                *contract.required_preconditions,
            ]
        )
        materialized.append(
            f"{contract.contract_id}(quantity={quantity:g}, route_id={route_id})"
        )
    if not materialized:
        return transaction
    unique_preconditions = list(
        {
            item.model_dump_json(exclude_none=False): item
            for item in preconditions
        }.values()
    )
    corrections.append(
        "trusted runtime materialized selected exact transport attempts: "
        + ", ".join(materialized)
    )
    return transaction.model_copy(
        update={
            "operations": [*retained_operations, *additions],
            "preconditions": unique_preconditions,
        }
    )


def _effective_transition_authority(
    world: CanonicalWorld,
    authority: TransitionAuthoritySpec,
    *,
    selected_contract_ids: set[str],
) -> TransitionAuthoritySpec:
    """Expose coarse grammar plus only the selected exact-contract patch shapes.

    Exact-contract operations remain licensed only when canonical attribution
    matches a selected contract. Keeping this view selection-scoped prevents an
    unrelated exact component from advertising patch shapes that the current
    intents cannot license at commit time.
    """

    allowed_operations = set(authority.patch_grammar.allowed_operations)
    allowed_record_types = set(authority.patch_grammar.allowed_record_types)
    selected_sensing = any(
        item.contract_id in selected_contract_ids
        for item in world.spec.sensing_contracts
    )
    selected_transformation = any(
        item.contract_id in selected_contract_ids
        for item in world.spec.resource_transformation_contracts
    )
    selected_transport = any(
        item.contract_id in selected_contract_ids
        for item in world.spec.resource_transport_contracts
    )
    if selected_sensing:
        allowed_operations.add("replace")
        allowed_record_types.add("record")
    if selected_transformation or selected_transport:
        allowed_operations.add("replace")
        allowed_record_types.update({"record", "resource"})
    if (
        allowed_operations == set(authority.patch_grammar.allowed_operations)
        and allowed_record_types == set(authority.patch_grammar.allowed_record_types)
    ):
        return authority
    return authority.model_copy(
        update={
            "patch_grammar": authority.patch_grammar.model_copy(
                update={
                    "allowed_operations": sorted(allowed_operations),
                    "allowed_record_types": sorted(allowed_record_types),
                }
            )
        }
    )


def _drop_unauthorized_representation_deliveries(
    transaction: WorldTransaction,
    world: CanonicalWorld,
    corrections: list[str],
) -> WorldTransaction:
    retained = []
    for consequence in transaction.consequences:
        if consequence.representation_id is None:
            retained.append(consequence)
            continue
        representation = world.state.representations.get(
            consequence.representation_id
        )
        if (
            representation is not None
            and consequence.recipient_id in representation.recipient_ids
        ):
            retained.append(consequence)
            continue
        corrections.append(
            "unauthorized representation delivery omitted: "
            f"{consequence.consequence_id}"
        )
    return transaction.model_copy(update={"consequences": retained})


def _drop_only_unlicensed_operations(
    transaction: WorldTransaction,
    errors: list[str],
) -> WorldTransaction | None:
    """Remove only extraneous effects while preserving truthful evidence.

    A transaction whose every operation failed exact-contract attribution is a
    failed attempt, not an acceptable no-op.  It must enter the bounded repair
    path so the model can correct the complete contract shape.  When only some
    operations are removed, their free-text consequences and rationale cannot
    survive as claims about effects that did not commit.
    """
    invalid_indices: set[int] = set()
    for error in errors:
        match = re.match(
            r"operation (\d+) on \w+ [^ ]+ is not licensed by a complete declared transition contract$",
            error,
        )
        if match is None:
            return None
        invalid_indices.add(int(match.group(1)))
    if not invalid_indices or max(invalid_indices) >= len(transaction.operations):
        return None
    if len(invalid_indices) == len(transaction.operations):
        return None
    retained = [
        operation
        for index, operation in enumerate(transaction.operations)
        if index not in invalid_indices
    ]
    return transaction.model_copy(
        update={
            "operations": retained,
            "consequences": [],
            "stated_rationale": (
                "Trusted validation removed explicitly unlicensed operations; "
                "only the retained operations were eligible to commit."
            ),
        }
    )


def _normalized_memory(value: str) -> str:
    return " ".join(value.lower().split())


def _memory_reference_is_grounded(reference: str, memories: set[str]) -> bool:
    """Accept one unambiguous retained-memory citation.

    Natural-language models sometimes cite the relevant leading sentence(s) of
    a retained memory instead of copying a later, unrelated sentence.  Treat a
    unique sentence-boundary prefix as a reference to that retained string,
    while continuing to reject paraphrases, fragments, and ambiguous prefixes.
    """
    normalized = _normalized_memory(reference)
    if not normalized:
        return False
    exact_matches = {memory for memory in memories if memory == normalized}
    if exact_matches:
        return True
    if len(normalized) < 24 or normalized[-1] not in ".?!":
        return False
    prefix_matches = {
        memory
        for memory in memories
        if memory.startswith(normalized) and len(memory) > len(normalized)
    }
    return len(prefix_matches) == 1


def _checkpoint_hash(checkpoint: Mapping[str, Any]) -> str:
    encoded = json.dumps(checkpoint, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def _strict_general_checkpoint(
    checkpoint: Mapping[str, Any],
    compiled: CompiledGeneralSimulation,
) -> dict[str, Any]:
    """Validate a persisted Concordia checkpoint before loading it.

    Stock Concordia deliberately tolerates missing names while restoring.  A
    resumable experiment cannot: silently omitting one actor, its memory, or
    the canonical world would create a different execution prefix.
    """
    try:
        retained = json.loads(json.dumps(dict(checkpoint)))
        scenario = _compiled_scenario(compiled)
        schedule = _compiled_schedule(compiled)
        expected_actors = {person.entity_id for person in scenario.people}
        entities = retained["entities"]
        game_masters = retained["game_masters"]
        if set(entities) != expected_actors:
            raise ValueError("checkpoint actor set differs from the approved proposal")
        if set(game_masters) != {"general_world_game_master"}:
            raise ValueError("checkpoint game-master set is incomplete")
        for actor_id in expected_actors:
            context = entities[actor_id]["components"]["context_components"]
            if set(context) != {ACTOR_CONTEXT_COMPONENT, "__memory__"}:
                raise ValueError(f"checkpoint components are incomplete for {actor_id}")
            entities[actor_id]["components"]["act_component"]["receipts"]
        gm_components = game_masters["general_world_game_master"]["components"]
        gm_components["act_component"]["moments"]
        gm_context = gm_components["context_components"]
        if set(gm_context) != {
            WORLD_COMPONENT,
            INBOX_COMPONENT,
            concordia_next_acting.DEFAULT_NEXT_ACTING_COMPONENT_KEY,
        }:
            raise ValueError("checkpoint game-master components are incomplete")
        world_state = gm_context[WORLD_COMPONENT]
        restored_world = CanonicalWorld(compiled.world_spec)
        restored_world.set_state(world_state)
        completed = len(gm_components["act_component"]["moments"])
        if completed > len(schedule):
            raise ValueError("checkpoint contains more moments than the approved schedule")
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("invalid or incomplete general-simulation checkpoint") from exc
    return cast(dict[str, Any], retained)


class GeneralActorActingComponent(entity_component.ActingComponent):  # type: ignore[misc]
    def __init__(
        self,
        call: StructuredCall,
        *,
        person: GeneralPersonDraft,
        trace_prefix: str,
        model: str,
        reasoning_effort: str,
        cognition_mode: str = "integrated",
    ) -> None:
        self._call = call
        self._person = person.model_copy(deep=True)
        self._trace_prefix = trace_prefix
        self._model = model
        self._reasoning_effort = reasoning_effort
        self._cognition_mode = cognition_mode
        self.receipts: list[ModelCallReceipt] = []
        self.activation_count = 0

    def _validate_decision(
        self, decision: ActorDecision, actor_context: ActorContext
    ) -> None:
        if decision.intent.actor_id != actor_context.actor_id:
            raise ValueError(
                f"actor_id must be {actor_context.actor_id!r}; received "
                f"{decision.intent.actor_id!r}"
            )
        if decision.intent.base_revision != actor_context.base_revision:
            raise ValueError(
                f"base_revision must be {actor_context.base_revision}; received "
                f"{decision.intent.base_revision}"
            )
        available_contract_ids = {
            item.contract_id for item in actor_context.available_transition_contracts
        }
        unknown_contract_ids = (
            set(decision.intent.transition_contract_ids) - available_contract_ids
        )
        if unknown_contract_ids:
            raise ValueError(
                "transition_contract_ids contained unavailable contracts "
                f"{sorted(unknown_contract_ids)}; allowed IDs are "
                f"{sorted(available_contract_ids)}"
            )
        arguments = decision.intent.transition_contract_arguments
        unknown_argument_ids = set(arguments) - set(decision.intent.transition_contract_ids)
        if unknown_argument_ids:
            raise ValueError(
                "transition_contract_arguments named unselected contracts "
                f"{sorted(unknown_argument_ids)}"
            )
        available_by_id = {
            item.contract_id: item for item in actor_context.available_transition_contracts
        }
        for contract_id in decision.intent.transition_contract_ids:
            contract = available_by_id[contract_id]
            supplied = arguments.get(contract_id)
            if contract.contract_kind == "sensing":
                if supplied not in (None, {}):
                    raise ValueError(
                        f"sensing contract {contract_id} accepts no arguments"
                    )
                continue
            if supplied is None:
                raise ValueError(
                    f"selected {contract.contract_kind} contract {contract_id} requires "
                    "structured transition_contract_arguments"
                )
            if contract.contract_kind == "resource_transformation":
                batches = supplied.get("batches")
                batches_schema = contract.argument_schema.get("batches")
                maximum = (
                    batches_schema.get("maximum")
                    if isinstance(batches_schema, dict)
                    else None
                )
                if (
                    isinstance(batches, bool)
                    or not isinstance(batches, int)
                    or not isinstance(maximum, int)
                    or not 1 <= batches <= maximum
                    or set(supplied) != {"batches"}
                ):
                    raise ValueError(
                        f"contract {contract_id} requires integer batches from 1 to {maximum}"
                    )
            elif contract.contract_kind == "resource_transport":
                quantity = supplied.get("quantity")
                route_id = supplied.get("route_id")
                quantity_schema = contract.argument_schema.get("quantity")
                route_schema = contract.argument_schema.get("route_id")
                maximum = (
                    quantity_schema.get("maximum")
                    if isinstance(quantity_schema, dict)
                    else None
                )
                allowed_routes = (
                    route_schema.get("enum") if isinstance(route_schema, dict) else None
                )
                if (
                    isinstance(quantity, bool)
                    or not isinstance(quantity, (int, float))
                    or not isinstance(maximum, (int, float))
                    or not 0 < float(quantity) <= float(maximum)
                    or not isinstance(route_id, str)
                    or not isinstance(allowed_routes, list)
                    or route_id not in allowed_routes
                    or set(supplied) != {"quantity", "route_id"}
                ):
                    raise ValueError(
                        f"contract {contract_id} requires quantity in (0, {maximum}] and "
                        f"route_id in {allowed_routes}"
                    )
        available_observations = {
            item.observation_id for item in actor_context.observations
        }
        unknown_attention = (
            set(decision.assimilation.attended_observation_ids)
            - available_observations
        )
        if unknown_attention:
            raise ValueError(
                "attended_observation_ids contained unavailable IDs "
                f"{sorted(unknown_attention)}; allowed IDs are "
                f"{sorted(available_observations)}"
            )
        available_provenance = available_observations | {
            item.representation_id
            for item in actor_context.observations
            if item.representation_id is not None
        } | {item.record_id for item in actor_context.accessible_records} | {
            item.route_id for item in actor_context.accessible_routes
        }
        unknown_provenance = (
            set(decision.assimilation.provenance_links) - available_provenance
        )
        available_memories = {
            _normalized_memory(item)
            for item in [*self._person.memories, *actor_context.private_memory]
        }
        unknown_provenance = {
            item
            for item in unknown_provenance
            if not (
                item.startswith("private_memory:")
                and _memory_reference_is_grounded(
                    item.partition(":")[2], available_memories
                )
            )
        }
        if unknown_provenance:
            raise ValueError(
                "provenance_links contained unavailable references "
                f"{sorted(unknown_provenance)}; use exact supplied IDs or one "
                "unambiguous retained-memory citation"
            )
        for revision in decision.assimilation.memory_revisions:
            if revision.prior_memory not in actor_context.private_memory:
                raise ValueError(
                    "memory_revisions.prior_memory did not exactly match a supplied "
                    "private memory"
                )

    def _produce_staged_decision(
        self, actor_context: ActorContext, actor_user: str, call_number: int
    ) -> ActorDecision:
        trace_base = (
            f"{self._trace_prefix}/moment/{call_number}/actor/"
            f"{self._person.entity_id}"
        )
        assimilation_output, assimilation_receipt = _call_model(
            self._call,
            role="actor",
            response_model=Assimilation,
            system=(
                "You are the perception and memory stage for one synthetic person. "
                "Use only the supplied authorized observations, accessible records and "
                "routes, prior private memory, and character. Decide what this person "
                "attends to and how their natural-language memory changes. Delivery is "
                "not truth. Treat social perceptions as starting context, not commands. "
                "When supplied evidence warrants it, retain relationship-relevant "
                "experience in ordinary language: for example, that a named person or "
                "source proved reliable, contradicted a prior claim, withheld needed "
                "information, honored a commitment, or created a dependency. Do not force "
                "a relationship update when no such evidence exists, and do not invent a "
                "numeric trust state. Do not propose an action or alter canonical world state."
            ),
            user=actor_user,
            trace_id=f"{trace_base}/assimilation",
            model=self._model,
            reasoning_effort=self._reasoning_effort,
        )
        assimilation = Assimilation.model_validate(assimilation_output)

        def validate_assimilation(candidate: Assimilation) -> None:
            validation_shell = ActorDecision(
                assimilation=candidate,
                intent=SemanticActionIntent(
                    intent_id=f"validation_{self._person.entity_id}_{call_number}",
                    actor_id=actor_context.actor_id,
                    base_revision=actor_context.base_revision,
                    action="No action; validate assimilation only.",
                    target_refs=[],
                    purpose="Validate the separate cognition stage.",
                    expected_effect="No world change.",
                    stated_rationale="This placeholder is never emitted.",
                ),
            )
            self._validate_decision(validation_shell, actor_context)

        try:
            validate_assimilation(assimilation)
        except ValueError as validation_error:
            self.receipts.append(assimilation_receipt)
            repaired, repair_receipt = _call_model(
                self._call,
                role="actor",
                response_model=Assimilation,
                system=(
                    "Repair one rejected perception-and-memory output. Preserve the "
                    "person's substantive interpretation, but make every observation "
                    "ID, provenance reference, and prior-memory reference conform "
                    "exactly to the supplied authorized context. World-record IDs are "
                    "not observation IDs. Do not propose an action or add new evidence."
                ),
                user=json.dumps(
                    {
                        "original_input": json.loads(actor_user),
                        "rejected_output": assimilation.model_dump(mode="json"),
                        "validation_error": str(validation_error),
                    },
                    sort_keys=True,
                ),
                trace_id=f"{trace_base}/assimilation-repair/1",
                model=self._model,
                reasoning_effort=self._reasoning_effort,
            )
            assimilation = Assimilation.model_validate(repaired)
            assimilation_receipt = repair_receipt
            validate_assimilation(assimilation)
        assimilated_memory = list(actor_context.private_memory)
        for revision in assimilation.memory_revisions:
            index = assimilated_memory.index(revision.prior_memory)
            assimilated_memory[index] = revision.revised_memory
        assimilated_memory.extend(assimilation.memory_additions)
        action_output, action_receipt = _call_model(
            self._call,
            role="actor",
            response_model=SemanticActionIntent,
            system=(
                "You are the action-selection stage for one synthetic person. The prior "
                "perception stage is retained and cannot be revised here. Using that exact "
                "assimilation, the updated private memory, character, and available transition "
                "contracts, return one coherent bounded semantic action intent against the "
                "supplied world revision. A capability or contract permits an attempt; it does "
                "not guarantee authorization or success. For every selected resource contract, "
                "supply the exact structured arguments required by its argument_schema. The "
                "natural-language action must describe the same quantity, route, or batch count; "
                "the structured arguments govern the canonical attempt."
            ),
            user=json.dumps(
                {
                    "person": self._person.model_dump(mode="json"),
                    "actor_context": actor_context.model_dump(mode="json"),
                    "retained_assimilation": assimilation.model_dump(mode="json"),
                    "assimilated_private_memory": assimilated_memory,
                },
                sort_keys=True,
            ),
            trace_id=f"{trace_base}/action",
            model=self._model,
            reasoning_effort=self._reasoning_effort,
        )
        action = SemanticActionIntent.model_validate(action_output)
        decision = ActorDecision(assimilation=assimilation, intent=action)
        try:
            self._validate_decision(decision, actor_context)
        except ValueError as validation_error:
            self.receipts.append(action_receipt)
            repaired, repair_receipt = _call_model(
                self._call,
                role="actor",
                response_model=SemanticActionIntent,
                system=(
                    "Repair one rejected action-selection output. Preserve the person's "
                    "substantive judgment, but make actor identity, world revision, target "
                    "references, and transition-contract selections conform exactly to the "
                    "supplied authorized context. Make each selected resource contract's structured "
                    "arguments satisfy its argument_schema, and make the action prose agree with "
                    "those arguments. Do not change the retained assimilation."
                ),
                user=json.dumps(
                    {
                        "original_input": json.loads(action_receipt.input_context),
                        "rejected_output": action.model_dump(mode="json"),
                        "validation_error": str(validation_error),
                    },
                    sort_keys=True,
                ),
                trace_id=f"{trace_base}/action-repair/1",
                model=self._model,
                reasoning_effort=self._reasoning_effort,
            )
            action = SemanticActionIntent.model_validate(repaired)
            action_receipt = repair_receipt
            decision = ActorDecision(assimilation=assimilation, intent=action)
            self._validate_decision(decision, actor_context)
        self.receipts.extend([assimilation_receipt, action_receipt])
        return decision

    def _produce_action_attempt(
        self,
        context: entity_component.ComponentContextMapping,
        action_spec: entity_lib.ActionSpec,
    ) -> str:
        del action_spec
        actor_context = ActorContext.model_validate_json(context[ACTOR_CONTEXT_COMPONENT])
        self.activation_count += 1
        call_number = self.activation_count
        actor_user = json.dumps(
            {
                "person": self._person.model_dump(mode="json"),
                "actor_context": actor_context.model_dump(mode="json"),
            },
            sort_keys=True,
        )
        if self._cognition_mode == "staged":
            decision = self._produce_staged_decision(
                actor_context, actor_user, call_number
            )
            receipt = None
        else:
            parsed, receipt = _call_model(
                self._call,
                role="actor",
                response_model=ActorDecision,
                system=(
                    "You are one synthetic person in an exploratory causal simulation. "
                    "Use only the supplied authorized observations, accessible world records, "
                    "private memory, and character. Delivery is not truth and an attempted action "
                    "is not guaranteed to succeed. Return an assimilation record and one coherent, "
                    "bounded open-ended semantic action intent against the supplied world revision. "
                    "The phase responsibilities describe the requested work, not a dictated outcome. "
                    "When several supplied transition contracts are jointly necessary and you are "
                    "authorized to attempt them, one coherent intent may select all of their exact "
                    "contract IDs. Otherwise select only the contracts you actually attempt. Selecting "
                    "a contract permits only an attempt; it does not guarantee authorization or success. "
                    "For every selected resource contract, supply the exact arguments required by its "
                    "argument_schema and describe those same values in the action prose. Structured "
                    "arguments govern the canonical attempt."
                ),
                user=actor_user,
                trace_id=(
                    f"{self._trace_prefix}/moment/{call_number}/actor/"
                    f"{self._person.entity_id}"
                ),
                model=self._model,
                reasoning_effort=self._reasoning_effort,
            )
            decision = ActorDecision.model_validate(parsed)
            try:
                self._validate_decision(decision, actor_context)
            except ValueError as validation_error:
                self.receipts.append(receipt)
                repaired, repair_receipt = _call_model(
                self._call,
                role="actor",
                response_model=ActorDecision,
                system=(
                    "Repair one rejected synthetic-person output. Preserve the actor's "
                    "substantive judgment, but make every typed identity, revision, "
                    "observation ID, provenance reference, and prior-memory reference "
                    "conform exactly to the supplied authorized context. Do not add new "
                    "evidence or change the world. Return only the corrected typed output."
                ),
                user=json.dumps(
                    {
                        "original_input": json.loads(actor_user),
                        "rejected_output": decision.model_dump(mode="json"),
                        "validation_error": str(validation_error),
                    },
                    sort_keys=True,
                ),
                trace_id=(
                    f"{self._trace_prefix}/moment/{call_number}/actor/"
                    f"{self._person.entity_id}/repair/1"
                ),
                model=self._model,
                reasoning_effort=self._reasoning_effort,
            )
                decision = ActorDecision.model_validate(repaired)
                receipt = repair_receipt
                self._validate_decision(decision, actor_context)
        context_component = self.get_entity().get_component(
            ACTOR_CONTEXT_COMPONENT, type_=ActorContextComponent
        )
        if context_component.context is not None:
            for revision in decision.assimilation.memory_revisions:
                index = context_component.context.private_memory.index(
                    revision.prior_memory
                )
                context_component.context.private_memory[index] = revision.revised_memory
            context_component.context.private_memory.extend(
                decision.assimilation.memory_additions
            )
        if receipt is not None:
            self.receipts.append(receipt)
        return decision.intent.model_dump_json()

    def get_action_attempt(
        self,
        context: entity_component.ComponentContextMapping,
        action_spec: entity_lib.ActionSpec,
    ) -> str:
        """Return a parseable failure envelope instead of letting Concordia hide it.

        Stock Concordia logs and suppresses exceptions from concurrent actor
        activations.  A failed actor must therefore travel through the same
        simultaneous batch to the game master, which can fail the run loudly
        with the actual cause rather than a misleading missing-intents error.
        """
        try:
            return self._produce_action_attempt(context, action_spec)
        except Exception as exc:
            return (
                f"{self._person.entity_id}: __actor_failure__ "
                f"{type(exc).__name__}: {exc}"
            )

    def get_state(self) -> entity_component.ComponentState:
        return {
            "receipts": [item.model_dump(mode="json") for item in self.receipts],
            "activation_count": self.activation_count,
        }

    def set_state(self, state: entity_component.ComponentState) -> None:
        self.receipts = TypeAdapter(list[ModelCallReceipt]).validate_python(state["receipts"])
        self.activation_count = int(state.get("activation_count", len(self.receipts)))


class GeneralGameMasterActingComponent(entity_component.ActingComponent):  # type: ignore[misc]
    def __init__(
        self,
        call: StructuredCall,
        *,
        scenario: ScenarioContract,
        schedule: list[ScheduledMomentProposalV1],
        authority_id: str,
        trace_prefix: str,
        model: str,
        reasoning_effort: str,
    ) -> None:
        self._call = call
        self._scenario = scenario.model_copy(deep=True)
        self._schedule = [item.model_copy(deep=True) for item in schedule]
        self._authority_id = authority_id
        self._trace_prefix = trace_prefix
        self._model = model
        self._reasoning_effort = reasoning_effort
        self.receipts: list[ModelCallReceipt] = []
        self.moments: list[GeneralMomentEvidence] = []
        self.lifecycle_events: list[str] = []

    def _world(self) -> CanonicalWorld:
        return cast(
            CanonicalWorld,
            self.get_entity().get_component(WORLD_COMPONENT, type_=CanonicalWorld),
        )

    def _moment(self) -> Any:
        if len(self.moments) >= len(self._schedule):
            return self._schedule[-1]
        return self._schedule[len(self.moments)]

    def _delivered_representations(self) -> set[str]:
        current_minute = self._moment().minute
        return {
            representation_id
            for moment in self._schedule
            if moment.minute <= current_minute
            for representation_id in moment.external_inject_representation_ids
        }

    def _active_component_requests(self) -> list[dict[str, object]]:
        request_ids = set(self._moment().active_component_request_ids)
        return [
            item.model_dump(mode="json")
            for item in self._scenario.component_requests
            if item.request_id in request_ids
        ]

    def _active_transition_contracts(self) -> tuple[set[str], set[str], set[str]]:
        """Return the exact contracts this moment may adjudicate by family."""
        active_ids = set(self._moment().active_transition_contract_ids)
        return (
            {item.rule_id for item in self._scenario.sensing_rules if item.rule_id in active_ids},
            {
                item.transformation_id
                for item in self._scenario.resource_transformations
                if item.transformation_id in active_ids
            },
            {
                item.transport_id
                for item in self._scenario.resource_transports
                if item.transport_id in active_ids
            },
        )

    def get_action_attempt(
        self,
        context: entity_component.ComponentContextMapping,
        action_spec: entity_lib.ActionSpec,
    ) -> str:
        del context
        output_type = action_spec.output_type
        self.lifecycle_events.append(output_type.value)
        actor_ids = [person.entity_id for person in self._scenario.people]
        if output_type == entity_lib.OutputType.TERMINATE:
            return "Yes" if len(self.moments) >= len(self._schedule) else "No"
        if output_type == entity_lib.OutputType.NEXT_ACTING:
            selector = self.get_entity().get_component(
                concordia_next_acting.DEFAULT_NEXT_ACTING_COMPONENT_KEY,
                type_=concordia_next_acting.NextActingAllEntities,
            )
            return str(selector.pre_act(action_spec))
        if output_type == entity_lib.OutputType.NEXT_ACTION_SPEC:
            return "prompt: Propose one coherent bounded action plan from your authorized context.;;type: free"
        if output_type == entity_lib.OutputType.MAKE_OBSERVATION:
            actor_id = next(
                (candidate for candidate in actor_ids if candidate in action_spec.call_to_action),
                None,
            )
            if actor_id is None:
                raise ValueError("Concordia observation request did not name a configured actor")
            self._world().drain_outbox(actor_id)
            moment = self._moment()
            responsibilities = [
                item.behavior_description
                for item in self._scenario.component_requests
                if item.request_id in moment.active_component_request_ids
                and actor_id in item.subject_refs
            ]
            return self._world().actor_context(
                actor_id,
                current_minute=moment.minute,
                delivered_representation_ids=self._delivered_representations(),
                active_transition_contract_ids=set(
                    moment.active_transition_contract_ids
                ),
                phase_description=moment.description,
                phase_responsibilities=responsibilities,
            ).model_dump_json()
        if output_type == entity_lib.OutputType.RESOLVE:
            inbox = self.get_entity().get_component(INBOX_COMPONENT, type_=InboxComponent)
            if inbox.putative_event is None:
                raise RuntimeError("joint resolution requested without actor intents")
            intents: list[SemanticActionIntent] = []
            actor_failures: list[str] = []
            for line in inbox.putative_event.splitlines():
                raw = line.removeprefix("[putative_event]").strip()
                actor_id, separator, payload = raw.partition(":")
                if not separator or actor_id.strip() not in actor_ids:
                    continue
                if payload.strip().startswith("__actor_failure__"):
                    actor_failures.append(
                        f"{actor_id.strip()}: {payload.strip().removeprefix('__actor_failure__').strip()}"
                    )
                    continue
                intents.append(SemanticActionIntent.model_validate_json(payload.strip()))
            if actor_failures:
                raise RuntimeError(
                    "one or more same-moment actors failed before joint resolution: "
                    + "; ".join(actor_failures)
                )
            if {item.actor_id for item in intents} != set(actor_ids):
                received = {item.actor_id for item in intents}
                missing = sorted(set(actor_ids) - received)
                duplicate = sorted(
                    item.actor_id
                    for item in intents
                    if sum(other.actor_id == item.actor_id for other in intents) > 1
                )
                raise ValueError(
                    "joint resolution did not receive one intent from every actor; "
                    f"missing={missing}; duplicate={sorted(set(duplicate))}"
                )
            frozen_revisions = {item.base_revision for item in intents}
            world = self._world()
            if frozen_revisions != {world.state.revision}:
                raise ValueError("same-moment actors did not reason from one frozen revision")
            authority = next(
                item for item in world.spec.authorities if item.authority_id == self._authority_id
            )
            selected_contract_ids = {
                contract_id
                for intent in intents
                for contract_id in intent.transition_contract_ids
            }
            effective_authority = _effective_transition_authority(
                world,
                authority,
                selected_contract_ids=selected_contract_ids,
            )
            moment = self._moment()
            active_sensing_rules, active_transformations, active_transports = (
                self._active_transition_contracts()
            )
            parsed, receipt = _call_model(
                self._call,
                role="adjudicator",
                response_model=WorldTransactionProposal,
                system=(
                    "You are a bounded joint transition authority in an exploratory simulation. "
                    "Reconcile the same-revision semantic intents into one transaction containing "
                    "only mutations allowed by the supplied effective patch grammar. That grammar "
                    "combines the coarse authority with configured exact-contract patch shapes; exact "
                    "operations still commit only when canonical attribution matches a selected "
                    "contract. You propose; canonical "
                    "validation determines whether the transaction commits. Do not put hidden world "
                    "facts into actor-visible consequences. Do not assess an analyst objective or "
                    "declare whether the simulation succeeded; this authority only adjudicates the "
                    "supplied actor intents against canonical state. "
                    "You may use canonical hidden state to adjudicate the result of a scoped sensing "
                    "or inspection intent, but expose only the resulting public finding through a "
                    "record-state operation; never quote unrelated hidden state. When canonical stocks "
                    "and an actor intent support a bounded material transformation, express it through "
                    "preconditioned resource quantity changes and matching public inventory-record "
                    "changes. Quantities may never become negative. Do not merely record that an attempt "
                    "was requested when the supplied world state lets this authority adjudicate its result. "
                    "Actor communications belong in consequences; do not create, replace, or rebind "
                    "information representations unless the supplied grammar explicitly permits the "
                    "representation target type. "
                    "Apply only the active component requests and transition contracts for this moment; do not perform a later phase early. "
                    "A sensing rule "
                    "reveals only its named hidden keys when a permitted observer actually attempts it. "
                    "For a sensing result, update only the public output fields named by "
                    "hidden_to_output_fields; do not add a status, explanation, or other output field. "
                    "A transformation may execute only when a permitted operator attempts it and every "
                    "declared input quantity is available; apply at most maximum_batches and update the "
                    "named public inventory record in the same transaction. A resource transport may "
                    "execute only when a permitted operator attempts it, the source quantity is available, "
                    "and one allowed directed route connects the declared origin and destination and is "
                    "operational. Move no more than the declared quantity by decrementing the source resource "
                    "and incrementing the destination resource in one transaction. Derive arrival minute from "
                    "the current moment plus the selected route's public travel_time_minutes, and update only "
                    "the three declared arrival-record keys. Every configured required_precondition is a "
                    "non-negotiable exact guard; the trusted runtime attaches it to a selected transport and "
                    "canonical validation rejects the transition when it is false. A transport attempt is not "
                    "permission or success."
                ),
                user=json.dumps(
                    {
                        "moment": moment.model_dump(mode="json"),
                        "world": world.state.model_dump(mode="json"),
                        "intents": [item.model_dump(mode="json") for item in intents],
                        "authority": effective_authority.model_dump(mode="json"),
                        "active_component_requests": self._active_component_requests(),
                        "active_transition_contract_ids": moment.active_transition_contract_ids,
                        "configured_active_systems": [
                            item.model_dump(mode="json")
                            for item in self._scenario.active_systems
                        ],
                        "sensing_contracts": [
                            item.model_dump(mode="json")
                            for item in world.spec.sensing_contracts
                            if item.contract_id in active_sensing_rules
                        ],
                        "resource_transformation_contracts": [
                            item.model_dump(mode="json")
                            for item in world.spec.resource_transformation_contracts
                            if item.contract_id in active_transformations
                        ],
                        "resource_transports": [
                            item.model_dump(mode="json")
                            for item in self._scenario.resource_transports
                            if item.transport_id in active_transports
                        ],
                        "requirements": {
                            "authority_id": self._authority_id,
                            "base_revision": world.state.revision,
                            "intent_ids": [item.intent_id for item in intents],
                            "actor_visible_consequences_may_name": actor_ids,
                            "evidence_refs_may_name": sorted(
                                {
                                    *[item.intent_id for item in intents],
                                    moment.moment_id,
                                    *world.state.records,
                                    *world.state.places,
                                    *world.state.routes,
                                    *world.state.representations,
                                    *world.state.resources,
                                }
                            ),
                        },
                    },
                    sort_keys=True,
                ),
                trace_id=f"{self._trace_prefix}/moment/{len(self.moments) + 1}/adjudicator",
                timeout_s=180,
                model=self._model,
                reasoning_effort=self._reasoning_effort,
            )
            proposed_transaction = WorldTransactionProposal.model_validate(
                parsed.model_dump(mode="json", exclude_none=True)
            ).as_transaction()
            expected_intents = {item.intent_id for item in intents}
            corrections: list[str] = []
            if proposed_transaction.authority_id != self._authority_id:
                corrections.append("authority_id restored from trusted runtime")
            if proposed_transaction.base_revision != world.state.revision:
                corrections.append("base_revision restored from trusted runtime")
            if set(proposed_transaction.intent_ids) != expected_intents:
                corrections.append("intent_ids restored from collected Concordia actions")
            transaction = proposed_transaction.model_copy(
                update={
                    "authority_id": self._authority_id,
                    "base_revision": world.state.revision,
                    "intent_ids": [item.intent_id for item in intents],
                }
            )
            transaction = _normalize_transaction_targets(
                transaction, world, corrections
            )
            transaction = _materialize_unambiguous_exact_transformations(
                transaction,
                intents=intents,
                world=world,
                corrections=corrections,
            )
            transaction = _materialize_unambiguous_exact_transports(
                transaction,
                intents=intents,
                world=world,
                current_minute=moment.minute,
                corrections=corrections,
            )
            transaction = _inject_selected_contract_preconditions(
                transaction,
                intents=intents,
                world=world,
                corrections=corrections,
            )
            allowed_evidence_refs = (
                expected_intents
                | {moment.moment_id}
                | set(world.state.records)
                | set(world.state.places)
                | set(world.state.routes)
                | set(world.state.representations)
                | set(world.state.resources)
            )
            allowed_evidence_refs |= {
                f"{record_type}:{record_id}"
                for record_type, record_ids in (
                    ("record", world.state.records),
                    ("place", world.state.places),
                    ("route", world.state.routes),
                    ("representation", world.state.representations),
                    ("resource", world.state.resources),
                )
                for record_id in record_ids
            }
            unknown_evidence_refs = set(transaction.evidence_refs) - allowed_evidence_refs
            if unknown_evidence_refs:
                corrections.append(
                    "unknown stated evidence references omitted: "
                    + ", ".join(sorted(unknown_evidence_refs))
                )
                transaction = transaction.model_copy(
                    update={
                        "evidence_refs": [
                            item for item in transaction.evidence_refs
                            if item in allowed_evidence_refs
                        ]
                    }
                )
            unknown_recipients = {
                item.recipient_id for item in transaction.consequences
            } - set(actor_ids)
            if unknown_recipients:
                raise ValueError("adjudicator consequence named an unknown actor")
            transaction = _drop_unauthorized_representation_deliveries(
                transaction, world, corrections
            )
            frozen_revision = world.state.revision
            validation = world.validate_and_commit(
                transaction,
                envelope_corrections=corrections,
                intents=intents,
                current_minute=moment.minute,
            )
            repairable_shape_errors = [
                error
                for error in validation.errors
                if "outside authority grammar" in error
                or "not licensed by a complete declared transition contract" in error
            ]
            if repairable_shape_errors and len(repairable_shape_errors) == len(
                validation.errors
            ):
                pruned_transaction = _drop_only_unlicensed_operations(
                    transaction, validation.errors
                )
                if pruned_transaction is not None:
                    pruned_validation = world.validate_and_commit(
                        pruned_transaction,
                        envelope_corrections=[
                            "trusted runtime removed only the explicitly unlicensed operations"
                        ],
                        intents=intents,
                        current_minute=moment.minute,
                    )
                    if pruned_validation.accepted:
                        transaction = pruned_transaction
                        validation = pruned_validation
                        repairable_shape_errors = []
            if repairable_shape_errors and len(repairable_shape_errors) == len(
                validation.errors
            ):
                self.receipts.append(receipt)
                repaired, repair_receipt = _call_model(
                    self._call,
                    role="adjudicator",
                    response_model=WorldTransactionProposal,
                    system=(
                        "Repair one rejected transition-authority output whose patch shape "
                        "did not match its authority or selected exact contract. Preserve the "
                        "substantive judgment, but remove undeclared effects and use only "
                        "operations and target record types in the supplied authority patch grammar. Actor-visible "
                        "communications belong in consequences; do not create, replace, "
                        "or rebind information representations unless the grammar explicitly "
                        "allows that target type. For exact sensing, write only the mapped "
                        "public output fields. Do not evade a failed precondition or world "
                        "invariant, change canonical facts to make an action pass, or invent "
                        "new evidence. Return only the corrected typed transaction."
                    ),
                    user=json.dumps(
                        {
                            "original_input": {
                                "moment": moment.model_dump(mode="json"),
                                "world": world.state.model_dump(mode="json"),
                                "intents": [item.model_dump(mode="json") for item in intents],
                                "authority": effective_authority.model_dump(mode="json"),
                                "active_component_requests": self._active_component_requests(),
                                "sensing_contracts": [
                                    item.model_dump(mode="json")
                                    for item in world.spec.sensing_contracts
                                    if item.contract_id in active_sensing_rules
                                ],
                                "resource_transformation_contracts": [
                                    item.model_dump(mode="json")
                                    for item in world.spec.resource_transformation_contracts
                                    if item.contract_id in active_transformations
                                ],
                                "resource_transports": [
                                    item.model_dump(mode="json")
                                    for item in self._scenario.resource_transports
                                    if item.transport_id in active_transports
                                ],
                                "requirements": {
                                    "authority_id": self._authority_id,
                                    "base_revision": world.state.revision,
                                    "intent_ids": [item.intent_id for item in intents],
                                    "actor_visible_consequences_may_name": actor_ids,
                                },
                            },
                            "rejected_output": transaction.model_dump(mode="json"),
                            "validation_errors": validation.errors,
                        },
                        sort_keys=True,
                    ),
                    trace_id=(
                        f"{self._trace_prefix}/moment/{len(self.moments) + 1}/"
                        "adjudicator/repair/1"
                    ),
                    timeout_s=180,
                    model=self._model,
                    reasoning_effort=self._reasoning_effort,
                )
                repaired_transaction = WorldTransactionProposal.model_validate(
                    repaired.model_dump(mode="json", exclude_none=True)
                ).as_transaction().model_copy(
                    update={
                        "authority_id": self._authority_id,
                        "base_revision": world.state.revision,
                        "intent_ids": [item.intent_id for item in intents],
                    }
                )
                repair_corrections: list[str] = []
                repaired_transaction = _normalize_transaction_targets(
                    repaired_transaction, world, repair_corrections
                )
                repaired_transaction = _materialize_unambiguous_exact_transformations(
                    repaired_transaction,
                    intents=intents,
                    world=world,
                    corrections=repair_corrections,
                )
                repaired_transaction = _inject_selected_contract_preconditions(
                    repaired_transaction,
                    intents=intents,
                    world=world,
                    corrections=repair_corrections,
                )
                if set(repaired_transaction.evidence_refs) - allowed_evidence_refs:
                    raise ValueError("repaired adjudicator output cited unknown canonical evidence")
                repaired_unknown_recipients = {
                    item.recipient_id for item in repaired_transaction.consequences
                } - set(actor_ids)
                if repaired_unknown_recipients:
                    raise ValueError("repaired adjudicator consequence named an unknown actor")
                validation = world.validate_and_commit(
                    repaired_transaction,
                    envelope_corrections=[
                        "one bounded repair followed an authority-grammar rejection",
                        *repair_corrections,
                    ],
                    intents=intents,
                    current_minute=moment.minute,
                )
                transaction = repaired_transaction
                receipt = repair_receipt
            self.receipts.append(receipt)
            self.moments.append(
                GeneralMomentEvidence(
                    moment_id=moment.moment_id,
                    minute=moment.minute,
                    description=moment.description,
                    frozen_revision=frozen_revision,
                    actor_ids=actor_ids,
                    intent_ids=[item.intent_id for item in intents],
                    resulting_revision=validation.resulting_revision,
                    checkpoint_hash="pending",
                )
            )
            return json.dumps(
                {
                    "moment_id": moment.moment_id,
                    "accepted": validation.accepted,
                    "resulting_revision": validation.resulting_revision,
                    "errors": validation.errors,
                }
            )
        raise NotImplementedError(f"unsupported Concordia action type {output_type}")

    def get_state(self) -> entity_component.ComponentState:
        return {
            "receipts": [item.model_dump(mode="json") for item in self.receipts],
            "moments": [item.model_dump(mode="json") for item in self.moments],
            "lifecycle_events": list(self.lifecycle_events),
        }

    def set_state(self, state: entity_component.ComponentState) -> None:
        self.receipts = TypeAdapter(list[ModelCallReceipt]).validate_python(state["receipts"])
        self.moments = TypeAdapter(list[GeneralMomentEvidence]).validate_python(state["moments"])
        self.lifecycle_events = TypeAdapter(list[str]).validate_python(state["lifecycle_events"])


@dataclass
class GeneralPersonPrefab(prefab.Prefab):  # type: ignore[misc]
    description = "One bounded authored person in a general simulation."
    call: StructuredCall = field(default_factory=_structured_call)
    person: GeneralPersonDraft | None = None
    trace_prefix: str = "general-simulation"
    model: str = CODEX_LUNA_MODEL
    reasoning_effort: str = "medium"
    cognition_mode: str = "integrated"

    def build(
        self,
        model: language_model.LanguageModel,
        memory_bank: basic_associative_memory.AssociativeMemoryBank,
    ) -> entity_component.EntityWithComponents:
        del model, memory_bank
        if self.person is None:
            raise ValueError("person prefab requires an authored person")
        return entity_agent.EntityAgent(
            agent_name=self.person.entity_id,
            act_component=GeneralActorActingComponent(
                self.call,
                person=self.person,
                trace_prefix=self.trace_prefix,
                model=self.model,
                reasoning_effort=self.reasoning_effort,
                cognition_mode=self.cognition_mode,
            ),
            context_components={
                ACTOR_CONTEXT_COMPONENT: ActorContextComponent(),
                "__memory__": MemoryViewComponent(),
            },
        )


@dataclass
class GeneralWorldPrefab(prefab.Prefab):  # type: ignore[misc]
    description = "Canonical world and joint transition authority."
    compiled: CompiledGeneralSimulation | None = None
    call: StructuredCall = field(default_factory=_structured_call)
    trace_prefix: str = "general-simulation"
    model: str = CODEX_LUNA_MODEL
    reasoning_effort: str = "medium"

    def build(
        self,
        model: language_model.LanguageModel,
        memory_bank: basic_associative_memory.AssociativeMemoryBank,
    ) -> entity_component.EntityWithComponents:
        del model, memory_bank
        if self.compiled is None:
            raise ValueError("world prefab requires a compiled simulation")
        semantic_authorities = [
            item for item in self.compiled.world_spec.authorities if item.implementation == "llm"
        ]
        if len(semantic_authorities) != 1:
            raise ValueError("this vertical requires exactly one joint LLM authority")
        scenario = _compiled_scenario(self.compiled)
        schedule = _compiled_schedule(self.compiled)
        world = CanonicalWorld(self.compiled.world_spec)
        for person in scenario.people:
            world.retain_memory(person.entity_id, person.memories)
        return entity_agent.EntityAgent(
            agent_name="general_world_game_master",
            act_component=GeneralGameMasterActingComponent(
                self.call,
                scenario=scenario,
                schedule=schedule,
                authority_id=semantic_authorities[0].authority_id,
                trace_prefix=self.trace_prefix,
                model=self.model,
                reasoning_effort=self.reasoning_effort,
            ),
            context_components={
                WORLD_COMPONENT: world,
                INBOX_COMPONENT: InboxComponent(),
                concordia_next_acting.DEFAULT_NEXT_ACTING_COMPONENT_KEY: (
                    concordia_next_acting.NextActingAllEntities(
                        [person.entity_id for person in scenario.people]
                    )
                ),
            },
        )


def _build_simulation(
    compiled: CompiledGeneralSimulation,
    call: StructuredCall,
    trace_prefix: str,
    model: str,
    reasoning_effort: str,
    cognition_mode: str = "integrated",
) -> generic.Simulation:
    scenario = _compiled_scenario(compiled)
    schedule = _compiled_schedule(compiled)
    prefabs: dict[str, prefab.Prefab] = {
        f"person_{person.entity_id}": GeneralPersonPrefab(
            call=call,
            person=person,
            trace_prefix=trace_prefix,
            model=model,
            reasoning_effort=reasoning_effort,
            cognition_mode=cognition_mode,
        )
        for person in scenario.people
    }
    prefabs["world"] = GeneralWorldPrefab(
        compiled=compiled,
        call=call,
        trace_prefix=trace_prefix,
        model=model,
        reasoning_effort=reasoning_effort,
    )
    instances = [
        prefab.InstanceConfig(
            prefab=f"person_{person.entity_id}",
            role=prefab.Role.ENTITY,
            params={"name": person.entity_id},
        )
        for person in scenario.people
    ]
    instances.append(
        prefab.InstanceConfig(
            prefab="world",
            role=prefab.Role.GAME_MASTER,
            params={"name": "general_world_game_master"},
        )
    )
    return generic.Simulation(
        config=prefab.Config(
            prefabs=prefabs,
            instances=instances,
            default_max_steps=len(schedule),
        ),
        model=no_language_model.NoLanguageModel(),
        embedder=lambda _: np.zeros(4),
        engine=simultaneous.Simultaneous(),
    )


def _run_compiled_general_simulation(
    compiled: CompiledGeneralSimulation,
    *,
    run_id: str,
    call: StructuredCall | None = None,
    progress_observer: ProgressObserver | None = None,
    checkpoint: Mapping[str, Any] | None = None,
    max_additional_moments: int | None = None,
    model: str = CODEX_LUNA_MODEL,
    reasoning_effort: str = "medium",
    cognition_mode: str = "integrated",
) -> GeneralGroupSimulationResult | GeneralGroupSimulationResultV2:
    scenario = _compiled_scenario(compiled)
    schedule = _compiled_schedule(compiled)
    selected_call = call or _structured_call()
    trace_prefix = f"{run_id}/general"
    simulation = _build_simulation(
        compiled,
        selected_call,
        trace_prefix,
        model=model,
        reasoning_effort=reasoning_effort,
        cognition_mode=cognition_mode,
    )
    restored_checkpoint: dict[str, Any] | None = None
    if checkpoint is not None:
        restored_checkpoint = _strict_general_checkpoint(checkpoint, compiled)
        simulation.load_from_checkpoint(restored_checkpoint)
    checkpoints: list[dict[str, Any]] = []

    def retain_checkpoint(checkpoint: dict[str, Any]) -> None:
        retained = json.loads(json.dumps(checkpoint))
        checkpoints.append(retained)
        if progress_observer is not None:
            retained_model_calls = len(gm_act.receipts)
            for actor in simulation.get_entities():
                assert isinstance(actor, entity_agent.EntityAgent)
                actor_act = cast(
                    GeneralActorActingComponent, actor.get_act_component()
                )
                retained_model_calls += len(actor_act.receipts)
            progress_observer(
                {
                    "stage": "commit",
                    "completed_moments": len(checkpoints),
                    "total_moments": len(schedule),
                    "model_calls": retained_model_calls,
                },
                retained,
            )

    game_master = simulation.get_game_masters()[0]
    assert isinstance(game_master, entity_agent.EntityAgent)
    gm_act = cast(GeneralGameMasterActingComponent, game_master.get_act_component())
    completed_before = len(gm_act.moments)
    remaining = len(schedule) - completed_before
    if max_additional_moments is not None:
        if max_additional_moments < 0:
            raise ValueError("max_additional_moments must be non-negative")
        remaining = min(remaining, max_additional_moments)
    if remaining:
        simulation.play(max_steps=remaining, get_state_callback=retain_checkpoint)
    world = cast(
        CanonicalWorld,
        game_master.get_component(WORLD_COMPONENT, type_=CanonicalWorld),
    )
    actor_receipts: list[ModelCallReceipt] = []
    for actor in simulation.get_entities():
        assert isinstance(actor, entity_agent.EntityAgent)
        actor_act = cast(GeneralActorActingComponent, actor.get_act_component())
        actor_receipts.extend(actor_act.receipts)
    if restored_checkpoint is not None and completed_before:
        gm_act.moments[completed_before - 1].checkpoint_hash = _checkpoint_hash(
            restored_checkpoint
        )
    for offset, retained_checkpoint in enumerate(checkpoints):
        gm_act.moments[completed_before + offset].checkpoint_hash = _checkpoint_hash(
            retained_checkpoint
        )
    adoption = AdoptionReceipt(
        simulation_class=f"{type(simulation).__module__}.{type(simulation).__name__}",
        engine_class=f"{type(simulation._engine).__module__}.{type(simulation._engine).__name__}",
        actor_selection_component=(
            "concordia.components.game_master.next_acting.NextActingAllEntities"
        ),
        concordia_revision=CONCORDIA_REVISION,
        actor_names=[item.name for item in simulation.get_entities()],
        game_master_names=[item.name for item in simulation.get_game_masters()],
        lifecycle_events=gm_act.lifecycle_events,
        forbidden_runtime_imports=[],
    )
    if isinstance(compiled, CompiledGeneralSimulationV2):
        return GeneralGroupSimulationResultV2(
            run_id=compiled.run_spec.run_id,
            scenario_id=compiled.scenario.scenario_id,
            title=compiled.scenario.title,
            scenario_digest=compiled.scenario_digest,
            run_spec_digest=compiled.run_spec_digest,
            registry_digest=compiled.registry_digest,
            final_state=world.state,
            transition_evidence=world.evidence,
            model_calls=actor_receipts + gm_act.receipts,
            moments=gm_act.moments,
            checkpoints=checkpoints,
            adoption=adoption,
        )
    return GeneralGroupSimulationResult(
        simulation_id=compiled.proposal.simulation_id,
        title=compiled.proposal.title,
        question=compiled.proposal.question,
        proposal_digest=compiled.proposal_digest,
        registry_digest=compiled.registry_digest,
        final_state=world.state,
        transition_evidence=world.evidence,
        model_calls=actor_receipts + gm_act.receipts,
        moments=gm_act.moments,
        checkpoints=checkpoints,
        adoption=adoption,
    )


def run_general_simulation(
    compiled: CompiledGeneralSimulationV1,
    *,
    run_id: str,
    call: StructuredCall | None = None,
    progress_observer: ProgressObserver | None = None,
    checkpoint: Mapping[str, Any] | None = None,
    max_additional_moments: int | None = None,
    model: str = CODEX_LUNA_MODEL,
    reasoning_effort: str = "medium",
) -> GeneralGroupSimulationResult:
    result = _run_compiled_general_simulation(
        compiled,
        run_id=run_id,
        call=call,
        progress_observer=progress_observer,
        checkpoint=checkpoint,
        max_additional_moments=max_additional_moments,
        model=model,
        reasoning_effort=reasoning_effort,
    )
    if not isinstance(result, GeneralGroupSimulationResult):
        raise AssertionError("legacy runner returned the wrong result contract")
    return result


def run_general_simulation_v2(
    compiled: CompiledGeneralSimulationV2,
    *,
    call: StructuredCall | None = None,
    progress_observer: ProgressObserver | None = None,
    checkpoint: Mapping[str, Any] | None = None,
    max_additional_moments: int | None = None,
) -> GeneralGroupSimulationResultV2:
    run_spec = compiled.run_spec
    model = run_spec.model or CODEX_LUNA_MODEL
    reasoning_effort = run_spec.reasoning_effort or "medium"
    result = _run_compiled_general_simulation(
        compiled,
        run_id=run_spec.run_id,
        call=call,
        progress_observer=progress_observer,
        checkpoint=checkpoint,
        max_additional_moments=max_additional_moments,
        model=model,
        reasoning_effort=reasoning_effort,
        cognition_mode=run_spec.cognition_mode,
    )
    if not isinstance(result, GeneralGroupSimulationResultV2):
        raise AssertionError("V2 runner returned the wrong result contract")
    return result
