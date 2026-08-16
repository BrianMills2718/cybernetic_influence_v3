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
from cybernetic_influence.analysis.theory_analysis import AnalysisSpecV2
from cybernetic_influence.general_simulation.authoring_models import (
    AnalysisSpecV1,
    DependencyCompletenessReviewV1,
    GeneralSimulationProposalV1,
    MissingDependencyFindingV1,
)
from cybernetic_influence.general_simulation.study_models import (
    AuthoredSimulationProposalEnvelopeV2,
    AuthoredSimulationProposalV2,
    AuthoringRunProposalV2,
    adapt_authored_bundle_v1,
)
from cybernetic_influence.general_simulation.models import (
    ActorDecision,
    Assimilation,
    SemanticActionIntent,
    WorldTransactionProposal,
)
from cybernetic_influence.run_configuration import EffectiveRunLlmConfiguration


FIXTURE = Path("tests/fixtures/general_simulation/port_coordination.json")


def _native_v2_proposal() -> AuthoredSimulationProposalV2:
    legacy = GeneralSimulationProposalV1.model_validate_json(
        FIXTURE.read_text(encoding="utf-8")
    )
    bundle = adapt_authored_bundle_v1(legacy, run_id="draft_fixture_run")
    return AuthoredSimulationProposalV2(
        authored_study_id=bundle.authored_study_id,
        scenario=bundle.scenario,
        default_run=AuthoringRunProposalV2(
            horizon_minutes=bundle.default_run.horizon_minutes,
            scheduled_moments=bundle.default_run.scheduled_moments,
            termination_conditions=bundle.default_run.termination_conditions,
        ),
        analyses=bundle.analyses,
        unresolved_questions=bundle.unresolved_questions,
        analyst_question=bundle.analyst_question,
    )


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

    assert replay["scenes"][0]["title"] == "Simulation brief"
    event = next(scene for scene in replay["scenes"] if scene["kind"] == "event")
    assert event["focus_node_ids"] == ["floor"]
    assert event["focus_edge_ids"] == ["storage_route"]
    assert "storage_route" in event["visible_edge_ids"]


class _GeneralRuntimeFake:
    def __init__(self) -> None:
        self.actor_counter = 0
        self.supplied_inputs: list[dict[str, object]] = []

    def __call__(self, *args: Any, **kwargs: Any) -> tuple[object, object]:
        response_model = kwargs["response_model"]
        user = json.loads(args[1][1]["content"])
        self.supplied_inputs.append(user)
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
        return WorldTransactionProposal(
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
    proposal = _native_v2_proposal()

    def provider(*args: Any, **kwargs: Any) -> tuple[object, object]:
        if kwargs["response_model"] is DependencyCompletenessReviewV1:
            return DependencyCompletenessReviewV1(
                status="complete",
                summary="No stated exact-action prerequisite is omitted.",
                missing_dependencies=[],
            ), SimpleNamespace(provider="test", cost=0.0)
        assert "state.<key>" in args[1][0]["content"]
        return AuthoredSimulationProposalEnvelopeV2(proposal=proposal), SimpleNamespace(
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
    assert draft["target_kind"] == "general_world_v2"

    generated = api.post(
        f"/api/authoring/drafts/{draft['draft_id']}/messages",
        json={
            "expected_revision": 0,
            "message_id": "port_prompt",
            "message": "Model relief cargo coordination after a bridge failure.",
        },
    )
    assert generated.status_code == 200
    assert [item["status"] for item in generated.json()["attempts"]] == [
        "accepted",
        "accepted",
    ]
    assert generated.json()["messages"][-1]["trace_ids"][-1].endswith(
        "/dependency-review"
    )
    assert generated.json()["configuration_graph"]["isolated_node_ids"] == []
    assert generated.json()["configuration_graph"]["edges"]
    document = generated.json()
    assert document["status"] == "ready_for_review"
    assert document["coverage"]["blocking_request_ids"] == []
    assert all(
        item["causal_closure"] in {"exact", "coarse"}
        for item in document["coverage"]["items"]
    )


    retained_path = tmp_path / "drafts" / f"{draft['draft_id']}.json"
    retained = json.loads(retained_path.read_text(encoding="utf-8"))
    retained["coverage"] = {
        "registry_digest": "stale_snapshot",
        "items": [],
        "blocking_request_ids": [],
    }
    retained_path.write_text(json.dumps(retained), encoding="utf-8")
    reopened = api.get(f"/api/authoring/drafts/{draft['draft_id']}")
    assert reopened.status_code == 200
    assert reopened.json()["coverage"]["registry_digest"] != "stale_snapshot"
    assert reopened.json()["coverage"]["items"]

    preview = api.get(f"/api/authoring/drafts/{draft['draft_id']}/preview")
    assert preview.status_code == 200
    preview_payload = preview.json()
    assert preview_payload["profile"] == "general_world_v2"
    assert preview_payload["world_spec"]["spec_id"] == "relief_port_coordination"
    assert preview_payload["composition_receipt"]["resolved_component_refs"]

    edited = deepcopy(document["proposal"])
    edited["analyst_question"] = "Can the parties dispatch safely before sunset?"
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


def test_dependency_review_repairs_an_omitted_exact_action_prerequisite(
    tmp_path: Path,
) -> None:
    proposal = _native_v2_proposal()
    review_calls = 0
    generation_inputs: list[str] = []

    def provider(*args: Any, **kwargs: Any) -> tuple[object, object]:
        nonlocal review_calls
        if kwargs["response_model"] is DependencyCompletenessReviewV1:
            review_calls += 1
            if review_calls == 1:
                return DependencyCompletenessReviewV1(
                    status="repair_required",
                    summary="Cargo movement omitted one stated prerequisite.",
                    missing_dependencies=[
                        MissingDependencyFindingV1(
                            exact_action_request_id="cargo_movement",
                            prerequisite_description="Customs clearance must gate movement.",
                            existing_ref="customs_release_status",
                            evidence="The analyst called customs clearance a genuine prerequisite.",
                            required_resolution="exact_guard",
                        )
                    ],
                ), SimpleNamespace(provider="test", cost=0.0)
            return DependencyCompletenessReviewV1(
                status="complete",
                summary="The repaired candidate covers every stated prerequisite.",
                missing_dependencies=[],
            ), SimpleNamespace(provider="test", cost=0.0)
        generation_inputs.append(str(args[1][1]["content"]))
        return AuthoredSimulationProposalEnvelopeV2(proposal=proposal), SimpleNamespace(
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
    generated = api.post(
        f"/api/authoring/drafts/{draft['draft_id']}/messages",
        json={
            "expected_revision": 0,
            "message_id": "review_repair",
            "message": "Model cargo movement where customs clearance is a genuine prerequisite.",
        },
    )

    assert generated.status_code == 200
    assert generated.json()["status"] == "ready_for_review"
    assert review_calls == 2
    assert len(generation_inputs) == 2
    assert "Dependency completeness review requires repair" in generation_inputs[1]
    assert [item["status"] for item in generated.json()["attempts"]] == [
        "accepted",
        "repair",
        "accepted",
        "accepted",
    ]


def test_live_general_authoring_runs_as_pollable_background_job(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setenv("CYBERNETIC_INFLUENCE_LIVE", "1")
    monkeypatch.setattr(
        api_module,
        "model_catalog",
        lambda: [{"model": "codex/gpt-5.6-luna"}],
    )
    proposal = _native_v2_proposal()

    def provider(*args: Any, **kwargs: Any) -> tuple[object, object]:
        del args
        if kwargs["response_model"] is DependencyCompletenessReviewV1:
            return DependencyCompletenessReviewV1(
                status="complete",
                summary="No stated exact-action prerequisite is omitted.",
                missing_dependencies=[],
            ), SimpleNamespace(provider="test", cost=0.0)
        return AuthoredSimulationProposalEnvelopeV2(proposal=proposal), SimpleNamespace(
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
    legacy = GeneralSimulationProposalV1.model_validate_json(
        FIXTURE.read_text(encoding="utf-8")
    )
    legacy.analysis_spec = legacy.analysis_spec or AnalysisSpecV1(
        analysis_id="waltzman_port_diagnostic",
        profile="waltzman_coordination_v1",
        purpose="Inspect influence-to-coordination signals in the retained run.",
    )
    proposal = adapt_authored_bundle_v1(
        legacy, run_id=f"{draft['draft_id']}_run"
    ).model_dump(mode="json")
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
    assert reopened["profile"] == "general_world_v2"
    assert reopened["execution_contract"] == "general_world_v2"
    assert reopened["authoring"]["proposal_kind"] == "general_world_v2"
    assert reopened["authoring"]["scenario_digest"]
    assert reopened["authoring"]["run_spec_digest"]
    assert reopened["model_calls"] == 15
    assert reopened["general_simulation"]["run_id"] == run_id
    assert "question" not in reopened["general_simulation"]
    assert reopened["run_evidence_bundle"]["run_id"] == run_id
    assert len(reopened["analysis_results"]) == 1
    assert reopened["analysis_results"][0]["coverage_status"] == "supported"
    assert all(
        "research_question" not in supplied
        for supplied in runtime_call.supplied_inputs
    )
    assert all("analysis_spec" not in supplied for supplied in runtime_call.supplied_inputs)
    assert reopened["general_simulation"]["adoption"]["engine_class"].endswith(
        "simultaneous.Simultaneous"
    )
    assert len(reopened["general_simulation"]["moments"]) == 3
    call_count = runtime_call.actor_counter
    summary = api.get(f"/api/runs/{run_id}/summary")
    assert summary.status_code == 200, summary.text
    summary_payload = summary.json()
    assert summary_payload["profile"] == "general_world_v2"
    assert summary_payload["execution_contract"] == "general_world_v2"
    assert summary_payload["authoring"]["question"]
    assert summary_payload["evidence_bundle"]["record_digest"]
    assert summary_payload["evidence_bundle"]["evidence_record_count"] > 0
    assert len(summary_payload["analysis_results"]) == 1
    assert summary_payload["causal_moments"] == 3
    assert summary_payload["participant_model_calls"] == 15
    assert summary_payload["simulation_replay"]["scenes"]
    assert not any(
        node["id"] == "collective_decision"
        for node in summary_payload["influence_network"]["nodes"]
    )
    assert summary_payload["simulation_replay"]["scenes"][0]["visible_node_ids"] == []
    assert summary_payload["simulation_replay"]["scenes"][0]["title"] == "Your review question"
    replay_scenes = summary_payload["simulation_replay"]["scenes"]
    assert len([scene for scene in replay_scenes if scene["kind"] == "event"]) == 3
    assert not any(scene["kind"] == "decisions" for scene in replay_scenes)
    assert not any(
        fact["label"] == "Positions"
        for scene in replay_scenes
        for fact in scene["facts"]
    )
    event_scenes = [scene for scene in replay_scenes if scene["kind"] == "event"]
    assert all(len(scene["visible_node_ids"]) <= 12 for scene in event_scenes)
    assert all(len(scene["visible_edge_ids"]) <= 18 for scene in event_scenes)
    assert all(
        any(fact["label"] == "World change" for fact in scene["facts"])
        for scene in event_scenes
    )
    assert not any(
        fact["label"] == "World transition"
        for scene in event_scenes
        for fact in scene["facts"]
    )

    before_revision = reopened["general_simulation"]["final_state"]["revision"]
    before_evidence = reopened["run_evidence_bundle"]["record_digest"]
    before_calls = reopened["model_calls"]
    exact_spec = AnalysisSpecV2(
        analysis_id="exact_terminal_review",
        profile="exact_outcome_v1",
        purpose="Read the retained terminal outcome without changing the run.",
        construct_definitions=["Terminal state is read from retained evidence."],
        required_evidence_kinds=["configuration", "terminal_state"],
        method_classes=["exact"],
        aggregation="Report the retained terminal evidence.",
        uncertainty="No inference beyond retained state.",
        limitations=["This does not establish a counterfactual."],
    )
    attached = api.post(
        f"/api/runs/{run_id}/analyses",
        json={"analysis_spec": exact_spec.model_dump(mode="json")},
    )
    assert attached.status_code == 200, attached.text
    assert len(attached.json()["analysis_results"]) == 2
    assert attached.json()["analysis_isolation_receipts"][-1][
        "simulation_unchanged"
    ]
    after_attachment = api.get(f"/api/runs/{run_id}").json()
    assert after_attachment["model_calls"] == before_calls
    assert after_attachment["general_simulation"]["final_state"]["revision"] == before_revision
    assert after_attachment["run_evidence_bundle"]["record_digest"] == before_evidence

    mutation_attempt = exact_spec.model_dump(mode="json")
    mutation_attempt["world_patch"] = {"operations": [{"op": "remove", "target": "port"}]}
    rejected = api.post(
        f"/api/runs/{run_id}/analyses",
        json={"analysis_spec": mutation_attempt},
    )
    assert rejected.status_code == 422
    after_rejection = api.get(f"/api/runs/{run_id}").json()
    assert after_rejection["model_calls"] == before_calls
    assert after_rejection["general_simulation"]["final_state"]["revision"] == before_revision
    assert after_rejection["run_evidence_bundle"]["record_digest"] == before_evidence

    removed = api.delete(f"/api/runs/{run_id}/analyses/exact_terminal_review")
    assert removed.status_code == 200, removed.text
    assert len(removed.json()["analysis_results"]) == 1
    assert removed.json()["analysis_isolation_receipts"][-1][
        "simulation_unchanged"
    ]
    assert replay_scenes[1]["facts"] == [
        {"label": "People", "value": "4"},
        {"label": "Other world components", "value": "17"},
    ]
    assert len(replay_scenes[1]["visible_node_ids"]) < len(
        summary_payload["influence_network"]["nodes"]
    )
    assert len(replay_scenes[-1]["visible_node_ids"]) < len(
        summary_payload["influence_network"]["nodes"]
    )
    outcome_scene = replay_scenes[-1]
    assert len(outcome_scene["visible_node_ids"]) <= 12
    assert len(outcome_scene["visible_edge_ids"]) <= 18
    assert outcome_scene["summary"] == "Retain the world while recording joint review."
    assert outcome_scene["facts"] == [
        {"label": "Committed transitions", "value": "3"},
        {"label": "Final world revision", "value": "3"},
    ]
    assert summary_payload["theory_analysis"] is None
    assert runtime_call.actor_counter == call_count
