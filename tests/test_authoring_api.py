"""API proof for revisioned, approval-gated conversational authoring."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from cybernetic_influence.api import create_app
from cybernetic_influence.authoring.service import (
    _ProposalConsumer,
    _provider_candidate_from_proposal,
)
from llm_client import LLMCapabilityError
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


def test_unapproved_draft_cannot_run(tmp_path: Path) -> None:
    api = _client(tmp_path)
    draft_id = api.post("/api/authoring/drafts").json()["draft_id"]
    response = api.post(f"/api/authoring/drafts/{draft_id}/runs", json={"execution": "scripted"})
    assert response.status_code == 409


def test_provider_schema_exposes_nested_template_fields() -> None:
    schema = _ProposalConsumer.model_json_schema()
    person = schema["$defs"]["_PersonConsumer"]["properties"]
    workflow = schema["$defs"]["_WorkflowConsumer"]["properties"]
    campaign = schema["$defs"]["_InformationCampaignWorkflowConsumer"]["properties"]
    placement = schema["$defs"]["_PlacementConsumer"]["properties"]
    assert {"entity_id", "label", "memories"} <= set(person)
    assert {"requester_id", "resource_id", "request_delivery_minutes"} <= set(workflow)
    assert {"source_id", "claim_information_id", "publication_delivery_minutes"} <= set(campaign)
    assert {"entity_id", "place_id"} <= set(placement)
    assert schema["properties"]["placements"]["type"] == "array"
    assert "template_id" in schema["$defs"]["_WorkflowConsumer"]["required"]
    assert "template_id" in schema["$defs"]["_InformationCampaignWorkflowConsumer"]["required"]
    assert schema["properties"]["workflow"]["discriminator"]["propertyName"] == "template_id"


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
