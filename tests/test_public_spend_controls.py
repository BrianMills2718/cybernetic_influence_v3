"""Sign-in-free spend controls on the public Waltzman app (ADR-016)."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from cybernetic_influence.public_spend_controls import (
    SpendControlMiddleware,
    SpendControlSettings,
    SpendLedger,
    classify_request,
)


class _RunBody(BaseModel):
    scenario: str
    execution: str = "scripted"


def _client(
    tmp_path: Path,
    *,
    clock: list[float] | None = None,
    run_cap: int = 2,
    per_ip_runs: int = 100,
) -> tuple[TestClient, SpendLedger]:
    inner = FastAPI()
    started: list[str] = []

    @inner.post("/api/runs")
    def start(body: _RunBody) -> dict[str, object]:
        if body.scenario == "invalid":
            raise HTTPException(status_code=422, detail="unknown scenario")
        started.append(body.scenario)
        return {"run_id": f"run_{len(started)}", "echo": body.model_dump()}

    @inner.get("/api/runs")
    def listing() -> dict[str, object]:
        return {"runs": started}

    @inner.post("/api/authoring/drafts/{draft_id}/experiments")
    def experiment(draft_id: str) -> dict[str, object]:
        return {"draft_id": draft_id}

    times = clock if clock is not None else [1_789_000_000.0]
    ledger = SpendLedger(
        SpendControlSettings(
            state_path=tmp_path / "spend.json",
            daily_run_cap=run_cap,
            daily_authoring_cap=5,
            per_ip_runs_per_hour=per_ip_runs,
            per_ip_authoring_per_hour=100,
        ),
        clock=lambda: times[0],
    )
    return TestClient(SpendControlMiddleware(inner, ledger)), ledger


def test_daily_run_cap_refuses_live_starts_with_plain_message(tmp_path: Path) -> None:
    client, _ = _client(tmp_path, run_cap=2)
    live = {"scenario": "coordination_decision", "execution": "live"}

    first = client.post("/api/runs", json=live)
    assert first.status_code == 200
    # The buffered body reached FastAPI's own parser intact.
    assert first.json()["echo"] == live
    assert client.post("/api/runs", json=live).status_code == 200

    refused = client.post("/api/runs", json=live)
    assert refused.status_code == 429
    payload = refused.json()
    assert payload["error"] == "daily_run_cap_reached"
    assert "Today's public limit of 2 live simulations has been reached" in payload["detail"]
    assert int(refused.headers["retry-after"]) > 0

    # Scripted runs and reads are never capped.
    assert client.post("/api/runs", json={"scenario": "x"}).status_code == 200
    assert client.get("/api/runs").status_code == 200


def test_refusal_message_reads_naturally_at_a_cap_of_one(tmp_path: Path) -> None:
    client, _ = _client(tmp_path, run_cap=1)
    live = {"scenario": "s", "execution": "live"}
    assert client.post("/api/runs", json=live).status_code == 200
    refused = client.post("/api/runs", json=live)
    assert (
        "Today's public limit of 1 live simulation has been reached (1 used)"
        in refused.json()["detail"]
    )


def test_rejected_request_returns_its_slot(tmp_path: Path) -> None:
    client, ledger = _client(tmp_path, run_cap=1)
    rejected = client.post("/api/runs", json={"scenario": "invalid", "execution": "live"})
    assert rejected.status_code == 422
    assert ledger.status()["live_runs"] == {
        "used": 0,
        "daily_cap": 1,
        "per_visitor_per_hour": 100,
    }
    accepted = client.post("/api/runs", json={"scenario": "ok", "execution": "live"})
    assert accepted.status_code == 200


def test_per_visitor_limit_uses_cloudflare_client_address(tmp_path: Path) -> None:
    client, _ = _client(tmp_path, run_cap=50, per_ip_runs=1)
    live = {"scenario": "s", "execution": "live"}
    visitor_a = {"CF-Connecting-IP": "203.0.113.7"}
    visitor_b = {"CF-Connecting-IP": "198.51.100.9"}

    assert client.post("/api/runs", json=live, headers=visitor_a).status_code == 200
    limited = client.post("/api/runs", json=live, headers=visitor_a)
    assert limited.status_code == 429
    assert limited.json()["error"] == "per_visitor_rate_limited"
    assert client.post("/api/runs", json=live, headers=visitor_b).status_code == 200


def test_daily_count_survives_restart_and_resets_next_utc_day(tmp_path: Path) -> None:
    clock = [1_789_000_000.0]
    client, _ = _client(tmp_path, clock=clock, run_cap=1)
    live = {"scenario": "s", "execution": "live"}
    assert client.post("/api/runs", json=live).status_code == 200

    restarted, _ = _client(tmp_path, clock=clock, run_cap=1)
    assert restarted.post("/api/runs", json=live).status_code == 429
    assert json.loads((tmp_path / "spend.json").read_text())["counts"] == {"run": 1}

    clock[0] += 86_400
    assert restarted.post("/api/runs", json=live).status_code == 200


def test_experiment_weight_counts_each_condition(tmp_path: Path) -> None:
    client, _ = _client(tmp_path, run_cap=3)
    four: dict[str, object] = {"conditions": [{}, {}, {}, {}]}
    refused = client.post("/api/authoring/drafts/d1/experiments", json=four)
    assert refused.status_code == 429
    three: dict[str, object] = {"conditions": [{}, {}, {}]}
    assert client.post("/api/authoring/drafts/d1/experiments", json=three).status_code == 200


def test_public_demo_refuses_deleting_retained_runs(tmp_path: Path) -> None:
    inner = FastAPI()
    deleted: list[str] = []

    @inner.delete("/api/runs/{run_id}")
    def delete_run(run_id: str) -> dict[str, object]:
        deleted.append(run_id)
        return {"deleted": run_id}

    @inner.delete("/api/runs/{run_id}/analyses/{analysis_id}")
    def delete_analysis(run_id: str, analysis_id: str) -> dict[str, object]:
        deleted.append(analysis_id)
        return {"deleted": analysis_id}

    ledger = SpendLedger(SpendControlSettings(state_path=tmp_path / "spend.json"))
    client = TestClient(SpendControlMiddleware(inner, ledger))

    refused = client.delete("/api/runs/run_abc")
    assert refused.status_code == 403
    assert refused.json()["error"] == "public_delete_disabled"
    # Detaching an analysis lens (used by the public page) is still allowed.
    assert client.delete("/api/runs/run_abc/analyses/a1").status_code == 200
    assert deleted == ["a1"]


def test_classification_covers_every_provider_backed_start() -> None:
    live = b'{"execution": "live"}'
    scripted = b'{"execution": "scripted"}'
    assert classify_request("POST", "/api/runs", live) == ("run", 1)
    assert classify_request("POST", "/api/runs", scripted) is None
    assert classify_request("POST", "/api/authoring/drafts/d/runs", live) == ("run", 1)
    assert classify_request("POST", "/api/runs/run_1/resume", b"") == ("run", 1)
    assert classify_request("POST", "/api/authoring/drafts/d/messages", b"{}") == (
        "authoring",
        1,
    )
    assert classify_request("GET", "/api/runs", b"") is None
    assert classify_request("POST", "/api/runs/run_1/stop", b"") is None
    assert classify_request("POST", "/api/authoring/drafts", b"") is None
