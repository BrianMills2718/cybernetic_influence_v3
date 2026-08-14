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
from cybernetic_influence.api import _general_world_node_overrides
from cybernetic_influence.api import _simulation_replay
from cybernetic_influence.general_simulation.authoring_models import (
    GeneralProposalEnvelopeV1,
    GeneralSimulationProposalV1,
)
from cybernetic_influence.general_simulation.models import (
    ActorDecision,
    Assimilation,
    ObjectiveAssessment,
    SemanticActionIntent,
    WorldTransaction,
)
from cybernetic_influence.run_configuration import EffectiveRunLlmConfiguration


FIXTURE = Path("tests/fixtures/general_simulation/port_coordination.json")


def test_general_world_replay_retains_state_by_revision() -> None:
    def state(revision: int, quantity: int) -> dict[str, object]:
        return {
            "revision": revision,
            "records": {
                "inventory": {"state": {"quantity": quantity}},
            },
            "resources": {
                "cargo": {"quantity": quantity, "custodian_id": "operator"},
            },
        }

    def checkpoint(revision: int, quantity: int) -> dict[str, object]:
        return {
            "game_masters": {
                "general_world_game_master": {
                    "components": {
                        "context_components": {
                            "canonical_world": {
                                "spec": {"initial_state": state(0, 0)},
                                "state": state(revision, quantity),
                            }
                        }
                    }
                }
            }
        }

    revisions = _general_world_node_overrides(
        {"checkpoints": [checkpoint(1, 0), checkpoint(2, 500)]}
    )

    initial = {item["node_id"]: item["description"] for item in revisions[0]}
    final = {item["node_id"]: item["description"] for item in revisions[2]}
    assert initial["inventory"] == '{"quantity": 0}'
    assert final["inventory"] == '{"quantity": 500}'
    assert initial["cargo"] == "quantity: 0; custodian: operator"
    assert final["cargo"] == "quantity: 500; custodian: operator"


def test_general_replay_focuses_changed_nodes_and_edges() -> None:
    replay = _simulation_replay(
        title="Route test",
        headline="Route test",
        summary="One retained transition.",
        outcome={"accepted_transactions": 1, "final_revision": 1},
        rounds=[],
        network_nodes=[
            {"id": "operator", "kind": "person", "label": "Operator"},
            {"id": "floor", "kind": "thing", "label": "Floor"},
            {"id": "storage", "kind": "place", "label": "Storage"},
            {"id": "loading", "kind": "place", "label": "Loading"},
        ],
        network_edges=[
            {
                "id": "storage_route",
                "kind": "route",
                "source": "storage",
                "target": "loading",
            }
        ],
        raw_moments=[
            {
                "event_id": "inspect_and_open",
                "narrative": "Inspect the floor and open the route.",
                "participants": ["operator"],
                "execution_parent": "revision:0",
                "resulting_revision": 1,
                "transition": {
                    "transaction": {
                        "operations": [
                            {
                                "operation": "replace",
                                "target": {
                                    "record_type": "record",
                                    "record_id": "floor",
                                    "field": "state.safety_status",
                                },
                                "value": "safe",
                            },
                            {
                                "operation": "replace",
                                "target": {
                                    "record_type": "route",
                                    "record_id": "storage_route",
                                    "field": "operational",
                                },
                                "value": True,
                            },
                        ],
                        "consequences": [],
                        "stated_rationale": "Inspection established a usable route.",
                    }
                },
            }
        ],
        general_world=True,
    )

    event = next(scene for scene in replay["scenes"] if scene["kind"] == "event")
    assert event["focus_node_ids"] == ["floor"]
    assert event["focus_edge_ids"] == ["storage_route"]
    assert "storage_route" in event["visible_edge_ids"]


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
            objective_assessment=(
                ObjectiveAssessment(
                    status="unresolved",
                    summary="The retained evidence does not establish completion of the objective.",
                    evidence_refs=user["requirements"]["intent_ids"],
                    unresolved_requirements=["A verified operational result is still required."],
                )
                if user["requirements"]["is_final_moment"]
                else None
            ),
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
    assert generated.json()["configuration_graph"]["isolated_node_ids"] == []
    assert generated.json()["configuration_graph"]["edges"]
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


def test_live_general_authoring_runs_as_pollable_background_job(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setenv("CYBERNETIC_INFLUENCE_LIVE", "1")
    monkeypatch.setattr(
        api_module,
        "model_catalog",
        lambda: [{"model": "codex/gpt-5.6-luna"}],
    )
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
    draft = api.post("/api/authoring/drafts").json()
    started = api.post(
        f"/api/authoring/drafts/{draft['draft_id']}/messages",
        json={
            "expected_revision": 0,
            "message_id": "background_generation",
            "message": "Model relief cargo coordination after a bridge failure.",
        },
    )

    assert started.status_code == 202
    job = started.json()
    assert job["status"] == "generating"
    for _ in range(100):
        polled = api.get(f"/api/authoring/jobs/{job['job_id']}")
        assert polled.status_code == 200
        job = polled.json()
        if job["status"] != "generating":
            break
        time.sleep(0.01)
    assert job["status"] == "completed"
    assert job["draft"]["status"] == "ready_for_review"
    assert job["draft"]["revision"] == 1


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
    assert summary_payload["simulation_replay"]["scenes"][0]["title"] == "The operational objective"
    replay_scenes = summary_payload["simulation_replay"]["scenes"]
    assert len([scene for scene in replay_scenes if scene["kind"] == "event"]) == 3
    assert not any(scene["kind"] == "decisions" for scene in replay_scenes)
    assert not any(
        fact["label"] == "Positions"
        for scene in replay_scenes
        for fact in scene["facts"]
    )
    event_scenes = [scene for scene in replay_scenes if scene["kind"] == "event"]
    assert all(
        any(fact["label"] == "World change" for fact in scene["facts"])
        for scene in event_scenes
    )
    assert not any(
        fact["label"] == "World transition"
        for scene in event_scenes
        for fact in scene["facts"]
    )
    assert replay_scenes[1]["facts"] == [
        {"label": "People", "value": "4"},
        {"label": "Other world components", "value": "17"},
    ]
    outcome_scene = replay_scenes[-1]
    assert outcome_scene["summary"] == (
        "The retained evidence does not establish completion of the objective."
    )
    assert outcome_scene["facts"] == [
        {"label": "Objective assessment", "value": "unresolved"},
        {"label": "Committed transitions", "value": "3"},
        {"label": "Final world revision", "value": "3"},
    ]
    assert summary_payload["theory_analysis"] is None
    assert runtime_call.actor_counter == call_count
