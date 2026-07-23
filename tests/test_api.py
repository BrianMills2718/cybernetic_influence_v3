"""End-to-end gates for the clean walking simulator."""

from pathlib import Path
from threading import Event, Thread
from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient

from cybernetic_influence.api import create_app
from cybernetic_influence.run_store import RunStore
from cybernetic_influence.scenarios.service_desk import (
    run_service_desk as original_run_service_desk,
    service_desk_scripted_bindings,
)


ROOT = Path(__file__).resolve().parents[1]


def client(run_root: Path) -> TestClient:
    return TestClient(create_app(ROOT / "web", run_root))


def test_config_and_static_ui_are_operator_first(tmp_path: Path) -> None:
    api = client(tmp_path)
    config = api.get("/api/config")
    assert config.status_code == 200
    assert config.json()["version"] == "0.8.0"
    assert config.json()["build_commit"] == "development"
    assert config.json()["model"] == "openrouter/openai/gpt-5.6-terra"
    assert config.json()["reasoning_effort"] == "medium"
    assert config.json()["profiles"] == ["position_context", "procedural_control"]
    assert set(config.json()["scenarios"]) == {
        "service_desk",
        "physical_access",
    }
    assert config.json()["scenarios"]["physical_access"]["arms"][0]["description"]
    page = api.get("/")
    assert page.status_code == 200
    assert page.headers["content-security-policy"].startswith("default-src 'self'")
    assert page.headers["x-content-type-options"] == "nosniff"
    assert "Scenario condition" in page.text
    assert "Simulation map" in page.text
    assert "Spatial layout" in page.text
    assert "Causal flow" in page.text
    assert "Narrative for the selected turn" in page.text
    assert "Turn-by-turn narrative" in page.text
    assert "Play simulation" in page.text
    assert "/assets/graph-canvas.js" in page.text
    assert "/assets/graph-canvas.css" in page.text
    assert "V2 Inspect" not in page.text
    assert "Choose a moment" in page.text
    graph_script = api.get("/assets/graph-canvas.js")
    graph_styles = api.get("/assets/graph-canvas.css")
    assert graph_script.status_code == 200
    assert graph_styles.status_code == 200
    assert len(graph_script.content) > 250_000
    assert b".react-flow" in graph_styles.content


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
    assert body["story"]["summary"]
    assert {entry["person"] for entry in body["traces"]} == {
        "triager",
        "specialist",
        "supervisor",
    }
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
    with patch("cybernetic_influence.api.run_service_desk", side_effect=RuntimeError("test failure")):
        api = client(tmp_path)
        response = api.post("/api/runs", json={"execution": "scripted"})
    assert response.status_code == 500
    history = api.get("/api/runs").json()["runs"]
    assert len(history) == 1
    retained = api.get(f"/api/runs/{history[0]['run_id']}").json()
    assert retained["status"] == "failed"
    assert "RuntimeError" in retained["error"]


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
        assert release.wait(timeout=5)
        return original_run_service_desk(*args, **kwargs)

    def scripted_native(fixture: Any, *, trace_id_prefix: str) -> Any:
        del trace_id_prefix
        return service_desk_scripted_bindings(fixture)

    first_response: list[object] = []
    with (
        patch.dict("os.environ", {"CYBERNETIC_INFLUENCE_LIVE": "1"}),
        patch(
            "cybernetic_influence.api.service_desk_native_bindings",
            side_effect=scripted_native,
        ),
        patch("cybernetic_influence.api.run_service_desk", side_effect=slow_run),
        patch(
            "cybernetic_influence.api.narrate_live_turns",
            return_value={
                "status": "completed",
                "model_calls": 0,
                "cost": 0.0,
                "turns": [],
                "calls": [],
            },
        ),
    ):
        api = client(tmp_path)

        def first_request() -> None:
            first_response.append(
                api.post("/api/runs", json={"execution": "live"})
            )

        thread = Thread(target=first_request)
        thread.start()
        assert entered.wait(timeout=5)
        second = api.post("/api/runs", json={"execution": "live"})
        assert second.status_code == 409
        assert "already active" in second.json()["detail"]
        release.set()
        thread.join(timeout=10)

    assert len(first_response) == 1
    assert getattr(first_response[0], "status_code") == 200
