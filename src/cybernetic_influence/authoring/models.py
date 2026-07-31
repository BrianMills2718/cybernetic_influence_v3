"""The constrained draft language for reviewed authored scenario templates.

These records are intentionally human-reviewable.  They are not a general
mechanism language: the compiler selects only reviewed executable templates and
owns all ports, carriers, exact mechanisms, and runtime bindings.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from cybernetic_influence.authoring.composition import ComponentSelectionV1


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


class ComponentCompositionWorkflowDraft(_StrictModel):
    """Reviewed delivery-and-recording composition, not executable source code."""

    template_id: Literal["component_composition_v1"]
    components: list[ComponentSelectionV1] = Field(min_length=8, max_length=8)
    source_id: str = Field(pattern=_ID_PATTERN)
    recipient_id: str = Field(pattern=_ID_PATTERN)
    record_id: str = Field(pattern=_ID_PATTERN)
    information_id: str = Field(pattern=_ID_PATTERN)
    channel_object_id: str = Field(pattern=_ID_PATTERN)
    delivery_enabled: bool
    delivery_minutes: int = Field(ge=1)
    recording_minutes: int = Field(ge=1)

    @model_validator(mode="after")
    def unique_component_ids(self) -> "ComponentCompositionWorkflowDraft":
        component_ids = [item.component_id for item in self.components]
        if len(component_ids) != len(set(component_ids)):
            raise ValueError("composition component IDs must be unique")
        return self


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
CoordinationPositionKind = Literal[
    "coordinator",
    "technical_reviewer",
    "policy_reviewer",
    "local_health_reviewer",
    "partner_representative",
]
CoordinationConcernKind = Literal["technical", "policy", "local"]


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


class CoordinationPersonReview(_StrictModel):
    """Human-facing person description without a compiler-owned entity ID."""

    position_kind: CoordinationPositionKind = Field(
        description="The one reviewed decision position occupied by this person."
    )
    label: str = Field(
        min_length=1,
        description="The human-readable name shown for this person.",
    )
    position: str = Field(
        min_length=1,
        description="A descriptive account of the person's position in the situation.",
    )
    disposition: str = Field(
        min_length=1,
        description="Stable tendencies relevant to how this person may decide.",
    )
    memories: list[str] = Field(
        min_length=1,
        description="Information or experience this person already remembers.",
    )
    behavioral_profile: BehavioralProfileDraft = Field(
        description="Descriptive behavioral assumptions about this person."
    )


class CoordinationConcernReview(_StrictModel):
    """One human-facing concern; source, recipient, and route IDs are compiled."""

    concern_kind: CoordinationConcernKind = Field(
        description="The reviewed semantic kind of outside concern."
    )
    source_label: str = Field(
        min_length=1,
        description="The human-readable name of the concrete concern source.",
    )
    source_description: str = Field(
        min_length=1,
        description="What the concrete source is in the modeled situation.",
    )
    topic: str = Field(
        min_length=1,
        description="A concise human-readable topic for the concern.",
    )
    content: str = Field(
        min_length=1,
        description="The information delivered by this concern source.",
    )
    delivery_minutes: int = Field(
        ge=1,
        description="Positive scenario minutes before the concern is delivered.",
    )


class CoordinationPlaceReview(_StrictModel):
    """Editable descriptions for the reviewed spatial projection."""

    partnership_label: str = Field(
        min_length=1,
        description="The human-readable name of the shared decision location.",
    )
    partnership_description: str = Field(
        min_length=1,
        description="What the shared decision location represents.",
    )
    source_site_label: str = Field(
        min_length=1,
        description="The human-readable name of the concern-source location.",
    )
    source_site_description: str = Field(
        min_length=1,
        description="What the concern-source location represents.",
    )
    registry_label: str = Field(
        min_length=1,
        description="The human-readable name of the external decision destination.",
    )
    registry_description: str = Field(
        min_length=1,
        description="What the external decision destination represents.",
    )


class CoordinationBoundaryReview(_StrictModel):
    """Human-facing names for execution-inert analytical group views."""

    partnership_label: str = Field(
        min_length=1,
        description="The label for the execution-inert partnership view.",
    )
    partnership_description: str = Field(
        min_length=1,
        description="What exact members the partnership view groups for analysis.",
    )
    source_group_label: str = Field(
        min_length=1,
        description="The label for the execution-inert concern-source view.",
    )
    source_group_description: str = Field(
        min_length=1,
        description="What exact sources the concern-source view groups for analysis.",
    )


class CoordinationGoalReview(_StrictModel):
    """Human-facing candidate goal without a compiler-owned goal ID."""

    label: str = Field(
        min_length=1,
        description="The human-readable name of the candidate collective goal.",
    )
    description: str = Field(
        min_length=1,
        description="What success would mean for the candidate collective goal.",
    )
    acceptable_outcomes: list[CoordinationOutcome] = Field(
        min_length=1,
        description="Terminal outcomes that count as satisfying the candidate goal.",
    )
    constraints: list[str] = Field(
        min_length=1,
        description="Constraints the decision must respect to satisfy the goal.",
    )

    @model_validator(mode="after")
    def unique_outcomes(self) -> "CoordinationGoalReview":
        if len(self.acceptable_outcomes) != len(set(self.acceptable_outcomes)):
            raise ValueError("acceptable outcomes must be unique")
        return self


class CoordinationScenarioReview(_StrictModel):
    """Complete semantic review/edit surface for the bounded coordination template."""

    template_id: Literal["coordination_decision_v1"] = Field(
        description="The reviewed executable coordination template."
    )
    title: str = Field(
        min_length=1,
        description="A concise human-readable name for the situation.",
    )
    description: str = Field(
        min_length=1,
        description="A plain-language account of the decision situation.",
    )
    condition: CoordinationConditionDraft = Field(
        description="The reviewed world condition applied to this scenario."
    )
    people: list[CoordinationPersonReview] = Field(
        min_length=5,
        max_length=5,
        description="Exactly one concrete person in each reviewed position.",
    )
    concerns: list[CoordinationConcernReview] = Field(
        min_length=3,
        max_length=3,
        description="Exactly one technical, policy, and local concern source.",
    )
    collective_goal: CoordinationGoalReview = Field(
        description="The candidate collective goal used only for analysis."
    )
    places: CoordinationPlaceReview = Field(
        description="Human-readable labels for the reviewed spatial projection."
    )
    analytical_boundaries: CoordinationBoundaryReview = Field(
        description="Execution-inert group views used for multiscale analysis."
    )
    meeting_days: list[int] = Field(
        min_length=4,
        max_length=4,
        description="The reviewed four-day meeting cadence [0, 3, 6, 9].",
    )
    deadline_day: int = Field(
        ge=1,
        description="The reviewed terminal decision deadline on day 10.",
    )
    analysis_ids: list[CoordinationAnalysisId] = Field(
        min_length=1,
        description="One or both per-run analyses to apply after execution.",
    )
    assumptions: list[str] = Field(
        min_length=1,
        description="Material assumptions needed to interpret the simulation.",
    )
    known_omissions: list[str] = Field(
        min_length=1,
        description="Material real-world behavior outside this bounded scenario.",
    )
    fidelity_questions: list[str] = Field(
        min_length=1,
        description="Questions a reviewer should check against the exact trace.",
    )
    unresolved_questions: list[str] = Field(
        default_factory=list,
        description="Only user choices that would materially change the causal question.",
    )

    @model_validator(mode="after")
    def complete_closed_sets(self) -> "CoordinationScenarioReview":
        position_kinds = [item.position_kind for item in self.people]
        concern_kinds = [item.concern_kind for item in self.concerns]
        expected_positions = {
            "coordinator",
            "technical_reviewer",
            "policy_reviewer",
            "local_health_reviewer",
            "partner_representative",
        }
        expected_concerns = {"technical", "policy", "local"}
        if set(position_kinds) != expected_positions:
            raise ValueError(
                "coordination review requires each of the five reviewed positions"
            )
        if len(position_kinds) != len(set(position_kinds)):
            raise ValueError("coordination review positions must be unique")
        if set(concern_kinds) != expected_concerns:
            raise ValueError(
                "coordination review requires technical, policy, and local concerns"
            )
        if len(concern_kinds) != len(set(concern_kinds)):
            raise ValueError("coordination concern kinds must be unique")
        for label, values in (
            ("meeting days", self.meeting_days),
            ("analysis IDs", self.analysis_ids),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"{label} must be unique")
        if self.meeting_days != sorted(self.meeting_days):
            raise ValueError("meeting days must be in increasing order")
        if self.deadline_day <= self.meeting_days[-1]:
            raise ValueError("the deadline must be after the final meeting")
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
        | ComponentCompositionWorkflowDraft
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
