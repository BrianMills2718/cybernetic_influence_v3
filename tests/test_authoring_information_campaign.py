"""Focused proof for the bounded information-campaign authoring template."""

from __future__ import annotations

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
