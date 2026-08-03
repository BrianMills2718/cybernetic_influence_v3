"""Strict zero-execution fixtures for the Slice-21 coordination scenario.

Packet 21A0 owns only reviewed domain records and pure fixture construction.
Scheduling, exact handlers, participant policies, and model calls belong to
later packets.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import json
from typing import Annotated, Literal, TypeAlias, cast

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from cybernetic_influence.active_runtime.run_control import (
    CompletionRecord,
    ExactFactTerminalCondition,
    ResolvedRunControlPlan,
    RunControlOptions,
    resolve_run_control,
    terminal_condition_ids,
)
from cybernetic_influence.active_runtime import (
    ActionIntent,
    ActiveProposal,
    ActiveRuntimeCheckpoint,
    ActiveRuntimeConfig,
    ActiveRuntimeResult,
    ActiveRuntimeSession,
    ActiveStepResult,
    ActiveSystemBinding,
    ActiveSystemInput,
    ActiveSystemSpec,
    NativeLlmActiveSystem,
    RuntimeProgressObserver,
    ScriptedActiveSystem,
    UpdateScheduleDirective,
    bound_native_llm_implementation_id,
)
from cybernetic_influence.causal_core.engine import (
    ExactMechanismBinding,
    MechanismContext,
)
from cybernetic_influence.causal_core.models import (
    AnalyticalBoundary,
    CarrierState,
    CausalScenario,
    CausalState,
    ConnectionState,
    EntityState,
    EffectDraft,
    FactState,
    FactUpdate,
    FidelityNote,
    MechanismOutcome,
    MechanismSpec,
    ObservationDraft,
    PlacementState,
    PlaceState,
    PortState,
    RepresentationDraft,
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
MEETING_DAYS: tuple[int, ...] = (0, 1, 2, 3)
DECISION_DEADLINE_DAY = 4
MINUTES_PER_DAY = 24 * 60
MEETING_TIMES: tuple[int, ...] = tuple(day * MINUTES_PER_DAY for day in MEETING_DAYS)
DECISION_DEADLINE_TIME = DECISION_DEADLINE_DAY * MINUTES_PER_DAY
MAX_CAUSAL_MOMENTS = 28
# This is a run-length guard, not a model of social pressure and not a target.
# It must be high enough for the bounded 28-moment scenario to reach its exact
# terminal condition even when several people are activated at one moment.
MAX_PARTICIPANT_CALLS = 150
COORDINATION_LLM_TASK = "cybernetic_influence_v3_coordination_step"

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
    deadline_day: Literal[4] = 4

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
        if self.run_control_options.default_horizon != DECISION_DEADLINE_TIME:
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
        time_unit="scenario_minute",
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
            description="Four daily decision meetings and the day-4 fallback deadline.",
            attributes={
                "schedule": _fact(schedule.model_dump(mode="json")),
                "last_wake_day": _fact(None),
            },
        ),
        "decision_goal": EntityState(
            entity_id="decision_goal",
            entity_kind="goal_record",
            description="Reach a valid terminal deployment decision by day 4.",
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
    position_memories = {
        "mission_coordinator": [
            "The reviewed process designates the fourth scheduled meeting for a final proposal.",
            "The registry accepts full deployment only when all five recorded commitments support full scope and no blocking issue remains; it accepts reduced scope when commitments support full or reduced scope and no blocking issue remains.",
        ],
        "technical_validation_lead": [
            "Independent calibration is the available way to test material calibration uncertainty.",
            "A supportive result supports full scope; bounded support supports reduced scope; insufficient evidence warrants deferral.",
        ],
        "sovereignty_policy_representative": [
            "Material oversight or sovereignty concerns are retained as issue records until evidence addresses them.",
            "A blocking open or reopened issue prevents a final deployment decision.",
        ],
        "local_public_health_liaison": [
            "Local safety information should be recorded with how it affected the liaison's judgment.",
        ],
        "partner_representative": [
            "The represented partner may support full scope, support reduced scope, defer, or withdraw as evidence changes.",
        ],
    }
    return PersonAssumptions(
        position=positions[person_id],
        dispositions=["conscientious", "fallible", "responsive to credible evidence"],
        memories=[
            "The initial dossier supports deployment subject to review.",
            *position_memories[person_id],
        ],
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
    add(
        "meeting_snapshot_out",
        "meeting_scheduler",
        "output",
        "meeting_snapshot",
        "Shared reviewed meeting-state snapshot output.",
    )
    for person_id in PERSON_IDS:
        add(
            f"meeting_snapshot_{person_id}_in",
            f"meeting_snapshot_delivery_{person_id}",
            "input",
            "meeting_snapshot",
            f"Meeting-state snapshot delivery input for {person_id}.",
        )
    add("deadline_transition_out", "meeting_clock", "output", "deadline_transition", "Exact day-4 fallback deadline trigger.")
    add("verification_request_out", "technical_validation_lead", "output", "verification_request", "Request the available independent calibration review using the retained technical dossier.")
    add("verification_request_in", "verification_recorder", "input", "verification_request", "Verification recorder input.")
    add("verification_response_out", "verification_recorder", "output", "verification_response", "Exact verification response output.")
    for person_id in PERSON_IDS:
        add(
            f"verification_response_{person_id}_in",
            f"verification_response_delivery_{person_id}",
            "input",
            "verification_response",
            f"Verification response delivery input for {person_id}.",
        )
    add("issue_update_out", "sovereignty_policy_representative", "output", "issue_update", "Open, resolve, or reopen one retained oversight issue with its evidence references.")
    add("issue_update_in", "issue_recorder", "input", "issue_update", "Issue recorder input.")
    add("source_disposition_out", "local_public_health_liaison", "output", "source_disposition", "Record how one concrete source affected the liaison's judgment and cite the delivered evidence.")
    add("source_disposition_in", "source_disposition_recorder", "input", "source_disposition", "Source disposition recorder input.")
    for person_id in PERSON_IDS:
        add(
            f"{person_id}_commitment_out",
            person_id,
            "output",
            "commitment_update",
            "Record this person's current commitment as support full, support reduced, defer, or withdraw.",
        )
    add("commitment_update_in", "commitment_recorder", "input", "commitment_update", "Commitment recorder input.")
    add("scope_threshold_out", "mission_coordinator", "output", "scope_threshold_proposal", "Record the reviewed deployment scope and its decision threshold.")
    add("scope_threshold_in", "proposal_recorder", "input", "scope_threshold_proposal", "Proposal recorder input.")
    add("alignment_message_out", "mission_coordinator", "output", "alignment_message", "Informal alignment message.")
    for person_id in PERSON_IDS[1:]:
        add(
            f"alignment_message_{person_id}_in",
            f"alignment_delivery_{person_id}",
            "input",
            "alignment_message",
            f"Alignment delivery input for {person_id}.",
        )
    add("withdrawal_out", "partner_representative", "output", "partner_withdrawal", "Partner withdrawal action.")
    add("withdrawal_in", "withdrawal_recorder", "input", "partner_withdrawal", "Withdrawal recorder input.")
    add("terminal_proposal_out", "mission_coordinator", "output", "terminal_proposal", "Submit a reviewed final proposal to the exact decision gate with its evidence, acknowledged issues, and active partners.")
    add("terminal_proposal_in", "terminal_decision_gate", "input", "terminal_proposal", "Exact terminal gate input.")
    add("deadline_transition_in", "terminal_decision_gate", "input", "deadline_transition", "Exact deadline transition input.")
    add("terminal_decision_out", "terminal_decision_gate", "output", "terminal_decision", "Reviewed terminal-decision output.")
    add("external_decision_in", "external_decision_receiver", "input", "terminal_decision", "External decision receipt input.")
    return ports


def _connections() -> dict[str, ConnectionState]:
    connections = {
        "technical_source_route": _connection("technical_source_route", "technical_source_out", "technical_delivery_in"),
        "policy_source_route": _connection("policy_source_route", "policy_source_out", "policy_delivery_in"),
        "local_source_route": _connection("local_source_route", "local_source_out", "local_delivery_in"),
        "scheduler_wake_route": _connection("scheduler_wake_route", "scheduler_wake_out", "scheduler_wake_in"),
        "deadline_transition_route": _connection("deadline_transition_route", "deadline_transition_out", "deadline_transition_in"),
        "verification_request_route": _connection("verification_request_route", "verification_request_out", "verification_request_in"),
        "issue_update_route": _connection("issue_update_route", "issue_update_out", "issue_update_in"),
        "source_disposition_route": _connection("source_disposition_route", "source_disposition_out", "source_disposition_in"),
        "scope_threshold_route": _connection("scope_threshold_route", "scope_threshold_out", "scope_threshold_in"),
        "withdrawal_route": _connection("withdrawal_route", "withdrawal_out", "withdrawal_in"),
        "terminal_proposal_route": _connection("terminal_proposal_route", "terminal_proposal_out", "terminal_proposal_in"),
        "terminal_decision_output_route": _connection("terminal_decision_output_route", "terminal_decision_out", "external_decision_in"),
    }
    for person_id in PERSON_IDS:
        route_id = f"meeting_snapshot_{person_id}_route"
        connections[route_id] = _connection(
            route_id,
            "meeting_snapshot_out",
            f"meeting_snapshot_{person_id}_in",
        )
    for person_id in PERSON_IDS:
        route_id = f"{person_id}_commitment_route"
        connections[route_id] = _connection(
            route_id,
            f"{person_id}_commitment_out",
            "commitment_update_in",
        )
        verification_route_id = f"verification_response_{person_id}_route"
        connections[verification_route_id] = _connection(
            verification_route_id,
            "verification_response_out",
            f"verification_response_{person_id}_in",
        )
        if person_id != "mission_coordinator":
            alignment_route_id = f"alignment_message_{person_id}_route"
            connections[alignment_route_id] = _connection(
                alignment_route_id,
                "alignment_message_out",
                f"alignment_message_{person_id}_in",
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
        "meeting_scheduler": _mechanism(
            "meeting_scheduler",
            ["scheduler_wake_in"],
            read_facts=[
                "meeting_schedule.schedule",
                "external_decision_registry.received_status",
                "deployment_proposal.scope",
                "deployment_proposal.decision_threshold",
                "issue_register.items",
                "commitment_register.items",
                "verification_register.items",
                "decision_record.active_partner_count",
            ],
            write_facts=["meeting_schedule.last_wake_day"],
            output_ports=["meeting_snapshot_out"],
        ),
        "verification_recorder": _mechanism("verification_recorder", ["verification_request_in"], output_ports=["verification_response_out"], read_facts=["coordination_condition.condition", "verification_register.items"], write_facts=["verification_register.items"], write_carriers=["verification_response_carrier"]),
        "issue_recorder": _mechanism("issue_recorder", ["issue_update_in"], read_facts=["issue_register.items"], write_facts=["issue_register.items"]),
        "source_disposition_recorder": _mechanism("source_disposition_recorder", ["source_disposition_in"], read_facts=["source_disposition_register.items"], write_facts=["source_disposition_register.items"]),
        "commitment_recorder": _mechanism("commitment_recorder", ["commitment_update_in"], read_facts=["commitment_register.items"], write_facts=["commitment_register.items"]),
        "proposal_recorder": _mechanism("proposal_recorder", ["scope_threshold_in"], read_facts=["deployment_proposal.scope", "deployment_proposal.decision_threshold"], write_facts=["deployment_proposal.scope", "deployment_proposal.decision_threshold"]),
        "withdrawal_recorder": _mechanism("withdrawal_recorder", ["withdrawal_in"], read_facts=["decision_record.active_partner_count"], write_facts=["decision_record.active_partner_count"]),
        "terminal_decision_gate": _mechanism(
            "terminal_decision_gate",
            ["terminal_proposal_in", "deadline_transition_in"],
            output_ports=["terminal_decision_out"],
            read_facts=[
                "coordination_condition.condition",
                "deployment_proposal.scope",
                "deployment_proposal.decision_threshold",
                "issue_register.items",
                "commitment_register.items",
                "decision_record.active_partner_count",
                "external_decision_registry.received_status",
                "meeting_schedule.last_wake_day",
            ],
            write_facts=[
                "decision_record.gate_status",
                "decision_record.proposed_status",
                "decision_record.proposed_scope",
            ],
            write_carriers=["terminal_decision_carrier"],
        ),
        "external_decision_receiver": _mechanism(
            "external_decision_receiver",
            ["external_decision_in"],
            read_facts=["external_decision_registry.received_status"],
            write_facts=["external_decision_registry.received_status", "external_decision_registry.received_scope"],
            substrate="external_registry_system",
        ),
    } | {
        f"meeting_snapshot_delivery_{person_id}": _mechanism(
            f"meeting_snapshot_delivery_{person_id}",
            [f"meeting_snapshot_{person_id}_in"],
            observation_targets=[person_id],
        )
        for person_id in PERSON_IDS
    } | {
        f"verification_response_delivery_{person_id}": _mechanism(
            f"verification_response_delivery_{person_id}",
            [f"verification_response_{person_id}_in"],
            observation_targets=[person_id],
        )
        for person_id in PERSON_IDS
    } | {
        f"alignment_delivery_{person_id}": _mechanism(
            f"alignment_delivery_{person_id}",
            [f"alignment_message_{person_id}_in"],
            observation_targets=[person_id],
        )
        for person_id in PERSON_IDS[1:]
    }


def _mechanism(
    mechanism_id: str,
    input_ports: list[str],
    *,
    output_ports: list[str] | None = None,
    read_facts: list[str] | None = None,
    read_representations: list[str] | None = None,
    write_facts: list[str] | None = None,
    write_carriers: list[str] | None = None,
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
        write_carrier_ids=write_carriers or [],
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
        "verification_response_carrier": CarrierState(
            carrier_id="verification_response_carrier",
            owner_ref="verification_recorder",
            medium="verification_response_record",
            locator="partnership verification register",
        ),
        "terminal_decision_carrier": CarrierState(
            carrier_id="terminal_decision_carrier",
            owner_ref="terminal_decision_gate",
            medium="terminal_decision_record",
            locator="partnership decision gateway",
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
        minimum_horizon=DECISION_DEADLINE_TIME,
        default_horizon=DECISION_DEADLINE_TIME,
        maximum_horizon=DECISION_DEADLINE_TIME,
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


# Packet 21A1: scripted recurring execution over the contracts above.


class VerificationRequestAction(_StrictModel):
    verification_id: Literal["independent_calibration"] = "independent_calibration"
    topic: Literal["independent_calibration"] = "independent_calibration"
    requested_by: Literal["technical_validation_lead"] = (
        "technical_validation_lead"
    )


class VerificationResponseRecord(_StrictModel):
    document_kind: Literal["verification_response"] = "verification_response"
    verification_id: Literal["independent_calibration"] = "independent_calibration"
    result: Literal["supportive", "insufficient", "bounded_support"]
    explanation: str = Field(min_length=1)


class IssueUpdateAction(_StrictModel):
    issue_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    topic: str = Field(min_length=1)
    lifecycle: IssueLifecycle
    blocking: bool
    opened_by: PersonId
    evidence_refs: list[str] = Field(default_factory=list)


class SourceDispositionAction(_StrictModel):
    person_id: PersonId
    source_id: PressureSourceId
    disposition: SourceDisposition
    evidence_refs: list[str] = Field(default_factory=list)


class CommitmentAction(_StrictModel):
    person_id: PersonId
    commitment: Commitment


class ScopeThresholdAction(_StrictModel):
    proposed_by: Literal["mission_coordinator"] = "mission_coordinator"
    scope: DecisionScope
    decision_threshold: Literal[
        "reviewed_evidence_and_partner_support",
        "bounded_evidence_and_partner_support",
    ]


class AlignmentMessageAction(_StrictModel):
    sender_id: PersonId
    content: str = Field(min_length=1)


class PartnerWithdrawalAction(_StrictModel):
    person_id: Literal["partner_representative"] = "partner_representative"


class SchedulerWakeAction(_StrictModel):
    meeting_index: int = Field(ge=0, le=3)
    modeled_day: int = Field(ge=0, le=3)


class DeadlineTransitionAction(_StrictModel):
    modeled_day: Literal[4] = 4


class TerminalDecisionRecord(_StrictModel):
    document_kind: Literal["terminal_decision"] = "terminal_decision"
    status: FinalDecision
    scope: DecisionScope
    source: Literal["reviewed_proposal", "deadline"]


class _CoordinationActionBase(_StrictModel):
    representation_id: str | None = Field(
        default=None,
        description="One retained representation used by this action, or null.",
    )
    public_summary: str = Field(
        min_length=1,
        description="Concise public description of the attempted action.",
    )


class LlmCommitmentPayload(_StrictModel):
    commitment: Commitment = Field(
        description="This person's current reviewed commitment."
    )


class LlmScopeThresholdPayload(_StrictModel):
    scope: DecisionScope = Field(description="The proposed deployment scope.")
    decision_threshold: Literal[
        "reviewed_evidence_and_partner_support",
        "bounded_evidence_and_partner_support",
    ] = Field(description="The exact reviewed threshold attached to the scope.")


class LlmAlignmentPayload(_StrictModel):
    content: str = Field(
        min_length=1,
        description="The alignment message to send to the other participants.",
    )


class LlmTerminalProposalPayload(_StrictModel):
    requested_status: FinalDecision = Field(
        description="The requested terminal decision."
    )
    requested_scope: DecisionScope = Field(
        description="The requested terminal scope."
    )
    evidence_refs: list[str] = Field(
        description="Delivered evidence references supporting the proposal."
    )
    acknowledged_issue_ids: list[str] = Field(
        description="Retained issue records explicitly acknowledged."
    )
    active_partner_ids: list[PersonId] = Field(
        description="Partners believed to remain active in the reviewed proposal."
    )


class LlmVerificationRequestPayload(_StrictModel):
    request: Literal["independent_calibration"] = Field(
        description="The configured independent review being requested."
    )


class LlmIssueUpdatePayload(_StrictModel):
    issue_id: str = Field(
        pattern=r"^[a-z][a-z0-9_]*$",
        description="Stable domain name for the reviewed issue.",
    )
    topic: str = Field(min_length=1, description="The issue being reviewed.")
    lifecycle: IssueLifecycle = Field(description="The issue's reviewed lifecycle.")
    blocking: bool = Field(description="Whether this issue currently blocks a decision.")
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="Delivered evidence references relevant to the update.",
    )


class LlmSourceDispositionPayload(_StrictModel):
    source_id: PressureSourceId = Field(
        description="The delivered pressure source being assessed."
    )
    disposition: SourceDisposition = Field(
        description="How that source affected this person's judgment."
    )
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="Delivered evidence references supporting the disposition.",
    )


class LlmWithdrawalPayload(_StrictModel):
    decision: Literal["withdraw"] = Field(
        description="The represented partner's withdrawal decision."
    )


class CommitmentDecisionAction(_CoordinationActionBase):
    output_port_id: Literal[
        "mission_coordinator_commitment_out",
        "technical_validation_lead_commitment_out",
        "sovereignty_policy_representative_commitment_out",
        "local_public_health_liaison_commitment_out",
        "partner_representative_commitment_out",
    ]
    payload: LlmCommitmentPayload


class MissionCoordinatorCommitmentDecisionAction(_CoordinationActionBase):
    output_port_id: Literal["mission_coordinator_commitment_out"]
    payload: LlmCommitmentPayload


class TechnicalLeadCommitmentDecisionAction(_CoordinationActionBase):
    output_port_id: Literal["technical_validation_lead_commitment_out"]
    payload: LlmCommitmentPayload


class PolicyRepresentativeCommitmentDecisionAction(_CoordinationActionBase):
    output_port_id: Literal[
        "sovereignty_policy_representative_commitment_out"
    ]
    payload: LlmCommitmentPayload


class LocalLiaisonCommitmentDecisionAction(_CoordinationActionBase):
    output_port_id: Literal["local_public_health_liaison_commitment_out"]
    payload: LlmCommitmentPayload


class PartnerRepresentativeCommitmentDecisionAction(_CoordinationActionBase):
    output_port_id: Literal["partner_representative_commitment_out"]
    payload: LlmCommitmentPayload


class ScopeThresholdDecisionAction(_CoordinationActionBase):
    output_port_id: Literal["scope_threshold_out"]
    payload: LlmScopeThresholdPayload


class AlignmentDecisionAction(_CoordinationActionBase):
    output_port_id: Literal["alignment_message_out"]
    payload: LlmAlignmentPayload


class TerminalProposalDecisionAction(_CoordinationActionBase):
    output_port_id: Literal["terminal_proposal_out"]
    payload: LlmTerminalProposalPayload


class VerificationRequestDecisionAction(_CoordinationActionBase):
    output_port_id: Literal["verification_request_out"]
    representation_id: Literal["technical_validation_dossier_copy"]
    payload: LlmVerificationRequestPayload


class IssueUpdateDecisionAction(_CoordinationActionBase):
    output_port_id: Literal["issue_update_out"]
    payload: LlmIssueUpdatePayload


class SourceDispositionDecisionAction(_CoordinationActionBase):
    output_port_id: Literal["source_disposition_out"]
    payload: LlmSourceDispositionPayload


class WithdrawalDecisionAction(_CoordinationActionBase):
    output_port_id: Literal["withdrawal_out"]
    payload: LlmWithdrawalPayload


CoordinationDecisionAction: TypeAlias = Annotated[
    CommitmentDecisionAction
    | ScopeThresholdDecisionAction
    | AlignmentDecisionAction
    | TerminalProposalDecisionAction
    | VerificationRequestDecisionAction
    | IssueUpdateDecisionAction
    | SourceDispositionDecisionAction
    | WithdrawalDecisionAction,
    Field(discriminator="output_port_id"),
]


class _CoordinationDecisionBase(_StrictModel):
    orientation: str = Field(
        min_length=1,
        description="Concise read of the bounded situation and rationale.",
    )
    memory_update: str = Field(
        description="What this person wants to retain after a successful step."
    )
    silence_reason: str | None = Field(
        default=None,
        description="Required when actions is empty and null otherwise.",
    )

    @model_validator(mode="after")
    def validate_silence(self) -> "_CoordinationDecisionBase":
        actions = getattr(self, "actions", [])
        if not actions and not (
            self.silence_reason and self.silence_reason.strip()
        ):
            raise ValueError("empty actions require a nonempty silence reason")
        if actions and self.silence_reason is not None:
            raise ValueError("actions require a null silence reason")
        return self


class CoordinationLlmDecision(_CoordinationDecisionBase):
    """Complete scenario action contract used for structural inspection."""

    actions: list[CoordinationDecisionAction] = Field(
        description="Zero or more actions through this person's owned interfaces."
    )


MissionCoordinatorDecisionAction: TypeAlias = Annotated[
    MissionCoordinatorCommitmentDecisionAction
    | ScopeThresholdDecisionAction
    | AlignmentDecisionAction
    | TerminalProposalDecisionAction,
    Field(discriminator="output_port_id"),
]
TechnicalLeadDecisionAction: TypeAlias = Annotated[
    TechnicalLeadCommitmentDecisionAction | VerificationRequestDecisionAction,
    Field(discriminator="output_port_id"),
]
PolicyRepresentativeDecisionAction: TypeAlias = Annotated[
    PolicyRepresentativeCommitmentDecisionAction | IssueUpdateDecisionAction,
    Field(discriminator="output_port_id"),
]
LocalLiaisonDecisionAction: TypeAlias = Annotated[
    LocalLiaisonCommitmentDecisionAction | SourceDispositionDecisionAction,
    Field(discriminator="output_port_id"),
]
PartnerRepresentativeDecisionAction: TypeAlias = Annotated[
    PartnerRepresentativeCommitmentDecisionAction | WithdrawalDecisionAction,
    Field(discriminator="output_port_id"),
]


class MissionCoordinatorLlmDecision(_CoordinationDecisionBase):
    actions: list[MissionCoordinatorDecisionAction] = Field(
        description="Zero or more actions through the coordinator's owned interfaces."
    )


class TechnicalLeadLlmDecision(_CoordinationDecisionBase):
    actions: list[TechnicalLeadDecisionAction] = Field(
        description="Zero or more actions through the technical lead's owned interfaces."
    )


class PolicyRepresentativeLlmDecision(_CoordinationDecisionBase):
    actions: list[PolicyRepresentativeDecisionAction] = Field(
        description="Zero or more actions through the policy representative's interfaces."
    )


class LocalLiaisonLlmDecision(_CoordinationDecisionBase):
    actions: list[LocalLiaisonDecisionAction] = Field(
        description="Zero or more actions through the local liaison's owned interfaces."
    )


class PartnerRepresentativeLlmDecision(_CoordinationDecisionBase):
    actions: list[PartnerRepresentativeDecisionAction] = Field(
        description="Zero or more actions through the partner's owned interfaces."
    )


COORDINATION_PERSON_DECISION_MODELS: Mapping[PersonId, type[BaseModel]] = {
    "mission_coordinator": MissionCoordinatorLlmDecision,
    "technical_validation_lead": TechnicalLeadLlmDecision,
    "sovereignty_policy_representative": PolicyRepresentativeLlmDecision,
    "local_public_health_liaison": LocalLiaisonLlmDecision,
    "partner_representative": PartnerRepresentativeLlmDecision,
}


def _coordination_persona(
    fixture: CoordinationDecisionFixture,
    person_id: PersonId,
) -> str:
    """Render only reviewed descriptive person context, never a procedure."""

    raw = fixture.scenario.initial_state.entities[person_id].attributes[
        "assumptions"
    ].value
    assumptions = PersonAssumptions.model_validate(raw)
    labels = (
        ("Position", assumptions.position),
        ("Dispositions", assumptions.dispositions),
        ("Memories", assumptions.memories),
        ("Values", assumptions.values),
        ("Goals", assumptions.goals),
        ("Beliefs", assumptions.beliefs),
        ("Decision tendencies", assumptions.decision_tendencies),
        ("Perceived social conditions", assumptions.perceived_social_conditions),
        ("Current state", assumptions.current_state),
        ("Capabilities", assumptions.capabilities),
        ("Limitations", assumptions.limitations),
    )
    return "\n".join(
        f"{label}: {value if isinstance(value, str) else '; '.join(value)}"
        for label, value in labels
    )


@dataclass(frozen=True)
class CoordinationRuntimeFixture:
    """Validated 21A0 contract plus scenario-local runtime registries."""

    contract: CoordinationDecisionFixture
    exact_bindings: Mapping[str, ExactMechanismBinding]
    active_specs: tuple[ActiveSystemSpec, ...]

    @property
    def scenario(self) -> CausalScenario:
        return self.contract.scenario


class CoordinationRuntimePaused(RuntimeError):
    """Expose one validated causal-boundary checkpoint for later continuation."""

    def __init__(self, checkpoint: ActiveRuntimeCheckpoint) -> None:
        super().__init__("coordination run paused at a causal boundary")
        self.checkpoint = checkpoint


def coordination_runtime_fixture(
    contract: CoordinationDecisionFixture,
    *,
    model: str | None = None,
    reasoning_effort: str | None = None,
) -> CoordinationRuntimeFixture:
    """Reopen the committed fixture before adding replaceable implementations."""

    reopened = CoordinationDecisionFixture.model_validate(
        contract.model_dump(mode="json")
    )
    return CoordinationRuntimeFixture(
        contract=reopened,
        exact_bindings=_coordination_exact_bindings(),
        active_specs=_coordination_active_specs(
            reopened,
            model=model,
            reasoning_effort=reasoning_effort,
        ),
    )


def coordination_runtime_config(
    *,
    per_call_budget: float = 0.01,
    per_run_budget: float = 0.01,
) -> ActiveRuntimeConfig:
    """Return the bounded provider envelope for one coordination run."""

    return ActiveRuntimeConfig(
        per_call_budget=per_call_budget,
        per_run_budget=per_run_budget,
        max_actions_per_system=4,
        max_observations_per_system=32,
        max_private_state_bytes=32_768,
    )


def coordination_run_control_plan(
    fixture: CoordinationRuntimeFixture,
) -> ResolvedRunControlPlan:
    """Resolve only the fixture's reviewed terminal facts and safety bounds."""

    return resolve_run_control(fixture.contract.run_control_options, None)


def coordination_scripted_bindings(
    fixture: CoordinationRuntimeFixture,
) -> dict[str, ActiveSystemBinding]:
    """Bind every concrete person/process to one zero-call scripted controller."""

    controllers: dict[str, Callable[[ActiveSystemInput], ActiveStepResult]] = {
        "mission_coordinator": _scripted_mission_coordinator,
        "technical_validation_lead": _scripted_technical_lead,
        "sovereignty_policy_representative": _scripted_policy_representative,
        "local_public_health_liaison": _scripted_local_liaison,
        "partner_representative": _scripted_partner_representative,
        "technical_pressure_source": _scripted_pressure_source,
        "policy_pressure_source": _scripted_pressure_source,
        "local_pressure_source": _scripted_pressure_source,
        "meeting_clock": _scripted_meeting_clock,
    }
    return {
        spec.active_system_id: ActiveSystemBinding(
            spec.implementation_id,
            ScriptedActiveSystem(
                implementation_id=spec.implementation_id,
                controller=controllers[spec.active_system_id],
            ),
        )
        for spec in fixture.active_specs
    }


def _normalized_coordination_payload(
    person_id: PersonId,
    output_port_id: str,
    payload: Mapping[str, JsonValue],
) -> dict[str, JsonValue]:
    """Attach simulator-owned identity fields after the LLM schema parses."""

    normalized = dict(payload)
    if output_port_id.endswith("_commitment_out"):
        normalized["person_id"] = person_id
    elif output_port_id == "scope_threshold_out":
        normalized["proposed_by"] = person_id
    elif output_port_id == "alignment_message_out":
        normalized["sender_id"] = person_id
    elif output_port_id == "terminal_proposal_out":
        normalized["proposal_id"] = "reviewed_terminal_proposal"
        normalized["proposed_by"] = person_id
    elif output_port_id == "verification_request_out":
        normalized = {
            "verification_id": "independent_calibration",
            "topic": "independent_calibration",
            "requested_by": person_id,
        }
    elif output_port_id == "issue_update_out":
        normalized["opened_by"] = person_id
    elif output_port_id == "source_disposition_out":
        normalized["person_id"] = person_id
    elif output_port_id == "withdrawal_out":
        normalized = {"person_id": person_id}
    return normalized


@dataclass(frozen=True)
class CoordinationNativePerson:
    """Scenario-local identity normalization around generic LLM cognition."""

    active_system_id: PersonId
    inner: NativeLlmActiveSystem
    implementation_id: str
    provider_bound: bool = True

    def step(self, active_input: ActiveSystemInput) -> ActiveStepResult:
        if active_input.active_system_id != self.active_system_id:
            raise ValueError("coordination native binding received another person")
        result = ActiveStepResult.model_validate(self.inner.step(active_input))
        actions = [
            action.model_copy(
                update={
                    "payload": _normalized_coordination_payload(
                        self.active_system_id,
                        action.output_port_id,
                        action.payload,
                    )
                }
            )
            for action in result.proposal.actions
        ]
        return result.model_copy(
            update={
                "proposal": result.proposal.model_copy(
                    update={"actions": actions}
                )
            }
        )


def coordination_native_bindings(
    fixture: CoordinationRuntimeFixture,
    *,
    trace_id_prefix: str,
    model: str,
    reasoning_effort: str | None,
) -> dict[str, ActiveSystemBinding]:
    """Bind only concrete people to LLM cognition; keep processes exact/scripted."""

    scripted = coordination_scripted_bindings(fixture)
    for person_id in PERSON_IDS:
        persona = _coordination_persona(fixture.contract, person_id)
        policy = NativeLlmActiveSystem.from_bound_configuration(
            implementation_family_id=f"native_coordination_{person_id}_v1",
            persona=persona,
            model=model,
            task=COORDINATION_LLM_TASK,
            trace_id_prefix=trace_id_prefix,
            reasoning_effort=reasoning_effort,
            decision_model=COORDINATION_PERSON_DECISION_MODELS[person_id],
        )
        normalized = CoordinationNativePerson(
            active_system_id=person_id,
            inner=policy,
            implementation_id=policy.implementation_id,
        )
        scripted[person_id] = ActiveSystemBinding(
            normalized.implementation_id,
            normalized,
        )
    return scripted


def run_coordination(
    fixture: CoordinationRuntimeFixture,
    bindings: Mapping[str, ActiveSystemBinding],
    *,
    run_id: str,
    runtime_config: ActiveRuntimeConfig | None = None,
    checkpoint: ActiveRuntimeCheckpoint | None = None,
    checkpoint_observer: Callable[[ActiveRuntimeCheckpoint], None] | None = None,
    pause_requested: Callable[[], bool] | None = None,
    stop_requested: Callable[[], bool] | None = None,
    progress_observer: RuntimeProgressObserver | None = None,
) -> ActiveRuntimeResult:
    """Run scripted or live people through the same exact coordination world."""

    session = (
        ActiveRuntimeSession.restore(
            fixture.scenario,
            fixture.exact_bindings,
            bindings,
            checkpoint,
            progress_observer=progress_observer,
        )
        if checkpoint is not None
        else ActiveRuntimeSession(
            fixture.scenario,
            fixture.exact_bindings,
            fixture.active_specs,
            bindings,
            run_id=run_id,
            config=runtime_config or coordination_runtime_config(),
            progress_observer=progress_observer,
        )
    )
    run_control = coordination_run_control_plan(fixture)

    def completion(reason: Literal[
        "terminal_condition_met",
        "modeled_time_horizon",
        "quiescent_before_terminal",
        "operator_stopped",
        "safety_limit",
    ], condition_ids: list[str] | None = None) -> CompletionRecord:
        matched = condition_ids or []
        evidence = _terminal_evidence_event_ids(session, run_control, matched)
        terminal_summaries = {
            "decision_deploy_on_time": "The reviewed full deployment decision was accepted and recorded.",
            "decision_delayed": "The delayed deployment decision was accepted and recorded.",
            "decision_scope_reduced": "The reviewed reduced-scope decision was accepted and recorded.",
            "decision_partner_disengaged": "The partner-disengagement outcome was accepted and recorded.",
            "decision_no_decision_by_horizon": "The decision deadline was recorded without an approved deployment.",
        }
        summaries = {
            "terminal_condition_met": next(
                (
                    terminal_summaries[condition_id]
                    for condition_id in matched
                    if condition_id in terminal_summaries
                ),
                "The team's exact terminal outcome was accepted and recorded.",
            ),
            "modeled_time_horizon": "The modeled deadline passed without its required exact transition.",
            "quiescent_before_terminal": "No modeled work remained before a terminal decision was retained.",
            "operator_stopped": "The operator stopped at a causal boundary.",
            "safety_limit": "A configured safety bound ended the run.",
        }
        return CompletionRecord(
            reason=reason,
            condition_ids=matched,
            causal_time=len(session.attempts),
            logical_time=session.core_state.logical_time,
            public_summary=summaries[reason],
            evidence_event_ids=evidence,
        )

    while True:
        matched = terminal_condition_ids(run_control, session.core_state)
        if matched:
            session.drain_pending_exact_work()
            return session.complete(
                completion=completion("terminal_condition_met", matched)
            )
        if stop_requested is not None and stop_requested():
            return session.complete(
                completion=completion("operator_stopped"),
                discard_pending_effects=True,
            )
        if len(session.attempts) >= run_control.max_causal_moments:
            return session.complete(
                completion=completion("safety_limit"),
                discard_pending_effects=True,
            )
        due = session.next_due_activation()
        matched = terminal_condition_ids(run_control, session.core_state)
        if matched:
            session.drain_pending_exact_work()
            return session.complete(
                completion=completion("terminal_condition_met", matched)
            )
        if due is None:
            return session.complete(
                completion=completion("quiescent_before_terminal")
            )
        if due.logical_time > DECISION_DEADLINE_TIME:
            return session.complete(
                completion=completion("modeled_time_horizon"),
                discard_pending_effects=True,
            )
        observed_calls = sum(
            len(participant.call_evidence)
            for attempt in session.attempts
            for participant in attempt.participants
        )
        due_provider_calls = sum(
            bindings[active_system_id].implementation.provider_bound
            for active_system_id in due.active_system_ids
        )
        if observed_calls + due_provider_calls > run_control.max_participant_calls:
            return session.complete(
                completion=completion("safety_limit"),
                discard_pending_effects=True,
            )
        session.activate(
            due.active_system_ids,
            logical_time=due.logical_time,
            activation_causes=due.causes,
        )
        current = session.checkpoint()
        if checkpoint_observer is not None:
            checkpoint_observer(current)
        if pause_requested is not None and pause_requested():
            raise CoordinationRuntimePaused(current)


def run_scripted_coordination(
    fixture: CoordinationRuntimeFixture,
    *,
    run_id: str,
    checkpoint: ActiveRuntimeCheckpoint | None = None,
    checkpoint_observer: Callable[[ActiveRuntimeCheckpoint], None] | None = None,
    pause_requested: Callable[[], bool] | None = None,
    progress_observer: RuntimeProgressObserver | None = None,
) -> ActiveRuntimeResult:
    """Run the recurring scripted vertical through its exact terminal fact."""

    return run_coordination(
        fixture,
        coordination_scripted_bindings(fixture),
        run_id=run_id,
        checkpoint=checkpoint,
        checkpoint_observer=checkpoint_observer,
        pause_requested=pause_requested,
        progress_observer=progress_observer,
    )


def _coordination_active_specs(
    fixture: CoordinationDecisionFixture,
    *,
    model: str | None = None,
    reasoning_effort: str | None = None,
) -> tuple[ActiveSystemSpec, ...]:
    condition = fixture.condition
    assumptions = {
        person_id: fixture.scenario.initial_state.entities[person_id].attributes[
            "assumptions"
        ].value
        for person_id in PERSON_IDS
    }

    def person_spec(
        person_id: PersonId,
        *,
        observation_ports: list[str],
        output_ports: list[str],
        initial_representations: list[str] | None = None,
    ) -> ActiveSystemSpec:
        persona = _coordination_persona(fixture, person_id)
        implementation_id = (
            bound_native_llm_implementation_id(
                implementation_family_id=f"native_coordination_{person_id}_v1",
                persona=persona,
                model=model,
                task=COORDINATION_LLM_TASK,
                reasoning_effort=reasoning_effort,
                decision_model=COORDINATION_PERSON_DECISION_MODELS[person_id],
            )
            if model is not None
            else f"scripted_coordination_{person_id}_v1"
        )
        return ActiveSystemSpec(
            active_system_id=person_id,
            entity_id=person_id,
            implementation_id=implementation_id,
            description=(
                f"Live LLM cognition for {person_id}."
                if model is not None
                else f"Zero-call reference behavior for {person_id}."
            ),
            observation_port_ids=observation_ports,
            output_port_ids=output_ports,
            initial_representation_ids=initial_representations or [],
            initial_private_state=(
                {"memory": []}
                if model is not None
                else {
                    "assumptions": assumptions[person_id],
                    "meetings_completed": 0,
                    "verification_result": "unknown",
                    "commitment": "support_full",
                    "opened_issue_ids": [],
                }
            ),
            initial_next_update_at=None,
        )

    def shared_observation_ports(person_id: PersonId) -> list[str]:
        ports = [
            f"meeting_snapshot_{person_id}_in",
            f"verification_response_{person_id}_in",
        ]
        if person_id != "mission_coordinator":
            ports.append(f"alignment_message_{person_id}_in")
        return ports

    people = (
        person_spec(
            "mission_coordinator",
            observation_ports=shared_observation_ports("mission_coordinator"),
            output_ports=[
                "mission_coordinator_commitment_out",
                "scope_threshold_out",
                "alignment_message_out",
                "terminal_proposal_out",
            ],
            initial_representations=["deployment_proposal_copy"],
        ),
        person_spec(
            "technical_validation_lead",
            observation_ports=[
                "technical_delivery_in",
                *shared_observation_ports("technical_validation_lead"),
            ],
            output_ports=[
                "technical_validation_lead_commitment_out",
                "verification_request_out",
            ],
            initial_representations=["technical_validation_dossier_copy"],
        ),
        person_spec(
            "sovereignty_policy_representative",
            observation_ports=[
                "policy_delivery_in",
                *shared_observation_ports("sovereignty_policy_representative"),
            ],
            output_ports=[
                "sovereignty_policy_representative_commitment_out",
                "issue_update_out",
            ],
        ),
        person_spec(
            "local_public_health_liaison",
            observation_ports=[
                "local_delivery_in",
                *shared_observation_ports("local_public_health_liaison"),
            ],
            output_ports=[
                "local_public_health_liaison_commitment_out",
                "source_disposition_out",
            ],
        ),
        person_spec(
            "partner_representative",
            observation_ports=shared_observation_ports("partner_representative"),
            output_ports=[
                "partner_representative_commitment_out",
                "withdrawal_out",
            ],
        ),
    )
    source_representations = dict(
        zip(PRESSURE_SOURCE_IDS, PRESSURE_SOURCE_REPRESENTATION_IDS, strict=True)
    )
    source_ports = {
        "technical_pressure_source": "technical_source_out",
        "policy_pressure_source": "policy_source_out",
        "local_pressure_source": "local_source_out",
    }
    sources = tuple(
        ActiveSystemSpec(
            active_system_id=source_id,
            entity_id=source_id,
            implementation_id=f"scripted_coordination_{source_id}_v1",
            description=f"Zero-call concrete source process {source_id}.",
            output_port_ids=[source_ports[source_id]],
            output_port_initial_representation_ids={
                source_ports[source_id]: [source_representations[source_id]]
            },
            initial_representation_ids=[source_representations[source_id]],
            initial_private_state={"emissions": 0},
            initial_next_update_at=(
                MINUTES_PER_DAY if condition.pressure_sources_enabled else None
            ),
        )
        for source_id in PRESSURE_SOURCE_IDS
    )
    clock = ActiveSystemSpec(
        active_system_id="meeting_clock",
        entity_id="meeting_clock",
        implementation_id="scripted_coordination_meeting_clock_v1",
        description="Zero-call recurring meeting and deadline clock.",
        output_port_ids=["scheduler_wake_out", "deadline_transition_out"],
        initial_private_state={"wake_index": 0},
        initial_next_update_at=MEETING_TIMES[0],
    )
    return (*people, *sources, clock)


def _coordination_exact_bindings() -> dict[str, ExactMechanismBinding]:
    handlers: dict[str, Callable[[MechanismContext], MechanismOutcome]] = {
        "technical_source_delivery": _exact_source_delivery,
        "policy_source_delivery": _exact_source_delivery,
        "local_source_delivery": _exact_source_delivery,
        "meeting_scheduler": _exact_meeting_scheduler,
        "verification_recorder": _exact_verification,
        "issue_recorder": _exact_issue_update,
        "source_disposition_recorder": _exact_source_disposition,
        "commitment_recorder": _exact_commitment,
        "proposal_recorder": _exact_scope_threshold,
        "withdrawal_recorder": _exact_withdrawal,
        "terminal_decision_gate": _exact_terminal_decision,
        "external_decision_receiver": _exact_external_decision_receipt,
    }
    for person_id in PERSON_IDS[1:]:
        handlers[f"alignment_delivery_{person_id}"] = _exact_alignment_delivery
    for person_id in PERSON_IDS:
        handlers[f"verification_response_delivery_{person_id}"] = (
            _exact_verification_delivery
        )
        handlers[f"meeting_snapshot_delivery_{person_id}"] = (
            _exact_meeting_snapshot_delivery
        )
    bindings: dict[str, ExactMechanismBinding] = {}
    for mechanism_id, handler in handlers.items():
        invariant_id = f"{mechanism_id}_contract"

        def checker(
            context: MechanismContext,
            outcome: MechanismOutcome,
            *,
            expected_handler: Callable[[MechanismContext], MechanismOutcome] = handler,
        ) -> bool:
            expected = expected_handler(context)
            return expected.model_dump(mode="json") == outcome.model_dump(mode="json")

        bindings[mechanism_id] = ExactMechanismBinding(
            implementation_id=f"{mechanism_id}_v1",
            handler=handler,
            invariant_checkers={invariant_id: checker},
        )
    return bindings


def _exact_source_delivery(context: MechanismContext) -> MechanismOutcome:
    targets = {
        "technical_source_delivery": (
            "technical_validation_lead",
            "technical_pressure_source",
        ),
        "policy_source_delivery": (
            "sovereignty_policy_representative",
            "policy_pressure_source",
        ),
        "local_source_delivery": (
            "local_public_health_liaison",
            "local_pressure_source",
        ),
    }
    target, source = targets[context.mechanism.mechanism_id]
    representation = _required_effect_representation(context)
    return MechanismOutcome(
        outcome_code="source_message_delivered",
        observations=[
            ObservationDraft(
                target_entity_id=target,
                via_port_id=context.target_port.port_id,
                apparent_content=representation.content,
                apparent_source_ref=source,
                representation_id=representation.representation_id,
            )
        ],
    )


def _exact_meeting_scheduler(context: MechanismContext) -> MechanismOutcome:
    wake = SchedulerWakeAction.model_validate(context.effect.payload)
    schedule = context.read("meeting_schedule.schedule")
    if not isinstance(schedule, dict):
        raise TypeError("compiled meeting schedule must be an object")
    slots = schedule.get("slots")
    if not isinstance(slots, list) or wake.meeting_index >= len(slots):
        raise ValueError("scheduler wake is outside the compiled schedule")
    slot = slots[wake.meeting_index]
    if not isinstance(slot, dict) or slot.get("modeled_day") != wake.modeled_day:
        raise ValueError("scheduler wake disagrees with the compiled schedule")
    if context.read("external_decision_registry.received_status") is not None:
        return MechanismOutcome(outcome_code="meeting_wake_denied_after_terminal")
    due_people = slot.get("due_person_ids")
    if due_people != list(PERSON_IDS):
        raise ValueError("scheduler wake has an invalid participant set")
    snapshot = {
        "document_kind": "meeting_snapshot",
        "meeting_index": wake.meeting_index,
        "modeled_day": wake.modeled_day,
        "proposal_scope": context.read("deployment_proposal.scope"),
        "decision_threshold": context.read(
            "deployment_proposal.decision_threshold"
        ),
        "issues": context.read("issue_register.items"),
        "commitments": context.read("commitment_register.items"),
        "verification_items": context.read("verification_register.items"),
        "active_partner_count": context.read("decision_record.active_partner_count"),
    }
    return MechanismOutcome(
        outcome_code="meeting_wake_recorded",
        updates=[
            FactUpdate(
                fact_id="meeting_schedule.last_wake_day",
                value=wake.modeled_day,
            )
        ],
        effects=[
            EffectDraft(
                output_port_id="meeting_snapshot_out",
                effect_type="meeting_snapshot",
                payload=cast(dict[str, JsonValue], snapshot),
            )
        ],
    )


def _exact_meeting_snapshot_delivery(
    context: MechanismContext,
) -> MechanismOutcome:
    target = context.mechanism.mechanism_id.removeprefix(
        "meeting_snapshot_delivery_"
    )
    if target not in PERSON_IDS:
        raise ValueError("meeting snapshot delivery has an unknown person")
    if context.effect.payload.get("document_kind") != "meeting_snapshot":
        raise ValueError("meeting snapshot delivery has invalid content")
    return MechanismOutcome(
        outcome_code="meeting_snapshot_delivered",
        observations=[
            ObservationDraft(
                target_entity_id=target,
                via_port_id=context.target_port.port_id,
                apparent_content=_render_json(context.effect.payload),
                apparent_source_ref="meeting_scheduler",
            )
        ],
    )


def _exact_verification(context: MechanismContext) -> MechanismOutcome:
    request = VerificationRequestAction.model_validate(context.effect.payload)
    existing = _record_list(context.read("verification_register.items"))
    if any(item.get("verification_id") == request.verification_id for item in existing):
        return MechanismOutcome(outcome_code="verification_request_denied_duplicate")
    condition = context.read("coordination_condition.condition")
    if not isinstance(condition, str):
        raise TypeError("compiled coordination condition must be a string")
    responses: dict[str, VerificationResponseRecord] = {
        "baseline": VerificationResponseRecord(
            result="supportive",
            explanation="Ordinary independent review remained supportive.",
        ),
        "heterogeneous_pressure": VerificationResponseRecord(
            result="insufficient",
            explanation="Available review did not resolve the introduced uncertainty.",
        ),
        "stabilization": VerificationResponseRecord(
            result="bounded_support",
            explanation="Authoritative review supported a reduced, bounded deployment.",
        ),
    }
    response = responses.get(condition)
    if response is None:
        raise ValueError("unknown compiled coordination condition")
    response_content = _render_model(response)
    response_id = "independent_calibration_response"
    item = VerificationItem(
        verification_id=request.verification_id,
        topic=request.topic,
        requested_by=request.requested_by,
        status="answered",
        response_representation_id=response_id,
    )
    return MechanismOutcome(
        outcome_code="verification_answered",
        updates=[
            FactUpdate(
                fact_id="verification_register.items",
                value=[*existing, item.model_dump(mode="json")],
            )
        ],
        representations=[
            RepresentationDraft(
                representation_id=response_id,
                carrier_id="verification_response_carrier",
                encoding="application/vnd.cybernetic.verification-response+json",
                content=response_content,
                actual_source_ref="verification_recorder",
                parent_representation_ids=(
                    [context.representation.representation_id]
                    if context.representation is not None
                    else []
                ),
            )
        ],
        effects=[
            EffectDraft(
                output_port_id="verification_response_out",
                effect_type="verification_response",
                representation_id=response_id,
                payload={},
            )
        ],
    )


def _exact_verification_delivery(context: MechanismContext) -> MechanismOutcome:
    representation = _required_effect_representation(context)
    VerificationResponseRecord.model_validate_json(representation.content)
    target = context.mechanism.mechanism_id.removeprefix(
        "verification_response_delivery_"
    )
    if target not in PERSON_IDS:
        raise ValueError("verification delivery has an unknown person")
    return MechanismOutcome(
        outcome_code="verification_response_delivered",
        observations=[
            ObservationDraft(
                target_entity_id=target,
                via_port_id=context.target_port.port_id,
                apparent_content=representation.content,
                apparent_source_ref="verification_recorder",
                representation_id=representation.representation_id,
            )
        ],
    )


def _exact_issue_update(context: MechanismContext) -> MechanismOutcome:
    action = IssueUpdateAction.model_validate(context.effect.payload)
    if action.opened_by != "sovereignty_policy_representative":
        return MechanismOutcome(outcome_code="issue_update_denied_actor_mismatch")
    existing = _record_list(context.read("issue_register.items"))
    index = next(
        (i for i, item in enumerate(existing) if item.get("issue_id") == action.issue_id),
        None,
    )
    if index is None and action.lifecycle != "open":
        return MechanismOutcome(outcome_code="issue_update_denied_missing_issue")
    updated = list(existing)
    item = IssueItem(**action.model_dump(mode="json")).model_dump(mode="json")
    if index is None:
        updated.append(item)
    elif existing[index] == item:
        return MechanismOutcome(outcome_code="issue_update_denied_no_change")
    else:
        updated[index] = item
    return MechanismOutcome(
        outcome_code=f"issue_{action.lifecycle}",
        updates=[
            FactUpdate(
                fact_id="issue_register.items",
                value=cast(JsonValue, updated),
            )
        ],
    )


def _exact_source_disposition(context: MechanismContext) -> MechanismOutcome:
    action = SourceDispositionAction.model_validate(context.effect.payload)
    if action.person_id != "local_public_health_liaison":
        return MechanismOutcome(
            outcome_code="source_disposition_denied_actor_mismatch"
        )
    existing = _record_list(context.read("source_disposition_register.items"))
    item = SourceDispositionRecord(**action.model_dump(mode="json")).model_dump(
        mode="json"
    )
    key = (action.person_id, action.source_id)
    updated = [
        record
        for record in existing
        if (record.get("person_id"), record.get("source_id")) != key
    ]
    if len(updated) != len(existing) and any(record == item for record in existing):
        return MechanismOutcome(outcome_code="source_disposition_denied_no_change")
    updated.append(item)
    return MechanismOutcome(
        outcome_code="source_disposition_recorded",
        updates=[
            FactUpdate(
                fact_id="source_disposition_register.items",
                value=cast(JsonValue, updated),
            )
        ],
    )


def _exact_commitment(context: MechanismContext) -> MechanismOutcome:
    action = CommitmentAction.model_validate(context.effect.payload)
    expected_person = context.effect.source_port_id.removesuffix("_commitment_out")
    if action.person_id != expected_person:
        return MechanismOutcome(outcome_code="commitment_denied_actor_mismatch")
    existing = _record_list(context.read("commitment_register.items"))
    updated: list[dict[str, JsonValue]] = []
    changed = False
    for record in existing:
        if record.get("person_id") != action.person_id:
            updated.append(record)
            continue
        if record.get("commitment") == action.commitment:
            return MechanismOutcome(outcome_code="commitment_denied_no_change")
        updated.append(
            CommitmentRecord(
                person_id=action.person_id,
                commitment=action.commitment,
                updated_at_day=context.effect.logical_time // MINUTES_PER_DAY,
            ).model_dump(mode="json")
        )
        changed = True
    if not changed:
        raise ValueError("commitment action names an absent person")
    return MechanismOutcome(
        outcome_code="commitment_recorded",
        updates=[
            FactUpdate(
                fact_id="commitment_register.items",
                value=cast(JsonValue, updated),
            )
        ],
    )


def _exact_scope_threshold(context: MechanismContext) -> MechanismOutcome:
    action = ScopeThresholdAction.model_validate(context.effect.payload)
    updates: list[FactUpdate] = []
    if context.read("deployment_proposal.scope") != action.scope:
        updates.append(FactUpdate(fact_id="deployment_proposal.scope", value=action.scope))
    if context.read("deployment_proposal.decision_threshold") != action.decision_threshold:
        updates.append(
            FactUpdate(
                fact_id="deployment_proposal.decision_threshold",
                value=action.decision_threshold,
            )
        )
    if not updates:
        return MechanismOutcome(outcome_code="scope_threshold_denied_no_change")
    return MechanismOutcome(outcome_code="scope_threshold_recorded", updates=updates)


def _exact_alignment_delivery(context: MechanismContext) -> MechanismOutcome:
    action = AlignmentMessageAction.model_validate(context.effect.payload)
    if action.sender_id != "mission_coordinator":
        return MechanismOutcome(outcome_code="alignment_denied_actor_mismatch")
    target = context.mechanism.mechanism_id.removeprefix("alignment_delivery_")
    if target not in PERSON_IDS:
        raise ValueError("alignment delivery has an unknown person")
    if target == action.sender_id:
        return MechanismOutcome(outcome_code="alignment_sender_delivery_skipped")
    content = _render_json(
        {
            "document_kind": "alignment_message",
            "sender_id": action.sender_id,
            "content": action.content,
        }
    )
    return MechanismOutcome(
        outcome_code="alignment_message_delivered",
        observations=[
            ObservationDraft(
                target_entity_id=target,
                via_port_id=context.target_port.port_id,
                apparent_content=content,
                apparent_source_ref=action.sender_id,
            )
        ],
    )


def _exact_withdrawal(context: MechanismContext) -> MechanismOutcome:
    PartnerWithdrawalAction.model_validate(context.effect.payload)
    count = context.read("decision_record.active_partner_count")
    if not isinstance(count, int) or isinstance(count, bool):
        raise TypeError("active partner count must be an integer")
    if count <= 4:
        return MechanismOutcome(outcome_code="withdrawal_denied_already_recorded")
    return MechanismOutcome(
        outcome_code="partner_withdrawal_recorded",
        updates=[
            FactUpdate(fact_id="decision_record.active_partner_count", value=count - 1)
        ],
    )


def _exact_terminal_decision(context: MechanismContext) -> MechanismOutcome:
    if context.read("external_decision_registry.received_status") is not None:
        return MechanismOutcome(outcome_code="terminal_decision_denied_already_final")
    if context.target_port.port_id == "deadline_transition_in":
        DeadlineTransitionAction.model_validate(context.effect.payload)
        return _accepted_terminal_outcome(
            status="no_decision_by_horizon",
            scope="none",
            source="deadline",
        )
    proposal = DecisionProposal.model_validate(context.effect.payload)
    triggering_representation = _required_effect_representation(context)
    if proposal.proposed_by != "mission_coordinator":
        return MechanismOutcome(
            outcome_code="terminal_decision_denied_actor_mismatch"
        )
    if context.read("meeting_schedule.last_wake_day") != MEETING_DAYS[-1]:
        return MechanismOutcome(
            outcome_code="terminal_decision_denied_before_final_meeting"
        )
    issues = _record_list(context.read("issue_register.items"))
    commitments = _record_list(context.read("commitment_register.items"))
    active_partners = context.read("decision_record.active_partner_count")
    proposal_scope = context.read("deployment_proposal.scope")
    open_blocking = any(
        item.get("blocking") is True
        and item.get("lifecycle") in {"open", "reopened"}
        for item in issues
    )
    commitment_values = {item.get("commitment") for item in commitments}
    eligible = False
    if proposal.requested_status == "deploy_on_time":
        eligible = (
            proposal.requested_scope == "full"
            and proposal_scope == "full"
            and commitment_values == {"support_full"}
            and active_partners == 5
            and not open_blocking
        )
    elif proposal.requested_status == "scope_reduced":
        eligible = (
            proposal.requested_scope == "reduced"
            and proposal_scope == "reduced"
            and commitment_values <= {"support_full", "support_reduced"}
            and active_partners == 5
            and not open_blocking
        )
    if not eligible:
        return MechanismOutcome(outcome_code="terminal_decision_denied_ineligible")
    return _accepted_terminal_outcome(
        status=proposal.requested_status,
        scope=proposal.requested_scope,
        source="reviewed_proposal",
        parent_representation_id=triggering_representation.representation_id,
    )


def _accepted_terminal_outcome(
    *,
    status: FinalDecision,
    scope: DecisionScope,
    source: Literal["reviewed_proposal", "deadline"],
    parent_representation_id: str | None = None,
) -> MechanismOutcome:
    record = TerminalDecisionRecord(status=status, scope=scope, source=source)
    content = _render_model(record)
    representation_id = f"terminal_decision_{status}"
    return MechanismOutcome(
        outcome_code="terminal_decision_accepted",
        updates=[
            FactUpdate(fact_id="decision_record.gate_status", value="approved"),
            FactUpdate(fact_id="decision_record.proposed_status", value=status),
            FactUpdate(fact_id="decision_record.proposed_scope", value=scope),
        ],
        representations=[
            RepresentationDraft(
                representation_id=representation_id,
                carrier_id="terminal_decision_carrier",
                encoding="application/vnd.cybernetic.terminal-decision+json",
                content=content,
                actual_source_ref="terminal_decision_gate",
                parent_representation_ids=(
                    [parent_representation_id]
                    if parent_representation_id is not None
                    else []
                ),
            )
        ],
        effects=[
            EffectDraft(
                output_port_id="terminal_decision_out",
                effect_type="terminal_decision",
                representation_id=representation_id,
                payload={},
            )
        ],
    )


def _exact_external_decision_receipt(context: MechanismContext) -> MechanismOutcome:
    if context.read("external_decision_registry.received_status") is not None:
        return MechanismOutcome(outcome_code="external_receipt_denied_already_final")
    representation = _required_effect_representation(context)
    record = TerminalDecisionRecord.model_validate_json(representation.content)
    return MechanismOutcome(
        outcome_code="external_decision_received",
        updates=[
            FactUpdate(
                fact_id="external_decision_registry.received_status",
                value=record.status,
            ),
            FactUpdate(
                fact_id="external_decision_registry.received_scope",
                value=record.scope,
            ),
        ],
    )


def _scripted_meeting_clock(item: ActiveSystemInput) -> ActiveStepResult:
    wake_index = _private_int(item, "wake_index")
    if wake_index < 4:
        action = ActionIntent(
            output_port_id="scheduler_wake_out",
            payload=SchedulerWakeAction(
                meeting_index=wake_index,
                modeled_day=MEETING_DAYS[wake_index],
            ).model_dump(mode="json"),
            public_summary=(
                f"The retained scheduler opened meeting {wake_index + 1} "
                f"for modeled day {MEETING_DAYS[wake_index]}."
            ),
        )
        next_time = (
            MEETING_TIMES[wake_index + 1]
            if wake_index + 1 < 4
            else DECISION_DEADLINE_TIME
        )
        directive = UpdateScheduleDirective(mode="schedule", next_update_at=next_time)
    elif wake_index == 4:
        action = ActionIntent(
            output_port_id="deadline_transition_out",
            payload=DeadlineTransitionAction().model_dump(mode="json"),
            public_summary="The retained day-4 fallback decision deadline became due.",
        )
        directive = UpdateScheduleDirective(mode="dormant")
    else:
        raise ValueError("meeting clock wake index exceeded the reviewed schedule")
    return _scripted_result(
        item,
        private_state={"wake_index": wake_index + 1},
        actions=[action],
        directive=directive,
    )


def _scripted_pressure_source(item: ActiveSystemInput) -> ActiveStepResult:
    emissions = _private_int(item, "emissions")
    if emissions not in {0, 1}:
        raise ValueError("pressure source exceeded its reviewed emission schedule")
    output_ports = {
        "technical_pressure_source": (
            "technical_source_out",
            "technical_pressure_message",
        ),
        "policy_pressure_source": ("policy_source_out", "policy_pressure_message"),
        "local_pressure_source": ("local_source_out", "local_pressure_message"),
    }
    output_port, representation_id = output_ports[item.active_system_id]
    directive = (
        UpdateScheduleDirective(mode="schedule", next_update_at=2 * MINUTES_PER_DAY)
        if emissions == 0
        else UpdateScheduleDirective(mode="dormant")
    )
    return _scripted_result(
        item,
        private_state={"emissions": emissions + 1},
        actions=[
            ActionIntent(
                output_port_id=output_port,
                representation_id=representation_id,
                payload={},
                public_summary=f"{item.active_system_id} emitted its retained message.",
            )
        ],
        directive=directive,
    )


def _scripted_mission_coordinator(item: ActiveSystemInput) -> ActiveStepResult:
    state = _person_state(item)
    _retain_verification_result(state, item)
    actions: list[ActionIntent] = []
    meeting_index = _due_meeting_index(item, state)
    if meeting_index == 0:
        actions.append(
            ActionIntent(
                output_port_id="alignment_message_out",
                payload=AlignmentMessageAction(
                    sender_id="mission_coordinator",
                    content="Surface material concerns and retain reasons for changes.",
                ).model_dump(mode="json"),
                public_summary="The coordinator requested explicit, reasoned review.",
            )
        )
    elif meeting_index == 1:
        actions.append(_scope_action("full"))
    elif meeting_index == 3:
        bounded = state["verification_result"] == "bounded_support"
        requested_scope: DecisionScope = "reduced" if bounded else "full"
        requested_status: FinalDecision = "scope_reduced" if bounded else "deploy_on_time"
        if bounded:
            actions.append(_scope_action("reduced"))
        actions.append(
            ActionIntent(
                output_port_id="terminal_proposal_out",
                representation_id="deployment_proposal_copy",
                payload=DecisionProposal(
                    proposal_id="meeting_four_terminal_proposal",
                    proposed_by="mission_coordinator",
                    requested_status=requested_status,
                    requested_scope=requested_scope,
                    evidence_refs=["independent_calibration_response"],
                    acknowledged_issue_ids=list(
                        cast(list[str], state["opened_issue_ids"])
                    ),
                    active_partner_ids=list(PERSON_IDS),
                ).model_dump(mode="json"),
                public_summary=(
                    f"The coordinator proposed {requested_status} at "
                    f"{requested_scope} scope."
                ),
            )
        )
    return _person_result(item, state, actions, meeting_index)


def _scripted_technical_lead(item: ActiveSystemInput) -> ActiveStepResult:
    state = _person_state(item)
    _retain_verification_result(state, item)
    actions: list[ActionIntent] = []
    meeting_index = _due_meeting_index(item, state)
    if meeting_index == 0 and state["commitment"] != "defer":
        actions.append(_commitment_intent("technical_validation_lead", "defer"))
        state["commitment"] = "defer"
    received_technical_pressure = any(
        document.get("topic") == "calibration_uncertainty"
        for document in _observation_documents(item)
    )
    if not _private_bool(state, "verification_requested") and (
        received_technical_pressure or meeting_index == 1
    ):
        actions.append(
            ActionIntent(
                output_port_id="verification_request_out",
                representation_id="technical_validation_dossier_copy",
                payload=VerificationRequestAction().model_dump(mode="json"),
                public_summary="The validation lead requested independent calibration review.",
            )
        )
        state["verification_requested"] = True
    result = cast(str, state["verification_result"])
    desired: Commitment | None = None
    if result == "supportive":
        desired = "support_full"
    elif result == "bounded_support":
        desired = "support_reduced"
    if desired is not None and state["commitment"] != desired:
        actions.append(_commitment_intent("technical_validation_lead", desired))
        state["commitment"] = desired
    return _person_result(item, state, actions, meeting_index)


def _scripted_policy_representative(item: ActiveSystemInput) -> ActiveStepResult:
    state = _person_state(item)
    _retain_verification_result(state, item)
    actions: list[ActionIntent] = []
    meeting_index = _due_meeting_index(item, state)
    opened = cast(list[str], state["opened_issue_ids"])
    if meeting_index == 0 and "oversight_review" not in opened:
        actions.append(
            _issue_intent(
                issue_id="oversight_review",
                topic="Ordinary oversight review",
                lifecycle="open",
                blocking=True,
                evidence_refs=["deployment_proposal_copy"],
            )
        )
        opened.append("oversight_review")
    documents = _observation_documents(item)
    received_policy_pressure = any(
        document.get("topic") == "sovereignty_and_transparency"
        for document in documents
    )
    verification_result = cast(str, state["verification_result"])
    if (
        received_policy_pressure
        and verification_result != "bounded_support"
        and "sovereignty_concern" not in opened
    ):
        actions.append(
            _issue_intent(
                issue_id="sovereignty_concern",
                topic="Sovereignty and transparency concern",
                lifecycle="open",
                blocking=True,
                evidence_refs=["policy_pressure_message"],
            )
        )
        opened.append("sovereignty_concern")
    reopened = cast(list[str], state.setdefault("reopened_issue_ids", []))
    if (
        verification_result == "insufficient"
        and "sovereignty_concern" in opened
        and "sovereignty_concern" not in reopened
    ):
        actions.append(
            _issue_intent(
                issue_id="sovereignty_concern",
                topic="Sovereignty and transparency concern",
                lifecycle="reopened",
                blocking=True,
                evidence_refs=["independent_calibration_response"],
            )
        )
        reopened.append("sovereignty_concern")
    if verification_result in {"supportive", "bounded_support"}:
        for issue_id in list(opened):
            resolved = cast(list[str], state.setdefault("resolved_issue_ids", []))
            if issue_id in resolved:
                continue
            actions.append(
                _issue_intent(
                    issue_id=issue_id,
                    topic=(
                        "Ordinary oversight review"
                        if issue_id == "oversight_review"
                        else "Sovereignty and transparency concern"
                    ),
                    lifecycle="resolved",
                    blocking=True,
                    evidence_refs=["independent_calibration_response"],
                )
            )
            resolved.append(issue_id)
    return _person_result(item, state, actions, meeting_index)


def _scripted_local_liaison(item: ActiveSystemInput) -> ActiveStepResult:
    state = _person_state(item)
    _retain_verification_result(state, item)
    actions: list[ActionIntent] = []
    meeting_index = _due_meeting_index(item, state)
    received_local_pressure = any(
        document.get("topic") == "local_safety_and_legitimacy"
        for document in _observation_documents(item)
    )
    if received_local_pressure and not _private_bool(state, "source_recorded"):
        bounded = state["verification_result"] == "bounded_support"
        disposition: SourceDisposition = "relied_on" if bounded else "validation_pending"
        actions.append(
            ActionIntent(
                output_port_id="source_disposition_out",
                payload=SourceDispositionAction(
                    person_id="local_public_health_liaison",
                    source_id="local_pressure_source",
                    disposition=disposition,
                    evidence_refs=["local_pressure_message"],
                ).model_dump(mode="json"),
                public_summary=f"The local liaison recorded {disposition} for the local source.",
            )
        )
        desired: Commitment = "support_reduced" if bounded else "defer"
        if state["commitment"] != desired:
            actions.append(_commitment_intent("local_public_health_liaison", desired))
            state["commitment"] = desired
        state["source_recorded"] = True
    if (
        state["verification_result"] == "bounded_support"
        and state["commitment"] != "support_reduced"
    ):
        actions.append(
            _commitment_intent("local_public_health_liaison", "support_reduced")
        )
        state["commitment"] = "support_reduced"
    return _person_result(item, state, actions, meeting_index)


def _scripted_partner_representative(item: ActiveSystemInput) -> ActiveStepResult:
    state = _person_state(item)
    _retain_verification_result(state, item)
    meeting_index = _due_meeting_index(item, state)
    actions: list[ActionIntent] = []
    verification_result = state["verification_result"]
    if verification_result == "insufficient" and state["commitment"] != "withdraw":
        actions.extend(
            [
                _commitment_intent("partner_representative", "withdraw"),
                ActionIntent(
                    output_port_id="withdrawal_out",
                    payload=PartnerWithdrawalAction().model_dump(mode="json"),
                    public_summary=(
                        "The partner representative withdrew after the "
                        "independent review remained insufficient."
                    ),
                ),
            ]
        )
        state["commitment"] = "withdraw"
    elif (
        verification_result == "bounded_support"
        and state["commitment"] != "support_reduced"
    ):
        actions.append(_commitment_intent("partner_representative", "support_reduced"))
        state["commitment"] = "support_reduced"
    return _person_result(item, state, actions, meeting_index)


def _person_result(
    item: ActiveSystemInput,
    state: dict[str, JsonValue],
    actions: list[ActionIntent],
    meeting_index: int | None,
) -> ActiveStepResult:
    return _scripted_result(
        item,
        private_state=state,
        actions=actions,
        directive=UpdateScheduleDirective(mode="preserve"),
    )


def _scripted_result(
    item: ActiveSystemInput,
    *,
    private_state: dict[str, JsonValue],
    actions: list[ActionIntent],
    directive: UpdateScheduleDirective,
) -> ActiveStepResult:
    return ActiveStepResult(
        proposal=ActiveProposal(
            active_system_id=item.active_system_id,
            implementation_id=f"scripted_coordination_{item.active_system_id}_v1",
            private_state=private_state,
            actions=actions,
            update_schedule=directive,
        )
    )


def _person_state(item: ActiveSystemInput) -> dict[str, JsonValue]:
    state = dict(item.private_state)
    state.setdefault("verification_requested", False)
    state.setdefault("source_recorded", False)
    state.setdefault("resolved_issue_ids", [])
    state.setdefault("reopened_issue_ids", [])
    return state


def _due_meeting_index(
    item: ActiveSystemInput,
    state: dict[str, JsonValue],
) -> int | None:
    snapshots = [
        document
        for document in _observation_documents(item)
        if document.get("document_kind") == "meeting_snapshot"
    ]
    if not snapshots:
        return None
    if len(snapshots) != 1:
        raise ValueError("person received multiple meeting snapshots at once")
    meeting_index = snapshots[0].get("meeting_index")
    if not isinstance(meeting_index, int) or isinstance(meeting_index, bool):
        raise ValueError("meeting snapshot has an invalid index")
    completed = _private_int_value(state, "meetings_completed")
    if completed >= len(MEETING_TIMES):
        raise ValueError("person exceeded the four reviewed meetings")
    if meeting_index != completed:
        raise ValueError("person received an out-of-order meeting snapshot")
    state["meetings_completed"] = completed + 1
    return meeting_index


def _retain_verification_result(
    state: dict[str, JsonValue],
    item: ActiveSystemInput,
) -> None:
    for document in _observation_documents(item):
        if document.get("document_kind") == "verification_response":
            result = document.get("result")
            if result not in {"supportive", "insufficient", "bounded_support"}:
                raise ValueError("verification response has unknown result")
            state["verification_result"] = result


def _scope_action(scope: DecisionScope) -> ActionIntent:
    threshold: Literal[
        "reviewed_evidence_and_partner_support",
        "bounded_evidence_and_partner_support",
    ] = (
        "bounded_evidence_and_partner_support"
        if scope == "reduced"
        else "reviewed_evidence_and_partner_support"
    )
    return ActionIntent(
        output_port_id="scope_threshold_out",
        payload=ScopeThresholdAction(
            scope=scope,
            decision_threshold=threshold,
        ).model_dump(mode="json"),
        public_summary=f"The coordinator proposed {scope} deployment scope.",
    )


def _commitment_intent(person_id: PersonId, commitment: Commitment) -> ActionIntent:
    return ActionIntent(
        output_port_id=f"{person_id}_commitment_out",
        payload=CommitmentAction(
            person_id=person_id,
            commitment=commitment,
        ).model_dump(mode="json"),
        public_summary=f"{person_id} changed commitment to {commitment}.",
    )


def _issue_intent(
    *,
    issue_id: str,
    topic: str,
    lifecycle: IssueLifecycle,
    blocking: bool,
    evidence_refs: list[str],
) -> ActionIntent:
    return ActionIntent(
        output_port_id="issue_update_out",
        payload=IssueUpdateAction(
            issue_id=issue_id,
            topic=topic,
            lifecycle=lifecycle,
            blocking=blocking,
            opened_by="sovereignty_policy_representative",
            evidence_refs=evidence_refs,
        ).model_dump(mode="json"),
        public_summary=f"The policy representative marked {issue_id} {lifecycle}.",
    )


def _observation_documents(item: ActiveSystemInput) -> list[dict[str, JsonValue]]:
    documents: list[dict[str, JsonValue]] = []
    for observation in item.observations:
        try:
            value = json.loads(observation.apparent_content)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            documents.append(cast(dict[str, JsonValue], value))
    return documents


def _required_effect_representation(context: MechanismContext) -> RepresentationToken:
    if context.representation is None:
        raise ValueError("mechanism requires a routed representation")
    return context.representation


def _record_list(value: JsonValue) -> list[dict[str, JsonValue]]:
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise TypeError("record fact must be a list of objects")
    return [cast(dict[str, JsonValue], item) for item in value]


def _private_int(item: ActiveSystemInput, key: str) -> int:
    return _private_int_value(item.private_state, key)


def _private_int_value(state: Mapping[str, JsonValue], key: str) -> int:
    value = state.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"private state {key} must be an integer")
    return value


def _private_bool(state: Mapping[str, JsonValue], key: str) -> bool:
    value = state.get(key)
    if not isinstance(value, bool):
        raise TypeError(f"private state {key} must be a boolean")
    return value


def _render_model(model: BaseModel) -> str:
    return _render_json(model.model_dump(mode="json"))


def _render_json(value: object) -> str:
    return _canonical_json(value).decode()


def _terminal_evidence_event_ids(
    session: ActiveRuntimeSession,
    run_control: ResolvedRunControlPlan,
    condition_ids: list[str],
) -> list[str]:
    if not condition_ids:
        return []
    conditions = {item.condition_id: item for item in run_control.terminal_conditions}
    return [
        event.event_id
        for event in session.checkpoint().core_checkpoint.events
        if event.patch is not None
        and any(
            change.fact_id == conditions[condition_id].fact_id
            and change.after == conditions[condition_id].expected_value
            for change in event.patch.fact_changes
            for condition_id in condition_ids
        )
    ][-1:]
