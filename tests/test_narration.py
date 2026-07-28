"""Gates for sequential, evidence-bound causal-moment narration."""

from __future__ import annotations

from collections.abc import Mapping
import json
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
    validate_retained_narration,
)
from cybernetic_influence.run_store import RunStore


ROOT = Path(__file__).resolve().parents[1]


def narrated_response(
    response_model: type[CausalMomentNarration],
    *,
    concise: str,
    current_event_id: str | None = None,
    detailed_event_ids: list[str] | None = None,
) -> CausalMomentNarration:
    """Create a valid prose-only narrator response for focused tests."""
    del current_event_id, detailed_event_ids
    return response_model(
        concise_narrative=concise,
        detailed_paragraphs=[
            NarrativeParagraph(
                text="The retained trace records the decision, exact result, and remaining uncertainty.",
            )
        ],
    )


def test_live_moment_narration_groups_participants_and_retains_simulator_owned_context(
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
    assert moments[0]["narrative_version"] == 3
    assert moments[0]["concise_narrative"] == moments[0]["narrative"]
    assert moments[0]["detailed_paragraphs"]
    assert "source_event_ids" not in moments[0]
    first_context = moments[0]["evidence_context"]
    expected_first_event_ids = [
        event["event_id"]
        for event in document["timeline"]
        if event.get("activation") == moments[0]["activation"]
    ]
    assert first_context["current_event_ids"] == expected_first_event_ids
    assert first_context["prior_narrative_record_ids"] == []
    second_context = moments[1]["evidence_context"]
    assert second_context["prior_narrative_record_ids"] == [
        moments[0]["narrative_record_id"]
    ]
    assert all(
        paragraph["evidence_context_id"] == first_context["context_id"]
        for paragraph in moments[0]["detailed_paragraphs"]
    )
    assert [moment["causal_time"] for moment in moments] == list(
        range(1, len(moments) + 1)
    )
    assert [moment["causal_timestamp"] for moment in moments] == [
        f"c{index}" for index in range(1, len(moments) + 1)
    ]
    assert any(len(moment["participants"]) > 1 for moment in moments)
    assert "Earlier causal-moment narratives, in order:\n[]" in prompts[0]
    assert "Never describe scenario_start as an internal" in prompts[0]
    assert "concise_narrative must be exactly one sentence of at most 240 characters" in prompts[0]
    assert "detailed_paragraphs must contain one to three connected prose paragraphs" in prompts[0]
    assert "never write an event id" in " ".join(system_prompts[0].split()).lower()
    assert "Narrated causal moment 1." in prompts[1]
    assert all(item["max_tokens"] == 640 for item in call_options)
    assert all(item["reasoning_effort"] == "high" for item in call_options)
    calls = narration["calls"]
    assert isinstance(calls, list)
    assert all(item["reasoning_effort"] == "high" for item in calls)
    assert "source_event_ids" not in prompts[0]


def test_narrator_rejects_a_model_selected_provenance_field(
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
    ) -> tuple[object, object]:
        return (
            {
                "concise_narrative": "This should not be retained as a supported account.",
                "concise_source_event_ids": ["event_not_in_this_turn"],
                "detailed_paragraphs": [
                    {"text": "The model must not select provenance identifiers."}
                ],
            },
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
    assert calls[0]["error_type"] == "ValidationError"


def test_narrator_rejects_missing_detailed_paragraphs(tmp_path: Path) -> None:
    document = TestClient(create_app(ROOT / "web", tmp_path)).post(
        "/api/runs",
        json={"execution": "scripted"},
    ).json()

    def malformed_call(
        _model: str,
        _messages: list[dict[str, str]],
        response_model: type[CausalMomentNarration],
        **_kwargs: Any,
    ) -> tuple[object, object]:
        del response_model
        return (
            {"concise_narrative": "A malformed account omitted its detailed prose."},
            SimpleNamespace(cost=0.01, cost_source="provider_reported"),
        )

    narration = narrate_live_moments(
        document,
        model="test-model",
        trace_id_prefix="run_missing_paragraphs",
        structured_call=malformed_call,
    )
    assert narration["status"] == "unavailable"
    assert narration["moments"] == []
    assert narration["calls"][0]["error_type"] == "ValidationError"


def test_narrator_retains_partial_provider_failure_as_unavailable(tmp_path: Path) -> None:
    document = TestClient(create_app(ROOT / "web", tmp_path)).post(
        "/api/runs",
        json={"execution": "scripted"},
    ).json()
    call_number = 0

    def partial_call(
        _model: str,
        _messages: list[dict[str, str]],
        response_model: type[CausalMomentNarration],
        **_kwargs: Any,
    ) -> tuple[CausalMomentNarration, object]:
        nonlocal call_number
        call_number += 1
        if call_number == 2:
            raise RuntimeError("provider stopped after the first retained account")
        return (
            narrated_response(
                response_model,
                concise="The first retained causal moment has a complete account.",
            ),
            SimpleNamespace(cost=0.01, cost_source="provider_reported"),
        )

    narration = narrate_live_moments(
        document,
        model="test-model",
        trace_id_prefix="run_partial_failure",
        structured_call=partial_call,
    )
    assert narration["status"] == "unavailable"
    assert len(narration["moments"]) == 1
    assert narration["calls"][1]["status"] == "failed"
    assert "provider stopped" in narration["calls"][1]["error_message"]


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


def test_v3_context_reconstructs_prior_narrative_chain(
    tmp_path: Path,
) -> None:
    document = TestClient(create_app(ROOT / "web", tmp_path)).post(
        "/api/runs",
        json={"execution": "scripted"},
    ).json()
    call_number = 0

    def fake_call(
        _model: str,
        messages: list[dict[str, str]],
        response_model: type[CausalMomentNarration],
        **_kwargs: Any,
    ) -> tuple[CausalMomentNarration, object]:
        nonlocal call_number
        call_number += 1
        return (
            narrated_response(
                response_model,
                concise=f"Moment {call_number} has a retained account.",
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
    document["narration"] = narration
    validate_retained_narration(document)
    assert moments[1]["evidence_context"]["prior_narrative_record_ids"] == [
        moments[0]["narrative_record_id"]
    ]


@pytest.mark.parametrize(
    "corrupt",
    [
        "missing_context",
        "unknown_event",
        "cross_run",
        "future_reference",
        "digest_mismatch",
    ],
)
def test_v3_context_corruption_fails_loudly(tmp_path: Path, corrupt: str) -> None:
    document = TestClient(create_app(ROOT / "web", tmp_path)).post(
        "/api/runs",
        json={"execution": "scripted"},
    ).json()
    def fake_call(
        _model: str,
        _messages: list[dict[str, str]],
        response_model: type[CausalMomentNarration],
        **_kwargs: Any,
    ) -> tuple[CausalMomentNarration, object]:
        return (
            narrated_response(
                response_model,
                concise="A retained causal moment has a grounded account.",
            ),
            SimpleNamespace(cost=0.01, cost_source="provider_reported"),
        )

    narration = narrate_live_moments(
        document,
        model="test-model",
        trace_id_prefix="run_corrupt_context",
        structured_call=fake_call,
    )
    document["narration"] = narration
    corrupted = json.loads(json.dumps(document))
    moments = corrupted["narration"]["moments"]
    if corrupt == "missing_context":
        del moments[0]["evidence_context"]
    elif corrupt == "unknown_event":
        moments[0]["evidence_context"]["current_event_ids"][0] = "event_unknown"
    elif corrupt == "cross_run":
        moments[0]["evidence_context"]["run_id"] = "run_ffffffffffff"
    elif corrupt == "future_reference":
        moments[0]["evidence_context"]["prior_narrative_record_ids"] = [
            moments[1]["narrative_record_id"]
        ]
    else:
        moments[0]["evidence_context"]["context_digest"] = "0" * 64
    with pytest.raises(ValueError, match="context"):
        validate_retained_narration(corrupted)


def test_legacy_v1_and_v2_narration_remain_readable_without_provider_call(
    tmp_path: Path,
) -> None:
    legacy = {
        "run_id": "run_0123456789ab",
        "narration": {
            "status": "completed",
            "moments": [
                {"narrative": "A legacy concise account.", "source_event_ids": ["event_1"]},
                {
                    "narrative_version": 2,
                    "narrative": "A legacy detailed account.",
                    "source_event_ids": ["event_2"],
                    "detailed_paragraphs": [
                        {"text": "Legacy provenance remains readable.", "source_event_ids": ["event_2"]}
                    ],
                },
            ],
        },
    }
    validate_retained_narration(legacy)
    RunStore(tmp_path).save(legacy)
    api = TestClient(create_app(ROOT / "web", tmp_path))
    reopened = api.get("/api/runs/run_0123456789ab")
    assert reopened.status_code == 200
    assert reopened.json()["narration"]["moments"] == legacy["narration"]["moments"]


def test_api_refuses_to_reopen_a_corrupted_v3_evidence_context(tmp_path: Path) -> None:
    api = TestClient(create_app(ROOT / "web", tmp_path))
    document = api.post("/api/runs", json={"execution": "scripted"}).json()

    def fake_call(
        _model: str,
        _messages: list[dict[str, str]],
        response_model: type[CausalMomentNarration],
        **_kwargs: Any,
    ) -> tuple[CausalMomentNarration, object]:
        return (
            narrated_response(
                response_model,
                concise="The retained trace has a readable causal account.",
            ),
            SimpleNamespace(cost=0.01, cost_source="provider_reported"),
        )

    document["narration"] = narrate_live_moments(
        document,
        model="test-model",
        trace_id_prefix=str(document["run_id"]),
        structured_call=fake_call,
    )
    RunStore(tmp_path).save(document)
    assert api.get(f"/api/runs/{document['run_id']}").status_code == 200

    stored = RunStore(tmp_path).get(str(document["run_id"]))
    stored["narration"]["moments"][0]["evidence_context"]["context_digest"] = "0" * 64
    RunStore(tmp_path).save(stored)
    response = api.get(f"/api/runs/{document['run_id']}")
    assert response.status_code == 409
    assert response.json()["detail"] == "retained narration evidence context is corrupt"
