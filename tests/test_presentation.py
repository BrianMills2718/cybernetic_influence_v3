"""Adversarial gates for analyst visibility and temporal truth."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from cybernetic_influence.api import create_app
from cybernetic_influence.causal_core.models import CausalEvent, FactChange, StatePatch
from cybernetic_influence.presentation import analyst_event, service_desk_summary


ROOT = Path(__file__).resolve().parents[1]
TRIAGER_CANARY = "triager_route_key_17"
SUPERVISOR_CANARY = "supervisor_close_key_17"


def test_mechanism_credentials_never_cross_analyst_boundary(tmp_path: Path) -> None:
    body = TestClient(create_app(ROOT / "web", tmp_path)).post(
        "/api/runs",
        json={"arm_id": "baseline", "execution": "scripted"},
    ).json()
    encoded = json.dumps(body)
    assert TRIAGER_CANARY not in encoded
    assert SUPERVISOR_CANARY not in encoded

    authority = next(node for node in body["nodes"] if node["id"] == "credential_authority")
    assert authority["state"]["triager_verifier"] == {
        "visibility": "mechanism",
        "redacted": True,
    }
    credential = next(
        node for node in body["nodes"] if node["id"] == "triager_routing_credential"
    )
    assert credential["state"]["redacted"] is True
    assert "content" not in credential["state"]
    assert "content_hash" not in credential["state"]
    protected_action = next(
        action
        for trace in body["traces"]
        for action in trace["actions"]
        if action["representation_id"] == "triager_routing_credential"
    )
    assert protected_action["payload"] == "[redacted]"


def test_selected_revision_contains_no_future_world_state(tmp_path: Path) -> None:
    body = TestClient(create_app(ROOT / "web", tmp_path)).post(
        "/api/runs",
        json={"arm_id": "baseline", "execution": "scripted"},
    ).json()

    first_action = next(event for event in body["timeline"] if event["kind"] == "action_attempted")
    initial_nodes = body["snapshots"][str(first_action["state_revision"])]
    initial_incident = next(node for node in initial_nodes if node["id"] == "incident_17")
    assert initial_incident["state"]["status"]["value"] == "new"

    assignment_commit = next(
        event
        for event in body["timeline"]
        if event["kind"] == "state_committed"
        and "ticket_routing" in event["summary"]
    )
    assigned_nodes = body["snapshots"][str(assignment_commit["state_revision"])]
    assigned_incident = next(node for node in assigned_nodes if node["id"] == "incident_17")
    assert assigned_incident["state"]["status"]["value"] == "assigned"

    final_incident = next(node for node in body["nodes"] if node["id"] == "incident_17")
    assert final_incident["state"]["status"]["value"] == "closed_confirmed"


def test_timeline_events_link_to_exact_activation_not_only_time(tmp_path: Path) -> None:
    body = TestClient(create_app(ROOT / "web", tmp_path)).post(
        "/api/runs",
        json={"arm_id": "speed_priority", "execution": "scripted"},
    ).json()
    trace_activations = {trace["activation"] for trace in body["traces"]}
    for event in body["timeline"]:
        if event["activation"] is not None:
            assert event["activation"] in trace_activations
    assert all(
        step["activation"] is not None
        for step in body["story"]["steps"]
    )


def test_narrative_is_derived_from_open_remediated_and_closed_outcomes() -> None:
    open_summary = service_desk_summary(
        "baseline",
        {
            "final_status": "assigned",
            "remediation_activation": None,
            "confirmed_closure_activation": None,
            "denied_closure_attempt_count": 0,
        },
    )
    assert "without remediation or confirmed closure" in open_summary
    assert "safely closed" not in open_summary

    remediated_summary = service_desk_summary(
        "no_direct_path",
        {
            "final_status": "remediated",
            "remediation_activation": 4,
            "confirmed_closure_activation": None,
            "denied_closure_attempt_count": 0,
        },
    )
    assert "without confirmed closure" in remediated_summary

    closed_summary = service_desk_summary(
        "speed_priority",
        {
            "final_status": "closed_confirmed",
            "remediation_activation": 1,
            "confirmed_closure_activation": 5,
            "denied_closure_attempt_count": 1,
        },
    )
    assert "safely closed after confirmation" in closed_summary
    assert "denied 1 premature closure attempt" in closed_summary


def test_mechanism_fact_changes_are_redacted_from_raw_event_projection() -> None:
    event = CausalEvent(
        run_id="protected_patch_gate",
        event_id="event_000001",
        sequence=1,
        event_kind="state_committed",
        logical_time=0,
        state_revision=1,
        causal_parent_event_ids=["event_000000"],
        summary="Committed protected state.",
        variance_source="exact",
        mechanism_id="exact_gate",
        effect_id="effect_000000",
        target_port_id="gate_input",
        patch=StatePatch(
            before_revision=0,
            after_revision=1,
            before_logical_time=0,
            after_logical_time=0,
            before_digest="a" * 64,
            after_digest="b" * 64,
            fact_changes=[
                FactChange(
                    fact_id="gate.verifier",
                    visibility="mechanism",
                    before="old-secret",
                    after="new-secret",
                )
            ],
        ),
    )
    projected = analyst_event(event)
    encoded = json.dumps(projected)
    assert "old-secret" not in encoded
    assert "new-secret" not in encoded
    patch = projected["patch"]
    assert isinstance(patch, dict)
    fact_changes = patch["fact_changes"]
    assert isinstance(fact_changes, list)
    change = fact_changes[0]
    assert isinstance(change, dict)
    assert change["before"] == "[redacted]"
    assert change["after"] == "[redacted]"
