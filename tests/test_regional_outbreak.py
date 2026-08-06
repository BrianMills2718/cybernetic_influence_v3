"""Focused exact-plumbing checks for the authentic regional outbreak scenario."""

import json

from cybernetic_influence.active_runtime import (
    ActionIntent,
    ActiveProposal,
    ActiveRuntimeResult,
    ActiveStepResult,
    ActiveSystemBinding,
    ActiveSystemInput,
    ScriptedActiveSystem,
    UpdateScheduleDirective,
)
from cybernetic_influence.scenarios.regional_outbreak import (
    AGENT_IDS,
    CSO_IDS,
    SOURCE_IDS,
    OutbreakCondition,
    OutbreakFixture,
    default_outbreak_configuration,
    outbreak_bindings,
    outbreak_fixture,
    outbreak_readout,
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
            if active_system_id == "cso_decision_environment_monitor":
                payload = {
                    "trust_structure": "conditional",
                    "perceived_risk": "high",
                    "coordination_readiness": "blocked",
                    "evidence": "Most coalition roles require unresolved verification or resources.",
                }
                output_port_id = "cso_detection_out"
            elif active_system_id == "cso_coordination_diagnostician":
                payload = {
                    "primary_dimension": "cross_dimension",
                    "mechanism": "incompatible_requirements",
                    "affected_groups": ["alba", "borin", "cyrenia", "darsia"],
                    "rationale": "Several locally valid requirements cannot be met together.",
                }
                output_port_id = "cso_diagnosis_out"
            elif active_system_id == "cso_stabilization_planner":
                payload = {
                    "action_id": "cross_domain_compact",
                    "target_dimensions": [
                        "trust_structure",
                        "perceived_risk",
                        "coordination_readiness",
                    ],
                    "rationale": "The diagnosis spans evidence, authority, and resources.",
                }
                output_port_id = "cso_intervention_out"
            else:
                payload = {
                    "decision": "support",
                    "risk": "capacity",
                    "request": "resources",
                    "rationale": "Support depends on an explicit surge allocation.",
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
    memory = spec.initial_private_state["memory"][0]["content"]
    bindings = outbreak_bindings(
        fixture,
        trace_id_prefix="configuration_test",
        model="codex/gpt-5.6-luna",
        reasoning_effort="medium",
    )
    policy = bindings["alba_epidemiologist"].implementation.inner

    assert fixture.configuration == changed
    assert "protected domestic confirmation reserve" in memory
    assert "preserve laboratory continuity" in policy.persona
    assert "You are Alba Epidemiologist" in policy.persona


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
        personas[condition] = bindings["alba_epidemiologist"].implementation.inner.persona

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

    assert len(readout["exercise_injects"]) == len(SOURCE_IDS) * 2
    assert all("pressure_source" in item for item in readout["exercise_injects"])
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
    assert [
        bundle["coalition_snapshot"]["stances"] for bundle in alba_bundles
    ] == [round_document["stances"] for round_document in readout["round_history"][:2]]
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

    assert len(readout["exercise_injects"]) == len(SOURCE_IDS) * 2
    assert readout["stabilization_events"] == [
        "round_2_verified_minimum_capacity_package"
    ]
    stabilization_observations = [
        observation
        for observation in result.core_result.final_state.observations.values()
        if observation.apparent_source_ref == "outbreak_source_delivery"
        and '"stabilization"' in observation.apparent_content
    ]
    assert len(stabilization_observations) == len(AGENT_IDS)
    assert len({item.apparent_content for item in stabilization_observations}) == 5
    assert "not a command about your stance" in stabilization_observations[0].apparent_content
    assert "pre-signed activation" not in stabilization_observations[0].apparent_content


def test_adaptive_cso_cell_detects_diagnoses_and_selects_before_round_three() -> None:
    fixture, result, readout = _run("adaptive_cso_stabilization")

    assert len(fixture.active_specs) == len(AGENT_IDS) + len(SOURCE_IDS) + len(CSO_IDS)
    assert [record["stage"] for record in readout["cso_records"]] == [
        "detection",
        "diagnosis",
        "intervention",
    ]
    assert [record["actor_id"] for record in readout["cso_records"]] == list(
        CSO_IDS
    )
    assert readout["cso_records"][-1]["payload"]["action_id"] == "cross_domain_compact"
    assert readout["cso_records"][0]["payload"]["evidence_summary"].startswith(
        "Most coalition roles"
    )
    assert readout["cso_records"][1]["payload"]["affected_scope"] == "multiple_groups"
    assert readout["cso_records"][2]["payload"]["target_dimension"] == "cross_dimension"
    assert readout["stabilization_events"] == ["cso_cross_domain_compact"]
    assert [attempt.logical_time for attempt in result.attempts] == list(range(8))

    final_inputs = [
        json.loads(observation.apparent_content)
        for observation in result.core_result.final_state.observations.values()
        if observation.apparent_source_ref == "cso_stabilization_planner"
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
