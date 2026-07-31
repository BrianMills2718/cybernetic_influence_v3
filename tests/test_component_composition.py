"""Focused Slice-25B proof for the first mixed reviewed-component workflow."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from cybernetic_influence.api import create_app
from cybernetic_influence.authoring import AuthoringCompilationError, compile_scenario
from cybernetic_influence.authoring.examples import reviewed_component_composition_proposal
from cybernetic_influence.authoring.models import ScenarioDraftProposal
from cybernetic_influence.causal_core.replay import replay_committed_trajectory


def test_mixed_component_composition_compiles_runs_and_replays() -> None:
    compiled = compile_scenario(reviewed_component_composition_proposal())

    result = compiled.run_scripted(run_id="component_composition_reference")

    assert result.core_result.final_state.entities["field_report_ledger"].attributes[
        "status"
    ].value == "assessed_contested"
    assert replay_committed_trajectory(compiled.scenario, result.core_result) == (
        result.core_result.final_state
    )
    receipt = compiled.composition_receipt
    assert receipt.workflow_template_id == "component_composition_v1"
    assert {item.component_kind for item in receipt.selected_components} >= {
        "person_participant",
        "information_carrier",
        "directed_connection",
        "exact_mechanism",
    }


def test_mixed_component_composition_rejects_missing_reviewed_seam() -> None:
    payload = reviewed_component_composition_proposal().model_dump(mode="json")
    components = payload["workflow"]["components"]
    assert isinstance(components, list)
    assert isinstance(components[-1], dict)
    components[-1]["component_id"] = "unbound_recording"

    with pytest.raises(AuthoringCompilationError, match="exactly the reviewed"):
        compile_scenario(ScenarioDraftProposal.model_validate(payload))


def test_component_example_can_be_created_previewed_approved_and_run(tmp_path: Path) -> None:
    api = TestClient(
        create_app(web_root=Path("web"), run_root=tmp_path / "runs", authoring_root=tmp_path / "drafts")
    )
    draft = api.post("/api/authoring/reviewed-component-composition-drafts")

    assert draft.status_code == 200
    draft_id = draft.json()["draft_id"]
    preview = api.get(f"/api/authoring/drafts/{draft_id}/preview")
    assert preview.status_code == 200
    assert preview.json()["composition_receipt"]["workflow_template_id"] == (
        "component_composition_v1"
    )
    approved = api.post(
        f"/api/authoring/drafts/{draft_id}/approve", json={"expected_revision": 1}
    )
    assert approved.status_code == 200
    run = api.post(
        f"/api/authoring/drafts/{draft_id}/runs", json={"execution": "scripted"}
    )
    assert run.status_code == 200
    assert run.json()["outcome"]["status"] == "assessed_contested"
