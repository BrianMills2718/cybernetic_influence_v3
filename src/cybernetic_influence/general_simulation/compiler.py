"""Compile semantic proposals using only trusted registered implementations."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Literal

from .authoring_models import (
    CoverageItemV1,
    DependencyEnforcementItemV1,
    ExecutionCoverageReportV1,
    GeneralSimulationProposalV1,
    ScheduledMomentProposalV1,
)
from .contracts_v2 import (
    ComponentRequestV2,
    RunSpecV2,
    ScenarioSpecV2,
    validate_run_against_scenario,
)
from .models import (
    ActiveSystemSpec,
    ActorAccessSpec,
    GeneralWorldSpec,
    GeneralWorldState,
    PatchGrammar,
    Place,
    Placement,
    Representation,
    ResourceTransformationContract,
    ResourceTransportContract,
    ResourceStock,
    Route,
    SensingTransitionContract,
    TransitionAuthoritySpec,
    WorldRecord,
)
from .registry import RegisteredComponentV1, default_registry, registry_digest, resolve_request
from .composition_graph import project_configuration_graph


class GeneralCompilationError(ValueError):
    """Semantic proposal cannot be compiled through trusted implementations."""


@dataclass(frozen=True)
class CompiledGeneralSimulationV1:
    proposal: GeneralSimulationProposalV1
    proposal_digest: str
    coverage: ExecutionCoverageReportV1
    world_spec: GeneralWorldSpec
    registry_digest: str
    resolved_components: tuple[RegisteredComponentV1, ...]
    configuration_graph: dict[str, object]

    def preview(self) -> dict[str, object]:
        return {
            "profile": "general_world_v1",
            "proposal_digest": self.proposal_digest,
            "coverage": self.coverage.model_dump(mode="json"),
            "world_spec": self.world_spec.model_dump(mode="json"),
            "composition_receipt": {
                "registry_digest": self.registry_digest,
                "resolved_component_refs": [item.ref for item in self.resolved_components],
            },
            "configuration_graph": self.configuration_graph,
        }


@dataclass(frozen=True)
class CompiledGeneralSimulationV2:
    scenario: ScenarioSpecV2
    run_spec: RunSpecV2
    scenario_digest: str
    run_spec_digest: str
    coverage: ExecutionCoverageReportV1
    world_spec: GeneralWorldSpec
    registry_digest: str
    resolved_components: tuple[RegisteredComponentV1, ...]
    configuration_graph: dict[str, object]

    def preview(self) -> dict[str, object]:
        return {
            "profile": "general_world_v2",
            "scenario_digest": self.scenario_digest,
            "run_spec_digest": self.run_spec_digest,
            "coverage": self.coverage.model_dump(mode="json"),
            "world_spec": self.world_spec.model_dump(mode="json"),
            "composition_receipt": {
                "registry_digest": self.registry_digest,
                "resolved_component_refs": [item.ref for item in self.resolved_components],
            },
            "configuration_graph": self.configuration_graph,
        }


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _state_dict(entries: list[Any]) -> dict[str, Any]:
    values = {entry.key: entry.value for entry in entries}
    if len(values) != len(entries):
        raise GeneralCompilationError("state entry keys must be unique within each record")
    return values


def _exact_contract_access(
    proposal: GeneralSimulationProposalV1 | ScenarioSpecV2,
) -> dict[str, tuple[set[str], set[str]]]:
    """Return declared semantic reads and writes for each exact contract."""
    access: dict[str, tuple[set[str], set[str]]] = {}
    for rule in proposal.sensing_rules:
        access[rule.rule_id] = ({rule.subject_ref}, {rule.output_record_id})
    for transformation in proposal.resource_transformations:
        access[transformation.transformation_id] = (
            {item.resource_id for item in transformation.input_resource_quantities},
            {transformation.output_resource_id, transformation.public_inventory_record_id},
        )
    for transport in proposal.resource_transports:
        access[transport.transport_id] = (
            {transport.source_resource_id, *transport.allowed_route_ids},
            {
                transport.source_resource_id,
                transport.destination_resource_id,
                transport.arrival_record_id,
            },
        )
    return access


def _compile_general_simulation(
    proposal: GeneralSimulationProposalV1 | ScenarioSpecV2,
    *,
    schedule: list[ScheduledMomentProposalV1],
    run_spec: RunSpecV2 | None = None,
    registry: tuple[RegisteredComponentV1, ...] | None = None,
) -> CompiledGeneralSimulationV1 | CompiledGeneralSimulationV2:
    selected_registry = registry or default_registry()
    digest = registry_digest(selected_registry)
    declared_refs = {
        *[item.entity_id for item in proposal.people],
        *[item.record_id for item in proposal.world_records],
    }
    if proposal.spatial_extension:
        declared_refs.update(item.place_id for item in proposal.spatial_extension.places)
        declared_refs.update(item.link_id for item in proposal.spatial_extension.links)
    if proposal.information_extension:
        declared_refs.update(
            item.representation_id for item in proposal.information_extension.representations
        )
    if proposal.resource_extension:
        declared_refs.update(item.resource_id for item in proposal.resource_extension.stocks)
    actor_ids = {item.entity_id for item in proposal.people}
    record_ids = {
        *actor_ids,
        *[item.record_id for item in proposal.world_records],
    }
    for record in proposal.world_records:
        unknown = sorted(set(record.visible_to_actor_ids) - actor_ids)
        if unknown:
            raise GeneralCompilationError(
                f"record {record.record_id} names unknown visible actors: {', '.join(unknown)}"
            )
    representation_ids: set[str] = set()
    if proposal.information_extension:
        representation_ids = {
            item.representation_id
            for item in proposal.information_extension.representations
        }
        for representation in proposal.information_extension.representations:
            unknown = sorted(set(representation.recipient_ids) - actor_ids)
            if unknown:
                raise GeneralCompilationError(
                    f"representation {representation.representation_id} names unknown recipients: "
                    + ", ".join(unknown)
                )
    for rule in proposal.sensing_rules:
        if rule.subject_ref not in declared_refs:
            raise GeneralCompilationError(
                f"sensing rule {rule.rule_id} names unknown subject {rule.subject_ref}"
            )
        unknown_actors = sorted(
            (set(rule.observer_ids) | set(rule.result_recipient_ids)) - actor_ids
        )
        if unknown_actors:
            raise GeneralCompilationError(
                f"sensing rule {rule.rule_id} names unknown actors: {', '.join(unknown_actors)}"
            )
        if rule.output_record_id not in record_ids:
            raise GeneralCompilationError(
                f"sensing rule {rule.rule_id} names unknown output record "
                f"{rule.output_record_id}"
            )
        world_record_subject = next(
            (
                item
                for item in proposal.world_records
                if item.record_id == rule.subject_ref
            ),
            None,
        )
        if world_record_subject is not None:
            hidden_keys = {item.key for item in world_record_subject.hidden_state}
        elif rule.subject_ref in actor_ids:
            hidden_keys = {"disposition", "behavioral_profile"}
        elif proposal.spatial_extension and rule.subject_ref in {
            item.link_id for item in proposal.spatial_extension.links
        }:
            subject = next(
                item
                for item in proposal.spatial_extension.links
                if item.link_id == rule.subject_ref
            )
            hidden_keys = {item.key for item in subject.hidden_state}
        else:
            hidden_keys = set()
        unknown_hidden_keys = sorted(set(rule.reveal_hidden_keys) - hidden_keys)
        if unknown_hidden_keys:
            raise GeneralCompilationError(
                f"sensing rule {rule.rule_id} names unavailable hidden keys: "
                + ", ".join(unknown_hidden_keys)
            )
    resource_ids = (
        {item.resource_id for item in proposal.resource_extension.stocks}
        if proposal.resource_extension else set()
    )
    for transformation in proposal.resource_transformations:
        unknown_resources = sorted(
            ({
                *(item.resource_id for item in transformation.input_resource_quantities),
                transformation.output_resource_id,
            })
            - resource_ids
        )
        if unknown_resources:
            raise GeneralCompilationError(
                f"transformation {transformation.transformation_id} names unknown resources: "
                + ", ".join(unknown_resources)
            )
        unknown_operators = sorted(set(transformation.operator_ids) - actor_ids)
        if unknown_operators:
            raise GeneralCompilationError(
                f"transformation {transformation.transformation_id} names unknown operators: "
                + ", ".join(unknown_operators)
            )
        if transformation.public_inventory_record_id not in record_ids:
            raise GeneralCompilationError(
                f"transformation {transformation.transformation_id} names unknown inventory record "
                f"{transformation.public_inventory_record_id}"
            )
    resource_custodians = (
        {item.resource_id: item.custodian_id for item in proposal.resource_extension.stocks}
        if proposal.resource_extension else {}
    )
    place_ids = (
        {item.place_id for item in proposal.spatial_extension.places}
        if proposal.spatial_extension else set()
    )
    route_ids = (
        {item.link_id for item in proposal.spatial_extension.links}
        if proposal.spatial_extension else set()
    )
    route_endpoints = (
        {
            item.link_id: (item.origin_place_id, item.destination_place_id)
            for item in proposal.spatial_extension.links
        }
        if proposal.spatial_extension else {}
    )
    for transport in proposal.resource_transports:
        unknown_resources = sorted(
            {transport.source_resource_id, transport.destination_resource_id}
            - resource_ids
        )
        if unknown_resources:
            raise GeneralCompilationError(
                f"transport {transport.transport_id} names unknown resources: "
                + ", ".join(unknown_resources)
            )
        unknown_operators = sorted(set(transport.operator_ids) - actor_ids)
        if unknown_operators:
            raise GeneralCompilationError(
                f"transport {transport.transport_id} names unknown operators: "
                + ", ".join(unknown_operators)
            )
        if resource_custodians.get(transport.source_resource_id) != transport.source_custodian_id:
            raise GeneralCompilationError(
                f"transport {transport.transport_id} source custodian does not match "
                f"resource {transport.source_resource_id}"
            )
        if resource_custodians.get(transport.destination_resource_id) != transport.destination_custodian_id:
            raise GeneralCompilationError(
                f"transport {transport.transport_id} destination custodian does not match "
                f"resource {transport.destination_resource_id}"
            )
        unknown_places = sorted(
            {transport.origin_place_id, transport.destination_place_id} - place_ids
        )
        if unknown_places:
            raise GeneralCompilationError(
                f"transport {transport.transport_id} names unknown places: "
                + ", ".join(unknown_places)
            )
        unknown_routes = sorted(set(transport.allowed_route_ids) - route_ids)
        if unknown_routes:
            raise GeneralCompilationError(
                f"transport {transport.transport_id} names unknown routes: "
                + ", ".join(unknown_routes)
            )
        mismatched_routes = sorted(
            route_id
            for route_id in transport.allowed_route_ids
            if route_endpoints.get(route_id)
            != (transport.origin_place_id, transport.destination_place_id)
        )
        if mismatched_routes:
            raise GeneralCompilationError(
                f"transport {transport.transport_id} allowed routes do not match its "
                "directed endpoints: " + ", ".join(mismatched_routes)
            )
        if transport.arrival_record_id not in record_ids:
            raise GeneralCompilationError(
                f"transport {transport.transport_id} names unknown arrival record "
                f"{transport.arrival_record_id}"
            )
    for moment in schedule:
        unknown = sorted(
            set(moment.external_inject_representation_ids) - representation_ids
        )
        if unknown:
            raise GeneralCompilationError(
                f"moment {moment.moment_id} injects unknown representations: "
                + ", ".join(unknown)
            )
    request_ids = {item.request_id for item in proposal.component_requests}
    contract_ids = {
        *[item.rule_id for item in proposal.sensing_rules],
        *[item.transformation_id for item in proposal.resource_transformations],
        *[item.transport_id for item in proposal.resource_transports],
    }
    scheduled_request_ids: set[str] = set()
    scheduled_contract_ids: set[str] = set()
    for moment in schedule:
        unknown_requests = sorted(
            set(moment.active_component_request_ids) - request_ids
        )
        if unknown_requests:
            raise GeneralCompilationError(
                f"moment {moment.moment_id} names unknown component requests: "
                + ", ".join(unknown_requests)
            )
        unknown_contracts = sorted(
            set(moment.active_transition_contract_ids) - contract_ids
        )
        if unknown_contracts:
            raise GeneralCompilationError(
                f"moment {moment.moment_id} names unknown transition contracts: "
                + ", ".join(unknown_contracts)
            )
        scheduled_request_ids.update(moment.active_component_request_ids)
        scheduled_contract_ids.update(moment.active_transition_contract_ids)
    missing_requests = sorted(request_ids - scheduled_request_ids)
    if missing_requests:
        raise GeneralCompilationError(
            "component requests have no scheduled execution moment: "
            + ", ".join(missing_requests)
        )
    missing_contracts = sorted(contract_ids - scheduled_contract_ids)
    if missing_contracts:
        raise GeneralCompilationError(
            "transition contracts have no scheduled execution moment: "
            + ", ".join(missing_contracts)
        )
    request_contracts = {
        request.request_id: set(request.transition_contract_ids)
        for request in proposal.component_requests
    }
    unclaimed_contracts = sorted(
        contract_ids - set().union(*request_contracts.values())
        if request_contracts
        else contract_ids
    )
    if unclaimed_contracts:
        raise GeneralCompilationError(
            "transition contracts are not bound to a component request: "
            + ", ".join(unclaimed_contracts)
        )
    for moment in schedule:
        for request_id in moment.active_component_request_ids:
            inactive_contracts = sorted(
                request_contracts[request_id]
                - set(moment.active_transition_contract_ids)
            )
            if inactive_contracts:
                raise GeneralCompilationError(
                    f"moment {moment.moment_id} activates component request {request_id} "
                    "without its transition contracts: "
                    + ", ".join(inactive_contracts)
                )
    sensing_field_counts: dict[tuple[str, str], int] = {}
    for rule in proposal.sensing_rules:
        for hidden_key in rule.reveal_hidden_keys:
            key = (rule.output_record_id, hidden_key)
            sensing_field_counts[key] = sensing_field_counts.get(key, 0) + 1
    public_record_fields = {
        item.record_id: {entry.key for entry in item.public_state}
        for item in proposal.world_records
    }
    for rule in proposal.sensing_rules:
        required_fields = {
            (
                f"{rule.subject_ref}_{hidden_key}"
                if sensing_field_counts[(rule.output_record_id, hidden_key)] > 1
                else hidden_key
            )
            for hidden_key in rule.reveal_hidden_keys
        }
        missing_fields = sorted(
            required_fields - public_record_fields.get(rule.output_record_id, set())
        )
        if missing_fields:
            raise GeneralCompilationError(
                f"sensing rule {rule.rule_id} writes undeclared public fields on "
                f"{rule.output_record_id}: " + ", ".join(missing_fields)
            )
    if proposal.spatial_extension:
        route_public_fields = {
            item.link_id: {entry.key for entry in item.public_state}
            for item in proposal.spatial_extension.links
        }
        for transport in proposal.resource_transports:
            missing_time = sorted(
                route_id
                for route_id in transport.allowed_route_ids
                if "travel_time_minutes" not in route_public_fields.get(route_id, set())
            )
            if missing_time:
                raise GeneralCompilationError(
                    f"transport {transport.transport_id} requires public "
                    "travel_time_minutes on routes: " + ", ".join(missing_time)
                )
    if proposal.spatial_extension:
        place_ids = {item.place_id for item in proposal.spatial_extension.places}
        for placement in proposal.spatial_extension.placements:
            if placement.record_id not in record_ids:
                raise GeneralCompilationError(
                    f"placement names unknown record {placement.record_id}"
                )
            if placement.place_id not in place_ids:
                raise GeneralCompilationError(
                    f"placement names unknown place {placement.place_id}"
                )
        for link in proposal.spatial_extension.links:
            if link.origin_place_id not in place_ids or link.destination_place_id not in place_ids:
                raise GeneralCompilationError(
                    f"link {link.link_id} names an unknown endpoint"
                )
            unknown = sorted(set(link.visible_to_actor_ids) - actor_ids)
            if unknown:
                raise GeneralCompilationError(
                    f"link {link.link_id} names unknown visible actors: {', '.join(unknown)}"
                )
    if proposal.resource_extension:
        for resource in proposal.resource_extension.stocks:
            if resource.custodian_id not in record_ids:
                raise GeneralCompilationError(
                    f"resource {resource.resource_id} names unknown custodian "
                    f"{resource.custodian_id}"
                )
    coverage_items: list[CoverageItemV1] = []
    resolved: list[RegisteredComponentV1] = []
    contract_access = _exact_contract_access(proposal)
    for request in proposal.component_requests:
        unknown_subjects = sorted(set(request.subject_refs) - declared_refs)
        unknown_reads = sorted(set(request.required_reads) - declared_refs)
        entry, evidence = resolve_request(request, selected_registry, actor_ids=actor_ids)
        evidence = list(evidence)
        if (
            isinstance(request, ComponentRequestV2)
            and request.fidelity_need == "bounded"
            and not request.transition_contract_ids
            and entry is not None
            and entry.fidelity == "exact"
        ):
            bounded_entry, bounded_evidence = resolve_request(
                request,
                tuple(item for item in selected_registry if item.fidelity == "coarse_llm"),
                actor_ids=actor_ids,
            )
            if bounded_entry is not None:
                entry = bounded_entry
                evidence = [
                    "bounded semantic behavior was not promoted to an exact "
                    "structural component",
                    *bounded_evidence,
                ]
        classification: Literal[
            "exact", "coarse_llm", "descriptive", "unsupported"
        ]
        component_ref: str | None
        can_change: list[str]
        cannot_change: list[str]
        assumptions: list[str]
        if request.transition_contract_ids:
            classification = "exact"
            component_ref = "transition_contracts:" + ",".join(
                request.transition_contract_ids
            )
            can_change = ["only the state changes declared by its exact transition contracts"]
            cannot_change = ["state outside its exact transition-contract grammar"]
            assumptions = ["the actor must still select the contract and pass validation"]
            evidence.append(
                "bound exact transition contracts: "
                + ", ".join(request.transition_contract_ids)
            )
            entry = None
        if unknown_subjects:
            evidence.append(f"unknown subject refs: {', '.join(unknown_subjects)}")
        if unknown_reads:
            evidence.append(f"unknown required reads: {', '.join(unknown_reads)}")
        if unknown_subjects or unknown_reads:
            classification = "unsupported"
            component_ref = None
            can_change = []
            cannot_change = ["all requested material behavior"]
            assumptions = []
        elif request.transition_contract_ids:
            pass
        elif entry is None:
            classification = "unsupported"
            component_ref = None
            can_change = []
            cannot_change = ["all requested material behavior"]
            assumptions = []
        else:
            classification = entry.fidelity
            component_ref = entry.ref
            can_change = entry.what_can_change
            cannot_change = entry.what_cannot_change
            assumptions = entry.assumptions
            if entry not in resolved:
                resolved.append(entry)
        dependency_enforcement: list[DependencyEnforcementItemV1] = []
        exact_readers: dict[str, list[str]] = {}
        exact_writers: dict[str, list[str]] = {}
        for contract_id in request.transition_contract_ids:
            reads, writes = contract_access[contract_id]
            for dependency_ref in reads:
                exact_readers.setdefault(dependency_ref, []).append(contract_id)
            for dependency_ref in writes:
                exact_writers.setdefault(dependency_ref, []).append(contract_id)
        for dependency_ref in dict.fromkeys(request.required_reads):
            enforcement: Literal[
                "exact_read",
                "exact_write_only",
                "coarse_llm",
                "descriptive",
                "unsupported",
            ]
            dependency_contract_ids: list[str]
            dependency_evidence: list[str]
            if dependency_ref in exact_readers:
                enforcement = "exact_read"
                dependency_contract_ids = sorted(exact_readers[dependency_ref])
                dependency_evidence = [
                    "read as an exact transition precondition or input"
                ]
            elif dependency_ref in exact_writers:
                enforcement = "exact_write_only"
                dependency_contract_ids = sorted(exact_writers[dependency_ref])
                dependency_evidence = [
                    "written by an exact contract but not read as a prerequisite"
                ]
            elif (
                classification == "exact"
                and not request.transition_contract_ids
                and component_ref is not None
            ):
                enforcement = "exact_read"
                dependency_contract_ids = []
                dependency_evidence = [
                    f"covered by registered exact component {component_ref}"
                ]
            elif classification == "coarse_llm":
                enforcement = "coarse_llm"
                dependency_contract_ids = []
                dependency_evidence = ["available only to coarse LLM adjudication"]
            elif classification == "descriptive":
                enforcement = "descriptive"
                dependency_contract_ids = []
                dependency_evidence = ["descriptive context has no transition authority"]
            else:
                enforcement = "unsupported"
                dependency_contract_ids = []
                dependency_evidence = ["no bound exact contract reads this dependency"]
            dependency_enforcement.append(
                DependencyEnforcementItemV1(
                    dependency_ref=dependency_ref,
                    enforcement=enforcement,
                    transition_contract_ids=dependency_contract_ids,
                    compiler_evidence=dependency_evidence,
                )
            )
        unenforced_dependency_refs = [
            item.dependency_ref
            for item in dependency_enforcement
            if item.enforcement != "exact_read"
        ]
        if classification == "exact":
            causal_closure: Literal[
                "exact", "partial", "coarse", "descriptive", "unsupported"
            ] = "partial" if unenforced_dependency_refs else "exact"
        elif classification == "coarse_llm":
            causal_closure = "coarse"
        elif classification == "descriptive":
            causal_closure = "descriptive"
        else:
            causal_closure = "unsupported"
        if causal_closure == "partial":
            evidence.append(
                "required dependencies not read by an exact contract: "
                + ", ".join(unenforced_dependency_refs)
            )
        material = (
            request.blocks_if_unexecutable
            if isinstance(request, ComponentRequestV2)
            else request.material_to_question
        )
        blocking = material and classification in {
            "unsupported",
            "descriptive",
        }
        if (
            isinstance(request, ComponentRequestV2)
            and material
            and request.fidelity_need == "exact"
            and causal_closure != "exact"
        ):
            blocking = True
        coverage_items.append(
            CoverageItemV1(
                request_id=request.request_id,
                classification=classification,
                resolved_component_ref=component_ref,
                what_can_change=can_change,
                what_cannot_change=cannot_change,
                assumptions=assumptions,
                blocking=blocking,
                compiler_evidence=evidence,
                causal_closure=causal_closure,
                dependency_enforcement=dependency_enforcement,
                unenforced_dependency_refs=unenforced_dependency_refs,
            )
        )
    coverage = ExecutionCoverageReportV1(
        registry_digest=digest,
        items=coverage_items,
        blocking_request_ids=[item.request_id for item in coverage_items if item.blocking],
    )
    people_ids = {item.entity_id for item in proposal.people}
    records = {
        item.record_id: WorldRecord(
            record_id=item.record_id,
            kind=item.kind,
            label=item.label,
            state=_state_dict(item.public_state),
            hidden_state=_state_dict(item.hidden_state),
        )
        for item in proposal.world_records
    }
    for person in proposal.people:
        records.setdefault(
            person.entity_id,
            WorldRecord(
                record_id=person.entity_id,
                kind="person",
                label=person.label,
                state={"position": person.position},
                hidden_state={
                    "disposition": person.disposition,
                    "behavioral_profile": person.behavioral_profile.model_dump(mode="json"),
                },
            ),
        )
    places: dict[str, Place] = {}
    placements: dict[str, Placement] = {}
    routes: dict[str, Route] = {}
    if proposal.spatial_extension:
        places = {
            item.place_id: Place(place_id=item.place_id, label=item.label)
            for item in proposal.spatial_extension.places
        }
        placements = {
            item.record_id: Placement(record_id=item.record_id, place_id=item.place_id)
            for item in proposal.spatial_extension.placements
        }
        routes = {
            item.link_id: Route(
                route_id=item.link_id,
                origin_id=item.origin_place_id,
                destination_id=item.destination_place_id,
                operational=item.operational,
                public_state=_state_dict(item.public_state),
                hidden_state=_state_dict(item.hidden_state),
            )
            for item in proposal.spatial_extension.links
        }
    representations = (
        {
            item.representation_id: Representation(
                representation_id=item.representation_id,
                content=item.content,
                apparent_source=item.apparent_source,
                recipient_ids=item.recipient_ids,
                hidden_provenance=_state_dict(item.hidden_provenance),
            )
            for item in proposal.information_extension.representations
        }
        if proposal.information_extension
        else {}
    )
    resources = (
        {
            item.resource_id: ResourceStock(
                resource_id=item.resource_id,
                quantity=item.quantity,
                custodian_id=item.custodian_id,
                conserved=item.conserved,
            )
            for item in proposal.resource_extension.stocks
        }
        if proposal.resource_extension
        else {}
    )
    exact_entries = [item for item in resolved if item.fidelity == "exact"]
    coarse_entries = [item for item in resolved if item.fidelity == "coarse_llm"]
    authorities: list[TransitionAuthoritySpec] = []
    if exact_entries:
        authorities.append(
            TransitionAuthoritySpec(
                authority_id="general_deterministic_mechanics",
                implementation="deterministic",
                patch_grammar=PatchGrammar(
                    allowed_operations=sorted(
                        {operation for item in exact_entries for operation in item.patch_operations}
                    ),
                    allowed_record_types=sorted(
                        {kind for item in exact_entries for kind in item.patch_record_types}
                    ),
                ),
                reads=sorted({read for item in exact_entries for read in item.read_scope_schema}),
                writes=sorted(
                    {change for item in exact_entries for change in item.what_can_change}
                ),
                deterministic=True,
                replayable_from_receipt=True,
                idempotent=True,
                assumptions=[assumption for item in exact_entries for assumption in item.assumptions],
                invalid_questions=[
                    question for item in exact_entries for question in item.invalid_questions
                ],
            )
        )
    if coarse_entries:
        authorities.append(
            TransitionAuthoritySpec(
                authority_id="general_semantic_adjudicator",
                implementation="llm",
                patch_grammar=PatchGrammar(
                    allowed_operations=sorted(
                        {operation for item in coarse_entries for operation in item.patch_operations}
                    ),
                    allowed_record_types=sorted(
                        {kind for item in coarse_entries for kind in item.patch_record_types}
                    ),
                ),
                reads=sorted({read for item in coarse_entries for read in item.read_scope_schema}),
                writes=sorted(
                    {change for item in coarse_entries for change in item.what_can_change}
                ),
                deterministic=False,
                replayable_from_receipt=True,
                assumptions=[assumption for item in coarse_entries for assumption in item.assumptions],
                invalid_questions=[
                    question for item in coarse_entries for question in item.invalid_questions
                ],
            )
        )
    active_systems: list[ActiveSystemSpec] = []
    responsibility_owners: dict[str, tuple[str, str]] = {}
    for system in proposal.active_systems:
        for tag in system.causal_responsibility_tags:
            existing = responsibility_owners.get(tag)
            if existing and existing[1] != system.representation_strategy:
                raise GeneralCompilationError(
                    f"causal responsibility {tag!r} is assigned at both "
                    f"{existing[1]} and {system.representation_strategy} resolution"
                )
            responsibility_owners[tag] = (system.system_id, system.representation_strategy)
        executor: Literal["actor", "inert"] = (
            "inert" if system.representation_strategy == "inert" else "actor"
        )
        active_systems.append(
            ActiveSystemSpec(
                system_id=system.system_id,
                executor=executor,
                resolution=system.representation_strategy,
            )
        )
    if coarse_entries:
        active_systems.append(
            ActiveSystemSpec(
                system_id="general_semantic_transition",
                executor="transition_authority",
                authority_id="general_semantic_adjudicator",
                resolution="coarse semantic adjudication",
            )
        )
    actor_access: list[ActorAccessSpec] = []
    for actor_id in people_ids:
        visible_records = [
            item.record_id
            for item in proposal.world_records
            if actor_id in item.visible_to_actor_ids
        ]
        visible_records.append(actor_id)
        visible_routes = (
            [
                item.link_id
                for item in proposal.spatial_extension.links
                if actor_id in item.visible_to_actor_ids
            ]
            if proposal.spatial_extension
            else []
        )
        visible_representations = (
            [
                item.representation_id
                for item in proposal.information_extension.representations
                if actor_id in item.recipient_ids
            ]
            if proposal.information_extension
            else []
        )
        actor_access.append(
            ActorAccessSpec(
                actor_id=actor_id,
                record_ids=sorted(set(visible_records)),
                route_ids=sorted(visible_routes),
                representation_ids=sorted(visible_representations),
            )
        )
    output_sensing_field_counts: dict[tuple[str, str], int] = {}
    for rule in proposal.sensing_rules:
        for hidden_key in rule.reveal_hidden_keys:
            key = (rule.output_record_id, hidden_key)
            output_sensing_field_counts[key] = (
                output_sensing_field_counts.get(key, 0) + 1
            )
    sensing_contracts = [
        SensingTransitionContract(
            contract_id=rule.rule_id,
            subject_type=("route" if rule.subject_ref in route_ids else "record"),
            subject_id=rule.subject_ref,
            observer_ids=rule.observer_ids,
            hidden_to_output_fields={
                hidden_key: (
                    f"{rule.subject_ref}_{hidden_key}"
                    if output_sensing_field_counts[(rule.output_record_id, hidden_key)] > 1
                    else hidden_key
                )
                for hidden_key in rule.reveal_hidden_keys
            },
            output_record_id=rule.output_record_id,
            result_recipient_ids=rule.result_recipient_ids,
        )
        for rule in proposal.sensing_rules
    ]
    transformation_contracts = [
        ResourceTransformationContract(
            contract_id=item.transformation_id,
            operator_ids=item.operator_ids,
            input_resource_quantities={
                requirement.resource_id: requirement.quantity
                for requirement in item.input_resource_quantities
            },
            output_resource_id=item.output_resource_id,
            output_quantity=item.output_quantity,
            maximum_batches=item.maximum_batches,
            public_inventory_record_id=item.public_inventory_record_id,
        )
        for item in proposal.resource_transformations
    ]
    transport_contracts = [
        ResourceTransportContract(
            contract_id=item.transport_id,
            operator_ids=item.operator_ids,
            source_resource_id=item.source_resource_id,
            destination_resource_id=item.destination_resource_id,
            quantity=item.quantity,
            origin_place_id=item.origin_place_id,
            destination_place_id=item.destination_place_id,
            allowed_route_ids=item.allowed_route_ids,
            arrival_record_id=item.arrival_record_id,
            arrival_quantity_key=item.arrival_quantity_key,
            usable_quantity_key=item.usable_quantity_key,
            arrival_minute_key=item.arrival_minute_key,
        )
        for item in proposal.resource_transports
    ]
    world_spec = GeneralWorldSpec(
        spec_id=(
            proposal.scenario_id
            if isinstance(proposal, ScenarioSpecV2)
            else proposal.simulation_id
        ),
        initial_state=GeneralWorldState(
            records=records,
            places=places,
            placements=placements,
            routes=routes,
            representations=representations,
            resources=resources,
        ),
        active_systems=active_systems,
        authorities=authorities,
        invariants=proposal.declared_invariants,
        fidelity_assumptions=proposal.fidelity_assumptions,
        timing={item.moment_id: item.minute for item in schedule},
        actor_access=actor_access,
        sensing_contracts=sensing_contracts,
        resource_transformation_contracts=transformation_contracts,
        resource_transport_contracts=transport_contracts,
    )
    proposal_payload = proposal.model_dump(mode="json")
    configuration_graph = project_configuration_graph(proposal)
    if isinstance(proposal, ScenarioSpecV2):
        if run_spec is None:
            raise GeneralCompilationError("V2 compilation requires a RunSpec")
        return CompiledGeneralSimulationV2(
            scenario=proposal,
            run_spec=run_spec,
            scenario_digest=_digest(proposal_payload),
            run_spec_digest=_digest(run_spec.model_dump(mode="json")),
            coverage=coverage,
            world_spec=world_spec,
            registry_digest=digest,
            resolved_components=tuple(resolved),
            configuration_graph=configuration_graph,
        )
    return CompiledGeneralSimulationV1(
        proposal=proposal,
        proposal_digest=_digest(proposal_payload),
        coverage=coverage,
        world_spec=world_spec,
        registry_digest=digest,
        resolved_components=tuple(resolved),
        configuration_graph=configuration_graph,
    )


def compile_general_simulation(
    proposal: GeneralSimulationProposalV1,
    *,
    registry: tuple[RegisteredComponentV1, ...] | None = None,
) -> CompiledGeneralSimulationV1:
    compiled = _compile_general_simulation(
        proposal,
        schedule=proposal.schedule,
        registry=registry,
    )
    if not isinstance(compiled, CompiledGeneralSimulationV1):
        raise AssertionError("legacy compiler returned the wrong contract")
    return compiled


def compile_general_simulation_v2(
    scenario: ScenarioSpecV2,
    run_spec: RunSpecV2,
    *,
    registry: tuple[RegisteredComponentV1, ...] | None = None,
) -> CompiledGeneralSimulationV2:
    validate_run_against_scenario(scenario, run_spec)
    compiled = _compile_general_simulation(
        scenario,
        schedule=run_spec.scheduled_moments,
        run_spec=run_spec,
        registry=registry,
    )
    if not isinstance(compiled, CompiledGeneralSimulationV2):
        raise AssertionError("V2 compiler returned the wrong contract")
    return compiled
