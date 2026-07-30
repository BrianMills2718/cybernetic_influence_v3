"""Compile reviewed coordination drafts onto the existing exact runtime."""

from __future__ import annotations

import json

from cybernetic_influence.authoring.models import (
    CoordinationDecisionWorkflowDraft,
    ScenarioDraftProposal,
)
from cybernetic_influence.causal_core.models import representation_digest
from cybernetic_influence.scenarios.coordination_decision import (
    DECISION_DEADLINE_DAY,
    MEETING_DAYS,
    PARTNERSHIP_BOUNDARY_ID,
    PERSON_IDS,
    PRESSURE_SOURCE_IDS,
    SOURCE_BOUNDARY_ID,
    CoordinationDecisionFixture,
    baseline_coordination_fixture,
    heterogeneous_pressure_coordination_fixture,
    stabilization_coordination_fixture,
)


_MESSAGE_BINDINGS = {
    "technical_pressure_message": (
        "technical_pressure_source",
        "technical_validation_lead",
        "technical_source_route",
    ),
    "policy_pressure_message": (
        "policy_pressure_source",
        "sovereignty_policy_representative",
        "policy_source_route",
    ),
    "local_pressure_message": (
        "local_pressure_source",
        "local_public_health_liaison",
        "local_source_route",
    ),
}
_REQUIRED_TERMINAL_OUTCOMES = {
    "deploy_on_time",
    "delayed",
    "scope_reduced",
    "partner_disengaged",
    "no_decision_by_horizon",
}
_REQUIRED_ANALYSES = {
    "waltzman_decision_environment_v1",
    "levin_collective_competence_v1",
}
_REQUIRED_PLACE_IDS = {
    "coordination_world",
    "partnership_hub",
    "source_operations_site",
    "external_registry_site",
}
_REQUIRED_SPATIAL_LINK_IDS = {
    "partnership_source_network_path",
    "partnership_registry_network_path",
}
_STABILIZERS = {
    "authoritative_validation",
    "evidence_based_risk_admission",
    "uncertainty_bounds",
    "commitment_feedback",
}


def validate_coordination_proposal(proposal: ScenarioDraftProposal) -> None:
    """Reject references or options the bounded runtime cannot implement."""

    workflow = proposal.workflow
    if not isinstance(workflow, CoordinationDecisionWorkflowDraft):
        raise ValueError("proposal is not a coordination_decision_v1 workflow")

    people = {item.entity_id: item for item in proposal.people}
    objects = {item.entity_id: item for item in proposal.objects}
    information = {item.information_id: item for item in proposal.information}
    places = {item.place_id: item for item in proposal.places}
    links = {item.spatial_link_id: item for item in proposal.spatial_links}
    boundaries = {
        item.boundary_id: item for item in proposal.analytical_boundaries
    }

    if set(people) != set(PERSON_IDS):
        raise ValueError(
            "coordination_decision_v1 requires exactly the five reviewed people"
        )
    for person in people.values():
        profile = person.behavioral_profile
        if any(
            not values
            for values in (
                profile.values,
                profile.goals,
                profile.beliefs,
                profile.decision_tendencies,
                profile.social_perceptions,
                profile.current_state,
                profile.capabilities,
                profile.limitations,
            )
        ):
            raise ValueError(
                f"coordination person {person.entity_id!r} requires a complete "
                "reviewable behavioral profile"
            )

    if set(PRESSURE_SOURCE_IDS) - set(objects):
        raise ValueError("coordination draft is missing a reviewed source process")
    if any(
        objects[source_id].entity_kind != "source_process"
        for source_id in PRESSURE_SOURCE_IDS
    ):
        raise ValueError("coordination sources must be concrete source_process objects")
    if any(
        "organization" in item.entity_kind and "executor" in item.entity_kind
        for item in proposal.objects
    ):
        raise ValueError("an analytical organization cannot be a world executor")

    all_declared_ids = [
        *people,
        *objects,
        *information,
        workflow.collective_goal.goal_id,
    ]
    if len(all_declared_ids) != len(set(all_declared_ids)):
        raise ValueError(
            "people, objects, information, and collective goal need distinct IDs"
        )

    if tuple(workflow.meeting_days) != MEETING_DAYS:
        raise ValueError(
            "the bounded coordination runtime currently supports meeting days "
            f"{list(MEETING_DAYS)!r}"
        )
    if workflow.deadline_day != DECISION_DEADLINE_DAY:
        raise ValueError(
            "the bounded coordination runtime currently supports deadline day "
            f"{DECISION_DEADLINE_DAY}"
        )
    if set(workflow.terminal_outcomes) != _REQUIRED_TERMINAL_OUTCOMES:
        raise ValueError(
            "terminal outcomes must cover every exact reviewed decision outcome"
        )

    expected_stabilizers = (
        _STABILIZERS if workflow.condition == "stabilization" else set()
    )
    if set(workflow.stabilizing_resources) != expected_stabilizers:
        raise ValueError(
            "stabilizing resources do not match the selected reviewed condition"
        )

    messages = {item.message_id: item for item in workflow.messages}
    if set(messages) != set(_MESSAGE_BINDINGS):
        raise ValueError("coordination workflow requires the three reviewed messages")
    for message in workflow.messages:
        message_id = message.message_id
        expected = _MESSAGE_BINDINGS[message_id]
        observed = (message.source_id, message.recipient_id, message.route_id)
        if observed != expected:
            raise ValueError(
                f"message {message_id!r} has an incompatible source, recipient, "
                "or route"
            )
        if message.information_id not in information:
            raise ValueError(
                f"message {message_id!r} references unknown information "
                f"{message.information_id!r}"
            )
        timing_name = f"{message.route_id}_delivery"
        timing = {
            item.name: item.minutes for item in proposal.timing_assumptions
        }
        if timing.get(timing_name) != message.delivery_minutes:
            raise ValueError(
                f"timing assumption {timing_name!r} must equal the message delay"
            )

    if set(places) != _REQUIRED_PLACE_IDS:
        raise ValueError("coordination draft must declare the reviewed place topology")
    if set(links) != _REQUIRED_SPATIAL_LINK_IDS:
        raise ValueError("coordination draft must declare the reviewed spatial links")
    for link in links.values():
        if {link.endpoint_a_place_id, link.endpoint_b_place_id} - set(places):
            raise ValueError(f"spatial link {link.spatial_link_id!r} is ungrounded")

    placeable = set(PERSON_IDS) | set(PRESSURE_SOURCE_IDS)
    if set(proposal.placements) != placeable:
        raise ValueError(
            "coordination placements must cover exactly the reviewed people and sources"
        )
    if set(proposal.placements.values()) - set(places):
        raise ValueError("coordination placement refers to an unknown place")

    if set(boundaries) != {PARTNERSHIP_BOUNDARY_ID, SOURCE_BOUNDARY_ID}:
        raise ValueError("coordination draft requires the two reviewed boundaries")
    partnership = boundaries[PARTNERSHIP_BOUNDARY_ID]
    sources = boundaries[SOURCE_BOUNDARY_ID]
    if not (set(PERSON_IDS) | {workflow.collective_goal.goal_id}) <= set(
        partnership.member_refs
    ):
        raise ValueError("candidate partnership boundary is missing people or goal")
    if set(PRESSURE_SOURCE_IDS) & set(partnership.member_refs):
        raise ValueError("pressure source cannot enter the partnership boundary")
    if set(PRESSURE_SOURCE_IDS) - set(sources.member_refs):
        raise ValueError("source boundary is missing a concrete source")

    analysis = workflow.analysis
    if set(analysis.analysis_ids) != _REQUIRED_ANALYSES:
        raise ValueError("the MVP configuration must select both analysis modules")
    if analysis.candidate_boundary_ref not in boundaries:
        raise ValueError("analysis refers to a boundary outside the configuration")
    if analysis.candidate_boundary_ref != PARTNERSHIP_BOUNDARY_ID:
        raise ValueError("Levin analysis must use the partnership boundary")
    if analysis.candidate_goal_ref != workflow.collective_goal.goal_id:
        raise ValueError("analysis refers to a goal outside the configuration")


def authored_coordination_fixture(
    proposal: ScenarioDraftProposal,
) -> CoordinationDecisionFixture:
    """Map reviewed values onto the existing tested coordination mechanisms."""

    validate_coordination_proposal(proposal)
    workflow = proposal.workflow
    assert isinstance(workflow, CoordinationDecisionWorkflowDraft)
    builders = {
        "baseline": baseline_coordination_fixture,
        "heterogeneous_pressure": heterogeneous_pressure_coordination_fixture,
        "stabilization": stabilization_coordination_fixture,
    }
    payload = builders[workflow.condition]().model_dump(mode="json")
    scenario = payload["scenario"]
    state = scenario["initial_state"]
    entities = state["entities"]
    representations = state["representations"]

    scenario["description"] = proposal.description
    scenario["fidelity_questions"] = proposal.fidelity_questions

    people = {item.entity_id: item for item in proposal.people}
    for person_id in PERSON_IDS:
        person = people[person_id]
        profile = person.behavioral_profile
        assumptions = {
            "position": person.position,
            "dispositions": [person.disposition],
            "memories": person.memories,
            "values": profile.values,
            "goals": profile.goals,
            "beliefs": profile.beliefs,
            "decision_tendencies": profile.decision_tendencies,
            "perceived_social_conditions": profile.social_perceptions,
            "current_state": profile.current_state,
            "capabilities": profile.capabilities,
            "limitations": profile.limitations,
        }
        entities[person_id]["description"] = person.position
        entities[person_id]["attributes"]["assumptions"]["value"] = assumptions

    goal = entities.pop("decision_goal")
    goal_placement = state["placements"].pop("decision_goal")
    goal_id = workflow.collective_goal.goal_id
    goal["entity_id"] = goal_id
    goal["description"] = workflow.collective_goal.description
    goal["attributes"] = {
        "label": {"value": workflow.collective_goal.label, "visibility": "public"},
        "acceptable_outcomes": {
            "value": workflow.collective_goal.acceptable_outcomes,
            "visibility": "public",
        },
        "constraints": {
            "value": workflow.collective_goal.constraints,
            "visibility": "public",
        },
    }
    entities[goal_id] = goal
    goal_placement["entity_id"] = goal_id
    state["placements"][goal_id] = goal_placement
    entities["deployment_proposal"]["description"] = (
        workflow.collective_goal.description
    )

    objects = {item.entity_id: item for item in proposal.objects}
    for source_id in PRESSURE_SOURCE_IDS:
        entities[source_id]["description"] = objects[source_id].description

    information = {
        item.information_id: item for item in proposal.information
    }
    for message in workflow.messages:
        item = information[message.information_id]
        content = json.dumps(
            {
                "document_kind": message.representation_kind,
                "topic": item.label,
                "claim": item.content,
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        representation = representations[message.message_id]
        representation["content"] = content
        representation["content_hash"] = representation_digest(content)
        entities[message.source_id]["attributes"]["message_topic"]["value"] = (
            item.label
        )
        state["connections"][message.route_id]["delay"] = message.delivery_minutes

    places = {item.place_id: item for item in proposal.places}
    for place_id, place in places.items():
        state["places"][place_id]["description"] = place.description
    links = {item.spatial_link_id: item for item in proposal.spatial_links}
    for link_id, link in links.items():
        state["spatial_links"][link_id]["description"] = link.description
    for entity_id, place_id in proposal.placements.items():
        state["placements"][entity_id]["place_id"] = place_id

    authored_boundaries = {
        item.boundary_id: item for item in proposal.analytical_boundaries
    }
    for boundary in scenario["analytical_boundaries"]:
        authored = authored_boundaries[boundary["boundary_id"]]
        boundary["label"] = authored.label
        boundary["description"] = authored.description
        boundary["member_refs"] = [
            goal_id if member == "decision_goal" else member
            for member in boundary["member_refs"]
        ]

    payload["run_control_options"]["default_terminal_condition_ids"] = [
        f"decision_{outcome}" for outcome in workflow.terminal_outcomes
    ]
    return CoordinationDecisionFixture.model_validate(payload)
