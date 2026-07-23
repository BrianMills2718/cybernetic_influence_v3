"""Direct gates for exact mechanics, replay, and protected agent input."""

from __future__ import annotations

from cybernetic_influence.active_runtime.llm import render_llm_prompts
from cybernetic_influence.causal_core.fixtures import authentication_fixture
from cybernetic_influence.causal_core.replay import replay_committed_trajectory
from cybernetic_influence.scenarios.service_desk import (
    run_service_desk,
    service_desk_arm_configurations,
    service_desk_fixture,
    service_desk_personas,
    service_desk_scripted_bindings,
)


def test_exact_authentication_accepts_equality_and_rejects_inequality() -> None:
    accepted = authentication_fixture(candidate="correct_horse_battery").run(
        run_id="authentication_accepted"
    )
    assert accepted.final_state.fact("auth_service.session_active").value is True
    assert accepted.final_state.fact("auth_service.failure_count").value == 0

    denied = authentication_fixture(candidate="wrong").run(
        run_id="authentication_denied"
    )
    assert denied.final_state.fact("auth_service.session_active").value is False
    assert denied.final_state.fact("auth_service.failure_count").value == 1


def test_service_desk_replay_reconstructs_exact_final_state() -> None:
    fixture = service_desk_fixture(
        service_desk_arm_configurations()[0],
        cognition_profile="position_context",
        reasoning_effort="medium",
    )
    result = run_service_desk(
        fixture,
        service_desk_scripted_bindings(fixture),
        run_id="service_desk_replay_gate",
    )
    replayed = replay_committed_trajectory(fixture.scenario, result.core_result)
    assert replayed == result.core_result.final_state


def test_mechanism_credentials_do_not_enter_agent_prompts() -> None:
    fixture = service_desk_fixture(
        service_desk_arm_configurations()[0],
        cognition_profile="position_context",
        reasoning_effort="medium",
    )
    result = run_service_desk(
        fixture,
        service_desk_scripted_bindings(fixture),
        run_id="service_desk_prompt_gate",
    )
    personas = service_desk_personas("position_context")
    for attempt in result.attempts:
        for participant in attempt.participants:
            system, user = render_llm_prompts(
                participant.input,
                persona=personas[participant.requested_active_system_id],
            )
            rendered = system + user
            assert "triager_route_key_17" not in rendered
            assert "supervisor_close_key_17" not in rendered
