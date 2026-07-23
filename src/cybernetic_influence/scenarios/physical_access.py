"""Grounded physical-access probe separating proof, permission, and capability."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import json
from typing import Literal, TypeAlias, TypeVar, cast

from pydantic import BaseModel, ConfigDict
from pydantic.types import JsonValue

from cybernetic_influence.active_runtime import (
    ActiveProposal,
    ActiveRuntimeConfig,
    ActiveRuntimeResult,
    ActiveRuntimeSession,
    ActiveStepResult,
    ActiveSystemBinding,
    ActiveSystemInput,
    ActiveSystemSpec,
    ActionIntent,
    NativeLlmActiveSystem,
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
    EffectDraft,
    EntityState,
    FactState,
    FactUpdate,
    FidelityNote,
    MechanismOutcome,
    MechanismSpec,
    ObservationDraft,
    PlacementDraft,
    PlacementState,
    PlaceState,
    PortState,
    RepresentationDraft,
    RepresentationToken,
    SpatialLinkState,
    representation_digest,
)

PHYSICAL_ACCESS_MODEL = "gpt-5.6-terra"
PHYSICAL_ACCESS_REASONING_EFFORT = "medium"
PHYSICAL_ACCESS_TASK = "cybernetic_influence_v3_physical_access_step"
PHYSICAL_ACCESS_BOUNDARY_ID = "equipment_access_view"
PHYSICAL_ACCESS_SCHEDULE: tuple[tuple[int, str], ...] = (
    (0, "technician"),
    (1, "technician"),
    (2, "technician"),
)

BADGE_ENCODING = "application/vnd.cybernetic.badge-presentation+json"
POLICY_ENCODING = "application/vnd.cybernetic.access-policy+json"
AUTHENTICATION_ENCODING = "application/vnd.cybernetic.authentication-decision+json"
AUTHORIZATION_ENCODING = "application/vnd.cybernetic.authorization-decision+json"
ACCESS_RESULT_ENCODING = "application/vnd.cybernetic.access-result+json"
ENTRY_RESULT_ENCODING = "application/vnd.cybernetic.entry-result+json"

PhysicalAccessArmId: TypeAlias = Literal[
    "authorized_access",
    "authorization_absent",
    "latch_jammed",
]
AccessStatus: TypeAlias = Literal[
    "access_granted",
    "denied_authentication",
    "denied_authorization",
    "denied_latch_jammed",
]

_FORBID = ConfigDict(extra="forbid", strict=True)
_BADGE_SECRET = "equipment_badge_key_41"
_StrictModelT = TypeVar("_StrictModelT", bound="_StrictModel")


class _StrictModel(BaseModel):
    model_config = _FORBID


class PhysicalAccessArmConfiguration(_StrictModel):
    arm_id: PhysicalAccessArmId
    policy_authorizes: bool
    latch_operable: bool


class BadgePresentation(_StrictModel):
    document_kind: Literal["badge_presentation"] = "badge_presentation"
    subject_id: Literal["technician"] = "technician"
    candidate: str


class AccessPolicy(_StrictModel):
    document_kind: Literal["access_policy"] = "access_policy"
    policy_id: Literal["equipment_room_policy"] = "equipment_room_policy"
    allowed_subject_ids: list[str]


class AuthenticationDecision(_StrictModel):
    document_kind: Literal["authentication_decision"] = "authentication_decision"
    subject_id: Literal["technician"] = "technician"
    authenticated: bool


class AuthorizationDecision(_StrictModel):
    document_kind: Literal["authorization_decision"] = "authorization_decision"
    subject_id: Literal["technician"] = "technician"
    authenticated: bool
    authorized: bool
    policy_id: Literal["equipment_room_policy"] = "equipment_room_policy"


class AccessResult(_StrictModel):
    document_kind: Literal["access_result"] = "access_result"
    subject_id: Literal["technician"] = "technician"
    status: AccessStatus


class CrossingRequest(_StrictModel):
    target_place_id: Literal["equipment_room"] = "equipment_room"


class EntryResult(_StrictModel):
    document_kind: Literal["entry_result"] = "entry_result"
    subject_id: Literal["technician"] = "technician"
    status: Literal["entered", "crossing_denied"]


class PhysicalAccessReadout(_StrictModel):
    final_location: str
    authentication: str
    authorization: str
    latch_result: str
    entered: bool


TECHNICIAN_PERSONA = (
    "You are a cautious maintenance technician. You accepted a position that "
    "includes inspecting equipment when assigned, remember being assigned to "
    "inspect pump_7, and believe the carried badge is the normal way to request "
    "entry. You treat reader and door feedback as evidence rather than assuming "
    "that a valid badge guarantees permission or that an approved door can move."
)


@dataclass(frozen=True)
class PhysicalAccessFixture:
    arm: PhysicalAccessArmConfiguration
    scenario: CausalScenario
    exact_bindings: Mapping[str, ExactMechanismBinding]
    active_specs: tuple[ActiveSystemSpec, ...]


@dataclass(frozen=True)
class _ScriptedImplementation:
    implementation_id: str
    handler: Callable[[ActiveSystemInput], ActiveStepResult]

    def step(self, active_input: ActiveSystemInput) -> ActiveStepResult:
        return self.handler(active_input)


def physical_access_arm_configurations() -> tuple[PhysicalAccessArmConfiguration, ...]:
    return (
        PhysicalAccessArmConfiguration(
            arm_id="authorized_access",
            policy_authorizes=True,
            latch_operable=True,
        ),
        PhysicalAccessArmConfiguration(
            arm_id="authorization_absent",
            policy_authorizes=False,
            latch_operable=True,
        ),
        PhysicalAccessArmConfiguration(
            arm_id="latch_jammed",
            policy_authorizes=True,
            latch_operable=False,
        ),
    )


def physical_access_fixture(
    arm: PhysicalAccessArmConfiguration,
    *,
    badge_candidate: str = _BADGE_SECRET,
) -> PhysicalAccessFixture:
    selected = PhysicalAccessArmConfiguration.model_validate(
        arm.model_dump(mode="json")
    )
    policy = AccessPolicy(
        allowed_subject_ids=["technician"] if selected.policy_authorizes else []
    )
    badge = BadgePresentation(candidate=badge_candidate)
    state = CausalState(
        entities=_entities(selected),
        places=_places(),
        placements=_placements(),
        spatial_links=_spatial_links(),
        ports=_ports(),
        connections=_connections(),
        mechanisms=_mechanisms(),
        carriers=_carriers(),
        representations={
            "technician_badge": _token(
                "technician_badge",
                "technician_badge_carrier",
                BADGE_ENCODING,
                badge,
                "credential_authority",
                visibility="mechanism",
            ),
            "access_policy_copy": _token(
                "access_policy_copy",
                "access_policy_carrier",
                POLICY_ENCODING,
                policy,
                "policy_author",
            ),
        },
    )
    scenario = CausalScenario(
        scenario_id=f"physical_access_{selected.arm_id}",
        description=(
            "One technician requests and, when possible, crosses a controlled "
            "physical boundary."
        ),
        initial_state=state,
        analytical_boundaries=[
            AnalyticalBoundary(
                boundary_id=PHYSICAL_ACCESS_BOUNDARY_ID,
                label="Equipment-room access view",
                description=(
                    "Execution-inert view over a person, information, controller, "
                    "latch, boundary, and observed crossing."
                ),
                member_refs=_boundary_members(state),
            )
        ],
        fidelity_questions=[
            "Did credential proof remain distinct from policy authorization?",
            "Did authorization remain distinct from latch operability?",
            "Did location change only after the boundary became open?",
            "Did the technician receive outcomes only through declared observations?",
        ],
    )
    return PhysicalAccessFixture(
        arm=selected,
        scenario=scenario,
        exact_bindings=_exact_bindings(),
        active_specs=(_active_spec(),),
    )


def physical_access_runtime_config() -> ActiveRuntimeConfig:
    return ActiveRuntimeConfig(
        per_call_budget=0.05,
        per_run_budget=0.20,
        max_actions_per_system=1,
        max_observations_per_system=8,
        max_private_state_bytes=16_384,
    )


def physical_access_native_bindings(
    fixture: PhysicalAccessFixture,
    *,
    trace_id_prefix: str,
) -> dict[str, ActiveSystemBinding]:
    spec = fixture.active_specs[0]
    return {
        "technician": ActiveSystemBinding(
            spec.implementation_id,
            NativeLlmActiveSystem.from_bound_configuration(
                implementation_family_id="native_physical_technician_v1",
                persona=TECHNICIAN_PERSONA,
                model=PHYSICAL_ACCESS_MODEL,
                task=PHYSICAL_ACCESS_TASK,
                trace_id_prefix=trace_id_prefix,
                reasoning_effort=PHYSICAL_ACCESS_REASONING_EFFORT,
                max_memory_entries=16,
                max_output_tokens=768,
                decision_wire_contract="openai-json-payload-wire.v2",
            ),
        )
    }


def physical_access_scripted_bindings(
    fixture: PhysicalAccessFixture,
) -> dict[str, ActiveSystemBinding]:
    spec = fixture.active_specs[0]

    def bound(active_input: ActiveSystemInput) -> ActiveStepResult:
        result = _scripted_technician(active_input)
        return result.model_copy(
            update={
                "proposal": result.proposal.model_copy(
                    update={"implementation_id": spec.implementation_id}
                )
            }
        )

    return {
        "technician": ActiveSystemBinding(
            spec.implementation_id,
            _ScriptedImplementation(spec.implementation_id, bound),
        )
    }


def run_physical_access(
    fixture: PhysicalAccessFixture,
    bindings: Mapping[str, ActiveSystemBinding],
    *,
    run_id: str,
) -> ActiveRuntimeResult:
    session = ActiveRuntimeSession(
        fixture.scenario,
        fixture.exact_bindings,
        fixture.active_specs,
        bindings,
        run_id=run_id,
        config=physical_access_runtime_config(),
    )
    for logical_time, participant_id in PHYSICAL_ACCESS_SCHEDULE:
        session.activate([participant_id], logical_time=logical_time)
    return session.complete()


def build_physical_access_readout(
    result: ActiveRuntimeResult,
) -> PhysicalAccessReadout:
    state = result.core_result.final_state
    location = state.placements["technician"].place_id
    return PhysicalAccessReadout(
        final_location=location,
        authentication=str(
            state.fact("credential_authority.last_authentication").value
        ),
        authorization=str(
            state.fact("access_controller.last_authorization").value
        ),
        latch_result=str(state.fact("secure_door.last_latch_result").value),
        entered=location == "equipment_room",
    )


def physical_access_summary(
    readout: PhysicalAccessReadout,
) -> tuple[str, str]:
    if readout.entered:
        return (
            "Entered equipment room",
            "The badge authenticated and the stored policy authorized the "
            "technician. The operable latch unlocked, the technician crossed the "
            "open boundary, and the entry sensor reported the realized crossing.",
        )
    if readout.authentication != "authenticated":
        return (
            "Entry denied at authentication",
            "The credential comparison failed. No policy grant, latch release, or "
            "physical crossing followed.",
        )
    if readout.authorization != "authorized":
        return (
            "Entry denied by policy",
            "The badge authenticated, but the stored policy did not authorize the "
            "technician. The latch remained locked and no crossing occurred.",
        )
    return (
        "Entry blocked by jammed latch",
        "The badge authenticated and the stored policy authorized the technician, "
        "but the physical latch could not release. The boundary remained locked "
        "and no crossing occurred.",
    )


def _entities(
    arm: PhysicalAccessArmConfiguration,
) -> dict[str, EntityState]:
    return {
        "technician": EntityState(
            entity_id="technician",
            entity_kind="person",
            description="Person assigned to inspect pump_7.",
        ),
        "pump_7": EntityState(
            entity_id="pump_7",
            entity_kind="equipment",
            description="Non-agentic pump inside the equipment room.",
        ),
        "secure_door": EntityState(
            entity_id="secure_door",
            entity_kind="state_machine",
            description="Controlled physical boundary and latch.",
            attributes={
                "lock_state": FactState(value="locked"),
                "latch_operable": FactState(value=arm.latch_operable),
                "last_latch_result": FactState(value="not_attempted"),
            },
        ),
        "credential_authority": EntityState(
            entity_id="credential_authority",
            entity_kind="authentication_service",
            description="Protected exact badge-comparison state.",
            attributes={
                "badge_verifier": FactState(
                    value=_BADGE_SECRET,
                    visibility="mechanism",
                ),
                "last_authentication": FactState(value="not_attempted"),
            },
        ),
        "access_controller": EntityState(
            entity_id="access_controller",
            entity_kind="authorization_service",
            description="Controller that reads one bound policy representation.",
            attributes={
                "last_authorization": FactState(value="not_attempted"),
            },
        ),
        "written_access_policy": EntityState(
            entity_id="written_access_policy",
            entity_kind="document",
            description="Concrete access-policy document copied to the controller.",
        ),
        "policy_author": EntityState(
            entity_id="policy_author",
            entity_kind="person",
            description="Person who authored the access-policy copy.",
        ),
    }


def _places() -> dict[str, PlaceState]:
    return {
        "maintenance_facility": PlaceState(
            place_id="maintenance_facility",
            place_kind="facility",
            description="Facility containing the controlled maintenance area.",
        ),
        "hallway": PlaceState(
            place_id="hallway",
            place_kind="corridor",
            description="Hallway outside the controlled equipment room.",
            parent_place_id="maintenance_facility",
        ),
        "equipment_room": PlaceState(
            place_id="equipment_room",
            place_kind="room",
            description="Controlled room containing pump_7.",
            parent_place_id="maintenance_facility",
        ),
    }


def _placements() -> dict[str, PlacementState]:
    return {
        "technician": PlacementState(
            entity_id="technician",
            place_id="hallway",
        ),
        "pump_7": PlacementState(
            entity_id="pump_7",
            place_id="equipment_room",
        ),
        "credential_authority": PlacementState(
            entity_id="credential_authority",
            place_id="hallway",
        ),
        "access_controller": PlacementState(
            entity_id="access_controller",
            place_id="hallway",
        ),
        "written_access_policy": PlacementState(
            entity_id="written_access_policy",
            place_id="hallway",
        ),
    }


def _spatial_links() -> dict[str, SpatialLinkState]:
    return {
        "equipment_room_threshold": SpatialLinkState(
            spatial_link_id="equipment_room_threshold",
            endpoint_a_place_id="hallway",
            endpoint_b_place_id="equipment_room",
            link_kind="controlled_doorway",
            substrate_entity_ids=["secure_door"],
            description=(
                "Topological adjacency across the controlled equipment-room "
                "threshold; it does not assert permission or operability."
            ),
        )
    }


def _ports() -> dict[str, PortState]:
    specifications = (
        ("technician_badge_out", "technician", "output", "badge_presentation"),
        ("badge_reader_in", "credential_authority", "input", "badge_presentation"),
        (
            "authentication_decision_out",
            "exact_badge_authentication",
            "output",
            "authentication_decision",
        ),
        (
            "authorization_request_in",
            "access_controller",
            "input",
            "authentication_decision",
        ),
        (
            "authorization_decision_out",
            "exact_policy_authorization",
            "output",
            "authorization_decision",
        ),
        ("latch_command_in", "secure_door", "input", "authorization_decision"),
        (
            "access_result_out",
            "exact_latch_actuation",
            "output",
            "access_result",
        ),
        (
            "technician_access_result_in",
            "technician",
            "input",
            "access_result",
        ),
        ("technician_cross_out", "technician", "output", "crossing_attempt"),
        ("door_crossing_in", "secure_door", "input", "crossing_attempt"),
        (
            "entry_result_out",
            "exact_threshold_crossing",
            "output",
            "entry_result",
        ),
        (
            "technician_entry_result_in",
            "technician",
            "input",
            "entry_result",
        ),
    )
    return {
        port_id: PortState(
            port_id=port_id,
            owner_ref=owner,
            direction=cast(Literal["input", "output"], direction),
            effect_type=effect_type,
            description=f"Physical-access interface {port_id}.",
        )
        for port_id, owner, direction, effect_type in specifications
    }


def _connections() -> dict[str, ConnectionState]:
    specifications = (
        ("technician_to_reader", "technician_badge_out", "badge_reader_in"),
        (
            "authenticator_to_controller",
            "authentication_decision_out",
            "authorization_request_in",
        ),
        (
            "controller_to_latch",
            "authorization_decision_out",
            "latch_command_in",
        ),
        (
            "latch_to_technician",
            "access_result_out",
            "technician_access_result_in",
        ),
        ("technician_to_threshold", "technician_cross_out", "door_crossing_in"),
        (
            "threshold_to_technician",
            "entry_result_out",
            "technician_entry_result_in",
        ),
    )
    return {
        connection_id: ConnectionState(
            connection_id=connection_id,
            source_port_id=source,
            target_port_id=target,
            description=f"Concrete physical-access route {connection_id}.",
        )
        for connection_id, source, target in specifications
    }


def _mechanisms() -> dict[str, MechanismSpec]:
    fidelity = _fidelity()
    return {
        "exact_badge_authentication": MechanismSpec(
            mechanism_id="exact_badge_authentication",
            mechanism_kind="credential_comparison",
            implementation_id="exact_badge_authentication_v1",
            description="Compare the presented badge with protected verifier state.",
            input_port_ids=["badge_reader_in"],
            output_port_ids=["authentication_decision_out"],
            read_fact_ids=[
                "credential_authority.badge_verifier",
                "credential_authority.last_authentication",
            ],
            write_fact_ids=["credential_authority.last_authentication"],
            write_carrier_ids=["authentication_decision_buffer"],
            substrate_refs=[
                "credential_authority",
                "authentication_decision_buffer",
            ],
            invariant_ids=["authentication_valid"],
            fidelity=fidelity,
        ),
        "exact_policy_authorization": MechanismSpec(
            mechanism_id="exact_policy_authorization",
            mechanism_kind="policy_authorization",
            implementation_id="exact_policy_authorization_v1",
            description="Read the bound policy copy after successful authentication.",
            input_port_ids=["authorization_request_in"],
            output_port_ids=["authorization_decision_out"],
            read_fact_ids=["access_controller.last_authorization"],
            read_representation_ids=["access_policy_copy"],
            write_fact_ids=["access_controller.last_authorization"],
            write_carrier_ids=["authorization_decision_buffer"],
            substrate_refs=[
                "access_controller",
                "access_policy_carrier",
                "authorization_decision_buffer",
            ],
            invariant_ids=["authorization_valid"],
            fidelity=fidelity,
        ),
        "exact_latch_actuation": MechanismSpec(
            mechanism_id="exact_latch_actuation",
            mechanism_kind="physical_latch_actuation",
            implementation_id="exact_latch_actuation_v1",
            description="Attempt latch release after the authorization decision.",
            input_port_ids=["latch_command_in"],
            output_port_ids=["access_result_out"],
            read_fact_ids=[
                "secure_door.lock_state",
                "secure_door.latch_operable",
                "secure_door.last_latch_result",
            ],
            write_fact_ids=[
                "secure_door.lock_state",
                "secure_door.last_latch_result",
            ],
            write_carrier_ids=["access_result_buffer"],
            substrate_refs=["secure_door", "access_result_buffer"],
            invariant_ids=["latch_valid"],
            fidelity=fidelity,
        ),
        "exact_access_result_delivery": MechanismSpec(
            mechanism_id="exact_access_result_delivery",
            mechanism_kind="sensor_delivery",
            implementation_id="exact_access_delivery_v1",
            description="Deliver reader/latch feedback to the technician.",
            input_port_ids=["technician_access_result_in"],
            write_carrier_ids=["technician_access_result_buffer"],
            observation_target_ids=["technician"],
            substrate_refs=["technician", "technician_access_result_buffer"],
            invariant_ids=["delivery_valid"],
            fidelity=fidelity,
        ),
        "exact_threshold_crossing": MechanismSpec(
            mechanism_id="exact_threshold_crossing",
            mechanism_kind="physical_threshold_crossing",
            implementation_id="exact_threshold_crossing_v1",
            description="Change location only across an open physical boundary.",
            input_port_ids=["door_crossing_in"],
            output_port_ids=["entry_result_out"],
            read_fact_ids=["secure_door.lock_state"],
            read_placement_entity_ids=["technician"],
            read_spatial_link_ids=["equipment_room_threshold"],
            write_placement_entity_ids=["technician"],
            write_carrier_ids=["entry_result_buffer"],
            substrate_refs=[
                "technician",
                "secure_door",
                "entry_result_buffer",
            ],
            invariant_ids=["crossing_valid"],
            fidelity=fidelity,
        ),
        "exact_entry_result_delivery": MechanismSpec(
            mechanism_id="exact_entry_result_delivery",
            mechanism_kind="sensor_delivery",
            implementation_id="exact_access_delivery_v1",
            description="Deliver threshold-sensor feedback to the technician.",
            input_port_ids=["technician_entry_result_in"],
            write_carrier_ids=["technician_entry_result_buffer"],
            observation_target_ids=["technician"],
            substrate_refs=["technician", "technician_entry_result_buffer"],
            invariant_ids=["delivery_valid"],
            fidelity=fidelity,
        ),
    }


def _carriers() -> dict[str, CarrierState]:
    owners = {
        "technician_badge_carrier": "technician",
        "access_policy_carrier": "written_access_policy",
        "authentication_decision_buffer": "exact_badge_authentication",
        "authorization_decision_buffer": "exact_policy_authorization",
        "access_result_buffer": "exact_latch_actuation",
        "technician_access_result_buffer": "exact_access_result_delivery",
        "entry_result_buffer": "exact_threshold_crossing",
        "technician_entry_result_buffer": "exact_entry_result_delivery",
    }
    return {
        carrier_id: CarrierState(
            carrier_id=carrier_id,
            owner_ref=owner,
            medium="physical_access_record",
            locator=f"physical_access/{carrier_id}",
            visibility=(
                "mechanism" if carrier_id == "technician_badge_carrier" else "public"
            ),
        )
        for carrier_id, owner in owners.items()
    }


def _active_spec() -> ActiveSystemSpec:
    return ActiveSystemSpec(
        active_system_id="technician",
        entity_id="technician",
        implementation_id=_technician_implementation_id(),
        description="Bounded maintenance-person decision process.",
        observation_port_ids=[
            "technician_access_result_in",
            "technician_entry_result_in",
        ],
        output_port_ids=["technician_badge_out", "technician_cross_out"],
        output_port_initial_representation_ids={
            "technician_badge_out": ["technician_badge"],
        },
        output_port_representation_sources={
            "technician_cross_out": ["technician_access_result_in"],
        },
        initial_representation_ids=["technician_badge"],
        initial_private_state={
            "memory": [
                {
                    "logical_time": 0,
                    "kind": "autobiographical_memory",
                    "content": (
                        "I accepted a maintenance technician position and was "
                        "assigned to inspect pump_7 in the equipment room."
                    ),
                },
                {
                    "logical_time": 0,
                    "kind": "belief",
                    "content": (
                        "My carried badge is normally presented at the reader, but "
                        "the reader, policy, and physical door can produce different "
                        "outcomes."
                    ),
                },
            ]
        },
    )


def _exact_bindings() -> dict[str, ExactMechanismBinding]:
    return {
        "exact_badge_authentication": ExactMechanismBinding(
            implementation_id="exact_badge_authentication_v1",
            handler=_exact_authentication,
            invariant_checkers={"authentication_valid": _authentication_valid},
        ),
        "exact_policy_authorization": ExactMechanismBinding(
            implementation_id="exact_policy_authorization_v1",
            handler=_exact_authorization,
            invariant_checkers={"authorization_valid": _authorization_valid},
        ),
        "exact_latch_actuation": ExactMechanismBinding(
            implementation_id="exact_latch_actuation_v1",
            handler=_exact_latch,
            invariant_checkers={"latch_valid": _latch_valid},
        ),
        "exact_access_result_delivery": ExactMechanismBinding(
            implementation_id="exact_access_delivery_v1",
            handler=_exact_delivery,
            invariant_checkers={"delivery_valid": _delivery_valid},
        ),
        "exact_threshold_crossing": ExactMechanismBinding(
            implementation_id="exact_threshold_crossing_v1",
            handler=_exact_crossing,
            invariant_checkers={"crossing_valid": _crossing_valid},
        ),
        "exact_entry_result_delivery": ExactMechanismBinding(
            implementation_id="exact_access_delivery_v1",
            handler=_exact_delivery,
            invariant_checkers={"delivery_valid": _delivery_valid},
        ),
    }


def _exact_authentication(context: MechanismContext) -> MechanismOutcome:
    badge = _parse_trigger(context, BADGE_ENCODING, BadgePresentation)
    authenticated = (
        badge.subject_id == "technician"
        and badge.candidate == context.read("credential_authority.badge_verifier")
    )
    status = "authenticated" if authenticated else "denied"
    decision = AuthenticationDecision(authenticated=authenticated)
    representation_id = f"authentication_decision_{context.route_event_id}"
    return MechanismOutcome(
        outcome_code=status,
        updates=[
            FactUpdate(
                fact_id="credential_authority.last_authentication",
                value=status,
            )
        ],
        representations=[
            _draft(
                representation_id,
                "authentication_decision_buffer",
                AUTHENTICATION_ENCODING,
                decision,
                "credential_authority",
                [badge_representation(context).representation_id],
            )
        ],
        effects=[
            EffectDraft(
                output_port_id="authentication_decision_out",
                effect_type="authentication_decision",
                representation_id=representation_id,
            )
        ],
    )


def _exact_authorization(context: MechanismContext) -> MechanismOutcome:
    authentication = _parse_trigger(
        context,
        AUTHENTICATION_ENCODING,
        AuthenticationDecision,
    )
    policy_representation = context.read_representation("access_policy_copy")
    _require_encoding(policy_representation, POLICY_ENCODING)
    policy = AccessPolicy.model_validate_json(policy_representation.content)
    authorized = (
        authentication.authenticated
        and authentication.subject_id in policy.allowed_subject_ids
    )
    status = (
        "authorized"
        if authorized
        else (
            "denied_authentication"
            if not authentication.authenticated
            else "denied_policy"
        )
    )
    decision = AuthorizationDecision(
        authenticated=authentication.authenticated,
        authorized=authorized,
    )
    representation_id = f"authorization_decision_{context.route_event_id}"
    return MechanismOutcome(
        outcome_code=status,
        updates=[
            FactUpdate(
                fact_id="access_controller.last_authorization",
                value=status,
            )
        ],
        representations=[
            _draft(
                representation_id,
                "authorization_decision_buffer",
                AUTHORIZATION_ENCODING,
                decision,
                "access_controller",
                [
                    badge_representation(context).representation_id,
                    policy_representation.representation_id,
                ],
            )
        ],
        effects=[
            EffectDraft(
                output_port_id="authorization_decision_out",
                effect_type="authorization_decision",
                representation_id=representation_id,
            )
        ],
    )


def _exact_latch(context: MechanismContext) -> MechanismOutcome:
    decision = _parse_trigger(
        context,
        AUTHORIZATION_ENCODING,
        AuthorizationDecision,
    )
    if not decision.authenticated:
        status: AccessStatus = "denied_authentication"
    elif not decision.authorized:
        status = "denied_authorization"
    elif context.read("secure_door.latch_operable") is not True:
        status = "denied_latch_jammed"
    else:
        status = "access_granted"
    updates = [
        FactUpdate(fact_id="secure_door.last_latch_result", value=status)
    ]
    if status == "access_granted":
        updates.append(
            FactUpdate(fact_id="secure_door.lock_state", value="unlocked")
        )
    result = AccessResult(status=status)
    representation_id = f"access_result_{context.route_event_id}"
    return MechanismOutcome(
        outcome_code=status,
        updates=updates,
        representations=[
            _draft(
                representation_id,
                "access_result_buffer",
                ACCESS_RESULT_ENCODING,
                result,
                "secure_door",
                [badge_representation(context).representation_id],
            )
        ],
        effects=[
            EffectDraft(
                output_port_id="access_result_out",
                effect_type="access_result",
                representation_id=representation_id,
            )
        ],
    )


def _exact_crossing(context: MechanismContext) -> MechanismOutcome:
    access = _parse_trigger(context, ACCESS_RESULT_ENCODING, AccessResult)
    request = CrossingRequest.model_validate(context.effect.payload)
    placement = context.read_placement("technician")
    spatial_link = context.read_spatial_link("equipment_room_threshold")
    entered = (
        access.status == "access_granted"
        and context.read("secure_door.lock_state") == "unlocked"
        and placement.place_id == spatial_link.endpoint_a_place_id
        and request.target_place_id == spatial_link.endpoint_b_place_id
    )
    status: Literal["entered", "crossing_denied"] = (
        "entered" if entered else "crossing_denied"
    )
    result = EntryResult(status=status)
    representation_id = f"entry_result_{context.route_event_id}"
    return MechanismOutcome(
        outcome_code=status,
        placement_updates=(
            [
                PlacementDraft(
                    entity_id="technician",
                    destination_place_id="equipment_room",
                    via_spatial_link_id="equipment_room_threshold",
                )
            ]
            if entered
            else []
        ),
        representations=[
            _draft(
                representation_id,
                "entry_result_buffer",
                ENTRY_RESULT_ENCODING,
                result,
                "exact_threshold_crossing",
                [badge_representation(context).representation_id],
            )
        ],
        effects=[
            EffectDraft(
                output_port_id="entry_result_out",
                effect_type="entry_result",
                representation_id=representation_id,
            )
        ],
    )


def _exact_delivery(context: MechanismContext) -> MechanismOutcome:
    source = badge_representation(context)
    carrier_id = {
        "exact_access_result_delivery": "technician_access_result_buffer",
        "exact_entry_result_delivery": "technician_entry_result_buffer",
    }[context.mechanism.mechanism_id]
    representation_id = f"delivered_{context.route_event_id}"
    return MechanismOutcome(
        outcome_code="representation_delivered",
        representations=[
            RepresentationDraft(
                representation_id=representation_id,
                carrier_id=carrier_id,
                encoding=source.encoding,
                content=source.content,
                actual_source_ref=source.actual_source_ref,
                parent_representation_ids=[source.representation_id],
            )
        ],
        observations=[
            ObservationDraft(
                target_entity_id="technician",
                via_port_id=context.target_port.port_id,
                apparent_content=source.content,
                apparent_source_ref=source.actual_source_ref,
                representation_id=representation_id,
            )
        ],
    )


def _authentication_valid(
    context: MechanismContext,
    outcome: MechanismOutcome,
) -> bool:
    try:
        badge = _parse_trigger(context, BADGE_ENCODING, BadgePresentation)
    except (TypeError, ValueError):
        return False
    expected = (
        "authenticated"
        if badge.candidate == context.read("credential_authority.badge_verifier")
        else "denied"
    )
    return (
        outcome.outcome_code == expected
        and {item.fact_id: item.value for item in outcome.updates}
        == {"credential_authority.last_authentication": expected}
        and len(outcome.representations) == 1
        and len(outcome.effects) == 1
    )


def _authorization_valid(
    context: MechanismContext,
    outcome: MechanismOutcome,
) -> bool:
    try:
        authentication = _parse_trigger(
            context,
            AUTHENTICATION_ENCODING,
            AuthenticationDecision,
        )
        policy_representation = context.read_representation("access_policy_copy")
        policy = AccessPolicy.model_validate_json(policy_representation.content)
    except (TypeError, ValueError):
        return False
    expected = (
        "authorized"
        if (
            authentication.authenticated
            and authentication.subject_id in policy.allowed_subject_ids
        )
        else (
            "denied_authentication"
            if not authentication.authenticated
            else "denied_policy"
        )
    )
    return (
        outcome.outcome_code == expected
        and {item.fact_id: item.value for item in outcome.updates}
        == {"access_controller.last_authorization": expected}
        and len(outcome.representations) == 1
        and "access_policy_copy"
        in outcome.representations[0].parent_representation_ids
    )


def _latch_valid(context: MechanismContext, outcome: MechanismOutcome) -> bool:
    try:
        decision = _parse_trigger(
            context,
            AUTHORIZATION_ENCODING,
            AuthorizationDecision,
        )
    except (TypeError, ValueError):
        return False
    expected: AccessStatus
    if not decision.authenticated:
        expected = "denied_authentication"
    elif not decision.authorized:
        expected = "denied_authorization"
    elif context.read("secure_door.latch_operable") is not True:
        expected = "denied_latch_jammed"
    else:
        expected = "access_granted"
    updates = {item.fact_id: item.value for item in outcome.updates}
    return (
        outcome.outcome_code == expected
        and updates.get("secure_door.last_latch_result") == expected
        and (
            expected != "access_granted"
            or updates.get("secure_door.lock_state") == "unlocked"
        )
        and len(outcome.representations) == 1
        and len(outcome.effects) == 1
    )


def _crossing_valid(
    context: MechanismContext,
    outcome: MechanismOutcome,
) -> bool:
    try:
        access = _parse_trigger(context, ACCESS_RESULT_ENCODING, AccessResult)
        CrossingRequest.model_validate(context.effect.payload)
    except (TypeError, ValueError):
        return False
    expected_entered = (
        access.status == "access_granted"
        and context.read("secure_door.lock_state") == "unlocked"
        and context.read_placement("technician").place_id == "hallway"
        and context.read_spatial_link("equipment_room_threshold").endpoint_b_place_id
        == "equipment_room"
    )
    placement_updates = {
        item.entity_id: (
            item.destination_place_id,
            item.via_spatial_link_id,
        )
        for item in outcome.placement_updates
    }
    return (
        outcome.outcome_code
        == ("entered" if expected_entered else "crossing_denied")
        and (
            placement_updates
            == {
                "technician": (
                    "equipment_room",
                    "equipment_room_threshold",
                )
            }
            if expected_entered
            else not placement_updates
        )
        and len(outcome.representations) == 1
        and len(outcome.effects) == 1
    )


def _delivery_valid(context: MechanismContext, outcome: MechanismOutcome) -> bool:
    try:
        source = badge_representation(context)
    except ValueError:
        return False
    return (
        outcome.outcome_code == "representation_delivered"
        and not outcome.updates
        and not outcome.effects
        and len(outcome.representations) == 1
        and len(outcome.observations) == 1
        and outcome.representations[0].content == source.content
        and outcome.observations[0].target_entity_id == "technician"
        and outcome.observations[0].representation_id
        == outcome.representations[0].representation_id
    )


def _scripted_technician(item: ActiveSystemInput) -> ActiveStepResult:
    actions: list[ActionIntent] = []
    if item.logical_time == 0:
        actions.append(
            ActionIntent(
                output_port_id="technician_badge_out",
                representation_id="technician_badge",
                payload={},
                public_summary="Technician presented the carried badge to the reader.",
            )
        )
    else:
        granted = next(
            (
                observation
                for observation in item.observations
                if _document_kind(observation.apparent_content) == "access_result"
                and AccessResult.model_validate_json(
                    observation.apparent_content
                ).status
                == "access_granted"
            ),
            None,
        )
        if granted is not None:
            actions.append(
                ActionIntent(
                    output_port_id="technician_cross_out",
                    representation_id=granted.representation_id,
                    payload=CrossingRequest().model_dump(mode="json"),
                    public_summary="Technician attempted to cross the controlled doorway.",
                )
            )
    memory = item.private_state.get("memory")
    if not isinstance(memory, list):
        raise TypeError("physical-access memory must be a list")
    return ActiveStepResult(
        proposal=ActiveProposal(
            active_system_id="technician",
            implementation_id=_technician_implementation_id(),
            private_state={
                "memory": [
                    *memory,
                    {
                        "logical_time": item.logical_time,
                        "kind": "scripted_step",
                        "content": "Technician used only carried or delivered evidence.",
                    },
                ]
            },
            actions=actions,
        )
    )


def _technician_implementation_id() -> str:
    return bound_native_llm_implementation_id(
        implementation_family_id="native_physical_technician_v1",
        persona=TECHNICIAN_PERSONA,
        model=PHYSICAL_ACCESS_MODEL,
        task=PHYSICAL_ACCESS_TASK,
        reasoning_effort=PHYSICAL_ACCESS_REASONING_EFFORT,
        max_memory_entries=16,
        max_output_tokens=768,
        decision_wire_contract="openai-json-payload-wire.v2",
    )


def _token(
    representation_id: str,
    carrier_id: str,
    encoding: str,
    model: BaseModel,
    source_ref: str,
    *,
    visibility: Literal["public", "analyst", "mechanism"] = "public",
) -> RepresentationToken:
    content = _render(model)
    return RepresentationToken(
        representation_id=representation_id,
        carrier_id=carrier_id,
        carrier_revision=0,
        encoding=encoding,
        content=content,
        content_hash=representation_digest(content),
        actual_source_ref=source_ref,
        visibility=visibility,
    )


def _draft(
    representation_id: str,
    carrier_id: str,
    encoding: str,
    model: BaseModel,
    source_ref: str,
    parents: list[str],
) -> RepresentationDraft:
    return RepresentationDraft(
        representation_id=representation_id,
        carrier_id=carrier_id,
        encoding=encoding,
        content=_render(model),
        actual_source_ref=source_ref,
        parent_representation_ids=parents,
    )


def _parse_trigger(
    context: MechanismContext,
    encoding: str,
    model: type[_StrictModelT],
) -> _StrictModelT:
    representation = badge_representation(context)
    _require_encoding(representation, encoding)
    return model.model_validate_json(representation.content)


def badge_representation(context: MechanismContext) -> RepresentationToken:
    if context.representation is None:
        raise ValueError("physical-access mechanism requires a representation")
    return context.representation


def _require_encoding(
    representation: RepresentationToken,
    encoding: str,
) -> None:
    if representation.encoding != encoding:
        raise ValueError("physical-access representation has the wrong encoding")


def _document_kind(content: str) -> str:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return "unknown"
    if not isinstance(parsed, dict):
        return "unknown"
    kind = parsed.get("document_kind")
    return kind if isinstance(kind, str) else "unknown"


def _render(model: BaseModel) -> str:
    return json.dumps(
        model.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )


def _boundary_members(state: CausalState) -> list[str]:
    return sorted(
        [
            "technician",
            "pump_7",
            "equipment_room",
            "hallway",
            "maintenance_facility",
            "secure_door",
            "written_access_policy",
            *state.ports,
            *state.mechanisms,
            *state.carriers,
            *state.representations,
        ]
    )


def _fidelity() -> FidelityNote:
    return FidelityNote(
        abstraction=(
            "Discrete badge comparison, policy lookup, latch actuation, and "
            "threshold crossing."
        ),
        assumptions=[
            "One badge, one policy copy, one controller, and one doorway are stipulated."
        ],
        known_omissions=[
            "Cryptography, tailgating, forces, continuous motion, latency, and sensor failure."
        ],
        validation_basis=[
            "Matched authorization and latch interventions, exact replay, and trace review."
        ],
    )
