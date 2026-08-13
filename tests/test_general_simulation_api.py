from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

from cybernetic_influence.api import create_app
from cybernetic_influence.general_simulation.authoring_models import (
    GeneralProposalEnvelopeV1,
    GeneralSimulationProposalV1,
)


FIXTURE = Path("tests/fixtures/general_simulation/port_coordination.json")


def test_general_authoring_api_create_generate_preview_edit_and_approve(
    tmp_path: Path,
) -> None:
    proposal = GeneralSimulationProposalV1.model_validate_json(
        FIXTURE.read_text(encoding="utf-8")
    )

    def provider(*args: Any, **kwargs: Any) -> tuple[object, object]:
        del args, kwargs
        return GeneralProposalEnvelopeV1(proposal=proposal), SimpleNamespace(
            provider="test", cost=0.0
        )

    api = TestClient(
        create_app(
            Path(__file__).resolve().parents[1] / "web",
            tmp_path / "runs",
            authoring_root=tmp_path / "drafts",
            authoring_call=provider,
        )
    )
    created = api.post("/api/authoring/drafts")
    assert created.status_code == 200
    draft = created.json()
    assert draft["target_kind"] == "general_world_v1"

    generated = api.post(
        f"/api/authoring/drafts/{draft['draft_id']}/messages",
        json={
            "expected_revision": 0,
            "message_id": "port_prompt",
            "message": "Model relief cargo coordination after a bridge failure.",
        },
    )
    assert generated.status_code == 200
    document = generated.json()
    assert document["status"] == "ready_for_review"
    assert document["coverage"]["blocking_request_ids"] == []

    preview = api.get(f"/api/authoring/drafts/{draft['draft_id']}/preview")
    assert preview.status_code == 200
    preview_payload = preview.json()
    assert preview_payload["profile"] == "general_world_v1"
    assert preview_payload["world_spec"]["spec_id"] == "relief_port_coordination"
    assert preview_payload["composition_receipt"]["resolved_component_refs"]

    edited = deepcopy(document["proposal"])
    edited["question"] = "Can the parties dispatch safely before sunset?"
    response = api.put(
        f"/api/authoring/drafts/{draft['draft_id']}/general-proposal",
        json={"expected_revision": 1, "edit_id": "question_edit", "proposal": edited},
    )
    assert response.status_code == 200
    assert response.json()["revision"] == 2

    stale = api.put(
        f"/api/authoring/drafts/{draft['draft_id']}/general-proposal",
        json={"expected_revision": 1, "edit_id": "stale_edit", "proposal": edited},
    )
    assert stale.status_code == 409

    approved = api.post(
        f"/api/authoring/drafts/{draft['draft_id']}/approve",
        json={"expected_revision": 2},
    )
    assert approved.status_code == 200
    assert approved.json()["approval"]["registry_digest"]


def test_general_proposal_endpoint_rejects_invented_implementation_reference(
    tmp_path: Path,
) -> None:
    api = TestClient(
        create_app(
            Path(__file__).resolve().parents[1] / "web",
            tmp_path / "runs",
            authoring_root=tmp_path / "drafts",
        )
    )
    draft = api.post("/api/authoring/drafts").json()
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload["component_requests"][0]["implementation_ref"] = "invented.module:run"

    response = api.put(
        f"/api/authoring/drafts/{draft['draft_id']}/general-proposal",
        json={"expected_revision": 0, "edit_id": "bad", "proposal": payload},
    )

    assert response.status_code == 422
    assert "implementation_ref" in response.text
