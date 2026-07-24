"""Gates for the purchase-to-payment representation-depth probe."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient
import pytest

from cybernetic_influence.active_runtime import (
    ActiveRuntimeResult,
    ActiveStepResult,
    ActiveSystemBinding,
    ActiveSystemInput,
    ScriptedActiveSystem,
    UpdateScheduleDirective,
)
from cybernetic_influence.api import create_app
from cybernetic_influence.causal_core.replay import (
    replay_committed_trajectory,
)
from cybernetic_influence.presentation import build_analyst_document
from cybernetic_influence.scenarios.purchase_payment import (
    build_purchase_payment_readout,
    PurchasePaymentArmConfiguration,
    PurchasePaymentFixture,
    PurchasePaymentReadout,
    purchase_payment_arm_configurations,
    purchase_payment_fixture,
    purchase_payment_scripted_bindings,
    purchase_payment_summary,
    run_purchase_payment,
)


def _arms() -> dict[str, PurchasePaymentArmConfiguration]:
    return {
        arm.arm_id: arm for arm in purchase_payment_arm_configurations()
    }


def _run(
    arm_id: str,
    *,
    force_payment_request: bool = False,
) -> tuple[
    PurchasePaymentFixture,
    ActiveRuntimeResult,
    PurchasePaymentReadout,
]:
    arm = _arms()[arm_id]
    fixture = purchase_payment_fixture(arm)
    result = run_purchase_payment(
        fixture,
        purchase_payment_scripted_bindings(
            fixture,
            force_payment_request=force_payment_request,
        ),
        run_id=f"purchase_payment_{arm_id}",
    )
    return fixture, result, build_purchase_payment_readout(result)


def test_purchase_payment_arms_separate_internal_and_external_outcomes() -> None:
    settled_fixture, settled_result, settled = _run("settled")
    _, denied_result, denied = _run("approval_denied")
    _, declined_result, declined = _run("processor_declined")

    assert settled.final_status == "settled"
    assert settled.approval_status == "approved"
    assert settled.gate_status == "authorized"
    assert settled.processor_executed is True

    assert denied.final_status == "approval_denied"
    assert denied.approval_status == "denied"
    assert denied.gate_status == "not_attempted"
    assert denied.processor_executed is False

    assert declined.final_status == "processor_declined"
    assert declined.approval_status == "approved"
    assert declined.gate_status == "authorized"
    assert declined.processor_status == "declined"
    assert declined.processor_executed is True

    assert (
        replay_committed_trajectory(
            settled_fixture.scenario,
            settled_result.core_result,
        )
        == settled_result.core_result.final_state
    )
    assert not any(
        event.mechanism_id == "coarse_payment_processor"
        for event in denied_result.core_result.events
    )
    assert any(
        event.mechanism_id == "coarse_payment_processor"
        for event in declined_result.core_result.events
    )
    assert len(settled_result.attempts) == 4
    assert len(denied_result.attempts) == 3
    assert len(declined_result.attempts) == 4


def test_purchase_payment_activations_follow_delivered_information() -> None:
    _, settled_result, _ = _run("settled")
    assert [
        attempt.declared_active_system_ids
        for attempt in settled_result.attempts
    ] == [["requester"], ["approver"], ["ap_clerk"], ["ap_clerk"]]
    assert [attempt.logical_time for attempt in settled_result.attempts] == [
        0,
        0,
        0,
        0,
    ]

    first, *later = settled_result.attempts
    assert [
        cause.kind
        for cause in first.participants[0].input.activation_causes
    ] == ["scenario_start"]
    assert first.participants[0].input.observations == []

    for attempt in later:
        assert len(attempt.participants) == 1
        participant = attempt.participants[0]
        assert [
            cause.kind for cause in participant.input.activation_causes
        ] == ["observation_delivery"]
        caused_observation_ids = {
            observation_id
            for cause in participant.input.activation_causes
            for observation_id in cause.observation_ids
        }
        assert caused_observation_ids == {
            observation.observation_id
            for observation in participant.input.observations
        }

    assert not any(
        cause.kind == "manual_schedule"
        for attempt in settled_result.attempts
        for participant in attempt.participants
        for cause in participant.input.activation_causes
    )


def test_purchase_payment_stops_a_self_scheduling_binding_at_its_bound() -> None:
    fixture = purchase_payment_fixture(_arms()["settled"])
    bindings = purchase_payment_scripted_bindings(fixture)
    original = bindings["ap_clerk"]

    def self_scheduling(active_input: ActiveSystemInput) -> ActiveStepResult:
        result = ActiveStepResult.model_validate(
            original.implementation.step(active_input)
        )
        return result.model_copy(
            update={
                "proposal": result.proposal.model_copy(
                    update={
                        "update_schedule": UpdateScheduleDirective(
                            mode="schedule",
                            next_update_at=active_input.logical_time + 1,
                        )
                    }
                )
            }
        )

    bindings["ap_clerk"] = ActiveSystemBinding(
        original.implementation_id,
        ScriptedActiveSystem(
            original.implementation_id,
            self_scheduling,
        ),
    )
    with pytest.raises(
        RuntimeError,
        match="purchase-payment event scheduler exceeded its causal-moment bound",
    ):
        run_purchase_payment(
            fixture,
            bindings,
            run_id="purchase_payment_self_scheduling_bound",
        )


def test_exact_gate_denies_forced_payment_after_human_denial() -> None:
    _, result, readout = _run(
        "approval_denied",
        force_payment_request=True,
    )
    assert readout.final_status == "gate_denied"
    assert readout.gate_status == "denied"
    assert readout.processor_executed is False
    denial = next(
        representation
        for representation in result.core_result.final_state.representations.values()
        if representation.encoding.endswith("payment-gate-result+json")
        and representation.carrier_id == "ap_gate_result_buffer"
    )
    assert json.loads(denial.content)["reason_code"] == (
        "recorded_decision_not_approved"
    )
    assert [
        attempt.declared_active_system_ids for attempt in result.attempts
    ] == [["requester"], ["approver"], ["ap_clerk"], ["ap_clerk"]]


def test_mismatched_documents_and_inactive_signer_fail_before_payment() -> None:
    settled = _arms()["settled"]
    mismatch_fixture = purchase_payment_fixture(
        settled,
        invoice_amount_cents=120_001,
    )
    mismatch = run_purchase_payment(
        mismatch_fixture,
        purchase_payment_scripted_bindings(mismatch_fixture),
        run_id="purchase_payment_mismatch",
    )
    mismatch_readout = build_purchase_payment_readout(mismatch)
    assert mismatch_readout.approval_status == "not_recorded"
    assert mismatch_readout.processor_executed is False
    assert mismatch.core_result.final_state.fact("purchase_17.status").value == (
        "submission_rejected"
    )
    assert [
        attempt.declared_active_system_ids for attempt in mismatch.attempts
    ] == [["requester"]]

    signer_fixture = purchase_payment_fixture(
        settled,
        signer_active=False,
    )
    signer = run_purchase_payment(
        signer_fixture,
        purchase_payment_scripted_bindings(signer_fixture),
        run_id="purchase_payment_inactive_signer",
    )
    signer_readout = build_purchase_payment_readout(signer)
    assert signer_readout.approval_status == "signer_rejected"
    assert signer_readout.processor_executed is False
    assert [
        attempt.declared_active_system_ids for attempt in signer.attempts
    ] == [["requester"], ["approver"], ["ap_clerk"]]


def test_processor_fidelity_and_lineage_bound_the_claim() -> None:
    fixture, result, readout = _run("processor_declined")
    headline, summary = purchase_payment_summary(readout)
    assert headline == "External processor declined payment"
    assert "does not contain enough processor internals to explain why" in summary

    processor = fixture.scenario.initial_state.mechanisms[
        "coarse_payment_processor"
    ]
    assert processor.implementation_id == "stipulated_payment_processor_v1"
    assert any(
        "cannot answer why" in omission
        for omission in processor.fidelity.known_omissions
    )
    final = result.core_result.final_state
    result_token = next(
        representation
        for representation in final.representations.values()
        if representation.encoding.endswith("payment-result+json")
        and representation.carrier_id == "payment_result_buffer"
    )
    assert len(result_token.parent_representation_ids) == 1
    parent = final.representations[result_token.parent_representation_ids[0]]
    assert parent.encoding.endswith("payment-instruction+json")
    assert set(json.loads(result_token.content)) == {
        "document_kind",
        "invoice_id",
        "request_id",
        "status",
    }


def test_purchase_boundaries_are_derived_and_temporally_projectable() -> None:
    fixture, result, readout = _run("settled")
    headline, summary = purchase_payment_summary(readout)
    document = cast(
        dict[str, Any],
        build_analyst_document(
            initial_state=fixture.scenario.initial_state,
            analytical_boundaries=fixture.scenario.analytical_boundaries,
            result=result,
            scenario="purchase_payment",
            profile="position_context",
            arm_id="settled",
            execution="scripted",
            created_at="2026-07-23T00:00:00+00:00",
            outcome=readout.model_dump(mode="json"),
            headline=headline,
            summary=summary,
        ),
    )
    assert {boundary["id"] for boundary in document["boundaries"]} == {
        "operating_unit_view",
        "finance_operations_view",
        "purchase_to_payment_view",
    }
    assert all(
        boundary["executor"] is False
        for boundary in document["boundaries"]
    )
    boundary_ids = {
        boundary.boundary_id
        for boundary in fixture.scenario.analytical_boundaries
    }
    assert not boundary_ids & set(fixture.scenario.initial_state.entities)
    assert not boundary_ids & {
        spec.active_system_id for spec in fixture.active_specs
    }
    assert not boundary_ids & {
        event.actor_entity_id
        for event in result.core_result.events
        if event.actor_entity_id is not None
    }
    assert not boundary_ids & {
        event.mechanism_id
        for event in result.core_result.events
        if event.mechanism_id is not None
    }

    exact_node_ids = {node["id"] for node in document["nodes"]}
    for boundary in document["boundaries"]:
        for snapshot in boundary["snapshots"].values():
            assert set(snapshot["member_ids"]) <= exact_node_ids
    assert document["world"]["links"] == [
        {
            "id": "office_corridor",
            "kind": "corridor",
            "label": "Office Corridor",
            "description": (
                "Physical adjacency between work areas; it does not carry the "
                "digital purchase records or imply authority."
            ),
            "endpoint_a_place_id": "operating_area",
            "endpoint_b_place_id": "finance_area",
            "substrate_entity_ids": [],
            "does_not_imply_traversability": True,
        }
    ]


def test_purchase_payment_is_a_closed_inspectable_api_scenario(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[1]
    api = TestClient(create_app(root / "web", tmp_path))
    config = api.get("/api/config").json()
    assert {
        arm["id"]
        for arm in config["scenarios"]["purchase_payment"]["arms"]
    } == {"settled", "approval_denied", "processor_declined"}
    purchase_config = config["scenarios"]["purchase_payment"]
    assert {
        key: purchase_config[key]
        for key in (
            "model",
            "reasoning_effort",
            "maximum_live_calls",
            "maximum_live_cost",
        )
    } == {
        "model": "openrouter/openai/gpt-5.6-terra",
        "reasoning_effort": "medium",
        "maximum_live_calls": 8,
        "maximum_live_cost": 0.38,
    }

    outcomes: dict[str, str] = {}
    for arm_id in ("settled", "approval_denied", "processor_declined"):
        response = api.post(
            "/api/runs",
            json={
                "scenario": "purchase_payment",
                "arm_id": arm_id,
                "execution": "scripted",
            },
        )
        assert response.status_code == 200, response.text
        body = response.json()
        outcomes[arm_id] = body["outcome"]["final_status"]
        assert body["scenario"] == "purchase_payment"
        assert body["time_unit"] == "minute"
        assert body["model_calls"] == 0
        assert len(body["boundaries"]) == 3
        assert body["narration"]["status"] == "not_requested"
        processor = next(
            node
            for node in body["nodes"]
            if node["id"] == "coarse_payment_processor"
        )
        assert processor["state"]["implementation_id"] == (
            "stipulated_payment_processor_v1"
        )
        assert any(
            "cannot answer why" in omission
            for omission in processor["state"]["fidelity"]["known_omissions"]
        )
    assert outcomes == {
        "settled": "settled",
        "approval_denied": "approval_denied",
        "processor_declined": "processor_declined",
    }

    assert (
        api.post(
            "/api/runs",
            json={
                "scenario": "purchase_payment",
                "arm_id": "authorized_access",
            },
        ).status_code
        == 422
    )
    assert (
        api.post(
            "/api/runs",
            json={
                "scenario": "physical_access",
                "arm_id": "settled",
            },
        ).status_code
        == 422
    )
