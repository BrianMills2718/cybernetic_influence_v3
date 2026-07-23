"""Gates for sequential, evidence-bound live turn narration."""

from __future__ import annotations

from collections.abc import Mapping
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

from cybernetic_influence.api import create_app
from cybernetic_influence.narration import TurnNarration, narrate_live_turns


ROOT = Path(__file__).resolve().parents[1]


def test_live_turn_narration_chains_prior_accounts_and_cites_current_events(
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
        response_model: type[TurnNarration],
        **_kwargs: Any,
    ) -> tuple[TurnNarration, object]:
        prompts.append(messages[1]["content"])
        source_ids = re.findall(r'"event_id":\s*"([^"]+)"', messages[1]["content"])
        return (
            response_model(
                narrative=f"Narrated activation {len(prompts)}.",
                source_event_ids=[source_ids[-1]],
            ),
            SimpleNamespace(cost=0.01, cost_source="provider_reported"),
        )

    narration = narrate_live_turns(
        document,
        model="test-model",
        trace_id_prefix="run_test",
        structured_call=fake_call,
    )

    assert narration["status"] == "completed"
    assert narration["model_calls"] == len(document["traces"])
    assert narration["cost"] == 0.01 * len(document["traces"])
    turns = narration["turns"]
    assert isinstance(turns, list)
    assert turns[0]["source_event_ids"]
    assert "Earlier turn narratives, in order:\n[]" in prompts[0]
    assert "Narrated activation 1." in prompts[1]
    exact_event_ids = {event["event_id"] for event in document["timeline"]}
    assert all(
        set(turn["source_event_ids"]) <= exact_event_ids
        or turn["source_event_ids"] == [f"{turn['activation']}:silence"]
        for turn in turns
    )


def test_narrator_citation_outside_the_current_turn_is_retained_as_unavailable(
    tmp_path: Path,
) -> None:
    document = TestClient(create_app(ROOT / "web", tmp_path)).post(
        "/api/runs",
        json={"execution": "scripted"},
    ).json()

    def forged_call(
        _model: str,
        _messages: list[dict[str, str]],
        response_model: type[TurnNarration],
        **_kwargs: Any,
    ) -> tuple[TurnNarration, object]:
        return (
            response_model(
                narrative="This should not be retained as a supported account.",
                source_event_ids=["event_not_in_this_turn"],
            ),
            SimpleNamespace(cost=0.01, cost_source="provider_reported"),
        )

    narration = narrate_live_turns(
        document,
        model="test-model",
        trace_id_prefix="run_test",
        structured_call=forged_call,
    )

    assert narration["status"] == "unavailable"
    assert narration["turns"] == []
    calls = narration["calls"]
    assert isinstance(calls, list)
    assert isinstance(calls[0], Mapping)
    assert calls[0]["error_type"] == "ValueError"
