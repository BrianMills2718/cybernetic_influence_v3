"""Semantic authoring boundary for the reviewed coordination template.

The LLM and direct-edit API see descriptive fields only.  This module overlays
those fields onto the reviewed template, which remains the sole owner of
runtime IDs, routes, mechanisms, placements, and executable bindings.
"""

from __future__ import annotations

from typing import cast

from cybernetic_influence.authoring.examples import reviewed_coordination_proposal
from cybernetic_influence.authoring.models import (
    CoordinationDecisionWorkflowDraft,
    CoordinationScenarioReview,
    ScenarioDraftProposal,
)


_POSITION_BINDINGS = {
    "coordinator": "mission_coordinator",
    "technical_reviewer": "technical_validation_lead",
    "policy_reviewer": "sovereignty_policy_representative",
    "local_health_reviewer": "local_public_health_liaison",
    "partner_representative": "partner_representative",
}
_CONCERN_BINDINGS = {
    "technical": (
        "technical_pressure_source",
        "technical_concern",
        "technical_pressure_message",
        "technical_source_route_delivery",
    ),
    "policy": (
        "policy_pressure_source",
        "policy_concern",
        "policy_pressure_message",
        "policy_source_route_delivery",
    ),
    "local": (
        "local_pressure_source",
        "local_concern",
        "local_pressure_message",
        "local_source_route_delivery",
    ),
}
_STABILIZERS = [
    "authoritative_validation",
    "evidence_based_risk_admission",
    "uncertainty_bounds",
    "commitment_feedback",
]


def coordination_review_from_proposal(
    proposal: ScenarioDraftProposal,
) -> CoordinationScenarioReview:
    """Project one strict proposal into the ID-free human review contract."""

    workflow = proposal.workflow
    if not isinstance(workflow, CoordinationDecisionWorkflowDraft):
        raise ValueError("proposal is not a coordination_decision_v1 workflow")
    people = {item.entity_id: item for item in proposal.people}
    objects = {item.entity_id: item for item in proposal.objects}
    information = {item.information_id: item for item in proposal.information}
    messages = {str(item.message_id): item for item in workflow.messages}
    places = {item.place_id: item for item in proposal.places}
    boundaries = {item.boundary_id: item for item in proposal.analytical_boundaries}

    return CoordinationScenarioReview.model_validate(
        {
            "template_id": "coordination_decision_v1",
            "title": proposal.title,
            "description": proposal.description,
            "condition": workflow.condition,
            "people": [
                {
                    "position_kind": position_kind,
                    **people[entity_id].model_dump(
                        mode="json",
                        exclude={"entity_id"},
                    ),
                }
                for position_kind, entity_id in _POSITION_BINDINGS.items()
            ],
            "concerns": [
                {
                    "concern_kind": concern_kind,
                    "source_label": objects[source_id].label,
                    "source_description": objects[source_id].description,
                    "topic": information[information_id].label,
                    "content": information[information_id].content,
                    "delivery_minutes": messages[message_id].delivery_minutes,
                }
                for concern_kind, (
                    source_id,
                    information_id,
                    message_id,
                    _timing_name,
                ) in _CONCERN_BINDINGS.items()
            ],
            "collective_goal": workflow.collective_goal.model_dump(
                mode="json", exclude={"goal_id"}
            ),
            "places": {
                "partnership_label": places["partnership_hub"].label,
                "partnership_description": places["partnership_hub"].description,
                "source_site_label": places["source_operations_site"].label,
                "source_site_description": places[
                    "source_operations_site"
                ].description,
                "registry_label": places["external_registry_site"].label,
                "registry_description": places["external_registry_site"].description,
            },
            "analytical_boundaries": {
                "partnership_label": boundaries["deployment_partnership"].label,
                "partnership_description": boundaries[
                    "deployment_partnership"
                ].description,
                "source_group_label": boundaries[
                    "pressure_source_ensemble"
                ].label,
                "source_group_description": boundaries[
                    "pressure_source_ensemble"
                ].description,
            },
            "meeting_days": workflow.meeting_days,
            "deadline_day": workflow.deadline_day,
            "analysis_ids": workflow.analysis.analysis_ids,
            "assumptions": workflow.assumptions,
            "known_omissions": workflow.known_omissions,
            "fidelity_questions": proposal.fidelity_questions,
            "unresolved_questions": proposal.unresolved_questions,
        }
    )


def coordination_proposal_from_review(
    review: CoordinationScenarioReview,
) -> ScenarioDraftProposal:
    """Overlay semantic fields on compiler-owned IDs from the reviewed template."""

    payload = reviewed_coordination_proposal().model_dump(mode="json")
    payload["title"] = review.title
    payload["description"] = review.description
    payload["fidelity_questions"] = review.fidelity_questions
    payload["unresolved_questions"] = review.unresolved_questions

    raw_people = payload["people"]
    assert isinstance(raw_people, list)
    people = {
        cast(str, item["entity_id"]): item
        for item in raw_people
        if isinstance(item, dict)
    }
    for person in review.people:
        entity_id = _POSITION_BINDINGS[person.position_kind]
        people[entity_id].update(
            person.model_dump(mode="json", exclude={"position_kind"})
        )

    raw_objects = payload["objects"]
    raw_information = payload["information"]
    raw_timing = payload["timing_assumptions"]
    raw_workflow = payload["workflow"]
    assert isinstance(raw_objects, list)
    assert isinstance(raw_information, list)
    assert isinstance(raw_timing, list)
    assert isinstance(raw_workflow, dict)
    objects = {
        cast(str, item["entity_id"]): item
        for item in raw_objects
        if isinstance(item, dict)
    }
    information = {
        cast(str, item["information_id"]): item
        for item in raw_information
        if isinstance(item, dict)
    }
    timings = {
        cast(str, item["name"]): item
        for item in raw_timing
        if isinstance(item, dict)
    }
    raw_messages = raw_workflow["messages"]
    assert isinstance(raw_messages, list)
    messages = {
        cast(str, item["message_id"]): item
        for item in raw_messages
        if isinstance(item, dict)
    }
    for concern in review.concerns:
        (
            source_id,
            information_id,
            message_id,
            timing_name,
        ) = _CONCERN_BINDINGS[concern.concern_kind]
        objects[source_id]["label"] = concern.source_label
        objects[source_id]["description"] = concern.source_description
        information[information_id]["label"] = concern.topic
        information[information_id]["content"] = concern.content
        messages[message_id]["delivery_minutes"] = concern.delivery_minutes
        timings[timing_name]["minutes"] = concern.delivery_minutes

    raw_workflow["condition"] = review.condition
    raw_goal = raw_workflow["collective_goal"]
    assert isinstance(raw_goal, dict)
    goal_id = cast(str, raw_goal["goal_id"])
    raw_goal.update(review.collective_goal.model_dump(mode="json"))
    raw_workflow["meeting_days"] = review.meeting_days
    raw_workflow["deadline_day"] = review.deadline_day
    raw_workflow["stabilizing_resources"] = (
        list(_STABILIZERS) if review.condition == "stabilization" else []
    )
    raw_analysis = raw_workflow["analysis"]
    assert isinstance(raw_analysis, dict)
    raw_analysis["analysis_ids"] = review.analysis_ids
    raw_analysis["candidate_goal_ref"] = goal_id
    raw_workflow["assumptions"] = review.assumptions
    raw_workflow["known_omissions"] = review.known_omissions

    raw_places = payload["places"]
    assert isinstance(raw_places, list)
    places = {
        cast(str, item["place_id"]): item
        for item in raw_places
        if isinstance(item, dict)
    }
    places["partnership_hub"].update(
        {
            "label": review.places.partnership_label,
            "description": review.places.partnership_description,
        }
    )
    places["source_operations_site"].update(
        {
            "label": review.places.source_site_label,
            "description": review.places.source_site_description,
        }
    )
    places["external_registry_site"].update(
        {
            "label": review.places.registry_label,
            "description": review.places.registry_description,
        }
    )

    raw_boundaries = payload["analytical_boundaries"]
    assert isinstance(raw_boundaries, list)
    boundaries = {
        cast(str, item["boundary_id"]): item
        for item in raw_boundaries
        if isinstance(item, dict)
    }
    boundaries["deployment_partnership"].update(
        {
            "label": review.analytical_boundaries.partnership_label,
            "description": review.analytical_boundaries.partnership_description,
        }
    )
    boundaries["pressure_source_ensemble"].update(
        {
            "label": review.analytical_boundaries.source_group_label,
            "description": review.analytical_boundaries.source_group_description,
        }
    )
    return ScenarioDraftProposal.model_validate(payload)
