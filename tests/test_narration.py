"""Gates for sequential, evidence-bound causal-moment narration."""

from __future__ import annotations

from collections.abc import Mapping
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient
import pytest

from cybernetic_influence.api import create_app
from cybernetic_influence.narration import (
    CausalMomentNarration,
    narrate_live_moments,
)


ROOT = Path(__file__).resolve().parents[1]


def test_live_moment_narration_groups_participants_and_cites_current_events(
    tmp_path: Path,
) -> None:
    document = TestClient(create_app(ROOT / "web", tmp_path)).post(
        "/api/runs",
        json={"execution": "scripted"},
    ).json()
    prompts: list[str] = []

    def fake_call(
        _model: str,
        messages: list[dict[str, str]],
        response_model: type[CausalMomentNarration],
        **_kwargs: Any,
    ) -> tuple[CausalMomentNarration, object]:
        prompts.append(messages[1]["content"])
        source_ids = re.findall(r'"event_id":\s*"([^"]+)"', messages[1]["content"])
        return (
            response_model(
                narrative=f"Narrated causal moment {len(prompts)}.",
                source_event_ids=[source_ids[-1]],
            ),
            SimpleNamespace(cost=0.01, cost_source="provider_reported"),
        )

    narration = narrate_live_moments(
        document,
        model="test-model",
        trace_id_prefix="run_test",
        structured_call=fake_call,
    )

    assert narration["status"] == "completed"
    activation_count = len({trace["activation"] for trace in document["traces"]})
    assert narration["model_calls"] == activation_count
    assert narration["cost"] == 0.01 * activation_count
    moments = narration["moments"]
    assert isinstance(moments, list)
    assert moments[0]["source_event_ids"]
    assert any(len(moment["participants"]) > 1 for moment in moments)
    assert "Earlier causal-moment narratives, in order:\n[]" in prompts[0]
    assert "Never describe scenario_start as an internal" in prompts[0]
    assert "at most 600 characters" in prompts[0]
    assert "Narrated causal moment 1." in prompts[1]
    exact_event_ids = {event["event_id"] for event in document["timeline"]}
    assert all(
        set(moment["source_event_ids"]) <= exact_event_ids
        or moment["source_event_ids"] == [f"{moment['activation']}:silence"]
        for moment in moments
    )


def test_narrator_citation_outside_current_moment_is_retained_as_unavailable(
    tmp_path: Path,
) -> None:
    document = TestClient(create_app(ROOT / "web", tmp_path)).post(
        "/api/runs",
        json={"execution": "scripted"},
    ).json()

    def forged_call(
        _model: str,
        _messages: list[dict[str, str]],
        response_model: type[CausalMomentNarration],
        **_kwargs: Any,
    ) -> tuple[CausalMomentNarration, object]:
        return (
            response_model(
                narrative="This should not be retained as a supported account.",
                source_event_ids=["event_not_in_this_turn"],
            ),
            SimpleNamespace(cost=0.01, cost_source="provider_reported"),
        )

    narration = narrate_live_moments(
        document,
        model="test-model",
        trace_id_prefix="run_test",
        structured_call=forged_call,
    )

    assert narration["status"] == "unavailable"
    assert narration["moments"] == []
    calls = narration["calls"]
    assert isinstance(calls, list)
    assert isinstance(calls[0], Mapping)
    assert calls[0]["error_type"] == "ValueError"


def test_narrator_stops_before_call_ceiling_no_longer_fits(
    tmp_path: Path,
) -> None:
    document = TestClient(create_app(ROOT / "web", tmp_path)).post(
        "/api/runs",
        json={"execution": "scripted"},
    ).json()
    calls = 0

    def fake_call(
        _model: str,
        messages: list[dict[str, str]],
        response_model: type[CausalMomentNarration],
        **_kwargs: Any,
    ) -> tuple[CausalMomentNarration, object]:
        nonlocal calls
        calls += 1
        source_ids = re.findall(
            r'"event_id":\s*"([^"]+)"',
            messages[1]["content"],
        )
        return (
            response_model(
                narrative="One authorized account.",
                source_event_ids=[source_ids[-1]],
            ),
            SimpleNamespace(cost=0.01, cost_source="provider_reported"),
        )

    narration = narrate_live_moments(
        document,
        model="test-model",
        trace_id_prefix="run_budget_test",
        max_total_cost=0.025,
        structured_call=fake_call,
    )

    assert calls == 1
    assert narration["status"] == "unavailable"
    assert narration["cost"] == 0.01
    boundary = narration["failure_boundary"]
    assert isinstance(boundary, Mapping)
    assert boundary["kind"] == "budget_exhausted"
    assert boundary["next_moment"] == 2
    assert boundary["remaining_authorization"] == pytest.approx(0.015)
    assert boundary["required_call_ceiling"] == 0.02


def test_narrator_retains_observed_over_ceiling_cost_as_failure(
    tmp_path: Path,
) -> None:
    document = TestClient(create_app(ROOT / "web", tmp_path)).post(
        "/api/runs",
        json={"execution": "scripted"},
    ).json()

    def expensive_call(
        _model: str,
        messages: list[dict[str, str]],
        response_model: type[CausalMomentNarration],
        **_kwargs: Any,
    ) -> tuple[CausalMomentNarration, object]:
        source_ids = re.findall(
            r'"event_id":\s*"([^"]+)"',
            messages[1]["content"],
        )
        return (
            response_model(
                narrative="An unexpectedly expensive account.",
                source_event_ids=[source_ids[-1]],
            ),
            SimpleNamespace(cost=0.021, cost_source="provider_reported"),
        )

    narration = narrate_live_moments(
        document,
        model="test-model",
        trace_id_prefix="run_over_ceiling_test",
        max_total_cost=0.10,
        structured_call=expensive_call,
    )

    assert narration["status"] == "unavailable"
    assert narration["cost"] == 0.021
    calls = narration["calls"]
    assert isinstance(calls, list)
    assert calls[0]["status"] == "failed"
    assert calls[0]["cost"] == 0.021
    assert "exceeds per-call ceiling" in calls[0]["error_message"]


def test_narrator_receives_representation_scope_and_private_update_evidence(
    tmp_path: Path,
) -> None:
    document = TestClient(create_app(ROOT / "web", tmp_path)).post(
        "/api/runs",
        json={
            "scenario": "purchase_payment",
            "arm_id": "settled",
            "execution": "scripted",
        },
    ).json()
    prompts: list[tuple[str, str]] = []

    def fake_call(
        _model: str,
        messages: list[dict[str, str]],
        response_model: type[CausalMomentNarration],
        **_kwargs: Any,
    ) -> tuple[CausalMomentNarration, object]:
        system, user = messages
        prompts.append((system["content"], user["content"]))
        source_ids = re.findall(
            r'"event_id":\s*"([^"]+)"',
            user["content"],
        )
        return (
            response_model(
                narrative=f"Narrated causal moment {len(prompts)}.",
                source_event_ids=[source_ids[-1]],
            ),
            SimpleNamespace(cost=0.01, cost_source="provider_reported"),
        )

    narration = narrate_live_moments(
        document,
        model="test-model",
        trace_id_prefix="run_purchase_narration_test",
        structured_call=fake_call,
    )

    assert narration["status"] == "completed"
    system_prompt = prompts[0][0]
    normalized_system_prompt = " ".join(system_prompt.split())
    rendered_moments = "\n".join(user for _, user in prompts)
    assert (
        "A stipulated or coarse external subsystem must never be called an "
        "exact subsystem"
    ) in normalized_system_prompt
    assert (
        "Never broaden “no external action” into “no process state changed.”"
        in normalized_system_prompt
    )
    assert '"mechanism_kind": "coarse_external_processor"' in rendered_moments
    assert (
        '"representation_abstraction": "Stipulated '
        "instruction-to-status behavior"
    ) in rendered_moments
    assert "Exact mechanism coarse_payment_processor" not in rendered_moments
    assert '"private_state_updated": true' in prompts[-1][1]
    assert (
        "Protected private state changed for ap_clerk."
        in prompts[-1][1]
    )
