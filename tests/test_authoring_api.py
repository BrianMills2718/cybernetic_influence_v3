"""API proof for revisioned, approval-gated conversational authoring."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from cybernetic_influence.api import create_app
from cybernetic_influence.authoring.service import _ProposalConsumer
from test_authoring_compiler import _proposal


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


def test_unapproved_draft_cannot_run(tmp_path: Path) -> None:
    api = _client(tmp_path)
    draft_id = api.post("/api/authoring/drafts").json()["draft_id"]
    response = api.post(f"/api/authoring/drafts/{draft_id}/runs", json={"execution": "scripted"})
    assert response.status_code == 409


def test_provider_schema_exposes_nested_template_fields() -> None:
    schema = _ProposalConsumer.model_json_schema()
    person = schema["$defs"]["_PersonConsumer"]["properties"]
    workflow = schema["$defs"]["_WorkflowConsumer"]["properties"]
    assert {"entity_id", "label", "memories"} <= set(person)
    assert {"requester_id", "resource_id", "request_delivery_minutes"} <= set(workflow)


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
