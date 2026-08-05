"""Focused exact-plumbing checks for the authentic regional outbreak scenario."""

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
            return ActiveStepResult(
                proposal=ActiveProposal(
                    active_system_id=active_system_id,
                    implementation_id=implementation_id,
                    private_state=private_state,
                    actions=[
                        ActionIntent(
                            output_port_id=f"stance_{active_system_id}_out",
                            payload={
                                "decision": "support",
                                "risk": "capacity",
                                "request": "resources",
                                "rationale": "Support depends on an explicit surge allocation.",
                            },
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


def test_baseline_runs_twelve_autonomous_roles_for_three_rounds() -> None:
    fixture, result, readout = _run("baseline")

    assert len(fixture.active_specs) == len(AGENT_IDS) == 12
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


def test_responsive_condition_selects_declared_injects_from_reported_risk() -> None:
    _, result, readout = _run("responsive_exercise_injects")

    assert readout["exercise_injects"] == [
        "round_1_capacity_conflict",
        "round_2_capacity_conflict",
    ]
    inject_observations = [
        observation
        for observation in result.core_result.final_state.observations.values()
        if observation.apparent_source_ref == "exercise_control"
    ]
    assert len(inject_observations) == 24
    first_round = inject_observations[:12]
    assert len({item.apparent_content for item in first_round}) == 4


def test_stabilization_adds_one_authoritative_fact_without_replacing_pressure() -> None:
    _, result, readout = _run("capacity_inject_replay_with_stabilization")

    assert readout["exercise_injects"] == [
        "round_1_capacity_conflict",
        "round_2_capacity_conflict",
    ]
    assert readout["stabilization_events"] == [
        "round_2_verified_minimum_capacity_package"
    ]
    stabilization_observations = [
        observation
        for observation in result.core_result.final_state.observations.values()
        if observation.apparent_source_ref == "regional_allocation_authority"
    ]
    assert len(stabilization_observations) == 12
    assert len({item.apparent_content for item in stabilization_observations}) == 1
    assert "not a command about which stance" in stabilization_observations[0].apparent_content
