"""Four-condition coordination experiment and bounded live-agent probe.

The experiment separates pressure presence, feedback-driven adaptation, and one
concrete authoritative-validation intervention.  Its reference runner remains
provider-free; the live-probe seam replaces only concrete people with native
LLM cognition.  Neither path promotes a synthetic comparison to a real-world
invariant or causal claim.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
from secrets import token_hex
from statistics import mean
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from cybernetic_influence.active_runtime import (
    ActionIntent,
    ActiveProposal,
    ActiveRuntimeResult,
    ActiveStepResult,
    ActiveSystemBinding,
    ActiveSystemInput,
    ActiveSystemSpec,
    ScriptedActiveSystem,
    UpdateScheduleDirective,
)
from cybernetic_influence.analysis.coordination import calculate_exact_values
from cybernetic_influence.analysis.theory_retention import (
    build_reference_theory_analysis,
)
from cybernetic_influence.authoring.compiler import CompiledScenario
from cybernetic_influence.authoring.examples import reviewed_coordination_proposal
from cybernetic_influence.causal_core.engine import (
    ExactMechanismBinding,
    MechanismContext,
)
from cybernetic_influence.causal_core.models import (
    AnalyticalBoundary,
    CarrierState,
    CausalScenario,
    CausalState,
    ConnectionState,
    EffectDraft,
    EntityState,
    FactState,
    FactUpdate,
    FidelityNote,
    MechanismOutcome,
    MechanismSpec,
    ObservationDraft,
    PlacementState,
    PortState,
    RepresentationDraft,
    RepresentationToken,
    representation_digest,
)
from cybernetic_influence.presentation import build_analyst_document
from cybernetic_influence.run_store import RunStore, now_iso
from cybernetic_influence.scenarios.coordination_decision import (
    MINUTES_PER_DAY,
    PARTNERSHIP_BOUNDARY_ID,
    PERSON_IDS,
    PRESSURE_SOURCE_IDS,
    PRESSURE_SOURCE_REPRESENTATION_IDS,
    SOURCE_BOUNDARY_ID,
    CoordinationDecisionFixture,
    CoordinationRuntimeFixture,
    VerificationItem,
    VerificationRequestAction,
    VerificationResponseRecord,
    baseline_coordination_fixture,
    coordination_native_bindings,
    coordination_runtime_fixture,
    coordination_scripted_bindings,
    heterogeneous_pressure_coordination_fixture,
    run_coordination,
)

type CoordinationExperimentCondition = Literal[
    "baseline",
    "fixed_heterogeneous_pressure",
    "adaptive_heterogeneous_pressure",
    "adaptive_pressure_with_stabilization",
]
type LiveCoordinationProbeCondition = Literal[
    "fixed_heterogeneous_pressure",
    "adaptive_heterogeneous_pressure",
    "adaptive_pressure_with_stabilization",
]
type Direction = Literal["increase", "decrease", "no_change", "unclear"]

EXPERIMENT_CONDITIONS: tuple[CoordinationExperimentCondition, ...] = (
    "baseline",
    "fixed_heterogeneous_pressure",
    "adaptive_heterogeneous_pressure",
    "adaptive_pressure_with_stabilization",
)
LIVE_COORDINATION_PROBE_CONDITIONS: tuple[LiveCoordinationProbeCondition, ...] = (
    "fixed_heterogeneous_pressure",
    "adaptive_heterogeneous_pressure",
    "adaptive_pressure_with_stabilization",
)
EXPERIMENT_REPLICATES = 2
EXPERIMENT_RUN_COUNT = len(EXPERIMENT_CONDITIONS) * EXPERIMENT_REPLICATES
EXPERIMENT_ID_PATTERN = r"^coordexp_[0-9a-f]{12}$"

_FORBID = ConfigDict(extra="forbid", strict=True)
_FOLLOWUP_REPRESENTATIONS: dict[str, str] = {
    "technical_pressure_source": "technical_adaptive_followup",
    "policy_pressure_source": "policy_adaptive_followup",
    "local_pressure_source": "local_adaptive_followup",
}
_SOURCE_TARGETS: dict[str, str] = {
    "technical_pressure_source": "technical_validation_lead",
    "policy_pressure_source": "sovereignty_policy_representative",
    "local_pressure_source": "local_public_health_liaison",
}
_SOURCE_OUTPUTS: dict[str, str] = {
    "technical_pressure_source": "technical_source_out",
    "policy_pressure_source": "policy_source_out",
    "local_pressure_source": "local_source_out",
}
_BASE_REPRESENTATIONS: dict[str, str] = dict(
    zip(PRESSURE_SOURCE_IDS, PRESSURE_SOURCE_REPRESENTATION_IDS, strict=True)
)
_CONTRASTS: tuple[
    tuple[str, CoordinationExperimentCondition, CoordinationExperimentCondition],
    ...,
] = (
    ("pressure_presence", "baseline", "fixed_heterogeneous_pressure"),
    (
        "adaptation_effect",
        "fixed_heterogeneous_pressure",
        "adaptive_heterogeneous_pressure",
    ),
    (
        "stabilization_effect",
        "adaptive_heterogeneous_pressure",
        "adaptive_pressure_with_stabilization",
    ),
)
_NUMERIC_METRICS = (
    "verification_requests",
    "risk_register_expansion",
    "unresolved_risk_load",
    "modeled_time_to_terminal",
    "issue_reopening",
    "informal_alignment",
    "disengagement",
)


class _ProducedModel(BaseModel):
    model_config = _FORBID


class CoordinationExperimentConditionSpecV1(_ProducedModel):
    condition: CoordinationExperimentCondition
    pressure_mode: Literal["none", "fixed", "adaptive"]
    authoritative_validation: bool
    changed_refs: list[str]


class CoordinationExperimentSpecV1(_ProducedModel):
    schema_version: Literal[1] = 1
    scenario_id: Literal["coordination_decision_v1"] = "coordination_decision_v1"
    scenario_revision: Literal["coordination_experiment_revision_1"] = (
        "coordination_experiment_revision_1"
    )
    execution: Literal["scripted_reference"] = "scripted_reference"
    replicates_per_condition: Literal[2] = 2
    conditions: list[CoordinationExperimentConditionSpecV1]
    limitations: list[str]

    @model_validator(mode="after")
    def validate_conditions(self) -> "CoordinationExperimentSpecV1":
        if [item.condition for item in self.conditions] != list(EXPERIMENT_CONDITIONS):
            raise ValueError("coordination experiment conditions are incomplete or unordered")
        return self


class CoordinationExperimentRunReadoutV1(_ProducedModel):
    run_id: str = Field(pattern=r"^run_[0-9a-f]{12}$")
    condition: CoordinationExperimentCondition
    replicate: int = Field(ge=1, le=EXPERIMENT_REPLICATES)
    status: Literal["completed"] = "completed"
    terminal_outcome: str
    numeric_metrics: dict[str, float]
    trajectories: dict[str, JsonValue]
    subgroup_source_reliance: list[dict[str, JsonValue]]
    adaptive_followup_event_ids: list[str]
    authoritative_validation_event_ids: list[str]

    @model_validator(mode="after")
    def validate_run_evidence(self) -> "CoordinationExperimentRunReadoutV1":
        if set(self.numeric_metrics) != set(_NUMERIC_METRICS):
            raise ValueError("coordination experiment numeric metrics are incomplete")
        if any(not math.isfinite(value) for value in self.numeric_metrics.values()):
            raise ValueError("coordination experiment numeric metrics must be finite")
        if set(self.trajectories) != {
            "verification_by_meeting",
            "open_risks_by_meeting",
        }:
            raise ValueError("coordination experiment trajectories are incomplete")
        adaptive = self.condition in {
            "adaptive_heterogeneous_pressure",
            "adaptive_pressure_with_stabilization",
        }
        if adaptive != bool(self.adaptive_followup_event_ids):
            raise ValueError("adaptive follow-up evidence disagrees with the condition")
        stabilized = self.condition == "adaptive_pressure_with_stabilization"
        if stabilized != bool(self.authoritative_validation_event_ids):
            raise ValueError(
                "authoritative validation evidence disagrees with the condition"
            )
        return self


class CoordinationExperimentConditionReadoutV1(_ProducedModel):
    condition: CoordinationExperimentCondition
    run_ids: list[str]
    terminal_outcomes: list[str]
    metric_means: dict[str, float]

    @model_validator(mode="after")
    def validate_summary(self) -> "CoordinationExperimentConditionReadoutV1":
        if (
            len(self.run_ids) != EXPERIMENT_REPLICATES
            or len(set(self.run_ids)) != EXPERIMENT_REPLICATES
            or len(self.terminal_outcomes) != EXPERIMENT_REPLICATES
        ):
            raise ValueError("coordination condition summary is incomplete")
        if set(self.metric_means) != set(_NUMERIC_METRICS):
            raise ValueError("coordination condition metric means are incomplete")
        return self


class CoordinationExperimentMetricContrastV1(_ProducedModel):
    metric_id: str
    reference_mean: float
    treatment_mean: float
    direction: Direction
    difference: float


class CoordinationExperimentContrastV1(_ProducedModel):
    contrast_id: Literal[
        "pressure_presence",
        "adaptation_effect",
        "stabilization_effect",
    ]
    reference_condition: CoordinationExperimentCondition
    treatment_condition: CoordinationExperimentCondition
    metrics: list[CoordinationExperimentMetricContrastV1]


class CoordinationExperimentReadoutV1(_ProducedModel):
    schema_version: Literal[1] = 1
    experiment_id: str = Field(pattern=EXPERIMENT_ID_PATTERN)
    created_at: str
    status: Literal["completed"] = "completed"
    provider_calls: Literal[0] = 0
    specification: CoordinationExperimentSpecV1
    specification_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    runs: list[CoordinationExperimentRunReadoutV1]
    conditions: list[CoordinationExperimentConditionReadoutV1]
    contrasts: list[CoordinationExperimentContrastV1]
    limitations: list[str]

    @model_validator(mode="after")
    def validate_complete_readout(self) -> "CoordinationExperimentReadoutV1":
        if self.specification_digest != _digest(self.specification.model_dump(mode="json")):
            raise ValueError("coordination experiment specification digest mismatch")
        slots = [(item.condition, item.replicate) for item in self.runs]
        expected = [
            (condition, replicate)
            for condition in EXPERIMENT_CONDITIONS
            for replicate in range(1, EXPERIMENT_REPLICATES + 1)
        ]
        if slots != expected or len({item.run_id for item in self.runs}) != len(expected):
            raise ValueError("coordination experiment run matrix is incomplete")
        if [item.condition for item in self.conditions] != list(EXPERIMENT_CONDITIONS):
            raise ValueError("coordination experiment condition summaries are incomplete")
        if [item.contrast_id for item in self.contrasts] != [item[0] for item in _CONTRASTS]:
            raise ValueError("coordination experiment contrasts are incomplete")
        summaries = {item.condition: item for item in self.conditions}
        for condition in EXPERIMENT_CONDITIONS:
            selected = [item for item in self.runs if item.condition == condition]
            summary = summaries[condition]
            if summary.run_ids != [item.run_id for item in selected]:
                raise ValueError("coordination condition run identities disagree")
            if summary.terminal_outcomes != [item.terminal_outcome for item in selected]:
                raise ValueError("coordination condition outcomes disagree")
            expected_means = {
                metric: mean(item.numeric_metrics[metric] for item in selected)
                for metric in _NUMERIC_METRICS
            }
            if summary.metric_means != expected_means:
                raise ValueError("coordination condition metric means disagree")
        for contrast, expected_contrast in zip(
            self.contrasts, _CONTRASTS, strict=True
        ):
            _, reference, treatment = expected_contrast
            if (
                contrast.reference_condition != reference
                or contrast.treatment_condition != treatment
                or [item.metric_id for item in contrast.metrics]
                != list(_NUMERIC_METRICS)
            ):
                raise ValueError("coordination experiment contrast contract disagrees")
            for metric in contrast.metrics:
                reference_mean = summaries[reference].metric_means[metric.metric_id]
                treatment_mean = summaries[treatment].metric_means[metric.metric_id]
                difference = treatment_mean - reference_mean
                direction: Direction = (
                    "increase"
                    if difference > 0
                    else "decrease" if difference < 0 else "no_change"
                )
                if (
                    metric.reference_mean != reference_mean
                    or metric.treatment_mean != treatment_mean
                    or metric.difference != difference
                    or metric.direction != direction
                ):
                    raise ValueError("coordination experiment contrast values disagree")
        return self


@dataclass(frozen=True)
class CoordinationExperimentRuntimeFixture:
    condition: CoordinationExperimentCondition
    runtime: CoordinationRuntimeFixture


@dataclass(frozen=True)
class CoordinationExperimentExecution:
    experiment_id: str
    readout: CoordinationExperimentReadoutV1
    retained_run_ids: tuple[str, ...]


def coordination_live_probe_fixture(
    condition: LiveCoordinationProbeCondition,
    *,
    model: str,
    reasoning_effort: str | None,
) -> CoordinationExperimentRuntimeFixture:
    """Bind real cognition into one existing experiment condition.

    The experiment-owned pressure and validation mechanisms stay unchanged;
    only the five concrete people move from scripted policies to the selected
    model.  This preserves the isolated condition contrast while exposing it
    to authentic participant behavior.
    """

    reference = coordination_experiment_fixture(condition)
    live = coordination_runtime_fixture(
        reference.runtime.contract,
        model=model,
        reasoning_effort=reasoning_effort,
    )
    live_people: dict[str, ActiveSystemSpec] = {
        spec.active_system_id: spec
        for spec in live.active_specs
        if spec.active_system_id in PERSON_IDS
    }
    active_specs = tuple(
        live_people.get(spec.active_system_id, spec)
        for spec in reference.runtime.active_specs
    )
    return CoordinationExperimentRuntimeFixture(
        condition=condition,
        runtime=CoordinationRuntimeFixture(
            contract=reference.runtime.contract,
            exact_bindings=reference.runtime.exact_bindings,
            active_specs=active_specs,
        ),
    )


def coordination_live_probe_bindings(
    fixture: CoordinationExperimentRuntimeFixture,
    *,
    trace_id_prefix: str,
    model: str,
    reasoning_effort: str | None,
) -> dict[str, ActiveSystemBinding]:
    """Use model-driven people with the experiment's exact source policies."""

    bindings = coordination_experiment_bindings(fixture)
    native = coordination_native_bindings(
        fixture.runtime,
        trace_id_prefix=trace_id_prefix,
        model=model,
        reasoning_effort=reasoning_effort,
    )
    for person_id in PERSON_IDS:
        bindings[person_id] = native[person_id]
    return bindings


def coordination_experiment_spec() -> CoordinationExperimentSpecV1:
    """Return the frozen first four-condition provider-free contract."""

    return CoordinationExperimentSpecV1(
        conditions=[
            CoordinationExperimentConditionSpecV1(
                condition="baseline",
                pressure_mode="none",
                authoritative_validation=False,
                changed_refs=[],
            ),
            CoordinationExperimentConditionSpecV1(
                condition="fixed_heterogeneous_pressure",
                pressure_mode="fixed",
                authoritative_validation=False,
                changed_refs=["coordination_condition.pressure_sources_enabled"],
            ),
            CoordinationExperimentConditionSpecV1(
                condition="adaptive_heterogeneous_pressure",
                pressure_mode="adaptive",
                authoritative_validation=False,
                changed_refs=[
                    "pressure_source_feedback_routes",
                    "pressure_source_feedback_policies",
                    "adaptive_followup_representations",
                ],
            ),
            CoordinationExperimentConditionSpecV1(
                condition="adaptive_pressure_with_stabilization",
                pressure_mode="adaptive",
                authoritative_validation=True,
                changed_refs=[
                    "pressure_source_feedback_routes",
                    "pressure_source_feedback_policies",
                    "adaptive_followup_representations",
                    "authoritative_validation_record.available",
                ],
            ),
        ],
        limitations=[
            "The reference policies are synthetic and make no real-world behavioral prediction.",
            "Two deterministic replicates exercise retention and comparison; they do not estimate population uncertainty.",
            "Candidate directions are not invariants, causal effects, or hostile attribution.",
        ],
    )


def run_scripted_coordination_experiment(
    store_root: Path,
) -> CoordinationExperimentExecution:
    """Execute, compare, and retain eight zero-provider run documents."""

    store = RunStore(store_root)
    existing_ids = {
        str(metadata.get("experiment_id"))
        for summary in store.list_runs()[0]
        if isinstance((metadata := summary.get("coordination_experiment")), Mapping)
    }
    experiment_id = f"coordexp_{token_hex(6)}"
    while experiment_id in existing_ids:
        experiment_id = f"coordexp_{token_hex(6)}"
    created_at = now_iso()
    specification = coordination_experiment_spec()
    run_readouts: list[CoordinationExperimentRunReadoutV1] = []
    documents: list[dict[str, object]] = []
    reserved_run_ids: set[str] = set()

    for condition in EXPERIMENT_CONDITIONS:
        fixture = coordination_experiment_fixture(condition)
        for replicate in range(1, EXPERIMENT_REPLICATES + 1):
            run_id = _new_run_id(store_root, reserved_run_ids)
            reserved_run_ids.add(run_id)
            result = run_coordination(
                fixture.runtime,
                coordination_experiment_bindings(fixture),
                run_id=run_id,
            )
            if result.model_calls != 0 or result.total_observed_cost != 0.0:
                raise RuntimeError("scripted coordination experiment used a provider")
            exact_values = calculate_exact_values(result)
            run_readout = _run_readout(
                condition,
                replicate,
                result,
                cast(Mapping[str, JsonValue], exact_values),
            )
            theory = build_reference_theory_analysis(_compiled(fixture), result)
            document = _retained_document(
                fixture,
                replicate,
                result,
                run_readout,
                theory,
                experiment_id=experiment_id,
                created_at=created_at,
            )
            run_readouts.append(run_readout)
            documents.append(document)

    readout = _experiment_readout(
        experiment_id,
        created_at,
        specification,
        run_readouts,
    )
    retained_ids: list[str] = []
    for document in documents:
        document["coordination_experiment_readout"] = readout.model_dump(mode="json")
        store.save(document)
        retained_ids.append(cast(str, document["run_id"]))
    return CoordinationExperimentExecution(
        experiment_id=experiment_id,
        readout=readout,
        retained_run_ids=tuple(retained_ids),
    )


def coordination_experiment_fixture(
    condition: CoordinationExperimentCondition,
) -> CoordinationExperimentRuntimeFixture:
    """Compile one row with shared feedback and validation infrastructure."""

    if condition == "baseline":
        base = baseline_coordination_fixture()
    else:
        base = heterogeneous_pressure_coordination_fixture()
    validation_enabled = condition == "adaptive_pressure_with_stabilization"
    contract = _instrument_contract(base, validation_enabled=validation_enabled)
    original_runtime = coordination_runtime_fixture(contract)
    adaptive = condition in {
        "adaptive_heterogeneous_pressure",
        "adaptive_pressure_with_stabilization",
    }
    active_specs = tuple(
        _adaptive_source_spec(item) if adaptive and item.active_system_id in PRESSURE_SOURCE_IDS else item
        for item in original_runtime.active_specs
    )
    exact_bindings = dict(original_runtime.exact_bindings)
    for source_id in PRESSURE_SOURCE_IDS:
        mechanism_id = f"{source_id}_feedback_delivery"
        exact_bindings[mechanism_id] = _exact_binding(
            mechanism_id,
            _exact_feedback_delivery,
        )
    original_verification = exact_bindings["verification_recorder"].handler
    exact_bindings["verification_recorder"] = _exact_binding(
        "verification_recorder",
        _authoritative_verification_handler(original_verification),
    )
    runtime = CoordinationRuntimeFixture(
        contract=contract,
        exact_bindings=exact_bindings,
        active_specs=active_specs,
    )
    return CoordinationExperimentRuntimeFixture(condition=condition, runtime=runtime)


def coordination_experiment_bindings(
    fixture: CoordinationExperimentRuntimeFixture,
) -> dict[str, ActiveSystemBinding]:
    """Bind adaptive source policies only in the two adaptive conditions."""

    bindings = coordination_scripted_bindings(fixture.runtime)
    if fixture.condition not in {
        "adaptive_heterogeneous_pressure",
        "adaptive_pressure_with_stabilization",
    }:
        return bindings
    for source_id in PRESSURE_SOURCE_IDS:
        implementation_id = f"scripted_adaptive_{source_id}_v1"
        bindings[source_id] = ActiveSystemBinding(
            implementation_id=implementation_id,
            implementation=ScriptedActiveSystem(
                implementation_id=implementation_id,
                controller=_adaptive_source_controller(source_id, implementation_id),
            ),
        )
    return bindings


def _instrument_contract(
    base: CoordinationDecisionFixture,
    *,
    validation_enabled: bool,
) -> CoordinationDecisionFixture:
    state = base.scenario.initial_state
    entities = dict(state.entities)
    placements = dict(state.placements)
    ports = dict(state.ports)
    connections = dict(state.connections)
    mechanisms = dict(state.mechanisms)
    carriers = dict(state.carriers)
    representations = dict(state.representations)

    entities["authoritative_validation_record"] = EntityState(
        entity_id="authoritative_validation_record",
        entity_kind="validation_record",
        description="Concrete reviewed source for the first stabilization intervention.",
        attributes={"available": FactState(value=validation_enabled)},
    )
    placements["authoritative_validation_record"] = PlacementState(
        entity_id="authoritative_validation_record",
        place_id="partnership_hub",
    )
    carriers["authoritative_validation_carrier"] = CarrierState(
        carrier_id="authoritative_validation_carrier",
        owner_ref="authoritative_validation_record",
        medium="reviewed_validation_record",
        locator="partnership validation register",
    )
    validation_content = _json(
        {
            "document_kind": "authoritative_validation",
            "topic": "independent_calibration",
            "finding": "bounded_support",
            "scope": "reduced",
        }
    )
    representations["authoritative_validation_evidence"] = RepresentationToken(
        representation_id="authoritative_validation_evidence",
        carrier_id="authoritative_validation_carrier",
        carrier_revision=0,
        encoding="application/vnd.cybernetic.authoritative-validation+json",
        content=validation_content,
        content_hash=representation_digest(validation_content),
        actual_source_ref="authoritative_validation_record",
    )

    verification = mechanisms["verification_recorder"]
    mechanisms["verification_recorder"] = verification.model_copy(
        update={
            "read_fact_ids": [
                *verification.read_fact_ids,
                "authoritative_validation_record.available",
            ],
            "read_representation_ids": [
                *verification.read_representation_ids,
                "authoritative_validation_evidence",
            ],
        }
    )

    for source_id in PRESSURE_SOURCE_IDS:
        feedback_port_id = f"{source_id}_feedback_in"
        mechanism_id = f"{source_id}_feedback_delivery"
        connection_id = f"{source_id}_feedback_route"
        ports[feedback_port_id] = PortState(
            port_id=feedback_port_id,
            owner_ref=mechanism_id,
            direction="input",
            effect_type="meeting_snapshot",
            description=f"Reviewed meeting feedback input for {source_id}.",
        )
        connections[connection_id] = ConnectionState(
            connection_id=connection_id,
            source_port_id="meeting_snapshot_out",
            target_port_id=feedback_port_id,
            delay=1,
            description=f"Positive-duration public meeting feedback route to {source_id}.",
        )
        mechanisms[mechanism_id] = MechanismSpec(
            mechanism_id=mechanism_id,
            mechanism_kind="exact_transition",
            implementation_id=f"{mechanism_id}_v1",
            description=f"Deliver the public meeting snapshot to {source_id}.",
            input_port_ids=[feedback_port_id],
            observation_target_ids=[source_id],
            substrate_refs=["coordination_platform"],
            invariant_ids=[f"{mechanism_id}_contract"],
            fidelity=_fidelity("Synthetic public-feedback delivery."),
        )
        followup_id = _FOLLOWUP_REPRESENTATIONS[source_id]
        carrier_id = f"{followup_id}_carrier"
        carriers[carrier_id] = CarrierState(
            carrier_id=carrier_id,
            owner_ref=source_id,
            medium="adaptive_source_message_record",
            locator=f"{source_id} reviewed follow-up workspace",
        )
        followup_content = _json(
            {
                "document_kind": "source_message",
                "topic": "adaptive_follow_up",
                "claim": (
                    f"After observing {_SOURCE_TARGETS[source_id]}'s updated "
                    "commitment, the source introduced a narrower unresolved concern."
                ),
            }
        )
        representations[followup_id] = RepresentationToken(
            representation_id=followup_id,
            carrier_id=carrier_id,
            carrier_revision=0,
            encoding="application/vnd.cybernetic.source-message+json",
            content=followup_content,
            content_hash=representation_digest(followup_content),
            actual_source_ref=source_id,
            parent_representation_ids=[_BASE_REPRESENTATIONS[source_id]],
        )

    new_state = CausalState.model_validate(
        {
            **state.model_dump(mode="json"),
            "entities": {key: value.model_dump(mode="json") for key, value in entities.items()},
            "placements": {key: value.model_dump(mode="json") for key, value in placements.items()},
            "ports": {key: value.model_dump(mode="json") for key, value in ports.items()},
            "connections": {key: value.model_dump(mode="json") for key, value in connections.items()},
            "mechanisms": {key: value.model_dump(mode="json") for key, value in mechanisms.items()},
            "carriers": {key: value.model_dump(mode="json") for key, value in carriers.items()},
            "representations": {key: value.model_dump(mode="json") for key, value in representations.items()},
        }
    )
    boundaries: list[AnalyticalBoundary] = []
    for boundary in base.scenario.analytical_boundaries:
        additions: list[str] = []
        if boundary.boundary_id == PARTNERSHIP_BOUNDARY_ID:
            additions = [
                "authoritative_validation_record",
                "authoritative_validation_carrier",
                "authoritative_validation_evidence",
            ]
        elif boundary.boundary_id == SOURCE_BOUNDARY_ID:
            additions = [
                item
                for source_id in PRESSURE_SOURCE_IDS
                for item in (
                    f"{source_id}_feedback_in",
                    f"{source_id}_feedback_delivery",
                    f"{_FOLLOWUP_REPRESENTATIONS[source_id]}_carrier",
                    _FOLLOWUP_REPRESENTATIONS[source_id],
                )
            ]
        boundaries.append(
            boundary.model_copy(update={"member_refs": [*boundary.member_refs, *additions]})
        )
    scenario = CausalScenario.model_validate(
        {
            **base.scenario.model_dump(mode="json"),
            "initial_state": new_state.model_dump(mode="json"),
            "analytical_boundaries": [item.model_dump(mode="json") for item in boundaries],
        }
    )
    return CoordinationDecisionFixture.model_validate(
        {
            **base.model_dump(mode="json"),
            "scenario": scenario.model_dump(mode="json"),
        }
    )


def _adaptive_source_spec(spec: ActiveSystemSpec) -> ActiveSystemSpec:
    source_id = spec.active_system_id
    followup_id = _FOLLOWUP_REPRESENTATIONS[source_id]
    output_id = _SOURCE_OUTPUTS[source_id]
    implementation_id = f"scripted_adaptive_{source_id}_v1"
    return spec.model_copy(
        update={
            "implementation_id": implementation_id,
            "description": f"Feedback-responsive scripted source process {source_id}.",
            "observation_port_ids": [f"{source_id}_feedback_in"],
            "initial_representation_ids": [
                *spec.initial_representation_ids,
                followup_id,
            ],
            "output_port_initial_representation_ids": {
                output_id: [_BASE_REPRESENTATIONS[source_id], followup_id]
            },
            "initial_private_state": {
                "emissions": 0,
                "latest_feedback_meeting": -1,
                "latest_target_commitment": "unknown",
            },
        }
    )


def _adaptive_source_controller(
    source_id: str,
    implementation_id: str,
) -> Callable[[ActiveSystemInput], ActiveStepResult]:
    def controller(item: ActiveSystemInput) -> ActiveStepResult:
        state = dict(item.private_state)
        emissions = state.get("emissions")
        if isinstance(emissions, bool) or not isinstance(emissions, int):
            raise ValueError("adaptive source emission state is invalid")
        latest_feedback_meeting = state.get("latest_feedback_meeting")
        if (
            isinstance(latest_feedback_meeting, bool)
            or not isinstance(latest_feedback_meeting, int)
        ):
            raise ValueError("adaptive source feedback state is invalid")
        for observation in item.observations:
            try:
                document = json.loads(observation.apparent_content)
            except json.JSONDecodeError as error:
                raise ValueError("adaptive source feedback is not valid JSON") from error
            if (
                not isinstance(document, dict)
                or document.get("document_kind") != "meeting_snapshot"
            ):
                raise ValueError("adaptive source feedback is not a meeting snapshot")
            meeting_index = document.get("meeting_index")
            commitments = document.get("commitments")
            if (
                isinstance(meeting_index, bool)
                or not isinstance(meeting_index, int)
                or not isinstance(commitments, list)
            ):
                raise ValueError("adaptive source meeting feedback is malformed")
            target = _SOURCE_TARGETS[source_id]
            matched = next(
                (
                    entry.get("commitment")
                    for entry in commitments
                    if isinstance(entry, dict) and entry.get("person_id") == target
                ),
                None,
            )
            if not isinstance(matched, str):
                raise ValueError("adaptive source target commitment is missing")
            state["latest_feedback_meeting"] = meeting_index
            state["latest_target_commitment"] = matched

        due_time = MINUTES_PER_DAY if emissions == 0 else 2 * MINUTES_PER_DAY
        if emissions >= 2:
            return _source_step(item, implementation_id, state, [], None)
        if item.logical_time < due_time:
            return _source_step(item, implementation_id, state, [], due_time)

        representation_id = _BASE_REPRESENTATIONS[source_id]
        adapted = False
        if emissions == 1 and latest_feedback_meeting >= 1:
            representation_id = _FOLLOWUP_REPRESENTATIONS[source_id]
            adapted = True
        state["emissions"] = emissions + 1
        action = ActionIntent(
            output_port_id=_SOURCE_OUTPUTS[source_id],
            representation_id=representation_id,
            payload={},
            public_summary=(
                f"{source_id} adapted its follow-up after observed meeting feedback."
                if adapted
                else f"{source_id} emitted its retained initial message."
            ),
        )
        next_time = 2 * MINUTES_PER_DAY if emissions == 0 else None
        return _source_step(item, implementation_id, state, [action], next_time)

    return controller


def _source_step(
    item: ActiveSystemInput,
    implementation_id: str,
    state: Mapping[str, JsonValue],
    actions: list[ActionIntent],
    next_time: int | None,
) -> ActiveStepResult:
    directive = (
        UpdateScheduleDirective(mode="dormant")
        if next_time is None
        else UpdateScheduleDirective(mode="schedule", next_update_at=next_time)
    )
    return ActiveStepResult(
        proposal=ActiveProposal(
            active_system_id=item.active_system_id,
            implementation_id=implementation_id,
            private_state=dict(state),
            actions=actions,
            update_schedule=directive,
        )
    )


def _exact_feedback_delivery(context: MechanismContext) -> MechanismOutcome:
    if context.effect.payload.get("document_kind") != "meeting_snapshot":
        raise ValueError("adaptive feedback requires a meeting snapshot")
    source_id = context.mechanism.mechanism_id.removesuffix("_feedback_delivery")
    if source_id not in PRESSURE_SOURCE_IDS:
        raise ValueError("adaptive feedback targets an unknown source")
    return MechanismOutcome(
        outcome_code="source_feedback_delivered",
        observations=[
            ObservationDraft(
                target_entity_id=source_id,
                via_port_id=context.target_port.port_id,
                apparent_content=_json(context.effect.payload),
                apparent_source_ref="meeting_scheduler",
            )
        ],
    )


def _authoritative_verification_handler(
    original: Callable[[MechanismContext], MechanismOutcome],
) -> Callable[[MechanismContext], MechanismOutcome]:
    def handler(context: MechanismContext) -> MechanismOutcome:
        available = context.read("authoritative_validation_record.available")
        if not isinstance(available, bool):
            raise TypeError("authoritative validation availability must be boolean")
        if not available:
            return original(context)
        request = VerificationRequestAction.model_validate(context.effect.payload)
        existing_value = context.read("verification_register.items")
        if not isinstance(existing_value, list) or any(
            not isinstance(item, dict) for item in existing_value
        ):
            raise TypeError("verification register must be a list of objects")
        existing = cast(list[dict[str, JsonValue]], existing_value)
        if any(item.get("verification_id") == request.verification_id for item in existing):
            return MechanismOutcome(outcome_code="verification_request_denied_duplicate")
        response = VerificationResponseRecord(
            result="bounded_support",
            explanation=(
                "The retained authoritative validation supported a reduced, bounded deployment."
            ),
        )
        response_id = "independent_calibration_response"
        parents = ["authoritative_validation_evidence"]
        if context.representation is not None:
            parents.append(context.representation.representation_id)
        item = VerificationItem(
            verification_id=request.verification_id,
            topic=request.topic,
            requested_by=request.requested_by,
            status="answered",
            response_representation_id=response_id,
        )
        return MechanismOutcome(
            outcome_code="verification_answered_authoritative",
            updates=[
                FactUpdate(
                    fact_id="verification_register.items",
                    value=[*existing, item.model_dump(mode="json")],
                )
            ],
            representations=[
                RepresentationDraft(
                    representation_id=response_id,
                    carrier_id="verification_response_carrier",
                    encoding="application/vnd.cybernetic.verification-response+json",
                    content=response.model_dump_json(),
                    actual_source_ref="authoritative_validation_record",
                    parent_representation_ids=parents,
                )
            ],
            effects=[
                EffectDraft(
                    output_port_id="verification_response_out",
                    effect_type="verification_response",
                    representation_id=response_id,
                    payload={},
                )
            ],
        )

    return handler


def _run_readout(
    condition: CoordinationExperimentCondition,
    replicate: int,
    result: ActiveRuntimeResult,
    exact_values: Mapping[str, JsonValue],
) -> CoordinationExperimentRunReadoutV1:
    numeric = {
        metric: _numeric_metric(metric, exact_values)
        for metric in _NUMERIC_METRICS
    }
    reliance = _object(exact_values, "source_reliance_topology").get("edges", [])
    events = result.core_result.events
    followups = {
        event.event_id
        for event in events
        if event.representation_id in set(_FOLLOWUP_REPRESENTATIONS.values())
    }
    validations = {
        event.event_id
        for event in events
        if event.details.get("outcome_code") == "verification_answered_authoritative"
    }
    terminal = exact_values["final_deployment_status"]
    if not isinstance(terminal, str):
        raise TypeError("terminal deployment status must be a string")
    return CoordinationExperimentRunReadoutV1(
        run_id=result.run_id,
        condition=condition,
        replicate=replicate,
        terminal_outcome=terminal,
        numeric_metrics=numeric,
        trajectories={
            "verification_by_meeting": _object(
                exact_values, "verification_requests"
            ).get("by_meeting", []),
            "open_risks_by_meeting": _object(
                exact_values, "unresolved_risk_load"
            ).get("at_meetings", []),
        },
        subgroup_source_reliance=(
            cast(list[dict[str, JsonValue]], reliance)
            if isinstance(reliance, list)
            else []
        ),
        adaptive_followup_event_ids=sorted(followups),
        authoritative_validation_event_ids=sorted(validations),
    )


def _experiment_readout(
    experiment_id: str,
    created_at: str,
    specification: CoordinationExperimentSpecV1,
    runs: list[CoordinationExperimentRunReadoutV1],
) -> CoordinationExperimentReadoutV1:
    summaries: list[CoordinationExperimentConditionReadoutV1] = []
    for condition in EXPERIMENT_CONDITIONS:
        selected = [item for item in runs if item.condition == condition]
        summaries.append(
            CoordinationExperimentConditionReadoutV1(
                condition=condition,
                run_ids=[item.run_id for item in selected],
                terminal_outcomes=[item.terminal_outcome for item in selected],
                metric_means={
                    metric: mean(item.numeric_metrics[metric] for item in selected)
                    for metric in _NUMERIC_METRICS
                },
            )
        )
    by_condition = {item.condition: item for item in summaries}
    contrasts: list[CoordinationExperimentContrastV1] = []
    for contrast_id, reference, treatment in _CONTRASTS:
        metrics: list[CoordinationExperimentMetricContrastV1] = []
        for metric in _NUMERIC_METRICS:
            reference_mean = by_condition[reference].metric_means[metric]
            treatment_mean = by_condition[treatment].metric_means[metric]
            difference = treatment_mean - reference_mean
            metrics.append(
                CoordinationExperimentMetricContrastV1(
                    metric_id=metric,
                    reference_mean=reference_mean,
                    treatment_mean=treatment_mean,
                    direction=(
                        "increase"
                        if difference > 0
                        else "decrease" if difference < 0 else "no_change"
                    ),
                    difference=difference,
                )
            )
        contrasts.append(
            CoordinationExperimentContrastV1(
                contrast_id=cast(
                    Literal[
                        "pressure_presence",
                        "adaptation_effect",
                        "stabilization_effect",
                    ],
                    contrast_id,
                ),
                reference_condition=reference,
                treatment_condition=treatment,
                metrics=metrics,
            )
        )
    return CoordinationExperimentReadoutV1(
        experiment_id=experiment_id,
        created_at=created_at,
        specification=specification,
        specification_digest=_digest(specification.model_dump(mode="json")),
        runs=runs,
        conditions=summaries,
        contrasts=contrasts,
        limitations=[
            "Directions describe only this retained synthetic batch.",
            "Deterministic repetitions prove lifecycle consistency, not empirical uncertainty.",
            "Slower coordination can represent rational caution; outcome constraints remain visible.",
        ],
    )


def _retained_document(
    fixture: CoordinationExperimentRuntimeFixture,
    replicate: int,
    result: ActiveRuntimeResult,
    run_readout: CoordinationExperimentRunReadoutV1,
    theory: Mapping[str, object],
    *,
    experiment_id: str,
    created_at: str,
) -> dict[str, object]:
    document = build_analyst_document(
        initial_state=fixture.runtime.scenario.initial_state,
        analytical_boundaries=fixture.runtime.scenario.analytical_boundaries,
        result=result,
        scenario="coordination_experiment",
        profile="four condition scripted reference",
        arm_id=fixture.condition,
        execution="reference",
        created_at=created_at,
        outcome={
            "terminal_status": run_readout.terminal_outcome,
            "replicate": replicate,
        },
        headline=f"Coordination experiment: {fixture.condition.replace('_', ' ')}",
        summary=(
            f"Replicate {replicate} ended with {run_readout.terminal_outcome}; "
            "the result remains a synthetic candidate observation."
        ),
        include_boundary_activity=True,
    )
    document["theory_analysis"] = dict(theory)
    document["coordination_experiment_run_readout"] = run_readout.model_dump(
        mode="json"
    )
    document["coordination_experiment"] = {
        "schema_version": 1,
        "experiment_id": experiment_id,
        "condition": fixture.condition,
        "replicate": replicate,
        "row_count": EXPERIMENT_RUN_COUNT,
        "provider_calls": 0,
    }
    return document


def _compiled(fixture: CoordinationExperimentRuntimeFixture) -> CompiledScenario:
    proposal = reviewed_coordination_proposal()
    internal_condition = (
        "baseline" if fixture.condition == "baseline" else "heterogeneous_pressure"
    )
    workflow = proposal.workflow.model_copy(
        update={"condition": internal_condition, "stabilizing_resources": []}
    )
    proposal = proposal.model_copy(update={"workflow": workflow})
    return CompiledScenario(
        proposal=proposal,
        proposal_digest=_digest(proposal.model_dump(mode="json")),
        fixture=fixture.runtime,
    )


def _numeric_metric(metric: str, exact_values: Mapping[str, JsonValue]) -> float:
    paths: dict[str, tuple[str, ...]] = {
        "verification_requests": ("total",),
        "risk_register_expansion": ("distinct_risks",),
        "unresolved_risk_load": ("final_open_count",),
        "modeled_time_to_terminal": ("scenario_minutes",),
        "issue_reopening": ("count",),
        "informal_alignment": ("message_count",),
        "disengagement": ("count",),
    }
    value: object = exact_values[metric]
    for key in paths[metric]:
        if not isinstance(value, Mapping):
            raise TypeError(f"metric {metric!r} is not an object")
        value = value.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"metric {metric!r} is not numeric")
    return float(value)


def _object(values: Mapping[str, JsonValue], key: str) -> dict[str, JsonValue]:
    value = values[key]
    if not isinstance(value, dict):
        raise TypeError(f"exact measure {key!r} is not an object")
    return value


def _exact_binding(
    mechanism_id: str,
    handler: Callable[[MechanismContext], MechanismOutcome],
) -> ExactMechanismBinding:
    invariant_id = f"{mechanism_id}_contract"

    def checker(context: MechanismContext, outcome: MechanismOutcome) -> bool:
        expected = handler(context)
        return expected.model_dump(mode="json") == outcome.model_dump(mode="json")

    return ExactMechanismBinding(
        implementation_id=f"{mechanism_id}_v1",
        handler=handler,
        invariant_checkers={invariant_id: checker},
    )


def _fidelity(abstraction: str) -> FidelityNote:
    return FidelityNote(
        abstraction=abstraction,
        assumptions=["The reviewed transition is stipulated for this synthetic PoC."],
        known_omissions=["Real institutions, platforms, timing, and behavior."],
        validation_basis=["Scenario-local contracts and both-sign tests."],
    )


def _new_run_id(root: Path, reserved: set[str]) -> str:
    run_id = f"run_{token_hex(6)}"
    while run_id in reserved or (root / f"{run_id}.json").exists():
        run_id = f"run_{token_hex(6)}"
    return run_id


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: object) -> str:
    return sha256(_json(value).encode()).hexdigest()
