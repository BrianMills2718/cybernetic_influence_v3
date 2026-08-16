"""Small, extensible contracts for canonical world transitions.

The kernel deliberately does not encode ports, outbreaks, institutions, or any
other scenario family. Domain records use open ``kind`` strings while every
executable mutation must still pass a registered authority's patch grammar.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator


JsonScalar = None | bool | int | float | str
PatchValue = (
    JsonScalar
    | list[JsonScalar]
    | dict[str, JsonScalar | list[JsonScalar] | dict[str, JsonScalar]]
)



class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WorldRecord(StrictModel):
    record_id: str
    kind: str
    label: str
    state: dict[str, JsonValue] = Field(default_factory=dict)
    hidden_state: dict[str, JsonValue] = Field(default_factory=dict)


class Place(StrictModel):
    place_id: str
    label: str


class Placement(StrictModel):
    record_id: str
    place_id: str


class Route(StrictModel):
    route_id: str
    origin_id: str
    destination_id: str
    operational: bool = True
    public_state: dict[str, JsonValue] = Field(default_factory=dict)
    hidden_state: dict[str, JsonValue] = Field(default_factory=dict)


class Representation(StrictModel):
    representation_id: str
    content: str
    apparent_source: str
    recipient_ids: list[str]
    hidden_provenance: dict[str, JsonValue] = Field(default_factory=dict)


class ResourceStock(StrictModel):
    resource_id: str
    quantity: float
    custodian_id: str
    conserved: bool = True


class Observation(StrictModel):
    observation_id: str
    content: str
    apparent_source: str
    representation_id: str | None = None


class Consequence(StrictModel):
    consequence_id: str
    recipient_id: str
    content: str
    apparent_source: str
    representation_id: str | None = None


class GeneralWorldState(StrictModel):
    revision: int = 0
    records: dict[str, WorldRecord] = Field(default_factory=dict)
    places: dict[str, Place] = Field(default_factory=dict)
    placements: dict[str, Placement] = Field(default_factory=dict)
    routes: dict[str, Route] = Field(default_factory=dict)
    representations: dict[str, Representation] = Field(default_factory=dict)
    resources: dict[str, ResourceStock] = Field(default_factory=dict)
    outbox: list[Consequence] = Field(default_factory=list)
    delivered_consequence_ids: list[str] = Field(default_factory=list)


class PatchGrammar(StrictModel):
    allowed_operations: list[Literal["create", "remove", "replace", "rebind"]]
    allowed_record_types: list[
        Literal["record", "place", "placement", "route", "representation", "resource"]
    ]


class TransitionAuthoritySpec(StrictModel):
    authority_id: str
    implementation: Literal["deterministic", "stochastic", "llm", "external", "scripted"]
    patch_grammar: PatchGrammar
    reads: list[str]
    writes: list[str]
    deterministic: bool
    replayable_from_receipt: bool
    externally_stateful: bool = False
    synchronous: bool = True
    idempotent: bool = False
    assumptions: list[str] = Field(default_factory=list)
    invalid_questions: list[str] = Field(default_factory=list)


class ActiveSystemSpec(StrictModel):
    system_id: str
    executor: Literal["actor", "transition_authority", "inert"]
    authority_id: str | None = None
    resolution: str


class ActorAccessSpec(StrictModel):
    actor_id: str
    record_ids: list[str]
    route_ids: list[str]
    representation_ids: list[str]


class AvailableTransitionContract(StrictModel):
    contract_id: str
    contract_kind: Literal["sensing", "resource_transformation", "resource_transport"]
    summary: str
    target_refs: list[str]


class SensingTransitionContract(StrictModel):
    contract_id: str
    subject_type: Literal["record", "route"]
    subject_id: str
    observer_ids: list[str]
    hidden_to_output_fields: dict[str, str]
    output_record_id: str
    result_recipient_ids: list[str]


class ResourceTransformationContract(StrictModel):
    contract_id: str
    operator_ids: list[str]
    input_resource_quantities: dict[str, float]
    output_resource_id: str
    output_quantity: float
    maximum_batches: int
    public_inventory_record_id: str


class ResourceTransportContract(StrictModel):
    contract_id: str
    operator_ids: list[str]
    source_resource_id: str
    destination_resource_id: str
    quantity: float
    origin_place_id: str
    destination_place_id: str
    allowed_route_ids: list[str]
    arrival_record_id: str
    arrival_quantity_key: str
    usable_quantity_key: str
    arrival_minute_key: str
    required_preconditions: list["Precondition"] = Field(default_factory=list)


class GeneralWorldSpec(StrictModel):
    spec_id: str
    initial_state: GeneralWorldState
    active_systems: list[ActiveSystemSpec]
    authorities: list[TransitionAuthoritySpec]
    invariants: list[str]
    fidelity_assumptions: list[str]
    timing: dict[str, int] = Field(default_factory=dict)
    actor_access: list[ActorAccessSpec] = Field(default_factory=list)
    sensing_contracts: list[SensingTransitionContract] = Field(default_factory=list)
    resource_transformation_contracts: list[ResourceTransformationContract] = Field(
        default_factory=list
    )
    resource_transport_contracts: list[ResourceTransportContract] = Field(
        default_factory=list
    )

    @model_validator(mode="after")
    def references_registered_authorities(self) -> "GeneralWorldSpec":
        ids = {authority.authority_id for authority in self.authorities}
        missing = {
            system.authority_id
            for system in self.active_systems
            if system.authority_id is not None and system.authority_id not in ids
        }
        if missing:
            raise ValueError(f"unregistered transition authorities: {sorted(missing)}")
        return self


class ActorContext(StrictModel):
    actor_id: str
    base_revision: int
    current_minute: int = 0
    observations: list[Observation]
    accessible_records: list[WorldRecord]
    accessible_routes: list[Route]
    private_memory: list[str]
    available_transition_contracts: list[AvailableTransitionContract] = Field(
        default_factory=list
    )
    phase_description: str | None = None
    phase_responsibilities: list[str] = Field(default_factory=list)


class MemoryRevision(StrictModel):
    prior_memory: str
    revised_memory: str


class Assimilation(StrictModel):
    attended_observation_ids: list[str]
    memory_additions: list[str]
    memory_revisions: list[MemoryRevision]
    provenance_links: list[str] = Field(
        description=(
            "Only supplied observation IDs, representation IDs, accessible record/route "
            "IDs, or private_memory:<exact supplied memory>."
        )
    )
    interpretation: str


class SemanticActionIntent(StrictModel):
    intent_id: str
    actor_id: str
    base_revision: int
    action: str
    target_refs: list[str]
    purpose: str
    expected_effect: str
    stated_rationale: str
    transition_contract_ids: list[str] = Field(default_factory=list)


class ActorDecision(StrictModel):
    assimilation: Assimilation
    intent: SemanticActionIntent


class TypedTarget(StrictModel):
    record_type: Literal[
        "record", "place", "placement", "route", "representation", "resource"
    ]
    record_id: str
    field: str | None = None


class PatchOperation(StrictModel):
    operation: Literal["create", "remove", "replace", "rebind"]
    target: TypedTarget
    value: PatchValue = None


class Precondition(StrictModel):
    target: TypedTarget
    comparison: Literal["equals", "greater_than_or_equal", "less_than_or_equal"] = (
        "equals"
    )
    expected: PatchValue


class ObjectiveAssessment(StrictModel):
    status: Literal["achieved", "partially_achieved", "failed", "unresolved"]
    summary: str
    evidence_refs: list[str]
    unresolved_requirements: list[str] = Field(default_factory=list)


class WorldTransactionProposal(StrictModel):
    """Execution-only transition proposal with no analytical output authority."""

    transaction_id: str
    base_revision: int
    authority_id: str
    intent_ids: list[str]
    operations: list[PatchOperation]
    preconditions: list[Precondition]
    consequences: list[Consequence]
    evidence_refs: list[str] = Field(
        description=(
            "Canonical record, place, route, representation, resource, or collected intent "
            "identities supporting the proposed transition."
        )
    )
    stated_rationale: str

    def as_transaction(self) -> "WorldTransaction":
        return WorldTransaction.model_validate(self.model_dump(mode="json"))


class WorldTransaction(StrictModel):
    transaction_id: str
    base_revision: int
    authority_id: str
    intent_ids: list[str]
    operations: list[PatchOperation]
    preconditions: list[Precondition]
    consequences: list[Consequence]
    evidence_refs: list[str] = Field(
        description=(
            "Canonical record, place, route, representation, resource, or collected intent "
            "identities supporting the proposed transition."
        )
    )
    stated_rationale: str
    objective_assessment: ObjectiveAssessment | None = None


class ValidationResult(StrictModel):
    accepted: bool
    base_revision: int
    resulting_revision: int
    errors: list[str]


class TransitionEvidence(StrictModel):
    transaction: WorldTransaction
    envelope_corrections: list[str]
    validation: ValidationResult
    resulting_state_hash: str
    operation_attributions: list["OperationAttribution"] = Field(default_factory=list)


class OperationAttribution(StrictModel):
    operation_index: int
    authority_id: str
    classification: Literal["exact_contract", "coarse_authority", "no_op"]
    contract_id: str | None = None
    intent_ids: list[str] = Field(default_factory=list)


class ModelCallReceipt(StrictModel):
    role: Literal["actor", "adjudicator"]
    provider: str
    model: str
    trace_id: str
    input_context: str
    structured_output: dict[str, Any]
    decoding: dict[str, JsonValue]
    exact_replay_possible: bool


class AdoptionReceipt(StrictModel):
    simulation_class: str
    engine_class: str
    actor_selection_component: str
    concordia_revision: str
    actor_names: list[str]
    game_master_names: list[str]
    lifecycle_events: list[str]
    forbidden_runtime_imports: list[str]


class GeneralSimulationResult(StrictModel):
    checkpoint_hash: str
    restored_checkpoint_hash: str
    final_state: GeneralWorldState
    transition_evidence: list[TransitionEvidence]
    model_calls: list[ModelCallReceipt]
    actor_contexts: list[ActorContext]
    adoption: AdoptionReceipt


class GeneralMomentEvidence(StrictModel):
    moment_id: str
    minute: int
    description: str
    frozen_revision: int
    actor_ids: list[str]
    intent_ids: list[str]
    resulting_revision: int
    checkpoint_hash: str


class GeneralGroupSimulationResult(StrictModel):
    simulation_id: str
    title: str
    question: str
    proposal_digest: str
    registry_digest: str
    final_state: GeneralWorldState
    transition_evidence: list[TransitionEvidence]
    model_calls: list[ModelCallReceipt]
    moments: list[GeneralMomentEvidence]
    checkpoints: list[dict[str, Any]]
    adoption: AdoptionReceipt


class GeneralGroupSimulationResultV2(StrictModel):
    run_id: str
    scenario_id: str
    title: str
    scenario_digest: str
    run_spec_digest: str
    registry_digest: str
    final_state: GeneralWorldState
    transition_evidence: list[TransitionEvidence]
    model_calls: list[ModelCallReceipt]
    moments: list[GeneralMomentEvidence]
    checkpoints: list[dict[str, Any]]
    adoption: AdoptionReceipt
