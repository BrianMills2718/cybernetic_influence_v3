"""Focused proof for reusable authored influence networks."""

from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace
from typing import Any

import pytest

from cybernetic_influence.authoring import ScenarioDraftProposal, compile_scenario
from cybernetic_influence.authoring.compiler import AuthoringCompilationError
from cybernetic_influence.authoring.influence_network import influence_network_outcome
from cybernetic_influence.causal_core.replay import replay_committed_trajectory


def influence_network_proposal() -> ScenarioDraftProposal:
    people = []
    for entity_id, label, position in (
        ("election_director", "Elena", "municipal election director"),
        ("journalist", "Jonah", "local investigative journalist"),
        ("community_leader", "Mara", "neighborhood coalition organizer"),
    ):
        people.append(
            {
                "entity_id": entity_id,
                "label": label,
                "position": position,
                "disposition": "Independent-minded and attentive to evidence provenance.",
                "memories": ["The city must decide whether to certify the election result."],
                "behavioral_profile": {
                    "values": ["Legitimate collective decisions should rest on reviewable evidence."],
                    "goals": ["Reach a defensible position on certification."],
                    "beliefs": ["Different information sources may have different reliability."],
                    "decision_tendencies": ["Compare new claims with the evidence actually received."],
                    "social_perceptions": ["Other participants may receive different messages."],
                    "current_state": ["Attentive but uncertain."],
                    "capabilities": ["Can state a position and explain it."],
                    "limitations": ["Cannot observe messages that were not delivered."],
                },
            }
        )
    return ScenarioDraftProposal.model_validate(
        {
            "scenario_id": "city_election_information_network",
            "title": "City election information network",
            "description": (
                "Three people receive a common public bulletin while two also receive "
                "a targeted allegation, then repeatedly decide whether to certify."
            ),
            "people": people,
            "objects": [
                {
                    "entity_id": "election_office_feed",
                    "entity_kind": "information_source",
                    "label": "Election office feed",
                    "description": "A public municipal bulletin source.",
                },
                {
                    "entity_id": "anonymous_channel",
                    "entity_kind": "information_source",
                    "label": "Anonymous channel",
                    "description": "A source for an unverified targeted allegation.",
                },
            ],
            "information": [
                {
                    "information_id": "public_audit_bulletin",
                    "label": "Public audit bulletin",
                    "content": "The routine tabulation audit found no count discrepancy.",
                },
                {
                    "information_id": "targeted_fraud_allegation",
                    "label": "Targeted fraud allegation",
                    "content": "An anonymous message alleges that one precinct altered ballots.",
                },
            ],
            "places": [
                {
                    "place_id": "city_network",
                    "label": "City information network",
                    "description": "A coarse location for participants and sources.",
                },
                {
                    "place_id": "public_record",
                    "label": "Public record",
                    "description": "A coarse location for the public bulletin source.",
                },
            ],
            "spatial_links": [
                {
                    "spatial_link_id": "public_communications_link",
                    "endpoint_a_place_id": "city_network",
                    "endpoint_b_place_id": "public_record",
                    "description": "Coarse contextual relationship, not the delivery route.",
                }
            ],
            "placements": {
                "election_director": "city_network",
                "journalist": "city_network",
                "community_leader": "city_network",
                "election_office_feed": "public_record",
                "anonymous_channel": "city_network",
            },
            "timing_assumptions": [
                {"name": "public_broadcast", "minutes": 2, "basis": "authored schedule"},
                {"name": "targeted_message", "minutes": 5, "basis": "authored schedule"},
                {"name": "decision_round_1", "minutes": 3, "basis": "authored schedule"},
                {"name": "decision_round_2", "minutes": 7, "basis": "authored schedule"},
            ],
            "workflow": {
                "template_id": "influence_network_v1",
                "collective_question": "Should the city certify the election result?",
                "round_minutes": [3, 7],
                "deliveries": [
                    {
                        "delivery_id": "public_broadcast",
                        "source_id": "election_office_feed",
                        "information_id": "public_audit_bulletin",
                        "recipient_ids": [
                            "election_director",
                            "journalist",
                            "community_leader",
                        ],
                        "delivery_minutes": 2,
                    },
                    {
                        "delivery_id": "targeted_message",
                        "source_id": "anonymous_channel",
                        "information_id": "targeted_fraud_allegation",
                        "recipient_ids": ["journalist", "community_leader"],
                        "delivery_minutes": 5,
                    },
                ],
                "decision_rule": {
                    "minimum_support": 2,
                    "minimum_support_or_conditional": 3,
                    "maximum_oppose": 0,
                },
            },
            "analytical_boundaries": [
                {
                    "boundary_id": "city_decision_network",
                    "label": "City decision network",
                    "description": "An execution-inert view over people and information sources.",
                    "member_refs": [
                        "election_director",
                        "journalist",
                        "community_leader",
                        "election_office_feed",
                        "anonymous_channel",
                    ],
                }
            ],
            "fidelity_questions": [
                "Did only explicit recipients observe each configured message?",
                "Did each person select a stance independently from delivered evidence?",
            ],
        }
    )


def test_influence_network_compiles_fanout_runs_and_replays() -> None:
    compiled = compile_scenario(influence_network_proposal())

    broadcast_routes = {
        connection.target_port_id
        for connection in compiled.scenario.initial_state.connections.values()
        if connection.source_port_id == "public_broadcast_source_out"
    }
    targeted_routes = {
        connection.target_port_id
        for connection in compiled.scenario.initial_state.connections.values()
        if connection.source_port_id == "targeted_message_source_out"
    }
    assert len(broadcast_routes) == 3
    assert len(targeted_routes) == 2
    assert compiled.composition_receipt.workflow_template_id == "influence_network_v1"

    result = compiled.run_scripted(run_id="influence_network_reference")
    final = result.core_result.final_state
    assert final.fact("decision_register.outcome").value == "approved"
    assert final.fact("decision_register.counts").value == {
        "conditional": 0,
        "defer": 0,
        "oppose": 0,
        "support": 3,
    }
    assert result.model_calls == 0
    outcome, headline, summary = influence_network_outcome(result)
    assert headline == "The group approved the proposal"
    assert summary == "Every configured decision threshold passed."
    assert outcome["gate_checks"] == {
        "support": {"actual": 3, "required": 2, "passed": True},
        "support_or_conditional": {"actual": 3, "required": 3, "passed": True},
        "opposition": {"actual": 0, "maximum": 0, "passed": True},
    }
    assert replay_committed_trajectory(compiled.scenario, result.core_result) == final


def test_influence_network_rejects_unknown_delivery_recipient() -> None:
    payload = deepcopy(influence_network_proposal().model_dump(mode="json"))
    payload["workflow"]["deliveries"][0]["recipient_ids"].append("unknown_person")

    with pytest.raises(AuthoringCompilationError, match="unknown recipients"):
        compile_scenario(ScenarioDraftProposal.model_validate(payload))


def test_influence_network_rejects_delivery_after_final_round() -> None:
    payload = deepcopy(influence_network_proposal().model_dump(mode="json"))
    payload["workflow"]["deliveries"][1]["delivery_minutes"] = 8

    with pytest.raises(AuthoringCompilationError, match="after the final decision round"):
        compile_scenario(ScenarioDraftProposal.model_validate(payload))


def test_influence_network_live_people_receive_only_routed_messages() -> None:
    compiled = compile_scenario(influence_network_proposal())
    calls: list[dict[str, Any]] = []

    def decide(
        _model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> tuple[object, object]:
        calls.append({"messages": messages, **kwargs})
        trace_id = str(kwargs["trace_id"])
        person_id = next(
            person_id
            for person_id in ("election_director", "journalist", "community_leader")
            if f"/{person_id}/" in trace_id
        )
        response_model = kwargs["response_model"]
        actions = (
            []
            if person_id == "community_leader"
            else [
                {
                    "output_port_id": f"stance_{person_id}_out",
                    "representation_id": None,
                    "payload": (
                        '{"person_id":"'
                        + person_id
                        + '","stance":"support","reason":"The evidence I received supports certification."}'
                    ),
                    "public_summary": f"{person_id} stated support.",
                }
            ]
        )
        return (
            response_model.model_validate(
                {
                    "orientation": "I will decide from my memories and delivered evidence.",
                    "memory_update": "I retain my latest stated position.",
                    "actions": actions,
                    "silence_reason": (
                        "I am not ready to state a position."
                        if not actions
                        else None
                    ),
                }
            ),
            SimpleNamespace(cost=0.01, cost_source="provider_reported"),
        )

    result = compiled.run_live(
        run_id="influence_network_live",
        model="openrouter/openai/gpt-5.6-luna",
        reasoning_effort="medium",
        per_call_budget=0.05,
        per_run_budget=0.50,
        structured_call=decide,
        participant_concurrency=3,
    )

    assert result.core_result.final_state.fact("decision_register.outcome").value == (
        "not_approved"
    )
    assert result.core_result.final_state.fact("decision_register.counts").value == {
        "conditional": 0,
        "defer": 1,
        "oppose": 0,
        "support": 2,
    }
    assert result.model_calls == 11
    director_inputs = [
        call["messages"][1]["content"]
        for call in calls
        if "/election_director/" in str(call["trace_id"])
    ]
    assert director_inputs
    assert all("targeted_fraud_allegation" not in item for item in director_inputs)
    journalist_inputs = [
        call["messages"][1]["content"]
        for call in calls
        if "/journalist/" in str(call["trace_id"])
    ]
    assert any("targeted_message_representation" in item for item in journalist_inputs)
