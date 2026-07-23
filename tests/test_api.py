"""End-to-end gates for the clean walking simulator."""

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from cybernetic_influence.api import create_app
from cybernetic_influence.run_store import RunStore


ROOT = Path(__file__).resolve().parents[1]


def client(run_root: Path) -> TestClient:
    return TestClient(create_app(ROOT / "web", run_root))


def test_config_and_static_ui_are_operator_first(tmp_path: Path) -> None:
    api = client(tmp_path)
    config = api.get("/api/config")
    assert config.status_code == 200
    assert config.json()["version"] == "0.3.0"
    assert config.json()["build_commit"] == "development"
    assert config.json()["profiles"] == ["position_context", "procedural_control"]
    page = api.get("/")
    assert page.status_code == 200
    assert "What happened" in page.text
    assert "V2 Inspect" not in page.text
    assert "Step through what changed" in page.text


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
    assert body["story"]["summary"]
    assert {entry["person"] for entry in body["traces"]} == {
        "triager",
        "specialist",
        "supervisor",
    }
    assert any(node["id"] == "incident_17" for node in body["nodes"])
    assert body["events"]
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
    assert "alternate route" in missing["story"]["summary"]
    assert "denied" in speed["story"]["summary"]
    assert missing["outcome"]["remediation_activation"] > speed["outcome"]["remediation_activation"]


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
