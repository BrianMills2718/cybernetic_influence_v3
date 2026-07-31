"""Execution-free contract tests for the first composite perturbation assay."""

from __future__ import annotations

from functools import lru_cache
from typing import cast

import pytest
from pydantic import JsonValue, ValidationError

from cybernetic_influence.analysis.composite_agency import (
    CAPABILITY_ID,
    CONTROL_ID,
    CompositeAssayContractError,
    CompositeAssayRunEvidence,
    CompositeAssayRunRef,
    CompositeAssayRunRefConsumer,
    CompositeAssayScenarioFixture,
    CompositeAssaySetup,
    CompositeCapabilitySpec,
    CompositeCapabilitySpecConsumer,
    CompositeControlReadout,
    CompositeControlReadoutConsumer,
    CompositePatternEvidence,
    PerturbationSpec,
    PerturbationSpecConsumer,
    build_composite_assay_scenario_fixture,
    compile_composite_assay_setup,
    validate_composite_assay_evidence,
)
from cybernetic_influence.analysis.theory_analysis import (
    FrameworkReadoutConsumerV1,
    RunEvidenceBundleConsumerV1,
)
from cybernetic_influence.presentation import (
    BoundaryActivityProjection,
    BoundaryCoordinationEpisode,
    BoundaryCrossing,
)
from cybernetic_influence.scenarios.coordination_decision import (
    PERSON_IDS,
    scenario_fingerprint,
    stabilization_coordination_fixture,
)

_DIGEST = scenario_fingerprint(stabilization_coordination_fixture().scenario)
_MATCHED = "b" * 64
_MODEL = "c" * 64
_CONTROL = "d" * 64
_BOUNDARY_REF = "boundary:deployment_partnership:activity"

_PERTURBATION_PAYLOADS: tuple[dict[str, object], ...] = (
    {
        "perturbation_id": "member_replacement",
        "family": "component",
        "variant": "position_matched_member_replacement",
        "application": "initial_condition",
        "changed_refs": ["technical_validation_lead"],
        "description": "Replace one person while preserving the reviewed position.",
    },
    {
        "perturbation_id": "route_interruption",
        "family": "structure",
        "variant": "decision_route_interruption",
        "application": "scheduled_day_4",
        "changed_refs": ["perturbation_register.direct_route_enabled"],
        "description": "Interrupt the direct terminal-proposal route.",
    },
    {
        "perturbation_id": "feedback_interruption",
        "family": "feedback",
        "variant": "verification_feedback_interruption",
        "application": "scheduled_day_4",
        "changed_refs": [
            "perturbation_register.verification_feedback_enabled"
        ],
        "description": "Interrupt reviewed verification feedback routes.",
    },
    {
        "perturbation_id": "external_risk",
        "family": "shock",
        "variant": "relevant_external_risk",
        "application": "scheduled_day_4",
        "changed_refs": [
            "external_risk_source",
            "external_risk_carrier",
            "external_risk_message",
            "external_risk_out",
            "external_risk_route",
            "external_risk_in",
            "external_risk_delivery",
        ],
        "description": "Introduce one legitimate decision-relevant risk.",
    },
)


def _perturbations() -> list[PerturbationSpec]:
    return [
        PerturbationSpec.model_validate(
            {
                "schema_version": 1,
                "matched_control_id": CONTROL_ID,
                **payload,
            }
        )
        for payload in _PERTURBATION_PAYLOADS
    ]


@lru_cache(maxsize=1)
def _fixture() -> CompositeAssayScenarioFixture:
    return build_composite_assay_scenario_fixture(
        stabilization_coordination_fixture(),
        scenario_revision="coordination_revision_one",
        matched_world_fingerprint=_MATCHED,
        model_policy_fingerprint=_MODEL,
        run_control_fingerprint=_CONTROL,
    )


def _capability() -> CompositeCapabilitySpec:
    fixture = _fixture()
    return CompositeCapabilitySpec(
        member_refs=fixture.member_refs,
        substrate_refs=fixture.substrate_refs,
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
            "This bounded assay does not establish organization consciousness."
        ],
    )


def _setup() -> CompositeAssaySetup:
    return compile_composite_assay_setup(
        _fixture(),
        _capability(),
        _perturbations(),
    )


def _activity(*, unknown_episode_event: bool = False) -> BoundaryActivityProjection:
    incoming = BoundaryCrossing(
        crossing_id=(
            "boundary_crossing_deployment_partnership_event_000001"
        ),
        boundary_id="deployment_partnership",
        event_id="event_000001",
        sequence=1,
        direction="incoming",
        source_ref="external_risk_source",
        target_ref="technical_validation_lead",
        route_kind="connection",
        route_ref="external_risk_route",
        effect_id="incoming_effect",
    )
    outgoing = BoundaryCrossing(
        crossing_id=(
            "boundary_crossing_deployment_partnership_event_000004"
        ),
        boundary_id="deployment_partnership",
        event_id="event_000004",
        sequence=4,
        direction="outgoing",
        source_ref="terminal_decision_gate",
        target_ref="external_decision_registry",
        route_kind="connection",
        route_ref="terminal_decision_output_route",
        effect_id="outgoing_effect",
    )
    episode = BoundaryCoordinationEpisode(
        episode_id=(
            "boundary_episode_deployment_partnership_event_000004"
        ),
        boundary_id="deployment_partnership",
        status="completed",
        input_crossing_ids=[incoming.crossing_id],
        prior_output_crossing_ids=[],
        trigger_event_ids=["event_000001"],
        internal_event_ids=[
            "event_999999" if unknown_episode_event else "event_000002",
            "event_000003",
        ],
        output_crossing_id=outgoing.crossing_id,
        external_result_event_ids=["event_000005"],
        contributing_member_ids=[
            "technical_validation_lead",
            "terminal_decision_gate",
        ],
        start_sequence=1,
        end_sequence=4,
    )
    return BoundaryActivityProjection(
        boundary_id="deployment_partnership",
        crossings=[incoming, outgoing],
        episodes=[episode],
    )


def _bundle(run_id: str, fingerprint: str = _DIGEST) -> RunEvidenceBundleConsumerV1:
    event_records = [
        {
            "evidence_ref": f"event:event_{index:06d}",
            "evidence_kind": "causal_event",
            "source_refs": [],
        }
        for index in range(1, 7)
    ]
    return RunEvidenceBundleConsumerV1.model_validate(
        {
            "bundle_version": 1,
            "bundle_id": f"bundle_{run_id}",
            "run_id": run_id,
            "scenario_id": "coordination_decision_v1",
            "scenario_fingerprint": fingerprint,
            "proposal_digest": "e" * 64,
            "evidence_records": [
                *event_records,
                {
                    "evidence_ref": _BOUNDARY_REF,
                    "evidence_kind": "boundary_activity",
                    "source_refs": [
                        item["evidence_ref"] for item in event_records[:5]
                    ],
                },
            ],
            "record_digest": "f" * 64,
        }
    )


def _framework_readouts(run_id: str) -> list[FrameworkReadoutConsumerV1]:
    bundle_id = f"bundle_{run_id}"
    return [
        FrameworkReadoutConsumerV1.model_validate(
            {
                "readout_version": 1,
                "readout_id": f"{framework}_{bundle_id}",
                "framework": framework,
                "analysis_id": analysis_id,
                "bundle_id": bundle_id,
                "bundle_digest": "f" * 64,
                "findings": [
                    {
                        "finding_id": f"{framework}_fixture_finding",
                        "framework": framework,
                        "evidence_refs": ["event:event_000002"],
                        "analysis_id": analysis_id,
                    }
                ],
                "record_digest": "a" * 64,
            }
        )
        for framework, analysis_id in (
            ("waltzman", "waltzman_decision_environment_v1"),
            ("levin", "levin_collective_competence_v1"),
        )
    ]


def _exact_values(
    *, capability_satisfied: bool = True, constraints_satisfied: bool = True
) -> dict[str, JsonValue]:
    return cast(dict[str, JsonValue], {
        "capability_satisfied": capability_satisfied,
        "all_constraints_satisfied": constraints_satisfied,
        "failed_constraint_ids": (
            [] if constraints_satisfied else ["blocking_issue_open"]
        ),
        "terminal_outcome": "scope_reduced",
        "modeled_decision_time": 120,
        "correction_event_pairs": [],
        "recovery": "not_applicable",
        "alternate_routes_used": [],
        "active_partners_retained": list(PERSON_IDS),
        "member_replacements": [],
        "terminal_proposal_denials": 0,
        "input_crossing_count": 1,
        "output_crossing_count": 1,
        "completed_episode_count": 1,
        "in_progress_episode_count": 0,
    })


def _readout(
    row_id: str,
    run_id: str,
    *,
    activity: BoundaryActivityProjection | None = None,
) -> CompositeControlReadout:
    retained = activity or _activity()
    episode = retained.episodes[0]
    return CompositeControlReadout(
        perturbation_id=row_id,
        exact_values=_exact_values(),
        boundary_activity_ref=_BOUNDARY_REF,
        input_crossing_ids=episode.input_crossing_ids,
        output_crossing_ids=[cast(str, episode.output_crossing_id)],
        coordination_episode_ids=[episode.episode_id],
        output_attempt_event_ids=["event_000003"],
        external_result_event_ids=episode.external_result_event_ids,
        terminal_outcome_event_id="event_000006",
        framework_readout_refs=[
            item.readout_id for item in _framework_readouts(run_id)
        ],
        coded_patterns=[
            CompositePatternEvidence(
                pattern_id="unclear",
                direction="unclear",
                explanation="No substantive pattern is asserted by this fixture.",
                source_event_ids=["event_000002"],
                source_trace_ids=["trace:fixture"],
            )
        ],
        source_run_ids=[run_id],
        limitations=["Synthetic contract fixture; no trajectory was run."],
    )


def _matrix() -> tuple[
    CompositeAssaySetup,
    list[CompositeAssayRunRef],
    list[CompositeControlReadout],
    dict[str, CompositeAssayRunEvidence],
]:
    setup = _setup()
    run_refs: list[CompositeAssayRunRef] = []
    readouts: list[CompositeControlReadout] = []
    evidence_by_run: dict[str, CompositeAssayRunEvidence] = {}
    perturbations = {item.perturbation_id: item for item in setup.perturbations}
    for index, row_id in enumerate(setup.row_ids):
        run_id = f"run_assay_{index}"
        run_refs.append(
            CompositeAssayRunRef(
                run_id=run_id,
                perturbation_id=row_id,
                scenario_fingerprint=_DIGEST,
                valid=True,
            )
        )
        activity = _activity()
        readouts.append(_readout(row_id, run_id, activity=activity))
        perturbation = perturbations.get(row_id)
        evidence_by_run[run_id] = CompositeAssayRunEvidence(
            run_id=run_id,
            perturbation_id=row_id,
            scenario_revision=setup.scenario_revision,
            matched_world_fingerprint=setup.matched_world_fingerprint,
            model_policy_fingerprint=setup.model_policy_fingerprint,
            run_control_fingerprint=setup.run_control_fingerprint,
            applied_changed_refs=(
                [] if perturbation is None else perturbation.changed_refs
            ),
            perturbation_application_event_id=(
                "event_000002"
                if perturbation is not None
                and perturbation.application == "scheduled_day_4"
                else None
            ),
            evidence_bundle=_bundle(run_id),
            framework_readouts=_framework_readouts(run_id),
            boundary_activity_ref=_BOUNDARY_REF,
            boundary_activity=activity,
        )
    return setup, run_refs, readouts, evidence_by_run


def test_compiles_all_five_rows_and_validates_synthetic_retained_evidence() -> None:
    setup, run_refs, readouts, evidence_by_run = _matrix()

    validated = validate_composite_assay_evidence(
        setup, run_refs, readouts, evidence_by_run
    )

    assert validated.setup.row_ids == [
        "matched_control",
        "member_replacement",
        "route_interruption",
        "feedback_interruption",
        "external_risk",
    ]
    assert len(validated.run_refs) == len(validated.readouts) == 5
    for evidence in evidence_by_run.values():
        assert {item.framework for item in evidence.framework_readouts} == {
            "waltzman",
            "levin",
        }


def test_unknown_variant_and_out_of_scope_changed_ref_fail_loud() -> None:
    payload = {
        "schema_version": 1,
        "perturbation_id": "bad",
        "family": "component",
        "variant": "invented_variant",
        "application": "initial_condition",
        "changed_refs": ["technical_validation_lead"],
        "matched_control_id": CONTROL_ID,
        "description": "Invalid.",
    }
    with pytest.raises(ValidationError, match="variant"):
        PerturbationSpec.model_validate(payload)

    payload["variant"] = "position_matched_member_replacement"
    payload["changed_refs"] = ["deployment_partnership"]
    with pytest.raises(ValidationError, match="reviewed scope"):
        PerturbationSpec.model_validate(payload)


def test_retained_consumers_ignore_new_fields_without_weakening_invariants() -> None:
    capability_payload = _capability().model_dump(mode="json")
    capability_payload["future_note"] = "ignored"
    assert CompositeCapabilitySpecConsumer.model_validate(
        capability_payload
    ).capability_id == CAPABILITY_ID

    perturbation_payload = _perturbations()[0].model_dump(mode="json")
    perturbation_payload["future_note"] = "ignored"
    assert PerturbationSpecConsumer.model_validate(
        perturbation_payload
    ).variant == "position_matched_member_replacement"

    run_payload = CompositeAssayRunRef(
        run_id="run_consumer",
        perturbation_id=CONTROL_ID,
        scenario_fingerprint=_DIGEST,
        valid=True,
    ).model_dump(mode="json")
    run_payload["future_note"] = "ignored"
    assert CompositeAssayRunRefConsumer.model_validate(run_payload).valid

    readout_payload = _readout(
        CONTROL_ID, "run_assay_0"
    ).model_dump(mode="json")
    readout_payload["future_note"] = "ignored"
    assert CompositeControlReadoutConsumer.model_validate(
        readout_payload
    ).terminal_outcome_event_id == "event_000006"

    run_payload["invalid_reason"] = "cannot accompany valid true"
    with pytest.raises(ValidationError, match="valid run and invalid reason disagree"):
        CompositeAssayRunRefConsumer.model_validate(run_payload)


def test_analytical_boundary_cannot_be_an_executor() -> None:
    payload = _fixture().model_dump(mode="json")
    payload["executable_refs"].append("deployment_partnership")

    with pytest.raises(ValidationError, match="cannot be a scenario executor"):
        CompositeAssayScenarioFixture.model_validate(payload)


def test_missing_control_and_duplicate_run_id_fail_loud() -> None:
    setup, run_refs, readouts, evidence_by_run = _matrix()
    with pytest.raises(CompositeAssayContractError, match="lacks its matched control"):
        validate_composite_assay_evidence(
            setup,
            run_refs[1:],
            readouts[1:],
            {
                key: value
                for key, value in evidence_by_run.items()
                if key != "run_assay_0"
            },
        )

    duplicate = run_refs[1].model_copy(update={"run_id": run_refs[0].run_id})
    with pytest.raises(CompositeAssayContractError, match="run IDs must be unique"):
        validate_composite_assay_evidence(
            setup,
            [run_refs[0], duplicate, *run_refs[2:]],
            readouts,
            evidence_by_run,
        )


def test_fingerprint_and_evidence_version_drift_fail_loud() -> None:
    setup, run_refs, readouts, evidence_by_run = _matrix()
    evidence_by_run["run_assay_2"] = evidence_by_run[
        "run_assay_2"
    ].model_copy(update={"evidence_bundle": _bundle("run_assay_2", "9" * 64)})
    with pytest.raises(
        CompositeAssayContractError, match="scenario fingerprint mismatch"
    ):
        validate_composite_assay_evidence(
            setup, run_refs, readouts, evidence_by_run
        )

    setup, run_refs, readouts, evidence_by_run = _matrix()
    run_refs[2] = run_refs[2].model_copy(update={"evidence_bundle_version": 2})
    with pytest.raises(
        CompositeAssayContractError, match="evidence-bundle version mismatch"
    ):
        validate_composite_assay_evidence(
            setup, run_refs, readouts, evidence_by_run
        )


def test_valid_run_requires_framework_readouts_and_boundary_activity() -> None:
    payload = _matrix()[3]["run_assay_1"].model_dump(mode="json")
    payload["framework_readouts"] = []
    with pytest.raises(ValidationError):
        CompositeAssayRunEvidence.model_validate(payload)

    setup, run_refs, readouts, evidence_by_run = _matrix()
    evidence_by_run["run_assay_1"] = evidence_by_run[
        "run_assay_1"
    ].model_copy(
        update={"boundary_activity_ref": None, "boundary_activity": None}
    )
    with pytest.raises(
        CompositeAssayContractError, match="lacks retained boundary activity"
    ):
        validate_composite_assay_evidence(
            setup, run_refs, readouts, evidence_by_run
        )


def test_boundary_framework_and_event_references_are_exact() -> None:
    setup, run_refs, readouts, evidence_by_run = _matrix()
    readouts[0] = readouts[0].model_copy(
        update={"boundary_activity_ref": "boundary:wrong:activity"}
    )
    with pytest.raises(
        CompositeAssayContractError, match="boundary activity reference mismatch"
    ):
        validate_composite_assay_evidence(
            setup, run_refs, readouts, evidence_by_run
        )

    setup, run_refs, readouts, evidence_by_run = _matrix()
    readouts[0] = readouts[0].model_copy(
        update={"framework_readout_refs": ["waltzman_wrong", "levin_wrong"]}
    )
    with pytest.raises(
        CompositeAssayContractError, match="framework readout references mismatch"
    ):
        validate_composite_assay_evidence(
            setup, run_refs, readouts, evidence_by_run
        )

    setup, run_refs, readouts, evidence_by_run = _matrix()
    readouts[0] = readouts[0].model_copy(
        update={"terminal_outcome_event_id": "event_999999"}
    )
    with pytest.raises(
        CompositeAssayContractError, match="unknown source event"
    ):
        validate_composite_assay_evidence(
            setup, run_refs, readouts, evidence_by_run
        )

    setup, run_refs, readouts, evidence_by_run = _matrix()
    exact_values = dict(readouts[0].exact_values)
    exact_values["alternate_routes_used"] = ["event_999999"]
    readouts[0] = readouts[0].model_copy(update={"exact_values": exact_values})
    with pytest.raises(
        CompositeAssayContractError, match="unknown source event"
    ):
        validate_composite_assay_evidence(
            setup, run_refs, readouts, evidence_by_run
        )


def test_episode_event_outside_source_run_is_rejected() -> None:
    setup, run_refs, readouts, evidence_by_run = _matrix()
    bad_activity = _activity(unknown_episode_event=True)
    evidence_by_run["run_assay_0"] = evidence_by_run[
        "run_assay_0"
    ].model_copy(update={"boundary_activity": bad_activity})
    readouts[0] = _readout(
        CONTROL_ID, "run_assay_0", activity=bad_activity
    )

    with pytest.raises(
        CompositeAssayContractError, match="outside its source run"
    ):
        validate_composite_assay_evidence(
            setup, run_refs, readouts, evidence_by_run
        )


def test_output_attempt_and_terminal_outcome_cannot_be_conflated() -> None:
    payload = _readout(CONTROL_ID, "run_assay_0").model_dump(mode="json")
    payload["output_crossing_ids"] = []
    with pytest.raises(ValidationError, match="requires an outgoing"):
        CompositeControlReadout.model_validate(payload)

    payload = _readout(CONTROL_ID, "run_assay_0").model_dump(mode="json")
    payload["terminal_outcome_event_id"] = "event_000003"
    with pytest.raises(ValidationError, match="must differ"):
        CompositeControlReadout.model_validate(payload)


def test_fast_decision_cannot_pass_with_a_blocking_constraint() -> None:
    payload = _readout(CONTROL_ID, "run_assay_0").model_dump(mode="json")
    payload["exact_values"] = _exact_values(
        capability_satisfied=True,
        constraints_satisfied=False,
    )

    with pytest.raises(ValidationError, match="cannot pass"):
        CompositeControlReadout.model_validate(payload)


def test_producer_contract_rejects_prose_or_time_episode_rederivation() -> None:
    payload = _readout(CONTROL_ID, "run_assay_0").model_dump(mode="json")
    payload["episode_derivation"] = {
        "method": "prose_and_time_proximity",
        "window_seconds": 30,
    }

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        CompositeControlReadout.model_validate(payload)


def test_invalid_runs_remain_visible_but_cannot_have_readouts() -> None:
    setup, run_refs, readouts, evidence_by_run = _matrix()
    run_refs[3] = run_refs[3].model_copy(
        update={"valid": False, "invalid_reason": "scheduled event missing"}
    )

    validated = validate_composite_assay_evidence(
        setup,
        run_refs,
        [item for item in readouts if item.perturbation_id != "feedback_interruption"],
        evidence_by_run,
    )
    assert not validated.run_refs[3].valid
    assert all(
        item.perturbation_id != "feedback_interruption"
        for item in validated.readouts
    )
