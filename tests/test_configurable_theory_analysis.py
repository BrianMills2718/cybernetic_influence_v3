"""Slice 24A0 provider-free configuration and dual-readout contract."""

from __future__ import annotations

from typing import Any, cast

import pytest
from pydantic import JsonValue, ValidationError

from cybernetic_influence.active_runtime import ActiveRuntimeResult
from cybernetic_influence.analysis import (
    FrameworkFindingV1,
    FrameworkReadoutConsumerV1,
    RunEvidenceBundleConsumerV1,
    RunEvidenceBundleV1,
    build_levin_reference_readout,
    build_run_evidence_bundle,
    build_waltzman_reference_readout,
    coordination_analysis_specs,
    reference_run_spec,
    validate_readout_against_bundle,
)
from cybernetic_influence.authoring import (
    AuthoringCompilationError,
    CompiledScenario,
    ScenarioDraftProposal,
    compile_scenario,
)
from cybernetic_influence.scenarios.coordination_decision import PERSON_IDS


def _proposal_payload() -> dict[str, object]:
    positions = {
        "mission_coordinator": "Coordinates the partnership decision.",
        "technical_validation_lead": "Assesses technical validation.",
        "sovereignty_policy_representative": "Assesses authority and oversight.",
        "local_public_health_liaison": "Assesses local safety and legitimacy.",
        "partner_representative": "Represents one participating partner.",
    }
    people = [
        {
            "entity_id": person_id,
            "label": person_id.replace("_", " ").title(),
            "position": positions[person_id],
            "disposition": "Conscientious, fallible, and responsive to evidence.",
            "memories": [
                "The partnership is reviewing a bio-surveillance deployment."
            ],
            "behavioral_profile": {
                "values": ["A legitimate and effective public-health decision."],
                "goals": ["Contribute to a valid collective decision."],
                "beliefs": ["Other participants may hold relevant information."],
                "decision_tendencies": [
                    "Seeks clarification when material uncertainty is salient."
                ],
                "social_perceptions": [
                    "The partnership expects reasons for changed commitments."
                ],
                "current_state": ["Prepared for the first review meeting."],
                "capabilities": ["Can use the interfaces assigned to this position."],
                "limitations": ["Cannot observe undelivered information."],
            },
        }
        for person_id in PERSON_IDS
    ]
    return {
        "proposal_version": 1,
        "scenario_id": "authored_biosurveillance_decision",
        "title": "Multinational bio-surveillance deployment review",
        "description": (
            "Five people decide whether and how to deploy a shared "
            "bio-surveillance capability."
        ),
        "people": people,
        "objects": [
            {
                "entity_id": "technical_pressure_source",
                "entity_kind": "source_process",
                "label": "Independent technical source",
                "description": "Publishes a bounded calibration concern.",
            },
            {
                "entity_id": "policy_pressure_source",
                "entity_kind": "source_process",
                "label": "Sovereignty source",
                "description": "Publishes a bounded oversight concern.",
            },
            {
                "entity_id": "local_pressure_source",
                "entity_kind": "source_process",
                "label": "Local health source",
                "description": "Publishes a bounded local safety concern.",
            },
        ],
        "information": [
            {
                "information_id": "technical_concern",
                "label": "calibration_uncertainty",
                "content": "Independent calibration may be insufficient.",
            },
            {
                "information_id": "policy_concern",
                "label": "sovereignty_and_transparency",
                "content": "Deployment may weaken local oversight authority.",
            },
            {
                "information_id": "local_concern",
                "label": "local_safety_and_legitimacy",
                "content": "Deployment may create locally unacceptable safety risk.",
            },
        ],
        "places": [
            {
                "place_id": "coordination_world",
                "label": "Coordination world",
                "description": "Spatial root for the reviewed decision.",
            },
            {
                "place_id": "partnership_hub",
                "label": "Partnership hub",
                "description": "Shared location for the partnership meetings.",
            },
            {
                "place_id": "source_operations_site",
                "label": "Source operations site",
                "description": "Location of the three concrete source processes.",
            },
            {
                "place_id": "external_registry_site",
                "label": "External registry site",
                "description": "Location of the external decision registry.",
            },
        ],
        "spatial_links": [
            {
                "spatial_link_id": "partnership_source_network_path",
                "endpoint_a_place_id": "partnership_hub",
                "endpoint_b_place_id": "source_operations_site",
                "description": "Physical-network adjacency to source operations.",
            },
            {
                "spatial_link_id": "partnership_registry_network_path",
                "endpoint_a_place_id": "partnership_hub",
                "endpoint_b_place_id": "external_registry_site",
                "description": "Physical-network adjacency to the registry.",
            },
        ],
        "placements": cast(dict[str, object], {
            **{person_id: "partnership_hub" for person_id in PERSON_IDS},
            "technical_pressure_source": "source_operations_site",
            "policy_pressure_source": "source_operations_site",
            "local_pressure_source": "source_operations_site",
        }),
        "timing_assumptions": [
            {
                "name": "technical_source_route_delivery",
                "minutes": 90,
                "basis": "Reviewed synthetic timing assumption.",
            },
            {
                "name": "policy_source_route_delivery",
                "minutes": 120,
                "basis": "Reviewed synthetic timing assumption.",
            },
            {
                "name": "local_source_route_delivery",
                "minutes": 150,
                "basis": "Reviewed synthetic timing assumption.",
            },
        ],
        "workflow": {
            "template_id": "coordination_decision_v1",
            "condition": "stabilization",
            "collective_goal": {
                "goal_id": "partnership_decision_goal",
                "label": "Reach a legitimate deployment decision",
                "description": (
                    "Reach a reviewed deployment decision by the deadline while "
                    "respecting technical, sovereignty, and safety constraints."
                ),
                "acceptable_outcomes": [
                    "deploy_on_time",
                    "scope_reduced",
                    "delayed",
                ],
                "constraints": [
                    "No blocking issue may remain open.",
                    "Active partners must support the selected scope.",
                ],
            },
            "meeting_days": [0, 1, 2, 3],
            "deadline_day": 4,
            "terminal_outcomes": [
                "deploy_on_time",
                "delayed",
                "scope_reduced",
                "partner_disengaged",
                "no_decision_by_horizon",
            ],
            "messages": [
                {
                    "message_id": "technical_pressure_message",
                    "information_id": "technical_concern",
                    "source_id": "technical_pressure_source",
                    "recipient_id": "technical_validation_lead",
                    "route_id": "technical_source_route",
                    "representation_kind": "source_message",
                    "delivery_minutes": 90,
                },
                {
                    "message_id": "policy_pressure_message",
                    "information_id": "policy_concern",
                    "source_id": "policy_pressure_source",
                    "recipient_id": "sovereignty_policy_representative",
                    "route_id": "policy_source_route",
                    "representation_kind": "source_message",
                    "delivery_minutes": 120,
                },
                {
                    "message_id": "local_pressure_message",
                    "information_id": "local_concern",
                    "source_id": "local_pressure_source",
                    "recipient_id": "local_public_health_liaison",
                    "route_id": "local_source_route",
                    "representation_kind": "source_message",
                    "delivery_minutes": 150,
                },
            ],
            "stabilizing_resources": [
                "authoritative_validation",
                "evidence_based_risk_admission",
                "uncertainty_bounds",
                "commitment_feedback",
            ],
            "analysis": {
                "analysis_ids": [
                    "waltzman_decision_environment_v1",
                    "levin_collective_competence_v1",
                ],
                "candidate_boundary_ref": "deployment_partnership",
                "candidate_goal_ref": "partnership_decision_goal",
            },
            "assumptions": [
                "The reviewed exact mechanisms adequately represent the bounded decision procedure."
            ],
            "known_omissions": [
                "The scenario does not model the full institutions or software behind the partnership."
            ],
        },
        "analytical_boundaries": [
            {
                "boundary_id": "deployment_partnership",
                "label": "Deployment partnership",
                "description": "Analytical view over the five people and their coordination substrate.",
                "member_refs": [
                    *PERSON_IDS,
                    "partnership_decision_goal",
                ],
            },
            {
                "boundary_id": "pressure_source_ensemble",
                "label": "Concern sources",
                "description": "Analytical view over three concrete source processes.",
                "member_refs": [
                    "technical_pressure_source",
                    "policy_pressure_source",
                    "local_pressure_source",
                ],
            },
        ],
        "fidelity_questions": [
            "Did people use only retained memory and delivered observations?",
            "Did the exact decision gate enforce the reviewed constraints?",
        ],
        "unresolved_questions": [],
    }


def _compiled_reference() -> tuple[CompiledScenario, ActiveRuntimeResult, RunEvidenceBundleV1]:
    proposal = ScenarioDraftProposal.model_validate(_proposal_payload())
    compiled = compile_scenario(proposal)
    result = compiled.run_scripted(run_id="run_configured_theory")
    workflow = proposal.workflow
    assert workflow.template_id == "coordination_decision_v1"
    specs = coordination_analysis_specs(
        boundary_ref=workflow.analysis.candidate_boundary_ref,
        goal_ref=workflow.analysis.candidate_goal_ref,
    )
    run_spec = reference_run_spec(
        run_id=result.run_id,
        horizon_minutes=4 * 24 * 60,
    )
    bundle = build_run_evidence_bundle(
        compiled,
        result,
        run_spec=run_spec,
        analysis_specs=specs,
    )
    return compiled, result, bundle


def test_configured_coordination_compiles_runs_and_produces_dual_readouts() -> None:
    compiled, result, bundle = _compiled_reference()
    state = compiled.scenario.initial_state
    waltzman = build_waltzman_reference_readout(bundle, result)
    levin = build_levin_reference_readout(bundle, result)

    assert compiled.proposal.workflow.template_id == "coordination_decision_v1"
    assert compiled.scenario.description.startswith("Five people decide")
    assert (
        cast(dict[str, Any], state.entities["mission_coordinator"].attributes["assumptions"].value)[
            "position"
        ]
        == "Coordinates the partnership decision."
    )
    assert "partnership_decision_goal" in state.entities
    assert state.connections["technical_source_route"].delay == 90
    assert "Independent calibration may be insufficient" in state.representations[
        "technical_pressure_message"
    ].content
    assert result.model_calls == 0
    assert result.total_observed_cost == 0.0
    assert result.completion is not None
    assert result.completion.reason == "terminal_condition_met"
    workflow_spec = cast(dict[str, Any], bundle.scenario_spec["workflow"])
    assert workflow_spec["template_id"] == (
        "coordination_decision_v1"
    )
    assert {item.framework for item in bundle.analysis_specs} == {
        "waltzman",
        "levin",
    }
    assert len(waltzman.findings) == 16
    assert any(
        item.finding_id == "waltzman_authority_divergence_scope"
        and cast(dict[str, Any], item.value)["status"] == "not_computed"
        for item in waltzman.findings
    )
    assert any(
        item.construct_id == "candidate_collective_goal" for item in levin.findings
    )
    assert any(
        item.construct_id == "unobserved_agency_dimensions"
        and cast(dict[str, Any], item.value)["robustness"] == "not_tested"
        for item in levin.findings
    )
    validate_readout_against_bundle(waltzman, bundle)
    validate_readout_against_bundle(levin, bundle)


def test_evidence_bundle_consumer_tolerates_additive_fields_without_losing_refs() -> None:
    _, result, bundle = _compiled_reference()
    payload = bundle.model_dump(mode="json")
    payload["future_bundle_field"] = {"new": "value"}
    payload["evidence_records"][0]["future_record_field"] = True

    reopened = RunEvidenceBundleConsumerV1.model_validate(payload)

    assert reopened.bundle_id == bundle.bundle_id
    assert reopened.record_digest == bundle.record_digest

    readout_payload = build_levin_reference_readout(
        bundle, result
    ).model_dump(mode="json")
    readout_payload["future_readout_field"] = "retained"
    readout_payload["findings"][0]["future_finding_field"] = 1
    reopened_readout = FrameworkReadoutConsumerV1.model_validate(readout_payload)

    assert reopened_readout.bundle_id == bundle.bundle_id


def test_missing_candidate_goal_fails_typed_authoring() -> None:
    payload = _proposal_payload()
    workflow = cast(dict[str, Any], payload["workflow"])
    del workflow["collective_goal"]

    with pytest.raises(ValidationError, match="collective_goal"):
        ScenarioDraftProposal.model_validate(payload)


def test_unknown_terminal_outcome_fails_typed_authoring() -> None:
    payload = _proposal_payload()
    workflow = cast(dict[str, Any], payload["workflow"])
    terminal_outcomes = cast(list[Any], workflow["terminal_outcomes"])
    terminal_outcomes[0] = "whatever_the_coordinator_wants"

    with pytest.raises(ValidationError, match="literal"):
        ScenarioDraftProposal.model_validate(payload)


def test_collective_goal_cannot_count_every_terminal_outcome_as_success() -> None:
    payload = _proposal_payload()
    workflow = payload["workflow"]
    assert isinstance(workflow, dict)
    workflow["collective_goal"]["acceptable_outcomes"] = list(
        workflow["terminal_outcomes"]
    )
    proposal = ScenarioDraftProposal.model_validate(payload)

    with pytest.raises(
        AuthoringCompilationError,
        match="must distinguish goal-satisfying outcomes",
    ):
        compile_scenario(proposal)


@pytest.mark.parametrize("mutation", ["source", "recipient", "route"])
def test_incompatible_message_referents_fail_compilation(mutation: str) -> None:
    payload = _proposal_payload()
    workflow = cast(dict[str, Any], payload["workflow"])
    messages = cast(list[Any], workflow["messages"])
    message = cast(dict[str, Any], messages[0])
    if mutation == "source":
        message["source_id"] = "policy_pressure_source"
    elif mutation == "recipient":
        message["recipient_id"] = "mission_coordinator"
    else:
        message["route_id"] = "policy_source_route"
    proposal = ScenarioDraftProposal.model_validate(payload)

    with pytest.raises(AuthoringCompilationError, match="incompatible"):
        compile_scenario(proposal)


@pytest.mark.parametrize("mutation", ["boundary", "goal"])
def test_analysis_reference_outside_configuration_fails(mutation: str) -> None:
    payload = _proposal_payload()
    workflow = cast(dict[str, Any], payload["workflow"])
    analysis = cast(dict[str, Any], workflow["analysis"])
    if mutation == "boundary":
        analysis["candidate_boundary_ref"] = "unknown_boundary"
    else:
        analysis["candidate_goal_ref"] = "unknown_goal"
    proposal = ScenarioDraftProposal.model_validate(payload)

    with pytest.raises(AuthoringCompilationError, match="outside"):
        compile_scenario(proposal)


def test_organization_executor_fails_compilation() -> None:
    payload = _proposal_payload()
    objects = cast(list[Any], payload["objects"])
    objects.append(
        {
            "entity_id": "partnership_executor",
            "entity_kind": "organization_executor",
            "label": "Organization mind",
            "description": "Improper aggregate executor.",
        }
    )
    proposal = ScenarioDraftProposal.model_validate(payload)

    with pytest.raises(AuthoringCompilationError, match="cannot be a world executor"):
        compile_scenario(proposal)


def test_invented_mechanism_implementation_is_not_in_the_schema() -> None:
    payload = _proposal_payload()
    workflow = cast(dict[str, Any], payload["workflow"])
    workflow["mechanism_implementation"] = "generated_python_handler"

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ScenarioDraftProposal.model_validate(payload)


def test_corrupt_finding_reference_fails_without_invalidating_run() -> None:
    _, result, bundle = _compiled_reference()
    readout = build_levin_reference_readout(bundle, result)
    corrupt_finding = readout.findings[0].model_copy(
        update={"evidence_refs": ["event:event_999999"]}
    )
    corrupt = readout.model_copy(
        update={"findings": [corrupt_finding, *readout.findings[1:]]}
    )

    with pytest.raises(ValueError, match="unknown evidence"):
        validate_readout_against_bundle(corrupt, bundle)
    assert result.status == "completed"


def test_narrator_prose_cannot_be_measurement_evidence() -> None:
    _, result, bundle = _compiled_reference()
    payload = bundle.model_dump(mode="json")
    payload["evidence_records"].append(
        {
            "evidence_ref": "narrative:moment_1",
            "evidence_kind": "narrative",
            "summary": "A narrator's prose.",
            "source_refs": [],
            "payload": {"text": "This is presentation, not source truth."},
        }
    )

    with pytest.raises(ValidationError, match="evidence_kind"):
        RunEvidenceBundleV1.model_validate(payload)

    readout = build_waltzman_reference_readout(bundle, result)
    narrative_finding = FrameworkFindingV1(
        finding_id="waltzman_narrative_claim",
        framework="waltzman",
        construct_id="trust_structure",
        method_class="llm_coded",
        value="unsupported",
        evidence_refs=["narrative:moment_1"],
        uncertainty="Unsupported.",
        limitations=["Narrative is not source evidence."],
        analysis_id="waltzman_decision_environment_v1",
    )
    corrupt = readout.model_copy(update={"findings": [narrative_finding]})
    with pytest.raises(ValueError, match="unknown evidence"):
        validate_readout_against_bundle(corrupt, bundle)


def test_authored_proposal_rejects_analysis_no_run_can_satisfy() -> None:
    """An unsatisfiable requirement must fail where it is authored.

    "boundary_activity" is a declared EvidenceKind that no execution path emits.
    An authored analysis asked for it, so its lens reported itself unsupported
    on a run that was perfectly good -- which reads to the analyst as their
    simulation being deficient rather than as a request that could never have
    been satisfied by any run at all.

    The check belongs on the model's proposal, not on AnalysisSpecV2. Putting it
    on the spec made every already-retained draft holding such an analysis fail
    to parse, so saved work became unopenable: a new invariant governs what may
    be created, never what is already on disk. Both halves are asserted here.
    """
    from cybernetic_influence.analysis.theory_analysis import (
        RETAINABLE_EVIDENCE_KINDS,
        AnalysisSpecV2,
    )

    assert "boundary_activity" not in RETAINABLE_EVIDENCE_KINDS

    spec_fields = {
        "analysis_id": "probe_analysis",
        "profile": "waltzman_coordination_v1",
        "purpose": "purpose",
        "construct_definitions": ["construct"],
        "method_classes": ["exact"],
        "aggregation": "aggregation",
        "uncertainty": "uncertainty",
        "limitations": ["limitation"],
    }

    # Retained data keeps loading: the spec itself accepts the historical value.
    retained = AnalysisSpecV2(
        required_evidence_kinds=["configuration", "boundary_activity"],
        **cast(Any, spec_fields),
    )
    assert "boundary_activity" in retained.required_evidence_kinds


def test_activation_rows_read_split_assimilation_and_intent_calls() -> None:
    """The runtime's two-call actor shape must reach the analysis.

    Originally one model call produced a combined decision carrying both
    `assimilation` and `intent`. The runtime now issues two calls per actor and
    retains each as its own record. Reading only the combined shape skipped
    every record of both new shapes, so a run holding 32 retained activations
    produced no rows and every coordination measure reported zero -- "0 of 0
    people", "no typed participant activations were available" -- on a run where
    four people deliberated across four moments and committed seven operations.

    One row per acting person per moment: the standalone assimilation record's
    content reaches the analysis through the intent it fed, and emitting both
    would double-count a person who acted once.
    """
    from cybernetic_influence.analysis.theory_analysis import EvidenceRecordV1
    from cybernetic_influence.general_simulation.analysis_service import (
        _activation_rows,
    )

    actor_context: dict[str, JsonValue] = {
        "actor_id": "mara_ellis",
        "base_revision": 0,
        "current_minute": 15,
    }
    assimilation_record = EvidenceRecordV1(
        evidence_ref="call:1:actor",
        evidence_kind="participant_activation",
        summary="assimilation",
        payload={
            "input_context": {"actor_context": actor_context},
            "structured_output": {
                "attended_observation_ids": ["observation_1"],
                "interpretation": "The bridge defect is unconfirmed.",
                "memory_additions": [],
                "memory_revisions": [],
                "provenance_links": ["record_1"],
            },
        },
    )
    intent_record = EvidenceRecordV1(
        evidence_ref="call:2:actor",
        evidence_kind="participant_activation",
        summary="intent",
        payload={
            "input_context": {
                "actor_context": actor_context,
                "retained_assimilation": {
                    "attended_observation_ids": ["observation_1"],
                    "interpretation": "The bridge defect is unconfirmed.",
                    "provenance_links": ["record_1"],
                },
            },
            "structured_output": {
                "actor_id": "mara_ellis",
                "base_revision": 0,
                "intent_id": "intent_mara_ellis_0",
                "action": "Defer dispatch until the defect is confirmed.",
                "purpose": "Avoid unsafe infrastructure.",
                "expected_effect": "No cargo movement this moment.",
                "target_refs": ["damaged_bridge_record"],
                "transition_contract_ids": ["bridge_defect_sensing_contract"],
            },
        },
    )

    rows = _activation_rows([assimilation_record, intent_record])

    assert len(rows) == 1, "one acting person at one moment is one row"
    row = rows[0]
    assert row["actor_id"] == "mara_ellis"
    assert row["moment"] == 15
    assert row["target_refs"] == ["damaged_bridge_record"]
    assert row["transition_contract_ids"] == ["bridge_defect_sensing_contract"]
    # The assimilation the intent was given must reach the text the lens reads.
    assert "bridge defect is unconfirmed" in cast(str, row["text"])
    assert "defer dispatch" in cast(str, row["intent_text"])
    assert row["attended_observation_ids"] == ["observation_1"]


def test_evasion_arm_differs_from_the_overt_arm_only_in_source_expression() -> None:
    """The detector under test must be identical across the two arms.

    The comparison the evasion case makes is that the same directional pressure,
    shaped to stay inside ordinary variation, is not seen by a detector that saw
    it when it was overt. That claim is only worth anything if the detector, its
    thresholds and its trigger are the same in both arms -- otherwise the result
    is about the detector being changed, which is not interesting.

    So: the monitor, diagnostician and planner personas must match exactly, and
    the source personas must not.
    """
    from cybernetic_influence.scenarios.regional_outbreak import (
        SOURCE_IDS,
        _cso_policy,
        _source_policy,
    )

    cso_ids = (
        "cso_decision_environment_monitor",
        "cso_coordination_diagnostician",
        "cso_stabilization_planner",
    )
    for cso_id in cso_ids:
        overt = _cso_policy(
            cso_id, model="m", reasoning_effort=None, trace_id_prefix="t"
        )
        evasion = _cso_policy(
            cso_id, model="m", reasoning_effort=None, trace_id_prefix="t"
        )
        assert overt.persona == evasion.persona, (
            f"{cso_id} must be identical in both arms or the comparison is void"
        )

    for source_id in SOURCE_IDS:
        overt = _source_policy(
            source_id, model="m", reasoning_effort=None, trace_id_prefix="t"
        )
        evasion = _source_policy(
            source_id,
            model="m",
            reasoning_effort=None,
            trace_id_prefix="t",
            threshold_managed=True,
        )
        assert overt.persona != evasion.persona
        # The evasion arm constrains how pressure is expressed, never how much
        # the source wants. It must not be told to escalate, and must not be
        # told to be less effective.
        assert "Always choose verify" in evasion.persona
        assert "Never choose escalate" in evasion.persona
        assert "escalate for a concrete external incompatibility" in overt.persona
