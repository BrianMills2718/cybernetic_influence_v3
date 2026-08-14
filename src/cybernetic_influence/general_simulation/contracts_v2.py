"""Separated semantic-world and execution contracts for general simulations."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .authoring_models import (
    ComponentRequestV1,
    GeneralActiveSystemProposalV1,
    GeneralPersonDraft,
    GeneralSimulationProposalV1,
    GeneralWorldRecordProposalV1,
    InformationExtensionV1,
    RelationshipExtensionV1,
    ResourceExtensionV1,
    ResourceTransformationProposalV1,
    ResourceTransportProposalV1,
    ScheduledMomentProposalV1,
    SensingRuleProposalV1,
    SpatialExtensionV1,
)


_ID = r"^[a-z][a-z0-9_]*$"
_DIGEST = r"^[0-9a-f]{64}$"


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


def contract_digest(value: BaseModel | dict[str, object]) -> str:
    """Return the stable identity of one versioned contract payload."""
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


class ComponentRequestV2(ComponentRequestV1):
    """Execution coverage based on causal and fidelity materiality."""

    material_to_question: bool | None = Field(default=None, exclude=True)
    causally_material: bool
    fidelity_material: bool

    @model_validator(mode="after")
    def reject_legacy_materiality(self) -> "ComponentRequestV2":
        if self.material_to_question is not None:
            raise ValueError("V2 component requests cannot use material_to_question")
        return self

    @property
    def blocks_if_unexecutable(self) -> bool:
        return self.causally_material or self.fidelity_material


class ScenarioSpecV2(_StrictModel):
    """What exists and how it may change, without run or analysis authority."""

    scenario_spec_version: Literal[2] = 2
    scenario_id: str = Field(pattern=_ID)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    people: list[GeneralPersonDraft] = Field(min_length=1)
    world_records: list[GeneralWorldRecordProposalV1] = Field(min_length=1)
    active_systems: list[GeneralActiveSystemProposalV1] = Field(min_length=1)
    component_requests: list[ComponentRequestV2] = Field(min_length=1)
    spatial_extension: SpatialExtensionV1 | None = None
    information_extension: InformationExtensionV1 | None = None
    resource_extension: ResourceExtensionV1 | None = None
    relationship_extension: RelationshipExtensionV1 | None = None
    sensing_rules: list[SensingRuleProposalV1] = Field(default_factory=list)
    resource_transformations: list[ResourceTransformationProposalV1] = Field(
        default_factory=list
    )
    resource_transports: list[ResourceTransportProposalV1] = Field(default_factory=list)
    fidelity_assumptions: list[str] = Field(min_length=1)
    declared_invariants: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_primary_ids(self) -> "ScenarioSpecV2":
        collections = {
            "people": [item.entity_id for item in self.people],
            "world records": [item.record_id for item in self.world_records],
            "active systems": [item.system_id for item in self.active_systems],
            "component requests": [item.request_id for item in self.component_requests],
            "sensing rules": [item.rule_id for item in self.sensing_rules],
            "resource transformations": [
                item.transformation_id for item in self.resource_transformations
            ],
            "resource transports": [item.transport_id for item in self.resource_transports],
        }
        for label, values in collections.items():
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate {label} IDs")
        transition_ids = self.transition_contract_ids
        for request in self.component_requests:
            unknown = sorted(set(request.transition_contract_ids) - transition_ids)
            if unknown:
                raise ValueError(
                    f"component request {request.request_id} names unknown transition "
                    f"contracts: {', '.join(unknown)}"
                )
        return self

    @property
    def transition_contract_ids(self) -> set[str]:
        return {
            *[item.rule_id for item in self.sensing_rules],
            *[item.transformation_id for item in self.resource_transformations],
            *[item.transport_id for item in self.resource_transports],
        }

    @property
    def digest(self) -> str:
        return contract_digest(self)


class RunSpecV2(_StrictModel):
    """Controls for one execution, separate from scenario semantics."""

    run_spec_version: Literal[2] = 2
    run_id: str = Field(pattern=_ID)
    scenario_digest: str = Field(pattern=_DIGEST)
    execution_mode: Literal["reference", "live", "replay"]
    model: str | None = Field(default=None, min_length=1)
    reasoning_effort: str | None = Field(default=None, min_length=1)
    per_call_budget: float | None = Field(default=None, gt=0)
    per_run_budget: float | None = Field(default=None, gt=0)
    starting_checkpoint_id: str | None = Field(default=None, pattern=_ID)
    horizon_minutes: int = Field(ge=1)
    scheduled_moments: list[ScheduledMomentProposalV1] = Field(min_length=1)
    termination_conditions: list[str] = Field(default_factory=list)
    seed_or_provider_seed_status: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_execution_controls(self) -> "RunSpecV2":
        moment_ids = [item.moment_id for item in self.scheduled_moments]
        if len(moment_ids) != len(set(moment_ids)):
            raise ValueError("scheduled moment IDs must be unique")
        minutes = [item.minute for item in self.scheduled_moments]
        if minutes != sorted(minutes):
            raise ValueError("scheduled moments must be ordered by minute")
        if max(minutes) > self.horizon_minutes:
            raise ValueError("run horizon cannot precede a scheduled moment")
        provider_fields = (
            self.model,
            self.reasoning_effort,
            self.per_call_budget,
            self.per_run_budget,
        )
        if self.execution_mode in {"reference", "replay"} and any(
            item is not None for item in provider_fields
        ):
            raise ValueError(
                "reference and replay runs cannot contain live provider controls"
            )
        if self.execution_mode == "live" and any(
            item is None for item in provider_fields
        ):
            raise ValueError("live runs require complete provider controls")
        return self

    @property
    def digest(self) -> str:
        return contract_digest(self)


def adapt_general_proposal_v1(
    proposal: GeneralSimulationProposalV1,
    *,
    run_id: str,
    execution_mode: Literal["reference", "live", "replay"] = "reference",
    model: str | None = None,
    reasoning_effort: str | None = None,
    per_call_budget: float | None = None,
    per_run_budget: float | None = None,
) -> tuple[ScenarioSpecV2, RunSpecV2]:
    """Translate one retained V1 proposal into the separated execution inputs.

    The V1 question and analysis fields are deliberately not projected into
    either executable contract. Callers may retain them as presentation or
    candidate post-run analysis metadata.
    """
    scenario = ScenarioSpecV2(
        scenario_id=proposal.simulation_id,
        title=proposal.title,
        description=proposal.description,
        people=proposal.people,
        world_records=proposal.world_records,
        active_systems=proposal.active_systems,
        component_requests=[
            ComponentRequestV2(
                request_id=item.request_id,
                subject_refs=item.subject_refs,
                behavior_description=item.behavior_description,
                required_reads=item.required_reads,
                desired_effects=item.desired_effects,
                fidelity_need=item.fidelity_need,
                causally_material=item.material_to_question,
                fidelity_material=False,
                transition_contract_ids=item.transition_contract_ids,
            )
            for item in proposal.component_requests
        ],
        spatial_extension=proposal.spatial_extension,
        information_extension=proposal.information_extension,
        resource_extension=proposal.resource_extension,
        relationship_extension=proposal.relationship_extension,
        sensing_rules=proposal.sensing_rules,
        resource_transformations=proposal.resource_transformations,
        resource_transports=proposal.resource_transports,
        fidelity_assumptions=proposal.fidelity_assumptions,
        declared_invariants=proposal.declared_invariants,
    )
    run_spec = RunSpecV2(
        run_id=run_id,
        scenario_digest=scenario.digest,
        execution_mode=execution_mode,
        model=model,
        reasoning_effort=reasoning_effort,
        per_call_budget=per_call_budget,
        per_run_budget=per_run_budget,
        horizon_minutes=max(item.minute for item in proposal.schedule),
        scheduled_moments=proposal.schedule,
    )
    return scenario, run_spec


def validate_run_against_scenario(
    scenario: ScenarioSpecV2, run_spec: RunSpecV2
) -> None:
    """Validate references spanning the separated contracts."""
    if run_spec.scenario_digest != scenario.digest:
        raise ValueError("RunSpec scenario digest does not match ScenarioSpec")
    request_ids = {item.request_id for item in scenario.component_requests}
    representation_ids = (
        {
            item.representation_id
            for item in scenario.information_extension.representations
        }
        if scenario.information_extension
        else set()
    )
    scheduled_requests: set[str] = set()
    scheduled_contracts: set[str] = set()
    for moment in run_spec.scheduled_moments:
        unknown_requests = set(moment.active_component_request_ids) - request_ids
        unknown_contracts = (
            set(moment.active_transition_contract_ids)
            - scenario.transition_contract_ids
        )
        unknown_injects = (
            set(moment.external_inject_representation_ids) - representation_ids
        )
        if unknown_requests:
            raise ValueError(
                f"moment {moment.moment_id} names unknown component requests: "
                + ", ".join(sorted(unknown_requests))
            )
        if unknown_contracts:
            raise ValueError(
                f"moment {moment.moment_id} names unknown transition contracts: "
                + ", ".join(sorted(unknown_contracts))
            )
        if unknown_injects:
            raise ValueError(
                f"moment {moment.moment_id} names unknown external injects: "
                + ", ".join(sorted(unknown_injects))
            )
        scheduled_requests.update(moment.active_component_request_ids)
        scheduled_contracts.update(moment.active_transition_contract_ids)
        for request_id in moment.active_component_request_ids:
            request = next(
                item for item in scenario.component_requests if item.request_id == request_id
            )
            inactive = set(request.transition_contract_ids) - set(
                moment.active_transition_contract_ids
            )
            if inactive:
                raise ValueError(
                    f"moment {moment.moment_id} activates component request {request_id} "
                    f"without its transition contracts: {', '.join(sorted(inactive))}"
                )
    missing_requests = request_ids - scheduled_requests
    missing_contracts = scenario.transition_contract_ids - scheduled_contracts
    if missing_requests:
        raise ValueError(
            "every component request must have a scheduled execution moment: "
            + ", ".join(sorted(missing_requests))
        )
    if missing_contracts:
        raise ValueError(
            "every transition contract must have a scheduled execution moment: "
            + ", ".join(sorted(missing_contracts))
        )
