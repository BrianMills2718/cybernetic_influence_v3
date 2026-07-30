"""The constrained draft language for reviewed authored scenario templates.

These records are intentionally human-reviewable.  They are not a general
mechanism language: the compiler selects only reviewed executable templates and
owns all ports, carriers, exact mechanisms, and runtime bindings.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


_FORBID = ConfigDict(extra="forbid", strict=True)
_ID_PATTERN = r"^[a-z][a-z0-9_]*$"
ProfileStatement = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]


class _StrictModel(BaseModel):
    model_config = _FORBID


class BehavioralProfileDraft(_StrictModel):
    """Scenario-relevant descriptions of one person, not behavioral commands."""

    values: list[ProfileStatement] = Field(
        default_factory=list,
        description="Principles or outcomes the person regards as important.",
    )
    goals: list[ProfileStatement] = Field(
        default_factory=list,
        description="Outcomes the person currently wants to bring about.",
    )
    beliefs: list[ProfileStatement] = Field(
        default_factory=list,
        description="Claims the person currently takes to be true and may be wrong about.",
    )
    decision_tendencies: list[ProfileStatement] = Field(
        default_factory=list,
        description="Scenario-relevant habits, biases, or ways the person tends to decide.",
    )
    social_perceptions: list[ProfileStatement] = Field(
        default_factory=list,
        description="What the person thinks others do, value, or expect.",
    )
    current_state: list[ProfileStatement] = Field(
        default_factory=list,
        description="Current affect, attention, confidence, fatigue, or intent.",
    )
    capabilities: list[ProfileStatement] = Field(
        default_factory=list,
        description="Relevant real-world skills or knowledge attributed to the person.",
    )
    limitations: list[ProfileStatement] = Field(
        default_factory=list,
        description="Relevant real-world skill, knowledge, physical, or practical limits.",
    )


class PersonDraft(_StrictModel):
    entity_id: str = Field(pattern=_ID_PATTERN)
    label: str = Field(min_length=1)
    position: str = Field(min_length=1)
    disposition: str = Field(min_length=1)
    memories: list[str] = Field(min_length=1)
    behavioral_profile: BehavioralProfileDraft = Field(
        default_factory=BehavioralProfileDraft
    )


class ObjectDraft(_StrictModel):
    entity_id: str = Field(pattern=_ID_PATTERN)
    entity_kind: str = Field(pattern=_ID_PATTERN)
    label: str = Field(min_length=1)
    description: str = Field(min_length=1)


class InformationDraft(_StrictModel):
    information_id: str = Field(pattern=_ID_PATTERN)
    label: str = Field(min_length=1)
    content: str = Field(min_length=1)


class PlaceDraft(_StrictModel):
    place_id: str = Field(pattern=_ID_PATTERN)
    label: str = Field(min_length=1)
    description: str = Field(min_length=1)


class SpatialLinkDraft(_StrictModel):
    spatial_link_id: str = Field(pattern=_ID_PATTERN)
    endpoint_a_place_id: str = Field(pattern=_ID_PATTERN)
    endpoint_b_place_id: str = Field(pattern=_ID_PATTERN)
    description: str = Field(min_length=1)

    @model_validator(mode="after")
    def distinct_endpoints(self) -> "SpatialLinkDraft":
        if self.endpoint_a_place_id == self.endpoint_b_place_id:
            raise ValueError("spatial link endpoints must be distinct")
        return self


class TimingAssumption(_StrictModel):
    name: str = Field(pattern=_ID_PATTERN)
    minutes: int = Field(ge=1)
    basis: str = Field(min_length=1)


class AnalyticalBoundaryDraft(_StrictModel):
    boundary_id: str = Field(pattern=_ID_PATTERN)
    label: str = Field(min_length=1)
    description: str = Field(min_length=1)
    member_refs: list[str] = Field(min_length=1)


class ResourceRequestWorkflowDraft(_StrictModel):
    template_id: Literal["resource_request_v1"]
    requester_id: str = Field(pattern=_ID_PATTERN)
    reviewer_id: str = Field(pattern=_ID_PATTERN)
    request_id: str = Field(pattern=_ID_PATTERN)
    resource_id: str = Field(pattern=_ID_PATTERN)
    policy_information_id: str = Field(pattern=_ID_PATTERN)
    eligible_requester_ids: list[str] = Field(min_length=1)
    resource_available: bool
    request_delivery_minutes: int = Field(ge=1)
    decision_delivery_minutes: int = Field(ge=1)
    result_delivery_minutes: int = Field(ge=1)


class InformationCampaignWorkflowDraft(_StrictModel):
    """One traceable publication and assessment pathway, not a persuasion oracle."""

    template_id: Literal["information_campaign_v1"]
    source_id: str = Field(pattern=_ID_PATTERN)
    recipient_id: str = Field(pattern=_ID_PATTERN)
    campaign_id: str = Field(pattern=_ID_PATTERN)
    claim_information_id: str = Field(pattern=_ID_PATTERN)
    channel_object_id: str = Field(pattern=_ID_PATTERN)
    publication_enabled: bool
    publication_delivery_minutes: int = Field(ge=1)
    assessment_recording_minutes: int = Field(ge=1)


CoordinationOutcome = Literal[
    "deploy_on_time",
    "delayed",
    "scope_reduced",
    "partner_disengaged",
    "no_decision_by_horizon",
]
CoordinationConditionDraft = Literal[
    "baseline",
    "heterogeneous_pressure",
    "stabilization",
]
CoordinationAnalysisId = Literal[
    "waltzman_decision_environment_v1",
    "levin_collective_competence_v1",
]


class CollectiveGoalDraft(_StrictModel):
    """One reviewed candidate collective goal, not an organization mind."""

    goal_id: str = Field(pattern=_ID_PATTERN)
    label: str = Field(min_length=1)
    description: str = Field(min_length=1)
    acceptable_outcomes: list[CoordinationOutcome] = Field(min_length=1)
    constraints: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_outcomes(self) -> "CollectiveGoalDraft":
        if len(self.acceptable_outcomes) != len(set(self.acceptable_outcomes)):
            raise ValueError("collective goal outcomes must be unique")
        return self


class CoordinationMessageDraft(_StrictModel):
    """One concrete source representation and configured delivery route."""

    message_id: Literal[
        "technical_pressure_message",
        "policy_pressure_message",
        "local_pressure_message",
    ]
    information_id: str = Field(pattern=_ID_PATTERN)
    source_id: str = Field(pattern=_ID_PATTERN)
    recipient_id: str = Field(pattern=_ID_PATTERN)
    route_id: Literal[
        "technical_source_route",
        "policy_source_route",
        "local_source_route",
    ]
    representation_kind: Literal["source_message"]
    delivery_minutes: int = Field(ge=1)


class CoordinationAnalysisDraft(_StrictModel):
    """Reviewed post-run analyses; this record has no execution authority."""

    analysis_ids: list[CoordinationAnalysisId] = Field(min_length=1)
    candidate_boundary_ref: str = Field(pattern=_ID_PATTERN)
    candidate_goal_ref: str = Field(pattern=_ID_PATTERN)

    @model_validator(mode="after")
    def unique_analysis_ids(self) -> "CoordinationAnalysisDraft":
        if len(self.analysis_ids) != len(set(self.analysis_ids)):
            raise ValueError("analysis IDs must be unique")
        return self


class CoordinationDecisionWorkflowDraft(_StrictModel):
    """Bounded authoring surface for the reviewed coordination runtime."""

    template_id: Literal["coordination_decision_v1"]
    condition: CoordinationConditionDraft
    collective_goal: CollectiveGoalDraft
    meeting_days: list[int] = Field(min_length=4, max_length=4)
    deadline_day: int = Field(ge=1)
    terminal_outcomes: list[CoordinationOutcome] = Field(min_length=1)
    messages: list[CoordinationMessageDraft] = Field(min_length=3, max_length=3)
    stabilizing_resources: list[
        Literal[
            "authoritative_validation",
            "evidence_based_risk_admission",
            "uncertainty_bounds",
            "commitment_feedback",
        ]
    ] = Field(default_factory=list)
    analysis: CoordinationAnalysisDraft
    assumptions: list[str] = Field(min_length=1)
    known_omissions: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_closed_sets(self) -> "CoordinationDecisionWorkflowDraft":
        for label, values in (
            ("meeting days", self.meeting_days),
            ("terminal outcomes", self.terminal_outcomes),
            ("message IDs", [item.message_id for item in self.messages]),
            ("stabilizing resources", self.stabilizing_resources),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"{label} must be unique")
        return self


class ScenarioDraftProposal(_StrictModel):
    """One proposal that can be semantically validated before compilation."""

    proposal_version: Literal[1] = 1
    scenario_id: str = Field(pattern=_ID_PATTERN)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    people: list[PersonDraft] = Field(min_length=2)
    objects: list[ObjectDraft] = Field(min_length=1)
    information: list[InformationDraft] = Field(min_length=1)
    places: list[PlaceDraft] = Field(min_length=2)
    spatial_links: list[SpatialLinkDraft] = Field(min_length=1)
    placements: dict[str, str] = Field(min_length=2)
    timing_assumptions: list[TimingAssumption] = Field(min_length=1)
    workflow: Annotated[
        ResourceRequestWorkflowDraft
        | InformationCampaignWorkflowDraft
        | CoordinationDecisionWorkflowDraft,
        Field(discriminator="template_id"),
    ]
    analytical_boundaries: list[AnalyticalBoundaryDraft] = Field(min_length=1)
    fidelity_questions: list[str] = Field(min_length=1)
    unresolved_questions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_declared_ids(self) -> "ScenarioDraftProposal":
        for label, values in (
            ("people", [item.entity_id for item in self.people]),
            ("objects", [item.entity_id for item in self.objects]),
            ("information", [item.information_id for item in self.information]),
            ("places", [item.place_id for item in self.places]),
            ("spatial links", [item.spatial_link_id for item in self.spatial_links]),
            ("timing assumptions", [item.name for item in self.timing_assumptions]),
            ("analytical boundaries", [item.boundary_id for item in self.analytical_boundaries]),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate {label}")
        return self
