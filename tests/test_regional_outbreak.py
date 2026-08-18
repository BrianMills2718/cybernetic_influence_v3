"""Focused exact-plumbing checks for the authentic regional outbreak scenario."""

import json
from typing import Any, cast

import pytest
from pydantic import JsonValue, ValidationError

from cybernetic_influence.active_runtime import (
    ActionIntent,
    ActiveProposal,
    ActiveRuntimeResult,
    ActiveRuntimeSession,
    ActiveStepResult,
    ActiveSystemBinding,
    ActiveSystemInput,
    ScriptedActiveSystem,
    UpdateScheduleDirective,
)
from cybernetic_influence.causal_core.models import ActionAttempt
from cybernetic_influence.scenarios.regional_outbreak import (
    AGENT_IDS,
    CSO_IDS,
    SOURCE_IDS,
    OutbreakAgentConfiguration,
    OutbreakCondition,
    OutbreakFixture,
    RequiredStanceSystem,
    default_outbreak_configuration,
    outbreak_bindings,
    outbreak_fixture,
    outbreak_readout,
    outbreak_resource_commitments,
    outbreak_runtime_config,
    run_outbreak,
)


def _bindings(fixture: OutbreakFixture) -> dict[str, ActiveSystemBinding]:
    bindings: dict[str, ActiveSystemBinding] = {}
    for spec in fixture.active_specs:
        def step(
            item: ActiveSystemInput,
            implementation_id: str = spec.implementation_id,
        ) -> ActiveStepResult:
            active_system_id = item.active_system_id
            private_state = item.private_state
            if active_system_id == "regional_allocation_authority":
                request = json.loads(item.observations[0].apparent_content)
                return ActiveStepResult(
                    proposal=ActiveProposal(
                        active_system_id=active_system_id,
                        implementation_id=implementation_id,
                        private_state=private_state,
                        actions=[
                            ActionIntent(
                                output_port_id="resource_allocation_out",
                                payload=cast(dict[str, JsonValue], {
                                    "commitments": outbreak_resource_commitments([
                                        "alba_mobile_lab", "borin_clinician_roster",
                                        "cyrenia_diagnostic_kits", "cyrenia_protective_equipment",
                                        "darsia_cold_chain_route", "darsia_fuel_lot",
                                    ]),
                                    "manifest_claim_status": "claimed_verified",
                                    "manifest_ref": "scripted-cso-allocation",
                                    "delivery_mode": "cso_stabilization",
                                    "intervention_action_id": request["action_id"],
                                }),
                                public_summary="Committed the CSO-selected resources.",
                            )
                        ],
                        update_schedule=UpdateScheduleDirective(mode="dormant"),
                    )
                )
            if active_system_id in SOURCE_IDS:
                snapshot = json.loads(item.observations[0].apparent_content)
                signal_id = "verify" if snapshot["completed_round"] == 1 else "escalate"
                return ActiveStepResult(
                    proposal=ActiveProposal(
                        active_system_id=active_system_id,
                        implementation_id=implementation_id,
                        private_state=private_state,
                        actions=[
                            ActionIntent(
                                output_port_id=f"{active_system_id}_out",
                                payload={
                                    "signal_id": signal_id,
                                    "rationale": (
                                        "Selected the reviewed development that matches "
                                        "the public coalition feedback."
                                    ),
                                },
                                public_summary="Emitted one bounded external signal.",
                            )
                        ],
                        update_schedule=UpdateScheduleDirective(mode="dormant"),
                    )
                )
            payload: dict[str, JsonValue]
            if active_system_id == "cso_decision_environment_monitor":
                payload = cast(dict[str, JsonValue], {
                    "trust_structure": "conditional",
                    "perceived_risk": "high",
                    "coordination_readiness": "blocked",
                    "evidence": "Most coalition roles require unresolved verification or resources.",
                })
                output_port_id = "cso_detection_out"
            elif active_system_id == "cso_coordination_diagnostician":
                payload = cast(dict[str, JsonValue], {
                    "primary_dimension": "cross_dimension",
                    "mechanism": "incompatible_requirements",
                    "affected_groups": ["alba", "borin", "cyrenia", "darsia"],
                    "rationale": "Several locally valid requirements cannot be met together.",
                })
                output_port_id = "cso_diagnosis_out"
            elif active_system_id == "cso_stabilization_planner":
                payload = cast(dict[str, JsonValue], {
                    "action_id": "cross_domain_compact",
                    "target_dimensions": [
                        "trust_structure",
                        "perceived_risk",
                        "coordination_readiness",
                    ],
                    "rationale": "The diagnosis spans evidence, authority, and resources.",
                })
                output_port_id = "cso_intervention_out"
            else:
                payload = {
                    "decision": "support",
                    "risk": "capacity",
                    "request": "resources",
                    "rationale": "Support depends on an explicit surge allocation.",
                    "coordination_action": "send_message",
                    "coordination_target_ref": (
                        "regional_logistics_coordinator"
                        if active_system_id != "regional_logistics_coordinator"
                        else "alba_operations_lead"
                    ),
                    "coordination_content": "Please confirm the named surge allocation before the next round.",
                }
                output_port_id = f"stance_{active_system_id}_out"
            return ActiveStepResult(
                proposal=ActiveProposal(
                    active_system_id=active_system_id,
                    implementation_id=implementation_id,
                    private_state=private_state,
                    actions=[
                        ActionIntent(
                            output_port_id=output_port_id,
                            payload=payload,
                            public_summary="Submitted a conditional stance.",
                        )
                    ],
                    update_schedule=UpdateScheduleDirective(mode="dormant"),
                )
            )

        implementation = ScriptedActiveSystem(spec.implementation_id, step)
        bindings[spec.active_system_id] = ActiveSystemBinding(
            spec.implementation_id, implementation
        )
    return bindings


def _run(
    condition: OutbreakCondition,
) -> tuple[OutbreakFixture, ActiveRuntimeResult, dict[str, object]]:
    fixture = outbreak_fixture(condition)
    result = run_outbreak(
        fixture,
        _bindings(fixture),
        run_id=f"test_outbreak_{condition}",
        runtime_config=outbreak_runtime_config(
            per_call_budget=0.01,
            per_run_budget=0.1,
        ),
    )
    return fixture, result, outbreak_readout(result)[0]


def test_baseline_runs_the_cross_border_compact_for_three_rounds() -> None:
    fixture, result, readout = _run("baseline")

    assert len(fixture.active_specs) == len(AGENT_IDS) == 26
    assert len(result.attempts) == 3
    assert result.model_calls == 0
    assert readout["rounds_completed"] == 3
    assert readout["outcome"] == "joint_response_approved"
    assert readout["exercise_injects"] == []
    assert readout["stabilization_events"] == []
    messages = cast(list[Any], readout["coordination_messages"])
    assert len(messages) == len(AGENT_IDS) * 3
    assert {
        item["outcome"] for item in messages if item["round"] in {1, 2}
    } == {"delivered"}
    assert {
        item["outcome"] for item in messages if item["round"] == 3
    } == {"expired_at_simulation_horizon"}

    regional_inputs = [
        json.loads(observation.apparent_content)
        for observation in result.core_result.final_state.observations.values()
        if observation.target_entity_id == "regional_logistics_coordinator"
        and observation.apparent_source_ref == "outbreak_decision"
    ]
    assert len(regional_inputs[0]["direct_messages"]) == len(AGENT_IDS) - 1
    assert all(
        "coordination_action" not in stance
        for stance in regional_inputs[0]["stances"].values()
    )
    assert outbreak_runtime_config(
        per_call_budget=0.01, per_run_budget=0.1
    ).max_private_state_bytes == 65_536


def test_exact_checkpoint_fork_can_withhold_one_targets_queued_messages() -> None:
    fixture = outbreak_fixture(
        "responsive_exercise_injects", message_fork_probe=True
    )
    bindings = _bindings(fixture)
    session = ActiveRuntimeSession(
        fixture.scenario,
        fixture.exact_bindings,
        fixture.active_specs,
        bindings,
        run_id="outbreak_message_fork",
        config=outbreak_runtime_config(per_call_budget=0.01, per_run_budget=0.1),
        participant_concurrency=3,
    )
    first = session.next_due_activation()
    assert first is not None and first.logical_time == 0
    session.activate(
        first.active_system_ids,
        logical_time=first.logical_time,
        activation_causes=first.causes,
    )
    sources = session.next_due_activation()
    assert sources is not None and set(sources.active_system_ids) == set(SOURCE_IDS)
    shared = session.checkpoint()

    fork = ActiveRuntimeSession.restore(
        fixture.scenario, fixture.exact_bindings, bindings, shared
    )
    fork.apply_external_action(
        ActionAttempt(
            action_id="withhold_regional_logistics_messages",
            actor_entity_id="message_fork_controller",
            output_port_id="message_fork_control_out",
            payload={
                "mode": "withhold_target",
                "target_ref": "regional_logistics_coordinator",
                "round": 1,
            },
            logical_time=fork.core_state.logical_time,
            public_summary="Withheld queued messages to one recipient in the control fork.",
        )
    )
    branched = fork.checkpoint()
    assert branched.attempts == shared.attempts
    assert branched.core_checkpoint.event_tail_digest != shared.core_checkpoint.event_tail_digest
    messages = branched.core_checkpoint.state.fact(
        "outbreak_decision.coordination_messages"
    ).value
    withheld = [
        item
        for item in cast(list[Any], messages)
        if item["outcome"] == "withheld_by_checkpoint_fork"
    ]
    assert len(withheld) == len(AGENT_IDS) - 1
    assert {item["target_ref"] for item in withheld} == {
        "regional_logistics_coordinator"
    }
    assert ActiveRuntimeSession.restore(
        fixture.scenario, fixture.exact_bindings, bindings, branched
    ).checkpoint() == branched


def test_reviewed_agent_configuration_reaches_private_memory_and_native_policy() -> None:
    default = default_outbreak_configuration()
    changed_agents = [
        agent.model_copy(
            update={
                "mandate": (
                    "You must preserve laboratory continuity before supporting launch."
                    if agent.agent_id == "alba_epidemiologist"
                    else agent.mandate
                ),
                "institutional_context": (
                    "Alba has assigned a protected domestic confirmation reserve."
                    if agent.agent_id == "alba_epidemiologist"
                    else agent.institutional_context
                ),
                "person": (
                    agent.person.model_copy(
                        update={
                            "disposition": "Personally impatient with avoidable delay but unwilling to hide uncertainty.",
                            "memories": [
                                "A previous delayed confirmation allowed a manageable cluster to spread."
                            ],
                            "behavioral_profile": agent.person.behavioral_profile.model_copy(
                                update={
                                    "goals": [
                                        "Avoid both an ungrounded alarm and preventable delay."
                                    ]
                                }
                            ),
                        }
                    )
                    if agent.agent_id == "alba_epidemiologist"
                    else agent.person
                ),
            }
        )
        for agent in default.agents
    ]
    changed = default.model_copy(update={"agents": changed_agents})

    fixture = outbreak_fixture("baseline", configuration=changed)
    spec = next(
        item
        for item in fixture.active_specs
        if item.active_system_id == "alba_epidemiologist"
    )
    memories = [item["content"] for item in cast(list[Any], spec.initial_private_state["memory"])]
    bindings = outbreak_bindings(
        fixture,
        trace_id_prefix="configuration_test",
        model="codex/gpt-5.6-luna",
        reasoning_effort="medium",
    )
    policy = cast(RequiredStanceSystem, bindings["alba_epidemiologist"].implementation).inner

    assert fixture.configuration == changed
    assert changed.person_contract_id == "person_contract_v1"
    assert any("previous delayed confirmation" in item for item in memories)
    assert any("protected domestic confirmation reserve" in item for item in memories)
    assert "preserve laboratory continuity" in policy.persona
    assert "Avoid both an ungrounded alarm" in policy.persona
    assert "Position expectations (institutional oughts" in policy.persona
    assert "do not dictate your judgment" in policy.persona
    assert policy.implementation_id.startswith(
        "native_outbreak_alba_epidemiologist_person_contract_v1"
    )


def test_outbreak_configuration_rejects_a_person_bound_to_another_actor() -> None:
    default = default_outbreak_configuration()
    first = default.agents[0]

    with pytest.raises(ValidationError, match="person identity must match"):
        OutbreakAgentConfiguration.model_validate(
            {
                **first.model_dump(mode="json"),
                "person": {
                    **first.person.model_dump(mode="json"),
                    "entity_id": "borin_epidemiologist",
                },
            }
        )


def test_participant_policy_is_blind_to_experiment_condition() -> None:
    personas: dict[str, str] = {}
    for condition in (
        "baseline",
        "responsive_exercise_injects",
        "capacity_inject_replay_with_stabilization",
        "adaptive_cso_stabilization",
    ):
        fixture = outbreak_fixture(condition)
        bindings = outbreak_bindings(
            fixture,
            trace_id_prefix="condition_blindness_test",
            model="codex/gpt-5.6-terra",
            reasoning_effort="medium",
        )
        personas[condition] = cast(RequiredStanceSystem, bindings["alba_epidemiologist"].implementation).inner.persona

    assert len(set(personas.values())) == 1
    assert "condition label" not in personas["baseline"]
    assert "responsive_exercise_injects" not in personas["baseline"]
    assert "capacity_inject_replay_with_stabilization" not in personas["baseline"]
    assert "adaptive_cso_stabilization" not in personas["baseline"]


def test_responsive_condition_delivers_complete_autonomous_source_bundles() -> None:
    _, result, readout = _run("responsive_exercise_injects")

    assert [attempt.logical_time for attempt in result.attempts] == [0, 1, 2, 3, 4]
    assert [
        set(attempt.declared_active_system_ids) == set(SOURCE_IDS)
        for attempt in result.attempts
    ] == [False, True, False, True, False]

    exercise_injects = cast(list[Any], readout["exercise_injects"])
    assert len(exercise_injects) == len(SOURCE_IDS) * 2
    assert all("pressure_source" in item for item in exercise_injects)
    inject_observations = [
        observation
        for observation in result.core_result.final_state.observations.values()
        if observation.apparent_source_ref == "outbreak_source_delivery"
    ]
    assert len(inject_observations) == len(AGENT_IDS) * 2
    alba_bundles = [
        json.loads(observation.apparent_content)
        for observation in inject_observations
        if observation.target_entity_id == "alba_epidemiologist"
    ]
    round_history = cast(list[Any], readout["round_history"])
    assert [
        bundle["coalition_snapshot"]["stances"] for bundle in alba_bundles
    ] == [round_document["stances"] for round_document in round_history[:2]]
    assert [
        {document["signal_id"] for document in bundle["documents"]}
        for bundle in alba_bundles
    ] == [{"verify"}, {"escalate"}]
    assert {
        document["content"] for document in alba_bundles[0]["documents"]
    }.isdisjoint(
        document["content"] for document in alba_bundles[1]["documents"]
    )


def test_stabilization_adds_one_authoritative_fact_without_replacing_pressure() -> None:
    _, result, readout = _run("capacity_inject_replay_with_stabilization")

    exercise_injects_2 = cast(list[Any], readout["exercise_injects"])
    assert len(exercise_injects_2) == len(SOURCE_IDS) * 2
    stabilization_events = cast(list[Any], readout["stabilization_events"])
    assert stabilization_events == [
        "round_2_verified_minimum_capacity_package"
    ]
    stabilization_observations = [
        observation
        for observation in result.core_result.final_state.observations.values()
        if observation.apparent_source_ref == "outbreak_source_delivery"
        and '"stabilization"' in observation.apparent_content
    ]
    assert len(stabilization_observations) == len(AGENT_IDS)
    normalized_bundles = []
    for observation in stabilization_observations:
        bundle = json.loads(observation.apparent_content)
        bundle.pop("direct_messages")
        normalized_bundles.append(json.dumps(bundle, sort_keys=True))
    assert len(set(normalized_bundles)) == 5
    assert "not a command about your stance" in stabilization_observations[0].apparent_content
    assert "pre-signed activation" not in stabilization_observations[0].apparent_content


def test_adaptive_cso_cell_detects_diagnoses_and_selects_before_round_three() -> None:
    fixture, result, readout = _run("adaptive_cso_stabilization")

    assert len(fixture.active_specs) == len(AGENT_IDS) + len(SOURCE_IDS) + len(CSO_IDS) + 1
    cso_records = cast(list[Any], readout["cso_records"])
    assert [record["stage"] for record in cso_records] == [
        "detection",
        "diagnosis",
        "intervention",
    ]
    assert [record["actor_id"] for record in cso_records] == list(
        CSO_IDS
    )
    assert cso_records[-1]["payload"]["action_id"] == "cross_domain_compact"
    assert cso_records[0]["payload"]["evidence_summary"].startswith(
        "Most coalition roles"
    )
    assert cso_records[1]["payload"]["affected_scope"] == "multiple_groups"
    assert cso_records[2]["payload"]["target_dimension"] == "cross_dimension"
    stabilization_events_2 = cast(list[Any], readout["stabilization_events"])
    assert stabilization_events_2 == ["world_cross_domain_compact"]
    assert [attempt.logical_time for attempt in result.attempts] == [
        *range(8),
        7,
    ]

    final_inputs = [
        json.loads(observation.apparent_content)
        for observation in result.core_result.final_state.observations.values()
        if observation.apparent_source_ref == "regional_allocation_authority"
    ]
    assert len(final_inputs) == len(AGENT_IDS)
    assert {item["document_kind"] for item in final_inputs} == {
        "cso_stabilization_bundle"
    }
    assert {item["intervention"]["action_id"] for item in final_inputs} == {
        "cross_domain_compact"
    }
    assert all("decision" not in item["intervention"] for item in final_inputs)
    assert all("cso_trace" not in item for item in final_inputs)


def test_resource_allocation_moves_conserved_objects_and_publishes_manifest() -> None:
    fixture = outbreak_fixture("baseline", world_resource_probe=True)
    session = ActiveRuntimeSession(
        fixture.scenario,
        fixture.exact_bindings,
        fixture.active_specs,
        _bindings(fixture),
        run_id="outbreak_resource_allocation",
        config=outbreak_runtime_config(per_call_budget=0.01, per_run_budget=0.1),
        participant_concurrency=3,
    )
    step = session.apply_external_action(
        ActionAttempt(
            action_id="verified_partial_allocation",
            actor_entity_id="regional_allocation_authority",
            output_port_id="resource_allocation_out",
            payload=cast(dict[str, JsonValue], {
                "commitments": outbreak_resource_commitments(
                    ["alba_mobile_lab", "borin_clinician_roster"]
                ),
                "manifest_claim_status": "claimed_verified",
                "manifest_ref": "manifest-48h-001",
            }),
            logical_time=0,
            public_summary="Committed two named operational resources.",
        )
    )

    state = session.core_state
    assert "outbreak_resource_allocation" in {
        event.mechanism_id for event in step.events
    }
    assert state.fact("alba_mobile_lab.availability").value == "committed"
    assert state.fact("alba_mobile_lab.assigned_to").value == "Alba domestic confirmation"
    assert state.fact("borin_clinician_roster.availability").value == "committed"
    assert state.fact("cyrenia_diagnostic_kits.availability").value == "available"
    assert state.fact("regional_allocation_manifest.status").value == "verified"
    assert state.fact("regional_allocation_manifest.commitment_ids").value == [
        "alba_mobile_lab",
        "borin_clinician_roster",
    ]
    observations = [
        item
        for item in state.observations.values()
        if item.apparent_source_ref == "regional_allocation_authority"
    ]
    assert len(observations) == len(AGENT_IDS)
    payload = json.loads(observations[0].apparent_content)
    assert payload["manifest"]["verification_status"] == "verified"
    assert {item["resource_id"] for item in payload["resource_commitments"]} == {
        "alba_mobile_lab",
        "borin_clinician_roster",
    }
    assert all(item["audit_status"] == "verified" for item in payload["resource_commitments"])
    assert all(item["availability_window"] for item in payload["resource_commitments"])


def test_contradicted_resource_claim_does_not_move_world_custody() -> None:
    fixture = outbreak_fixture("baseline", world_resource_probe=True)
    session = ActiveRuntimeSession(
        fixture.scenario, fixture.exact_bindings, fixture.active_specs, _bindings(fixture),
        run_id="outbreak_false_resource_claim",
        config=outbreak_runtime_config(per_call_budget=0.01, per_run_budget=0.1),
        participant_concurrency=3,
    )
    session.apply_external_action(
        ActionAttempt(
            action_id="contradicted_allocation_manifest",
            actor_entity_id="regional_allocation_authority",
            output_port_id="resource_allocation_out",
            payload=cast(dict[str, JsonValue], {
                "commitments": outbreak_resource_commitments(
                    ["darsia_fuel_lot"], falsified_ids=frozenset({"darsia_fuel_lot"})
                ),
                "manifest_claim_status": "claimed_verified",
                "manifest_ref": "manifest-false-001",
            }),
            logical_time=0,
            public_summary="Audited a claimed allocation whose evidence was contradicted.",
        )
    )
    state = session.core_state
    assert state.fact("darsia_fuel_lot.availability").value == "available"
    assert state.fact("darsia_fuel_lot.assigned_to").value == "unassigned"
    assert state.fact("regional_allocation_manifest.status").value == "contradicted"
    observations = [
        json.loads(item.apparent_content)
        for item in state.observations.values()
        if item.apparent_source_ref == "regional_allocation_authority"
    ]
    claim = observations[0]["resource_commitments"][0]
    assert claim["claim_status"] == "claimed_verified"
    assert claim["audit_status"] == "contradicted"
    assert claim["audit_mismatch_fields"] == ["custodian_ref"]
    assert claim["world_outcome"] == "claim_rejected_no_custody_change"


def test_no_package_event_changes_no_resource_custody() -> None:
    fixture = outbreak_fixture("baseline", world_resource_probe=True)
    session = ActiveRuntimeSession(
        fixture.scenario, fixture.exact_bindings, fixture.active_specs, _bindings(fixture),
        run_id="outbreak_no_resource_package",
        config=outbreak_runtime_config(per_call_budget=0.01, per_run_budget=0.1),
        participant_concurrency=3,
    )
    step = session.apply_external_action(
        ActionAttempt(
            action_id="no_resource_intervention",
            actor_entity_id="regional_allocation_authority",
            output_port_id="resource_allocation_out",
            payload={
                "commitments": [],
                "manifest_claim_status": "no_package",
                "manifest_ref": "no-package-after-round-two",
            },
            logical_time=0,
            public_summary="No regional resource package was issued.",
        )
    )
    assert "outbreak_resource_allocation" in {event.mechanism_id for event in step.events}
    assert session.core_state.fact("regional_allocation_manifest.status").value == "absent"
    assert all(
        session.core_state.fact(f"{resource_id}.availability").value == "available"
        for resource_id in (
            "alba_mobile_lab", "borin_clinician_roster", "cyrenia_diagnostic_kits",
            "cyrenia_protective_equipment", "darsia_cold_chain_route", "darsia_fuel_lot",
        )
    )
