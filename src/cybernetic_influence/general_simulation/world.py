"""Canonical world component: query, validate, atomically commit, emit."""

from __future__ import annotations

import copy
import hashlib
import json
from collections import deque
from typing import Any, cast

from concordia.typing import entity_component
from pydantic import JsonValue, TypeAdapter, ValidationError

from .models import (
    AvailableTransitionContract,
    ActorContext,
    Consequence,
    GeneralWorldSpec,
    GeneralWorldState,
    Observation,
    OperationAttribution,
    PatchOperation,
    Precondition,
    Route,
    SemanticActionIntent,
    TransitionEvidence,
    TypedTarget,
    ValidationResult,
    WorldTransaction,
)


def state_hash(state: GeneralWorldState) -> str:
    payload = state.model_dump_json(exclude_none=False)
    return hashlib.sha256(payload.encode()).hexdigest()


class CanonicalWorld(entity_component.ContextComponent):  # type: ignore[misc]
    """Owns truth but never chooses actors, advances time, or runs a loop."""

    def __init__(self, spec: GeneralWorldSpec):
        self._spec = spec.model_copy(deep=True)
        self._state = spec.initial_state.model_copy(deep=True)
        self._evidence: list[TransitionEvidence] = []
        self._private_memory: dict[str, list[str]] = {}
        self._observations: dict[str, list[Observation]] = {}

    @property
    def state(self) -> GeneralWorldState:
        return self._state.model_copy(deep=True)

    @property
    def spec(self) -> GeneralWorldSpec:
        return self._spec.model_copy(deep=True)

    @property
    def evidence(self) -> list[TransitionEvidence]:
        return copy.deepcopy(self._evidence)

    def actor_context(
        self,
        actor_id: str,
        *,
        current_minute: int = 0,
        delivered_representation_ids: set[str] | None = None,
        active_transition_contract_ids: set[str] | None = None,
        phase_description: str | None = None,
        phase_responsibilities: list[str] | None = None,
    ) -> ActorContext:
        access = next(
            (item for item in self._spec.actor_access if item.actor_id == actor_id), None
        )
        if access is None:
            raise ValueError(f"no actor access contract registered for {actor_id}")
        representations = [
            item
            for item in self._state.representations.values()
            if actor_id in item.recipient_ids
            and item.representation_id in access.representation_ids
            and (
                delivered_representation_ids is None
                or item.representation_id in delivered_representation_ids
            )
        ]
        representation_observations = [
            Observation(
                observation_id=f"representation:{item.representation_id}",
                content=item.content,
                apparent_source=item.apparent_source,
                representation_id=item.representation_id,
            )
            for item in representations
        ]
        # Hidden route state and hidden representation provenance are never
        # serialized into actor context.
        safe_routes = [
            Route(
                route_id=route.route_id,
                origin_id=route.origin_id,
                destination_id=route.destination_id,
                operational=route.operational,
                public_state=copy.deepcopy(route.public_state),
                hidden_state={},
            )
            for route in self._state.routes.values()
            if route.route_id in access.route_ids
        ]
        observations = representation_observations + copy.deepcopy(
            self._observations.get(actor_id, [])
        )
        available_contracts = [
            AvailableTransitionContract(
                contract_id=item.contract_id,
                contract_kind="sensing",
                summary=(
                    f"Observe {item.subject_id} and publish only its declared scoped "
                    f"finding in {item.output_record_id}."
                ),
                target_refs=[item.subject_id, item.output_record_id],
            )
            for item in self._spec.sensing_contracts
            if actor_id in item.observer_ids
            and (
                active_transition_contract_ids is None
                or item.contract_id in active_transition_contract_ids
            )
        ]
        available_contracts.extend(
            AvailableTransitionContract(
                contract_id=item.contract_id,
                contract_kind="resource_transformation",
                summary=(
                    f"Transform declared inputs into at most {item.maximum_batches} "
                    f"batch(es) of {item.output_resource_id}."
                ),
                target_refs=[
                    *item.input_resource_quantities,
                    item.output_resource_id,
                    item.public_inventory_record_id,
                ],
            )
            for item in self._spec.resource_transformation_contracts
            if actor_id in item.operator_ids
            and (
                active_transition_contract_ids is None
                or item.contract_id in active_transition_contract_ids
            )
        )
        available_contracts.extend(
            AvailableTransitionContract(
                contract_id=item.contract_id,
                contract_kind="resource_transport",
                summary=(
                    f"Attempt movement of up to {item.quantity:g} units from "
                    f"{item.origin_place_id} to {item.destination_place_id} over one "
                    "declared route."
                ),
                target_refs=[
                    item.source_resource_id,
                    item.destination_resource_id,
                    item.arrival_record_id,
                    *item.allowed_route_ids,
                ],
            )
            for item in self._spec.resource_transport_contracts
            if actor_id in item.operator_ids
            and (
                active_transition_contract_ids is None
                or item.contract_id in active_transition_contract_ids
            )
        )
        return ActorContext(
            actor_id=actor_id,
            base_revision=self._state.revision,
            current_minute=current_minute,
            observations=observations,
            accessible_records=[
                item.model_copy(update={"hidden_state": {}}, deep=True)
                for item in self._state.records.values()
                if item.record_id in access.record_ids
            ],
            accessible_routes=safe_routes,
            private_memory=copy.deepcopy(self._private_memory.get(actor_id, [])),
            available_transition_contracts=available_contracts,
            phase_description=phase_description,
            phase_responsibilities=phase_responsibilities or [],
        )

    def retain_memory(self, actor_id: str, memories: list[str]) -> None:
        self._private_memory.setdefault(actor_id, []).extend(memories)

    def drain_outbox(self, actor_id: str) -> list[Observation]:
        delivered = set(self._state.delivered_consequence_ids)
        observations: list[Observation] = []
        for consequence in self._state.outbox:
            if consequence.recipient_id != actor_id or consequence.consequence_id in delivered:
                continue
            observation = Observation(
                observation_id=f"consequence:{consequence.consequence_id}",
                content=consequence.content,
                apparent_source=consequence.apparent_source,
                representation_id=consequence.representation_id,
            )
            observations.append(observation)
            self._observations.setdefault(actor_id, []).append(observation)
            self._state.delivered_consequence_ids.append(consequence.consequence_id)
        return observations

    def validate_and_commit(
        self,
        transaction: WorldTransaction,
        *,
        envelope_corrections: list[str] | None = None,
        intents: list[SemanticActionIntent] | None = None,
        current_minute: int | None = None,
    ) -> ValidationResult:
        retained_corrections = list(envelope_corrections or [])
        errors: list[str] = []
        if transaction.base_revision != self._state.revision:
            errors.append(
                f"base revision {transaction.base_revision} does not match {self._state.revision}"
            )
        authorities = {
            authority.authority_id: authority for authority in self._spec.authorities
        }
        authority = authorities.get(transaction.authority_id)
        if authority is None:
            errors.append(f"unknown authority {transaction.authority_id}")
        else:
            for operation in transaction.operations:
                if operation.operation not in authority.patch_grammar.allowed_operations:
                    errors.append(f"operation {operation.operation} is outside authority grammar")
                if operation.target.record_type not in authority.patch_grammar.allowed_record_types:
                    errors.append(
                        f"target type {operation.target.record_type} is outside authority grammar"
                    )
        supplied_intents = list(intents or [])
        if supplied_intents and set(transaction.intent_ids) != {
            item.intent_id for item in supplied_intents
        }:
            errors.append("transaction intent ids differ from supplied actor intents")
        for consequence in transaction.consequences:
            if consequence.representation_id is None:
                continue
            representation = self._state.representations.get(
                consequence.representation_id
            )
            if representation is None:
                errors.append(
                    f"consequence {consequence.consequence_id} names unknown representation "
                    f"{consequence.representation_id}"
                )
            elif consequence.recipient_id not in representation.recipient_ids:
                errors.append(
                    f"consequence {consequence.consequence_id} would deliver representation "
                    f"{consequence.representation_id} to unauthorized recipient "
                    f"{consequence.recipient_id}"
                )
        for precondition in transaction.preconditions:
            try:
                actual = self._read_target(self._state, precondition.target)
            except KeyError as exc:
                if (
                    precondition.expected is None
                    and self._missing_final_mapping_key(
                        self._state, precondition.target
                    )
                ):
                    actual = None
                else:
                    errors.append(f"invalid precondition target: {exc}")
                    continue
            except (AttributeError, TypeError, ValueError) as exc:
                errors.append(f"invalid precondition target: {exc}")
                continue
            if actual != precondition.expected:
                errors.append(
                    f"precondition failed for {precondition.target.model_dump()}: "
                    f"expected {precondition.expected!r}, got {actual!r}"
                )
        operation_attributions, contract_errors = self._attribute_operations(
            transaction,
            intents=supplied_intents,
            current_minute=current_minute,
        )
        errors.extend(contract_errors)
        candidate = self._state.model_copy(deep=True)
        if not errors:
            for operation in transaction.operations:
                try:
                    if (
                        operation.target.record_type == "placement"
                        and operation.target.field == "place_id"
                        and operation.operation in {"replace", "rebind"}
                    ):
                        current = candidate.placements.get(operation.target.record_id)
                        destination = operation.value
                        if current is None or not isinstance(destination, str):
                            raise ValueError("placement movement requires an existing placement and place id")
                        if not self._path_exists(candidate, current.place_id, destination):
                            raise ValueError(
                                f"no operational path from {current.place_id} to {destination}"
                            )
                    self._apply(candidate, operation)
                except (KeyError, TypeError, ValueError, ValidationError) as exc:
                    errors.append(str(exc))
                    break
        if not errors:
            try:
                candidate = GeneralWorldState.model_validate(candidate.model_dump())
            except ValidationError as exc:
                errors.append(f"typed world validation failed: {exc}")
        if not errors:
            candidate.revision += 1
        # Adjudicator prose is evidence, never an actor observation. The
        # canonical committer projects a factual receipt from the state that
        # actually survived validation.
        if not errors:
            moved_records = [
                operation.target.record_id
                for operation in transaction.operations
                if operation.target.record_type == "placement"
                and operation.target.field == "place_id"
                and operation.operation in {"replace", "rebind"}
            ]
            placement_summary = "; ".join(
                f"{record_id} is at {candidate.placements[record_id].place_id}"
                for record_id in moved_records
            )
            for requested in transaction.consequences:
                candidate.outbox.append(
                    Consequence(
                        consequence_id=requested.consequence_id,
                        recipient_id=requested.recipient_id,
                        content=(
                            f"Canonical world revision {candidate.revision} committed"
                            + (f": {placement_summary}." if placement_summary else ".")
                        ),
                        apparent_source="canonical world commit",
                        representation_id=None,
                    )
                )
            errors.extend(self._invariant_errors(candidate))
        if errors:
            result = ValidationResult(
                accepted=False,
                base_revision=self._state.revision,
                resulting_revision=self._state.revision,
                errors=errors,
            )
            self._evidence.append(
                TransitionEvidence(
                    transaction=transaction,
                    envelope_corrections=retained_corrections,
                    validation=result,
                    resulting_state_hash=state_hash(self._state),
                    operation_attributions=operation_attributions,
                )
            )
            return result
        self._state = candidate
        result = ValidationResult(
            accepted=True,
            base_revision=transaction.base_revision,
            resulting_revision=candidate.revision,
            errors=[],
        )
        self._evidence.append(
            TransitionEvidence(
                transaction=transaction,
                envelope_corrections=retained_corrections,
                validation=result,
                resulting_state_hash=state_hash(candidate),
                operation_attributions=operation_attributions,
            )
        )
        return result

    @staticmethod
    def _numeric_delta(before: object, after: object) -> float | None:
        if isinstance(before, (int, float)) and isinstance(after, (int, float)):
            return float(after) - float(before)
        return None

    @staticmethod
    def _close(left: float, right: float) -> bool:
        return abs(left - right) <= 1e-9

    @staticmethod
    def _targets(
        operation: PatchOperation,
        record_type: str,
        record_id: str,
        field: str,
    ) -> bool:
        return (
            operation.operation == "replace"
            and operation.target.record_type == record_type
            and operation.target.record_id == record_id
            and operation.target.field == field
        )

    def _attribute_operations(
        self,
        transaction: WorldTransaction,
        *,
        intents: list[SemanticActionIntent],
        current_minute: int | None,
    ) -> tuple[list[OperationAttribution], list[str]]:
        """Bind contract-owned state changes to a selected executable contract."""
        if not transaction.operations:
            return [], []
        scratch = self._state.model_copy(deep=True)
        snapshots: list[tuple[object, object]] = []
        for operation in transaction.operations:
            try:
                before = self._read_target(scratch, operation.target)
            except (AttributeError, KeyError, TypeError, ValueError):
                before = None
            try:
                self._apply(scratch, operation)
                after = self._read_target(scratch, operation.target)
            except (AttributeError, KeyError, TypeError, ValueError, ValidationError):
                after = object()
            snapshots.append((before, after))

        claimed: dict[int, OperationAttribution] = {}
        for index, (before, after) in enumerate(snapshots):
            if before == after:
                claimed[index] = OperationAttribution(
                    operation_index=index,
                    authority_id=transaction.authority_id,
                    classification="no_op",
                    intent_ids=list(transaction.intent_ids),
                )

        intents_by_contract: dict[str, list[SemanticActionIntent]] = {}
        for intent in intents:
            for contract_id in intent.transition_contract_ids:
                intents_by_contract.setdefault(contract_id, []).append(intent)

        for contract in self._spec.sensing_contracts:
            selected = [
                intent
                for intent in intents_by_contract.get(contract.contract_id, [])
                if intent.actor_id in contract.observer_ids
            ]
            if not selected:
                continue
            subject = (
                self._state.routes[contract.subject_id]
                if contract.subject_type == "route"
                else self._state.records[contract.subject_id]
            )
            for hidden_key, output_field in contract.hidden_to_output_fields.items():
                for index, operation in enumerate(transaction.operations):
                    if index in claimed:
                        continue
                    if (
                        self._targets(
                            operation,
                            "record",
                            contract.output_record_id,
                            f"state.{output_field}",
                        )
                        and operation.value == subject.hidden_state[hidden_key]
                    ):
                        claimed[index] = OperationAttribution(
                            operation_index=index,
                            authority_id=transaction.authority_id,
                            classification="exact_contract",
                            contract_id=contract.contract_id,
                            intent_ids=[item.intent_id for item in selected],
                        )
                        break

        for contract in self._spec.resource_transformation_contracts:
            selected = [
                intent
                for intent in intents_by_contract.get(contract.contract_id, [])
                if intent.actor_id in contract.operator_ids
            ]
            if not selected:
                continue
            output_index: int | None = None
            batches = 0
            for index, operation in enumerate(transaction.operations):
                if index in claimed or not self._targets(
                    operation,
                    "resource",
                    contract.output_resource_id,
                    "quantity",
                ):
                    continue
                delta = self._numeric_delta(*snapshots[index])
                if delta is None or delta <= 0:
                    continue
                candidate_batches = round(delta / contract.output_quantity)
                if (
                    1 <= candidate_batches <= contract.maximum_batches
                    and self._close(
                        delta, candidate_batches * contract.output_quantity
                    )
                ):
                    output_index = index
                    batches = candidate_batches
                    break
            if output_index is None:
                continue
            input_indices: list[int] = []
            for resource_id, quantity in contract.input_resource_quantities.items():
                match: int | None = None
                for index, operation in enumerate(transaction.operations):
                    delta = self._numeric_delta(*snapshots[index])
                    if (
                        index not in claimed
                        and self._targets(operation, "resource", resource_id, "quantity")
                        and delta is not None
                        and self._close(delta, -(quantity * batches))
                    ):
                        match = index
                        break
                if match is None:
                    input_indices = []
                    break
                input_indices.append(match)
            if not input_indices:
                continue
            attribution = OperationAttribution(
                operation_index=0,
                authority_id=transaction.authority_id,
                classification="exact_contract",
                contract_id=contract.contract_id,
                intent_ids=[item.intent_id for item in selected],
            )
            for index in [*input_indices, output_index]:
                claimed[index] = attribution.model_copy(update={"operation_index": index})
            produced_quantity = snapshots[output_index][1]
            for index, operation in enumerate(transaction.operations):
                if index in claimed:
                    continue
                if (
                    operation.target.record_type == "record"
                    and operation.target.record_id == contract.public_inventory_record_id
                    and operation.target.field is not None
                    and operation.target.field.startswith("state.")
                ):
                    if operation.target.field == "state.quantity" and (
                        not isinstance(operation.value, (int, float))
                        or not isinstance(produced_quantity, (int, float))
                        or not self._close(
                            float(operation.value), float(produced_quantity)
                        )
                    ):
                        continue
                    claimed[index] = attribution.model_copy(
                        update={"operation_index": index}
                    )

        for contract in self._spec.resource_transport_contracts:
            selected = [
                intent
                for intent in intents_by_contract.get(contract.contract_id, [])
                if intent.actor_id in contract.operator_ids
            ]
            if not selected:
                continue
            source_index: int | None = None
            destination_index: int | None = None
            for index, operation in enumerate(transaction.operations):
                delta = self._numeric_delta(*snapshots[index])
                if index in claimed or delta is None:
                    continue
                if self._targets(
                    operation, "resource", contract.source_resource_id, "quantity"
                ) and self._close(delta, -contract.quantity):
                    source_index = index
                if self._targets(
                    operation,
                    "resource",
                    contract.destination_resource_id,
                    "quantity",
                ) and self._close(delta, contract.quantity):
                    destination_index = index
            selected_routes = list(
                dict.fromkeys(
                    precondition.target.record_id
                    for precondition in transaction.preconditions
                    if precondition.target.record_type == "route"
                    and precondition.target.record_id in contract.allowed_route_ids
                    and precondition.target.field == "operational"
                    and precondition.expected is True
                )
            )
            if (
                source_index is None
                or destination_index is None
                or len(selected_routes) != 1
                or current_minute is None
            ):
                continue
            route = self._state.routes[selected_routes[0]]
            travel_time = route.public_state.get("travel_time_minutes")
            if (
                not route.operational
                or (route.origin_id, route.destination_id)
                != (contract.origin_place_id, contract.destination_place_id)
                or not isinstance(travel_time, (int, float))
            ):
                continue
            required_arrivals = {
                contract.arrival_quantity_key: contract.quantity,
                contract.arrival_minute_key: current_minute + travel_time,
            }
            arrival_indices: list[int] = []
            for field_key, expected in required_arrivals.items():
                match = next(
                    (
                        index
                        for index, operation in enumerate(transaction.operations)
                        if index not in claimed
                        and self._targets(
                            operation,
                            "record",
                            contract.arrival_record_id,
                            f"state.{field_key}",
                        )
                        and operation.value == expected
                    ),
                    None,
                )
                if match is None:
                    arrival_indices = []
                    break
                arrival_indices.append(match)
            usable_index = next(
                (
                    index
                    for index, operation in enumerate(transaction.operations)
                    if index not in claimed
                    and self._targets(
                        operation,
                        "record",
                        contract.arrival_record_id,
                        f"state.{contract.usable_quantity_key}",
                    )
                    and isinstance(operation.value, (int, float))
                    and 0 <= float(operation.value) <= contract.quantity
                ),
                None,
            )
            if not arrival_indices or usable_index is None:
                continue
            attribution = OperationAttribution(
                operation_index=0,
                authority_id=transaction.authority_id,
                classification="exact_contract",
                contract_id=contract.contract_id,
                intent_ids=[item.intent_id for item in selected],
            )
            for index in [
                source_index,
                destination_index,
                *arrival_indices,
                usable_index,
            ]:
                claimed[index] = attribution.model_copy(update={"operation_index": index})

        controlled_record_ids = {
            *[item.output_record_id for item in self._spec.sensing_contracts],
            *[
                item.public_inventory_record_id
                for item in self._spec.resource_transformation_contracts
            ],
            *[item.arrival_record_id for item in self._spec.resource_transport_contracts],
        }
        controlled_resource_ids = {
            *[
                resource_id
                for item in self._spec.resource_transformation_contracts
                for resource_id in item.input_resource_quantities
            ],
            *[
                item.output_resource_id
                for item in self._spec.resource_transformation_contracts
            ],
            *[
                resource_id
                for item in self._spec.resource_transport_contracts
                for resource_id in (
                    item.source_resource_id,
                    item.destination_resource_id,
                )
            ],
        }
        errors: list[str] = []
        for index, operation in enumerate(transaction.operations):
            if index in claimed:
                continue
            controlled = (
                operation.target.record_type == "record"
                and operation.target.record_id in controlled_record_ids
            ) or (
                operation.target.record_type == "resource"
                and operation.target.record_id in controlled_resource_ids
            )
            if controlled:
                errors.append(
                    f"operation {index} on {operation.target.record_type} "
                    f"{operation.target.record_id} is not licensed by a complete declared "
                    "transition contract"
                )
            else:
                claimed[index] = OperationAttribution(
                    operation_index=index,
                    authority_id=transaction.authority_id,
                    classification="coarse_authority",
                    intent_ids=list(transaction.intent_ids),
                )
        return [claimed[index] for index in sorted(claimed)], errors

    def _container(self, state: GeneralWorldState, target: TypedTarget) -> dict[str, Any]:
        return cast(dict[str, Any], getattr(state, f"{target.record_type}s"))

    def _read_target(self, state: GeneralWorldState, target: TypedTarget) -> JsonValue:
        container = self._container(state, target)
        item = container.get(target.record_id)
        if item is None:
            return None
        if target.field is None:
            return cast(JsonValue, item.model_dump(mode="json"))
        segments = target.field.split(".")
        value: Any = getattr(item, segments[0])
        for segment in segments[1:]:
            if not isinstance(value, dict):
                raise ValueError(f"{target.field} does not identify nested state")
            value = value[segment]
        return cast(JsonValue, value)

    def _missing_final_mapping_key(
        self, state: GeneralWorldState, target: TypedTarget
    ) -> bool:
        """Recognize an explicit null guard on a not-yet-created state field."""

        if target.field is None:
            return False
        item = self._container(state, target).get(target.record_id)
        if item is None:
            return False
        segments = target.field.split(".")
        try:
            value: Any = getattr(item, segments[0])
            for segment in segments[1:-1]:
                if not isinstance(value, dict) or segment not in value:
                    return False
                value = value[segment]
        except (AttributeError, TypeError):
            return False
        return (
            len(segments) > 1
            and isinstance(value, dict)
            and segments[-1] not in value
        )

    def _apply(self, state: GeneralWorldState, operation: PatchOperation) -> None:
        container = self._container(state, operation.target)
        record_id = operation.target.record_id
        if operation.operation == "create":
            if record_id in container:
                raise ValueError(f"cannot create existing {operation.target.record_type} {record_id}")
            from .models import (
                Place,
                Placement,
                Representation,
                ResourceStock,
                Route,
                WorldRecord,
            )
            classes = {
                "record": WorldRecord,
                "place": Place,
                "placement": Placement,
                "route": Route,
                "representation": Representation,
                "resource": ResourceStock,
            }
            identity_fields = {
                "record": "record_id",
                "place": "place_id",
                "placement": "record_id",
                "route": "route_id",
                "representation": "representation_id",
                "resource": "resource_id",
            }
            model_class = cast(Any, classes[operation.target.record_type])
            create_value = operation.value
            if isinstance(create_value, dict):
                create_value = dict(create_value)
                create_value.setdefault(
                    identity_fields[operation.target.record_type], record_id
                )
            container[record_id] = model_class.model_validate(create_value)
            return
        if record_id not in container:
            raise KeyError(f"unknown {operation.target.record_type} {record_id}")
        if operation.operation == "remove":
            del container[record_id]
            return
        if operation.target.field is None:
            raise ValueError(f"{operation.operation} requires a target field")
        item = container[record_id]
        segments = operation.target.field.split(".")
        if len(segments) == 1:
            setattr(item, segments[0], operation.value)
            return
        value: Any = getattr(item, segments[0])
        for segment in segments[1:-1]:
            if not isinstance(value, dict):
                raise ValueError(
                    f"{operation.target.field} does not identify nested state"
                )
            value = value[segment]
        if not isinstance(value, dict):
            raise ValueError(f"{operation.target.field} does not identify nested state")
        value[segments[-1]] = operation.value

    def _invariant_errors(self, state: GeneralWorldState) -> list[str]:
        errors: list[str] = []
        for key, record in state.records.items():
            if key != record.record_id:
                errors.append(f"record identity mismatch: {key}")
        for key, placement in state.placements.items():
            if key != placement.record_id:
                errors.append(f"placement identity mismatch: {key}")
            if placement.record_id not in state.records:
                errors.append(f"placement references missing record {placement.record_id}")
            if placement.place_id not in state.places:
                errors.append(f"placement references missing place {placement.place_id}")
        for route in state.routes.values():
            if route.origin_id not in state.places or route.destination_id not in state.places:
                errors.append(f"route {route.route_id} references a missing place")
        for resource in state.resources.values():
            if resource.custodian_id not in state.records:
                errors.append(f"resource {resource.resource_id} has a missing custodian")
            if resource.conserved and resource.quantity < 0:
                errors.append(f"conserved resource {resource.resource_id} cannot be negative")
        consequence_ids = [item.consequence_id for item in state.outbox]
        if len(consequence_ids) != len(set(consequence_ids)):
            errors.append("outbox consequence ids must be unique")
        return errors

    def operational_path_exists(self, origin_id: str, destination_id: str) -> bool:
        return self._path_exists(self._state, origin_id, destination_id)

    @staticmethod
    def _path_exists(
        state: GeneralWorldState, origin_id: str, destination_id: str
    ) -> bool:
        adjacency: dict[str, set[str]] = {}
        for route in state.routes.values():
            if route.operational:
                adjacency.setdefault(route.origin_id, set()).add(route.destination_id)
                adjacency.setdefault(route.destination_id, set()).add(route.origin_id)
        queue = deque([origin_id])
        seen = {origin_id}
        while queue:
            current = queue.popleft()
            if current == destination_id:
                return True
            for neighbor in adjacency.get(current, set()) - seen:
                seen.add(neighbor)
                queue.append(neighbor)
        return False

    def pre_act(self, action_spec: Any) -> str:
        del action_spec
        return ""

    def get_state(self) -> entity_component.ComponentState:
        return {
            "spec": self._spec.model_dump(mode="json"),
            "state": self._state.model_dump(mode="json"),
            "evidence": [item.model_dump(mode="json") for item in self._evidence],
            "private_memory": copy.deepcopy(self._private_memory),
            "observations": {
                actor: [item.model_dump(mode="json") for item in items]
                for actor, items in self._observations.items()
            },
        }

    def set_state(self, state: entity_component.ComponentState) -> None:
        # Concordia's generic EntityAgent logs component restoration failures;
        # validate everything before assignment so malformed checkpoints fail at
        # the project codec boundary rather than partially restoring here.
        try:
            spec = GeneralWorldSpec.model_validate(state["spec"])
            world_state = GeneralWorldState.model_validate(state["state"])
            evidence = TypeAdapter(list[TransitionEvidence]).validate_python(state["evidence"])
            memories = TypeAdapter(dict[str, list[str]]).validate_python(state["private_memory"])
            observations = TypeAdapter(dict[str, list[Observation]]).validate_python(
                state["observations"]
            )
        except (KeyError, ValidationError) as exc:
            raise ValueError("invalid canonical-world checkpoint") from exc
        self._spec = spec
        self._state = world_state
        self._evidence = evidence
        self._private_memory = memories
        self._observations = observations
