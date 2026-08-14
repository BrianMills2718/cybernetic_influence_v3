from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import time
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

import cybernetic_influence.api as api_module
from cybernetic_influence.api import create_app
from cybernetic_influence.general_simulation.authoring_models import (
    GeneralProposalEnvelopeV1,
    GeneralSimulationProposalV1,
)
from cybernetic_influence.general_simulation.models import (
    ActorDecision,
    Assimilation,
    SemanticActionIntent,
    WorldTransaction,
)
from cybernetic_influence.run_configuration import EffectiveRunLlmConfiguration


FIXTURE = Path("tests/fixtures/general_simulation/port_coordination.json")


class _GeneralRuntimeFake:
    def __init__(self) -> None:
        self.actor_counter = 0

    def __call__(self, *args: Any, **kwargs: Any) -> tuple[object, object]:
        response_model = kwargs["response_model"]
        user = json.loads(args[1][1]["content"])
        if response_model is ActorDecision:
            self.actor_counter += 1
            context = user["actor_context"]
            return ActorDecision(
                assimilation=Assimilation(
                    attended_observation_ids=[
                        item["observation_id"] for item in context["observations"]
                    ],
                    memory_additions=[f"memory {self.actor_counter}"],
                    memory_revisions=[],
                    provenance_links=[
                        item["observation_id"] for item in context["observations"]
                    ],
                    interpretation="Bounded fixture interpretation.",
                ),
                intent=SemanticActionIntent(
                    intent_id=f"intent_{self.actor_counter}",
                    actor_id=context["actor_id"],
                    base_revision=context["base_revision"],
                    action="Propose a bounded joint check.",
                    target_refs=["relief_cargo"],
                    purpose="Explore the configured question.",
                    expected_effect="A joint proposal.",
                    stated_rationale="Available evidence supports a bounded attempt.",
                ),
            ), SimpleNamespace(provider="fixture")
        return WorldTransaction(
            transaction_id=f"transaction_{user['moment']['moment_id']}",
            base_revision=user["requirements"]["base_revision"],
            authority_id=user["requirements"]["authority_id"],
            intent_ids=user["requirements"]["intent_ids"],
            operations=[],
            preconditions=[],
            consequences=[],
            evidence_refs=user["requirements"]["intent_ids"],
            stated_rationale="Retain the world while recording joint review.",
        ), SimpleNamespace(provider="fixture")


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


def test_approved_general_draft_runs_and_reopens_without_more_calls(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("CYBERNETIC_INFLUENCE_LIVE", "1")
    effective = EffectiveRunLlmConfiguration(
        model="codex/gpt-5.6-luna",
        agent_reasoning_effort="medium",
        narrator_reasoning_effort="none",
        max_total_cost=0.74,
        selection_basis="operator_selected",
        llm_client_revision="fixture",
        billing_mode="subscription_included",
    )
    monkeypatch.setattr(api_module, "resolve_live_configuration", lambda _options: effective)
    runtime_call = _GeneralRuntimeFake()
    api = TestClient(
        create_app(
            Path(__file__).resolve().parents[1] / "web",
            tmp_path / "runs",
            authoring_root=tmp_path / "drafts",
            general_simulation_call=runtime_call,
        )
    )
    draft = api.post("/api/authoring/drafts").json()
    proposal = json.loads(FIXTURE.read_text(encoding="utf-8"))
    edited = api.put(
        f"/api/authoring/drafts/{draft['draft_id']}/general-proposal",
        json={"expected_revision": 0, "edit_id": "fixture", "proposal": proposal},
    ).json()
    approved = api.post(
        f"/api/authoring/drafts/{draft['draft_id']}/approve",
        json={"expected_revision": edited["revision"]},
    )
    assert approved.status_code == 200
    started = api.post(
        f"/api/authoring/drafts/{draft['draft_id']}/runs",
        json={
            "execution": "live",
            "narration": "deterministic",
            "llm_options": {
                "model": "codex/gpt-5.6-luna",
                "agent_reasoning_effort": "medium",
                "max_total_cost": 0.74,
            },
        },
    )
    assert started.status_code == 202, started.text
    run_id = started.json()["run_id"]
    for _ in range(200):
        reopened = api.get(f"/api/runs/{run_id}").json()
        if reopened["status"] != "running":
            break
        time.sleep(0.01)
    assert reopened["status"] == "completed", reopened
    assert reopened["profile"] == "general_world_v1"
    assert reopened["model_calls"] == 15
    assert reopened["general_simulation"]["adoption"]["engine_class"].endswith(
        "simultaneous.Simultaneous"
    )
    assert len(reopened["general_simulation"]["moments"]) == 3
    call_count = runtime_call.actor_counter
    summary = api.get(f"/api/runs/{run_id}/summary")
    assert summary.status_code == 200, summary.text
    summary_payload = summary.json()
    assert summary_payload["profile"] == "general_world_v1"
    assert summary_payload["causal_moments"] == 3
    assert summary_payload["participant_model_calls"] == 15
    assert summary_payload["simulation_replay"]["scenes"]
    assert not any(
        node["id"] == "collective_decision"
        for node in summary_payload["influence_network"]["nodes"]
    )
    assert summary_payload["simulation_replay"]["scenes"][0]["visible_node_ids"] == []
    assert summary_payload["simulation_replay"]["scenes"][0]["title"] == "The research question"
    assert summary_payload["simulation_replay"]["scenes"][-1]["facts"][0]["label"] == "Outcome"
    assert len(summary_payload["theory_analysis"]["findings"]) == 5
    assert runtime_call.actor_counter == call_count
