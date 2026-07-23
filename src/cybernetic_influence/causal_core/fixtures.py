"""Exact production fixtures for authentication and local typed relay."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from pydantic import JsonValue

from cybernetic_influence.causal_core.engine import (
    CausalLimits,
    CausalSession,
    ExactMechanismBinding,
    MechanismContext,
)
from cybernetic_influence.causal_core.models import (
    ActionAttempt,
    AnalyticalBoundary,
    CarrierState,
    CausalRunResult,
    CausalScenario,
    CausalState,
    ConnectionState,
    ContainerState,
    EffectDraft,
    EntityState,
    FactState,
    FactUpdate,
    FidelityNote,
    MechanismOutcome,
    MechanismSpec,
    ObservationDraft,
    PortState,
    RepresentationDraft,
    RepresentationToken,
    representation_digest,
)


@dataclass(frozen=True)
class ExactFixture:
    """One scenario plus trusted versioned exact bindings and actions."""

    scenario: CausalScenario
    bindings: Mapping[str, ExactMechanismBinding]
    actions: tuple[ActionAttempt, ...]

    def new_session(
        self,
        *,
        run_id: str,
        limits: CausalLimits | None = None,
    ) -> CausalSession:
        """Create one non-default exact causal session."""
        return CausalSession(
            self.scenario,
            self.bindings,
            run_id=run_id,
            limits=limits,
        )

    def run(
        self,
        *,
        run_id: str,
        actions: Sequence[ActionAttempt] | None = None,
        limits: CausalLimits | None = None,
    ) -> CausalRunResult:
        """Run supplied or fixture actions and return the completed trajectory."""
        session = self.new_session(run_id=run_id, limits=limits)
        for action in self.actions if actions is None else actions:
            session.advance(action)
        return session.complete()


def authentication_fixture(
    *,
    candidate: str,
    verifier: str = "correct_horse_battery",
) -> ExactFixture:
    """Build one exact password-comparison fixture with a protected verifier."""
    state = CausalState(
        entities={
            "alice": EntityState(
                entity_id="alice",
                entity_kind="person",
                description="Person submitting an authentication attempt.",
            ),
            "auth_service": EntityState(
                entity_id="auth_service",
                entity_kind="service",
                description="Stateful exact authentication service.",
                attributes={
                    "verifier": FactState(
                        value=verifier,
                        visibility="mechanism",
                    ),
                    "failure_count": FactState(value=0),
                    "session_active": FactState(value=False),
                },
            ),
        },
        ports={
            "alice_auth_out": PortState(
                port_id="alice_auth_out",
                owner_ref="alice",
                direction="output",
                effect_type="credential_submission",
                description="Alice's credential-submission interface.",
            ),
            "auth_input": PortState(
                port_id="auth_input",
                owner_ref="auth_service",
                direction="input",
                effect_type="credential_submission",
                description="Authentication service input.",
            ),
        },
        connections={
            "alice_to_auth": ConnectionState(
                connection_id="alice_to_auth",
                source_port_id="alice_auth_out",
                target_port_id="auth_input",
                description="Direct credential submission path.",
            )
        },
        mechanisms={
            "exact_authentication": MechanismSpec(
                mechanism_id="exact_authentication",
                mechanism_kind="credential_comparison",
                implementation_id="exact_authentication_v1",
                description="Compare submitted candidate with protected verifier.",
                input_port_ids=["auth_input"],
                read_fact_ids=[
                    "auth_service.verifier",
                    "auth_service.failure_count",
                    "auth_service.session_active",
                ],
                write_fact_ids=[
                    "auth_service.failure_count",
                    "auth_service.session_active",
                ],
                observation_target_ids=["alice"],
                substrate_refs=["auth_service"],
                invariant_ids=["candidate_is_text", "state_types_valid"],
                fidelity=FidelityNote(
                    abstraction=(
                        "Direct exact equality against stipulated protected state."
                    ),
                    assumptions=[
                        "The submitted candidate is the complete credential.",
                        "One accepted comparison immediately activates a session.",
                    ],
                    known_omissions=[
                        "Hashing, timing, rate windows, transport security, and MFA."
                    ],
                    validation_basis=[
                        "Positive equality and negative inequality controls.",
                        "Protected-value outward-surface canary.",
                    ],
                ),
            )
        },
    )
    scenario = CausalScenario(
        scenario_id="exact_authentication",
        description="Exact model-free credential comparison.",
        initial_state=state,
        fidelity_questions=[
            "Did equality alone determine the stipulated authentication result?",
            "Did the protected verifier remain outside outward evidence surfaces?",
        ],
    )
    action = ActionAttempt(
        action_id="alice_authenticates",
        actor_entity_id="alice",
        output_port_id="alice_auth_out",
        payload={"candidate": candidate},
        public_summary="Alice submitted one candidate credential.",
    )
    return ExactFixture(
        scenario=scenario,
        bindings={
            "exact_authentication": ExactMechanismBinding(
                implementation_id="exact_authentication_v1",
                handler=exact_authentication,
                invariant_checkers={
                    "candidate_is_text": authentication_candidate_is_text,
                    "state_types_valid": authentication_state_types_valid,
                },
            )
        },
        actions=(action,),
    )


def relay_fixture(*, connection_enabled: bool = True) -> ExactFixture:
    """Build a deterministic two-mechanism local representation relay."""
    content = "The maintenance window starts at noon."
    state = CausalState(
        entities={
            "alice": EntityState(
                entity_id="alice",
                entity_kind="person",
                description="Initial representation source.",
            ),
            "relay_device": EntityState(
                entity_id="relay_device",
                entity_kind="service",
                description="Concrete local relay substrate.",
            ),
            "bob": EntityState(
                entity_id="bob",
                entity_kind="person",
                description="Configured observation recipient.",
            ),
        },
        containers={
            "room": ContainerState(
                container_id="room",
                description="Configured local routing locus.",
                member_entity_ids=["alice", "relay_device", "bob"],
            )
        },
        ports={
            "alice_message_out": PortState(
                port_id="alice_message_out",
                owner_ref="alice",
                direction="output",
                effect_type="message_signal",
                description="Alice's local message output.",
                container_id="room",
            ),
            "relay_message_in": PortState(
                port_id="relay_message_in",
                owner_ref="relay_device",
                direction="input",
                effect_type="message_signal",
                description="Relay local input.",
                container_id="room",
            ),
            "relay_message_out": PortState(
                port_id="relay_message_out",
                owner_ref="exact_relay",
                direction="output",
                effect_type="message_signal",
                description="Relay directed output.",
            ),
            "bob_message_in": PortState(
                port_id="bob_message_in",
                owner_ref="bob",
                direction="input",
                effect_type="message_signal",
                description="Bob's configured message input.",
            ),
        },
        connections={
            "relay_to_bob": ConnectionState(
                connection_id="relay_to_bob",
                source_port_id="relay_message_out",
                target_port_id="bob_message_in",
                enabled=connection_enabled,
                description="Directed relay-to-recipient route.",
            )
        },
        mechanisms={
            "exact_relay": MechanismSpec(
                mechanism_id="exact_relay",
                mechanism_kind="representation_relay",
                implementation_id="exact_relay_copy_v1",
                description="Copy one representation onto the relay output carrier.",
                input_port_ids=["relay_message_in"],
                output_port_ids=["relay_message_out"],
                write_carrier_ids=["relay_output_buffer"],
                substrate_refs=["relay_device", "relay_output_buffer"],
                invariant_ids=["representation_present", "copy_lineage_valid"],
                fidelity=FidelityNote(
                    abstraction="Exact typed forwarding at one logical time.",
                    assumptions=["Configured local adjacency is sufficient reach."],
                    known_omissions=[
                        "Physical acoustics, loss, latency, attention, and cognition."
                    ],
                    validation_basis=["Carrier revision and token-parent checks."],
                ),
            ),
            "exact_delivery": MechanismSpec(
                mechanism_id="exact_delivery",
                mechanism_kind="observation_delivery",
                implementation_id="exact_delivery_copy_v1",
                description="Copy one public representation onto Bob's input carrier.",
                input_port_ids=["bob_message_in"],
                write_carrier_ids=["bob_observation_buffer"],
                observation_target_ids=["bob"],
                substrate_refs=["bob", "bob_observation_buffer"],
                invariant_ids=["representation_present", "public_copy_valid"],
                fidelity=FidelityNote(
                    abstraction="Exact interface delivery, not epistemic uptake.",
                    assumptions=["Bob's configured input is available."],
                    known_omissions=[
                        "Attention, interpretation, memory incorporation, and belief."
                    ],
                    validation_basis=["Observation/token identity checks."],
                ),
            ),
        },
        carriers={
            "alice_note": CarrierState(
                carrier_id="alice_note",
                owner_ref="alice",
                medium="memory_record",
                locator="note_0",
            ),
            "relay_output_buffer": CarrierState(
                carrier_id="relay_output_buffer",
                owner_ref="exact_relay",
                medium="message_buffer",
                locator="relay_output_0",
            ),
            "bob_observation_buffer": CarrierState(
                carrier_id="bob_observation_buffer",
                owner_ref="exact_delivery",
                medium="observation_buffer",
                locator="bob_input_0",
            ),
        },
        representations={
            "maintenance_notice": RepresentationToken(
                representation_id="maintenance_notice",
                carrier_id="alice_note",
                carrier_revision=0,
                encoding="text/plain",
                content=content,
                content_hash=representation_digest(content),
                actual_source_ref="alice",
            )
        },
    )
    scenario = CausalScenario(
        scenario_id="exact_local_relay",
        description="Exact two-hop local routing of one public representation.",
        initial_state=state,
        analytical_boundaries=[
            AnalyticalBoundary(
                boundary_id="relay_group_view",
                label="Relay group",
                description="View-only grouping for boundary negative controls.",
                member_refs=["alice", "relay_device", "bob", "exact_relay"],
            )
        ],
        fidelity_questions=[
            "Did every hop follow configured typed adjacency?",
            "Did delivery remain distinct from attention or belief?",
        ],
    )
    action = ActionAttempt(
        action_id="alice_emits_notice",
        actor_entity_id="alice",
        output_port_id="alice_message_out",
        representation_id="maintenance_notice",
        public_summary=(
            "Alice emitted the maintenance notice into the configured room."
        ),
    )
    return ExactFixture(
        scenario=scenario,
        bindings={
            "exact_relay": ExactMechanismBinding(
                implementation_id="exact_relay_copy_v1",
                handler=exact_relay,
                invariant_checkers={
                    "representation_present": representation_present,
                    "copy_lineage_valid": relay_copy_lineage_valid,
                },
            ),
            "exact_delivery": ExactMechanismBinding(
                implementation_id="exact_delivery_copy_v1",
                handler=exact_delivery,
                invariant_checkers={
                    "representation_present": representation_present,
                    "public_copy_valid": delivery_public_copy_valid,
                },
            ),
        },
        actions=(action,),
    )


def exact_authentication(context: MechanismContext) -> MechanismOutcome:
    """Compare a candidate with protected state and emit a public result only."""
    candidate = _string(context.effect.payload.get("candidate"), "candidate")
    verifier = _string(context.read("auth_service.verifier"), "verifier")
    failure_count = _integer(
        context.read("auth_service.failure_count"), "failure_count"
    )
    _boolean(context.read("auth_service.session_active"), "session_active")
    accepted = candidate == verifier
    return MechanismOutcome(
        outcome_code="accepted" if accepted else "denied",
        updates=[
            FactUpdate(
                fact_id="auth_service.failure_count",
                value=0 if accepted else failure_count + 1,
            ),
            FactUpdate(
                fact_id="auth_service.session_active",
                value=accepted,
            ),
        ],
        observations=[
            ObservationDraft(
                target_entity_id="alice",
                via_port_id="auth_input",
                apparent_content=(
                    "Authentication accepted."
                    if accepted
                    else "Authentication denied."
                ),
                apparent_source_ref="auth_service",
            )
        ],
    )


def exact_relay(context: MechanismContext) -> MechanismOutcome:
    """Copy one incoming representation onto the relay's output carrier."""
    representation = context.representation
    if representation is None:
        raise ValueError("exact relay requires a representation")
    copied_id = f"relay_copy_{context.route_event_id}"
    return MechanismOutcome(
        outcome_code="representation_copied",
        representations=[
            RepresentationDraft(
                representation_id=copied_id,
                carrier_id="relay_output_buffer",
                encoding=representation.encoding,
                content=representation.content,
                actual_source_ref=representation.actual_source_ref,
                parent_representation_ids=[representation.representation_id],
                visibility=representation.visibility,
            )
        ],
        effects=[
            EffectDraft(
                output_port_id="relay_message_out",
                effect_type="message_signal",
                representation_id=copied_id,
            )
        ],
    )


def exact_delivery(context: MechanismContext) -> MechanismOutcome:
    """Copy one public representation onto Bob's configured input carrier."""
    representation = context.representation
    if representation is None:
        raise ValueError("exact delivery requires a representation")
    copied_id = f"bob_copy_{context.route_event_id}"
    return MechanismOutcome(
        outcome_code="observation_copied",
        representations=[
            RepresentationDraft(
                representation_id=copied_id,
                carrier_id="bob_observation_buffer",
                encoding=representation.encoding,
                content=representation.content,
                actual_source_ref=representation.actual_source_ref,
                parent_representation_ids=[representation.representation_id],
                visibility=representation.visibility,
            )
        ],
        observations=[
            ObservationDraft(
                target_entity_id="bob",
                via_port_id="bob_message_in",
                apparent_content=representation.content,
                apparent_source_ref="alice",
                representation_id=copied_id,
            )
        ],
    )


def authentication_candidate_is_text(
    context: MechanismContext,
    _outcome: MechanismOutcome,
) -> bool:
    """Independently verify the submitted candidate's stipulated type."""
    return isinstance(context.effect.payload.get("candidate"), str)


def authentication_state_types_valid(
    context: MechanismContext,
    outcome: MechanismOutcome,
) -> bool:
    """Independently verify current and proposed authentication state types."""
    verifier = context.read("auth_service.verifier")
    current_failure = context.read("auth_service.failure_count")
    current_session = context.read("auth_service.session_active")
    updates = {item.fact_id: item.value for item in outcome.updates}
    proposed_failure = updates.get("auth_service.failure_count", current_failure)
    proposed_session = updates.get("auth_service.session_active", current_session)
    return (
        isinstance(verifier, str)
        and _is_integer(current_failure)
        and isinstance(current_session, bool)
        and _is_integer(proposed_failure)
        and isinstance(proposed_session, bool)
    )


def representation_present(
    context: MechanismContext,
    _outcome: MechanismOutcome,
) -> bool:
    """Independently verify that the routed effect carried a concrete token."""
    return context.representation is not None


def relay_copy_lineage_valid(
    context: MechanismContext,
    outcome: MechanismOutcome,
) -> bool:
    """Verify the relay proposal is one faithful carrier-bound child copy."""
    incoming = context.representation
    if incoming is None or len(outcome.representations) != 1:
        return False
    copied = outcome.representations[0]
    return (
        copied.carrier_id == "relay_output_buffer"
        and copied.encoding == incoming.encoding
        and copied.content == incoming.content
        and copied.actual_source_ref == incoming.actual_source_ref
        and copied.parent_representation_ids == [incoming.representation_id]
        and copied.visibility == incoming.visibility
        and len(outcome.effects) == 1
        and outcome.effects[0].representation_id == copied.representation_id
    )


def delivery_public_copy_valid(
    context: MechanismContext,
    outcome: MechanismOutcome,
) -> bool:
    """Verify delivery proposes one public child token and matching observation."""
    incoming = context.representation
    if (
        incoming is None
        or incoming.visibility != "public"
        or len(outcome.representations) != 1
        or len(outcome.observations) != 1
    ):
        return False
    copied = outcome.representations[0]
    observation = outcome.observations[0]
    return (
        copied.carrier_id == "bob_observation_buffer"
        and copied.encoding == incoming.encoding
        and copied.content == incoming.content
        and copied.actual_source_ref == incoming.actual_source_ref
        and copied.parent_representation_ids == [incoming.representation_id]
        and copied.visibility == "public"
        and observation.representation_id == copied.representation_id
        and observation.apparent_content == copied.content
    )


def _string(value: JsonValue | None, label: str) -> str:
    """Return one strict string payload/state value."""
    if not isinstance(value, str):
        raise ValueError(f"{label} must be text")
    return value


def _integer(value: JsonValue, label: str) -> int:
    """Return one strict non-boolean integer state value."""
    if not _is_integer(value):
        raise ValueError(f"{label} must be an integer")
    assert isinstance(value, int)
    return value


def _is_integer(value: JsonValue) -> bool:
    """Return whether one JSON value is an integer but not a Boolean."""
    return isinstance(value, int) and not isinstance(value, bool)


def _boolean(value: JsonValue, label: str) -> bool:
    """Return one strict boolean state value."""
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be a boolean")
    return value
