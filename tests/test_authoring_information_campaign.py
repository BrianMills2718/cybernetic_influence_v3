"""Focused proof for the bounded information-campaign authoring template."""

from __future__ import annotations

import re
from types import SimpleNamespace
from typing import Any

import pytest

from cybernetic_influence.active_runtime import ParticipantContractError
from cybernetic_influence.authoring import ScenarioDraftProposal, compile_scenario
from cybernetic_influence.causal_core.replay import replay_committed_trajectory


def information_campaign_proposal(*, publication_enabled: bool = True) -> ScenarioDraftProposal:
    return ScenarioDraftProposal.model_validate({
        "scenario_id": "diplomatic_claim_campaign",
        "title": "Diplomatic-position disinformation pathway",
        "description": "A campaign source publishes a false claim about a diplomatic position through a media channel; a State Department analyst receives and assesses the claim.",
        "people": [
            {
                "entity_id": "campaign_operator", "label": "Campaign operator",
                "position": "information campaign operator",
                "disposition": "The operator is focused on amplifying the retained claim.",
                "memories": ["A claim package has been prepared for publication."],
                "behavioral_profile": {
                    "values": ["The operator values campaign reach."],
                    "goals": ["The operator wants the claim published."],
                    "beliefs": ["The operator believes the claim supports the campaign."],
                    "decision_tendencies": ["The operator tends to prioritize publication."],
                    "social_perceptions": ["The operator expects campaign peers to reward reach."],
                    "current_state": ["The operator is ready to publish."],
                    "capabilities": ["The operator can submit content to the configured channel."],
                    "limitations": ["The operator cannot control the recipient's assessment."],
                },
            },
            {
                "entity_id": "department_analyst", "label": "Department analyst",
                "position": "public diplomacy analyst",
                "disposition": "The analyst is skeptical of unsupported diplomatic claims.",
                "memories": ["The department's retained position does not match the campaign claim."],
                "behavioral_profile": {
                    "values": ["The analyst values evidential accuracy."],
                    "goals": ["The analyst wants to assess the delivered claim."],
                    "beliefs": ["The analyst believes the retained position contradicts the claim."],
                    "decision_tendencies": ["The analyst tends to compare claims with retained context."],
                    "social_perceptions": [],
                    "current_state": ["The analyst is attentive to incoming claims."],
                    "capabilities": ["The analyst can record an assessment."],
                    "limitations": ["The analyst cannot infer population persuasion from delivery."],
                },
            },
        ],
        "objects": [{"entity_id": "media_channel", "entity_kind": "media_platform", "label": "Media publication channel", "description": "The concrete publication service used for the claim."}],
        "information": [{"information_id": "false_negotiation_claim", "label": "False negotiation-position claim", "content": "The State Department has secretly abandoned its stated negotiation position."}],
        "places": [
            {"place_id": "campaign_office", "label": "Campaign office", "description": "The source's authored location."},
            {"place_id": "department_office", "label": "Department office", "description": "The analyst's authored location."},
        ],
        "spatial_links": [{"spatial_link_id": "international_network", "endpoint_a_place_id": "campaign_office", "endpoint_b_place_id": "department_office", "description": "A coarse physical network relationship; it is not the publication route."}],
        "placements": {"campaign_operator": "campaign_office", "department_analyst": "department_office", "media_channel": "campaign_office"},
        "timing_assumptions": [
            {"name": "publication_delivery", "minutes": 15, "basis": "authored scenario estimate"},
            {"name": "assessment_recording", "minutes": 30, "basis": "authored scenario estimate"},
        ],
        "workflow": {
            "template_id": "information_campaign_v1", "source_id": "campaign_operator",
            "recipient_id": "department_analyst", "campaign_id": "campaign_record",
            "claim_information_id": "false_negotiation_claim", "channel_object_id": "media_channel",
            "publication_enabled": publication_enabled, "publication_delivery_minutes": 15,
            "assessment_recording_minutes": 30,
        },
        "analytical_boundaries": [
            {"boundary_id": "campaign_view", "label": "Campaign analytical view", "description": "An execution-inert view over source, claim, channel, and campaign record.", "member_refs": ["campaign_operator", "false_negotiation_claim", "media_channel", "campaign_record"]},
            {"boundary_id": "department_view", "label": "State Department analytical view", "description": "An execution-inert view over the concrete analyst.", "member_refs": ["department_analyst"]},
        ],
        "fidelity_questions": [
            "Did the claim reach the analyst only through the configured publication route?",
            "Did the trace distinguish delivery and assessment from persuasion or geopolitical effect?",
        ],
    })


def test_information_campaign_compiles_runs_and_replays() -> None:
    compiled = compile_scenario(information_campaign_proposal())
    result = compiled.run_scripted(run_id="information_campaign_reference")
    final = result.core_result.final_state

    assert compiled.proposal.workflow.template_id == "information_campaign_v1"
    assert final.fact("campaign_record.status").value == "assessed_contested"
    assert result.model_calls == 0
    assert result.total_observed_cost == 0.0
    assert replay_committed_trajectory(compiled.scenario, result.core_result) == final
    assert [attempt.declared_active_system_ids for attempt in result.attempts] == [
        ["campaign_source"], ["campaign_recipient"],
    ]


def test_disabled_publication_dissipates_without_inventing_recipient_access() -> None:
    compiled = compile_scenario(information_campaign_proposal(publication_enabled=False))
    result = compiled.run_scripted(run_id="information_campaign_disabled")

    assert result.core_result.final_state.fact("campaign_record.status").value == "drafted"
    assert [attempt.declared_active_system_ids for attempt in result.attempts] == [["campaign_source"]]
    assert any(event.event_kind == "effect_dissipated" for event in result.core_result.events)


def test_live_people_use_reviewed_profiles_and_only_delivered_representations() -> None:
    compiled = compile_scenario(information_campaign_proposal())
    calls: list[dict[str, Any]] = []

    def decide(
        _model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> tuple[object, object]:
        calls.append({"messages": messages, **kwargs})
        trace_id = str(kwargs["trace_id"])
        response_model = kwargs["response_model"]
        if "/campaign_source/" in trace_id:
            action = {
                "output_port_id": "source_publish_out",
                "representation_id": "claim_copy",
                "payload": "{}",
                "public_summary": "The campaign operator published the retained claim.",
            }
        else:
            user = messages[1]["content"]
            permitted = re.search(
                r"permitted representation IDs:\s+([a-z][a-z0-9_]*)",
                user,
            )
            assert permitted is not None
            delivered_id = permitted.group(1)
            action = {
                "output_port_id": "recipient_assess_out",
                "representation_id": delivered_id,
                "payload": '{"disposition":"contested"}',
                "public_summary": "The analyst recorded a contested assessment.",
            }
        return (
            response_model.model_validate(
                {
                    "orientation": "I will use only the supplied information and interface.",
                    "memory_update": "I remember the action I attempted.",
                    "actions": [action],
                    "silence_reason": None,
                }
            ),
            SimpleNamespace(cost=0.01, cost_source="provider_reported"),
        )

    result = compiled.run_live(
        run_id="information_campaign_live_profiles",
        model="openrouter/openai/gpt-5.6-terra",
        reasoning_effort="medium",
        per_call_budget=0.05,
        per_run_budget=0.20,
        structured_call=decide,
    )

    assert result.model_calls == 2
    assert result.total_observed_cost == pytest.approx(0.02)
    assert result.core_result.final_state.fact("campaign_record.status").value == (
        "assessed_contested"
    )
    assert replay_committed_trajectory(compiled.scenario, result.core_result) == (
        result.core_result.final_state
    )
    source_system = calls[0]["messages"][0]["content"]
    recipient_system = calls[1]["messages"][0]["content"]
    assert "The operator values campaign reach." in source_system
    assert "The analyst is skeptical of unsupported diplomatic claims." in recipient_system
    assert "campaign_record.status" not in calls[1]["messages"][1]["content"]
    recipient_input = result.attempts[1].participants[0].input
    assert len(recipient_input.observations) == 1
    assert recipient_input.action_interfaces[0].representation_ids == [
        recipient_input.observations[0].representation_id
    ]


def test_live_person_cannot_use_an_undelivered_representation() -> None:
    compiled = compile_scenario(information_campaign_proposal())

    def forge(
        _model: str,
        _messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> tuple[object, object]:
        trace_id = str(kwargs["trace_id"])
        response_model = kwargs["response_model"]
        source = "/campaign_source/" in trace_id
        return (
            response_model.model_validate(
                {
                    "orientation": "Attempting one action.",
                    "memory_update": "",
                    "actions": [
                        {
                            "output_port_id": (
                                "source_publish_out"
                                if source
                                else "recipient_assess_out"
                            ),
                            "representation_id": "claim_copy",
                            "payload": (
                                "{}"
                                if source
                                else '{"disposition":"contested"}'
                            ),
                            "public_summary": "Attempted action.",
                        }
                    ],
                    "silence_reason": None,
                }
            ),
            SimpleNamespace(cost=0.01, cost_source="provider_reported"),
        )

    with pytest.raises(
        ParticipantContractError,
        match="referenced inaccessible representation",
    ):
        compiled.run_live(
            run_id="information_campaign_live_forgery",
            model="openrouter/openai/gpt-5.6-terra",
            reasoning_effort="medium",
            per_call_budget=0.05,
            per_run_budget=0.20,
            structured_call=forge,
        )


def test_live_source_cannot_smuggle_content_beside_the_retained_claim() -> None:
    compiled = compile_scenario(information_campaign_proposal())

    def add_payload(
        _model: str,
        _messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> tuple[object, object]:
        response_model = kwargs["response_model"]
        return (
            response_model.model_validate(
                {
                    "orientation": "I will publish the selected retained claim.",
                    "memory_update": "",
                    "actions": [
                        {
                            "output_port_id": "source_publish_out",
                            "representation_id": "claim_copy",
                            "payload": '{"content":"replacement claim"}',
                            "public_summary": "Attempted publication.",
                        }
                    ],
                    "silence_reason": None,
                }
            ),
            SimpleNamespace(cost=0.01, cost_source="provider_reported"),
        )

    with pytest.raises(ValueError, match="publication payload must be empty"):
        compiled.run_live(
            run_id="information_campaign_payload_smuggling",
            model="openrouter/openai/gpt-5.6-terra",
            reasoning_effort="medium",
            per_call_budget=0.05,
            per_run_budget=0.20,
            structured_call=add_payload,
        )


def test_information_campaign_rejects_a_second_authored_campaign_record() -> None:
    proposal = information_campaign_proposal()
    proposal.objects.append(type(proposal.objects[0]).model_validate({
        "entity_id": "duplicate_campaign_record",
        "entity_kind": "campaign_record",
        "label": "Duplicate campaign record",
        "description": "A record the compiler already owns.",
    }))
    try:
        compile_scenario(proposal)
    except ValueError as error:
        assert "creates its campaign record" in str(error)
    else:
        raise AssertionError("a second authored campaign record was accepted")
