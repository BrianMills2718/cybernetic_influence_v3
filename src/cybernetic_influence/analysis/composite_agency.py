"""Strict, execution-inert contracts for a composite-agency perturbation assay.

This module prepares and validates retained analysis inputs. It cannot execute a
scenario, apply a perturbation, call a model, or mutate world state.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from cybernetic_influence.analysis.coordination_measurement import (
    COORDINATION_MEASUREMENT_SPEC_FINGERPRINT,
    EXACT_MEASURE_IDS,
    RunMeasurementConsumer,
)
from cybernetic_influence.analysis.theory_analysis import (
    RunEvidenceBundleConsumerV1,
)
from cybernetic_influence.presentation import BoundaryActivityProjection
from cybernetic_influence.scenarios.coordination_decision import (
    PERSON_IDS,
    CoordinationDecisionFixture,
    scenario_fingerprint,
)

CAPABILITY_ID: Literal[
    "valid_collective_decision_by_deadline_v1"
] = "valid_collective_decision_by_deadline_v1"
CONTROL_ID: Literal["matched_control"] = "matched_control"
BOUNDARY_ID: Literal["deployment_partnership"] = "deployment_partnership"
COORDINATION_SCENARIO_ID: Literal[
    "coordination_decision_v1"
] = "coordination_decision_v1"

PerturbationFamily: TypeAlias = Literal[
    "component", "structure", "feedback", "shock"
]
PerturbationVariant: TypeAlias = Literal[
    "position_matched_member_replacement",
    "decision_route_interruption",
    "verification_feedback_interruption",
    "relevant_external_risk",
]
PerturbationApplication: TypeAlias = Literal[
    "initial_condition", "scheduled_day_4"
]
CompositePatternId: TypeAlias = Literal[
    "competence_loss",
    "effective_goal_drift_or_capture",
    "fragmentation",
    "defensive_adaptation",
    "rational_caution",
    "unclear",
]
_ID_PATTERN = r"^[a-z][a-z0-9_]*$"
_DIGEST_PATTERN = r"^[0-9a-f]{64}$"
_EVENT_ID_PATTERN = r"^event_[0-9]{6}$"
_EVIDENCE_REF_PATTERN = r"^[A-Za-z0-9_.:-]+$"
EventId: TypeAlias = Annotated[str, Field(pattern=_EVENT_ID_PATTERN)]
EvidenceRef: TypeAlias = Annotated[str, Field(pattern=_EVIDENCE_REF_PATTERN)]

_EXPECTED_VARIANT_CONTRACT: dict[
    PerturbationVariant,
    tuple[PerturbationFamily, PerturbationApplication, frozenset[str]],
] = {
    "position_matched_member_replacement": (
        "component",
        "initial_condition",
        frozenset({"technical_validation_lead"}),
    ),
    "decision_route_interruption": (
        "structure",
        "scheduled_day_4",
        frozenset({"terminal_proposal_route"}),
    ),
    "verification_feedback_interruption": (
        "feedback",
        "scheduled_day_4",
        frozenset(
            {
                f"verification_response_{person_id}_route"
                for person_id in PERSON_IDS
            }
        ),
    ),
    "relevant_external_risk": (
        "shock",
        "scheduled_day_4",
        frozenset(
            {
                "external_risk_source",
                "external_risk_message",
                "external_risk_route",
            }
        ),
    ),
}

_REQUIRED_SUCCESS_MEASURES = frozenset(
    {
        "final_deployment_status",
        "modeled_time_to_terminal",
        "final_approved_scope",
    }
)
_REQUIRED_CONSTRAINT_MEASURES = frozenset(
    {
        "partners_retained",
        "unresolved_risk_load",
        "disengagement",
    }
)
_REQUIRED_ASSAY_EXACT_VALUES = frozenset(
    {
        "capability_satisfied",
        "all_constraints_satisfied",
        "failed_constraint_ids",
        "terminal_outcome",
        "modeled_decision_time",
        "correction_event_pairs",
        "recovery",
        "alternate_routes_used",
        "active_partners_retained",
        "member_replacements",
        "terminal_proposal_denials",
        "input_crossing_count",
        "output_crossing_count",
        "completed_episode_count",
        "in_progress_episode_count",
    }
)


class CompositeAssayContractError(ValueError):
    """Assay setup or retained evidence violates the reviewed contract."""


class _ProducedModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class _ConsumerModel(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)


class CompositeCapabilitySpec(_ProducedModel):
    """One reviewed collective capability; never an executable actor."""

    schema_version: Literal[1] = 1
    capability_id: Literal[
        "valid_collective_decision_by_deadline_v1"
    ] = CAPABILITY_ID
    boundary_id: Literal["deployment_partnership"] = BOUNDARY_ID
    member_refs: list[str] = Field(min_length=1)
    substrate_refs: list[str] = Field(min_length=1)
    exact_success_measure_ids: list[str] = Field(min_length=1)
    exact_constraint_measure_ids: list[str] = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_capability(self) -> "CompositeCapabilitySpec":
        for label, refs in (
            ("members", self.member_refs),
            ("substrates", self.substrate_refs),
            ("success measures", self.exact_success_measure_ids),
            ("constraint measures", self.exact_constraint_measure_ids),
            ("limitations", self.limitations),
        ):
            if len(refs) != len(set(refs)):
                raise ValueError(f"capability {label} must be unique")
        if set(self.exact_success_measure_ids) != _REQUIRED_SUCCESS_MEASURES:
            raise ValueError("capability success measures do not match the review")
        if set(self.exact_constraint_measure_ids) != _REQUIRED_CONSTRAINT_MEASURES:
            raise ValueError("capability constraint measures do not match the review")
        if not (
            set(self.exact_success_measure_ids)
            | set(self.exact_constraint_measure_ids)
        ) <= set(EXACT_MEASURE_IDS):
            raise ValueError("capability references an unknown exact measure")
        return self


class CompositeCapabilitySpecConsumer(CompositeCapabilitySpec):
    """Forward-tolerant reopening projection with unchanged invariants."""

    model_config = ConfigDict(extra="ignore", strict=True)


class PerturbationSpec(_ProducedModel):
    """One of four reviewed changes; arbitrary patches are impossible."""

    schema_version: Literal[1] = 1
    perturbation_id: str = Field(pattern=_ID_PATTERN)
    family: PerturbationFamily
    variant: PerturbationVariant
    application: PerturbationApplication
    changed_refs: list[str] = Field(min_length=1)
    matched_control_id: Literal["matched_control"] = CONTROL_ID
    description: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_variant(self) -> "PerturbationSpec":
        if len(self.changed_refs) != len(set(self.changed_refs)):
            raise ValueError("perturbation changed references must be unique")
        expected_family, expected_application, expected_refs = (
            _EXPECTED_VARIANT_CONTRACT[self.variant]
        )
        if self.family != expected_family:
            raise ValueError("perturbation family does not match its variant")
        if self.application != expected_application:
            raise ValueError("perturbation application does not match its variant")
        if set(self.changed_refs) != expected_refs:
            raise ValueError("perturbation changed references exceed reviewed scope")
        if BOUNDARY_ID in self.changed_refs:
            raise ValueError(
                "an analytical boundary cannot be perturbed as an executor"
            )
        return self


class PerturbationSpecConsumer(PerturbationSpec):
    """Forward-tolerant reopening projection with unchanged invariants."""

    model_config = ConfigDict(extra="ignore", strict=True)


class CompositeAssayRunRef(_ProducedModel):
    """Identity and validity of one retained row run."""

    schema_version: Literal[1] = 1
    run_id: str = Field(pattern=_ID_PATTERN)
    perturbation_id: str = Field(pattern=_ID_PATTERN)
    scenario_fingerprint: str = Field(pattern=_DIGEST_PATTERN)
    measurement_spec_version: Literal[1] = 1
    valid: bool
    invalid_reason: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_validity(self) -> "CompositeAssayRunRef":
        if self.valid == (self.invalid_reason is not None):
            raise ValueError("valid run and invalid reason disagree")
        return self


class CompositeAssayRunRefConsumer(CompositeAssayRunRef):
    """Forward-tolerant reopening projection with unchanged invariants."""

    model_config = ConfigDict(extra="ignore", strict=True)


class CompositePatternEvidence(_ProducedModel):
    """One perturbation-pattern interpretation tied to retained evidence."""

    pattern_id: CompositePatternId
    direction: Literal["present", "absent", "unclear"]
    explanation: str = Field(min_length=1)
    source_event_ids: list[EventId] = Field(min_length=1)
    source_trace_ids: list[EvidenceRef] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_citations(self) -> "CompositePatternEvidence":
        for label, refs in (
            ("event citations", self.source_event_ids),
            ("trace citations", self.source_trace_ids),
        ):
            if len(refs) != len(set(refs)):
                raise ValueError(f"composite pattern {label} must be unique")
        return self


class CompositeControlReadout(_ProducedModel):
    """One evidence-reversible row; attempts, results, and outcome stay separate."""

    schema_version: Literal[1] = 1
    capability_id: Literal[
        "valid_collective_decision_by_deadline_v1"
    ] = CAPABILITY_ID
    boundary_id: Literal["deployment_partnership"] = BOUNDARY_ID
    perturbation_id: str = Field(pattern=_ID_PATTERN)
    exact_values: dict[str, JsonValue]
    boundary_activity_ref: str = Field(pattern=_EVIDENCE_REF_PATTERN)
    input_crossing_ids: list[str]
    output_crossing_ids: list[str]
    coordination_episode_ids: list[str]
    output_attempt_event_ids: list[str]
    external_result_event_ids: list[str]
    terminal_outcome_event_id: str = Field(pattern=_EVENT_ID_PATTERN)
    coordination_measurement_ref: str = Field(pattern=_ID_PATTERN)
    coded_patterns: list[CompositePatternEvidence]
    source_run_ids: list[str] = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_readout_shape(self) -> "CompositeControlReadout":
        for label, refs in (
            ("input crossings", self.input_crossing_ids),
            ("output crossings", self.output_crossing_ids),
            ("episodes", self.coordination_episode_ids),
            ("output attempts", self.output_attempt_event_ids),
            ("external results", self.external_result_event_ids),
            (
                "coded patterns",
                [item.pattern_id for item in self.coded_patterns],
            ),
            ("source runs", self.source_run_ids),
            ("limitations", self.limitations),
        ):
            if len(refs) != len(set(refs)):
                raise ValueError(f"readout {label} must be unique")
        if set(self.exact_values) != _REQUIRED_ASSAY_EXACT_VALUES:
            raise ValueError("readout exact-value vector does not match schema v1")
        if self.output_attempt_event_ids and not self.output_crossing_ids:
            raise ValueError(
                "claimed composite output requires an outgoing boundary crossing"
            )
        separated = (
            set(self.output_attempt_event_ids),
            set(self.external_result_event_ids),
            {self.terminal_outcome_event_id},
        )
        if any(
            left & right
            for index, left in enumerate(separated)
            for right in separated[index + 1 :]
        ):
            raise ValueError(
                "output attempt, external result, and terminal outcome must differ"
            )
        capability_satisfied = self.exact_values["capability_satisfied"]
        constraints_satisfied = self.exact_values["all_constraints_satisfied"]
        failed_constraints = self.exact_values["failed_constraint_ids"]
        if not isinstance(capability_satisfied, bool):
            raise ValueError("capability satisfaction must be boolean")
        if not isinstance(constraints_satisfied, bool):
            raise ValueError("constraint satisfaction must be boolean")
        if not isinstance(failed_constraints, list) or any(
            not isinstance(item, str) for item in failed_constraints
        ):
            raise ValueError("failed constraints must be a list of IDs")
        if constraints_satisfied == bool(failed_constraints):
            raise ValueError("constraint status and failed constraints disagree")
        if capability_satisfied and not constraints_satisfied:
            raise ValueError("capability cannot pass while a constraint fails")
        if capability_satisfied and not self.output_crossing_ids:
            raise ValueError(
                "satisfied collective capability requires an outgoing crossing"
            )
        return self


class CompositeControlReadoutConsumer(CompositeControlReadout):
    """Forward-tolerant reopening projection with unchanged invariants."""

    model_config = ConfigDict(extra="ignore", strict=True)


class CompositeAssayScenarioFixture(_ProducedModel):
    """Reviewed scenario facts needed to compile an execution-free assay setup."""

    schema_version: Literal[1] = 1
    scenario_id: Literal["coordination_decision_v1"] = "coordination_decision_v1"
    scenario_revision: str = Field(pattern=_ID_PATTERN)
    control_scenario_fingerprint: str = Field(pattern=_DIGEST_PATTERN)
    boundary_id: Literal["deployment_partnership"] = BOUNDARY_ID
    member_refs: list[str] = Field(min_length=1)
    substrate_refs: list[str] = Field(min_length=1)
    configured_refs: list[str] = Field(min_length=1)
    reviewed_created_refs: list[str]
    executable_refs: list[str] = Field(min_length=1)
    matched_world_fingerprint: str = Field(pattern=_DIGEST_PATTERN)
    model_policy_fingerprint: str = Field(pattern=_DIGEST_PATTERN)
    run_control_fingerprint: str = Field(pattern=_DIGEST_PATTERN)

    @model_validator(mode="after")
    def validate_fixture(self) -> "CompositeAssayScenarioFixture":
        for label, refs in (
            ("members", self.member_refs),
            ("substrates", self.substrate_refs),
            ("configured references", self.configured_refs),
            ("reviewed created references", self.reviewed_created_refs),
            ("executable references", self.executable_refs),
        ):
            if len(refs) != len(set(refs)):
                raise ValueError(f"scenario fixture {label} must be unique")
        configured = set(self.configured_refs)
        if not set(self.member_refs) | set(self.substrate_refs) <= configured:
            raise ValueError("scenario fixture contains an unknown member or substrate")
        if BOUNDARY_ID in self.executable_refs:
            raise ValueError("analytical boundary cannot be a scenario executor")
        if not set(self.executable_refs) <= configured:
            raise ValueError("scenario fixture contains an unknown executor")
        if set(self.reviewed_created_refs) & configured:
            raise ValueError("reviewed created reference already exists in scenario")
        return self


class CompositeAssaySetup(_ProducedModel):
    """Compiled five-row setup; it contains no trajectories or run authority."""

    schema_version: Literal[1] = 1
    scenario_revision: str = Field(pattern=_ID_PATTERN)
    control_id: Literal["matched_control"] = CONTROL_ID
    capability: CompositeCapabilitySpec
    perturbations: list[PerturbationSpec] = Field(min_length=4, max_length=4)
    row_ids: list[str] = Field(min_length=5, max_length=5)
    control_scenario_fingerprint: str = Field(pattern=_DIGEST_PATTERN)
    matched_world_fingerprint: str = Field(pattern=_DIGEST_PATTERN)
    model_policy_fingerprint: str = Field(pattern=_DIGEST_PATTERN)
    run_control_fingerprint: str = Field(pattern=_DIGEST_PATTERN)
    measurement_spec_version: Literal[1] = 1
    measurement_spec_fingerprint: str = Field(pattern=_DIGEST_PATTERN)

    @model_validator(mode="after")
    def validate_setup(self) -> "CompositeAssaySetup":
        perturbation_ids = [item.perturbation_id for item in self.perturbations]
        variants = [item.variant for item in self.perturbations]
        if len(perturbation_ids) != len(set(perturbation_ids)):
            raise ValueError("setup perturbation IDs must be unique")
        if set(variants) != set(_EXPECTED_VARIANT_CONTRACT):
            raise ValueError("setup must contain each reviewed variant exactly once")
        if self.row_ids != [CONTROL_ID, *perturbation_ids]:
            raise ValueError("setup row order must be control then perturbations")
        if (
            self.measurement_spec_fingerprint
            != COORDINATION_MEASUREMENT_SPEC_FINGERPRINT
        ):
            raise ValueError("setup measurement specification is not current")
        return self


class CompositeAssayRunEvidence(_ProducedModel):
    """Existing retained artifacts needed to validate one completed row."""

    schema_version: Literal[1] = 1
    run_id: str = Field(pattern=_ID_PATTERN)
    perturbation_id: str = Field(pattern=_ID_PATTERN)
    scenario_revision: str = Field(pattern=_ID_PATTERN)
    matched_world_fingerprint: str = Field(pattern=_DIGEST_PATTERN)
    model_policy_fingerprint: str = Field(pattern=_DIGEST_PATTERN)
    run_control_fingerprint: str = Field(pattern=_DIGEST_PATTERN)
    applied_changed_refs: list[str]
    perturbation_application_event_id: str | None = Field(
        default=None, pattern=_EVENT_ID_PATTERN
    )
    evidence_bundle: RunEvidenceBundleConsumerV1
    measurement: RunMeasurementConsumer | None = None
    boundary_activity_ref: str | None = Field(
        default=None, pattern=_EVIDENCE_REF_PATTERN
    )
    boundary_activity: BoundaryActivityProjection | None = None

    @model_validator(mode="after")
    def validate_evidence_identity(self) -> "CompositeAssayRunEvidence":
        if len(self.applied_changed_refs) != len(set(self.applied_changed_refs)):
            raise ValueError("applied changed references must be unique")
        if self.evidence_bundle.run_id != self.run_id:
            raise ValueError("evidence bundle belongs to another run")
        if self.measurement is not None and self.measurement.run_id != self.run_id:
            raise ValueError("coordination measurement belongs to another run")
        if self.evidence_bundle.scenario_id != COORDINATION_SCENARIO_ID:
            raise ValueError("assay evidence is not the coordination scenario")
        if (self.boundary_activity_ref is None) != (self.boundary_activity is None):
            raise ValueError("boundary activity reference and projection must coexist")
        if self.boundary_activity is not None:
            if self.boundary_activity.boundary_id != BOUNDARY_ID:
                raise ValueError("assay evidence uses the wrong analytical boundary")
            evidence_refs = {
                item.evidence_ref for item in self.evidence_bundle.evidence_records
            }
            if self.boundary_activity_ref not in evidence_refs:
                raise ValueError(
                    "boundary activity reference is not retained in the bundle"
                )
        return self


class CompositeAssayEvidenceSet(_ProducedModel):
    """Validated matrix evidence; invalid runs remain visible and unscored."""

    schema_version: Literal[1] = 1
    setup: CompositeAssaySetup
    run_refs: list[CompositeAssayRunRef] = Field(min_length=5)
    readouts: list[CompositeControlReadout]

    @model_validator(mode="after")
    def validate_matrix_shape(self) -> "CompositeAssayEvidenceSet":
        run_ids = [item.run_id for item in self.run_refs]
        row_ids = [item.perturbation_id for item in self.run_refs]
        readout_rows = [item.perturbation_id for item in self.readouts]
        if len(run_ids) != len(set(run_ids)):
            raise ValueError("evidence set run IDs must be unique")
        if len(row_ids) != len(set(row_ids)):
            raise ValueError("evidence set rows must be unique")
        if set(row_ids) != set(self.setup.row_ids):
            raise ValueError("evidence set rows do not match setup")
        valid_rows = {
            item.perturbation_id for item in self.run_refs if item.valid
        }
        if len(readout_rows) != len(set(readout_rows)):
            raise ValueError("evidence set readout rows must be unique")
        if set(readout_rows) != valid_rows:
            raise ValueError("evidence set scores invalid or omits valid runs")
        return self


def compile_composite_assay_setup(
    fixture: CompositeAssayScenarioFixture,
    capability: CompositeCapabilitySpec,
    perturbations: Sequence[PerturbationSpec],
) -> CompositeAssaySetup:
    """Compile the reviewed five rows without executing or scheduling a run."""

    if capability.boundary_id != fixture.boundary_id:
        raise CompositeAssayContractError("capability boundary does not match scenario")
    if capability.member_refs != fixture.member_refs:
        raise CompositeAssayContractError("capability members do not match scenario")
    if capability.substrate_refs != fixture.substrate_refs:
        raise CompositeAssayContractError("capability substrates do not match scenario")
    by_variant = {item.variant: item for item in perturbations}
    if len(by_variant) != len(perturbations):
        raise CompositeAssayContractError("perturbation variants must be unique")
    if set(by_variant) != set(_EXPECTED_VARIANT_CONTRACT):
        raise CompositeAssayContractError(
            "setup requires each reviewed perturbation variant exactly once"
        )
    perturbation_ids = [item.perturbation_id for item in perturbations]
    if len(perturbation_ids) != len(set(perturbation_ids)):
        raise CompositeAssayContractError("perturbation IDs must be unique")
    if CONTROL_ID in perturbation_ids:
        raise CompositeAssayContractError("control ID cannot identify a perturbation")
    configured = set(fixture.configured_refs) | set(fixture.reviewed_created_refs)
    for perturbation in perturbations:
        unknown = set(perturbation.changed_refs) - configured
        if unknown:
            raise CompositeAssayContractError(
                "perturbation references unknown configured objects "
                f"{sorted(unknown)!r}"
            )
    return CompositeAssaySetup(
        scenario_revision=fixture.scenario_revision,
        capability=capability,
        perturbations=list(perturbations),
        row_ids=[CONTROL_ID, *perturbation_ids],
        control_scenario_fingerprint=fixture.control_scenario_fingerprint,
        matched_world_fingerprint=fixture.matched_world_fingerprint,
        model_policy_fingerprint=fixture.model_policy_fingerprint,
        run_control_fingerprint=fixture.run_control_fingerprint,
        measurement_spec_fingerprint=COORDINATION_MEASUREMENT_SPEC_FINGERPRINT,
    )


def build_composite_assay_scenario_fixture(
    source: CoordinationDecisionFixture,
    *,
    scenario_revision: str,
    matched_world_fingerprint: str,
    model_policy_fingerprint: str,
    run_control_fingerprint: str,
    reviewed_created_refs: Sequence[str] = (
        "external_risk_source",
        "external_risk_message",
        "external_risk_route",
    ),
) -> CompositeAssayScenarioFixture:
    """Derive the assay's reviewed facts from a real coordination fixture."""

    boundary = next(
        (
            item
            for item in source.scenario.analytical_boundaries
            if item.boundary_id == BOUNDARY_ID
        ),
        None,
    )
    if boundary is None:
        raise CompositeAssayContractError(
            "coordination fixture lacks the partnership boundary"
        )
    state = source.scenario.initial_state
    state_refs: list[str] = []
    for values in (
        state.entities,
        state.containers,
        state.places,
        state.spatial_links,
        state.ports,
        state.connections,
        state.mechanisms,
        state.carriers,
        state.representations,
    ):
        state_refs.extend(values)
    configured_refs = list(
        dict.fromkeys(
            [
                *state_refs,
                *(item.boundary_id for item in source.scenario.analytical_boundaries),
            ]
        )
    )
    member_refs: list[str] = list(PERSON_IDS)
    substrate_refs = [
        ref for ref in boundary.member_refs if ref not in set(member_refs)
    ]
    missing_boundary_refs = set(boundary.member_refs) - set(configured_refs)
    if missing_boundary_refs:
        raise CompositeAssayContractError(
            "partnership boundary contains unknown configured references "
            f"{sorted(missing_boundary_refs)!r}"
        )
    return CompositeAssayScenarioFixture(
        scenario_revision=scenario_revision,
        control_scenario_fingerprint=scenario_fingerprint(source.scenario),
        boundary_id=BOUNDARY_ID,
        member_refs=member_refs,
        substrate_refs=substrate_refs,
        configured_refs=configured_refs,
        reviewed_created_refs=list(reviewed_created_refs),
        executable_refs=[
            *member_refs,
            *state.mechanisms,
        ],
        matched_world_fingerprint=matched_world_fingerprint,
        model_policy_fingerprint=model_policy_fingerprint,
        run_control_fingerprint=run_control_fingerprint,
    )


def validate_composite_assay_evidence(
    setup: CompositeAssaySetup,
    run_refs: Sequence[CompositeAssayRunRef],
    readouts: Sequence[CompositeControlReadout],
    evidence_by_run: Mapping[str, CompositeAssayRunEvidence],
) -> CompositeAssayEvidenceSet:
    """Validate retained rows without executing, rerouting, or recoding anything."""

    run_ids = [item.run_id for item in run_refs]
    if len(run_ids) != len(set(run_ids)):
        raise CompositeAssayContractError("assay run IDs must be unique")
    run_by_row = {item.perturbation_id: item for item in run_refs}
    if len(run_by_row) != len(run_refs):
        raise CompositeAssayContractError("each assay row may reference one run")
    if CONTROL_ID not in run_by_row:
        raise CompositeAssayContractError("assay lacks its matched control")
    if set(run_by_row) != set(setup.row_ids):
        missing = set(setup.row_ids) - set(run_by_row)
        raise CompositeAssayContractError(
            f"assay rows do not match setup; missing {sorted(missing)!r}"
        )
    if set(evidence_by_run) != set(run_ids):
        raise CompositeAssayContractError("run evidence does not match run references")
    readout_by_row = {item.perturbation_id: item for item in readouts}
    if len(readout_by_row) != len(readouts):
        raise CompositeAssayContractError("assay readouts must have unique rows")
    valid_rows = {item.perturbation_id for item in run_refs if item.valid}
    if set(readout_by_row) != valid_rows:
        raise CompositeAssayContractError(
            "valid runs require one readout and invalid runs cannot be scored"
        )

    perturbation_by_id = {
        item.perturbation_id: item for item in setup.perturbations
    }
    for row_id, run_ref in run_by_row.items():
        evidence = evidence_by_run[run_ref.run_id]
        if evidence.run_id != run_ref.run_id or evidence.perturbation_id != row_id:
            raise CompositeAssayContractError("run evidence identity mismatch")
        if evidence.scenario_revision != setup.scenario_revision:
            raise CompositeAssayContractError("scenario revision mismatch")
        if (
            evidence.matched_world_fingerprint
            != setup.matched_world_fingerprint
        ):
            raise CompositeAssayContractError("matched-world fingerprint mismatch")
        if evidence.model_policy_fingerprint != setup.model_policy_fingerprint:
            raise CompositeAssayContractError("model policy fingerprint mismatch")
        if evidence.run_control_fingerprint != setup.run_control_fingerprint:
            raise CompositeAssayContractError("run-control fingerprint mismatch")
        fingerprints = {
            run_ref.scenario_fingerprint,
            evidence.evidence_bundle.scenario_fingerprint,
        }
        if evidence.measurement is not None:
            fingerprints.add(evidence.measurement.scenario_fingerprint)
        if len(fingerprints) != 1:
            raise CompositeAssayContractError("scenario fingerprint mismatch")
        if (
            row_id == CONTROL_ID
            and run_ref.scenario_fingerprint
            != setup.control_scenario_fingerprint
        ):
            raise CompositeAssayContractError(
                "control scenario fingerprint does not match setup"
            )
        if run_ref.measurement_spec_version != setup.measurement_spec_version:
            raise CompositeAssayContractError("measurement version mismatch")
        if run_ref.valid and evidence.measurement is None:
            raise CompositeAssayContractError("missing current Slice-21 measurement")
        if evidence.measurement is not None and (
            evidence.measurement.measurement_spec_version
            != setup.measurement_spec_version
            or evidence.measurement.measurement_spec_fingerprint
            != setup.measurement_spec_fingerprint
        ):
            raise CompositeAssayContractError("missing current Slice-21 measurement")
        expected_changed_refs = (
            set()
            if row_id == CONTROL_ID
            else set(perturbation_by_id[row_id].changed_refs)
        )
        applied_changed_refs = set(evidence.applied_changed_refs)
        if run_ref.valid and applied_changed_refs != expected_changed_refs:
            raise CompositeAssayContractError("applied changes do not match the row")
        if not run_ref.valid and not applied_changed_refs <= expected_changed_refs:
            raise CompositeAssayContractError(
                "invalid run claims changes outside its reviewed row"
            )
        scheduled = (
            row_id != CONTROL_ID
            and perturbation_by_id[row_id].application == "scheduled_day_4"
        )
        if not scheduled and evidence.perturbation_application_event_id is not None:
            raise CompositeAssayContractError(
                "initial-condition or control row cannot claim an application event"
            )
        if (
            run_ref.valid
            and scheduled
            and evidence.perturbation_application_event_id is None
        ):
            raise CompositeAssayContractError(
                "perturbation application evidence does not match its schedule"
            )
        retained_event_ids = {
            item.evidence_ref.removeprefix("event:")
            for item in evidence.evidence_bundle.evidence_records
            if item.evidence_ref.startswith("event:")
        }
        if (
            evidence.perturbation_application_event_id is not None
            and evidence.perturbation_application_event_id not in retained_event_ids
        ):
            raise CompositeAssayContractError(
                "perturbation application event is not retained by its source run"
            )
        if not run_ref.valid:
            continue
        if (
            evidence.boundary_activity_ref is None
            or evidence.boundary_activity is None
        ):
            raise CompositeAssayContractError(
                "valid run lacks retained boundary activity"
            )
        _validate_readout(
            setup.capability,
            run_ref,
            readout_by_row[row_id],
            evidence,
        )

    return CompositeAssayEvidenceSet(
        setup=setup,
        run_refs=list(run_refs),
        readouts=list(readouts),
    )


def _validate_readout(
    capability: CompositeCapabilitySpec,
    run_ref: CompositeAssayRunRef,
    readout: CompositeControlReadout,
    evidence: CompositeAssayRunEvidence,
) -> None:
    measurement = evidence.measurement
    activity = evidence.boundary_activity
    boundary_activity_ref = evidence.boundary_activity_ref
    if measurement is None or activity is None or boundary_activity_ref is None:
        raise CompositeAssayContractError("valid run evidence is incomplete")
    if readout.capability_id != capability.capability_id:
        raise CompositeAssayContractError("readout capability mismatch")
    if readout.boundary_id != capability.boundary_id:
        raise CompositeAssayContractError("readout boundary mismatch")
    if readout.perturbation_id != run_ref.perturbation_id:
        raise CompositeAssayContractError("readout row mismatch")
    if readout.source_run_ids != [run_ref.run_id]:
        raise CompositeAssayContractError("readout must cite exactly its source run")
    if readout.boundary_activity_ref != boundary_activity_ref:
        raise CompositeAssayContractError("boundary activity reference mismatch")
    if (
        readout.coordination_measurement_ref
        != measurement.measurement_id
    ):
        raise CompositeAssayContractError("coordination measurement reference mismatch")

    crossing_by_id = {
        item.crossing_id: item for item in activity.crossings
    }
    episode_by_id = {
        item.episode_id: item for item in activity.episodes
    }
    _require_known_ids("input crossing", readout.input_crossing_ids, crossing_by_id)
    _require_known_ids("output crossing", readout.output_crossing_ids, crossing_by_id)
    _require_known_ids(
        "coordination episode", readout.coordination_episode_ids, episode_by_id
    )
    if any(
        crossing_by_id[item].direction != "incoming"
        for item in readout.input_crossing_ids
    ):
        raise CompositeAssayContractError("input crossing has the wrong direction")
    if any(
        crossing_by_id[item].direction != "outgoing"
        for item in readout.output_crossing_ids
    ):
        raise CompositeAssayContractError("output crossing has the wrong direction")

    event_ids = {
        item.evidence_ref.removeprefix("event:")
        for item in evidence.evidence_bundle.evidence_records
        if item.evidence_ref.startswith("event:")
    }
    boundary_event_ids = {
        *(item.event_id for item in activity.crossings),
        *(
            event_id
            for episode in activity.episodes
            for event_id in (
                *episode.trigger_event_ids,
                *episode.internal_event_ids,
                *episode.external_result_event_ids,
            )
        ),
    }
    if boundary_event_ids - event_ids:
        raise CompositeAssayContractError(
            "boundary episode names an event outside its source run"
        )
    boundary_record = next(
        item
        for item in evidence.evidence_bundle.evidence_records
        if item.evidence_ref == boundary_activity_ref
    )
    boundary_record_event_ids = {
        ref.removeprefix("event:")
        for ref in boundary_record.source_refs
        if ref.startswith("event:")
    }
    if boundary_record_event_ids != boundary_event_ids:
        raise CompositeAssayContractError(
            "boundary projection disagrees with its retained evidence record"
        )
    claimed_event_ids = {
        *readout.output_attempt_event_ids,
        *readout.external_result_event_ids,
        readout.terminal_outcome_event_id,
        *(
            event_id
            for pattern in readout.coded_patterns
            for event_id in pattern.source_event_ids
        ),
    }
    if claimed_event_ids - event_ids:
        raise CompositeAssayContractError("readout cites an unknown source event")
    selected_episodes = [
        episode_by_id[item] for item in readout.coordination_episode_ids
    ]
    allowed_external_results = {
        event_id
        for episode in selected_episodes
        for event_id in episode.external_result_event_ids
    }
    if set(readout.external_result_event_ids) - allowed_external_results:
        raise CompositeAssayContractError(
            "external result is not retained by a selected episode"
        )
    selected_outputs = {
        episode.output_crossing_id
        for episode in selected_episodes
        if episode.output_crossing_id is not None
    }
    if set(readout.output_crossing_ids) - selected_outputs:
        raise CompositeAssayContractError(
            "claimed output is not retained by a selected episode"
        )
    completed_count = sum(item.status == "completed" for item in selected_episodes)
    in_progress_count = sum(
        item.status == "in_progress" for item in selected_episodes
    )
    expected_counts = {
        "input_crossing_count": len(readout.input_crossing_ids),
        "output_crossing_count": len(readout.output_crossing_ids),
        "completed_episode_count": completed_count,
        "in_progress_episode_count": in_progress_count,
    }
    if any(
        readout.exact_values[key] != value
        for key, value in expected_counts.items()
    ):
        raise CompositeAssayContractError(
            "readout counts disagree with retained boundary activity"
        )


def _require_known_ids(
    label: str,
    refs: Sequence[str],
    known: Mapping[str, object],
) -> None:
    unknown = set(refs) - set(known)
    if unknown:
        raise CompositeAssayContractError(
            f"readout has unknown {label} IDs {sorted(unknown)!r}"
        )
