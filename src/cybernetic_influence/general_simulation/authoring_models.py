"""Semantic authoring contracts for general-world simulations.

These models contain no Python references, prompt fragments, or executable
predicates. The trusted compiler owns every implementation binding.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from cybernetic_influence.authoring.models import BehavioralProfileDraft, ProfileStatement


_ID = r"^[a-z][a-z0-9_]*$"
Scalar = None | bool | int | float | str
OpenValue = Scalar | list[Scalar] | dict[str, Scalar | list[Scalar] | dict[str, Scalar]]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GeneralBehavioralProfileDraft(BehavioralProfileDraft):
    """Provider-strict form of the existing person-profile semantics."""

    values: list[ProfileStatement]
    goals: list[ProfileStatement]
    beliefs: list[ProfileStatement]
    decision_tendencies: list[ProfileStatement]
    social_perceptions: list[ProfileStatement]
    current_state: list[ProfileStatement]
    capabilities: list[ProfileStatement]
    limitations: list[ProfileStatement]


class GeneralPersonDraft(_StrictModel):
    entity_id: str = Field(pattern=_ID)
    label: str = Field(min_length=1)
    position: str = Field(min_length=1)
    disposition: str = Field(min_length=1)
    memories: list[str] = Field(min_length=1)
    behavioral_profile: GeneralBehavioralProfileDraft


class StateEntryV1(_StrictModel):
    key: str = Field(pattern=_ID)
    value: Scalar | list[Scalar]


class GeneralWorldRecordProposalV1(_StrictModel):
    record_id: str = Field(pattern=_ID, description="Stable semantic identity.")
    kind: str = Field(min_length=1, description="Open semantic kind, not a closed ontology.")
    label: str = Field(min_length=1, description="Human-readable label.")
    public_state: list[StateEntryV1] = Field(
        description="State visible to the named actors."
    )
    hidden_state: list[StateEntryV1] = Field(
        description="World truth withheld absent an information path."
    )
    visible_to_actor_ids: list[str] = Field(
        description="Actors authorized to receive this record's public state."
    )


class GeneralActiveSystemProposalV1(_StrictModel):
    system_id: str = Field(pattern=_ID)
    subject_refs: list[str] = Field(min_length=1)
    behavior_summary: str = Field(min_length=1)
    representation_strategy: Literal["detailed", "coarse_surrogate", "inert"]
    causal_responsibility_tags: list[str] = Field(min_length=1)


class ComponentRequestV1(_StrictModel):
    request_id: str = Field(pattern=_ID)
    subject_refs: list[str] = Field(min_length=1)
    behavior_description: str = Field(min_length=1)
    required_reads: list[str]
    desired_effects: list[str] = Field(min_length=1)
    fidelity_need: Literal["exact", "bounded", "coarse", "descriptive"]
    material_to_question: bool
    transition_contract_ids: list[str] = Field(default_factory=list)


class GeneralPlaceProposalV1(_StrictModel):
    place_id: str = Field(pattern=_ID)
    label: str = Field(min_length=1)
    state: list[StateEntryV1]


class GeneralPlacementProposalV1(_StrictModel):
    record_id: str = Field(pattern=_ID)
    place_id: str = Field(pattern=_ID)


class GeneralSpatialLinkProposalV1(_StrictModel):
    link_id: str = Field(pattern=_ID)
    origin_place_id: str = Field(pattern=_ID)
    destination_place_id: str = Field(pattern=_ID)
    operational: bool
    public_state: list[StateEntryV1]
    hidden_state: list[StateEntryV1]
    visible_to_actor_ids: list[str]


class SpatialExtensionV1(_StrictModel):
    places: list[GeneralPlaceProposalV1]
    placements: list[GeneralPlacementProposalV1]
    links: list[GeneralSpatialLinkProposalV1]


class InformationRepresentationProposalV1(_StrictModel):
    representation_id: str = Field(pattern=_ID)
    content: str = Field(min_length=1)
    apparent_source: str = Field(min_length=1)
    recipient_ids: list[str] = Field(min_length=1)
    hidden_provenance: list[StateEntryV1]


class InformationExtensionV1(_StrictModel):
    representations: list[InformationRepresentationProposalV1]


class ResourceStockProposalV1(_StrictModel):
    resource_id: str = Field(pattern=_ID)
    quantity: float
    custodian_id: str = Field(pattern=_ID)
    conserved: bool


class ResourceExtensionV1(_StrictModel):
    stocks: list[ResourceStockProposalV1]


class RelationshipProposalV1(_StrictModel):
    relationship_id: str = Field(pattern=_ID)
    participant_refs: list[str] = Field(min_length=2)
    description: str = Field(min_length=1)
    material_to_question: bool


class RelationshipExtensionV1(_StrictModel):
    relationships: list[RelationshipProposalV1]


class ScheduledMomentProposalV1(_StrictModel):
    moment_id: str = Field(pattern=_ID)
    minute: int = Field(ge=0)
    description: str = Field(min_length=1)
    external_inject_representation_ids: list[str]
    active_component_request_ids: list[str] = Field(min_length=1)
    active_transition_contract_ids: list[str]


class SensingRuleProposalV1(_StrictModel):
    rule_id: str = Field(pattern=_ID)
    subject_ref: str = Field(pattern=_ID)
    observer_ids: list[str] = Field(min_length=1)
    reveal_hidden_keys: list[str] = Field(min_length=1)
    output_record_id: str = Field(pattern=_ID)
    result_recipient_ids: list[str] = Field(min_length=1)


class ResourceQuantityRequirementV1(_StrictModel):
    resource_id: str = Field(pattern=_ID)
    quantity: float = Field(gt=0)


class PublicInventoryInputFieldV1(_StrictModel):
    """Provider-safe mapping from one conserved input to its public mirror field."""

    resource_id: str = Field(pattern=_ID)
    field: str = Field(min_length=1)


class TransitionPreconditionProposalV1(_StrictModel):
    """One generic canonical-state guard on an exact transition contract."""

    record_type: Literal["record", "route", "resource"]
    record_id: str = Field(pattern=_ID)
    field: str = Field(min_length=1)
    comparison: Literal["equals", "greater_than_or_equal", "less_than_or_equal"] = (
        "equals"
    )
    expected: Scalar


class ExactGuardRepairV1(_StrictModel):
    """A narrowly scoped reviewer-proposed guard for an existing transport.

    This is deliberately a patch, not a second scenario proposal.  The reviewer
    may only add a typed precondition to a transport already owned by the named
    exact component request; the trusted compiler validates the reference and
    field before it can become executable.
    """

    transition_contract_id: str = Field(pattern=_ID)
    precondition: TransitionPreconditionProposalV1


class ResourceTransformationProposalV1(_StrictModel):
    transformation_id: str = Field(pattern=_ID)
    operator_ids: list[str] = Field(min_length=1)
    input_resource_quantities: list[ResourceQuantityRequirementV1] = Field(min_length=1)
    output_resource_id: str = Field(pattern=_ID)
    output_quantity: float = Field(gt=0)
    maximum_batches: int = Field(ge=1)
    public_inventory_record_id: str = Field(pattern=_ID)
    public_inventory_input_fields: list[PublicInventoryInputFieldV1] = Field(
        default_factory=list,
        exclude_if=lambda value: not value,
    )
    public_inventory_output_field: str | None = Field(
        default=None,
        min_length=1,
        exclude_if=lambda value: value is None,
    )

    @model_validator(mode="before")
    @classmethod
    def migrate_resource_quantity_map(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        migrated = dict(value)
        quantities = migrated.get("input_resource_quantities")
        if isinstance(quantities, dict):
            migrated["input_resource_quantities"] = [
                {"resource_id": resource_id, "quantity": quantity}
                for resource_id, quantity in quantities.items()
            ]
        input_fields = migrated.get("public_inventory_input_fields")
        if isinstance(input_fields, dict):
            migrated["public_inventory_input_fields"] = [
                {"resource_id": resource_id, "field": field}
                for resource_id, field in input_fields.items()
            ]
        return migrated

    @model_validator(mode="after")
    def unique_input_resources(self) -> "ResourceTransformationProposalV1":
        input_field_resource_ids = [
            item.resource_id for item in self.public_inventory_input_fields
        ]
        if len(input_field_resource_ids) != len(set(input_field_resource_ids)):
            raise ValueError("public inventory input resource IDs must be unique")
        resource_ids = [item.resource_id for item in self.input_resource_quantities]
        if len(resource_ids) != len(set(resource_ids)):
            raise ValueError("transformation input resource IDs must be unique")
        return self


class ResourceTransportProposalV1(_StrictModel):
    transport_id: str = Field(pattern=_ID)
    operator_ids: list[str] = Field(min_length=1)
    source_resource_id: str = Field(pattern=_ID)
    destination_resource_id: str = Field(pattern=_ID)
    source_custodian_id: str = Field(pattern=_ID)
    destination_custodian_id: str = Field(pattern=_ID)
    quantity: float = Field(gt=0)
    origin_place_id: str = Field(pattern=_ID)
    destination_place_id: str = Field(pattern=_ID)
    allowed_route_ids: list[str] = Field(min_length=1)
    arrival_record_id: str = Field(pattern=_ID)
    arrival_quantity_key: str = Field(pattern=_ID)
    usable_quantity_key: str = Field(pattern=_ID)
    arrival_minute_key: str = Field(pattern=_ID)
    # A transport result can carry more than quantities.  Keep this optional so
    # existing scenarios remain valid, but require an explicit contract when a
    # later action depends on a result state such as "arrived".
    arrival_status_key: str | None = Field(default=None, pattern=_ID)
    arrival_status_value: Scalar | None = None
    required_preconditions: list[TransitionPreconditionProposalV1] = Field(
        default_factory=list
    )


class AnalysisSpecV1(_StrictModel):
    analysis_id: str = Field(pattern=_ID)
    profile: Literal["waltzman_coordination_v1"]
    purpose: str = Field(min_length=1)


class GeneralSimulationProposalV1(_StrictModel):
    schema_version: Literal[1]
    proposal_kind: Literal["general_world_v1"]
    simulation_id: str = Field(pattern=_ID)
    title: str = Field(min_length=1)
    question: str = Field(min_length=1)
    description: str = Field(min_length=1)
    people: list[GeneralPersonDraft] = Field(min_length=1)
    world_records: list[GeneralWorldRecordProposalV1] = Field(min_length=1)
    active_systems: list[GeneralActiveSystemProposalV1] = Field(min_length=1)
    component_requests: list[ComponentRequestV1] = Field(min_length=1)
    spatial_extension: SpatialExtensionV1 | None
    information_extension: InformationExtensionV1 | None
    resource_extension: ResourceExtensionV1 | None
    relationship_extension: RelationshipExtensionV1 | None
    schedule: list[ScheduledMomentProposalV1] = Field(min_length=1)
    sensing_rules: list[SensingRuleProposalV1]
    resource_transformations: list[ResourceTransformationProposalV1]
    resource_transports: list[ResourceTransportProposalV1]
    fidelity_assumptions: list[str] = Field(min_length=1)
    declared_invariants: list[str]
    analysis_requests: list[str]
    analysis_spec: AnalysisSpecV1 | None = None
    unresolved_questions: list[str]

    @model_validator(mode="before")
    @classmethod
    def migrate_pre_transition_contract_proposals(cls, value: object) -> object:
        """Keep retained pre-contract drafts readable without weakening provider schemas."""
        if not isinstance(value, dict):
            return value
        migrated = dict(value)
        migrated.setdefault("sensing_rules", [])
        migrated.setdefault("resource_transformations", [])
        migrated.setdefault("resource_transports", [])
        return migrated

    @model_validator(mode="after")
    def unique_ids_and_references(self) -> "GeneralSimulationProposalV1":
        collections = {
            "people": [item.entity_id for item in self.people],
            "world records": [item.record_id for item in self.world_records],
            "active systems": [item.system_id for item in self.active_systems],
            "component requests": [item.request_id for item in self.component_requests],
            "schedule": [item.moment_id for item in self.schedule],
        }
        if self.spatial_extension:
            collections.update(
                {
                    "places": [item.place_id for item in self.spatial_extension.places],
                    "placements": [item.record_id for item in self.spatial_extension.placements],
                    "spatial links": [item.link_id for item in self.spatial_extension.links],
                }
            )
        if self.information_extension:
            collections["representations"] = [
                item.representation_id for item in self.information_extension.representations
            ]
        if self.resource_extension:
            collections["resources"] = [
                item.resource_id for item in self.resource_extension.stocks
            ]
        if self.relationship_extension:
            collections["relationships"] = [
                item.relationship_id for item in self.relationship_extension.relationships
            ]
        for label, values in collections.items():
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate {label} IDs")
        request_ids = set(collections["component requests"])
        transition_contract_ids = {
            *[item.rule_id for item in self.sensing_rules],
            *[item.transformation_id for item in self.resource_transformations],
            *[item.transport_id for item in self.resource_transports],
        }
        scheduled_requests: set[str] = set()
        scheduled_contracts: set[str] = set()
        request_contracts = {
            request.request_id: set(request.transition_contract_ids)
            for request in self.component_requests
        }
        for request_id, contract_ids in request_contracts.items():
            if len(contract_ids) != len(
                next(
                    item.transition_contract_ids
                    for item in self.component_requests
                    if item.request_id == request_id
                )
            ):
                raise ValueError(
                    f"component request {request_id} repeats transition contracts"
                )
            unknown_contracts = sorted(contract_ids - transition_contract_ids)
            if unknown_contracts:
                raise ValueError(
                    f"component request {request_id} names unknown transition contracts: "
                    + ", ".join(unknown_contracts)
                )
        for moment in self.schedule:
            if len(moment.active_component_request_ids) != len(
                set(moment.active_component_request_ids)
            ):
                raise ValueError(
                    f"moment {moment.moment_id} repeats active component requests"
                )
            if len(moment.active_transition_contract_ids) != len(
                set(moment.active_transition_contract_ids)
            ):
                raise ValueError(
                    f"moment {moment.moment_id} repeats active transition contracts"
                )
            unknown_requests = sorted(
                set(moment.active_component_request_ids) - request_ids
            )
            if unknown_requests:
                raise ValueError(
                    f"moment {moment.moment_id} names unknown component requests: "
                    + ", ".join(unknown_requests)
                )
            unknown_contracts = sorted(
                set(moment.active_transition_contract_ids) - transition_contract_ids
            )
            if unknown_contracts:
                raise ValueError(
                    f"moment {moment.moment_id} names unknown transition contracts: "
                    + ", ".join(unknown_contracts)
                )
            scheduled_requests.update(moment.active_component_request_ids)
            scheduled_contracts.update(moment.active_transition_contract_ids)
            for request_id in moment.active_component_request_ids:
                inactive_contracts = sorted(
                    request_contracts[request_id]
                    - set(moment.active_transition_contract_ids)
                )
                if inactive_contracts:
                    raise ValueError(
                        f"moment {moment.moment_id} activates component request "
                        f"{request_id} without its transition contracts: "
                        + ", ".join(inactive_contracts)
                    )
        missing_requests = sorted(request_ids - scheduled_requests)
        if missing_requests:
            raise ValueError(
                "every component request must have a scheduled execution moment: "
                + ", ".join(missing_requests)
            )
        missing_contracts = sorted(transition_contract_ids - scheduled_contracts)
        if missing_contracts:
            raise ValueError(
                "every transition contract must have a scheduled execution moment: "
                + ", ".join(missing_contracts)
            )
        unclaimed_contracts = sorted(
            transition_contract_ids
            - set().union(*request_contracts.values())
            if request_contracts
            else transition_contract_ids
        )
        if unclaimed_contracts:
            raise ValueError(
                "every transition contract must belong to a component request: "
                + ", ".join(unclaimed_contracts)
            )
        return self


class CoverageItemV1(_StrictModel):
    request_id: str
    classification: Literal["exact", "coarse_llm", "descriptive", "unsupported"]
    resolved_component_ref: str | None = None
    what_can_change: list[str]
    what_cannot_change: list[str]
    assumptions: list[str]
    blocking: bool
    compiler_evidence: list[str]
    causal_closure: Literal["exact", "partial", "coarse", "descriptive", "unsupported"] = (
        "unsupported"
    )
    dependency_enforcement: list["DependencyEnforcementItemV1"] = Field(
        default_factory=list
    )
    unenforced_dependency_refs: list[str] = Field(default_factory=list)


class DependencyEnforcementItemV1(_StrictModel):
    dependency_ref: str
    enforcement: Literal[
        "exact_read", "exact_write_only", "coarse_llm", "descriptive", "unsupported"
    ]
    transition_contract_ids: list[str] = Field(default_factory=list)
    compiler_evidence: list[str] = Field(default_factory=list)


class ExecutionCoverageReportV1(_StrictModel):
    registry_digest: str
    items: list[CoverageItemV1]
    blocking_request_ids: list[str]

    @property
    def approvable(self) -> bool:
        return not self.blocking_request_ids


class GeneralProposalEnvelopeV1(_StrictModel):
    proposal: GeneralSimulationProposalV1


class GeneralAuthoringDiscussionV1(_StrictModel):
    """One conversational response before configuration is requested."""

    reply: str = Field(min_length=1)
    understood_summary: str = Field(min_length=1)
    material_questions: list[str]


class MissingDependencyFindingV1(_StrictModel):
    exact_action_request_id: str = Field(pattern=_ID)
    prerequisite_description: str = Field(min_length=1)
    existing_ref: str | None
    evidence: str = Field(min_length=1)
    required_resolution: Literal[
        "exact_guard", "required_read", "split_or_coarse", "declare_world_state"
    ]
    guard_repairs: list[ExactGuardRepairV1] = Field(default_factory=list)

    @model_validator(mode="after")
    def guard_repairs_match_resolution(self) -> "MissingDependencyFindingV1":
        if self.guard_repairs and self.required_resolution != "exact_guard":
            raise ValueError("guard repairs are only valid for exact_guard findings")
        return self


class DependencyCompletenessReviewV1(_StrictModel):
    """Semantic audit of whether generated exact actions omit stated prerequisites."""

    status: Literal["complete", "repair_required"]
    summary: str = Field(min_length=1)
    missing_dependencies: list[MissingDependencyFindingV1]

    @model_validator(mode="after")
    def status_matches_findings(self) -> "DependencyCompletenessReviewV1":
        if (self.status == "complete") != (not self.missing_dependencies):
            raise ValueError("dependency review status must match missing_dependencies")
        return self
