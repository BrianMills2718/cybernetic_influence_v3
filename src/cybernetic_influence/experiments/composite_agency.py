"""Exact five-row perturbation instrumentation for the coordination scenario.

The experiment changes concrete people, records, mechanisms, representations,
and routes. Analytical boundaries remain execution-inert and no provider is
ever bound by this module.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from secrets import token_hex
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, JsonValue

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
from cybernetic_influence.analysis.composite_agency import (
    BOUNDARY_ID,
    CONTROL_ID,
    CompositeAssayRunEvidence,
    CompositeAssayRunRef,
    CompositeAssaySetup,
    CompositeCapabilitySpec,
    CompositeControlReadout,
    CompositePatternId,
    CompositePatternEvidence,
    PerturbationSpec,
    build_composite_assay_scenario_fixture,
    compile_composite_assay_setup,
    reviewed_perturbation_specs,
    validate_composite_assay_evidence,
)
from cybernetic_influence.analysis.coordination import calculate_exact_values
from cybernetic_influence.analysis.theory_analysis import (
    FrameworkReadoutConsumerV1,
    RunEvidenceBundleConsumerV1,
)
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
    CausalEvent,
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
    RepresentationToken,
    representation_digest,
)
from cybernetic_influence.presentation import (
    BoundaryActivityProjection,
    build_analyst_document,
)
from cybernetic_influence.run_store import RunStore, now_iso
from cybernetic_influence.scenarios.coordination_decision import (
    DECISION_DEADLINE_TIME,
    MINUTES_PER_DAY,
    PARTNERSHIP_BOUNDARY_ID,
    PERSON_IDS,
    SOURCE_BOUNDARY_ID,
    CoordinationDecisionFixture,
    CoordinationRuntimeFixture,
    baseline_coordination_fixture,
    coordination_runtime_fixture,
    coordination_scripted_bindings,
    run_coordination,
)

PerturbationRowId = Literal[
    "matched_control",
    "member_replacement",
    "route_interruption",
    "feedback_interruption",
    "external_risk",
]

PERTURBATION_APPLICATION_TIME = 4 * MINUTES_PER_DAY
VERIFICATION_FEEDBACK_DELAY = 2 * MINUTES_PER_DAY
REPLACEMENT_PERSON_ID = "technical_validation_lead_replacement"

_COMMON_TECHNICAL_IMPLEMENTATION = "scripted_composite_technical_lead_v1"
_CONTROLLER_IMPLEMENTATION = "scripted_composite_perturbation_controller_v1"
_RISK_SOURCE_IMPLEMENTATION = "scripted_composite_external_risk_source_v1"

_FORBID = ConfigDict(extra="forbid", strict=True)


class _StrictModel(BaseModel):
    model_config = _FORBID


class PerturbationApplicationAction(_StrictModel):
    variant: Literal[
        "decision_route_interruption",
        "verification_feedback_interruption",
    ]


@dataclass(frozen=True)
class CompositeExperimentFixture:
    """One compiled row plus its reviewed perturbation identity."""

    row_id: PerturbationRowId
    perturbation: PerturbationSpec | None
    runtime: CoordinationRuntimeFixture
    changed_refs: tuple[str, ...]
    scheduled_application: bool

    @property
    def scenario(self) -> CausalScenario:
        return self.runtime.scenario


@dataclass(frozen=True)
class CompositeAssayExecution:
    """Validated five-row result retained through the ordinary run store."""

    assay_id: str
    setup: CompositeAssaySetup
    run_refs: tuple[CompositeAssayRunRef, ...]
    readouts: tuple[CompositeControlReadout, ...]
    evidence_by_run: Mapping[str, CompositeAssayRunEvidence]
    retained_run_ids: tuple[str, ...]


def run_scripted_composite_assay(
    store_root: Path,
) -> CompositeAssayExecution:
    """Execute, calculate, validate, and retain the five provider-free rows."""

    perturbations = reviewed_perturbation_specs()
    store = RunStore(store_root)
    existing_assay_ids = {
        str(metadata.get("assay_id"))
        for summary in store.list_runs()[0]
        if isinstance((metadata := summary.get("composite_assay")), Mapping)
    }
    assay_id = f"assay_{token_hex(6)}"
    while assay_id in existing_assay_ids:
        assay_id = f"assay_{token_hex(6)}"
    rows: list[tuple[PerturbationRowId, PerturbationSpec | None]] = [
        (CONTROL_ID, None),
        *[
            (cast(PerturbationRowId, item.perturbation_id), item)
            for item in perturbations
        ],
    ]
    fixtures = {
        row_id: composite_experiment_fixture(row_id, perturbation)
        for row_id, perturbation in rows
    }
    control = fixtures[CONTROL_ID]
    diff_reports = {
        row_id: validate_matched_configuration(control, fixture)
        for row_id, fixture in fixtures.items()
    }
    setup_fixture = build_composite_assay_scenario_fixture(
        control.runtime.contract,
        scenario_revision="composite_assay_revision_one",
        matched_world_fingerprint=_digest_json(
            {
                "scenario": "coordination_decision_v1",
                "assay": "composite_agency_v1",
                "shared_runtime": "packet_22a1_revision_2",
            }
        ),
        model_policy_fingerprint=_digest_json(
            {
                "execution": "scripted",
                "provider_calls": 0,
                "policy": "coordination_reference_v1",
            }
        ),
        run_control_fingerprint=_digest_json(
            control.runtime.contract.run_control_options.model_dump(mode="json")
        ),
        reviewed_created_refs=(
            "external_risk_source",
            "external_risk_carrier",
            "external_risk_message",
            "external_risk_out",
            "external_risk_route",
            "external_risk_in",
            "external_risk_delivery",
        ),
    )
    capability = CompositeCapabilitySpec(
        member_refs=setup_fixture.member_refs,
        substrate_refs=setup_fixture.substrate_refs,
        exact_success_measure_ids=[
            "final_deployment_status",
            "modeled_time_to_terminal",
            "final_approved_scope",
        ],
        exact_constraint_measure_ids=[
            "partners_retained",
            "unresolved_risk_load",
            "disengagement",
        ],
        limitations=[
            "This bounded scripted assay measures retained behavior, not consciousness."
        ],
    )
    setup = compile_composite_assay_setup(
        setup_fixture,
        capability,
        perturbations,
    )
    run_refs: list[CompositeAssayRunRef] = []
    readouts: list[CompositeControlReadout] = []
    evidence_by_run: dict[str, CompositeAssayRunEvidence] = {}
    retained_run_ids: list[str] = []
    documents: list[dict[str, object]] = []

    for row_index, (row_id, perturbation) in enumerate(rows):
        fixture = fixtures[row_id]
        run_id = f"run_{token_hex(6)}"
        while (store_root / f"{run_id}.json").exists():
            run_id = f"run_{token_hex(6)}"
        result = run_coordination(
            fixture.runtime,
            composite_scripted_bindings(fixture),
            run_id=run_id,
        )
        if result.model_calls != 0 or result.total_observed_cost != 0.0:
            raise RuntimeError("scripted composite assay unexpectedly used a provider")
        compiled = _compiled_experiment(fixture)
        theory = build_reference_theory_analysis(compiled, result)
        bundle, framework_readouts, activity = _reopen_theory(theory)
        application_event_id = _application_event_id(row_id, result.core_result.events)
        evidence = CompositeAssayRunEvidence(
            run_id=run_id,
            perturbation_id=row_id,
            scenario_revision=setup.scenario_revision,
            matched_world_fingerprint=setup.matched_world_fingerprint,
            model_policy_fingerprint=setup.model_policy_fingerprint,
            run_control_fingerprint=setup.run_control_fingerprint,
            applied_changed_refs=([] if perturbation is None else perturbation.changed_refs),
            perturbation_application_event_id=application_event_id,
            evidence_bundle=bundle,
            framework_readouts=framework_readouts,
            boundary_activity_ref=f"boundary:{BOUNDARY_ID}:activity",
            boundary_activity=activity,
        )
        readout = calculate_composite_control_readout(
            row_id=row_id,
            result=result,
            evidence=evidence,
            application_event_id=application_event_id,
        )
        run_ref = CompositeAssayRunRef(
            run_id=run_id,
            perturbation_id=row_id,
            scenario_fingerprint=result.scenario_fingerprint,
            valid=True,
        )
        run_refs.append(run_ref)
        readouts.append(readout)
        evidence_by_run[run_id] = evidence
        document = _retained_document(
            fixture,
            result,
            theory=theory,
            evidence=evidence,
            readout=readout,
            configuration_diff=diff_reports[row_id],
            assay_id=assay_id,
            row_index=row_index,
            row_count=len(rows),
        )
        documents.append(document)
        retained_run_ids.append(run_id)

    validate_composite_assay_evidence(
        setup,
        run_refs,
        readouts,
        evidence_by_run,
    )
    for document in documents:
        store.save(document)
    return CompositeAssayExecution(
        assay_id=assay_id,
        setup=setup,
        run_refs=tuple(run_refs),
        readouts=tuple(readouts),
        evidence_by_run=evidence_by_run,
        retained_run_ids=tuple(retained_run_ids),
    )


def composite_experiment_fixture(
    row_id: PerturbationRowId,
    perturbation: PerturbationSpec | None,
) -> CompositeExperimentFixture:
    """Compile one reviewed row without executing it."""

    if row_id == CONTROL_ID:
        if perturbation is not None:
            raise ValueError("matched control cannot carry a perturbation")
    elif perturbation is None or perturbation.perturbation_id != row_id:
        raise ValueError("experiment row and perturbation identity disagree")

    contract = _instrument_contract(
        baseline_coordination_fixture(),
        row_id=row_id,
        perturbation=perturbation,
    )
    base_runtime = coordination_runtime_fixture(contract)
    exact_bindings = dict(base_runtime.exact_bindings)
    exact_bindings["terminal_proposal_switch"] = _exact_binding(
        "terminal_proposal_switch",
        _exact_terminal_proposal_switch,
    )
    exact_bindings["perturbation_application"] = _exact_binding(
        "perturbation_application",
        _exact_perturbation_application,
    )
    for person_id in PERSON_IDS:
        mechanism_id = f"verification_response_delivery_{person_id}"
        original = exact_bindings[mechanism_id].handler
        exact_bindings[mechanism_id] = _exact_binding(
            mechanism_id,
            _feedback_guard(original),
        )
    if row_id == "external_risk":
        exact_bindings["external_risk_delivery"] = _exact_binding(
            "external_risk_delivery",
            _exact_external_risk_delivery,
        )

    active_specs = list(base_runtime.active_specs)
    for index, spec in enumerate(active_specs):
        if spec.active_system_id != "technical_validation_lead":
            continue
        private_state = dict(spec.initial_private_state)
        private_state["replacement_profile"] = row_id == "member_replacement"
        active_specs[index] = spec.model_copy(
            update={
                "implementation_id": _COMMON_TECHNICAL_IMPLEMENTATION,
                "initial_private_state": private_state,
            }
        )
        break
    else:  # pragma: no cover - base fixture contract guarantees the person
        raise AssertionError("technical validation active system is missing")

    scheduled_variant = (
        perturbation is not None
        and perturbation.variant
        in {
            "decision_route_interruption",
            "verification_feedback_interruption",
        }
    )
    active_specs.append(
        ActiveSystemSpec(
            active_system_id="perturbation_controller",
            entity_id="perturbation_controller",
            implementation_id=_CONTROLLER_IMPLEMENTATION,
            description="Exact scheduled intervention controller for this assay row.",
            output_port_ids=["perturbation_apply_out"],
            initial_private_state={
                "variant": (
                    perturbation.variant if scheduled_variant and perturbation else None
                ),
                "emitted": False,
            },
            initial_next_update_at=(
                PERTURBATION_APPLICATION_TIME if scheduled_variant else None
            ),
        )
    )
    if row_id == "external_risk":
        active_specs.append(
            ActiveSystemSpec(
                active_system_id="external_risk_source",
                entity_id="external_risk_source",
                implementation_id=_RISK_SOURCE_IMPLEMENTATION,
                description="Concrete source of one legitimate decision-relevant risk.",
                output_port_ids=["external_risk_out"],
                output_port_initial_representation_ids={
                    "external_risk_out": ["external_risk_message"]
                },
                initial_representation_ids=["external_risk_message"],
                initial_private_state={"emitted": False},
                initial_next_update_at=PERTURBATION_APPLICATION_TIME,
            )
        )

    runtime = CoordinationRuntimeFixture(
        contract=contract,
        exact_bindings=exact_bindings,
        active_specs=tuple(active_specs),
    )
    return CompositeExperimentFixture(
        row_id=row_id,
        perturbation=perturbation,
        runtime=runtime,
        changed_refs=tuple(perturbation.changed_refs if perturbation else ()),
        scheduled_application=scheduled_variant or row_id == "external_risk",
    )


def composite_scripted_bindings(
    fixture: CompositeExperimentFixture,
) -> dict[str, ActiveSystemBinding]:
    """Bind the shared zero-call policies plus experiment-local processes."""

    core_ids = {
        spec.active_system_id
        for spec in fixture.runtime.active_specs
        if spec.active_system_id
        not in {"perturbation_controller", "external_risk_source"}
    }
    core_runtime = CoordinationRuntimeFixture(
        contract=fixture.runtime.contract,
        exact_bindings=fixture.runtime.exact_bindings,
        active_specs=tuple(
            spec
            for spec in fixture.runtime.active_specs
            if spec.active_system_id in core_ids
        ),
    )
    bindings = coordination_scripted_bindings(core_runtime)
    base_technical = bindings["technical_validation_lead"]
    bindings["technical_validation_lead"] = ActiveSystemBinding(
        _COMMON_TECHNICAL_IMPLEMENTATION,
        ScriptedActiveSystem(
            implementation_id=_COMMON_TECHNICAL_IMPLEMENTATION,
            controller=_technical_controller(base_technical),
        ),
    )
    bindings["perturbation_controller"] = ActiveSystemBinding(
        _CONTROLLER_IMPLEMENTATION,
        ScriptedActiveSystem(
            implementation_id=_CONTROLLER_IMPLEMENTATION,
            controller=_perturbation_controller,
        ),
    )
    if fixture.row_id == "external_risk":
        bindings["external_risk_source"] = ActiveSystemBinding(
            _RISK_SOURCE_IMPLEMENTATION,
            ScriptedActiveSystem(
                implementation_id=_RISK_SOURCE_IMPLEMENTATION,
                controller=_external_risk_source,
            ),
        )
    return bindings


def _instrument_contract(
    source: CoordinationDecisionFixture,
    *,
    row_id: PerturbationRowId,
    perturbation: PerturbationSpec | None,
) -> CoordinationDecisionFixture:
    state = source.scenario.initial_state.model_copy(deep=True)
    _add_common_instrumentation(state, row_id=row_id, perturbation=perturbation)
    if row_id == "member_replacement":
        _apply_member_replacement(state)
    if row_id == "external_risk":
        _add_external_risk_source(state)
    state = CausalState.model_validate(state.model_dump(mode="json"))

    boundaries = [
        boundary.model_copy(deep=True)
        for boundary in source.scenario.analytical_boundaries
    ]
    partnership = _boundary(boundaries, PARTNERSHIP_BOUNDARY_ID)
    partnership.member_refs.extend(
        [
            "perturbation_register",
            "perturbation_application",
            "perturbation_apply_in",
            "terminal_proposal_switch",
            "terminal_proposal_switch_in",
            "terminal_proposal_direct_out",
            "terminal_proposal_alternate_out",
            "terminal_proposal_alternate_in",
        ]
    )
    source_boundary = _boundary(boundaries, SOURCE_BOUNDARY_ID)
    source_boundary.member_refs.extend(
        ["perturbation_controller", "perturbation_apply_out"]
    )
    if row_id == "external_risk":
        source_boundary.member_refs.extend(
            [
                "external_risk_source",
                "external_risk_carrier",
                "external_risk_message",
                "external_risk_out",
            ]
        )
        partnership.member_refs.extend(
            ["external_risk_delivery", "external_risk_in"]
        )
    validated_boundaries = [
        AnalyticalBoundary.model_validate(item.model_dump(mode="json"))
        for item in boundaries
    ]
    scenario = source.scenario.model_copy(
        update={
            "initial_state": state,
            "analytical_boundaries": validated_boundaries,
        }
    )
    return CoordinationDecisionFixture.model_validate(
        source.model_copy(update={"scenario": scenario}).model_dump(mode="json")
    )


def _add_common_instrumentation(
    state: CausalState,
    *,
    row_id: PerturbationRowId,
    perturbation: PerturbationSpec | None,
) -> None:
    state.entities["perturbation_register"] = EntityState(
        entity_id="perturbation_register",
        entity_kind="intervention_record",
        description="Exact retained state of the selected perturbation row.",
        attributes={
            "row_id": FactState(value=row_id, visibility="analyst"),
            "variant": FactState(
                value=perturbation.variant if perturbation else None,
                visibility="analyst",
            ),
            "direct_route_enabled": FactState(value=True),
            "verification_feedback_enabled": FactState(value=True),
            "applied": FactState(value=row_id == "member_replacement"),
            "applied_at": FactState(
                value=0 if row_id == "member_replacement" else None
            ),
        },
    )
    state.entities["perturbation_controller"] = EntityState(
        entity_id="perturbation_controller",
        entity_kind="scheduled_process",
        description="Outside exact process applying a reviewed scheduled change.",
    )
    state.placements["perturbation_register"] = PlacementState(
        entity_id="perturbation_register", place_id="partnership_hub"
    )
    state.placements["perturbation_controller"] = PlacementState(
        entity_id="perturbation_controller", place_id="source_operations_site"
    )
    state.ports.update(
        {
            "perturbation_apply_out": PortState(
                port_id="perturbation_apply_out",
                owner_ref="perturbation_controller",
                direction="output",
                effect_type="perturbation_application",
                description="Scheduled reviewed perturbation output.",
            ),
            "perturbation_apply_in": PortState(
                port_id="perturbation_apply_in",
                owner_ref="perturbation_application",
                direction="input",
                effect_type="perturbation_application",
                description="Exact perturbation application input.",
            ),
            "terminal_proposal_switch_in": PortState(
                port_id="terminal_proposal_switch_in",
                owner_ref="terminal_proposal_switch",
                direction="input",
                effect_type="terminal_proposal",
                description="Stable proposal submission input before route selection.",
            ),
            "terminal_proposal_direct_out": PortState(
                port_id="terminal_proposal_direct_out",
                owner_ref="terminal_proposal_switch",
                direction="output",
                effect_type="terminal_proposal",
                description="Direct proposal path selected by the exact switch.",
            ),
            "terminal_proposal_alternate_out": PortState(
                port_id="terminal_proposal_alternate_out",
                owner_ref="terminal_proposal_switch",
                direction="output",
                effect_type="terminal_proposal",
                description="Alternate proposal path selected by the exact switch.",
            ),
            "terminal_proposal_alternate_in": PortState(
                port_id="terminal_proposal_alternate_in",
                owner_ref="terminal_decision_gate",
                direction="input",
                effect_type="terminal_proposal",
                description="Alternate exact decision-gate proposal input.",
            ),
        }
    )
    state.connections["perturbation_application_route"] = ConnectionState(
        connection_id="perturbation_application_route",
        source_port_id="perturbation_apply_out",
        target_port_id="perturbation_apply_in",
        delay=1,
        description="Positive-duration route for one reviewed scheduled change.",
    )
    state.connections["terminal_proposal_submission_route"] = ConnectionState(
        connection_id="terminal_proposal_submission_route",
        source_port_id="terminal_proposal_out",
        target_port_id="terminal_proposal_switch_in",
        delay=1,
        description="Stable proposal submission route into the exact route switch.",
    )
    state.connections["terminal_proposal_route"] = ConnectionState(
        connection_id="terminal_proposal_route",
        source_port_id="terminal_proposal_direct_out",
        target_port_id="terminal_proposal_in",
        delay=1,
        description="Reviewed direct path from the route switch to the decision gate.",
    )
    state.connections["terminal_proposal_alternate_route"] = ConnectionState(
        connection_id="terminal_proposal_alternate_route",
        source_port_id="terminal_proposal_alternate_out",
        target_port_id="terminal_proposal_alternate_in",
        delay=3,
        description="Configured slower alternate path to the exact decision gate.",
    )
    state.mechanisms["perturbation_application"] = MechanismSpec(
        mechanism_id="perturbation_application",
        mechanism_kind="exact_transition",
        implementation_id="perturbation_application_v1",
        description="Applies only one reviewed scheduled assay variant.",
        input_port_ids=["perturbation_apply_in"],
        read_fact_ids=[
            "perturbation_register.variant",
            "perturbation_register.applied",
        ],
        write_fact_ids=[
            "perturbation_register.direct_route_enabled",
            "perturbation_register.verification_feedback_enabled",
            "perturbation_register.applied",
            "perturbation_register.applied_at",
        ],
        substrate_refs=["coordination_platform"],
        invariant_ids=["perturbation_application_contract"],
        fidelity=_fidelity("one exact reviewed scheduled intervention"),
    )
    state.mechanisms["terminal_proposal_switch"] = MechanismSpec(
        mechanism_id="terminal_proposal_switch",
        mechanism_kind="exact_transition",
        implementation_id="terminal_proposal_switch_v1",
        description="Selects one configured proposal path from retained route state.",
        input_port_ids=["terminal_proposal_switch_in"],
        output_port_ids=[
            "terminal_proposal_direct_out",
            "terminal_proposal_alternate_out",
        ],
        read_fact_ids=["perturbation_register.direct_route_enabled"],
        substrate_refs=["coordination_platform"],
        invariant_ids=["terminal_proposal_switch_contract"],
        fidelity=_fidelity("one exact two-path routing switch"),
    )
    gate = state.mechanisms["terminal_decision_gate"]
    state.mechanisms["terminal_decision_gate"] = gate.model_copy(
        update={
            "input_port_ids": [
                *gate.input_port_ids,
                "terminal_proposal_alternate_in",
            ]
        }
    )
    for person_id in PERSON_IDS:
        route_id = f"verification_response_{person_id}_route"
        route = state.connections[route_id]
        state.connections[route_id] = route.model_copy(
            update={"delay": VERIFICATION_FEEDBACK_DELAY}
        )
        mechanism_id = f"verification_response_delivery_{person_id}"
        mechanism = state.mechanisms[mechanism_id]
        state.mechanisms[mechanism_id] = mechanism.model_copy(
            update={
                "read_fact_ids": [
                    *mechanism.read_fact_ids,
                    "perturbation_register.verification_feedback_enabled",
                ]
            }
        )


def _apply_member_replacement(state: CausalState) -> None:
    person = state.entities["technical_validation_lead"]
    attributes = dict(person.attributes)
    attributes["person_instance_id"] = FactState(
        value=REPLACEMENT_PERSON_ID,
        visibility="analyst",
    )
    raw_assumptions = attributes["assumptions"].value
    if not isinstance(raw_assumptions, dict):
        raise TypeError("technical-position assumptions must be an object")
    assumptions = cast(dict[str, JsonValue], dict(raw_assumptions))
    assumptions["dispositions"] = [
        "methodical",
        "skeptical of unresolved calibration claims",
        "quick to request independent verification",
    ]
    assumptions["memories"] = [
        *cast(list[JsonValue], assumptions["memories"]),
        "A prior deployment review failed because verification began too late.",
    ]
    attributes["assumptions"] = FactState(
        value=assumptions,
        visibility="analyst",
    )
    state.entities["technical_validation_lead"] = person.model_copy(
        update={
            "description": (
                "Technical validation position occupied by a replacement person."
            ),
            "attributes": attributes,
        }
    )


def _add_external_risk_source(state: CausalState) -> None:
    content = json.dumps(
        {
            "document_kind": "source_message",
            "topic": "decision_relevant_external_risk",
            "claim": (
                "A newly confirmed cross-border data integrity failure could make "
                "the current full deployment unsafe without additional review."
            ),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    state.entities["external_risk_source"] = EntityState(
        entity_id="external_risk_source",
        entity_kind="source_process",
        description="Concrete source of a legitimate newly confirmed deployment risk.",
        attributes={
            "message_topic": FactState(value="decision_relevant_external_risk")
        },
    )
    state.placements["external_risk_source"] = PlacementState(
        entity_id="external_risk_source", place_id="source_operations_site"
    )
    state.carriers["external_risk_carrier"] = CarrierState(
        carrier_id="external_risk_carrier",
        owner_ref="external_risk_source",
        medium="source_message_record",
        locator="external risk source workspace",
    )
    state.representations["external_risk_message"] = RepresentationToken(
        representation_id="external_risk_message",
        carrier_id="external_risk_carrier",
        carrier_revision=0,
        encoding="application/vnd.cybernetic.source-message+json",
        content=content,
        content_hash=representation_digest(content),
        actual_source_ref="external_risk_source",
    )
    state.ports["external_risk_out"] = PortState(
        port_id="external_risk_out",
        owner_ref="external_risk_source",
        direction="output",
        effect_type="external_risk",
        description="Legitimate external-risk message output.",
    )
    state.ports["external_risk_in"] = PortState(
        port_id="external_risk_in",
        owner_ref="external_risk_delivery",
        direction="input",
        effect_type="external_risk",
        description="Exact external-risk delivery input.",
    )
    state.connections["external_risk_route"] = ConnectionState(
        connection_id="external_risk_route",
        source_port_id="external_risk_out",
        target_port_id="external_risk_in",
        delay=1,
        description="Positive-duration route for the legitimate external risk.",
    )
    state.mechanisms["external_risk_delivery"] = MechanismSpec(
        mechanism_id="external_risk_delivery",
        mechanism_kind="exact_transition",
        implementation_id="external_risk_delivery_v1",
        description="Delivers the retained external risk to the technical position.",
        input_port_ids=["external_risk_in"],
        read_fact_ids=["perturbation_register.applied"],
        write_fact_ids=[
            "perturbation_register.applied",
            "perturbation_register.applied_at",
        ],
        observation_target_ids=["technical_validation_lead"],
        substrate_refs=["coordination_platform"],
        invariant_ids=["external_risk_delivery_contract"],
        fidelity=_fidelity("one exact point-to-point external-risk delivery"),
    )


def _exact_terminal_proposal_switch(
    context: MechanismContext,
) -> MechanismOutcome:
    direct = context.read("perturbation_register.direct_route_enabled")
    if not isinstance(direct, bool):
        raise TypeError("direct route state must be boolean")
    output_port_id = (
        "terminal_proposal_direct_out"
        if direct
        else "terminal_proposal_alternate_out"
    )
    return MechanismOutcome(
        outcome_code=(
            "terminal_proposal_direct_path_selected"
            if direct
            else "terminal_proposal_alternate_path_selected"
        ),
        effects=[
            EffectDraft(
                output_port_id=output_port_id,
                effect_type="terminal_proposal",
                representation_id=(
                    context.representation.representation_id
                    if context.representation is not None
                    else None
                ),
                payload=context.effect.payload,
            )
        ],
    )


def _exact_perturbation_application(
    context: MechanismContext,
) -> MechanismOutcome:
    action = PerturbationApplicationAction.model_validate(context.effect.payload)
    if context.read("perturbation_register.applied") is True:
        return MechanismOutcome(outcome_code="perturbation_already_applied")
    retained_variant = context.read("perturbation_register.variant")
    if retained_variant != action.variant:
        return MechanismOutcome(outcome_code="perturbation_variant_mismatch")
    updates = [
        FactUpdate(fact_id="perturbation_register.applied", value=True),
        FactUpdate(
            fact_id="perturbation_register.applied_at",
            value=context.effect.logical_time,
        ),
    ]
    if action.variant == "decision_route_interruption":
        updates.append(
            FactUpdate(
                fact_id="perturbation_register.direct_route_enabled",
                value=False,
            )
        )
    else:
        updates.append(
            FactUpdate(
                fact_id="perturbation_register.verification_feedback_enabled",
                value=False,
            )
        )
    return MechanismOutcome(
        outcome_code=f"{action.variant}_applied",
        updates=updates,
    )


def _feedback_guard(
    original: Callable[[MechanismContext], MechanismOutcome],
) -> Callable[[MechanismContext], MechanismOutcome]:
    def guarded(context: MechanismContext) -> MechanismOutcome:
        enabled = context.read(
            "perturbation_register.verification_feedback_enabled"
        )
        if not isinstance(enabled, bool):
            raise TypeError("verification feedback state must be boolean")
        if not enabled:
            return MechanismOutcome(outcome_code="verification_feedback_interrupted")
        return original(context)

    return guarded


def _exact_external_risk_delivery(context: MechanismContext) -> MechanismOutcome:
    if context.representation is None:
        raise ValueError("external risk delivery requires its representation")
    document = json.loads(context.representation.content)
    if document.get("topic") != "decision_relevant_external_risk":
        raise ValueError("external risk representation has the wrong topic")
    return MechanismOutcome(
        outcome_code="external_risk_delivered",
        updates=[
            FactUpdate(fact_id="perturbation_register.applied", value=True),
            FactUpdate(
                fact_id="perturbation_register.applied_at",
                value=context.effect.logical_time,
            ),
        ],
        observations=[
            ObservationDraft(
                target_entity_id="technical_validation_lead",
                via_port_id="external_risk_in",
                apparent_content=context.representation.content,
                apparent_source_ref="external_risk_source",
                representation_id=context.representation.representation_id,
            )
        ],
    )


def _perturbation_controller(item: ActiveSystemInput) -> ActiveStepResult:
    variant = item.private_state.get("variant")
    emitted = item.private_state.get("emitted")
    if not isinstance(variant, str) or emitted is not False:
        raise ValueError("scheduled perturbation controller state is invalid")
    action = PerturbationApplicationAction.model_validate({"variant": variant})
    return _scripted_step(
        item,
        implementation_id=_CONTROLLER_IMPLEMENTATION,
        private_state={"variant": variant, "emitted": True},
        actions=[
            ActionIntent(
                output_port_id="perturbation_apply_out",
                payload=action.model_dump(mode="json"),
                public_summary=(
                    f"The reviewed experiment applied {variant} at modeled day 4."
                ),
            )
        ],
    )


def _external_risk_source(item: ActiveSystemInput) -> ActiveStepResult:
    if item.private_state.get("emitted") is not False:
        raise ValueError("external risk source may emit exactly once")
    return _scripted_step(
        item,
        implementation_id=_RISK_SOURCE_IMPLEMENTATION,
        private_state={"emitted": True},
        actions=[
            ActionIntent(
                output_port_id="external_risk_out",
                representation_id="external_risk_message",
                payload={},
                public_summary=(
                    "The external source emitted a newly confirmed deployment risk."
                ),
            )
        ],
    )


def _technical_controller(
    base_binding: ActiveSystemBinding,
) -> Callable[[ActiveSystemInput], ActiveStepResult]:
    def controller(item: ActiveSystemInput) -> ActiveStepResult:
        result = ActiveStepResult.model_validate(base_binding.implementation.step(item))
        proposal = result.proposal
        private_state = dict(proposal.private_state)
        actions = list(proposal.actions)
        replacement = private_state.get("replacement_profile") is True
        meeting_zero = any(
            _observation_document(observation.apparent_content).get("meeting_index")
            == 0
            for observation in item.observations
        )
        if replacement and meeting_zero and not private_state.get(
            "verification_requested", False
        ):
            actions.append(
                ActionIntent(
                    output_port_id="verification_request_out",
                    representation_id="technical_validation_dossier_copy",
                    payload={
                        "verification_id": "independent_calibration",
                        "topic": "independent_calibration",
                        "requested_by": "technical_validation_lead",
                    },
                    public_summary=(
                        "The replacement validation lead requested independent "
                        "calibration at the first meeting."
                    ),
                )
            )
            private_state["verification_requested"] = True
        received_external_risk = any(
            _observation_document(observation.apparent_content).get("topic")
            == "decision_relevant_external_risk"
            for observation in item.observations
        )
        if received_external_risk and private_state.get("commitment") != "defer":
            actions.append(
                ActionIntent(
                    output_port_id="technical_validation_lead_commitment_out",
                    payload={
                        "person_id": "technical_validation_lead",
                        "commitment": "defer",
                    },
                    public_summary=(
                        "The validation lead deferred after receiving the newly "
                        "confirmed external risk."
                    ),
                )
            )
            private_state["commitment"] = "defer"
        return result.model_copy(
            update={
                "proposal": proposal.model_copy(
                    update={
                        "implementation_id": _COMMON_TECHNICAL_IMPLEMENTATION,
                        "private_state": private_state,
                        "actions": actions,
                    }
                )
            }
        )

    return controller


def _scripted_step(
    item: ActiveSystemInput,
    *,
    implementation_id: str,
    private_state: Mapping[str, JsonValue],
    actions: list[ActionIntent],
) -> ActiveStepResult:
    return ActiveStepResult(
        proposal=ActiveProposal(
            active_system_id=item.active_system_id,
            implementation_id=implementation_id,
            private_state=dict(private_state),
            actions=actions,
            update_schedule=UpdateScheduleDirective(mode="dormant"),
        )
    )


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


def _boundary(
    boundaries: list[AnalyticalBoundary], boundary_id: str
) -> AnalyticalBoundary:
    return next(item for item in boundaries if item.boundary_id == boundary_id)


def _fidelity(abstraction: str) -> FidelityNote:
    return FidelityNote(
        abstraction=abstraction,
        assumptions=["The reviewed state transition is stipulated for this PoC."],
        known_omissions=["Real institutions, platforms, timing, and behavior."],
        validation_basis=["Scenario-local contracts and both-sign tests."],
    )


def _observation_document(content: str) -> dict[str, object]:
    try:
        value = json.loads(content)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def validate_matched_configuration(
    control: CompositeExperimentFixture,
    candidate: CompositeExperimentFixture,
) -> dict[str, JsonValue]:
    """Prove that one row changes only reviewed refs plus assay metadata."""

    control_refs = _state_ref_payloads(control.scenario.initial_state)
    candidate_refs = _state_ref_payloads(candidate.scenario.initial_state)
    changed = {
        ref
        for ref in set(control_refs) | set(candidate_refs)
        if control_refs.get(ref) != candidate_refs.get(ref)
    }
    declared = set(candidate.changed_refs)
    normalized_changed = {
        ref.split(".", 1)[0]
        if ref.split(".", 1)[0] in declared
        else ref
        for ref in changed
    }
    instrumentation_refs = {
        "perturbation_register.row_id",
        "perturbation_register.variant",
        "perturbation_register.applied",
        "perturbation_register.applied_at",
    }
    allowed = declared | instrumentation_refs
    unexpected = normalized_changed - allowed
    if unexpected:
        raise ValueError(
            "assay row changed undeclared scenario references "
            f"{sorted(unexpected)!r}"
        )

    control_shell = control.scenario.model_dump(
        mode="json",
        exclude={"initial_state", "analytical_boundaries"},
    )
    candidate_shell = candidate.scenario.model_dump(
        mode="json",
        exclude={"initial_state", "analytical_boundaries"},
    )
    if control_shell != candidate_shell:
        raise ValueError("assay row changed undeclared scenario-level configuration")
    control_boundaries = {
        item.boundary_id: item for item in control.scenario.analytical_boundaries
    }
    candidate_boundaries = {
        item.boundary_id: item for item in candidate.scenario.analytical_boundaries
    }
    if set(control_boundaries) != set(candidate_boundaries):
        raise ValueError("assay row changed analytical boundary identities")
    for boundary_id, control_boundary in control_boundaries.items():
        candidate_boundary = candidate_boundaries[boundary_id]
        control_metadata = control_boundary.model_dump(
            mode="json", exclude={"member_refs"}
        )
        candidate_metadata = candidate_boundary.model_dump(
            mode="json", exclude={"member_refs"}
        )
        if control_metadata != candidate_metadata:
            raise ValueError("assay row changed analytical boundary metadata")
        added_members = set(candidate_boundary.member_refs) - set(
            control_boundary.member_refs
        )
        removed_members = set(control_boundary.member_refs) - set(
            candidate_boundary.member_refs
        )
        if removed_members or added_members - set(candidate.changed_refs):
            raise ValueError("assay row changed undeclared analytical members")

    control_specs = {
        item.active_system_id: item.model_dump(mode="json")
        for item in control.runtime.active_specs
    }
    candidate_specs = {
        item.active_system_id: item.model_dump(mode="json")
        for item in candidate.runtime.active_specs
    }
    changed_specs = {
        ref
        for ref in set(control_specs) | set(candidate_specs)
        if control_specs.get(ref) != candidate_specs.get(ref)
    }
    allowed_specs = {"perturbation_controller"}
    if candidate.row_id == "member_replacement":
        allowed_specs.add("technical_validation_lead")
    if candidate.row_id == "external_risk":
        allowed_specs.add("external_risk_source")
    if changed_specs - allowed_specs:
        raise ValueError(
            "assay row changed undeclared active systems "
            f"{sorted(changed_specs - allowed_specs)!r}"
        )
    added_bindings = set(candidate.runtime.exact_bindings) - set(
        control.runtime.exact_bindings
    )
    removed_bindings = set(control.runtime.exact_bindings) - set(
        candidate.runtime.exact_bindings
    )
    expected_added_bindings = (
        {"external_risk_delivery"}
        if candidate.row_id == "external_risk"
        else set()
    )
    if added_bindings != expected_added_bindings or removed_bindings:
        raise ValueError("assay row changed undeclared exact bindings")
    return cast(
        dict[str, JsonValue],
        {
            "row_id": candidate.row_id,
            "declared_changed_refs": list(candidate.changed_refs),
            "initial_configuration_changed_refs": sorted(
                normalized_changed - instrumentation_refs
            ),
            "assay_metadata_refs": sorted(
                normalized_changed & instrumentation_refs
            ),
            "changed_active_system_specs": sorted(changed_specs),
            "scheduled_change": candidate.scheduled_application,
            "unexpected_refs": [],
        },
    )


def calculate_composite_control_readout(
    *,
    row_id: PerturbationRowId,
    result: ActiveRuntimeResult,
    evidence: CompositeAssayRunEvidence,
    application_event_id: str | None,
) -> CompositeControlReadout:
    """Calculate the exact vector and reference-coded pattern from one run."""

    retained_result = result
    exact = calculate_exact_values(retained_result)
    activity = evidence.boundary_activity
    if activity is None:  # pragma: no cover - evidence model requires coexistence
        raise ValueError("composite readout requires boundary activity")
    events = retained_result.core_result.events
    terminal_event = next(
        event for event in reversed(events) if event.event_kind == "run_completed"
    )
    terminal_status = exact["final_deployment_status"]
    decision_time = cast(dict[str, JsonValue], exact["modeled_time_to_terminal"])[
        "scenario_minutes"
    ]
    retained_partners = cast(dict[str, JsonValue], exact["partners_retained"])
    unresolved = cast(dict[str, JsonValue], exact["unresolved_risk_load"])
    disengagement = cast(dict[str, JsonValue], exact["disengagement"])
    failed_constraints: list[str] = []
    if retained_partners["count"] != len(PERSON_IDS):
        failed_constraints.append("partners_retained")
    if unresolved["final_open_count"] != 0:
        failed_constraints.append("unresolved_risk_load")
    if disengagement["count"] != 0:
        failed_constraints.append("disengagement")
    capability_satisfied = (
        terminal_status in {"deploy_on_time", "scope_reduced"}
        and not failed_constraints
        and isinstance(decision_time, int)
        and decision_time <= DECISION_DEADLINE_TIME
    )
    incoming = [item for item in activity.crossings if item.direction == "incoming"]
    outgoing = [item for item in activity.crossings if item.direction == "outgoing"]
    completed = [item for item in activity.episodes if item.status == "completed"]
    in_progress = [item for item in activity.episodes if item.status == "in_progress"]
    output_attempts = [
        event.event_id
        for event in events
        if event.event_kind == "action_attempted"
        and event.source_port_id == "terminal_proposal_out"
    ]
    external_results = list(
        dict.fromkeys(
            event_id
            for episode in activity.episodes
            for event_id in episode.external_result_event_ids
        )
    )
    alternate_route_events = [
        event.event_id
        for event in events
        if event.event_kind == "effect_routed"
        and event.connection_id == "terminal_proposal_alternate_route"
        and (
            application_event_id is None
            or event.sequence > _event_sequence(application_event_id)
        )
    ]
    corrections = _correction_pairs(events)
    recovery: JsonValue
    if row_id in {CONTROL_ID, "member_replacement"}:
        recovery = "not_applicable"
    elif not capability_satisfied or application_event_id is None:
        recovery = "not_observed"
    else:
        application_event = _event_by_id(events, application_event_id)
        restoration_event = next(
            event
            for event in events
            if event.details.get("outcome_code") == "terminal_decision_accepted"
        )
        recovery = cast(
            JsonValue,
            {
                "scenario_minutes": restoration_event.logical_time
                - application_event.logical_time,
                "application_event_id": application_event_id,
                "restoration_event_id": restoration_event.event_id,
            },
        )
    member_replacements: list[JsonValue] = []
    technical_attributes = retained_result.core_result.final_state.entities[
        "technical_validation_lead"
    ].attributes
    person_instance = (
        technical_attributes["person_instance_id"].value
        if "person_instance_id" in technical_attributes
        else None
    )
    if person_instance is not None:
        member_replacements.append(
            cast(
                JsonValue,
                {
                    "position_id": "technical_validation_lead",
                    "person_instance_id": person_instance,
                },
            )
        )
    denials = sum(
        event.event_kind == "mechanism_executed"
        and isinstance(event.details.get("outcome_code"), str)
        and str(event.details["outcome_code"]).endswith("_denied")
        for event in events
    )
    withdrawn_people = {
        event.actor_entity_id
        for event in events
        if event.event_kind == "action_attempted"
        and event.source_port_id == "withdrawal_out"
        and event.actor_entity_id is not None
    }
    active_people = [
        person_id for person_id in PERSON_IDS if person_id not in withdrawn_people
    ]
    if len(active_people) != retained_partners["count"]:
        raise ValueError("retained partner identities disagree with exact count")
    pattern = _reference_pattern(row_id, events, application_event_id)
    return CompositeControlReadout(
        perturbation_id=row_id,
        exact_values=cast(
            dict[str, JsonValue],
            {
                "capability_satisfied": capability_satisfied,
                "all_constraints_satisfied": not failed_constraints,
                "failed_constraint_ids": failed_constraints,
                "terminal_outcome": terminal_status,
                "modeled_decision_time": decision_time,
                "correction_event_pairs": corrections,
                "recovery": recovery,
                "alternate_routes_used": alternate_route_events,
                "active_partners_retained": active_people,
                "member_replacements": member_replacements,
                "terminal_proposal_denials": denials,
                "input_crossing_count": len(incoming),
                "output_crossing_count": len(outgoing),
                "completed_episode_count": len(completed),
                "in_progress_episode_count": len(in_progress),
            },
        ),
        boundary_activity_ref=f"boundary:{BOUNDARY_ID}:activity",
        input_crossing_ids=[item.crossing_id for item in incoming],
        output_crossing_ids=[item.crossing_id for item in outgoing],
        coordination_episode_ids=[item.episode_id for item in activity.episodes],
        output_attempt_event_ids=output_attempts,
        external_result_event_ids=external_results,
        terminal_outcome_event_id=terminal_event.event_id,
        framework_readout_refs=[
            item.readout_id for item in evidence.framework_readouts
        ],
        coded_patterns=[pattern],
        source_run_ids=[retained_result.run_id],
        limitations=[
            "Exact values are exact only relative to this synthetic retained trace.",
            "Reference-coded patterns describe compatibility with a pattern; they do not establish a cause.",
        ],
    )


def _compiled_experiment(fixture: CompositeExperimentFixture) -> CompiledScenario:
    proposal = reviewed_coordination_proposal()
    workflow = proposal.workflow.model_copy(update={"condition": "baseline"})
    proposal = proposal.model_copy(update={"workflow": workflow})
    payload = proposal.model_dump(mode="json")
    return CompiledScenario(
        proposal=proposal,
        proposal_digest=_digest_json(payload),
        fixture=fixture.runtime,
    )


def _reopen_theory(
    theory: Mapping[str, object],
) -> tuple[
    RunEvidenceBundleConsumerV1,
    list[FrameworkReadoutConsumerV1],
    BoundaryActivityProjection,
]:
    raw_bundle = theory.get("bundle")
    if not isinstance(raw_bundle, Mapping):
        raise ValueError("provider-free theory analysis did not retain a bundle")
    bundle = RunEvidenceBundleConsumerV1.model_validate(raw_bundle)
    raw_modules = theory.get("modules")
    if not isinstance(raw_modules, Mapping):
        raise ValueError("provider-free theory analysis did not retain modules")
    readouts: list[FrameworkReadoutConsumerV1] = []
    for module_id in ("decision_environment", "collective_competence"):
        module = raw_modules.get(module_id)
        if not isinstance(module, Mapping) or module.get("status") != "available":
            raise ValueError(f"provider-free theory module {module_id!r} is unavailable")
        readouts.append(FrameworkReadoutConsumerV1.model_validate(module.get("readout")))
    raw_records = raw_bundle.get("evidence_records")
    if not isinstance(raw_records, list):
        raise ValueError("theory bundle lacks evidence records")
    boundary_ref = f"boundary:{BOUNDARY_ID}:activity"
    boundary_record = next(
        (
            item
            for item in raw_records
            if isinstance(item, Mapping) and item.get("evidence_ref") == boundary_ref
        ),
        None,
    )
    if not isinstance(boundary_record, Mapping):
        raise ValueError("theory bundle lacks partnership boundary activity")
    activity = BoundaryActivityProjection.model_validate(boundary_record.get("payload"))
    return bundle, readouts, activity


def _retained_document(
    fixture: CompositeExperimentFixture,
    result: ActiveRuntimeResult,
    *,
    theory: Mapping[str, object],
    evidence: CompositeAssayRunEvidence,
    readout: CompositeControlReadout,
    configuration_diff: Mapping[str, JsonValue],
    assay_id: str,
    row_index: int,
    row_count: int,
) -> dict[str, object]:
    retained_result = result
    terminal = readout.exact_values["terminal_outcome"]
    capability = readout.exact_values["capability_satisfied"]
    document = build_analyst_document(
        initial_state=fixture.scenario.initial_state,
        analytical_boundaries=fixture.scenario.analytical_boundaries,
        result=retained_result,
        scenario="composite agency assay",
        profile="packet 22a1 scripted reference",
        arm_id=fixture.row_id,
        execution="reference",
        created_at=now_iso(),
        outcome={
            "terminal_status": terminal,
            "capability_satisfied": capability,
        },
        headline=f"Composite assay row: {fixture.row_id.replace('_', ' ')}",
        summary=(
            f"The row ended with {terminal}; reviewed collective capability "
            f"satisfaction was {capability}."
        ),
        include_boundary_activity=True,
    )
    document["theory_analysis"] = dict(theory)
    document["composite_assay_evidence"] = evidence.model_dump(mode="json")
    document["composite_control_readout"] = readout.model_dump(mode="json")
    document["configuration_diff"] = dict(configuration_diff)
    document["composite_assay"] = {
        "schema_version": 1,
        "assay_id": assay_id,
        "row_index": row_index,
        "row_count": row_count,
        "provider_calls": 0,
    }
    return document


def _application_event_id(
    row_id: PerturbationRowId,
    events: list[CausalEvent],
) -> str | None:
    if row_id in {CONTROL_ID, "member_replacement"}:
        return None
    mechanism_id = (
        "external_risk_delivery"
        if row_id == "external_risk"
        else "perturbation_application"
    )
    matches = [
        event.event_id
        for event in events
        if event.event_kind == "mechanism_executed"
        and event.mechanism_id == mechanism_id
    ]
    if len(matches) != 1:
        raise ValueError(f"row {row_id!r} lacks one exact application event")
    return matches[0]


def _correction_pairs(events: list[CausalEvent]) -> list[JsonValue]:
    opened = [
        event
        for event in events
        if event.details.get("outcome_code") in {"issue_open", "issue_reopened"}
    ]
    resolved = [
        event
        for event in events
        if event.details.get("outcome_code") == "issue_resolved"
    ]
    pairs: list[JsonValue] = []
    for resolution in resolved:
        candidates = [
            event
            for event in opened
            if event.sequence < resolution.sequence
            and _is_ancestor(event.event_id, resolution.event_id, events)
        ]
        if not candidates:
            continue
        source = candidates[-1]
        pairs.append(
            cast(
                JsonValue,
                {
                    "issue_event_id": source.event_id,
                    "correction_event_id": resolution.event_id,
                },
            )
        )
    return pairs


def _reference_pattern(
    row_id: PerturbationRowId,
    events: list[CausalEvent],
    application_event_id: str | None,
) -> CompositePatternEvidence:
    if row_id == "feedback_interruption":
        sources = [
            event.event_id
            for event in events
            if event.details.get("outcome_code") == "verification_feedback_interrupted"
        ]
        pattern_id = "competence_loss"
        explanation = (
            "Verification feedback was exactly interrupted and the partnership "
            "did not produce a valid decision by the horizon."
        )
    elif row_id == "route_interruption":
        sources = [
            event.event_id
            for event in events
            if event.connection_id == "terminal_proposal_alternate_route"
        ]
        pattern_id = "defensive_adaptation"
        explanation = (
            "The direct proposal path was disabled and the retained decision "
            "traversed the configured alternate path."
        )
    elif row_id == "external_risk":
        delivery_events = [
            event.event_id
            for event in events
            if event.mechanism_id == "external_risk_delivery"
        ]
        caution_events = [
            event.event_id
            for event in events
            if event.event_kind == "action_attempted"
            and event.actor_entity_id == "technical_validation_lead"
            and "defer" in event.summary.lower()
        ]
        if not delivery_events or not caution_events:
            raise ValueError(
                "external-risk row lacks delivered risk plus observed caution"
            )
        sources = [*delivery_events, *caution_events]
        pattern_id = "rational_caution"
        explanation = (
            "A legitimate retained risk reached the validation position and "
            "elicited a temporary deferral; no hostile intent is inferred."
        )
    elif row_id == "member_replacement":
        sources = [
            event.event_id
            for event in events
            if event.event_kind == "action_attempted"
            and event.actor_entity_id == "technical_validation_lead"
            and event.source_port_id == "verification_request_out"
        ][:1]
        pattern_id = "defensive_adaptation"
        explanation = (
            "The replacement occupant requested independent verification earlier "
            "while using the same position-owned interface."
        )
    else:
        sources = [
            event.event_id
            for event in events
            if event.event_kind == "run_completed"
        ]
        pattern_id = "unclear"
        explanation = "The matched control makes no perturbation-pattern claim."
    if application_event_id is not None:
        sources = list(dict.fromkeys([application_event_id, *sources]))
    if not sources:
        raise ValueError(f"row {row_id!r} lacks evidence for its reference pattern")
    return CompositePatternEvidence(
        pattern_id=cast(CompositePatternId, pattern_id),
        direction="unclear" if row_id == CONTROL_ID else "present",
        explanation=explanation,
        source_event_ids=sources,
        source_trace_ids=[f"event:{event_id}" for event_id in sources],
    )


def _is_ancestor(
    ancestor_id: str,
    descendant_id: str,
    events: list[CausalEvent],
) -> bool:
    parents = {event.event_id: event.causal_parent_event_ids for event in events}
    pending = list(parents[descendant_id])
    visited: set[str] = set()
    while pending:
        current = pending.pop()
        if current == ancestor_id:
            return True
        if current in visited:
            continue
        visited.add(current)
        pending.extend(parents[current])
    return False


def _event_by_id(events: list[CausalEvent], event_id: str) -> CausalEvent:
    return next(event for event in events if event.event_id == event_id)


def _event_sequence(event_id: str) -> int:
    return int(event_id.removeprefix("event_"))


def _state_ref_payloads(state: CausalState) -> dict[str, JsonValue]:
    grouped: dict[str, list[JsonValue]] = {}
    for kind, values in (
        ("entity", state.entities),
        ("container", state.containers),
        ("place", state.places),
        ("spatial_link", state.spatial_links),
        ("placement", state.placements),
        ("port", state.ports),
        ("connection", state.connections),
        ("mechanism", state.mechanisms),
        ("carrier", state.carriers),
        ("representation", state.representations),
    ):
        for ref, value in values.items():
            payload = value.model_dump(mode="json")
            if kind == "entity":
                attributes = payload.pop("attributes")
                if not isinstance(attributes, dict):  # pragma: no cover - model shape
                    raise TypeError("entity attributes must serialize as an object")
                for attribute, fact in attributes.items():
                    grouped.setdefault(f"{ref}.{attribute}", []).append(
                        cast(
                            JsonValue,
                            {"kind": "fact", "value": fact},
                        )
                    )
            grouped.setdefault(ref, []).append(
                cast(
                    JsonValue,
                    {
                        "kind": kind,
                        "value": payload,
                    },
                )
            )
    return cast(dict[str, JsonValue], grouped)


def _digest_json(value: object) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
