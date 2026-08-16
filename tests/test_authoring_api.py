"""API proof for revisioned, approval-gated conversational authoring."""

from __future__ import annotations

import json
import time
from copy import deepcopy
from pathlib import Path
from threading import Event
from typing import Any, cast

from fastapi.testclient import TestClient
from llm_client import LLMCapabilityError, LLMQuotaExhaustedError
from pytest import MonkeyPatch
from test_authoring_compiler import _proposal
from test_authoring_information_campaign import information_campaign_proposal
from test_authoring_influence_network import influence_network_proposal

import cybernetic_influence.api as api_module
from cybernetic_influence.active_runtime import (
    ActiveSystemExecutionError,
    ModelCallEvidence,
)
from cybernetic_influence.api import create_app
from cybernetic_influence.analysis.theory_retention import (
    build_live_theory_analysis,
    theory_analysis_contract,
)
from cybernetic_influence.authoring.compiler import CompiledScenario, compile_scenario
from cybernetic_influence.authoring.coordination_review import (
    coordination_review_from_proposal,
)
from cybernetic_influence.authoring.examples import reviewed_coordination_proposal
from cybernetic_influence.authoring.models import (
    ResourceRequestWorkflowDraft,
    ScenarioDraftProposal,
)
from cybernetic_influence.authoring.service import (
    _prompt,
    _ProposalConsumer,
    _provider_candidate_from_proposal,
)
from cybernetic_influence.general_simulation.authoring_models import (
    GeneralAuthoringDiscussionV1,
)
from cybernetic_influence.run_configuration import (
    EffectiveRunLlmConfiguration,
    llm_client_revision,
)
from cybernetic_influence.run_store import RunStore


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
            allow_internal_scripted_coordination=True,
        )
    )


def test_influence_network_can_be_edited_approved_and_run(tmp_path: Path) -> None:
    proposal = influence_network_proposal()

    def proposer(*_args: object, **_kwargs: object) -> tuple[object, object]:
        return proposal, _Meta()

    api = TestClient(
        create_app(
            Path(__file__).resolve().parents[1] / "web",
            tmp_path / "runs",
            authoring_root=tmp_path / "drafts",
            authoring_call=proposer,
            allow_internal_scripted_coordination=True,
        )
    )
    draft = api.post("/api/authoring/legacy-drafts").json()
    drafted = api.post(
        f"/api/authoring/drafts/{draft['draft_id']}/messages",
        json={
            "expected_revision": 0,
            "message_id": "network_prompt",
            "message": "Model common and targeted election information.",
        },
    ).json()
    edited_proposal = deepcopy(drafted["proposal"])
    edited_proposal["workflow"]["collective_question"] = (
        "Should the city certify after reviewing the available information?"
    )
    edited = api.put(
        f"/api/authoring/drafts/{draft['draft_id']}/proposal",
        json={
            "expected_revision": 1,
            "edit_id": "network_edit",
            "proposal": edited_proposal,
        },
    )
    assert edited.status_code == 200
    assert edited.json()["revision"] == 2
    assert edited.json()["attempts"] == drafted["attempts"]
    assert edited.json()["messages"][-1]["source"] == "direct_proposal_edit"

    approved = api.post(
        f"/api/authoring/drafts/{draft['draft_id']}/approve",
        json={"expected_revision": 2},
    )
    assert approved.status_code == 200
    run = api.post(
        f"/api/authoring/drafts/{draft['draft_id']}/runs",
        json={"execution": "scripted"},
    )
    assert run.status_code == 200
    document = run.json()
    assert document["authoring"]["template_id"] == "influence_network_v1"
    assert document["outcome"]["final_status"] == "approved"
    summary = api.get(f"/api/runs/{document['run_id']}/summary")
    assert summary.status_code == 200
    compact = summary.json()
    assert compact["template_id"] == "influence_network_v1"
    assert {person["last_explicit_commitment"] for person in compact["participants"]} == {"support"}
    assert len(compact["rounds"]) == 2
    assert [len(item["decisions"]) for item in compact["rounds"]] == [3, 3]
    assert compact["evidence_counts"]["decision_steps"] == 6
    assert compact["coordination_measurement_readout"]["status"] == "available"
    assert compact["coordination_measurement_readout"]["measurement_id"].endswith(
        "_influence_network_exact_v1"
    )
    assert all(
        measure["source_event_ids"]
        for measure in compact["coordination_measurement_readout"]["exact_measures"]
    )
    network = compact["influence_network"]
    assert {node["kind"] for node in network["nodes"]} >= {
        "person",
        "information",
        "mechanism",
    }
    assert len(network["edges"]) == 10
    assert {edge["kind"] for edge in network["edges"]} == {
        "issued_information",
        "delivered_to",
        "contributed_to_decision",
    }
    assert all(edge["directed"] is True for edge in network["edges"])
    replay = compact["simulation_replay"]
    assert replay["contract"] == "simulation-replay.v1"
    assert replay["question"] == (
        "Should the city certify after reviewing the available information?"
    )
    assert [scene["kind"] for scene in replay["scenes"]] == [
        "question",
        "setup",
        "information",
        "decisions",
        "information",
        "decisions",
        "outcome",
    ]
    assert "targeted" not in replay["scenes"][1]["summary"].lower()
    first_information, second_information = replay["scenes"][2], replay["scenes"][4]
    assert "message_targeted_message" not in first_information["visible_node_ids"]
    assert "message_targeted_message" in second_information["visible_node_ids"]
    assert first_information["focus_edge_ids"]


def test_public_authoring_advertises_and_dispatches_only_certified_models(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    calls: list[object] = []

    def proposer(*args: object, **_kwargs: object) -> tuple[object, object]:
        calls.append(args)
        return influence_network_proposal(), _Meta()

    monkeypatch.setenv("CYBERNETIC_INFLUENCE_LIVE", "1")
    monkeypatch.setattr(
        api_module,
        "model_catalog",
        lambda: [{"model": "codex/gpt-5.6-luna"}],
    )
    api = TestClient(
        create_app(
            Path(__file__).resolve().parents[1] / "web",
            tmp_path / "runs",
            authoring_root=tmp_path / "drafts",
            authoring_call=proposer,
        )
    )

    authoring = api.get("/api/config").json()["authoring"]
    assert [item["model"] for item in authoring["models"]] == [
        "codex/gpt-5.6-luna"
    ]
    assert [
        item["model"] for item in authoring["structured_contract"]["model_options"]
    ] == ["codex/gpt-5.6-luna"]
    assert authoring["model"] == "codex/gpt-5.6-luna"

    draft_id = api.post("/api/authoring/legacy-drafts").json()["draft_id"]
    rejected = api.post(
        f"/api/authoring/drafts/{draft_id}/messages",
        json={
            "expected_revision": 0,
            "message_id": "uncertified_model",
            "message": "Model one collective decision.",
            "model": "codex/gpt-5.6-terra",
            "reasoning_effort": "medium",
        },
    )
    assert rejected.status_code == 422
    assert rejected.json()["detail"] == (
        "authoring model route is not currently certified"
    )
    assert calls == []


def test_draft_is_idempotent_revisioned_previewable_approved_and_runnable(tmp_path: Path) -> None:
    api = _client(tmp_path)
    created = api.post("/api/authoring/legacy-drafts")
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
    assert run.json()["authoring"]["description"]


def test_discussion_only_general_draft_can_be_reloaded_before_configuration(
    tmp_path: Path,
) -> None:
    def discuss_call(*_args: object, **_kwargs: object) -> tuple[object, object]:
        return GeneralAuthoringDiscussionV1(
            reply="I understand the outage world.",
            understood_summary="A city coordinates during a prolonged power outage.",
            material_questions=["What event should end the run?"],
        ), _Meta()

    api = TestClient(
        create_app(
            Path(__file__).resolve().parents[1] / "web",
            tmp_path / "runs",
            authoring_root=tmp_path / "drafts",
            authoring_call=discuss_call,
        )
    )
    draft_id = api.post("/api/authoring/drafts").json()["draft_id"]
    discussed = api.post(
        f"/api/authoring/drafts/{draft_id}/messages",
        json={
            "expected_revision": 0,
            "message_id": "outage_discussion",
            "message": "Simulate coordination during a city power outage.",
            "mode": "discuss",
        },
    )

    assert discussed.status_code == 200
    reloaded = api.get(f"/api/authoring/drafts/{draft_id}")
    assert reloaded.status_code == 200
    assert reloaded.json()["revision"] == 1
    assert reloaded.json()["proposal"] is None
    assert reloaded.json()["coverage"] is None
    assert reloaded.json()["configuration_graph"] is None
    assert reloaded.json()["messages"] == discussed.json()["messages"]


def test_reviewed_coordination_example_runs_reopens_and_isolates_analysis_corruption(
    tmp_path: Path,
) -> None:
    api = _client(tmp_path)

    drafted = api.post("/api/authoring/reviewed-coordination-drafts")
    assert drafted.status_code == 200
    draft = drafted.json()
    assert draft["revision"] == 1
    assert draft["status"] == "ready_for_review"
    assert draft["attempts"] == []
    assert draft["messages"] == []
    assert draft["proposal"]["workflow"]["template_id"] == (
        "coordination_decision_v1"
    )
    assert draft["proposal"]["workflow"]["meeting_days"] == [0, 1, 2, 3]
    assert draft["proposal"]["workflow"]["deadline_day"] == 4

    preview = api.get(
        f"/api/authoring/drafts/{draft['draft_id']}/preview"
    )
    assert preview.status_code == 200
    assert preview.json()["world"]["places"]
    assert {item["id"] for item in preview.json()["boundaries"]} == {
        "deployment_partnership",
        "pressure_source_ensemble",
    }

    approved = api.post(
        f"/api/authoring/drafts/{draft['draft_id']}/approve",
        json={"expected_revision": 1},
    )
    assert approved.status_code == 200
    run = api.post(
        f"/api/authoring/drafts/{draft['draft_id']}/runs",
        json={"execution": "scripted"},
    )
    assert run.status_code == 200
    retained = run.json()
    assert retained["status"] == "completed"
    assert retained["execution"] == "scripted"
    assert retained["model_calls"] == 0
    assert retained["cost"] == 0.0
    assert retained["world"]["places"]
    assert retained["timeline"]
    assert retained["narration"]["status"] == "completed"
    assert retained["boundaries"]
    assert len(retained["moments"]) <= 57
    assert not any(
        left["participants"] == ["exact_mechanisms"]
        and right["participants"] == ["exact_mechanisms"]
        for left, right in zip(
            retained["moments"],
            retained["moments"][1:],
            strict=False,
        )
    )
    modules = retained["theory_analysis"]["modules"]
    assert modules["decision_environment"]["status"] == "available"
    assert modules["collective_competence"]["status"] == "available"

    reopened = api.get(f"/api/runs/{retained['run_id']}")
    assert reopened.status_code == 200
    reopened_body = reopened.json()
    assert (
        reopened_body["theory_analysis"]["bundle"]["record_digest"]
        == retained["theory_analysis"]["bundle"]["record_digest"]
    )
    assert reopened_body["model_calls"] == 0
    assert sorted(
        {
            moment["logical_time"] // (24 * 60)
            for moment in reopened_body["narration"]["moments"]
        }
    ) == [0, 1, 2, 3]
    assert "_pressure_source" not in " ".join(
        moment["concise_narrative"]
        for moment in reopened_body["narration"]["moments"]
    )
    summary = api.get(f"/api/runs/{retained['run_id']}/summary")
    assert summary.status_code == 200
    compact = summary.json()
    assert compact["headline"] == retained["story"]["headline"]
    assert compact["summary"] == retained["story"]["summary"]
    assert len(compact["participants"]) == 5
    assert all(person["position"] for person in compact["participants"])
    assert {person["label"] for person in compact["participants"]} == {
        person["label"] for person in draft["proposal"]["people"]
    }
    assert compact["decision_steps"]
    assert compact["simulation_replay"]["contract"] == "simulation-replay.v1"
    assert compact["simulation_replay"]["scenes"][0]["kind"] == "question"
    assert compact["simulation_replay"]["scenes"][-1]["kind"] == "outcome"
    assert any(
        scene["kind"] == "event"
        for scene in compact["simulation_replay"]["scenes"]
    )
    assert {node["kind"] for node in compact["influence_network"]["nodes"]} >= {
        "person",
        "mechanism",
        "information",
    }
    assert compact["influence_network"]["edges"]
    assert all(
        edge["directed"] is True
        for edge in compact["influence_network"]["edges"]
    )
    assert any(
        scene["visible_edge_ids"]
        for scene in compact["simulation_replay"]["scenes"]
        if scene["kind"] == "event"
    )
    assert "events" not in compact
    assert "traces" not in compact

    run_path = tmp_path / "runs" / f"{retained['run_id']}.json"
    raw = json.loads(run_path.read_text(encoding="utf-8"))
    raw["theory_analysis"]["modules"]["collective_competence"]["readout"][
        "findings"
    ][0]["evidence_refs"] = ["event:event_999999"]
    run_path.write_text(json.dumps(raw), encoding="utf-8")

    isolated = api.get(f"/api/runs/{retained['run_id']}")
    assert isolated.status_code == 200
    isolated_body = isolated.json()
    assert isolated_body["status"] == "completed"
    assert isolated_body["story"] == retained["story"]
    assert (
        isolated_body["theory_analysis"]["modules"]["decision_environment"][
            "status"
        ]
        == "available"
    )
    assert (
        isolated_body["theory_analysis"]["modules"]["collective_competence"][
            "status"
        ]
        == "invalid"
    )


def test_production_authoring_api_rejects_scripted_coordination_execution(
    tmp_path: Path,
) -> None:
    api = TestClient(
        create_app(
            Path(__file__).resolve().parents[1] / "web",
            tmp_path / "runs",
            authoring_root=tmp_path / "drafts",
        )
    )
    draft = api.post("/api/authoring/reviewed-coordination-drafts").json()
    approved = api.post(
        f"/api/authoring/drafts/{draft['draft_id']}/approve",
        json={"expected_revision": draft["revision"]},
    )
    assert approved.status_code == 200

    response = api.post(
        f"/api/authoring/drafts/{draft['draft_id']}/runs",
        json={"execution": "scripted"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "coordination scenarios require live agent execution; "
        "scripted people are internal verification fixtures"
    )
    assert api.get("/api/runs").json()["runs"] == []


def test_completed_authored_run_resumes_only_missing_narration(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    api = _client(tmp_path)
    completed: dict[str, Any] = {
        "run_id": "run_123456789abc",
        "created_at": "2026-07-30T00:00:00+00:00",
        "status": "completed",
        "scenario": "coordination_decision_v1",
        "profile": "authored_typed_scenario",
        "arm": "stabilization",
        "execution": "scripted",
        "story": {"headline": "World outcome retained", "summary": "Retained."},
        "outcome": {"final_status": "no_decision_by_horizon"},
        "events": [
            {"event_id": "event_000001"},
            {"event_id": "event_000002"},
        ],
        "timeline": [],
        "boundaries": [],
        "moments": [
            {
                "activation": "exact_work_000001",
                "causal_time": 1,
                "causal_timestamp": "c1",
                "logical_time": 1,
                "participants": ["exact_mechanisms"],
                "event_ids": ["event_000001"],
                "exact_work_ids": ["exact_work_000001"],
                "representative_event_index": 0,
                "moment": 1,
            },
            {
                "activation": "exact_work_000002",
                "causal_time": 2,
                "causal_timestamp": "c2",
                "logical_time": 2,
                "participants": ["exact_mechanisms"],
                "event_ids": ["event_000002"],
                "exact_work_ids": ["exact_work_000002"],
                "representative_event_index": 1,
                "moment": 2,
            },
        ],
    }
    original_event_ids = [
        event["event_id"] for event in completed["events"]
    ]
    original_final_status = completed["outcome"]["final_status"]

    # Recreate the exact pre-fix retained shape: adjacent exact-only moments
    # made the narration preflight exceed its configured limit.
    moments = deepcopy(completed["moments"])

    revision = llm_client_revision()
    effective = EffectiveRunLlmConfiguration(
        model="openrouter/openai/gpt-5.6-terra",
        agent_reasoning_effort="medium",
        narrator_reasoning_effort="low",
        max_total_cost=0.74,
        maximum_narrator_calls=57,
        selection_basis="operator_selected",
        llm_client_revision=revision,
    )
    retained = {
        **completed,
        "execution": "live",
        "moments": moments,
        "agent_model_calls": 5,
        "model_calls": 5,
        "agent_cost": 0.12,
        "cost": 0.12,
        "llm_configuration": effective.model_dump(mode="json"),
        "narration": {
            "status": "unavailable",
            "reason": "preflight",
            "failure_boundary": {
                "kind": "call_limit_preflight",
                "required_calls": 66,
                "configured_max_calls": 57,
            },
            "model_calls": 0,
            "cost": 0.0,
            "moments": [],
            "calls": [],
        },
    }
    RunStore(tmp_path / "runs").save(retained)

    narrated = Event()
    observed_moments: list[list[dict[str, object]]] = []

    def fake_narration(
        document: dict[str, object],
        **_kwargs: object,
    ) -> dict[str, object]:
        projected = cast(list[dict[str, object]], document["moments"])
        observed_moments.append(deepcopy(projected))
        narrated.set()
        return {
            "status": "completed",
            "model_calls": 2,
            "cost": 0.03,
            "cost_fully_observable": True,
            "moments": [],
            "calls": [],
        }

    monkeypatch.setenv("CYBERNETIC_INFLUENCE_LIVE", "1")
    monkeypatch.setattr(
        api_module,
        "resolve_live_configuration",
        lambda _options: effective,
    )
    monkeypatch.setattr(api_module, "narrate_live_moments", fake_narration)

    started = api.post(f"/api/runs/{completed['run_id']}/resume")
    assert started.status_code == 202, started.text
    assert started.json()["status"] == "narrating"
    assert started.json()["narration_resume"]["world_replayed"] is False
    assert narrated.wait(timeout=5)

    for _ in range(200):
        reopened = api.get(f"/api/runs/{completed['run_id']}").json()
        if reopened["status"] == "completed":
            break
        time.sleep(0.01)
    else:
        raise AssertionError("narration-only resume did not complete")

    assert len(observed_moments) == 1
    assert not any(
        left["participants"] == ["exact_mechanisms"]
        and right["participants"] == ["exact_mechanisms"]
        for left, right in zip(
            observed_moments[0],
            observed_moments[0][1:],
            strict=False,
        )
    )
    assert reopened["narration_resume"]["status"] == "completed"
    assert reopened["narration_resume"]["world_replayed"] is False
    assert reopened["agent_model_calls"] == 5
    assert reopened["narration_model_calls"] == 2
    assert reopened["model_calls"] == 7
    assert reopened["agent_cost"] == 0.12
    assert reopened["narration_cost"] == 0.03
    assert reopened["cost"] == 0.15
    assert [event["event_id"] for event in reopened["events"]] == original_event_ids
    assert reopened["outcome"]["final_status"] == original_final_status

    idempotent = api.post(f"/api/runs/{completed['run_id']}/resume")
    assert idempotent.status_code == 200
    assert len(observed_moments) == 1


def test_semantic_coordination_authoring_compiles_without_provider_owned_ids(
    tmp_path: Path,
) -> None:
    calls: list[tuple[object, list[dict[str, str]], object]] = []
    semantic = coordination_review_from_proposal(reviewed_coordination_proposal())

    # mock-ok: Packet 24B requires provider-free structured-output coverage.
    def semantic_proposer(*args: object, **kwargs: object) -> tuple[object, object]:
        raw_messages = args[1]
        assert isinstance(raw_messages, list)
        calls.append((args[0], raw_messages, kwargs["response_model"]))
        candidate = semantic.model_copy(
            update={
                "description": (
                    "Five people review a shared early-warning deployment "
                    f"(revision {len(calls)})."
                )
            }
        )
        return {"proposal": candidate.model_dump(mode="json")}, _Meta()

    api = TestClient(
        create_app(
            Path(__file__).resolve().parents[1] / "web",
            tmp_path / "runs",
            authoring_root=tmp_path / "drafts",
            authoring_call=semantic_proposer,
        )
    )
    draft_id = api.post("/api/authoring/legacy-drafts").json()["draft_id"]
    first = api.post(
        f"/api/authoring/drafts/{draft_id}/messages",
        json={
            "expected_revision": 0,
            "message_id": "m1",
            "message": "Model a five-person early-warning deployment decision.",
        },
    )
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "ready_for_review"
    assert first.json()["proposal"]["workflow"]["template_id"] == (
        "coordination_decision_v1"
    )
    assert first.json()["proposal"]["people"][0]["entity_id"] == (
        "mission_coordinator"
    )

    second = api.post(
        f"/api/authoring/drafts/{draft_id}/messages",
        json={
            "expected_revision": first.json()["revision"],
            "message_id": "m2",
            "message": "Make the decision description more explicit.",
        },
    )
    assert second.status_code == 200, second.text
    assert len(calls) == 2
    assert all(item[2] is _ProposalConsumer for item in calls)
    second_user_prompt = calls[1][1][-1]["content"]
    assert "mission_coordinator" not in second_user_prompt
    assert "technical_source_route" not in second_user_prompt
    assert '"position_kind": "coordinator"' in second_user_prompt


def test_semantic_coordination_candidate_is_repaired_against_compiler_feedback(
    tmp_path: Path,
) -> None:
    calls = 0
    repair_prompt = ""
    semantic = coordination_review_from_proposal(reviewed_coordination_proposal())

    # mock-ok: This isolates the real repair loop around the typed provider seam.
    def repairable(*args: object, **_kwargs: object) -> tuple[object, object]:
        nonlocal calls, repair_prompt
        calls += 1
        if calls == 1:
            invalid = semantic.model_copy(
                update={"meeting_days": [0, 1, 2, 4], "deadline_day": 5}
            )
            return {"proposal": invalid.model_dump(mode="json")}, _Meta()
        messages = args[1]
        assert isinstance(messages, list)
        repair_prompt = str(messages[-1]["content"])
        return {"proposal": semantic.model_dump(mode="json")}, _Meta()

    api = TestClient(
        create_app(
            Path(__file__).resolve().parents[1] / "web",
            tmp_path / "runs",
            authoring_root=tmp_path / "drafts",
            authoring_call=repairable,
        )
    )
    draft_id = api.post("/api/authoring/legacy-drafts").json()["draft_id"]
    drafted = api.post(
        f"/api/authoring/drafts/{draft_id}/messages",
        json={
            "expected_revision": 0,
            "message_id": "m1",
            "message": "Model a five-person coordination decision.",
        },
    )
    assert drafted.status_code == 200, drafted.text
    assert [item["status"] for item in drafted.json()["attempts"]] == [
        "repair",
        "accepted",
    ]
    assert "currently supports meeting days [0, 1, 2, 3]" in repair_prompt
    assert "mission_coordinator" not in repair_prompt


def test_direct_coordination_edit_selects_analysis_without_an_llm_call(
    tmp_path: Path,
) -> None:
    provider_calls = 0

    # mock-ok: The assertion is that a direct semantic edit never reaches this seam.
    def counted(*_args: object, **_kwargs: object) -> tuple[object, object]:
        nonlocal provider_calls
        provider_calls += 1
        return _proposal(), _Meta()

    api = TestClient(
        create_app(
            Path(__file__).resolve().parents[1] / "web",
            tmp_path / "runs",
            authoring_root=tmp_path / "drafts",
            authoring_call=counted,
            allow_internal_scripted_coordination=True,
        )
    )
    draft = api.post("/api/authoring/reviewed-coordination-drafts").json()
    configuration = coordination_review_from_proposal(
        ScenarioDraftProposal.model_validate(draft["proposal"])
    ).model_dump(mode="json")
    configuration["title"] = "Regional early-warning deployment review"
    configuration["condition"] = "heterogeneous_pressure"
    configuration["analysis_ids"] = ["levin_collective_competence_v1"]
    concerns = configuration["concerns"]
    assert isinstance(concerns, list)
    concerns[0]["content"] = "Independent sensitivity estimates remain uncertain."
    edited = api.put(
        f"/api/authoring/drafts/{draft['draft_id']}/coordination-configuration",
        json={
            "expected_revision": draft["revision"],
            "edit_id": "coordination-edit-1",
            "configuration": configuration,
        },
    )
    assert edited.status_code == 200, edited.text
    body = edited.json()
    assert provider_calls == 0
    assert body["revision"] == 2
    assert body["status"] == "ready_for_review"
    assert body["approval"] is None
    assert body["messages"][-1]["source"] == "direct_coordination_edit"
    assert body["messages"][-1]["trace_ids"] == []
    assert body["proposal"]["title"] == "Regional early-warning deployment review"
    assert body["proposal"]["workflow"]["stabilizing_resources"] == []
    assert body["proposal"]["workflow"]["analysis"]["analysis_ids"] == [
        "levin_collective_competence_v1"
    ]
    assert api.get(
        f"/api/authoring/drafts/{draft['draft_id']}/preview"
    ).status_code == 200

    duplicate = api.put(
        f"/api/authoring/drafts/{draft['draft_id']}/coordination-configuration",
        json={
            "expected_revision": draft["revision"],
            "edit_id": "coordination-edit-1",
            "configuration": configuration,
        },
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["revision"] == body["revision"]
    assert provider_calls == 0

    approved = api.post(
        f"/api/authoring/drafts/{draft['draft_id']}/approve",
        json={"expected_revision": body["revision"]},
    )
    assert approved.status_code == 200
    run = api.post(
        f"/api/authoring/drafts/{draft['draft_id']}/runs",
        json={"execution": "scripted"},
    )
    assert run.status_code == 200, run.text
    modules = run.json()["theory_analysis"]["modules"]
    assert modules["decision_environment"]["status"] == "not_selected"
    assert modules["collective_competence"]["status"] == "available"


def test_live_theory_projection_retains_selection_without_analysis_calls() -> None:
    proposal = reviewed_coordination_proposal()
    workflow = proposal.workflow
    assert workflow.template_id == "coordination_decision_v1"
    proposal = proposal.model_copy(
        update={
            "workflow": workflow.model_copy(
                update={
                    "analysis": workflow.analysis.model_copy(
                        update={
                            "analysis_ids": [
                                "levin_collective_competence_v1"
                            ]
                        }
                    )
                }
            )
        }
    )
    compiled = compile_scenario(proposal)
    result = compiled.run_scripted(run_id="live_theory_projection")
    theory = build_live_theory_analysis(
        compiled,
        result,
        model="openrouter/openai/gpt-5.6-terra",
        reasoning_effort="medium",
        per_call_budget=0.05,
        per_run_budget=0.20,
    )

    bundle = cast(dict[str, Any], theory["bundle"])
    modules = cast(dict[str, dict[str, object]], theory["modules"])
    assert bundle["run_spec"]["execution_mode"] == "live"
    assert modules["decision_environment"]["status"] == "not_selected"
    assert modules["collective_competence"]["status"] == "available"
    assert theory_analysis_contract()["maximum_model_calls_per_run"] == 0


def test_authoring_and_theory_call_contracts_are_exact_and_provider_free(
    tmp_path: Path,
) -> None:
    config = _client(tmp_path).get("/api/config").json()
    authoring = config["authoring"]["structured_contract"]
    assert authoring["task"] == "cybernetic_influence_v3_scenario_draft"
    assert authoring["prompt_version"] == "scenario_draft.v8"
    assert len(authoring["prompt_digest"]) == 64
    assert len(authoring["schema_digest"]) == 64
    assert authoring["maximum_attempts_per_message"] == 3
    assert authoring["maximum_output_tokens_per_attempt"] == 8000
    assert authoring["maximum_cost_per_attempt"] == 0.10
    assert authoring["maximum_usage_based_cost_per_message"] == 0.30
    assert {
        item["model"] for item in authoring["model_options"]
    } == {
        "codex/gpt-5.6-terra",
        "codex/gpt-5.6-luna",
        "openrouter/openai/gpt-5.6-terra",
        "openrouter/openai/gpt-5.6-sol",
    }
    system_prompt, _ = _prompt(
        message="Describe one coordination problem.",
        prior={},
        repair_feedback=None,
        candidate=None,
    )
    assert "does not directly broadcast one source message" in system_prompt
    assert "never describe a one-recipient source as a mass broadcast" in system_prompt

    analysis = config["theory_analysis"]
    assert analysis["maximum_model_calls_per_run"] == 0
    assert analysis["route"] is None
    assert analysis["reasoning_effort"] is None
    assert len(analysis["schemas"]["run_evidence_bundle_v1"]) == 64
    assert len(analysis["schemas"]["framework_readout_v1"]) == 64
    assert {
        item["analysis_id"] for item in analysis["modules"]
    } == {
        "waltzman_decision_environment_v1",
        "levin_collective_competence_v1",
    }


def test_direct_coordination_edit_rejects_invalid_cadence_and_stale_revision(
    tmp_path: Path,
) -> None:
    api = _client(tmp_path)
    draft = api.post("/api/authoring/reviewed-coordination-drafts").json()
    configuration = coordination_review_from_proposal(
        ScenarioDraftProposal.model_validate(draft["proposal"])
    ).model_dump(mode="json")
    invalid = json.loads(json.dumps(configuration))
    invalid["meeting_days"] = [0, 1, 2, 4]
    invalid["deadline_day"] = 5
    rejected = api.put(
        f"/api/authoring/drafts/{draft['draft_id']}/coordination-configuration",
        json={
            "expected_revision": draft["revision"],
            "edit_id": "invalid-cadence",
            "configuration": invalid,
        },
    )
    assert rejected.status_code == 422
    assert "currently supports meeting days [0, 1, 2, 3]" in rejected.text
    assert api.get(
        f"/api/authoring/drafts/{draft['draft_id']}"
    ).json()["revision"] == draft["revision"]

    saved = api.put(
        f"/api/authoring/drafts/{draft['draft_id']}/coordination-configuration",
        json={
            "expected_revision": draft["revision"],
            "edit_id": "valid-edit",
            "configuration": configuration,
        },
    )
    assert saved.status_code == 200
    stale = api.put(
        f"/api/authoring/drafts/{draft['draft_id']}/coordination-configuration",
        json={
            "expected_revision": draft["revision"],
            "edit_id": "stale-edit",
            "configuration": configuration,
        },
    )
    assert stale.status_code == 409


def test_authored_live_run_requires_authorization_and_live_options(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.delenv("CYBERNETIC_INFLUENCE_LIVE", raising=False)
    api = _client(tmp_path)
    draft_id = api.post("/api/authoring/legacy-drafts").json()["draft_id"]
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
    monkeypatch.setattr(
        api_module,
        "model_catalog",
        lambda: [
            {"model": "codex/gpt-5.6-luna"},
            {"model": "openrouter/openai/gpt-5.6-terra"},
            {"model": effective.model},
        ],
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
    draft_id = api.post("/api/authoring/legacy-drafts").json()["draft_id"]
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

    assert failed.status_code == 202
    run_id = failed.json()["run_id"]
    retained: dict[str, object] | None = None
    for _ in range(200):
        candidate = api.get(f"/api/runs/{run_id}").json()
        if candidate["status"] == "failed":
            retained = candidate
            break
        time.sleep(0.01)
    assert retained is not None
    assert retained["status"] == "failed"
    run = api.get(f"/api/runs/{run_id}").json()
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
    # A worker-side provider failure cannot strand the process-wide live lock.
    retry = api.post(
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
    assert retry.status_code == 202, retry.text


def test_authored_coordination_run_exposes_parallelism_and_stop_control(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("CYBERNETIC_INFLUENCE_LIVE", "1")
    effective = EffectiveRunLlmConfiguration(
        model="codex/gpt-5.6-luna",
        agent_reasoning_effort="medium",
        narrator_reasoning_effort="low",
        max_total_cost=0.74,
        selection_basis="operator_selected",
        llm_client_revision="package:0.7.0",
        billing_mode="subscription_included",
    )
    monkeypatch.setattr(
        api_module,
        "resolve_live_configuration",
        lambda _options: effective,
    )
    entered = Event()
    stop_observed = Event()
    release = Event()
    captured: dict[str, object] = {}

    def block_until_stopped(
        _compiled: CompiledScenario,
        **kwargs: object,
    ) -> object:
        captured.update(kwargs)
        entered.set()
        stop_requested = cast(Any, kwargs["stop_requested"])
        for _ in range(200):
            if stop_requested():
                stop_observed.set()
                break
            time.sleep(0.01)
        release.wait(2)
        raise RuntimeError("forced completion after stop wiring proof")

    monkeypatch.setattr(CompiledScenario, "run_live", block_until_stopped)
    api = _client(tmp_path)
    draft = api.post("/api/authoring/reviewed-coordination-drafts").json()
    approved = api.post(
        f"/api/authoring/drafts/{draft['draft_id']}/approve",
        json={"expected_revision": draft["revision"]},
    )
    assert approved.status_code == 200

    started = api.post(
        f"/api/authoring/drafts/{draft['draft_id']}/runs",
        json={
            "execution": "live",
            "llm_options": {
                "model": effective.model,
                "agent_reasoning_effort": "medium",
                "max_total_cost": 0.74,
            },
        },
    )
    assert started.status_code == 202
    run_id = started.json()["run_id"]
    assert entered.wait(2)
    assert captured["participant_concurrency"] == 5
    assert callable(captured["stop_requested"])

    first_stop = api.post(f"/api/runs/{run_id}/stop")
    assert first_stop.status_code == 200
    assert first_stop.json()["status"] == "stop_requested"
    assert stop_observed.wait(2)
    repeated_stop = api.post(f"/api/runs/{run_id}/stop")
    assert repeated_stop.status_code == 200
    release.set()

    for _ in range(200):
        retained = api.get(f"/api/runs/{run_id}").json()
        if retained["status"] == "failed":
            break
        time.sleep(0.01)
    assert retained["status"] == "failed"


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
        ("Terra · subscription", "codex/gpt-5.6-terra"),
        ("Luna · subscription", "codex/gpt-5.6-luna"),
        ("Terra · OpenRouter", "openrouter/openai/gpt-5.6-terra"),
        ("Sol", "openrouter/openai/gpt-5.6-sol"),
    ]
    assert config["reasoning_efforts"] == ["none", "low", "medium", "high", "xhigh", "max"]
    assert config["models"][0]["reasoning_efforts"] == ["medium"]
    assert config["models"][0]["default_reasoning_effort"] == "medium"

    draft_id = api.post("/api/authoring/legacy-drafts").json()["draft_id"]
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


def test_luna_rejects_unsupported_authoring_effort_before_dispatch(tmp_path: Path) -> None:
    calls: list[object] = []

    def proposer(*args: object, **_kwargs: object) -> tuple[object, object]:
        calls.append(args)
        return _proposal(), _Meta()

    api = TestClient(
        create_app(
            Path(__file__).resolve().parents[1] / "web",
            tmp_path / "runs",
            authoring_root=tmp_path / "drafts",
            authoring_call=proposer,
        )
    )
    draft_id = api.post("/api/authoring/legacy-drafts").json()["draft_id"]
    response = api.post(
        f"/api/authoring/drafts/{draft_id}/messages",
        json={
            "expected_revision": 0,
            "message_id": "m1",
            "message": "Model equipment checkout.",
            "model": "codex/gpt-5.6-luna",
            "reasoning_effort": "max",
        },
    )

    assert response.status_code == 422
    assert "choose one of low, medium, high" in response.text
    assert calls == []


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
    draft_id = api.post("/api/authoring/legacy-drafts").json()["draft_id"]
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
    draft_id = api.post("/api/authoring/legacy-drafts").json()["draft_id"]
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
    draft_id = api.post("/api/authoring/legacy-drafts").json()["draft_id"]
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
    draft_id = api.post("/api/authoring/legacy-drafts").json()["draft_id"]
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
    draft_id = api.post("/api/authoring/legacy-drafts").json()["draft_id"]
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
    legacy = schema["$defs"]["_LegacyProposalConsumer"]
    assert legacy["properties"]["placements"]["type"] == "array"
    assert "template_id" in schema["$defs"]["_WorkflowConsumer"]["required"]
    assert "template_id" in schema["$defs"]["_InformationCampaignWorkflowConsumer"]["required"]
    assert legacy["properties"]["workflow"]["discriminator"]["propertyName"] == "template_id"
    assert schema["additionalProperties"] is False
    assert schema["required"] == ["proposal"]
    coordination = schema["$defs"]["CoordinationScenarioReview"]
    assert {
        "template_id",
        "people",
        "concerns",
        "collective_goal",
        "places",
        "analytical_boundaries",
        "analysis_ids",
    } <= set(coordination["properties"])
    serialized_coordination = json.dumps(coordination)
    for compiler_owned_field in (
        "entity_id",
        "goal_id",
        "information_id",
        "route_id",
        "mechanism_id",
        "implementation_id",
    ):
        assert compiler_owned_field not in serialized_coordination


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
    assert "use each position_kind exactly once" in system
    assert "do not supply entity IDs" in system
    assert "analytical views, never minds or executors" in system


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
    draft_id = api.post("/api/authoring/legacy-drafts").json()["draft_id"]
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
    draft_id = api.post("/api/authoring/legacy-drafts").json()["draft_id"]
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
    assert config["model"] == "codex/gpt-5.6-luna"
    assert config["reasoning_effort"] == "medium"
    draft_id = api.post("/api/authoring/legacy-drafts").json()["draft_id"]
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
    progress = api.get(f"/api/runs/{run.json()['run_id']}/progress")
    assert progress.status_code == 200
    records = progress.json()["records"]
    assert records[0]["kind"] == "activation_started"
    assert any(
        item["kind"] == "causal_moment_committed" for item in records
    )
    assert all("scenario" not in item for item in records)


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
    draft_id = api.post("/api/authoring/legacy-drafts").json()["draft_id"]
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
    draft_id = api.post("/api/authoring/legacy-drafts").json()["draft_id"]
    body = api.post(
        f"/api/authoring/drafts/{draft_id}/messages",
        json={"expected_revision": 0, "message_id": "m1", "message": "Model checkout."},
    ).json()
    assert body["status"] == "ready_for_review"
    assert [attempt["status"] for attempt in body["attempts"]] == ["repair", "accepted"]
    assert "scenario_id" in repair_prompt
    assert "timing_assumptions.0.minutes" in repair_prompt
