"""Strict zero-execution fixtures for the Slice-21 coordination scenario.

Packet 21A0 owns only reviewed domain records and pure fixture construction.
Scheduling, exact handlers, participant policies, and model calls belong to
later packets.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from cybernetic_influence.active_runtime.run_control import (
    ExactFactTerminalCondition,
    RunControlOptions,
)
from cybernetic_influence.causal_core.models import (
    AnalyticalBoundary,
    CarrierState,
    CausalScenario,
    CausalState,
    ConnectionState,
    EntityState,
    FactState,
    FidelityNote,
    MechanismSpec,
    PlacementState,
    PlaceState,
    PortState,
    RepresentationToken,
    SpatialLinkState,
    representation_digest,
)

CoordinationCondition: TypeAlias = Literal[
    "baseline",
    "heterogeneous_pressure",
    "stabilization",
]
IssueLifecycle: TypeAlias = Literal["open", "resolved", "reopened"]
SourceDisposition: TypeAlias = Literal[
    "unreviewed",
    "relied_on",
    "rejected",
    "validation_pending",
]
Commitment: TypeAlias = Literal[
    "support_full",
    "support_reduced",
    "defer",
    "withdraw",
]
DecisionScope: TypeAlias = Literal["full", "reduced", "none"]
FinalDecision: TypeAlias = Literal[
    "deploy_on_time",
    "delayed",
    "scope_reduced",
    "partner_disengaged",
    "no_decision_by_horizon",
]
PersonId: TypeAlias = Literal[
    "mission_coordinator",
    "technical_validation_lead",
    "sovereignty_policy_representative",
    "local_public_health_liaison",
    "partner_representative",
]
PressureSourceId: TypeAlias = Literal[
    "technical_pressure_source",
    "policy_pressure_source",
    "local_pressure_source",
]

SCENARIO_ID = "coordination_decision_v1"
PARTNERSHIP_BOUNDARY_ID = "deployment_partnership"
SOURCE_BOUNDARY_ID = "pressure_source_ensemble"
CONDITION_ENTITY_ID = "coordination_condition"
DECISION_ENTITY_ID = "decision_record"
EXTERNAL_RECEIVER_ID = "external_decision_registry"
MEETING_DAYS: tuple[int, ...] = (0, 3, 6, 9)
DECISION_DEADLINE_DAY = 10
MAX_CAUSAL_MOMENTS = 28
MAX_PARTICIPANT_CALLS = 20

PERSON_IDS: tuple[PersonId, ...] = (
    "mission_coordinator",
    "technical_validation_lead",
    "sovereignty_policy_representative",
    "local_public_health_liaison",
    "partner_representative",
)
PRESSURE_SOURCE_IDS: tuple[PressureSourceId, ...] = (
    "technical_pressure_source",
    "policy_pressure_source",
    "local_pressure_source",
)
PRESSURE_SOURCE_CARRIER_IDS: tuple[str, ...] = (
    "technical_pressure_carrier",
    "policy_pressure_carrier",
    "local_pressure_carrier",
)
PRESSURE_SOURCE_REPRESENTATION_IDS: tuple[str, ...] = (
    "technical_pressure_message",
    "policy_pressure_message",
    "local_pressure_message",
)

_FORBID = ConfigDict(extra="forbid", strict=True)


class _StrictModel(BaseModel):
    """Reject coercion and unknown fields at every scenario-local boundary."""

    model_config = _FORBID


class CoordinationConditionConfig(_StrictModel):
    """The entire reviewed condition surface for one scenario arm."""

    schema_version: Literal[1] = 1
    condition: CoordinationCondition
    pressure_sources_enabled: bool
    adaptive_follow_up_enabled: bool
    authoritative_validation_enabled: bool
    evidence_based_risk_admission_enabled: bool
    uncertainty_bounds_enabled: bool
    commitment_feedback_enabled: bool

    @model_validator(mode="after")
    def validate_condition(self) -> "CoordinationConditionConfig":
        expected = {
            "baseline": (False, False, False, False, False, False),
            "heterogeneous_pressure": (True, True, False, False, False, False),
            "stabilization": (True, True, True, True, True, True),
        }[self.condition]
        observed = (
            self.pressure_sources_enabled,
            self.adaptive_follow_up_enabled,
            self.authoritative_validation_enabled,
            self.evidence_based_risk_admission_enabled,
            self.uncertainty_bounds_enabled,
            self.commitment_feedback_enabled,
        )
        if observed != expected:
            raise ValueError("condition flags do not match the reviewed arm")
        return self


class IssueItem(_StrictModel):
    """One concrete concern tracked through a reviewed lifecycle."""

    issue_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    topic: str = Field(min_length=1)
    lifecycle: IssueLifecycle
    blocking: bool
    opened_by: PersonId
    evidence_refs: list[str] = Field(default_factory=list)


class VerificationItem(_StrictModel):
    """One retained request/response record, initially unrequested."""

    verification_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    topic: str = Field(min_length=1)
    requested_by: PersonId | None = None
    status: Literal["not_requested", "pending", "answered"]
    response_representation_id: str | None = Field(
        default=None,
        pattern=r"^[a-z][a-z0-9_]*$",
    )

    @model_validator(mode="after")
    def validate_status(self) -> "VerificationItem":
        if self.status == "not_requested" and (
            self.requested_by is not None or self.response_representation_id is not None
        ):
            raise ValueError("unrequested verification cannot have request/response data")
        if self.status == "pending" and self.requested_by is None:
            raise ValueError("pending verification requires a requester")
        if self.status == "answered" and (
            self.requested_by is None or self.response_representation_id is None
        ):
            raise ValueError("answered verification requires requester and response")
        return self


class SourceDispositionRecord(_StrictModel):
    """One person's explicit retained treatment of one concrete source."""

    person_id: PersonId
    source_id: PressureSourceId
    disposition: SourceDisposition
    evidence_refs: list[str] = Field(default_factory=list)


class CommitmentRecord(_StrictModel):
    """One person's current decision commitment."""

    person_id: PersonId
    commitment: Commitment
    updated_at_day: int = Field(ge=0)


class MeetingSlot(_StrictModel):
    """One authored recurring decision opportunity."""

    meeting_index: int = Field(ge=0, le=3)
    modeled_day: int = Field(ge=0, le=9)
    due_person_ids: list[PersonId] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_due_people(self) -> "MeetingSlot":
        if len(self.due_person_ids) != len(set(self.due_person_ids)):
            raise ValueError("meeting due people must be unique")
        if tuple(self.due_person_ids) != PERSON_IDS:
            raise ValueError("each reviewed meeting must include the five people")
        return self


class MeetingSchedule(_StrictModel):
    """The four reviewed meeting opportunities and exact decision deadline."""

    schema_version: Literal[1] = 1
    slots: list[MeetingSlot] = Field(min_length=4, max_length=4)
    deadline_day: Literal[10] = 10

    @model_validator(mode="after")
    def validate_schedule(self) -> "MeetingSchedule":
        indices = [slot.meeting_index for slot in self.slots]
        days = [slot.modeled_day for slot in self.slots]
        if len(indices) != len(set(indices)):
            raise ValueError("meeting indices must be unique")
        if len(days) != len(set(days)):
            raise ValueError("meeting times must be unique")
        if indices != list(range(4)) or tuple(days) != MEETING_DAYS:
            raise ValueError("meeting schedule must use reviewed indices and days")
        return self


class DecisionProposal(_StrictModel):
    """A typed proposal; executable predicates are deliberately impossible."""

    proposal_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    proposed_by: PersonId
    requested_status: FinalDecision
    requested_scope: DecisionScope
    evidence_refs: list[str]
    acknowledged_issue_ids: list[str]
    active_partner_ids: list[PersonId]

    @model_validator(mode="after")
    def validate_references(self) -> "DecisionProposal":
        for label, refs in (
            ("evidence refs", self.evidence_refs),
            ("acknowledged issue ids", self.acknowledged_issue_ids),
            ("active partner ids", self.active_partner_ids),
        ):
            if len(refs) != len(set(refs)):
                raise ValueError(f"decision proposal {label} must be unique")
        return self


class PersonAssumptions(_StrictModel):
    """Reviewed descriptive person context without procedural commands."""

    position: str = Field(min_length=1)
    dispositions: list[str] = Field(min_length=1)
    memories: list[str] = Field(min_length=1)
    values: list[str] = Field(min_length=1)
    goals: list[str] = Field(min_length=1)
    beliefs: list[str] = Field(min_length=1)
    decision_tendencies: list[str] = Field(min_length=1)
    perceived_social_conditions: list[str] = Field(min_length=1)
    current_state: list[str] = Field(min_length=1)
    capabilities: list[str] = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)


class CoordinationDecisionFixture(_StrictModel):
    """One strict arm with no runtime implementations or model bindings."""

    condition: CoordinationConditionConfig
    schedule: MeetingSchedule
    scenario: CausalScenario
    run_control_options: RunControlOptions

    @model_validator(mode="after")
    def validate_fixture_contract(self) -> "CoordinationDecisionFixture":
        state = self.scenario.initial_state
        if self.scenario.scenario_id != SCENARIO_ID:
            raise ValueError("coordination scenario id drifted")
        if any(connection.delay <= 0 for connection in state.connections.values()):
            raise ValueError("coordination routes require positive duration")
        condition_entity = state.entities.get(CONDITION_ENTITY_ID)
        if condition_entity is None:
            raise ValueError("compiled condition entity is missing")
        expected_condition = self.condition.model_dump(mode="json")
        observed_condition = {
            key: fact.value for key, fact in condition_entity.attributes.items()
        }
        if observed_condition != expected_condition:
            raise ValueError("compiled condition entity does not match its contract")
        schedule_entity = state.entities.get("meeting_schedule")
        if schedule_entity is None:
            raise ValueError("meeting schedule entity is missing")
        if schedule_entity.attributes["schedule"].value != self.schedule.model_dump(
            mode="json"
        ):
            raise ValueError("compiled meeting schedule does not match its contract")
        decision_entity = state.entities.get(DECISION_ENTITY_ID)
        if decision_entity is None:
            raise ValueError("decision record is missing")
        external_receiver = state.entities.get(EXTERNAL_RECEIVER_ID)
        if external_receiver is None:
            raise ValueError("external decision receiver is missing")
        if external_receiver.attributes["received_status"].value is not None:
            raise ValueError("initial final decision must be unset")
        boundaries = {
            boundary.boundary_id: boundary
            for boundary in self.scenario.analytical_boundaries
        }
        if set(boundaries) != {PARTNERSHIP_BOUNDARY_ID, SOURCE_BOUNDARY_ID}:
            raise ValueError("coordination analytical boundaries drifted")
        partnership = boundaries[PARTNERSHIP_BOUNDARY_ID]
        source_boundary = boundaries[SOURCE_BOUNDARY_ID]
        if set(PERSON_IDS) - set(partnership.member_refs):
            raise ValueError("partnership boundary is missing a person")
        if set(PRESSURE_SOURCE_IDS) & set(partnership.member_refs):
            raise ValueError("pressure source entered the partnership boundary")
        if EXTERNAL_RECEIVER_ID in partnership.member_refs:
            raise ValueError("external decision receiver entered partnership boundary")
        if set(PRESSURE_SOURCE_IDS) - set(source_boundary.member_refs):
            raise ValueError("source boundary is missing a pressure source")
        output_route = state.connections.get("terminal_decision_output_route")
        if output_route is None:
            raise ValueError("reviewed terminal-decision output route is missing")
        source_owner = state.ports[output_route.source_port_id].owner_ref
        target_owner = state.ports[output_route.target_port_id].owner_ref
        if source_owner not in partnership.member_refs:
            raise ValueError("terminal-decision route does not originate inside")
        if target_owner in partnership.member_refs:
            raise ValueError("terminal-decision route does not leave the boundary")
        if self.run_control_options.default_horizon != DECISION_DEADLINE_DAY:
            raise ValueError("run-control deadline drifted")
        return self


def baseline_coordination_fixture() -> CoordinationDecisionFixture:
    """Build the ordinary-review control with inactive pressure processes."""

    return _build_fixture(
        CoordinationConditionConfig(
            condition="baseline",
            pressure_sources_enabled=False,
            adaptive_follow_up_enabled=False,
            authoritative_validation_enabled=False,
            evidence_based_risk_admission_enabled=False,
            uncertainty_bounds_enabled=False,
            commitment_feedback_enabled=False,
        )
    )


def heterogeneous_pressure_coordination_fixture() -> CoordinationDecisionFixture:
    """Build the heterogeneous-source arm with adaptive follow-up enabled."""

    return _build_fixture(
        CoordinationConditionConfig(
            condition="heterogeneous_pressure",
            pressure_sources_enabled=True,
            adaptive_follow_up_enabled=True,
            authoritative_validation_enabled=False,
            evidence_based_risk_admission_enabled=False,
            uncertainty_bounds_enabled=False,
            commitment_feedback_enabled=False,
        )
    )


def stabilization_coordination_fixture() -> CoordinationDecisionFixture:
    """Build the same pressure arm with all reviewed stabilizers enabled."""

    return _build_fixture(
        CoordinationConditionConfig(
            condition="stabilization",
            pressure_sources_enabled=True,
            adaptive_follow_up_enabled=True,
            authoritative_validation_enabled=True,
            evidence_based_risk_admission_enabled=True,
            uncertainty_bounds_enabled=True,
            commitment_feedback_enabled=True,
        )
    )


def coordination_decision_fixtures() -> tuple[CoordinationDecisionFixture, ...]:
    """Build and cross-check the complete three-arm family."""

    fixtures = (
        baseline_coordination_fixture(),
        heterogeneous_pressure_coordination_fixture(),
        stabilization_coordination_fixture(),
    )
    validate_coordination_fixture_family(fixtures)
    return fixtures


def scenario_fingerprint(scenario: CausalScenario) -> str:
    """Return a stable digest of one complete reviewed scenario."""

    return hashlib.sha256(_canonical_json(scenario.model_dump(mode="json"))).hexdigest()


def condition_independent_scenario_dump(scenario: CausalScenario) -> bytes:
    """Remove only the reviewed condition entity for cross-arm comparison."""

    payload = scenario.model_dump(mode="json")
    initial_state = payload["initial_state"]
    assert isinstance(initial_state, dict)
    entities = initial_state["entities"]
    assert isinstance(entities, dict)
    if CONDITION_ENTITY_ID not in entities:
        raise ValueError("compiled condition entity is missing")
    del entities[CONDITION_ENTITY_ID]
    return _canonical_json(payload)


def validate_coordination_fixture_family(
    fixtures: tuple[CoordinationDecisionFixture, ...],
) -> None:
    """Fail if anything except the reviewed condition entity differs by arm."""

    if len(fixtures) != 3:
        raise ValueError("coordination fixture family requires exactly three arms")
    conditions = [fixture.condition.condition for fixture in fixtures]
    if conditions != ["baseline", "heterogeneous_pressure", "stabilization"]:
        raise ValueError("coordination fixture family is missing a reviewed arm")
    normalized = [
        condition_independent_scenario_dump(fixture.scenario) for fixture in fixtures
    ]
    if len(set(normalized)) != 1:
        raise ValueError("scenario drift exists outside the reviewed condition entity")
    fingerprints = [scenario_fingerprint(fixture.scenario) for fixture in fixtures]
    if len(set(fingerprints)) != 3:
        raise ValueError("complete arm fingerprints must differ")


def _build_fixture(
    condition: CoordinationConditionConfig,
) -> CoordinationDecisionFixture:
    schedule = MeetingSchedule(
        slots=[
            MeetingSlot(
                meeting_index=index,
                modeled_day=day,
                due_person_ids=list(PERSON_IDS),
            )
            for index, day in enumerate(MEETING_DAYS)
        ]
    )
    state = _initial_state(condition, schedule)
    scenario = CausalScenario(
        scenario_id=SCENARIO_ID,
        description=(
            "A synthetic multinational partnership reviews whether and how to "
            "deploy an upgraded bio-surveillance system by a modeled deadline."
        ),
        time_unit="scenario_day",
        timing_contract="positive_duration",
        minimum_world_duration=1,
        initial_state=state,
        analytical_boundaries=[
            AnalyticalBoundary(
                boundary_id=PARTNERSHIP_BOUNDARY_ID,
                label="Deployment partnership",
                description=(
                    "Execution-inert view of the five people, internal decision "
                    "records, interfaces, and exact coordination mechanisms."
                ),
                member_refs=_partnership_members(state),
            ),
            AnalyticalBoundary(
                boundary_id=SOURCE_BOUNDARY_ID,
                label="Pressure-source ensemble",
                description=(
                    "Execution-inert view of three concrete source processes and "
                    "their retained shared objective."
                ),
                member_refs=[
                    *PRESSURE_SOURCE_IDS,
                    *PRESSURE_SOURCE_CARRIER_IDS,
                    *PRESSURE_SOURCE_REPRESENTATION_IDS,
                    "pressure_source_objective",
                    "technical_source_out",
                    "policy_source_out",
                    "local_source_out",
                ],
            ),
        ],
        fidelity_questions=[
            "Did every person use only retained memory and delivered observations?",
            "Did configured pressure alter concrete routes and records rather than hidden trust state?",
            "Did the terminal decision cross the partnership boundary before external receipt?",
        ],
    )
    return CoordinationDecisionFixture(
        condition=condition,
        schedule=schedule,
        scenario=scenario,
        run_control_options=_run_control_options(),
    )


def _initial_state(
    condition: CoordinationConditionConfig,
    schedule: MeetingSchedule,
) -> CausalState:
    entities = _entities(condition, schedule)
    places = _places()
    placements = _placements(entities)
    ports = _ports()
    mechanisms = _mechanisms()
    carriers, representations = _information_state()
    return CausalState(
        entities=entities,
        places=places,
        placements=placements,
        spatial_links=_spatial_links(),
        ports=ports,
        connections=_connections(),
        mechanisms=mechanisms,
        carriers=carriers,
        representations=representations,
    )


def _entities(
    condition: CoordinationConditionConfig,
    schedule: MeetingSchedule,
) -> dict[str, EntityState]:
    people: dict[str, EntityState] = {
        person_id: EntityState(
            entity_id=person_id,
            entity_kind="person",
            description=_person_assumptions(person_id).position,
            attributes={
                "assumptions": _fact(
                    _person_assumptions(person_id).model_dump(mode="json"),
                    visibility="analyst",
                )
            },
        )
        for person_id in PERSON_IDS
    }
    sources: dict[str, EntityState] = {
        "technical_pressure_source": EntityState(
            entity_id="technical_pressure_source",
            entity_kind="source_process",
            description="Concrete source process carrying calibration uncertainty.",
            attributes={"message_topic": _fact("calibration_uncertainty")},
        ),
        "policy_pressure_source": EntityState(
            entity_id="policy_pressure_source",
            entity_kind="source_process",
            description="Concrete source process carrying sovereignty concerns.",
            attributes={"message_topic": _fact("sovereignty_and_transparency")},
        ),
        "local_pressure_source": EntityState(
            entity_id="local_pressure_source",
            entity_kind="source_process",
            description="Concrete source process carrying local safety concerns.",
            attributes={"message_topic": _fact("local_safety_and_legitimacy")},
        ),
    }
    records: dict[str, EntityState] = {
        CONDITION_ENTITY_ID: EntityState(
            entity_id=CONDITION_ENTITY_ID,
            entity_kind="mechanism_configuration",
            description="Reviewed configuration consumed only by exact processes.",
            attributes={
                key: _fact(value, visibility="mechanism")
                for key, value in condition.model_dump(mode="json").items()
            },
        ),
        "deployment_proposal": EntityState(
            entity_id="deployment_proposal",
            entity_kind="proposal_record",
            description="Proposal to deploy the upgraded bio-surveillance system.",
            attributes={
                "scope": _fact("full"),
                "decision_threshold": _fact("reviewed_evidence_and_partner_support"),
            },
        ),
        "technical_validation_dossier": EntityState(
            entity_id="technical_validation_dossier",
            entity_kind="evidence_record",
            description="Initial technical evidence supporting deployment.",
            attributes={"validation_status": _fact("initially_supportive")},
        ),
        "meeting_schedule": EntityState(
            entity_id="meeting_schedule",
            entity_kind="schedule_record",
            description="Four authored decision meetings and the day-10 deadline.",
            attributes={"schedule": _fact(schedule.model_dump(mode="json"))},
        ),
        "decision_goal": EntityState(
            entity_id="decision_goal",
            entity_kind="goal_record",
            description="Reach a valid terminal deployment decision by day 10.",
            attributes={
                "capability": _fact("valid_collective_decision_by_deadline_v1")
            },
        ),
        "issue_register": EntityState(
            entity_id="issue_register",
            entity_kind="issue_record",
            description="Concrete lifecycle record for decision-blocking issues.",
            attributes={"items": _fact([])},
        ),
        "verification_register": EntityState(
            entity_id="verification_register",
            entity_kind="verification_record",
            description="Concrete verification request and response record.",
            attributes={"items": _fact([])},
        ),
        "source_disposition_register": EntityState(
            entity_id="source_disposition_register",
            entity_kind="source_disposition_record",
            description="Retained person-to-source reliance and rejection record.",
            attributes={"items": _fact([])},
        ),
        "commitment_register": EntityState(
            entity_id="commitment_register",
            entity_kind="commitment_record",
            description="Retained commitments for all five participants.",
            attributes={
                "items": _fact(
                    [
                        CommitmentRecord(
                            person_id=person_id,
                            commitment="support_full",
                            updated_at_day=0,
                        ).model_dump(mode="json")
                        for person_id in PERSON_IDS
                    ]
                )
            },
        ),
        DECISION_ENTITY_ID: EntityState(
            entity_id=DECISION_ENTITY_ID,
            entity_kind="decision_record",
            description="Internal retained proposal and gate-decision state.",
            attributes={
                "gate_status": _fact("pending"),
                "proposed_status": _fact(None),
                "proposed_scope": _fact("none"),
                "active_partner_count": _fact(5),
            },
        ),
        "pressure_source_objective": EntityState(
            entity_id="pressure_source_objective",
            entity_kind="objective_record",
            description="Concrete shared objective retained by the three sources.",
            attributes={"objective": _fact("increase_decision_friction")},
        ),
        EXTERNAL_RECEIVER_ID: EntityState(
            entity_id=EXTERNAL_RECEIVER_ID,
            entity_kind="decision_receiver",
            description="External registry that receives a committed decision effect.",
            attributes={
                "received_status": _fact(None),
                "received_scope": _fact("none"),
            },
        ),
        "meeting_clock": EntityState(
            entity_id="meeting_clock",
            entity_kind="deterministic_process",
            description="Retained process that emits due meeting and deadline wakes.",
        ),
        "coordination_platform": EntityState(
            entity_id="coordination_platform",
            entity_kind="computing_system",
            description="Exact substrate for records, delivery, and scheduling.",
        ),
        "external_registry_system": EntityState(
            entity_id="external_registry_system",
            entity_kind="computing_system",
            description="Exact substrate for external decision receipt.",
        ),
    }
    return {**people, **sources, **records}


def _person_assumptions(person_id: str) -> PersonAssumptions:
    positions = {
        "mission_coordinator": "Person coordinating the decision schedule and commitments.",
        "technical_validation_lead": "Person assessing calibration and independent validation.",
        "sovereignty_policy_representative": "Person assessing oversight, transparency, and authority.",
        "local_public_health_liaison": "Person assessing local safety and legitimacy.",
        "partner_representative": "Person deciding whether the represented partner remains committed.",
    }
    values = {
        "mission_coordinator": ["timely coordination", "procedural legitimacy"],
        "technical_validation_lead": ["technical accuracy", "independent validation"],
        "sovereignty_policy_representative": ["lawful authority", "transparency"],
        "local_public_health_liaison": ["public safety", "local legitimacy"],
        "partner_representative": ["partner interests", "credible commitments"],
    }
    return PersonAssumptions(
        position=positions[person_id],
        dispositions=["conscientious", "fallible", "responsive to credible evidence"],
        memories=["The initial dossier supports deployment subject to review."],
        values=values[person_id],
        goals=["Contribute to a valid decision without concealing material concerns."],
        beliefs=["Other participants may hold relevant information not yet delivered."],
        decision_tendencies=["Requests clarification when a material uncertainty is salient."],
        perceived_social_conditions=["The partnership expects reasons for changed commitments."],
        current_state=["Prepared for the first scheduled meeting."],
        capabilities=["Can use only the interfaces assigned to this position."],
        limitations=["Cannot observe undelivered messages or hidden mechanism state."],
    )


def _places() -> dict[str, PlaceState]:
    return {
        "coordination_world": PlaceState(
            place_id="coordination_world",
            place_kind="world",
            description="Spatial root for the synthetic decision environment.",
        ),
        "partnership_hub": PlaceState(
            place_id="partnership_hub",
            place_kind="facility",
            description="Shared partnership meeting and decision location.",
            parent_place_id="coordination_world",
        ),
        "source_operations_site": PlaceState(
            place_id="source_operations_site",
            place_kind="network_site",
            description="Location of the three concrete pressure-source processes.",
            parent_place_id="coordination_world",
        ),
        "external_registry_site": PlaceState(
            place_id="external_registry_site",
            place_kind="facility",
            description="Location of the external decision registry.",
            parent_place_id="coordination_world",
        ),
    }


def _placements(entities: dict[str, EntityState]) -> dict[str, PlacementState]:
    placements: dict[str, PlacementState] = {}
    for entity_id in entities:
        if entity_id in PRESSURE_SOURCE_IDS or entity_id == "pressure_source_objective":
            place_id = "source_operations_site"
        elif entity_id in {EXTERNAL_RECEIVER_ID, "external_registry_system"}:
            place_id = "external_registry_site"
        else:
            place_id = "partnership_hub"
        placements[entity_id] = PlacementState(entity_id=entity_id, place_id=place_id)
    return placements


def _spatial_links() -> dict[str, SpatialLinkState]:
    return {
        "partnership_source_network_path": SpatialLinkState(
            spatial_link_id="partnership_source_network_path",
            endpoint_a_place_id="partnership_hub",
            endpoint_b_place_id="source_operations_site",
            link_kind="network_path",
            description="Authored physical-network adjacency, not permission to communicate.",
        ),
        "partnership_registry_network_path": SpatialLinkState(
            spatial_link_id="partnership_registry_network_path",
            endpoint_a_place_id="partnership_hub",
            endpoint_b_place_id="external_registry_site",
            link_kind="network_path",
            description="Authored physical-network adjacency to the external registry.",
        ),
    }


def _ports() -> dict[str, PortState]:
    ports: dict[str, PortState] = {}

    def add(
        port_id: str,
        owner_ref: str,
        direction: Literal["input", "output"],
        effect_type: str,
        description: str,
    ) -> None:
        ports[port_id] = PortState(
            port_id=port_id,
            owner_ref=owner_ref,
            direction=direction,
            effect_type=effect_type,
            description=description,
        )

    add("technical_source_out", "technical_pressure_source", "output", "technical_concern", "Technical concern output.")
    add("policy_source_out", "policy_pressure_source", "output", "policy_concern", "Policy concern output.")
    add("local_source_out", "local_pressure_source", "output", "local_concern", "Local concern output.")
    add("technical_delivery_in", "technical_source_delivery", "input", "technical_concern", "Technical concern delivery input.")
    add("policy_delivery_in", "policy_source_delivery", "input", "policy_concern", "Policy concern delivery input.")
    add("local_delivery_in", "local_source_delivery", "input", "local_concern", "Local concern delivery input.")
    add("scheduler_wake_in", "meeting_scheduler", "input", "scheduled_wake", "Retained scheduler wake input.")
    add("scheduler_wake_out", "meeting_clock", "output", "scheduled_wake", "Retained scheduler wake output.")
    add("meeting_notice_out", "meeting_scheduler", "output", "meeting_notice", "Due-person meeting notice output.")
    add("meeting_delivery_in", "meeting_notice_delivery", "input", "meeting_notice", "Meeting notice delivery input.")
    add("verification_request_out", "technical_validation_lead", "output", "verification_request", "Verification request action.")
    add("verification_request_in", "verification_recorder", "input", "verification_request", "Verification recorder input.")
    add("verification_response_out", "verification_recorder", "output", "verification_response", "Exact verification response output.")
    add("verification_response_in", "verification_response_delivery", "input", "verification_response", "Verification response delivery input.")
    add("issue_update_out", "sovereignty_policy_representative", "output", "issue_update", "Issue lifecycle action.")
    add("issue_update_in", "issue_recorder", "input", "issue_update", "Issue recorder input.")
    add("source_disposition_out", "local_public_health_liaison", "output", "source_disposition", "Source disposition action.")
    add("source_disposition_in", "source_disposition_recorder", "input", "source_disposition", "Source disposition recorder input.")
    for person_id in PERSON_IDS:
        add(
            f"{person_id}_commitment_out",
            person_id,
            "output",
            "commitment_update",
            "Participant commitment action.",
        )
    add("commitment_update_in", "commitment_recorder", "input", "commitment_update", "Commitment recorder input.")
    add("scope_threshold_out", "mission_coordinator", "output", "scope_threshold_proposal", "Scope and threshold proposal.")
    add("scope_threshold_in", "proposal_recorder", "input", "scope_threshold_proposal", "Proposal recorder input.")
    add("alignment_message_out", "mission_coordinator", "output", "alignment_message", "Informal alignment message.")
    add("alignment_message_in", "alignment_delivery", "input", "alignment_message", "Alignment delivery input.")
    add("withdrawal_out", "partner_representative", "output", "partner_withdrawal", "Partner withdrawal action.")
    add("withdrawal_in", "withdrawal_recorder", "input", "partner_withdrawal", "Withdrawal recorder input.")
    add("terminal_proposal_out", "mission_coordinator", "output", "terminal_proposal", "Terminal decision proposal action.")
    add("terminal_proposal_in", "terminal_decision_gate", "input", "terminal_proposal", "Exact terminal gate input.")
    add("terminal_decision_out", "terminal_decision_gate", "output", "terminal_decision", "Reviewed terminal-decision output.")
    add("external_decision_in", "external_decision_receiver", "input", "terminal_decision", "External decision receipt input.")
    return ports


def _connections() -> dict[str, ConnectionState]:
    connections = {
        "technical_source_route": _connection("technical_source_route", "technical_source_out", "technical_delivery_in"),
        "policy_source_route": _connection("policy_source_route", "policy_source_out", "policy_delivery_in"),
        "local_source_route": _connection("local_source_route", "local_source_out", "local_delivery_in"),
        "meeting_notice_route": _connection("meeting_notice_route", "meeting_notice_out", "meeting_delivery_in"),
        "scheduler_wake_route": _connection("scheduler_wake_route", "scheduler_wake_out", "scheduler_wake_in"),
        "verification_request_route": _connection("verification_request_route", "verification_request_out", "verification_request_in"),
        "verification_response_route": _connection("verification_response_route", "verification_response_out", "verification_response_in"),
        "issue_update_route": _connection("issue_update_route", "issue_update_out", "issue_update_in"),
        "source_disposition_route": _connection("source_disposition_route", "source_disposition_out", "source_disposition_in"),
        "scope_threshold_route": _connection("scope_threshold_route", "scope_threshold_out", "scope_threshold_in"),
        "alignment_message_route": _connection("alignment_message_route", "alignment_message_out", "alignment_message_in"),
        "withdrawal_route": _connection("withdrawal_route", "withdrawal_out", "withdrawal_in"),
        "terminal_proposal_route": _connection("terminal_proposal_route", "terminal_proposal_out", "terminal_proposal_in"),
        "terminal_decision_output_route": _connection("terminal_decision_output_route", "terminal_decision_out", "external_decision_in"),
    }
    for person_id in PERSON_IDS:
        route_id = f"{person_id}_commitment_route"
        connections[route_id] = _connection(
            route_id,
            f"{person_id}_commitment_out",
            "commitment_update_in",
        )
    return connections


def _connection(connection_id: str, source: str, target: str) -> ConnectionState:
    return ConnectionState(
        connection_id=connection_id,
        source_port_id=source,
        target_port_id=target,
        delay=1,
        description=f"Positive-duration reviewed route from {source} to {target}.",
    )


def _mechanisms() -> dict[str, MechanismSpec]:
    return {
        "technical_source_delivery": _mechanism("technical_source_delivery", ["technical_delivery_in"], read_representations=["technical_pressure_message"], observation_targets=["technical_validation_lead"]),
        "policy_source_delivery": _mechanism("policy_source_delivery", ["policy_delivery_in"], read_representations=["policy_pressure_message"], observation_targets=["sovereignty_policy_representative"]),
        "local_source_delivery": _mechanism("local_source_delivery", ["local_delivery_in"], read_representations=["local_pressure_message"], observation_targets=["local_public_health_liaison"]),
        "meeting_scheduler": _mechanism("meeting_scheduler", ["scheduler_wake_in"], output_ports=["meeting_notice_out"], read_facts=["meeting_schedule.schedule", "external_decision_registry.received_status"]),
        "meeting_notice_delivery": _mechanism("meeting_notice_delivery", ["meeting_delivery_in"], observation_targets=list(PERSON_IDS)),
        "verification_recorder": _mechanism("verification_recorder", ["verification_request_in"], output_ports=["verification_response_out"], write_facts=["verification_register.items"]),
        "verification_response_delivery": _mechanism("verification_response_delivery", ["verification_response_in"], observation_targets=["technical_validation_lead"]),
        "issue_recorder": _mechanism("issue_recorder", ["issue_update_in"], write_facts=["issue_register.items"]),
        "source_disposition_recorder": _mechanism("source_disposition_recorder", ["source_disposition_in"], write_facts=["source_disposition_register.items"]),
        "commitment_recorder": _mechanism("commitment_recorder", ["commitment_update_in"], write_facts=["commitment_register.items"]),
        "proposal_recorder": _mechanism("proposal_recorder", ["scope_threshold_in"], write_facts=["deployment_proposal.scope", "deployment_proposal.decision_threshold"]),
        "alignment_delivery": _mechanism("alignment_delivery", ["alignment_message_in"], observation_targets=list(PERSON_IDS)),
        "withdrawal_recorder": _mechanism("withdrawal_recorder", ["withdrawal_in"], write_facts=["decision_record.active_partner_count"]),
        "terminal_decision_gate": _mechanism(
            "terminal_decision_gate",
            ["terminal_proposal_in"],
            output_ports=["terminal_decision_out"],
            read_facts=[
                "coordination_condition.condition",
                "deployment_proposal.scope",
                "deployment_proposal.decision_threshold",
                "issue_register.items",
                "commitment_register.items",
                "decision_record.active_partner_count",
            ],
        ),
        "external_decision_receiver": _mechanism(
            "external_decision_receiver",
            ["external_decision_in"],
            write_facts=["external_decision_registry.received_status", "external_decision_registry.received_scope"],
            substrate="external_registry_system",
        ),
    }


def _mechanism(
    mechanism_id: str,
    input_ports: list[str],
    *,
    output_ports: list[str] | None = None,
    read_facts: list[str] | None = None,
    read_representations: list[str] | None = None,
    write_facts: list[str] | None = None,
    observation_targets: list[str] | None = None,
    substrate: str = "coordination_platform",
) -> MechanismSpec:
    return MechanismSpec(
        mechanism_id=mechanism_id,
        mechanism_kind="exact_transition",
        implementation_id=f"{mechanism_id}_v1",
        description=f"Reviewed exact transition for {mechanism_id}.",
        input_port_ids=input_ports,
        output_port_ids=output_ports or [],
        read_fact_ids=read_facts or [],
        read_representation_ids=read_representations or [],
        write_fact_ids=write_facts or [],
        observation_target_ids=observation_targets or [],
        substrate_refs=[substrate],
        invariant_ids=[f"{mechanism_id}_contract"],
        fidelity=FidelityNote(
            abstraction="Synthetic typed decision-workflow transition.",
            assumptions=["The reviewed state transition is stipulated for this PoC."],
            known_omissions=["Real institutions, platforms, timing, and human behavior."],
            validation_basis=["Scenario-local contracts and both-sign fixture tests."],
        ),
    )


def _information_state() -> tuple[
    dict[str, CarrierState],
    dict[str, RepresentationToken],
]:
    carriers = {
        "proposal_carrier": CarrierState(
            carrier_id="proposal_carrier",
            owner_ref="mission_coordinator",
            medium="reviewed_document",
            locator="partnership proposal repository",
        ),
        "dossier_carrier": CarrierState(
            carrier_id="dossier_carrier",
            owner_ref="technical_validation_lead",
            medium="reviewed_document",
            locator="technical validation repository",
        ),
        "technical_pressure_carrier": CarrierState(
            carrier_id="technical_pressure_carrier",
            owner_ref="technical_pressure_source",
            medium="source_message_record",
            locator="technical source workspace",
        ),
        "policy_pressure_carrier": CarrierState(
            carrier_id="policy_pressure_carrier",
            owner_ref="policy_pressure_source",
            medium="source_message_record",
            locator="policy source workspace",
        ),
        "local_pressure_carrier": CarrierState(
            carrier_id="local_pressure_carrier",
            owner_ref="local_pressure_source",
            medium="source_message_record",
            locator="local source workspace",
        ),
    }
    proposal_content = _canonical_json(
        {"document_kind": "deployment_proposal", "scope": "full"}
    ).decode()
    dossier_content = _canonical_json(
        {
            "document_kind": "technical_validation_dossier",
            "status": "initially_supportive",
        }
    ).decode()
    source_contents = {
        "technical_pressure_message": _canonical_json(
            {
                "document_kind": "source_message",
                "topic": "calibration_uncertainty",
                "claim": "Independent calibration may be insufficient.",
            }
        ).decode(),
        "policy_pressure_message": _canonical_json(
            {
                "document_kind": "source_message",
                "topic": "sovereignty_and_transparency",
                "claim": "Deployment may weaken local oversight authority.",
            }
        ).decode(),
        "local_pressure_message": _canonical_json(
            {
                "document_kind": "source_message",
                "topic": "local_safety_and_legitimacy",
                "claim": "Deployment may create locally unacceptable safety risk.",
            }
        ).decode(),
    }
    representations = {
        "deployment_proposal_copy": RepresentationToken(
            representation_id="deployment_proposal_copy",
            carrier_id="proposal_carrier",
            carrier_revision=0,
            encoding="application/vnd.cybernetic.deployment-proposal+json",
            content=proposal_content,
            content_hash=representation_digest(proposal_content),
            actual_source_ref="mission_coordinator",
        ),
        "technical_validation_dossier_copy": RepresentationToken(
            representation_id="technical_validation_dossier_copy",
            carrier_id="dossier_carrier",
            carrier_revision=0,
            encoding="application/vnd.cybernetic.validation-dossier+json",
            content=dossier_content,
            content_hash=representation_digest(dossier_content),
            actual_source_ref="technical_validation_lead",
        ),
        "technical_pressure_message": RepresentationToken(
            representation_id="technical_pressure_message",
            carrier_id="technical_pressure_carrier",
            carrier_revision=0,
            encoding="application/vnd.cybernetic.source-message+json",
            content=source_contents["technical_pressure_message"],
            content_hash=representation_digest(
                source_contents["technical_pressure_message"]
            ),
            actual_source_ref="technical_pressure_source",
        ),
        "policy_pressure_message": RepresentationToken(
            representation_id="policy_pressure_message",
            carrier_id="policy_pressure_carrier",
            carrier_revision=0,
            encoding="application/vnd.cybernetic.source-message+json",
            content=source_contents["policy_pressure_message"],
            content_hash=representation_digest(
                source_contents["policy_pressure_message"]
            ),
            actual_source_ref="policy_pressure_source",
        ),
        "local_pressure_message": RepresentationToken(
            representation_id="local_pressure_message",
            carrier_id="local_pressure_carrier",
            carrier_revision=0,
            encoding="application/vnd.cybernetic.source-message+json",
            content=source_contents["local_pressure_message"],
            content_hash=representation_digest(source_contents["local_pressure_message"]),
            actual_source_ref="local_pressure_source",
        ),
    }
    return carriers, representations


def _partnership_members(state: CausalState) -> list[str]:
    excluded = {
        *PRESSURE_SOURCE_IDS,
        *PRESSURE_SOURCE_CARRIER_IDS,
        *PRESSURE_SOURCE_REPRESENTATION_IDS,
        "pressure_source_objective",
        "technical_source_out",
        "policy_source_out",
        "local_source_out",
        EXTERNAL_RECEIVER_ID,
        "external_registry_system",
        "external_decision_receiver",
        "external_decision_in",
    }
    node_refs = (
        set(state.entities)
        | set(state.ports)
        | set(state.mechanisms)
        | set(state.carriers)
        | set(state.representations)
    )
    return sorted(node_refs - excluded)


def _run_control_options() -> RunControlOptions:
    statuses: tuple[FinalDecision, ...] = (
        "deploy_on_time",
        "delayed",
        "scope_reduced",
        "partner_disengaged",
        "no_decision_by_horizon",
    )
    return RunControlOptions(
        available_terminal_conditions=[
            ExactFactTerminalCondition(
                condition_id=f"decision_{status}",
                fact_id="external_decision_registry.received_status",
                expected_value=status,
                public_description=f"Stop when the exact decision status is {status}.",
            )
            for status in statuses
        ],
        default_terminal_condition_ids=[f"decision_{status}" for status in statuses],
        allowed_terminal_modes=["any"],
        minimum_horizon=DECISION_DEADLINE_DAY,
        default_horizon=DECISION_DEADLINE_DAY,
        maximum_horizon=DECISION_DEADLINE_DAY,
        max_causal_moments_cap=MAX_CAUSAL_MOMENTS,
        max_participant_calls_cap=MAX_PARTICIPANT_CALLS,
    )


def _fact(
    value: JsonValue,
    *,
    visibility: Literal["public", "analyst", "mechanism"] = "public",
) -> FactState:
    return FactState(value=value, visibility=visibility)


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
