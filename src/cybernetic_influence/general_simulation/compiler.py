"""Compile semantic proposals using only trusted registered implementations."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Literal

from .authoring_models import (
    CoverageItemV1,
    ExecutionCoverageReportV1,
    GeneralSimulationProposalV1,
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
    ResourceStock,
    Route,
    TransitionAuthoritySpec,
    WorldRecord,
)
from .registry import RegisteredComponentV1, default_registry, registry_digest, resolve_request


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


def compile_general_simulation(
    proposal: GeneralSimulationProposalV1,
    *,
    registry: tuple[RegisteredComponentV1, ...] | None = None,
) -> CompiledGeneralSimulationV1:
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
    resource_ids = (
        {item.resource_id for item in proposal.resource_extension.stocks}
        if proposal.resource_extension else set()
    )
    for transformation in proposal.resource_transformations:
        unknown_resources = sorted(
            ({*transformation.input_resource_quantities, transformation.output_resource_id})
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
    for moment in proposal.schedule:
        unknown = sorted(
            set(moment.external_inject_representation_ids) - representation_ids
        )
        if unknown:
            raise GeneralCompilationError(
                f"moment {moment.moment_id} injects unknown representations: "
                + ", ".join(unknown)
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
    for request in proposal.component_requests:
        unknown_subjects = sorted(set(request.subject_refs) - declared_refs)
        unknown_reads = sorted(set(request.required_reads) - declared_refs)
        entry, evidence = resolve_request(
            request, selected_registry, actor_ids=actor_ids
        )
        evidence = list(evidence)
        if unknown_subjects:
            evidence.append(f"unknown subject refs: {', '.join(unknown_subjects)}")
        if unknown_reads:
            evidence.append(f"unknown required reads: {', '.join(unknown_reads)}")
        if entry is None or unknown_subjects or unknown_reads:
            classification: Literal["exact", "coarse_llm", "descriptive", "unsupported"] = (
                "unsupported"
            )
            component_ref = None
            can_change: list[str] = []
            cannot_change = ["all requested material behavior"]
            assumptions: list[str] = []
        else:
            classification = entry.fidelity
            component_ref = entry.ref
            can_change = entry.what_can_change
            cannot_change = entry.what_cannot_change
            assumptions = entry.assumptions
            if entry not in resolved:
                resolved.append(entry)
        blocking = request.material_to_question and classification in {
            "unsupported",
            "descriptive",
        }
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
    world_spec = GeneralWorldSpec(
        spec_id=proposal.simulation_id,
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
        timing={item.moment_id: item.minute for item in proposal.schedule},
        actor_access=actor_access,
    )
    proposal_payload = proposal.model_dump(mode="json")
    return CompiledGeneralSimulationV1(
        proposal=proposal,
        proposal_digest=_digest(proposal_payload),
        coverage=coverage,
        world_spec=world_spec,
        registry_digest=digest,
        resolved_components=tuple(resolved),
    )
