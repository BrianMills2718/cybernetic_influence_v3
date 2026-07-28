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
    NarrativeParagraph,
    narrate_live_moments,
)


ROOT = Path(__file__).resolve().parents[1]


def narrated_response(
    response_model: type[CausalMomentNarration],
    *,
    concise: str,
    current_event_id: str,
    detailed_event_ids: list[str] | None = None,
) -> CausalMomentNarration:
    """Create a valid dual-level narrator response for focused tests."""
    return response_model(
        concise_narrative=concise,
        concise_source_event_ids=[current_event_id],
        detailed_paragraphs=[
            NarrativeParagraph(
                text="The retained trace records the decision, exact result, and remaining uncertainty.",
                source_event_ids=detailed_event_ids or [current_event_id],
            )
        ],
    )


def test_live_moment_narration_groups_participants_and_cites_current_events(
    tmp_path: Path,
) -> None:
    document = TestClient(create_app(ROOT / "web", tmp_path)).post(
        "/api/runs",
        json={"execution": "scripted"},
    ).json()
    prompts: list[str] = []
    system_prompts: list[str] = []
    call_options: list[dict[str, Any]] = []

    def fake_call(
        _model: str,
        messages: list[dict[str, str]],
        response_model: type[CausalMomentNarration],
        **kwargs: Any,
    ) -> tuple[CausalMomentNarration, object]:
        system_prompts.append(messages[0]["content"])
        prompts.append(messages[1]["content"])
        call_options.append(kwargs)
        source_ids = re.findall(r'"event_id":\s*"([^"]+)"', messages[1]["content"])
        return (
            narrated_response(
                response_model,
                concise=f"Narrated causal moment {len(prompts)}.",
                current_event_id=source_ids[-1],
            ),
            SimpleNamespace(cost=0.01, cost_source="provider_reported"),
        )

    narration = narrate_live_moments(
        document,
        model="test-model",
        trace_id_prefix="run_test",
        reasoning_effort="high",
        structured_call=fake_call,
    )

    assert narration["status"] == "completed"
    retained_moment_count = len(document["moments"])
    assert narration["model_calls"] == retained_moment_count
    assert narration["cost"] == pytest.approx(0.01 * retained_moment_count)
    moments = narration["moments"]
    assert isinstance(moments, list)
    assert moments[0]["source_event_ids"]
    assert moments[0]["narrative_version"] == 2
    assert moments[0]["concise_narrative"] == moments[0]["narrative"]
    assert moments[0]["detailed_paragraphs"]
    assert [moment["causal_time"] for moment in moments] == list(
        range(1, len(moments) + 1)
    )
    assert [moment["causal_timestamp"] for moment in moments] == [
        f"c{index}" for index in range(1, len(moments) + 1)
    ]
    assert any(len(moment["participants"]) > 1 for moment in moments)
    assert "Earlier causal-moment narratives, in order:\n[]" in prompts[0]
    assert "Allowed provenance IDs for this response" in prompts[0]
    assert "Current-moment IDs" in prompts[0]
    assert "Never describe scenario_start as an internal" in prompts[0]
    assert "concise_narrative must be exactly one sentence of at most 240 characters" in prompts[0]
    assert "detailed_paragraphs must contain one to three connected prose paragraphs" in prompts[0]
    assert "never write an event ID" in " ".join(system_prompts[0].split())
    assert "Narrated causal moment 1." in prompts[1]
    assert all(item["max_tokens"] == 640 for item in call_options)
    assert all(item["reasoning_effort"] == "high" for item in call_options)
    calls = narration["calls"]
    assert isinstance(calls, list)
    assert all(item["reasoning_effort"] == "high" for item in calls)
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
            narrated_response(
                response_model,
                concise="This should not be retained as a supported account.",
                current_event_id="event_not_in_this_turn",
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


def test_narrator_reserves_the_full_account_before_any_provider_call(
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
            narrated_response(
                response_model,
                concise="One authorized account.",
                current_event_id=source_ids[-1],
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

    assert calls == 0
    assert narration["status"] == "unavailable"
    assert narration["cost"] == 0.0
    boundary = narration["failure_boundary"]
    assert isinstance(boundary, Mapping)
    assert boundary["kind"] == "budget_preflight"
    assert boundary["required_calls"] == len(document["moments"])
    assert boundary["remaining_authorization"] == pytest.approx(0.025)
    assert boundary["per_call_ceiling"] == 0.02


def test_narrator_checks_its_configured_call_limit_before_provider_calls(
    tmp_path: Path,
) -> None:
    document = TestClient(create_app(ROOT / "web", tmp_path)).post(
        "/api/runs",
        json={"execution": "scripted"},
    ).json()

    narration = narrate_live_moments(
        document,
        model="test-model",
        trace_id_prefix="run_call_limit_test",
        max_calls=1,
        structured_call=lambda *_args, **_kwargs: pytest.fail(
            "preflight must prevent any provider call"
        ),
    )

    assert narration["status"] == "unavailable"
    assert narration["model_calls"] == 0
    boundary = narration["failure_boundary"]
    assert isinstance(boundary, Mapping)
    assert boundary["kind"] == "call_limit_preflight"
    assert boundary["configured_max_calls"] == 1


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
            narrated_response(
                response_model,
                concise="An unexpectedly expensive account.",
                current_event_id=source_ids[-1],
            ),
            SimpleNamespace(cost=0.021, cost_source="provider_reported"),
        )

    narration = narrate_live_moments(
        document,
        model="test-model",
        trace_id_prefix="run_over_ceiling_test",
        max_total_cost=0.74,
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
            narrated_response(
                response_model,
                concise=f"Narrated causal moment {len(prompts)}.",
                current_event_id=source_ids[-1],
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


def test_detailed_narration_can_cite_prior_evidence_but_must_cite_current_evidence(
    tmp_path: Path,
) -> None:
    document = TestClient(create_app(ROOT / "web", tmp_path)).post(
        "/api/runs",
        json={"execution": "scripted"},
    ).json()
    call_number = 0
    first_event_id = ""

    def fake_call(
        _model: str,
        messages: list[dict[str, str]],
        response_model: type[CausalMomentNarration],
        **_kwargs: Any,
    ) -> tuple[CausalMomentNarration, object]:
        nonlocal call_number, first_event_id
        call_number += 1
        source_ids = re.findall(r'"event_id":\s*"([^"]+)"', messages[1]["content"])
        current_event_id = source_ids[-1]
        if call_number == 1:
            first_event_id = current_event_id
        detailed_ids = [current_event_id]
        if call_number > 1:
            detailed_ids.insert(0, first_event_id)
        return (
            narrated_response(
                response_model,
                concise=f"Moment {call_number} has a retained account.",
                current_event_id=current_event_id,
                detailed_event_ids=detailed_ids,
            ),
            SimpleNamespace(cost=0.01, cost_source="provider_reported"),
        )

    narration = narrate_live_moments(
        document,
        model="test-model",
        trace_id_prefix="run_prior_evidence",
        structured_call=fake_call,
    )

    assert narration["status"] == "completed"
    moments = narration["moments"]
    assert isinstance(moments, list)
    assert first_event_id in moments[1]["detailed_paragraphs"][0]["source_event_ids"]


def test_detailed_narration_without_current_evidence_fails_loudly(tmp_path: Path) -> None:
    document = TestClient(create_app(ROOT / "web", tmp_path)).post(
        "/api/runs",
        json={"execution": "scripted"},
    ).json()
    call_number = 0
    first_event_id = ""

    def forged_call(
        _model: str,
        messages: list[dict[str, str]],
        response_model: type[CausalMomentNarration],
        **_kwargs: Any,
    ) -> tuple[CausalMomentNarration, object]:
        nonlocal call_number, first_event_id
        call_number += 1
        source_ids = re.findall(r'"event_id":\s*"([^"]+)"', messages[1]["content"])
        current_event_id = source_ids[-1]
        if call_number == 1:
            first_event_id = current_event_id
        detailed_ids = [current_event_id] if call_number == 1 else [first_event_id]
        return (
            narrated_response(
                response_model,
                concise=f"Moment {call_number} account.",
                current_event_id=current_event_id,
                detailed_event_ids=detailed_ids,
            ),
            SimpleNamespace(cost=0.01, cost_source="provider_reported"),
        )

    narration = narrate_live_moments(
        document,
        model="test-model",
        trace_id_prefix="run_missing_current_evidence",
        structured_call=forged_call,
    )

    assert narration["status"] == "unavailable"
    calls = narration["calls"]
    assert isinstance(calls, list)
    assert isinstance(calls[1], Mapping)
    assert calls[1]["error_type"] == "ValueError"
    assert "did not cite the current causal moment" in str(calls[1]["error_message"])
