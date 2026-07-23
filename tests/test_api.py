"""End-to-end gates for the clean walking simulator."""

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from cybernetic_influence.api import create_app


ROOT = Path(__file__).resolve().parents[1]


def client() -> TestClient:
    return TestClient(create_app(ROOT / "web"))


def test_config_and_static_ui_are_operator_first() -> None:
    api = client()
    config = api.get("/api/config")
    assert config.status_code == 200
    assert config.json()["profiles"] == ["position_context", "procedural_control"]
    page = api.get("/")
    assert page.status_code == 200
    assert "What happened" in page.text
    assert "V2 Inspect" not in page.text


def test_scripted_position_context_run_is_zero_cost_and_inspectable() -> None:
    response = client().post(
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


def test_interventions_produce_distinct_grounded_accounts() -> None:
    api = client()
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


def test_live_run_requires_explicit_authorization() -> None:
    with patch.dict("os.environ", {"CYBERNETIC_INFLUENCE_LIVE": "0"}):
        response = client().post("/api/runs", json={"execution": "live"})
    assert response.status_code == 403
    assert "CYBERNETIC_INFLUENCE_LIVE=1" in response.json()["detail"]
