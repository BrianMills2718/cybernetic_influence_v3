"""Gates for sequential, evidence-bound causal-moment narration."""

from __future__ import annotations

from collections.abc import Mapping
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

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
