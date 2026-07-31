"""Reviewed provider-free examples for exercising the authoring workflow."""

from __future__ import annotations

from cybernetic_influence.authoring.models import ScenarioDraftProposal
from cybernetic_influence.scenarios.coordination_decision import PERSON_IDS


def reviewed_coordination_proposal() -> ScenarioDraftProposal:
    """Return the canonical reviewed multinational coordination configuration."""

    positions = {
        "mission_coordinator": "Coordinates the partnership decision.",
        "technical_validation_lead": "Assesses technical validation.",
        "sovereignty_policy_representative": "Assesses authority and oversight.",
        "local_public_health_liaison": "Assesses local safety and legitimacy.",
        "partner_representative": "Represents one participating partner.",
    }
    people = [
        {
            "entity_id": person_id,
            "label": person_id.replace("_", " ").title(),
            "position": positions[person_id],
            "disposition": "Conscientious, fallible, and responsive to evidence.",
            "memories": [
                "The partnership is reviewing a bio-surveillance deployment."
            ],
            "behavioral_profile": {
                "values": ["A legitimate and effective public-health decision."],
                "goals": ["Contribute to a valid collective decision."],
                "beliefs": ["Other participants may hold relevant information."],
                "decision_tendencies": [
                    "Seeks clarification when material uncertainty is salient."
                ],
                "social_perceptions": [
                    "The partnership expects reasons for changed commitments."
                ],
                "current_state": ["Prepared for the first review meeting."],
                "capabilities": ["Can use the interfaces assigned to this position."],
                "limitations": ["Cannot observe undelivered information."],
            },
        }
        for person_id in PERSON_IDS
    ]
    placements: dict[str, str] = {
        person_id: "partnership_hub" for person_id in PERSON_IDS
    }
    placements.update(
        {
            "technical_pressure_source": "source_operations_site",
            "policy_pressure_source": "source_operations_site",
            "local_pressure_source": "source_operations_site",
        }
    )
    payload = {
        "proposal_version": 1,
        "scenario_id": "authored_biosurveillance_decision",
        "title": "Multinational bio-surveillance deployment review",
        "description": (
            "Five people decide whether and how to deploy a shared "
            "bio-surveillance capability."
        ),
        "people": people,
        "objects": [
            {
                "entity_id": "technical_pressure_source",
                "entity_kind": "source_process",
                "label": "Independent technical source",
                "description": "Publishes a bounded calibration concern.",
            },
            {
                "entity_id": "policy_pressure_source",
                "entity_kind": "source_process",
                "label": "Sovereignty source",
                "description": "Publishes a bounded oversight concern.",
            },
            {
                "entity_id": "local_pressure_source",
                "entity_kind": "source_process",
                "label": "Local health source",
                "description": "Publishes a bounded local safety concern.",
            },
        ],
        "information": [
            {
                "information_id": "technical_concern",
                "label": "calibration_uncertainty",
                "content": "Independent calibration may be insufficient.",
            },
            {
                "information_id": "policy_concern",
                "label": "sovereignty_and_transparency",
                "content": "Deployment may weaken local oversight authority.",
            },
            {
                "information_id": "local_concern",
                "label": "local_safety_and_legitimacy",
                "content": "Deployment may create locally unacceptable safety risk.",
            },
        ],
        "places": [
            {
                "place_id": "coordination_world",
                "label": "Coordination world",
                "description": "Spatial root for the reviewed decision.",
            },
            {
                "place_id": "partnership_hub",
                "label": "Partnership hub",
                "description": "Shared location for the partnership meetings.",
            },
            {
                "place_id": "source_operations_site",
                "label": "Source operations site",
                "description": "Location of the three concrete source processes.",
            },
            {
                "place_id": "external_registry_site",
                "label": "External registry site",
                "description": "Location of the external decision registry.",
            },
        ],
        "spatial_links": [
            {
                "spatial_link_id": "partnership_source_network_path",
                "endpoint_a_place_id": "partnership_hub",
                "endpoint_b_place_id": "source_operations_site",
                "description": "Physical-network adjacency to source operations.",
            },
            {
                "spatial_link_id": "partnership_registry_network_path",
                "endpoint_a_place_id": "partnership_hub",
                "endpoint_b_place_id": "external_registry_site",
                "description": "Physical-network adjacency to the registry.",
            },
        ],
        "placements": placements,
        "timing_assumptions": [
            {
                "name": "technical_source_route_delivery",
                "minutes": 90,
                "basis": "Reviewed synthetic timing assumption.",
            },
            {
                "name": "policy_source_route_delivery",
                "minutes": 120,
                "basis": "Reviewed synthetic timing assumption.",
            },
            {
                "name": "local_source_route_delivery",
                "minutes": 150,
                "basis": "Reviewed synthetic timing assumption.",
            },
        ],
        "workflow": {
            "template_id": "coordination_decision_v1",
            "condition": "stabilization",
            "collective_goal": {
                "goal_id": "partnership_decision_goal",
                "label": "Reach a legitimate deployment decision",
                "description": (
                    "Reach a reviewed deployment decision by the deadline while "
                    "respecting technical, sovereignty, and safety constraints."
                ),
                "acceptable_outcomes": [
                    "deploy_on_time",
                    "scope_reduced",
                    "delayed",
                ],
                "constraints": [
                    "No blocking issue may remain open.",
                    "Active partners must support the selected scope.",
                ],
            },
            "meeting_days": [0, 3, 6, 9],
            "deadline_day": 10,
            "terminal_outcomes": [
                "deploy_on_time",
                "delayed",
                "scope_reduced",
                "partner_disengaged",
                "no_decision_by_horizon",
            ],
            "messages": [
                {
                    "message_id": "technical_pressure_message",
                    "information_id": "technical_concern",
                    "source_id": "technical_pressure_source",
                    "recipient_id": "technical_validation_lead",
                    "route_id": "technical_source_route",
                    "representation_kind": "source_message",
                    "delivery_minutes": 90,
                },
                {
                    "message_id": "policy_pressure_message",
                    "information_id": "policy_concern",
                    "source_id": "policy_pressure_source",
                    "recipient_id": "sovereignty_policy_representative",
                    "route_id": "policy_source_route",
                    "representation_kind": "source_message",
                    "delivery_minutes": 120,
                },
                {
                    "message_id": "local_pressure_message",
                    "information_id": "local_concern",
                    "source_id": "local_pressure_source",
                    "recipient_id": "local_public_health_liaison",
                    "route_id": "local_source_route",
                    "representation_kind": "source_message",
                    "delivery_minutes": 150,
                },
            ],
            "stabilizing_resources": [
                "authoritative_validation",
                "evidence_based_risk_admission",
                "uncertainty_bounds",
                "commitment_feedback",
            ],
            "analysis": {
                "analysis_ids": [
                    "waltzman_decision_environment_v1",
                    "levin_collective_competence_v1",
                ],
                "candidate_boundary_ref": "deployment_partnership",
                "candidate_goal_ref": "partnership_decision_goal",
            },
            "assumptions": [
                "The reviewed exact mechanisms adequately represent the bounded decision procedure."
            ],
            "known_omissions": [
                "The scenario does not model the full institutions or software behind the partnership."
            ],
        },
        "analytical_boundaries": [
            {
                "boundary_id": "deployment_partnership",
                "label": "Deployment partnership",
                "description": (
                    "Analytical view over the five people and their coordination "
                    "substrate."
                ),
                "member_refs": [*PERSON_IDS, "partnership_decision_goal"],
            },
            {
                "boundary_id": "pressure_source_ensemble",
                "label": "Concern sources",
                "description": (
                    "Analytical view over three concrete source processes."
                ),
                "member_refs": [
                    "technical_pressure_source",
                    "policy_pressure_source",
                    "local_pressure_source",
                ],
            },
        ],
        "fidelity_questions": [
            "Did people use only retained memory and delivered observations?",
            "Did the exact decision gate enforce the reviewed constraints?",
        ],
        "unresolved_questions": [],
    }
    return ScenarioDraftProposal.model_validate(payload)


def reviewed_component_composition_proposal() -> ScenarioDraftProposal:
    """A provider-free mixed-component review example for Slice 25B."""

    payload = {
        "proposal_version": 1,
        "scenario_id": "reviewed_component_delivery",
        "title": "Field report review",
        "description": (
            "A field coordinator sends a safety report through a declared channel. "
            "A review officer receives it and records a contested assessment in "
            "an exact ledger."
        ),
        "people": [
            {
                "entity_id": "field_coordinator",
                "label": "Field coordinator",
                "position": "Receives and forwards the retained field report.",
                "disposition": "Careful about preserving the report's source and content.",
                "memories": ["A safety report requires documented review."],
            },
            {
                "entity_id": "review_officer",
                "label": "Review officer",
                "position": "Assesses delivered field reports for the decision ledger.",
                "disposition": "Challenges unverified claims before treating them as settled.",
                "memories": ["Only delivered reports can be assessed."],
            },
        ],
        "objects": [
            {
                "entity_id": "secure_review_channel",
                "entity_kind": "message_channel",
                "label": "Secure review channel",
                "description": "The concrete channel used for the reviewed report delivery.",
            }
        ],
        "information": [
            {
                "information_id": "field_safety_report",
                "label": "Field safety report",
                "content": "The field team reports an unverified safety concern requiring review.",
            }
        ],
        "places": [
            {
                "place_id": "field_site",
                "label": "Field site",
                "description": "Where the field coordinator works.",
            },
            {
                "place_id": "review_office",
                "label": "Review office",
                "description": "Where the review officer records the assessment.",
            },
        ],
        "spatial_links": [
            {
                "spatial_link_id": "field_review_link",
                "endpoint_a_place_id": "field_site",
                "endpoint_b_place_id": "review_office",
                "description": "A physical-network relationship represented separately from the review route.",
            }
        ],
        "placements": {
            "field_coordinator": "field_site",
            "review_officer": "review_office",
            "secure_review_channel": "field_site",
            "field_safety_report": "field_site",
        },
        "timing_assumptions": [
            {
                "name": "report_delivery",
                "minutes": 30,
                "basis": "Reviewed synthetic delivery duration.",
            },
            {
                "name": "ledger_recording",
                "minutes": 15,
                "basis": "Reviewed synthetic exact-recording duration.",
            },
        ],
        "workflow": {
            "template_id": "component_composition_v1",
            "components": [
                {"component_id": "field_coordinator", "component_kind": "person_participant", "version": 1},
                {"component_id": "review_officer", "component_kind": "person_participant", "version": 1},
                {"component_id": "secure_review_channel", "component_kind": "stateful_object", "version": 1},
                {"component_id": "field_safety_report", "component_kind": "information_carrier", "version": 1},
                {"component_id": "publication_route", "component_kind": "directed_connection", "version": 1},
                {"component_id": "assessment_route", "component_kind": "directed_connection", "version": 1},
                {"component_id": "publication_delivery", "component_kind": "exact_mechanism", "version": 1},
                {"component_id": "assessment_recording", "component_kind": "exact_mechanism", "version": 1},
            ],
            "source_id": "field_coordinator",
            "recipient_id": "review_officer",
            "record_id": "field_report_ledger",
            "information_id": "field_safety_report",
            "channel_object_id": "secure_review_channel",
            "delivery_enabled": True,
            "delivery_minutes": 30,
            "recording_minutes": 15,
        },
        "analytical_boundaries": [
            {
                "boundary_id": "field_review_team",
                "label": "Field review team",
                "description": "An analytical view of the two people and their concrete report-review components.",
                "member_refs": ["field_coordinator", "review_officer", "secure_review_channel", "field_report_ledger"],
            }
        ],
        "fidelity_questions": [
            "Did the assessment follow delivery through the declared route?",
            "Did the exact ledger record an assessment without inferring report truth?",
        ],
        "unresolved_questions": [],
    }
    return ScenarioDraftProposal.model_validate(payload)
