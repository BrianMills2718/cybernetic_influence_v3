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
