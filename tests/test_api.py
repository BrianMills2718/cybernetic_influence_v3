"""End-to-end gates for the clean walking simulator."""

from copy import deepcopy
from pathlib import Path
from threading import Event, Thread
import time
from typing import Any, cast
from unittest.mock import patch

from fastapi.testclient import TestClient
import pytest

from cybernetic_influence.active_runtime import (
    ActiveStepResult,
    ActiveSystemBinding,
    ScriptedActiveSystem,
)
from cybernetic_influence.api import create_app
from cybernetic_influence.run_configuration import EffectiveRunLlmConfiguration
from cybernetic_influence.run_store import RunStore
from cybernetic_influence.scenarios.coordination_decision import (
    PERSON_IDS,
    baseline_coordination_fixture,
    coordination_runtime_fixture,
    run_scripted_coordination,
)
from cybernetic_influence.scenarios.service_desk import (
    RuntimePaused,
    run_event_driven_service_desk as original_run_service_desk,
    service_desk_arm_configurations,
    service_desk_fixture,
    service_desk_native_bindings,
    service_desk_scripted_bindings,
)


ROOT = Path(__file__).resolve().parents[1]


def client(run_root: Path) -> TestClient:
    return TestClient(create_app(ROOT / "web", run_root))


def test_config_and_static_ui_are_operator_first(tmp_path: Path) -> None:
    with (
        patch.dict(
            "os.environ",
            {
                "OPENROUTER_API_KEY": "test-key",
                "CYBERNETIC_INFLUENCE_CERT_TERRA": "test-canary-terra",
                "CYBERNETIC_INFLUENCE_CERT_DEEPSEEK_V4_FLASH": "test-canary-deepseek",
                "CYBERNETIC_INFLUENCE_CERT_COORDINATION_TERRA": "test-coordination-terra",
                "CYBERNETIC_INFLUENCE_CERT_COORDINATION_DEEPSEEK_V4_FLASH": "test-coordination-deepseek",
            },
        ),
        patch(
            "cybernetic_influence.run_configuration._validated_certification_basis",
            side_effect=lambda _model, configured: configured or None,
        ),
        patch(
            "cybernetic_influence.run_configuration._validated_coordination_certification_basis",
            side_effect=lambda _model, configured: configured or None,
        ),
    ):
        api = client(tmp_path)
        config = api.get("/api/config")
    assert config.status_code == 200
    assert config.json()["version"] == "0.13.0"
    assert config.json()["build_commit"] == "development"
    assert config.json()["model"] == "openrouter/deepseek/deepseek-v4-flash"
    assert config.json()["reasoning_effort"] == "none"
    assert config.json()["profiles"] == ["position_context", "procedural_control"]
    assert set(config.json()["scenarios"]) == {
        "service_desk",
        "physical_access",
        "purchase_payment",
        "coordination_decision",
    }
    coordination = config.json()["scenarios"]["coordination_decision"]
    assert coordination["supports_live"] is True
    assert coordination["live_model_ids"] == [
        "openrouter/openai/gpt-5.6-terra",
        "openrouter/deepseek/deepseek-v4-flash",
    ]
    assert {item["id"] for item in coordination["arms"]} == {
        "baseline",
        "heterogeneous_pressure",
        "stabilization",
    }
    assert config.json()["scenarios"]["physical_access"]["arms"][0]["description"]
    controls = config.json()["scenarios"]["service_desk"]["run_control_options"]
    assert controls["default_terminal_condition_ids"] == ["confirmed_closure"]
    assert controls["default_horizon"] >= 87
    assert [choice["model"] for choice in config.json()["live_options"]["models"]] == [
        "openrouter/openai/gpt-5.6-terra",
        "openrouter/deepseek/deepseek-v4-flash",
    ]
    deepseek = config.json()["live_options"]["models"][1]
    assert deepseek["agent_reasoning_efforts"] == ["none", "high", "xhigh"]
    assert deepseek["experimental_agent_reasoning_efforts"] == ["high", "xhigh"]
    assert config.json()["scenarios"]["service_desk"]["assumptions"]
    assert config.json()["scenarios"]["service_desk"]["known_omissions"]
    assert config.json()["scenarios"]["service_desk"]["fidelity_questions"]
    assert config.json()["scenarios"]["service_desk"]["representation_summary"].startswith(
        "A customer cannot log in after resetting a password."
    )
    assert config.json()["cost_baselines"] == []
    assert "No authored spatial topology is present." not in config.json()["scenarios"]["service_desk"]["known_omissions"]
    assert "authored topology" in config.json()["scenarios"]["service_desk"]["known_omissions"][0]
    page = api.get("/")
    assert page.status_code == 200
    assert page.headers["content-security-policy"].startswith("default-src 'self'")
    assert page.headers["x-content-type-options"] == "nosniff"
    assert "Scenario condition" in page.text
    assert "Simulation map" in page.text
    assert "Live evidence" in page.text
    assert 'id="narrative-section"' in page.text
    assert "Spatial topology" in page.text
    assert "Configured interaction pathways" in page.text
    assert "Realized causal graph" in page.text
    assert 'id="analytical-scale-control"' in page.text
    assert 'id="analytical-boundary"' in page.text
    assert 'id="analytical-scale-toggle"' in page.text
    assert "Account for the selected moment" in page.text
    assert "What happened" in page.text
    assert "Advanced" in page.text
    assert 'id="initial-situation"' in page.text
    assert 'id="narrative-concise"' in page.text
    assert 'id="narrative-detailed"' in page.text
    assert "Narrative detail" in page.text
    assert ">Detailed story</button>" in page.text
    assert 'id="detailed-narrative"' in page.text
    assert "People and groups" in page.text
    assert "Follow a participant or view the team as a whole" in page.text
    assert "analytical composites did" not in page.text
    assert "Play simulation" in page.text
    assert 'id="lifecycle-help"' in page.text
    assert "Run history" in page.text
    assert "Each entry includes its exact run ID." in page.text
    assert "Read me" in page.text
    assert "Author scenario" in page.text
    assert "Describe what you want" in page.text
    assert "Choose the model and thinking level independently for every message" in page.text
    assert 'id="authoring-view"' in page.text
    assert 'id="authoring-chat"' in page.text
    assert 'id="authoring-model"' in page.text
    assert 'id="authoring-reasoning"' in page.text
    assert 'id="authoring-people"' in page.text
    assert "editable scenario assumptions" in page.text
    assert "Copy saved draft link" in page.text
    assert 'id="authoring-spatial-layout"' in page.text
    assert 'id="authoring-causal-layout"' in page.text
    assert 'id="authoring-trajectory-layout"' in page.text
    assert "How to read a cybernetic simulation" in page.text
    assert 'id="model"' in page.text
    assert 'id="reasoning"' in page.text
    assert 'id="max-cost"' in page.text
    assert "Hard authorization cap" in page.text
    assert 'aria-controls="model-help"' in page.text
    assert 'id="history-view"' in page.text
    assert 'id="simulation-view"' in page.text
    assert "/assets/graph-canvas.js" in page.text
    assert "/assets/graph-canvas.css" in page.text
    assert "V2 Inspect" not in page.text
    assert "Choose a moment" in page.text
    graph_script = api.get("/assets/graph-canvas.js")
    graph_styles = api.get("/assets/graph-canvas.css")
    app_script = api.get("/assets/app.js")
    app_styles = api.get("/assets/styles.css")
    assert graph_script.status_code == 200
    assert graph_styles.status_code == 200
    assert app_script.status_code == 200
    assert app_styles.status_code == 200
    retained_render = app_script.text.split("function render(run) {", 1)[1].split(
        "$('#event-slider')", 1
    )[0]
    assert "$('#map-section').hidden = false" in retained_render
    assert "renderGraph()" in retained_render
    assert graph_script.headers["cache-control"] == "no-cache"
    assert graph_styles.headers["cache-control"] == "no-cache"
    assert app_script.headers["cache-control"] == "no-cache"
    assert app_styles.headers["cache-control"] == "no-cache"
    assert len(graph_script.content) > 250_000
    assert b".react-flow" in graph_styles.content
    assert b"logical entities are outside this spatial projection" in graph_script.content
    assert b".scrollIntoView" not in app_script.content
    assert b"Evidence supplied to the narrator" in app_script.content
    assert b"not proof of entailment" in app_script.content
    assert b"Configured interaction pathways show scenario-configured" in app_script.content
    assert b"function renderLifecycleControls" in app_script.content
    assert b"function applyButtonTooltips" in app_script.content
    assert b"new MutationObserver" in app_script.content
    assert b"renderLifecycleControls(current)" in app_script.content
    assert b"function loadScenarioPreview" in app_script.content
    assert b"/api/authoring/drafts" in app_script.content
    assert b"function renderAuthoring" in app_script.content
    assert b"function renderAuthoringChat" in app_script.content
    assert b"function renderAuthoringPeople" in app_script.content
    assert b"/people/${encodeURIComponent(person.entity_id)}" in app_script.content
    assert b"reasoning_effort:$('#authoring-reasoning').value" in app_script.content
    assert b"let previewRequestSerial = 0" in app_script.content
    assert b"requestSerial !== previewRequestSerial" in app_script.content
    assert b"/api/scenarios/${encodeURIComponent(scenario)}/preview" in app_script.content
    assert b"the realized causal graph appears only after events are committed" in app_script.content
    assert b"$('#analytical-scale-toggle').onclick" in app_script.content
    assert b"selectedGraphView = 'causal'" in app_script.content
    assert b"how did this condition change the path to safe closure" in app_script.content
    assert b"modeled elapsed time T+" in app_script.content
    assert b"aria-pressed" in app_script.content
    assert b"showTraceInPlace(button.dataset.person)" in app_script.content
    assert b"trace.style.minHeight" in app_script.content
    assert b"kind:edge.kind || 'connection'" in app_script.content
    assert b"function pollLiveRun" in app_script.content
    assert b"after_sequence=${liveProgressSequence}" in app_script.content
    assert b"function applyLiveProgress" in app_script.content
    assert b"function renderBoundaryActivity" in app_script.content
    assert b"Show supporting events" in app_script.content
    assert b"What reached the group" in app_script.content
    assert b"Technical details" in app_script.content
    assert b"through_event_id=" in app_script.content
    assert b"Nothing has left the group yet." in app_script.content
    assert b"This saved run predates group-flow summaries" in app_script.content
    # The shared canvas owns playback; the shell supplies retained updates and
    # contains no catalog-scenario branch for their visual interpretation.
    assert b"liveCue" in graph_script.content
    assert b"animateMotion" in graph_script.content
    assert b"prefers-reduced-motion" in graph_styles.content


def test_scenario_preview_exposes_the_initial_map_without_creating_a_run(tmp_path: Path) -> None:
    api = client(tmp_path)
    response = api.get(
        "/api/scenarios/service_desk/preview",
        params={"arm_id": "no_direct_path", "cognition_profile": "position_context"},
    )

    assert response.status_code == 200, response.text
    preview = response.json()
    assert preview["preview"] is True
    assert preview["status"] == "ready"
    assert preview["timeline"] == []
    assert preview["trajectory"] == {"nodes": [], "edges": []}
    assert preview["world"]["places"]
    assert preview["world"]["snapshots"][str(preview["initial_revision"])]["placements"]
    assert preview["nodes"]
    assert any(edge["enabled"] is False for edge in preview["edges"])
    assert api.get("/api/runs").json()["runs"] == []


def test_scripted_position_context_run_is_zero_cost_and_inspectable(tmp_path: Path) -> None:
    response = client(tmp_path).post(
        "/api/runs",
        json={
            "cognition_profile": "position_context",
            "arm_id": "baseline",
            "execution": "scripted",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "completed"
    assert body["model_calls"] == 0
    assert body["cost"] == 0
    assert body["narration"]["status"] == "not_requested"
    assert body["narration_model_calls"] == 0
    assert len(body["moments"]) == body["outcome"]["causal_moment_count"]
    assert body["completion"]["reason"] == "terminal_condition_met"
    assert body["completion"]["condition_ids"] == ["confirmed_closure"]
    assert body["outcome"]["final_status"] == "closed_confirmed"
    assert body["outcome"]["causal_moment_count"] > body["outcome"][
        "participant_activation_count"
    ]
    assert body["time_unit"] == "process_tick"
    assert [moment["causal_time"] for moment in body["moments"]] == list(
        range(1, len(body["moments"]) + 1)
    )
    assert [moment["causal_timestamp"] for moment in body["moments"]] == [
        f"c{index}" for index in range(1, len(body["moments"]) + 1)
    ]
    causal_events = [
        event for event in body["timeline"] if event["activation"] is not None
    ]
    assert len(
        {event["causal_timestamp"] for event in causal_events}
    ) == len(causal_events)
    assert all(
        event["causal_timestamp"].startswith(
            f"c{event['causal_time']}."
        )
        for event in causal_events
    )
    assert body["outcome"]["remediation_moment"] is not None
    assert body["outcome"]["confirmed_closure_moment"] is not None
    assert body["outcome"]["remediation_moment"] < body["outcome"]["confirmed_closure_moment"]
    assert body["outcome"]["autonomous_activation_count"] == 3
    assert body["outcome"]["exact_process_activation_count"] == 3
    assert any(
        len({trace["person"] for trace in body["traces"] if trace["activation"] == activation})
        > 1
        for activation in {trace["activation"] for trace in body["traces"]}
    )
    assert body["story"]["summary"]
    assert {entry["person"] for entry in body["traces"]} == {
        "triager",
        "specialist",
        "supervisor",
        "remediation_process",
    }
    autonomous_triager = next(
        trace
        for trace in body["traces"]
        if trace["person"] == "triager"
        and any(
            cause["kind"] == "internal_wake"
            for cause in trace["activation_causes"]
        )
    )
    assert autonomous_triager["observations"] == []
    process_traces = [
        trace
        for trace in body["traces"]
        if trace["person"] == "remediation_process"
    ]
    assert len(process_traces) == 3
    assert all(
        trace["participant_kind"] == "state_machine"
        and trace["model_call_count"] == 0
        for trace in process_traces
    )
    process_action = next(
        event
        for event in body["timeline"]
        if event["summary"]
        == "Exact remediation process advanced the invalidation."
    )
    assert process_action["person"] == "remediation_process"
    assert any(node["id"] == "incident_17" for node in body["nodes"])
    assert body["events"]
    assert body["snapshots"]
    assert [event["sequence"] for event in body["timeline"]] == list(range(len(body["timeline"])))
    assert len({event["event_id"] for event in body["timeline"]}) == len(body["timeline"])
    attempted = next(event for event in body["timeline"] if event["kind"] == "action_attempted")
    assert attempted["person"] in attempted["focus_ids"]
    routed = next(event for event in body["timeline"] if event["kind"] == "effect_routed")
    assert routed["focus_edges"]
    assert {step["kind"] for step in body["story"]["steps"]} == {"action_attempted"}
    assert body["llm_configuration"] is None


def test_scripted_run_rejects_live_options_before_dispatch(tmp_path: Path) -> None:
    response = client(tmp_path).post(
        "/api/runs",
        json={
            "execution": "scripted",
            "llm_options": {
                "model": "openrouter/openai/gpt-5.6-terra",
                "agent_reasoning_effort": "medium",
                "max_total_cost": 0.20,
            },
        },
    )
    assert response.status_code == 422
    assert "only to live" in response.json()["detail"]
    assert client(tmp_path).get("/api/runs").json()["runs"] == []


def test_service_desk_run_control_is_compiled_and_retained(tmp_path: Path) -> None:
    api = client(tmp_path)
    rejected = api.post(
        "/api/runs",
        json={"run_control": {"terminal_condition_ids": ["arbitrary_fact"]}},
    )
    assert rejected.status_code == 422
    assert "unknown terminal condition" in rejected.json()["detail"]

    bounded = api.post(
        "/api/runs",
        json={"run_control": {"modeled_time_horizon": 0}},
    )
    assert bounded.status_code == 200, bounded.text
    body = bounded.json()
    assert body["completion"]["reason"] == "modeled_time_horizon"
    assert body["run_control"]["modeled_time_horizon"]["logical_time"] == 0
    assert body["outcome"]["final_status"] != "closed_confirmed"


def test_live_options_are_applied_and_retained(tmp_path: Path) -> None:
    captured_bindings: list[tuple[str, str]] = []
    captured_narration: list[tuple[str, float]] = []

    def scripted_native(
        fixture: Any,
        *,
        trace_id_prefix: str,
        model: str,
        reasoning_effort: str,
    ) -> Any:
        del trace_id_prefix
        captured_bindings.append((model, reasoning_effort))
        return service_desk_scripted_bindings(fixture)

    def narrated(
        document: object,
        *,
        model: str,
        trace_id_prefix: str,
        max_total_cost: float,
        max_calls: int,
        reasoning_effort: str,
    ) -> dict[str, object]:
        del document, trace_id_prefix
        assert reasoning_effort == "none"
        assert max_calls == 32
        captured_narration.append((model, max_total_cost))
        return {
            "status": "completed",
            "model_calls": 0,
            "cost": 0.0,
            "moments": [],
            "calls": [],
        }

    with (
        patch.dict(
            "os.environ",
            {
                "OPENROUTER_API_KEY": "test-key",
                "CYBERNETIC_INFLUENCE_LIVE": "1",
                "CYBERNETIC_INFLUENCE_CERT_DEEPSEEK_V4_FLASH": "test-canary",
                "LLM_CLIENT_REVISION": "test-client-revision",
            },
        ),
        patch(
            "cybernetic_influence.api.service_desk_native_bindings",
            side_effect=scripted_native,
        ),
        patch(
            "cybernetic_influence.api.narrate_live_moments",
            side_effect=narrated,
        ),
        patch(
            "cybernetic_influence.run_configuration._validated_certification_basis",
            side_effect=lambda _model, configured: configured or None,
        ),
    ):
        response = client(tmp_path).post(
            "/api/runs",
            json={
                "execution": "live",
                "llm_options": {
                    "model": "openrouter/deepseek/deepseek-v4-flash",
                    "agent_reasoning_effort": "none",
                    "max_total_cost": 0.31,
                },
            },
        )
        assert response.status_code == 202, response.text
        run_id = response.json()["run_id"]
        body: dict[str, object] | None = None
        for _ in range(200):
            candidate = client(tmp_path).get(f"/api/runs/{run_id}").json()
            if candidate["status"] in {"completed", "failed"}:
                body = candidate
                break
            time.sleep(0.01)
        assert body is not None
    assert captured_bindings == [
        ("openrouter/deepseek/deepseek-v4-flash", "none")
    ]
    assert captured_narration == [
        ("openrouter/deepseek/deepseek-v4-flash", 0.31)
    ]
    assert body["llm_configuration"] == {
        "model": "openrouter/deepseek/deepseek-v4-flash",
        "agent_reasoning_effort": "none",
        "narrator_reasoning_effort": "none",
        "max_total_cost": 0.31,
        "participant_per_call_ceiling": 0.05,
        "narrator_per_call_ceiling": 0.025,
        "maximum_participant_calls": 48,
        "maximum_narrator_calls": 32,
        "selection_basis": "operator_selected",
        "llm_client_revision": "test-client-revision",
    }


def test_model_specific_reasoning_is_rejected_before_dispatch(
    tmp_path: Path,
) -> None:
    with (
        patch.dict(
            "os.environ",
            {
                "OPENROUTER_API_KEY": "test-key",
                "CYBERNETIC_INFLUENCE_LIVE": "1",
                "CYBERNETIC_INFLUENCE_CERT_DEEPSEEK_V4_FLASH": "test-canary",
            },
        ),
        patch(
            "cybernetic_influence.run_configuration._validated_certification_basis",
            side_effect=lambda _model, configured: configured or None,
        ),
    ):
        api = client(tmp_path)
        response = api.post(
            "/api/runs",
            json={
                "execution": "live",
                "llm_options": {
                    "model": "openrouter/deepseek/deepseek-v4-flash",
                    "agent_reasoning_effort": "medium",
                    "max_total_cost": 0.20,
                },
            },
        )
        history = api.get("/api/runs").json()["runs"]
    assert response.status_code == 422
    assert "does not support agent reasoning effort" in response.json()["detail"]
    assert history == []


def test_unadvertised_live_model_is_rejected_without_retained_run(
    tmp_path: Path,
) -> None:
    with (
        patch.dict(
            "os.environ",
            {
                "OPENROUTER_API_KEY": "test-key",
                "CYBERNETIC_INFLUENCE_LIVE": "1",
                "CYBERNETIC_INFLUENCE_CERT_TERRA": "test-canary",
                "CYBERNETIC_INFLUENCE_CERT_DEEPSEEK_V4_FLASH": "test-canary-deepseek",
            },
        ),
        patch(
            "cybernetic_influence.run_configuration._validated_certification_basis",
            side_effect=lambda _model, configured: configured or None,
        ),
    ):
        api = client(tmp_path)
        response = api.post(
            "/api/runs",
            json={
                "execution": "live",
                "llm_options": {
                    "model": "openrouter/openai/gpt-5.5",
                    "agent_reasoning_effort": "medium",
                    "max_total_cost": 0.20,
                },
            },
        )
        history = api.get("/api/runs").json()["runs"]
    assert response.status_code == 422
    assert history == []


def test_interventions_produce_distinct_grounded_accounts(tmp_path: Path) -> None:
    api = client(tmp_path)
    missing = api.post(
        "/api/runs",
        json={"arm_id": "no_direct_path", "execution": "scripted"},
    ).json()
    speed = api.post(
        "/api/runs",
        json={"arm_id": "speed_priority", "execution": "scripted"},
    ).json()
    assert "direct report path was unavailable" in missing["story"]["summary"]
    assert "denied" in speed["story"]["summary"]
    assert missing["outcome"]["remediation_activation"] > speed["outcome"]["remediation_activation"]


def test_retained_progress_is_ordered_analyst_safe_and_replayable(
    tmp_path: Path,
) -> None:
    api = client(tmp_path)
    run = api.post("/api/runs", json={"execution": "scripted"}).json()
    progress = api.get(f"/api/runs/{run['run_id']}/progress").json()
    assert progress["status"] == "completed"
    assert progress["latest_sequence"] > 0
    records = progress["records"]
    assert records
    assert [record["sequence"] for record in records] == list(
        range(1, len(records) + 1)
    )
    assert records[0]["kind"] == "activation_started"
    committed = next(
        record for record in records if record["kind"] == "causal_moment_committed"
    )
    assert committed["projection"]["nodes"]
    assert committed["projection"]["events"]
    assert all(
        "private_state" not in event
        for event in committed["projection"]["events"]
    )
    after = api.get(
        f"/api/runs/{run['run_id']}/progress",
        params={"after_sequence": progress["latest_sequence"]},
    ).json()
    assert after["records"] == []


def test_physical_access_uses_the_same_retained_progress_schema(
    tmp_path: Path,
) -> None:
    api = client(tmp_path)
    run = api.post(
        "/api/runs",
        json={
            "scenario": "physical_access",
            "arm_id": "authorization_absent",
            "execution": "scripted",
        },
    ).json()
    progress = api.get(f"/api/runs/{run['run_id']}/progress").json()
    records = progress["records"]
    assert progress["status"] == "completed"
    assert records[0]["kind"] == "activation_started"
    assert any(
        item["kind"] == "causal_moment_committed" for item in records
    )
    # The public playback schema does not branch on an arm or scenario name.
    assert all("scenario" not in item for item in records)
    committed = next(
        item for item in records if item["kind"] == "causal_moment_committed"
    )
    assert "private_state" not in str(committed["projection"])


def test_live_worker_retains_pending_activation_before_commit(tmp_path: Path) -> None:
    entered = Event()
    release = Event()

    def blocking_native(
        fixture: Any,
        *,
        trace_id_prefix: str,
        model: str,
        reasoning_effort: str,
    ) -> dict[str, ActiveSystemBinding]:
        del trace_id_prefix, model, reasoning_effort
        bindings = service_desk_scripted_bindings(fixture)
        original = bindings["triager"]

        class BlockingTriager:
            implementation_id = original.implementation_id
            provider_bound = False

            def step(self, active_input: Any) -> Any:
                entered.set()
                assert release.wait(timeout=5)
                return original.implementation.step(active_input)

        bindings["triager"] = ActiveSystemBinding(
            original.implementation_id, BlockingTriager()
        )
        return bindings

    with (
        patch.dict(
            "os.environ",
            {
                "OPENROUTER_API_KEY": "test-key",
                "CYBERNETIC_INFLUENCE_LIVE": "1",
                "CYBERNETIC_INFLUENCE_CERT_DEEPSEEK_V4_FLASH": "test-canary",
            },
        ),
        patch(
            "cybernetic_influence.api.service_desk_native_bindings",
            side_effect=blocking_native,
        ),
        patch(
            "cybernetic_influence.api.narrate_live_moments",
            return_value={
                "status": "completed",
                "model_calls": 0,
                "cost": 0.0,
                "moments": [],
                "calls": [],
            },
        ),
        patch(
            "cybernetic_influence.run_configuration._validated_certification_basis",
            side_effect=lambda _model, configured: configured or None,
        ),
    ):
        api = client(tmp_path)
        started = api.post("/api/runs", json={"execution": "live"})
        assert started.status_code == 202, started.text
        run_id = started.json()["run_id"]
        assert entered.wait(timeout=5)
        progress = api.get(f"/api/runs/{run_id}/progress").json()
        assert progress["status"] == "running"
        assert progress["records"][0]["kind"] == "activation_started"
        assert progress["records"][0]["participant_ids"] == ["triager"]
        assert progress["records"][0]["event_ids"] == []
        release.set()
        for _ in range(200):
            if api.get(f"/api/runs/{run_id}").json()["status"] == "completed":
                break
            time.sleep(0.01)
        assert api.get(f"/api/runs/{run_id}").json()["status"] == "completed"


def test_physical_access_arms_are_distinct_and_cross_scenario_arms_fail(
    tmp_path: Path,
) -> None:
    api = client(tmp_path)
    authorized = api.post(
        "/api/runs",
        json={
            "scenario": "physical_access",
            "arm_id": "authorized_access",
            "execution": "scripted",
        },
    ).json()
    policy_denied = api.post(
        "/api/runs",
        json={
            "scenario": "physical_access",
            "arm_id": "authorization_absent",
            "execution": "scripted",
        },
    ).json()
    jammed = api.post(
        "/api/runs",
        json={
            "scenario": "physical_access",
            "arm_id": "latch_jammed",
            "execution": "scripted",
        },
    ).json()

    assert authorized["outcome"]["entered"] is True
    assert "stored policy did not authorize" in policy_denied["story"]["summary"]
    assert policy_denied["outcome"]["authentication"] == "authenticated"
    assert policy_denied["outcome"]["entered"] is False
    assert "physical latch could not release" in jammed["story"]["summary"]
    assert jammed["outcome"]["authorization"] == "authorized"
    assert jammed["outcome"]["entered"] is False
    assert (
        api.post(
            "/api/runs",
            json={
                "scenario": "physical_access",
                "arm_id": "baseline",
            },
        ).status_code
        == 422
    )


def test_physical_world_topology_is_temporal_and_non_normative(
    tmp_path: Path,
) -> None:
    api = client(tmp_path)
    authorized = api.post(
        "/api/runs",
        json={
            "scenario": "physical_access",
            "arm_id": "authorized_access",
            "execution": "scripted",
        },
    ).json()
    world = authorized["world"]
    assert {place["id"] for place in world["places"]} == {
        "maintenance_facility",
        "hallway",
        "equipment_room",
    }
    assert world["links"] == [
        {
            "id": "equipment_room_threshold",
            "kind": "controlled_doorway",
            "label": "Equipment Room Threshold",
            "description": (
                "Topological adjacency across the controlled equipment-room "
                "threshold; it does not assert permission or operability."
            ),
            "endpoint_a_place_id": "hallway",
            "endpoint_b_place_id": "equipment_room",
            "substrate_entity_ids": ["secure_door"],
            "does_not_imply_traversability": True,
        }
    ]
    initial_placements = {
        item["entity_id"]: item["place_id"]
        for item in world["snapshots"]["0"]["placements"]
    }
    assert initial_placements["technician"] == "hallway"
    final_revision = str(authorized["timeline"][-1]["state_revision"])
    final_placements = {
        item["entity_id"]: item["place_id"]
        for item in world["snapshots"][final_revision]["placements"]
    }
    assert final_placements["technician"] == "equipment_room"
    crossing_commit = next(
        event
        for event in authorized["timeline"]
        if event["kind"] == "state_committed"
        and "equipment_room_threshold" in event["spatial_link_ids"]
    )
    assert {
        "technician",
        "hallway",
        "equipment_room",
    } <= set(crossing_commit["spatial_focus_ids"])

    denied = api.post(
        "/api/runs",
        json={
            "scenario": "physical_access",
            "arm_id": "authorization_absent",
            "execution": "scripted",
        },
    ).json()
    assert {
        item["place_id"]
        for snapshot in denied["world"]["snapshots"].values()
        for item in snapshot["placements"]
        if item["entity_id"] == "technician"
    } == {"hallway"}

    service = api.post(
        "/api/runs",
        json={"scenario": "service_desk", "execution": "scripted"},
    ).json()
    service_world = service["world"]
    assert {place["id"] for place in service_world["places"]} == {
        "service_operations_center",
        "intake_area",
        "resolution_area",
        "supervision_area",
        "customer_site",
    }
    service_placements = {
        item["entity_id"]: item["place_id"]
        for item in service_world["snapshots"]["0"]["placements"]
    }
    assert service_placements == {
        "customer": "customer_site",
        "triager": "intake_area",
        "specialist": "resolution_area",
        "supervisor": "supervision_area",
    }
    assert {link["id"] for link in service_world["links"]} == {
        "intake_resolution_aisle",
        "resolution_supervision_aisle",
    }
    assert all(
        link["does_not_imply_traversability"]
        for link in service_world["links"]
    )
    assert all(not event["spatial_link_ids"] for event in service["timeline"])
    assert any(
        {"triager", "intake_area"} <= set(event["spatial_focus_ids"])
        for event in service["timeline"]
    )


def test_live_run_requires_explicit_authorization(tmp_path: Path) -> None:
    with patch.dict("os.environ", {"CYBERNETIC_INFLUENCE_LIVE": "0"}):
        response = client(tmp_path).post("/api/runs", json={"execution": "live"})
    assert response.status_code == 403
    assert "CYBERNETIC_INFLUENCE_LIVE=1" in response.json()["detail"]


def test_completed_run_survives_app_restart_and_delete_is_recoverable(tmp_path: Path) -> None:
    first = client(tmp_path)
    created = first.post("/api/runs", json={"execution": "scripted"}).json()

    restarted = client(tmp_path)
    history = restarted.get("/api/runs").json()
    assert [run["run_id"] for run in history["runs"]] == [created["run_id"]]
    reopened = restarted.get(f"/api/runs/{created['run_id']}")
    assert reopened.status_code == 200
    assert reopened.json()["events"] == created["events"]

    deleted = restarted.delete(f"/api/runs/{created['run_id']}")
    assert deleted.json()["recoverable"] is True
    assert restarted.get(f"/api/runs/{created['run_id']}").status_code == 404
    assert list((tmp_path / ".trash").glob(f"{created['run_id']}.*.json"))


def test_interrupted_corrupt_and_invalid_records_are_explicit(tmp_path: Path) -> None:
    store = RunStore(tmp_path)
    store.save(
        {
            "run_id": "run_deadbeefcafe",
            "created_at": "2026-07-23T00:00:00+00:00",
            "status": "running",
        }
    )
    (tmp_path / "run_deadbeefdead.json").write_text("{broken", encoding="utf-8")

    api = client(tmp_path)
    interrupted = api.get("/api/runs/run_deadbeefcafe")
    assert interrupted.json()["status"] == "interrupted"
    history = api.get("/api/runs").json()
    assert history["corrupt_files"] == ["run_deadbeefdead.json"]
    assert api.get("/api/runs/not-a-run").status_code == 422


def test_failed_run_is_retained_for_inspection(tmp_path: Path) -> None:
    with patch(
        "cybernetic_influence.api.run_event_driven_service_desk",
        side_effect=RuntimeError("test failure"),
    ):
        api = client(tmp_path)
        response = api.post("/api/runs", json={"execution": "scripted"})
    assert response.status_code == 500
    history = api.get("/api/runs").json()["runs"]
    assert len(history) == 1
    retained = api.get(f"/api/runs/{history[0]['run_id']}").json()
    assert retained["status"] == "failed"
    assert "RuntimeError" in retained["error"]


def test_failed_run_retains_its_full_validated_continuation(tmp_path: Path) -> None:
    def checkpoint_then_fail(*args: Any, **kwargs: Any) -> Any:
        observer = kwargs["checkpoint_observer"]

        def fail_after_checkpoint(checkpoint: Any) -> None:
            observer(checkpoint)
            raise RuntimeError("after checkpoint")

        kwargs["checkpoint_observer"] = fail_after_checkpoint
        return original_run_service_desk(*args, **kwargs)

    with patch(
        "cybernetic_influence.api.run_event_driven_service_desk",
        side_effect=checkpoint_then_fail,
    ):
        api = client(tmp_path)
        response = api.post("/api/runs", json={"execution": "scripted"})

    assert response.status_code == 500
    retained = api.get(f"/api/runs/{api.get('/api/runs').json()['runs'][0]['run_id']}").json()
    continuation = retained["continuation"]
    assert continuation["lifecycle"] == "interrupted"
    assert continuation["checkpoint_digest"] == continuation["checkpoint"]["record_digest"]
    assert continuation["checkpoint"]["attempts"]


def test_scripted_service_desk_pauses_at_a_boundary_and_resumes(
    tmp_path: Path,
) -> None:
    entered = Event()
    release = Event()

    def pauseable_run(*args: Any, **kwargs: Any) -> Any:
        observer = kwargs["checkpoint_observer"]
        blocked = False

        def block_after_first_checkpoint(checkpoint: Any) -> None:
            nonlocal blocked
            observer(checkpoint)
            if not blocked:
                blocked = True
                entered.set()
                assert release.wait(timeout=5)

        kwargs["checkpoint_observer"] = block_after_first_checkpoint
        return original_run_service_desk(*args, **kwargs)

    with patch(
        "cybernetic_influence.api.run_event_driven_service_desk",
        side_effect=pauseable_run,
    ):
        api = client(tmp_path)
        responses: list[Any] = []
        run_id = "run_fade00000000"
        thread = Thread(
            target=lambda: responses.append(
                api.post(
                    "/api/runs",
                    json={"execution": "scripted", "run_id": run_id},
                )
            )
        )
        thread.start()
        assert entered.wait(timeout=5)
        requested = api.post(f"/api/runs/{run_id}/pause")
        assert requested.status_code == 200
        release.set()
        thread.join(timeout=5)

    assert len(responses) == 1
    assert responses[0].status_code == 200
    assert responses[0].json()["status"] == "paused"
    paused = api.get(f"/api/runs/{run_id}").json()
    assert paused["continuation"]["lifecycle"] == "paused"
    assert len(paused["continuation"]["checkpoint"]["attempts"]) == 1
    resumed = api.post(f"/api/runs/{run_id}/resume")
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["status"] == "completed"
    assert resumed.json()["outcome"]["final_status"] == "closed_confirmed"


def test_failed_resumed_run_retains_latest_checkpoint_evidence(tmp_path: Path) -> None:
    api = client(tmp_path)
    run_id = "run_feed00000000"

    def pause_after_first_checkpoint(*args: Any, **kwargs: Any) -> Any:
        observer = kwargs["checkpoint_observer"]

        def stop_at_checkpoint(checkpoint: Any) -> None:
            observer(checkpoint)
            raise RuntimePaused(checkpoint)

        kwargs["checkpoint_observer"] = stop_at_checkpoint
        return original_run_service_desk(*args, **kwargs)

    with patch(
        "cybernetic_influence.api.run_event_driven_service_desk",
        side_effect=pause_after_first_checkpoint,
    ):
        paused_response = api.post(
            "/api/runs", json={"execution": "scripted", "run_id": run_id}
        )
    assert paused_response.status_code == 200, paused_response.text
    paused = api.get(f"/api/runs/{run_id}").json()
    assert paused["status"] == "paused"
    paused_attempt_count = len(paused["continuation"]["checkpoint"]["attempts"])

    def retain_then_fail(*args: Any, **kwargs: Any) -> Any:
        observer = kwargs["checkpoint_observer"]

        def fail_after_new_checkpoint(checkpoint: Any) -> None:
            observer(checkpoint)
            if len(checkpoint.attempts) > paused_attempt_count:
                raise RuntimeError("resume failed after checkpoint retention")

        kwargs["checkpoint_observer"] = fail_after_new_checkpoint
        return original_run_service_desk(*args, **kwargs)

    with patch(
        "cybernetic_influence.api.run_event_driven_service_desk",
        side_effect=retain_then_fail,
    ):
        with pytest.raises(RuntimeError, match="resume failed after checkpoint retention"):
            api.post(f"/api/runs/{run_id}/resume")

    retained = api.get(f"/api/runs/{run_id}").json()
    assert retained["status"] == "failed"
    assert len(retained["continuation"]["checkpoint"]["attempts"]) > paused_attempt_count


def test_live_service_desk_resume_reuses_retained_llm_configuration(
    tmp_path: Path,
) -> None:
    resumed_worker_entered = Event()
    release_resumed_worker = Event()
    fixture = service_desk_fixture(
        service_desk_arm_configurations()[0],
        cognition_profile="position_context",
        model="openrouter/deepseek/deepseek-v4-flash",
        reasoning_effort="none",
    )
    def native_identity_scripted_bindings(item: Any, **kwargs: Any) -> Any:
        native = service_desk_native_bindings(item, **kwargs)
        scripted = service_desk_scripted_bindings(item)
        adapted: dict[str, ActiveSystemBinding] = {}
        for active_system_id, native_binding in native.items():
            scripted_binding = scripted[active_system_id]

            def controller(
                active_input: Any,
                *,
                source: Any = scripted_binding,
                implementation_id: str = native_binding.implementation_id,
            ) -> ActiveStepResult:
                result = ActiveStepResult.model_validate(source.implementation.step(active_input))
                return result.model_copy(update={"proposal": result.proposal.model_copy(update={"implementation_id": implementation_id})})

            adapted[active_system_id] = ActiveSystemBinding(
                native_binding.implementation_id,
                ScriptedActiveSystem(native_binding.implementation_id, controller),
            )
        return adapted

    bindings = native_identity_scripted_bindings(
        fixture,
        trace_id_prefix="run_feed00000000",
        model="openrouter/deepseek/deepseek-v4-flash",
        reasoning_effort="none",
    )
    with pytest.raises(RuntimePaused) as paused:
        original_run_service_desk(
            fixture,
            bindings,
            run_id="run_feed00000000",
            checkpoint_observer=lambda _checkpoint: None,
            pause_requested=lambda: True,
        )
    retained_checkpoint = paused.value.checkpoint
    RunStore(tmp_path).save({
        "run_id": "run_feed00000000", "created_at": "2026-07-24T00:00:00+00:00",
        "status": "paused", "scenario": "service_desk", "arm": "baseline",
        "profile": "position_context", "execution": "live",
        "llm_configuration": {"model": "openrouter/deepseek/deepseek-v4-flash", "agent_reasoning_effort": "none", "narrator_reasoning_effort": "none", "max_total_cost": 0.20, "participant_per_call_ceiling": 0.05, "narrator_per_call_ceiling": 0.02, "maximum_participant_calls": 48, "maximum_narrator_calls": 12, "selection_basis": "operator_selected", "llm_client_revision": "test-client"},
        "continuation": {"checkpoint": retained_checkpoint.model_dump(mode="json")},
    })
    captured: list[tuple[str, str]] = []
    api = client(tmp_path)
    with patch.dict("os.environ", {"CYBERNETIC_INFLUENCE_LIVE": ""}):
        unauthorized = api.post("/api/runs/run_feed00000000/resume")
    assert unauthorized.status_code == 403
    assert captured == []

    effective = EffectiveRunLlmConfiguration(
        model="openrouter/deepseek/deepseek-v4-flash",
        agent_reasoning_effort="none",
        narrator_reasoning_effort="none",
        max_total_cost=0.20,
        maximum_narrator_calls=12,
        selection_basis="operator_selected",
        llm_client_revision="test-client",
    )
    with (
        patch.dict(
            "os.environ",
            {
                "CYBERNETIC_INFLUENCE_LIVE": "1",
                "LLM_CLIENT_REVISION": "test-client",
            },
        ),
        patch(
            "cybernetic_influence.api.resolve_live_configuration",
            side_effect=ValueError("route unavailable"),
        ),
    ):
        uncertified = api.post("/api/runs/run_feed00000000/resume")
    assert uncertified.status_code == 409
    assert uncertified.json()["detail"] == (
        "paused live run route is not currently certified"
    )
    assert captured == []

    lock_checked = False

    def capture_native(item: Any, **kwargs: Any) -> Any:
        captured.append((kwargs["model"], kwargs["reasoning_effort"]))
        return native_identity_scripted_bindings(item, **kwargs)

    def narrate_while_locked(*_args: Any, **_kwargs: Any) -> dict[str, object]:
        nonlocal lock_checked
        concurrent = api.post(
            "/api/runs",
            json={
                "execution": "live",
                "llm_options": {
                    "model": effective.model,
                    "agent_reasoning_effort": "none",
                    "max_total_cost": 0.20,
                },
            },
        )
        assert concurrent.status_code == 409
        assert concurrent.json()["detail"] == "another live run is already active"
        lock_checked = True
        return {
            "status": "completed",
            "model_calls": 0,
            "cost": 0.0,
            "moments": [],
            "calls": [],
        }

    def hold_resumed_runtime(*args: Any, **kwargs: Any) -> Any:
        resumed_worker_entered.set()
        assert release_resumed_worker.wait(timeout=5)
        return original_run_service_desk(*args, **kwargs)

    with (
        patch.dict(
            "os.environ",
            {
                "CYBERNETIC_INFLUENCE_LIVE": "1",
                "LLM_CLIENT_REVISION": "test-client",
            },
        ),
        patch(
            "cybernetic_influence.api.resolve_live_configuration",
            return_value=effective,
        ),
        patch(
            "cybernetic_influence.api.service_desk_native_bindings",
            side_effect=capture_native,
        ),
        patch(
            "cybernetic_influence.api.run_event_driven_service_desk",
            side_effect=hold_resumed_runtime,
        ),
        patch(
            "cybernetic_influence.api.narrate_live_moments",
            side_effect=narrate_while_locked,
        ),
    ):
        response = api.post("/api/runs/run_feed00000000/resume")
        assert response.status_code == 202, response.text
        assert resumed_worker_entered.wait(timeout=5)
        assert api.get("/api/runs/run_feed00000000").json()["status"] == "running"
        release_resumed_worker.set()
        for _ in range(200):
            retained = api.get("/api/runs/run_feed00000000").json()
            if retained["status"] == "completed":
                break
            time.sleep(0.01)
        else:
            pytest.fail("resumed live run did not complete")
    assert captured == [("openrouter/deepseek/deepseek-v4-flash", "none")]
    assert lock_checked is True
    assert retained["status"] == "completed"


def test_optional_tailscale_identity_allowlist_guards_run_evidence(
    tmp_path: Path,
) -> None:
    with patch.dict(
        "os.environ",
        {"CYBERNETIC_INFLUENCE_ALLOWED_TAILSCALE_USERS": "brian@example.com"},
    ):
        api = client(tmp_path)
        assert api.get("/api/config").json()["access_restricted"] is True
        assert api.get("/api/runs").status_code == 403
        assert (
            api.get(
                "/api/runs",
                headers={"Tailscale-User-Login": "other@example.com"},
            ).status_code
            == 403
        )
        allowed = api.get(
            "/api/runs",
            headers={"Tailscale-User-Login": "Brian@Example.com"},
        )
        assert allowed.status_code == 200


def test_only_one_live_run_can_execute_per_process(tmp_path: Path) -> None:
    entered = Event()
    release = Event()

    def slow_run(*args: Any, **kwargs: Any) -> Any:
        entered.set()
        assert release.wait(timeout=30)
        return original_run_service_desk(*args, **kwargs)

    def scripted_native(
        fixture: Any,
        *,
        trace_id_prefix: str,
        model: str,
        reasoning_effort: str,
    ) -> Any:
        del trace_id_prefix, model, reasoning_effort
        return service_desk_scripted_bindings(fixture)

    with (
        patch.dict(
            "os.environ",
            {
                "OPENROUTER_API_KEY": "test-key",
                "CYBERNETIC_INFLUENCE_LIVE": "1",
                "CYBERNETIC_INFLUENCE_CERT_TERRA": "test-canary",
                "CYBERNETIC_INFLUENCE_CERT_DEEPSEEK_V4_FLASH": "test-canary-deepseek",
            },
        ),
        patch(
            "cybernetic_influence.api.service_desk_native_bindings",
            side_effect=scripted_native,
        ),
        patch(
            "cybernetic_influence.api.run_event_driven_service_desk",
            side_effect=slow_run,
        ),
        patch(
            "cybernetic_influence.api.narrate_live_moments",
            return_value={
                "status": "completed",
                "model_calls": 0,
                "cost": 0.0,
                "moments": [],
                "calls": [],
            },
        ),
        patch(
            "cybernetic_influence.run_configuration._validated_certification_basis",
            side_effect=lambda _model, configured: configured or None,
        ),
    ):
        api = client(tmp_path)

        first = api.post("/api/runs", json={"execution": "live"})
        assert first.status_code == 202, first.text
        assert entered.wait(timeout=5)
        second = api.post("/api/runs", json={"execution": "live"})
        assert second.status_code == 409
        assert "already active" in second.json()["detail"]
        release.set()
        run_id = first.json()["run_id"]
        for _ in range(200):
            if api.get(f"/api/runs/{run_id}").json()["status"] == "completed":
                break
            time.sleep(0.01)
        assert api.get(f"/api/runs/{run_id}").json()["status"] == "completed"


def test_invalid_live_run_id_does_not_leave_the_live_lock_held(tmp_path: Path) -> None:
    """Reject IDs before acquiring the single-live-run lock."""

    def scripted_native(
        fixture: Any,
        *,
        trace_id_prefix: str,
        model: str,
        reasoning_effort: str,
    ) -> Any:
        del trace_id_prefix, model, reasoning_effort
        return service_desk_scripted_bindings(fixture)

    with (
        patch.dict(
            "os.environ",
            {
                "OPENROUTER_API_KEY": "test-key",
                "CYBERNETIC_INFLUENCE_LIVE": "1",
                "CYBERNETIC_INFLUENCE_CERT_DEEPSEEK_V4_FLASH": "test-canary",
            },
        ),
        patch(
            "cybernetic_influence.api.service_desk_native_bindings",
            side_effect=scripted_native,
        ),
        patch(
            "cybernetic_influence.api.narrate_live_moments",
            return_value={
                "status": "completed",
                "model_calls": 0,
                "cost": 0.0,
                "moments": [],
                "calls": [],
            },
        ),
        patch(
            "cybernetic_influence.run_configuration._validated_certification_basis",
            side_effect=lambda _model, configured: configured or None,
        ),
    ):
        api = client(tmp_path)
        rejected = api.post(
            "/api/runs",
            json={"execution": "live", "run_id": "invalid"},
        )
        assert rejected.status_code == 422
        assert rejected.json()["detail"] == "invalid run ID"

        started = api.post("/api/runs", json={"execution": "live"})
        assert started.status_code == 202, started.text
        run_id = started.json()["run_id"]
        for _ in range(200):
            if api.get(f"/api/runs/{run_id}").json()["status"] == "completed":
                break
            time.sleep(0.01)
        assert api.get(f"/api/runs/{run_id}").json()["status"] == "completed"


def test_coordination_scenario_runs_reopens_and_clips_boundary_activity(
    tmp_path: Path,
) -> None:
    api = client(tmp_path)
    preview = api.get(
        "/api/scenarios/coordination_decision/preview",
        params={"arm_id": "stabilization"},
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["nodes"]
    assert preview.json()["edges"]
    assert preview.json()["world"]["places"]
    assert len(preview.json()["boundaries"]) == 2

    response = api.post(
        "/api/runs",
        json={
            "scenario": "coordination_decision",
            "arm_id": "stabilization",
            "execution": "scripted",
        },
    )
    assert response.status_code == 200, response.text
    document = response.json()
    assert document["status"] == "completed"
    assert document["cost"] == 0.0
    assert document["model_calls"] == 0
    assert document["completion"]
    assert document["outcome"]["final_status"]
    assert document["live_progress"] == []
    assert 12 <= len(document["narration"]["moments"]) <= 28
    assert all(
        item["concise_narrative"] and item["detailed_paragraphs"]
        for item in document["narration"]["moments"]
    )
    detailed_text = " ".join(
        paragraph["text"]
        for item in document["narration"]["moments"]
        for paragraph in item["detailed_paragraphs"]
    )
    assert "through connection" not in detailed_text
    assert "Committed mechanism" not in detailed_text
    assert "state revision" not in detailed_text
    assert '{"' not in detailed_text
    assert "The coordinator's request for explicit review reached 4 team members." in detailed_text
    assert all(
        not item["concise_narrative"].startswith(("On day", "At day"))
        for item in document["narration"]["moments"]
    )
    assert [item["moment"] for item in document["narration"]["moments"]] == list(
        range(1, len(document["narration"]["moments"]) + 1)
    )
    partnership = next(
        item for item in document["boundaries"] if item["id"] == "deployment_partnership"
    )
    activity = partnership["activity"]
    assert any(item["direction"] == "incoming" for item in activity["crossings"])
    output = next(
        item for item in activity["crossings"] if item["direction"] == "outgoing"
    )
    completed = next(
        item for item in activity["episodes"] if item["status"] == "completed"
    )
    assert len(completed["contributing_member_ids"]) >= 4
    assert completed["external_result_event_ids"]

    run_id = document["run_id"]
    reopened = api.get(f"/api/runs/{run_id}")
    assert reopened.status_code == 200
    assert next(
        item
        for item in reopened.json()["boundaries"]
        if item["id"] == "deployment_partnership"
    )["activity"] == activity

    legacy_document = cast(dict[str, Any], RunStore(tmp_path).get(run_id))
    legacy_narration = deepcopy(legacy_document["narration"])
    legacy_narration["moments"][0]["detailed_paragraphs"] = [
        {
            "text": "Routed alignment_message through connection legacy_route. "
            "Committed mechanism legacy_delivery as state revision 4.",
            "source_event_ids": legacy_narration["moments"][0]["source_event_ids"],
        }
    ]
    legacy_document["narration"] = legacy_narration
    RunStore(tmp_path).save(legacy_document)
    refreshed = api.get(f"/api/runs/{run_id}")
    assert refreshed.status_code == 200
    refreshed_text = " ".join(
        paragraph["text"]
        for item in refreshed.json()["narration"]["moments"]
        for paragraph in item["detailed_paragraphs"]
    )
    assert "through connection" not in refreshed_text
    assert "state revision" not in refreshed_text
    retained_legacy_document = cast(
        dict[str, Any], RunStore(tmp_path).get(run_id)
    )
    retained_legacy_text = retained_legacy_document["narration"]["moments"][0][
        "detailed_paragraphs"
    ][0]["text"]
    assert "through connection" in retained_legacy_text

    event_before_output = next(
        item for item in document["events"] if item["sequence"] == output["sequence"] - 1
    )
    clipped_before = api.get(
        f"/api/runs/{run_id}",
        params={"through_event_id": event_before_output["event_id"]},
    )
    assert clipped_before.status_code == 200, clipped_before.text
    before_activity = next(
        item
        for item in clipped_before.json()["boundaries"]
        if item["id"] == "deployment_partnership"
    )["activity"]
    assert not any(
        item["direction"] == "outgoing" for item in before_activity["crossings"]
    )
    assert all(item["status"] == "in_progress" for item in before_activity["episodes"])
    before_boundary = next(
        item
        for item in clipped_before.json()["boundaries"]
        if item["id"] == "deployment_partnership"
    )
    assert max(
        item["sequence"] for item in before_boundary["activity_event_index"]
    ) <= event_before_output["sequence"]

    at_output = api.get(
        f"/api/runs/{run_id}",
        params={"through_event_id": output["event_id"]},
    )
    assert at_output.status_code == 200, at_output.text
    at_output_activity = next(
        item
        for item in at_output.json()["boundaries"]
        if item["id"] == "deployment_partnership"
    )["activity"]
    output_episode = next(
        item for item in at_output_activity["episodes"] if item["status"] == "completed"
    )
    assert output_episode["external_result_event_ids"] == []

    progress = api.get(f"/api/runs/{run_id}/progress", params={"after_sequence": 0})
    assert progress.status_code == 200
    latest_sequence = progress.json()["latest_sequence"]
    assert latest_sequence == 0
    assert progress.json()["records"] == []
    assert progress.json()["projection"] is None
    unchanged = api.get(
        f"/api/runs/{run_id}/progress",
        params={"after_sequence": latest_sequence},
    )
    assert unchanged.status_code == 200
    assert unchanged.json()["records"] == []
    assert unchanged.json()["projection"] == progress.json()["projection"]

    corrupted = deepcopy(document)
    corrupted_partnership = next(
        item
        for item in corrupted["boundaries"]
        if item["id"] == "deployment_partnership"
    )
    corrupted_partnership["activity"]["crossings"][0]["event_id"] = "event_999999"
    RunStore(tmp_path).save(corrupted)
    rejected = api.get(f"/api/runs/{run_id}")
    assert rejected.status_code == 409


def test_coordination_live_execution_requires_explicit_spend_authorization(
    tmp_path: Path,
) -> None:
    with patch.dict("os.environ", {"CYBERNETIC_INFLUENCE_LIVE": ""}):
        response = client(tmp_path).post(
            "/api/runs",
            json={
                "scenario": "coordination_decision",
                "arm_id": "baseline",
                "execution": "live",
            },
        )
    assert response.status_code == 403
    assert "CYBERNETIC_INFLUENCE_LIVE=1" in response.json()["detail"]


def test_coordination_live_execution_requires_scenario_schema_certification(
    tmp_path: Path,
) -> None:
    with (
        patch.dict(
            "os.environ",
            {
                "OPENROUTER_API_KEY": "test-key",
                "CYBERNETIC_INFLUENCE_LIVE": "1",
                "CYBERNETIC_INFLUENCE_CERT_DEEPSEEK_V4_FLASH": "test-canary",
            },
        ),
        patch(
            "cybernetic_influence.run_configuration._validated_certification_basis",
            side_effect=lambda _model, configured: configured or None,
        ),
    ):
        response = client(tmp_path).post(
            "/api/runs",
            json={
                "scenario": "coordination_decision",
                "arm_id": "baseline",
                "execution": "live",
                "llm_options": {
                    "model": "openrouter/deepseek/deepseek-v4-flash",
                    "agent_reasoning_effort": "none",
                    "max_total_cost": 0.20,
                },
            },
        )

    assert response.status_code == 422
    assert "coordination participant schemas" in response.json()["detail"]


def test_coordination_live_api_selects_provider_people_and_live_narration(
    tmp_path: Path,
) -> None:
    captured: list[dict[str, object]] = []

    def capture_run(fixture: Any, bindings: Any, **kwargs: Any) -> Any:
        captured.append(
            {
                "provider_people": {
                    person_id
                    for person_id in PERSON_IDS
                    if bindings[person_id].implementation.provider_bound
                },
                "per_call_budget": kwargs["runtime_config"].per_call_budget,
                "per_run_budget": kwargs["runtime_config"].per_run_budget,
            }
        )
        return run_scripted_coordination(
            coordination_runtime_fixture(baseline_coordination_fixture()),
            run_id=kwargs["run_id"],
        )

    def narrate(*_args: Any, **_kwargs: Any) -> dict[str, object]:
        return {
            "status": "completed",
            "model_calls": 0,
            "cost": 0.0,
            "moments": [],
            "calls": [],
        }

    with (
        patch.dict(
            "os.environ",
            {
                "OPENROUTER_API_KEY": "test-key",
                "CYBERNETIC_INFLUENCE_LIVE": "1",
                "CYBERNETIC_INFLUENCE_CERT_DEEPSEEK_V4_FLASH": "test-canary",
                "CYBERNETIC_INFLUENCE_CERT_COORDINATION_DEEPSEEK_V4_FLASH": "test-coordination-canary",
                "LLM_CLIENT_REVISION": "test-client-revision",
            },
        ),
        patch(
            "cybernetic_influence.run_configuration._validated_certification_basis",
            side_effect=lambda _model, configured: configured or None,
        ),
        patch(
            "cybernetic_influence.run_configuration._validated_coordination_certification_basis",
            side_effect=lambda _model, configured: configured or None,
        ),
        patch("cybernetic_influence.api.run_coordination", side_effect=capture_run),
        patch("cybernetic_influence.api.narrate_live_moments", side_effect=narrate),
    ):
        api = client(tmp_path)
        response = api.post(
            "/api/runs",
            json={
                "scenario": "coordination_decision",
                "arm_id": "baseline",
                "execution": "live",
                "llm_options": {
                    "model": "openrouter/deepseek/deepseek-v4-flash",
                    "agent_reasoning_effort": "none",
                    "max_total_cost": 0.20,
                },
            },
        )
        assert response.status_code == 202, response.text
        run_id = response.json()["run_id"]
        retained: dict[str, object] | None = None
        for _ in range(200):
            candidate = api.get(f"/api/runs/{run_id}").json()
            if candidate["status"] in {"completed", "failed"}:
                retained = candidate
                break
            time.sleep(0.01)

    assert retained is not None
    assert retained["status"] == "completed"
    assert retained["execution"] == "live"
    assert captured == [
        {
            "provider_people": set(PERSON_IDS),
            "per_call_budget": 0.05,
            "per_run_budget": 0.20,
        }
    ]
