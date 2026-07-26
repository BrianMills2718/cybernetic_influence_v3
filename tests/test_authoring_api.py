"""API proof for revisioned, approval-gated conversational authoring."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

import cybernetic_influence.api as api_module
from cybernetic_influence.active_runtime import (
    ActiveSystemExecutionError,
    ModelCallEvidence,
)
from cybernetic_influence.api import create_app
from cybernetic_influence.authoring.compiler import CompiledScenario
from cybernetic_influence.authoring.service import (
    _ProposalConsumer,
    _prompt,
    _provider_candidate_from_proposal,
)
from cybernetic_influence.authoring.models import ResourceRequestWorkflowDraft
from cybernetic_influence.run_configuration import EffectiveRunLlmConfiguration
from llm_client import LLMCapabilityError, LLMQuotaExhaustedError
from test_authoring_compiler import _proposal
from test_authoring_information_campaign import information_campaign_proposal


class _Meta:
    cost = 0.0


def _proposer(*_args: object, **_kwargs: object) -> tuple[object, object]:
    return _proposal(), _Meta()


def _client(tmp_path: Path) -> TestClient:
    return TestClient(
        create_app(
            Path(__file__).resolve().parents[1] / "web",
            tmp_path / "runs",
            authoring_root=tmp_path / "drafts",
            authoring_call=_proposer,
        )
    )


def test_draft_is_idempotent_revisioned_previewable_approved_and_runnable(tmp_path: Path) -> None:
    api = _client(tmp_path)
    created = api.post("/api/authoring/drafts")
    assert created.status_code == 200
    draft = created.json()
    draft_id = draft["draft_id"]

    message = {"expected_revision": 0, "message_id": "m1", "message": "Model equipment checkout."}
    advanced = api.post(f"/api/authoring/drafts/{draft_id}/messages", json=message)
    assert advanced.status_code == 200
    assert advanced.json()["revision"] == 1
    assert advanced.json()["diagnostics"] == []
    duplicate = api.post(f"/api/authoring/drafts/{draft_id}/messages", json=message)
    assert duplicate.status_code == 200
    assert duplicate.json()["revision"] == 1
    conflict = api.post(
        f"/api/authoring/drafts/{draft_id}/messages",
        json={**message, "message_id": "m2"},
    )
    assert conflict.status_code == 409

    preview = api.get(f"/api/authoring/drafts/{draft_id}/preview")
    assert preview.status_code == 200
    assert preview.json()["world"]["places"]
    assert preview.json()["boundaries"][0]["executor"] is False

    approved = api.post(
        f"/api/authoring/drafts/{draft_id}/approve", json={"expected_revision": 1}
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    run = api.post(f"/api/authoring/drafts/{draft_id}/runs", json={"execution": "scripted"})
    assert run.status_code == 200
    assert run.json()["execution"] == "scripted"
    assert run.json()["cost"] == 0.0
    assert run.json()["authoring"]["draft_id"] == draft_id


def test_authored_live_run_requires_authorization_and_live_options(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.delenv("CYBERNETIC_INFLUENCE_LIVE", raising=False)
    api = _client(tmp_path)
    draft_id = api.post("/api/authoring/drafts").json()["draft_id"]
    api.post(
        f"/api/authoring/drafts/{draft_id}/messages",
        json={
            "expected_revision": 0,
            "message_id": "m1",
            "message": "Model equipment checkout.",
        },
    )
    api.post(
        f"/api/authoring/drafts/{draft_id}/approve",
        json={"expected_revision": 1},
    )
    options = {
        "model": "openrouter/openai/gpt-5.6-terra",
        "agent_reasoning_effort": "medium",
        "max_total_cost": 0.20,
    }

    unauthorized = api.post(
        f"/api/authoring/drafts/{draft_id}/runs",
        json={"execution": "live", "llm_options": options},
    )
    scripted_with_spend = api.post(
        f"/api/authoring/drafts/{draft_id}/runs",
        json={"execution": "scripted", "llm_options": options},
    )

    assert unauthorized.status_code == 403
    assert scripted_with_spend.status_code == 422


def test_failed_authored_live_run_is_retained_with_provider_evidence(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("CYBERNETIC_INFLUENCE_LIVE", "1")
    effective = EffectiveRunLlmConfiguration(
        model="openrouter/deepseek/deepseek-v3.2",
        agent_reasoning_effort="none",
        narrator_reasoning_effort="none",
        max_total_cost=0.20,
        selection_basis="operator_selected",
        llm_client_revision="package:0.7.0",
    )
    monkeypatch.setattr(
        api_module,
        "resolve_live_configuration",
        lambda _options: effective,
    )
    evidence = ModelCallEvidence(
        status="failed",
        trace_id="authored/failure/active/source",
        model=effective.model,
        task="cybernetic_influence.active_system.resource_request_v1.source",
        reasoning_effort="none",
        system_prompt="Act only from the bounded input.",
        user_prompt="The bounded input.",
        cost=0.01,
        cost_source="provider_reported",
        error_type="ForcedProviderError",
        error_message="forced provider failure",
    )

    def fail_live(
        _compiled: CompiledScenario,
        **_kwargs: object,
    ) -> object:
        raise ActiveSystemExecutionError(
            "forced provider failure",
            call_evidence=(evidence,),
        )

    monkeypatch.setattr(CompiledScenario, "run_live", fail_live)
    api = _client(tmp_path)
    draft_id = api.post("/api/authoring/drafts").json()["draft_id"]
    drafted = api.post(
        f"/api/authoring/drafts/{draft_id}/messages",
        json={
            "expected_revision": 0,
            "message_id": "m1",
            "message": "Model equipment checkout.",
        },
    ).json()
    api.post(
        f"/api/authoring/drafts/{draft_id}/approve",
        json={"expected_revision": drafted["revision"]},
    )

    failed = api.post(
        f"/api/authoring/drafts/{draft_id}/runs",
        json={
            "execution": "live",
            "llm_options": {
                "model": effective.model,
                "agent_reasoning_effort": "none",
                "max_total_cost": 0.20,
            },
        },
    )

    assert failed.status_code == 500
    assert failed.json()["detail"] == (
        "authored simulation failed; retained for inspection"
    )
    retained = api.get("/api/runs").json()["runs"][0]
    assert retained["status"] == "failed"
    run = api.get(f"/api/runs/{retained['run_id']}").json()
    assert run["model_calls"] == 1
    assert run["cost"] == 0.01
    assert run["model_call_summaries"] == [
        {
            "status": "failed",
            "trace_id": "authored/failure/active/source",
            "task": (
                "cybernetic_influence.active_system."
                "resource_request_v1.source"
            ),
            "model": effective.model,
            "reasoning_effort": "none",
            "cost": 0.01,
            "cost_source": "provider_reported",
            "error_type": "ForcedProviderError",
            "error_message": "forced provider failure",
        }
    ]


def test_each_revision_retains_its_selected_model_reasoning_and_trace(tmp_path: Path) -> None:
    calls: list[tuple[object, object]] = []

    def recording_proposer(*args: object, **kwargs: object) -> tuple[object, object]:
        calls.append((args[0], kwargs["reasoning_effort"]))
        proposal = _proposal().model_copy(deep=True)
        if len(calls) == 2:
            assert isinstance(proposal.workflow, ResourceRequestWorkflowDraft)
            proposal.workflow.resource_available = False
            proposal.description = "The requested laptop is unavailable."
        return proposal, _Meta()

    api = TestClient(
        create_app(
            Path(__file__).resolve().parents[1] / "web",
            tmp_path / "runs",
            authoring_root=tmp_path / "drafts",
            authoring_call=recording_proposer,
        )
    )
    config = api.get("/api/config").json()["authoring"]
    assert [(item["label"], item["model"]) for item in config["models"]] == [
        ("Terra", "openrouter/openai/gpt-5.6-terra"),
        ("Sol", "openrouter/openai/gpt-5.6-sol"),
    ]
    assert config["reasoning_efforts"] == ["none", "low", "medium", "high", "xhigh", "max"]

    draft_id = api.post("/api/authoring/drafts").json()["draft_id"]
    first = api.post(
        f"/api/authoring/drafts/{draft_id}/messages",
        json={
            "expected_revision": 0,
            "message_id": "m1",
            "message": "Model equipment checkout.",
            "model": "openrouter/openai/gpt-5.6-terra",
            "reasoning_effort": "low",
        },
    ).json()
    second = api.post(
        f"/api/authoring/drafts/{draft_id}/messages",
        json={
            "expected_revision": first["revision"],
            "message_id": "m2",
            "message": "Make the laptop unavailable.",
            "model": "openrouter/openai/gpt-5.6-sol",
            "reasoning_effort": "high",
        },
    ).json()

    assert calls == [
        ("openrouter/openai/gpt-5.6-terra", "low"),
        ("openrouter/openai/gpt-5.6-sol", "high"),
    ]
    assert [
        (message["model"], message["reasoning_effort"])
        for message in second["messages"]
    ] == [
        ("openrouter/openai/gpt-5.6-terra", "low"),
        ("openrouter/openai/gpt-5.6-sol", "high"),
    ]
    assert second["messages"][0]["trace_ids"] == [
        f"{draft_id}/revision/1/attempt/1"
    ]
    assert second["messages"][1]["trace_ids"] == [
        f"{draft_id}/revision/2/attempt/1"
    ]
    assert second["messages"][1]["assistant_summary"].startswith(
        "Ready to review: Equipment checkout desk"
    )
    assert second["proposal"]["workflow"]["resource_available"] is False

    reused = api.post(
        f"/api/authoring/drafts/{draft_id}/messages",
        json={
            "expected_revision": second["revision"],
            "message_id": "m2",
            "message": "Make the laptop unavailable.",
            "model": "openrouter/openai/gpt-5.6-terra",
            "reasoning_effort": "high",
        },
    )
    assert reused.status_code == 409


def test_provider_failure_becomes_a_visible_bounded_needs_input_state(tmp_path: Path) -> None:
    def failing(*_args: object, **_kwargs: object) -> tuple[object, object]:
        raise RuntimeError("provider unavailable")

    api = TestClient(
        create_app(
            Path(__file__).resolve().parents[1] / "web",
            tmp_path / "runs",
            authoring_root=tmp_path / "drafts",
            authoring_call=failing,
        )
    )
    draft_id = api.post("/api/authoring/drafts").json()["draft_id"]
    failed = api.post(
        f"/api/authoring/drafts/{draft_id}/messages",
        json={"expected_revision": 0, "message_id": "m1", "message": "A request."},
    )
    assert failed.status_code == 200
    retained = api.get(f"/api/authoring/drafts/{draft_id}").json()
    assert retained["revision"] == 1
    assert retained["status"] == "needs_input"
    assert retained["proposal"] is None
    assert len(retained["attempts"]) == 3
    assert all(attempt["status"] == "provider_error" for attempt in retained["attempts"])


def test_unresolved_question_retains_previewable_draft_without_repeating_spend(
    tmp_path: Path,
) -> None:
    calls = 0

    def questioning(*_args: object, **_kwargs: object) -> tuple[object, object]:
        nonlocal calls
        calls += 1
        proposal = _proposal().model_copy(deep=True)
        proposal.unresolved_questions = ["Which exact policy copy should govern eligibility?"]
        return proposal, _Meta()

    api = TestClient(
        create_app(
            Path(__file__).resolve().parents[1] / "web",
            tmp_path / "runs",
            authoring_root=tmp_path / "drafts",
            authoring_call=questioning,
        )
    )
    draft_id = api.post("/api/authoring/drafts").json()["draft_id"]
    draft = api.post(
        f"/api/authoring/drafts/{draft_id}/messages",
        json={"expected_revision": 0, "message_id": "m1", "message": "Model checkout."},
    ).json()
    assert calls == 1
    assert draft["status"] == "needs_input"
    assert draft["proposal"] is not None
    assert draft["attempts"][0]["status"] == "needs_input"
    assert "Which exact policy copy" in draft["diagnostics"][0]["message"]
    assert api.get(f"/api/authoring/drafts/{draft_id}/preview").status_code == 200


def test_nonretryable_capability_failure_stops_after_one_visible_attempt(tmp_path: Path) -> None:
    def unsupported(*_args: object, **_kwargs: object) -> tuple[object, object]:
        raise LLMCapabilityError("the selected route rejects this schema")

    api = TestClient(
        create_app(
            Path(__file__).resolve().parents[1] / "web",
            tmp_path / "runs",
            authoring_root=tmp_path / "drafts",
            authoring_call=unsupported,
        )
    )
    draft_id = api.post("/api/authoring/drafts").json()["draft_id"]
    failed = api.post(
        f"/api/authoring/drafts/{draft_id}/messages",
        json={"expected_revision": 0, "message_id": "m1", "message": "A request."},
    ).json()
    assert len(failed["attempts"]) == 1
    assert "cannot accept this structured schema" in failed["diagnostics"][0]["message"]
    assert "selected route rejects this schema" in failed["diagnostics"][0]["message"]


def test_quota_failure_stops_once_and_explains_that_the_prior_draft_is_safe(
    tmp_path: Path,
) -> None:
    calls = 0

    def exhausted(*_args: object, **_kwargs: object) -> tuple[object, object]:
        nonlocal calls
        calls += 1
        if calls == 1:
            return _proposal(), _Meta()
        raise LLMQuotaExhaustedError("insufficient quota")

    api = TestClient(
        create_app(
            Path(__file__).resolve().parents[1] / "web",
            tmp_path / "runs",
            authoring_root=tmp_path / "drafts",
            authoring_call=exhausted,
        )
    )
    draft_id = api.post("/api/authoring/drafts").json()["draft_id"]
    ready = api.post(
        f"/api/authoring/drafts/{draft_id}/messages",
        json={
            "expected_revision": 0,
            "message_id": "m1",
            "message": "A request.",
            "model": "openrouter/openai/gpt-5.6-terra",
            "reasoning_effort": "medium",
        },
    ).json()
    failed = api.post(
        f"/api/authoring/drafts/{draft_id}/messages",
        json={
            "expected_revision": ready["revision"],
            "message_id": "m2",
            "message": "Change the request.",
            "model": "openrouter/openai/gpt-5.6-sol",
            "reasoning_effort": "medium",
        },
    ).json()
    assert calls == 2
    assert len(failed["attempts"]) == 1
    assert failed["proposal"] == ready["proposal"]
    assert "selected OpenRouter route has no usable quota" in failed["messages"][-1]["assistant_summary"]


def test_unapproved_draft_cannot_run(tmp_path: Path) -> None:
    api = _client(tmp_path)
    draft_id = api.post("/api/authoring/drafts").json()["draft_id"]
    response = api.post(f"/api/authoring/drafts/{draft_id}/runs", json={"execution": "scripted"})
    assert response.status_code == 409


def test_provider_schema_exposes_nested_template_fields() -> None:
    schema = _ProposalConsumer.model_json_schema()
    person = schema["$defs"]["_PersonConsumer"]["properties"]
    behavioral_profile = schema["$defs"]["_BehavioralProfileConsumer"]
    workflow = schema["$defs"]["_WorkflowConsumer"]["properties"]
    campaign = schema["$defs"]["_InformationCampaignWorkflowConsumer"]["properties"]
    placement = schema["$defs"]["_PlacementConsumer"]["properties"]
    assert {"entity_id", "label", "memories", "behavioral_profile"} <= set(person)
    assert {
        "values",
        "goals",
        "beliefs",
        "decision_tendencies",
        "social_perceptions",
        "current_state",
        "capabilities",
        "limitations",
    } == set(behavioral_profile["required"])
    assert {"requester_id", "resource_id", "request_delivery_minutes"} <= set(workflow)
    assert {"source_id", "claim_information_id", "publication_delivery_minutes"} <= set(campaign)
    assert {"entity_id", "place_id"} <= set(placement)
    assert schema["properties"]["placements"]["type"] == "array"
    assert "template_id" in schema["$defs"]["_WorkflowConsumer"]["required"]
    assert "template_id" in schema["$defs"]["_InformationCampaignWorkflowConsumer"]["required"]
    assert schema["properties"]["workflow"]["discriminator"]["propertyName"] == "template_id"


def test_authoring_prompt_keeps_compiler_owned_details_out_of_user_questions() -> None:
    system, _user = _prompt(
        message="Model checkout.",
        prior={},
        repair_feedback=None,
        candidate=None,
    )
    assert "Place only declared people and objects" in system
    assert "Never put a statement, assumption, compiler-owned detail" in system
    assert "When the compiler owns a missing detail" in system
    assert "Alice is skeptical of official sources" in system
    assert "A social_perception is what the person thinks" in system
    assert "never creates or removes an interface" in system
    assert "describe the in-world human" in system
    assert "current_state is only current emotion" in system


def test_direct_person_edit_is_revisioned_idempotent_and_makes_no_llm_call(
    tmp_path: Path,
) -> None:
    calls = 0

    def counted_proposer(*_args: object, **_kwargs: object) -> tuple[object, object]:
        nonlocal calls
        calls += 1
        return _proposal(), _Meta()

    api = TestClient(
        create_app(
            Path(__file__).resolve().parents[1] / "web",
            tmp_path / "runs",
            authoring_root=tmp_path / "drafts",
            authoring_call=counted_proposer,
        )
    )
    draft_id = api.post("/api/authoring/drafts").json()["draft_id"]
    drafted = api.post(
        f"/api/authoring/drafts/{draft_id}/messages",
        json={"expected_revision": 0, "message_id": "m1", "message": "Model checkout."},
    ).json()
    person = drafted["proposal"]["people"][0]
    person["disposition"] = "Ari is cautious about relying on unverified equipment records."
    person["behavioral_profile"]["beliefs"] = [
        "Ari believes the inventory record may be stale."
    ]
    request = {
        "expected_revision": drafted["revision"],
        "edit_id": "person-edit-1",
        "person": person,
    }

    edited = api.put(
        f"/api/authoring/drafts/{draft_id}/people/{person['entity_id']}",
        json=request,
    )
    assert edited.status_code == 200
    body = edited.json()
    assert calls == 1
    assert body["revision"] == drafted["revision"] + 1
    assert body["approval"] is None
    assert body["proposal"]["people"][0]["behavioral_profile"]["beliefs"] == [
        "Ari believes the inventory record may be stale."
    ]
    assert body["messages"][-1]["source"] == "direct_person_edit"
    assert body["messages"][-1]["trace_ids"] == []
    assert body["attempts"] == drafted["attempts"]

    duplicate = api.put(
        f"/api/authoring/drafts/{draft_id}/people/{person['entity_id']}",
        json=request,
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["revision"] == body["revision"]
    assert calls == 1
    assert api.get(f"/api/authoring/drafts/{draft_id}/preview").status_code == 200


def test_direct_person_edit_rejects_stale_or_mismatched_content(tmp_path: Path) -> None:
    api = _client(tmp_path)
    draft_id = api.post("/api/authoring/drafts").json()["draft_id"]
    drafted = api.post(
        f"/api/authoring/drafts/{draft_id}/messages",
        json={"expected_revision": 0, "message_id": "m1", "message": "Model checkout."},
    ).json()
    person = drafted["proposal"]["people"][0]
    request = {
        "expected_revision": drafted["revision"],
        "edit_id": "person-edit-1",
        "person": person,
    }
    saved = api.put(
        f"/api/authoring/drafts/{draft_id}/people/{person['entity_id']}",
        json=request,
    )
    assert saved.status_code == 200

    stale_person = dict(person)
    stale_person["label"] = "Changed after save"
    stale = api.put(
        f"/api/authoring/drafts/{draft_id}/people/{person['entity_id']}",
        json={**request, "edit_id": "person-edit-2", "person": stale_person},
    )
    assert stale.status_code == 409

    mismatch = api.put(
        f"/api/authoring/drafts/{draft_id}/people/not_the_person",
        json={
            "expected_revision": saved.json()["revision"],
            "edit_id": "person-edit-3",
            "person": person,
        },
    )
    assert mismatch.status_code == 422


def test_information_campaign_can_be_drafted_approved_and_run(tmp_path: Path) -> None:
    def campaign_proposer(*_args: object, **_kwargs: object) -> tuple[object, object]:
        return information_campaign_proposal(), _Meta()

    api = TestClient(
        create_app(
            Path(__file__).resolve().parents[1] / "web",
            tmp_path / "runs",
            authoring_root=tmp_path / "drafts",
            authoring_call=campaign_proposer,
        )
    )
    config = api.get("/api/config").json()["authoring"]
    assert config["model"] == "openrouter/openai/gpt-5.6-terra"
    assert config["reasoning_effort"] == "medium"
    draft_id = api.post("/api/authoring/drafts").json()["draft_id"]
    drafted = api.post(
        f"/api/authoring/drafts/{draft_id}/messages",
        json={
            "expected_revision": 0,
            "message_id": "m1",
            "message": "Model a disinformation claim sent to a diplomatic office.",
        },
    )
    assert drafted.status_code == 200
    assert drafted.json()["proposal"]["workflow"]["template_id"] == "information_campaign_v1"
    preview = api.get(f"/api/authoring/drafts/{draft_id}/preview")
    assert preview.status_code == 200
    assert preview.json()["world"]["places"]
    approved = api.post(
        f"/api/authoring/drafts/{draft_id}/approve",
        json={"expected_revision": 1},
    )
    assert approved.status_code == 200
    run = api.post(
        f"/api/authoring/drafts/{draft_id}/runs",
        json={"execution": "scripted"},
    )
    assert run.status_code == 200
    assert run.json()["outcome"]["status"] == "assessed_contested"
    assert run.json()["authoring"]["template_id"] == "information_campaign_v1"


def test_authoring_repairs_a_compiler_error_before_returning_the_draft(tmp_path: Path) -> None:
    calls = 0

    def repairable(*_args: object, **_kwargs: object) -> tuple[object, object]:
        nonlocal calls
        calls += 1
        proposal = _proposal().model_copy(deep=True)
        if calls == 1:
            proposal.timing_assumptions[0].minutes = 7
        return proposal, _Meta()

    api = TestClient(
        create_app(
            Path(__file__).resolve().parents[1] / "web",
            tmp_path / "runs",
            authoring_root=tmp_path / "drafts",
            authoring_call=repairable,
        )
    )
    draft_id = api.post("/api/authoring/drafts").json()["draft_id"]
    drafted = api.post(
        f"/api/authoring/drafts/{draft_id}/messages",
        json={"expected_revision": 0, "message_id": "m1", "message": "Model checkout."},
    )
    assert drafted.status_code == 200
    body = drafted.json()
    assert calls == 2
    assert body["status"] == "ready_for_review"
    assert [attempt["status"] for attempt in body["attempts"]] == ["repair", "accepted"]


def test_authoring_returns_all_local_schema_issues_to_the_next_repair(tmp_path: Path) -> None:
    calls = 0
    repair_prompt = ""

    def repairable(*args: object, **_kwargs: object) -> tuple[object, object]:
        nonlocal calls, repair_prompt
        calls += 1
        if calls == 1:
            proposal = _provider_candidate_from_proposal(_proposal())
            proposal["scenario_id"] = "Invalid ID"
            timing = proposal["timing_assumptions"]
            assert isinstance(timing, list)
            first_timing = timing[0]
            assert isinstance(first_timing, dict)
            first_timing["minutes"] = 0
            return proposal, _Meta()
        messages = args[1]
        assert isinstance(messages, list)
        last_message = messages[-1]
        assert isinstance(last_message, dict)
        repair_prompt = str(last_message["content"])
        return _proposal(), _Meta()

    api = TestClient(
        create_app(
            Path(__file__).resolve().parents[1] / "web",
            tmp_path / "runs",
            authoring_root=tmp_path / "drafts",
            authoring_call=repairable,
        )
    )
    draft_id = api.post("/api/authoring/drafts").json()["draft_id"]
    body = api.post(
        f"/api/authoring/drafts/{draft_id}/messages",
        json={"expected_revision": 0, "message_id": "m1", "message": "Model checkout."},
    ).json()
    assert body["status"] == "ready_for_review"
    assert [attempt["status"] for attempt in body["attempts"]] == ["repair", "accepted"]
    assert "scenario_id" in repair_prompt
    assert "timing_assumptions.0.minutes" in repair_prompt
