"""Exact, locally routed, action-atomic causal session implementation."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from heapq import heapify, heappop, heappush
import json
import re
import threading
from types import MappingProxyType
from typing import Callable

from pydantic import JsonValue

from cybernetic_influence.causal_core.models import (
    ActionAttempt,
    CausalCheckpoint,
    CausalEvent,
    CausalMetrics,
    CausalRunResult,
    CausalScenario,
    CausalState,
    ScheduledWork,
    CausalStep,
    CarrierRevisionChange,
    ConnectionState,
    EffectDraft,
    EffectEnvelope,
    FactChange,
    FactState,
    InvariantResult,
    MechanismOutcome,
    MechanismSpec,
    ObservationDraft,
    ObservationRecord,
    PlacementChange,
    PlacementState,
    PortState,
    RepresentationDraft,
    RepresentationToken,
    RouteKind,
    SpatialLinkState,
    StatePatch,
    VarianceSource,
    canonical_record_digest,
    representation_digest,
    scenario_execution_fingerprint,
    scenario_fingerprint,
    state_digest,
    trace_digest,
)
from cybernetic_influence.causal_core.replay import replay_event_prefix


class CausalCoreError(RuntimeError):
    """Base class for fail-loud causal-core contract errors."""


class StateAccessViolation(CausalCoreError):
    """A handler attempted to read outside its declared state projection."""


class MechanismContractError(CausalCoreError):
    """An action or mechanism proposal exceeded its typed authority."""


class MechanismInvariantError(CausalCoreError):
    """A declared local-fidelity invariant was missing or failed."""


class PropagationBudgetExceeded(CausalCoreError):
    """Declared effect or zero-time propagation limits were exceeded."""


@dataclass(frozen=True)
class CausalLimits:
    """Fail-loud propagation guards that never silently prune work."""

    max_effects: int = 10_000
    max_zero_time_depth: int = 64

    def __post_init__(self) -> None:
        """Reject nonsensical limits at construction."""
        if self.max_effects < 1:
            raise ValueError("max_effects must be positive")
        if self.max_zero_time_depth < 0:
            raise ValueError("max_zero_time_depth must be non-negative")


class MechanismContext:
    """One exact handler's trigger and defensive declared-state projection."""

    def __init__(
        self,
        *,
        mechanism: MechanismSpec,
        allowed_facts: Mapping[str, FactState],
        allowed_representations: Mapping[str, RepresentationToken],
        allowed_placements: Mapping[str, PlacementState],
        allowed_spatial_links: Mapping[str, SpatialLinkState],
        effect: EffectEnvelope,
        target_port: PortState,
        representation: RepresentationToken | None,
        route_event_id: str,
    ) -> None:
        self.mechanism = mechanism.model_copy(deep=True)
        self.effect = effect.model_copy(deep=True)
        self.target_port = target_port.model_copy(deep=True)
        self.route_event_id = route_event_id
        self.representation = (
            representation.model_copy(deep=True)
            if representation is not None
            else None
        )
        self._allowed_facts = {
            fact_id: fact.model_copy(deep=True)
            for fact_id, fact in allowed_facts.items()
        }
        self._allowed_representations = {
            representation_id: representation.model_copy(deep=True)
            for representation_id, representation in allowed_representations.items()
        }
        self._allowed_placements = {
            entity_id: placement.model_copy(deep=True)
            for entity_id, placement in allowed_placements.items()
        }
        self._allowed_spatial_links = {
            spatial_link_id: spatial_link.model_copy(deep=True)
            for spatial_link_id, spatial_link in allowed_spatial_links.items()
        }

    def read(self, fact_id: str) -> JsonValue:
        """Return one declared fact or reject the undeclared read."""
        fact = self._allowed_facts.get(fact_id)
        if fact is None:
            raise StateAccessViolation(
                f"mechanism {self.mechanism.mechanism_id!r} attempted "
                f"undeclared read of {fact_id!r}"
            )
        return deepcopy(fact.value)

    def read_representation(self, representation_id: str) -> RepresentationToken:
        """Return one declared stored representation or reject a global read."""
        representation = self._allowed_representations.get(representation_id)
        if representation is None:
            raise StateAccessViolation(
                f"mechanism {self.mechanism.mechanism_id!r} attempted "
                f"undeclared representation read of {representation_id!r}"
            )
        return representation.model_copy(deep=True)

    def read_placement(self, entity_id: str) -> PlacementState:
        """Return one declared current placement or reject a global lookup."""
        placement = self._allowed_placements.get(entity_id)
        if placement is None:
            raise StateAccessViolation(
                f"mechanism {self.mechanism.mechanism_id!r} attempted "
                f"undeclared placement read of {entity_id!r}"
            )
        return placement.model_copy(deep=True)

    def read_spatial_link(self, spatial_link_id: str) -> SpatialLinkState:
        """Return one declared topological link without inferring access."""
        spatial_link = self._allowed_spatial_links.get(spatial_link_id)
        if spatial_link is None:
            raise StateAccessViolation(
                f"mechanism {self.mechanism.mechanism_id!r} attempted "
                f"undeclared spatial-link read of {spatial_link_id!r}"
            )
        return spatial_link.model_copy(deep=True)

    def defensive_copy(self) -> "MechanismContext":
        """Return fresh checker input isolated from handler/checker mutation."""
        return MechanismContext(
            mechanism=self.mechanism,
            allowed_facts=self._allowed_facts,
            allowed_representations=self._allowed_representations,
            allowed_placements=self._allowed_placements,
            allowed_spatial_links=self._allowed_spatial_links,
            effect=self.effect,
            target_port=self.target_port,
            representation=self.representation,
            route_event_id=self.route_event_id,
        )

MechanismHandler = Callable[[MechanismContext], MechanismOutcome]
InvariantChecker = Callable[[MechanismContext, MechanismOutcome], bool]


@dataclass(frozen=True)
class ExactMechanismBinding:
    """Trusted versioned exact code plus independently invoked checkers."""

    implementation_id: str
    handler: MechanismHandler
    invariant_checkers: Mapping[str, InvariantChecker]

    def __post_init__(self) -> None:
        """Reject malformed implementation and checker identifiers early."""
        if re.fullmatch(r"[a-z][a-z0-9_]*", self.implementation_id) is None:
            raise ValueError(
                f"invalid exact implementation id {self.implementation_id!r}"
            )
        for invariant_id in self.invariant_checkers:
            if re.fullmatch(r"[a-z][a-z0-9_]*", invariant_id) is None:
                raise ValueError(f"invalid invariant checker id {invariant_id!r}")
        object.__setattr__(
            self,
            "invariant_checkers",
            MappingProxyType(dict(self.invariant_checkers)),
        )


@dataclass(frozen=True)
class _RouteCandidate:
    """One concrete authored route; parallel paths remain distinct."""

    route_kind: RouteKind
    target_port_id: str
    route_delay: int
    connection_id: str | None = None
    container_id: str | None = None


@dataclass(frozen=True)
class _RoutedDelivery:
    """One effect scheduled to arrive at one compatible input port."""

    effect: EffectEnvelope
    route: _RouteCandidate


_QueuedWork = EffectEnvelope | _RoutedDelivery


@dataclass
class _SessionSnapshot:
    """Complete private rollback surface at one quiescent action boundary."""

    state: CausalState
    events: list[CausalEvent]
    metrics: CausalMetrics
    queue: list[tuple[int, int, _QueuedWork]]
    accepted_action_ids: list[str]
    event_sequence: int
    effect_sequence: int
    observation_sequence: int
    queue_sequence: int


class CausalSession:
    """Thread-safe exact causal session with atomic action advancement."""

    def __init__(
        self,
        scenario: CausalScenario,
        bindings: Mapping[str, ExactMechanismBinding],
        *,
        run_id: str,
        limits: CausalLimits | None = None,
    ) -> None:
        self._scenario = CausalScenario.model_validate(
            scenario.model_dump(mode="json")
        )
        if re.fullmatch(r"[a-z][a-z0-9_]*", run_id) is None:
            raise ValueError(f"invalid run id {run_id!r}")
        self._bindings = dict(bindings)
        self._run_id = run_id
        self._limits = limits or CausalLimits()
        self._state = CausalState.model_validate(
            self._scenario.initial_state.model_dump(mode="json")
        )
        self._events: list[CausalEvent] = []
        self._metrics = CausalMetrics()
        self._queue: list[tuple[int, int, _QueuedWork]] = []
        self._accepted_action_ids: list[str] = []
        self._event_sequence = 0
        self._effect_sequence = 0
        self._observation_sequence = len(self._state.observations)
        self._queue_sequence = 0
        self._terminal = False
        self._lock = threading.RLock()
        self._input_bindings: dict[str, str] = {}
        self._container_inputs: dict[tuple[str, str], list[str]] = {}
        self._connections_by_source: dict[str, list[ConnectionState]] = {}
        self._known_event_ids: set[str] = set()
        self._build_indexes()
        self._validate_binding_registry()
        self._append_event(
            event_kind="run_started",
            logical_time=0,
            summary=f"Started exact causal run {run_id} for {scenario.scenario_id}.",
            details={
                "scenario_id": scenario.scenario_id,
                "runtime_contract": scenario.runtime_contract,
                "time_unit": scenario.time_unit,
                "scenario_execution_fingerprint": scenario_execution_fingerprint(
                    self._scenario
                ),
                "max_effects": self._limits.max_effects,
                "max_zero_time_depth": self._limits.max_zero_time_depth,
                "timing_contract": scenario.timing_contract,
                "minimum_world_duration": scenario.minimum_world_duration,
            },
        )

    @property
    def state(self) -> CausalState:
        """Return a defensive validated copy of canonical state."""
        with self._lock:
            return CausalState.model_validate(self._state.model_dump(mode="json"))

    @property
    def events(self) -> list[CausalEvent]:
        """Return defensive copies of committed canonical events."""
        with self._lock:
            return [event.model_copy(deep=True) for event in self._events]

    @property
    def metrics(self) -> CausalMetrics:
        """Return defensive exact-execution accounting."""
        with self._lock:
            return self._metrics.model_copy(deep=True)

    def advance(
        self,
        action: ActionAttempt,
        *,
        drain_through: int | None = None,
    ) -> CausalStep:
        """Commit one action and drain only work due at the selected horizon.

        The default preserves the historical fully-drained action behavior.
        Active runtimes pass the action timestamp, retaining later work for the
        global scheduler and checkpoint rather than prematurely realizing it.
        """
        with self._lock:
            if self._terminal:
                raise RuntimeError("causal session is already terminal")
            validated_action = ActionAttempt.model_validate(
                action.model_dump(mode="json")
            )
            self._validate_action(validated_action)
            snapshot = self._snapshot()
            event_start = len(self._events)
            observation_ids = set(self._state.observations)
            try:
                self._accept_action(validated_action)
                self._drain_queue(through=drain_through)
                self._accepted_action_ids.append(validated_action.action_id)
            except Exception:
                self._restore_snapshot(snapshot)
                raise
            state = self.state
            return CausalStep(
                action_id=validated_action.action_id,
                events=[
                    event.model_copy(deep=True)
                    for event in self._events[event_start:]
                ],
                observations=[
                    observation.model_copy(deep=True)
                    for observation_id, observation in state.observations.items()
                    if observation_id not in observation_ids
                ],
                state=state,
            )

    @property
    def next_pending_time(self) -> int | None:
        """Return the earliest retained exact work time without consuming it."""
        with self._lock:
            return self._queue[0][0] if self._queue else None

    def advance_due(
        self,
        logical_time: int,
        *,
        event_time_limit: int | None = None,
    ) -> list[CausalEvent]:
        """Commit exact work due through one scheduler horizon.

        This operation has no actor proposal.  Its events remain exact causal
        evidence and any delivered observations become eligible only after it
        returns.
        """
        with self._lock:
            if self._terminal:
                raise RuntimeError("causal session is already terminal")
            if logical_time < self._state.logical_time:
                raise ValueError("due-work logical time regresses")
            snapshot = self._snapshot()
            event_start = len(self._events)
            try:
                self._drain_queue(through=logical_time)
                if event_time_limit is not None and any(
                    event.logical_time > event_time_limit
                    for event in self._events[event_start:]
                ):
                    self._restore_snapshot(snapshot)
                    return []
            except Exception:
                self._restore_snapshot(snapshot)
                raise
            return [
                event.model_copy(deep=True)
                for event in self._events[event_start:]
            ]

    def checkpoint(self) -> CausalCheckpoint:
        """Return a validating quiescent checkpoint for future continuation."""
        with self._lock:
            if self._terminal:
                raise RuntimeError("terminal causal sessions cannot be checkpointed")
            events = self.events
            return CausalCheckpoint.model_validate(
                _with_record_digest(
                    {
                        "runtime_contract": "causal-core.v2",
                        "schema_version": 2,
                        "scenario_id": self._scenario.scenario_id,
                        "scenario_fingerprint": scenario_fingerprint(
                            self._scenario
                        ),
                        "scenario_execution_fingerprint": (
                            scenario_execution_fingerprint(self._scenario)
                        ),
                        "run_id": self._run_id,
                        "time_unit": self._scenario.time_unit,
                        "max_effects": self._limits.max_effects,
                        "max_zero_time_depth": self._limits.max_zero_time_depth,
                        "state": self.state.model_dump(mode="json"),
                        "state_digest": state_digest(self._state),
                        "events": [
                            event.model_dump(mode="json") for event in events
                        ],
                        "event_tail_digest": trace_digest(events),
                        "metrics": self.metrics.model_dump(mode="json"),
                        "accepted_action_ids": list(self._accepted_action_ids),
                        "event_sequence": self._event_sequence,
                        "effect_sequence": self._effect_sequence,
                        "observation_sequence": self._observation_sequence,
                        "queue_sequence": self._queue_sequence,
                        "scheduled_work": [
                            item.model_dump(mode="json")
                            for item in self._serialize_queue()
                        ],
                    }
                )
            )

    @classmethod
    def restore(
        cls,
        scenario: CausalScenario,
        bindings: Mapping[str, ExactMechanismBinding],
        checkpoint: CausalCheckpoint,
    ) -> "CausalSession":
        """Restore only a strictly matching, nonterminal, quiescent checkpoint."""
        validated = CausalCheckpoint.model_validate(
            checkpoint.model_dump(mode="json")
        )
        if validated.scenario_id != scenario.scenario_id:
            raise ValueError("checkpoint scenario id does not match")
        if validated.time_unit != scenario.time_unit:
            raise ValueError("checkpoint scenario time unit does not match")
        if (
            validated.scenario_execution_fingerprint
            != scenario_execution_fingerprint(scenario)
        ):
            raise ValueError("checkpoint scenario execution fingerprint does not match")
        reconstructed = replay_event_prefix(scenario.initial_state, validated.events)
        if reconstructed != validated.state:
            raise ValueError("checkpoint state does not match its committed patches")
        session = cls.__new__(cls)
        session._scenario = CausalScenario.model_validate(
            scenario.model_dump(mode="json")
        )
        session._bindings = dict(bindings)
        session._run_id = validated.run_id
        session._limits = CausalLimits(
            max_effects=validated.max_effects,
            max_zero_time_depth=validated.max_zero_time_depth,
        )
        session._state = validated.state.model_copy(deep=True)
        session._events = [event.model_copy(deep=True) for event in validated.events]
        session._metrics = validated.metrics.model_copy(deep=True)
        session._queue = []
        session._accepted_action_ids = list(validated.accepted_action_ids)
        session._event_sequence = validated.event_sequence
        session._effect_sequence = validated.effect_sequence
        session._observation_sequence = validated.observation_sequence
        session._queue_sequence = validated.queue_sequence
        session._terminal = False
        session._lock = threading.RLock()
        session._input_bindings = {}
        session._container_inputs = {}
        session._connections_by_source = {}
        session._known_event_ids = {event.event_id for event in session._events}
        session._build_indexes()
        session._validate_binding_registry()
        session._validate_scheduled_work_topology(validated.scheduled_work)
        session._queue = session._deserialize_queue(validated.scheduled_work)
        return session

    def complete(self) -> CausalRunResult:
        """Append the terminal event and return one self-validating exact result."""
        with self._lock:
            if self._terminal:
                raise RuntimeError("causal session is already terminal")
            if self._queue:
                raise RuntimeError("cannot complete with pending effects")
            snapshot = self._snapshot()
            try:
                parent = [self._events[-1].event_id]
                self._append_event(
                    event_kind="run_completed",
                    logical_time=self._current_logical_time(),
                    causal_parent_event_ids=parent,
                    summary=(
                        f"Completed {self._scenario.scenario_id}: "
                        f"{self._metrics.mechanism_executions} exact mechanism "
                        f"execution(s), {self._metrics.observations_delivered} "
                        "observation(s), zero random samples, and zero model calls."
                    ),
                    details={"status": "completed"},
                )
                events = self.events
                final_state = self.state
                result = CausalRunResult.model_validate(
                    _with_record_digest(
                        {
                            "runtime_contract": "causal-core.v2",
                            "schema_version": 2,
                            "run_id": self._run_id,
                            "scenario_id": self._scenario.scenario_id,
                            "scenario_fingerprint": scenario_fingerprint(
                                self._scenario
                            ),
                            "scenario_execution_fingerprint": (
                                scenario_execution_fingerprint(self._scenario)
                            ),
                            "max_effects": self._limits.max_effects,
                            "max_zero_time_depth": (
                                self._limits.max_zero_time_depth
                            ),
                            "status": "completed",
                            "time_unit": self._scenario.time_unit,
                            "initial_state_digest": state_digest(
                                self._scenario.initial_state
                            ),
                            "final_state_digest": state_digest(final_state),
                            "event_tail_digest": trace_digest(events),
                            "final_state": final_state.model_dump(mode="json"),
                            "events": [
                                event.model_dump(mode="json") for event in events
                            ],
                            "metrics": self.metrics.model_dump(mode="json"),
                            "accepted_action_ids": list(
                                self._accepted_action_ids
                            ),
                            "outcome_summary": (
                                f"completed: {len(final_state.observations)} "
                                f"observation(s), {self._metrics.effects_emitted} "
                                "effect(s), trusted exact bindings"
                            ),
                        }
                    )
                )
            except Exception:
                self._restore_snapshot(snapshot)
                raise
            self._terminal = True
            return result

    def discard_pending_effects(self, *, reason: str) -> list[CausalEvent]:
        """Close an intentionally bounded run without pretending future work occurred.

        Pending effects become explicit dissipation events before the caller
        appends the ordinary terminal record. This is deliberately narrow: a
        partially delivered fan-out cannot be compressed into a dissipation
        without changing the causal contract, so it fails loudly instead.
        """
        with self._lock:
            if self._terminal:
                raise RuntimeError("causal session is already terminal")
            existing_routed = {
                event.effect_id
                for event in self._events
                if event.event_kind == "effect_routed" and event.effect_id is not None
            }
            pending = [work for _, _, work in sorted(self._queue)]
            pending_effect_ids = {
                (work if isinstance(work, EffectEnvelope) else work.effect).effect_id
                for work in pending
            }
            if existing_routed & pending_effect_ids:
                raise RuntimeError(
                    "cannot stop with a partially delivered fan-out; retain a checkpoint instead"
                )
            events: list[CausalEvent] = []
            for work in pending:
                effect = work if isinstance(work, EffectEnvelope) else work.effect
                if isinstance(work, EffectEnvelope):
                    self._metrics.effects_processed += 1
                events.append(
                    self._append_event(
                        event_kind="effect_dissipated",
                        logical_time=effect.logical_time,
                        causal_parent_event_ids=effect.causal_parent_event_ids,
                        summary=(
                            f"Effect {effect.effect_id} did not execute because the run "
                            f"ended at a configured boundary: {reason}."
                        ),
                        variance_source=self._effect_variance(effect),
                        effect_id=effect.effect_id,
                        source_port_id=effect.source_port_id,
                        representation_id=effect.representation_id,
                        details={"completion_boundary": reason},
                    )
                )
                self._metrics.dissipated_effects += 1
            self._queue = []
            return events

    def _validate_action(self, action: ActionAttempt) -> None:
        """Validate the full attempt surface without mutating the session."""
        if action.action_id in self._accepted_action_ids:
            raise MechanismContractError(
                f"duplicate action id {action.action_id!r}"
            )
        # In a positive-duration scenario a frozen activation set can enqueue
        # several later effects.  Those queued trace events must not make a
        # sibling action at the same activation time look like time travel.
        current_time = (
            self._state.logical_time
            if self._positive_duration
            else self._current_logical_time()
        )
        if action.logical_time < current_time:
            raise MechanismContractError(
                f"action {action.action_id!r} regresses logical time"
            )
        if action.actor_entity_id not in self._state.entities:
            raise MechanismContractError(
                f"action {action.action_id!r} has unknown actor"
            )
        port = self._state.ports.get(action.output_port_id)
        if port is None or port.direction != "output":
            raise MechanismContractError(
                f"action {action.action_id!r} references missing/non-output port"
            )
        if port.owner_ref != action.actor_entity_id:
            raise MechanismContractError(
                f"action {action.action_id!r} uses output not owned by actor"
            )
        if (
            action.representation_id is not None
            and action.representation_id not in self._state.representations
        ):
            raise MechanismContractError(
                f"action {action.action_id!r} references unknown representation"
            )

    def _accept_action(self, action: ActionAttempt) -> None:
        """Trace one validated attempt and enqueue its first typed effect."""
        port = self._state.ports[action.output_port_id]
        parent = [self._events[-1].event_id]
        action_event = self._append_event(
            event_kind="action_attempted",
            logical_time=action.logical_time,
            causal_parent_event_ids=parent,
            summary=action.public_summary,
            variance_source="external_action",
            action_id=action.action_id,
            actor_entity_id=action.actor_entity_id,
            source_port_id=action.output_port_id,
            representation_id=action.representation_id,
        )
        self._enqueue_effect(
            source_port_id=action.output_port_id,
            effect_type=port.effect_type,
            representation_id=action.representation_id,
            payload=action.payload,
            logical_time=action.logical_time,
            zero_time_depth=0,
            parent_event_id=action_event.event_id,
            variance_source="external_action",
        )

    def _drain_queue(self, *, through: int | None = None) -> None:
        """Process exact work in order, retaining items after ``through``."""
        while self._queue and (through is None or self._queue[0][0] <= through):
            _, _, work = heappop(self._queue)
            if isinstance(work, EffectEnvelope):
                self._metrics.effects_processed += 1
                self._metrics.maximum_zero_time_depth = max(
                    self._metrics.maximum_zero_time_depth,
                    work.zero_time_depth,
                )
                self._route_effect(work)
            else:
                self._deliver_effect(work)

    def _route_effect(self, effect: EffectEnvelope) -> None:
        """Enumerate only explicit connection and container-local candidates."""
        source = self._state.ports[effect.source_port_id]
        routes: list[_RouteCandidate] = []
        if source.container_id is not None:
            for port_id in self._container_inputs.get(
                (source.container_id, effect.effect_type), []
            ):
                routes.append(
                    _RouteCandidate(
                        route_kind="container",
                        target_port_id=port_id,
                        route_delay=0,
                        container_id=source.container_id,
                    )
                )
        for connection in self._connections_by_source.get(source.port_id, []):
            if connection.enabled:
                routes.append(
                    _RouteCandidate(
                        route_kind="connection",
                        target_port_id=connection.target_port_id,
                        route_delay=connection.delay,
                        connection_id=connection.connection_id,
                    )
                )

        self._metrics.candidates_considered += len(routes)
        self._metrics.maximum_fanout = max(
            self._metrics.maximum_fanout, len(routes)
        )
        if not routes:
            self._append_event(
                event_kind="effect_dissipated",
                logical_time=effect.logical_time,
                causal_parent_event_ids=effect.causal_parent_event_ids,
                summary=(
                    f"Effect {effect.effect_id} dissipated: no compatible adjacent "
                    "input port was enabled."
                ),
                variance_source=self._effect_variance(effect),
                effect_id=effect.effect_id,
                source_port_id=effect.source_port_id,
                representation_id=effect.representation_id,
            )
            self._metrics.dissipated_effects += 1
            return

        for route in sorted(
            routes,
            key=lambda item: (
                item.route_delay,
                item.target_port_id,
                item.route_kind,
                item.connection_id or item.container_id or "",
            ),
        ):
            routed_effect = effect.model_copy(
                update={
                    "logical_time": effect.logical_time + route.route_delay,
                    "zero_time_depth": (
                        effect.zero_time_depth if route.route_delay == 0 else 0
                    ),
                },
                deep=True,
            )
            self._push_work(
                _RoutedDelivery(
                    effect=routed_effect,
                    route=route,
                )
            )

    def _deliver_effect(self, delivery: _RoutedDelivery) -> None:
        """Trace and execute one scheduled typed arrival."""
        effect = delivery.effect
        target = self._state.ports[delivery.route.target_port_id]
        if target.effect_type != effect.effect_type:
            raise MechanismContractError("router selected incompatible effect type")
        routed_event = self._append_event(
            event_kind="effect_routed",
            logical_time=effect.logical_time,
            causal_parent_event_ids=effect.causal_parent_event_ids,
            summary=(
                f"Routed {effect.effect_type} from {effect.source_port_id} "
                f"to {delivery.route.target_port_id} through "
                f"{delivery.route.route_kind} "
                f"{delivery.route.connection_id or delivery.route.container_id}."
            ),
            variance_source=self._effect_variance(effect),
            effect_id=effect.effect_id,
            source_port_id=effect.source_port_id,
            target_port_id=delivery.route.target_port_id,
            route_kind=delivery.route.route_kind,
            connection_id=delivery.route.connection_id,
            container_id=delivery.route.container_id,
            representation_id=effect.representation_id,
            details={"route_delay": delivery.route.route_delay},
        )
        self._metrics.routed_deliveries += 1
        self._execute_mechanism(effect, target, routed_event)

    def _execute_mechanism(
        self,
        effect: EffectEnvelope,
        target_port: PortState,
        routed_event: CausalEvent,
    ) -> None:
        """Run, validate, and atomically commit one exact mechanism outcome."""
        mechanism_id = self._input_bindings[target_port.port_id]
        mechanism = self._state.mechanisms[mechanism_id]
        context = MechanismContext(
            mechanism=mechanism,
            allowed_facts={
                fact_id: self._state.fact(fact_id)
                for fact_id in mechanism.read_fact_ids
            },
            allowed_representations={
                representation_id: self._state.representations[representation_id]
                for representation_id in mechanism.read_representation_ids
            },
            allowed_placements={
                entity_id: self._state.placements[entity_id]
                for entity_id in mechanism.read_placement_entity_ids
            },
            allowed_spatial_links={
                spatial_link_id: self._state.spatial_links[spatial_link_id]
                for spatial_link_id in mechanism.read_spatial_link_ids
            },
            effect=effect,
            target_port=target_port,
            representation=(
                self._state.representations.get(effect.representation_id)
                if effect.representation_id is not None
                else None
            ),
            route_event_id=routed_event.event_id,
        )
        binding = self._bindings[mechanism_id]
        raw_outcome = binding.handler(context)
        outcome = MechanismOutcome.model_validate(
            raw_outcome.model_dump(mode="json")
        )
        self._validate_outcome(mechanism, target_port, effect, outcome)
        checker_context = MechanismContext(
            mechanism=mechanism,
            allowed_facts={
                fact_id: self._state.fact(fact_id)
                for fact_id in mechanism.read_fact_ids
            },
            allowed_representations={
                representation_id: self._state.representations[representation_id]
                for representation_id in mechanism.read_representation_ids
            },
            allowed_placements={
                entity_id: self._state.placements[entity_id]
                for entity_id in mechanism.read_placement_entity_ids
            },
            allowed_spatial_links={
                spatial_link_id: self._state.spatial_links[spatial_link_id]
                for spatial_link_id in mechanism.read_spatial_link_ids
            },
            effect=effect,
            target_port=target_port,
            representation=(
                self._state.representations.get(effect.representation_id)
                if effect.representation_id is not None
                else None
            ),
            route_event_id=routed_event.event_id,
        )
        invariants = self._evaluate_invariants(
            binding,
            checker_context,
            outcome,
        )
        mechanism_event = self._append_event(
            event_kind="mechanism_executed",
            logical_time=effect.logical_time,
            causal_parent_event_ids=[routed_event.event_id],
            summary=(
                f"Mechanism {mechanism.mechanism_id} produced outcome "
                f"{outcome.outcome_code}."
            ),
            variance_source="exact",
            mechanism_id=mechanism.mechanism_id,
            effect_id=effect.effect_id,
            target_port_id=target_port.port_id,
            representation_id=effect.representation_id,
            read_fact_ids=list(mechanism.read_fact_ids),
            read_representation_ids=list(mechanism.read_representation_ids),
            read_placement_entity_ids=list(
                mechanism.read_placement_entity_ids
            ),
            read_spatial_link_ids=list(mechanism.read_spatial_link_ids),
            invariants=invariants,
        )
        commit_time = self._next_positive_time(
            requested=effect.logical_time,
            parent_event_id=mechanism_event.event_id,
        )
        observation_time = (
            commit_time + self._scenario.minimum_world_duration
            if self._positive_duration
            else commit_time
        )
        patch, new_state = self._build_patch(
            mechanism,
            target_port,
            outcome,
            logical_time=commit_time,
            observation_logical_time=observation_time,
            parent_event_id=mechanism_event.event_id,
        )
        self._state = new_state
        commit_event = self._append_event(
            event_kind="state_committed",
            logical_time=commit_time,
            causal_parent_event_ids=[mechanism_event.event_id],
            summary=(
                f"Committed mechanism {mechanism.mechanism_id} as state "
                f"revision {patch.after_revision}."
            ),
            variance_source="exact",
            mechanism_id=mechanism.mechanism_id,
            effect_id=effect.effect_id,
            target_port_id=target_port.port_id,
            patch=patch,
        )
        self._metrics.mechanism_executions += 1
        self._metrics.state_commits += 1

        for observation in patch.observations_added:
            self._append_event(
                event_kind="observation_delivered",
                logical_time=observation.logical_time,
                causal_parent_event_ids=[commit_event.event_id],
                summary=(
                    f"Delivered an observation to {observation.target_entity_id} "
                    f"through {observation.via_port_id}: "
                    f"{observation.apparent_content}"
                ),
                variance_source="exact",
                mechanism_id=mechanism.mechanism_id,
                target_port_id=observation.via_port_id,
                representation_id=observation.representation_id,
                observation_id=observation.observation_id,
            )
            self._metrics.observations_delivered += 1

        for draft in outcome.effects:
            self._enqueue_effect(
                source_port_id=draft.output_port_id,
                effect_type=draft.effect_type,
                representation_id=draft.representation_id,
                payload=draft.payload,
                logical_time=effect.logical_time + draft.delay,
                zero_time_depth=(
                    effect.zero_time_depth + 1 if draft.delay == 0 else 0
                ),
                parent_event_id=commit_event.event_id,
                variance_source="exact",
            )

    def _validate_outcome(
        self,
        mechanism: MechanismSpec,
        target_port: PortState,
        effect: EffectEnvelope,
        outcome: MechanismOutcome,
    ) -> None:
        """Enforce writes, carrier authority, outputs, and observations."""
        update_ids = [update.fact_id for update in outcome.updates]
        if len(update_ids) != len(set(update_ids)):
            raise MechanismContractError(
                f"{mechanism.mechanism_id}: duplicate fact updates"
            )
        undeclared_updates = set(update_ids) - set(mechanism.write_fact_ids)
        if undeclared_updates:
            raise MechanismContractError(
                f"{mechanism.mechanism_id}: undeclared writes "
                f"{sorted(undeclared_updates)!r}"
            )
        for update in outcome.updates:
            self._state.fact(update.fact_id)

        placement_entity_ids = [
            update.entity_id for update in outcome.placement_updates
        ]
        if len(placement_entity_ids) != len(set(placement_entity_ids)):
            raise MechanismContractError(
                f"{mechanism.mechanism_id}: duplicate placement updates"
            )
        undeclared_placement_updates = (
            set(placement_entity_ids)
            - set(mechanism.write_placement_entity_ids)
        )
        if undeclared_placement_updates:
            raise MechanismContractError(
                f"{mechanism.mechanism_id}: undeclared placement writes "
                f"{sorted(undeclared_placement_updates)!r}"
            )
        for placement_update in outcome.placement_updates:
            placement = self._state.placements.get(placement_update.entity_id)
            if placement is None:
                raise MechanismContractError(
                    f"{mechanism.mechanism_id}: unknown placement entity "
                    f"{placement_update.entity_id!r}"
                )
            if placement.place_id == placement_update.destination_place_id:
                raise MechanismContractError(
                    f"{mechanism.mechanism_id}: placement update is a no-op for "
                    f"{placement_update.entity_id!r}"
                )
            if placement_update.destination_place_id not in self._state.places:
                raise MechanismContractError(
                    f"{mechanism.mechanism_id}: unknown placement destination "
                    f"{placement_update.destination_place_id!r}"
                )
            if (
                placement_update.via_spatial_link_id
                not in mechanism.read_spatial_link_ids
            ):
                raise MechanismContractError(
                    f"{mechanism.mechanism_id}: undeclared spatial link "
                    f"{placement_update.via_spatial_link_id!r}"
                )
            spatial_link = self._state.spatial_links[
                placement_update.via_spatial_link_id
            ]
            if {
                placement.place_id,
                placement_update.destination_place_id,
            } != {
                spatial_link.endpoint_a_place_id,
                spatial_link.endpoint_b_place_id,
            }:
                raise MechanismContractError(
                    f"{mechanism.mechanism_id}: placement update does not cross "
                    "the declared spatial link "
                    f"{placement_update.via_spatial_link_id!r}"
                )

        representation_ids = [
            draft.representation_id for draft in outcome.representations
        ]
        carrier_ids = [draft.carrier_id for draft in outcome.representations]
        if len(representation_ids) != len(set(representation_ids)):
            raise MechanismContractError(
                f"{mechanism.mechanism_id}: duplicate representation ids"
            )
        if len(carrier_ids) != len(set(carrier_ids)):
            raise MechanismContractError(
                f"{mechanism.mechanism_id}: multiple writes to one carrier"
            )
        collisions = set(representation_ids) & set(self._state.representations)
        if collisions:
            raise MechanismContractError(
                f"{mechanism.mechanism_id}: representation ids already exist "
                f"{sorted(collisions)!r}"
            )
        undeclared_carriers = set(carrier_ids) - set(mechanism.write_carrier_ids)
        if undeclared_carriers:
            raise MechanismContractError(
                f"{mechanism.mechanism_id}: undeclared carrier writes "
                f"{sorted(undeclared_carriers)!r}"
            )
        known_sources = set(self._state.entities) | set(self._state.mechanisms)
        existing_representations = set(self._state.representations)
        for draft in outcome.representations:
            if draft.actual_source_ref not in known_sources:
                raise MechanismContractError(
                    f"{mechanism.mechanism_id}: unknown representation source"
                )
            unknown_parents = (
                set(draft.parent_representation_ids) - existing_representations
            )
            if unknown_parents:
                raise MechanismContractError(
                    f"{mechanism.mechanism_id}: unknown representation parents "
                    f"{sorted(unknown_parents)!r}"
                )
            if (
                effect.representation_id is not None
                and effect.representation_id
                not in draft.parent_representation_ids
            ):
                raise MechanismContractError(
                    f"{mechanism.mechanism_id}: copied representation must name "
                    "the triggering token as a parent"
                )

        proposed_by_id = {
            draft.representation_id: draft for draft in outcome.representations
        }
        available_representations = existing_representations | set(proposed_by_id)

        for effect_draft in outcome.effects:
            if effect_draft.output_port_id not in mechanism.output_port_ids:
                raise MechanismContractError(
                    f"{mechanism.mechanism_id}: undeclared output port"
                )
            port = self._state.ports[effect_draft.output_port_id]
            if port.owner_ref != mechanism.mechanism_id:
                raise MechanismContractError(
                    f"{mechanism.mechanism_id}: output port has wrong owner"
                )
            if port.effect_type != effect_draft.effect_type:
                raise MechanismContractError(
                    f"{mechanism.mechanism_id}: output effect type mismatch"
                )
            if (
                effect_draft.representation_id is not None
                and effect_draft.representation_id not in available_representations
            ):
                raise MechanismContractError(
                    f"{mechanism.mechanism_id}: unknown output representation"
                )
            if (
                effect_draft.representation_id is not None
                and effect_draft.representation_id not in proposed_by_id
                and effect_draft.representation_id != effect.representation_id
            ):
                raise MechanismContractError(
                    f"{mechanism.mechanism_id}: output representation was not "
                    "available on the triggering effect"
                )

        for observation in outcome.observations:
            if observation.target_entity_id not in mechanism.observation_target_ids:
                raise MechanismContractError(
                    f"{mechanism.mechanism_id}: undeclared observation target"
                )
            if observation.via_port_id != target_port.port_id:
                raise MechanismContractError(
                    f"{mechanism.mechanism_id}: observation via undeclared input"
                )
            if (
                observation.apparent_source_ref is not None
                and observation.apparent_source_ref not in known_sources
            ):
                raise MechanismContractError(
                    f"{mechanism.mechanism_id}: unknown apparent source"
                )
            if (
                observation.representation_id is not None
                and observation.representation_id not in available_representations
            ):
                raise MechanismContractError(
                    f"{mechanism.mechanism_id}: unknown observation representation"
                )
            if observation.representation_id is not None:
                existing = self._state.representations.get(
                    observation.representation_id
                )
                visibility = (
                    existing.visibility
                    if existing is not None
                    else proposed_by_id[observation.representation_id].visibility
                )
                if visibility != "public":
                    raise MechanismContractError(
                        f"{mechanism.mechanism_id}: protected representation may "
                        "not be delivered"
                    )
            if (
                observation.representation_id is not None
                and observation.representation_id not in proposed_by_id
                and observation.representation_id != effect.representation_id
            ):
                raise MechanismContractError(
                    f"{mechanism.mechanism_id}: observation representation was "
                    "not available on the triggering effect"
                )

    @staticmethod
    def _evaluate_invariants(
        binding: ExactMechanismBinding,
        context: MechanismContext,
        outcome: MechanismOutcome,
    ) -> list[InvariantResult]:
        """Run independent registered checkers and construct canonical evidence."""
        results: list[InvariantResult] = []
        failed: list[str] = []
        for invariant_id in context.mechanism.invariant_ids:
            passed = binding.invariant_checkers[invariant_id](
                context.defensive_copy(),
                outcome.model_copy(deep=True),
            )
            if not isinstance(passed, bool):
                raise MechanismInvariantError(
                    f"{context.mechanism.mechanism_id}: checker {invariant_id!r} "
                    "did not return a Boolean"
                )
            results.append(
                InvariantResult(
                    invariant_id=invariant_id,
                    passed=passed,
                    detail=(
                        f"Independent exact checker {invariant_id} "
                        f"{'passed' if passed else 'failed'}."
                    ),
                )
            )
            if not passed:
                failed.append(invariant_id)
        if failed:
            raise MechanismInvariantError(
                f"{context.mechanism.mechanism_id}: failed independent "
                f"invariants {failed!r}"
            )
        return results

    def _build_patch(
        self,
        mechanism: MechanismSpec,
        target_port: PortState,
        outcome: MechanismOutcome,
        *,
        logical_time: int,
        observation_logical_time: int,
        parent_event_id: str,
    ) -> tuple[StatePatch, CausalState]:
        """Construct and validate a complete next-state patch without partial mutation."""
        before = self.state
        before_digest = state_digest(before)
        after = before.model_copy(deep=True)
        changes: list[FactChange] = []
        for update in outcome.updates:
            fact = after.fact(update.fact_id)
            before_value = deepcopy(fact.value)
            if not _json_values_equal(before_value, update.value):
                changes.append(
                    FactChange(
                        fact_id=update.fact_id,
                        visibility=fact.visibility,
                        before=before_value,
                        after=deepcopy(update.value),
                    )
                )
            fact.value = deepcopy(update.value)

        placement_changes: list[PlacementChange] = []
        for placement_update in outcome.placement_updates:
            placement = after.placements[placement_update.entity_id]
            before_place_id = placement.place_id
            if before_place_id != placement_update.destination_place_id:
                placement_changes.append(
                    PlacementChange(
                        entity_id=placement_update.entity_id,
                        before_place_id=before_place_id,
                        after_place_id=placement_update.destination_place_id,
                        via_spatial_link_id=(
                            placement_update.via_spatial_link_id
                        ),
                    )
                )
            placement.place_id = placement_update.destination_place_id

        carrier_changes: list[CarrierRevisionChange] = []
        representations: list[RepresentationToken] = []
        for draft in outcome.representations:
            carrier = after.carriers[draft.carrier_id]
            before_carrier_revision = carrier.revision
            carrier.revision += 1
            carrier_changes.append(
                CarrierRevisionChange(
                    carrier_id=carrier.carrier_id,
                    before_revision=before_carrier_revision,
                    after_revision=carrier.revision,
                )
            )
            representation = RepresentationToken(
                representation_id=draft.representation_id,
                carrier_id=draft.carrier_id,
                carrier_revision=carrier.revision,
                encoding=draft.encoding,
                content=draft.content,
                content_hash=representation_digest(draft.content),
                actual_source_ref=draft.actual_source_ref,
                parent_representation_ids=list(
                    draft.parent_representation_ids
                ),
                visibility=draft.visibility,
            )
            after.representations[representation.representation_id] = representation
            representations.append(representation)

        observations: list[ObservationRecord] = []
        for observation_draft in outcome.observations:
            observation_id = f"observation_{self._observation_sequence:06d}"
            self._observation_sequence += 1
            observation = ObservationRecord(
                observation_id=observation_id,
                target_entity_id=observation_draft.target_entity_id,
                via_port_id=target_port.port_id,
                apparent_content=observation_draft.apparent_content,
                apparent_source_ref=observation_draft.apparent_source_ref,
                representation_id=observation_draft.representation_id,
                logical_time=observation_logical_time,
                causal_parent_event_ids=[parent_event_id],
            )
            after.observations[observation_id] = observation
            after.inboxes.setdefault(observation_draft.target_entity_id, []).append(
                observation_id
            )
            observations.append(observation)

        after.revision = before.revision + 1
        after.logical_time = max(before.logical_time, logical_time)
        validated_after = CausalState.model_validate(after.model_dump(mode="json"))
        patch = StatePatch(
            before_revision=before.revision,
            after_revision=validated_after.revision,
            before_logical_time=before.logical_time,
            after_logical_time=validated_after.logical_time,
            before_digest=before_digest,
            after_digest=state_digest(validated_after),
            fact_changes=changes,
            placement_changes=placement_changes,
            carrier_changes=carrier_changes,
            representations_added=representations,
            observations_added=observations,
        )
        return patch, validated_after

    def _enqueue_effect(
        self,
        *,
        source_port_id: str,
        effect_type: str,
        representation_id: str | None,
        payload: Mapping[str, JsonValue],
        logical_time: int,
        zero_time_depth: int,
        parent_event_id: str,
        variance_source: VarianceSource,
    ) -> None:
        """Validate, trace, and queue one exact or external action effect."""
        if self._metrics.effects_emitted >= self._limits.max_effects:
            raise PropagationBudgetExceeded(
                f"emitted effect limit {self._limits.max_effects} exceeded"
            )
        if zero_time_depth > self._limits.max_zero_time_depth:
            raise PropagationBudgetExceeded(
                f"zero-time depth {zero_time_depth} exceeds "
                f"limit {self._limits.max_zero_time_depth}"
            )
        port = self._state.ports.get(source_port_id)
        if port is None or port.direction != "output" or port.effect_type != effect_type:
            raise MechanismContractError(
                f"cannot emit {effect_type!r} through {source_port_id!r}"
            )
        if (
            representation_id is not None
            and representation_id not in self._state.representations
        ):
            raise MechanismContractError("effect references unknown representation")
        effect_id = f"effect_{self._effect_sequence:06d}"
        self._effect_sequence += 1
        event = self._append_event(
            event_kind="effect_emitted",
            logical_time=logical_time,
            causal_parent_event_ids=[parent_event_id],
            summary=f"Emitted {effect_type} through {source_port_id}.",
            variance_source=variance_source,
            effect_id=effect_id,
            source_port_id=source_port_id,
            representation_id=representation_id,
            details={
                "zero_time_depth": 0 if self._positive_duration else zero_time_depth
            },
        )
        effect = EffectEnvelope(
            effect_id=effect_id,
            effect_type=effect_type,
            source_port_id=source_port_id,
            representation_id=representation_id,
            payload={key: deepcopy(value) for key, value in payload.items()},
            logical_time=event.logical_time,
            zero_time_depth=0 if self._positive_duration else zero_time_depth,
            variance_source=(
                "external_action"
                if variance_source == "external_action"
                else "exact"
            ),
            causal_parent_event_ids=[event.event_id],
        )
        self._metrics.effects_emitted += 1
        self._push_work(effect)

    def _push_work(self, work: _QueuedWork) -> None:
        """Add one agenda item with a stable tie-breaker and visible high-water."""
        logical_time = (
            work.logical_time
            if isinstance(work, EffectEnvelope)
            else work.effect.logical_time
        )
        heappush(self._queue, (logical_time, self._queue_sequence, work))
        self._queue_sequence += 1
        self._metrics.queue_high_water = max(
            self._metrics.queue_high_water, len(self._queue)
        )

    def _append_event(self, **values: object) -> CausalEvent:
        """Append one event with canonical sequence, revision, and parent checks."""
        event_kind = values.get("event_kind")
        if self._positive_duration and event_kind not in {
            "run_started",
            "run_completed",
        }:
            parent_ids = values.get("causal_parent_event_ids", [])
            if not isinstance(parent_ids, list) or not parent_ids:
                raise AssertionError("positive-duration event requires a parent")
            parent_times = [
                next(event.logical_time for event in self._events if event.event_id == parent_id)
                for parent_id in parent_ids
            ]
            requested = values.get("logical_time")
            if not isinstance(requested, int):
                raise AssertionError("event logical time must be an integer")
            starts_at = max(parent_times)
            nominal_due_at = max(
                requested,
                starts_at + self._scenario.minimum_world_duration,
            )
            due_at = max(
                nominal_due_at,
                self._events[-1].logical_time + self._scenario.minimum_world_duration,
            )
            serialization_delay = due_at - nominal_due_at
            values["logical_time"] = due_at
            raw_details = values.get("details", {})
            if not isinstance(raw_details, Mapping):
                raise AssertionError("event details must be a mapping")
            details = dict(raw_details)
            details["timing"] = {
                "starts_at": starts_at,
                "duration": due_at - starts_at,
                "minimum_duration": self._scenario.minimum_world_duration,
                "serialization_delay": serialization_delay,
                "source_kind": (
                    "scenario_assumption"
                    if serialization_delay == 0
                    else "scenario_assumption_plus_runtime_serialization"
                ),
                "source_ref": (
                    "minimum_world_duration"
                    if serialization_delay == 0
                    else "minimum_world_duration + trace_serialization"
                ),
            }
            values["details"] = details
        sequence = self._event_sequence
        event = CausalEvent.model_validate(
            {
                "event_id": f"event_{sequence:06d}",
                "sequence": sequence,
                "run_id": self._run_id,
                "state_revision": self._state.revision,
                **values,
            }
        )
        unknown = set(event.causal_parent_event_ids) - self._known_event_ids
        if unknown:
            raise MechanismContractError(
                f"event {event.event_id!r} has unknown parents {sorted(unknown)!r}"
            )
        self._events.append(event)
        self._known_event_ids.add(event.event_id)
        self._event_sequence += 1
        return event

    def _snapshot(self) -> _SessionSnapshot:
        """Capture every mutable surface needed for exact action rollback."""
        return _SessionSnapshot(
            state=self.state,
            events=self.events,
            metrics=self.metrics,
            queue=[
                (time, sequence, _copy_queued_work(work))
                for time, sequence, work in self._queue
            ],
            accepted_action_ids=list(self._accepted_action_ids),
            event_sequence=self._event_sequence,
            effect_sequence=self._effect_sequence,
            observation_sequence=self._observation_sequence,
            queue_sequence=self._queue_sequence,
        )

    def _restore_snapshot(self, snapshot: _SessionSnapshot) -> None:
        """Restore a failed action's complete pre-attempt state."""
        self._state = snapshot.state.model_copy(deep=True)
        self._events = [event.model_copy(deep=True) for event in snapshot.events]
        self._metrics = snapshot.metrics.model_copy(deep=True)
        self._queue = [
            (time, sequence, _copy_queued_work(work))
            for time, sequence, work in snapshot.queue
        ]
        self._accepted_action_ids = list(snapshot.accepted_action_ids)
        self._event_sequence = snapshot.event_sequence
        self._effect_sequence = snapshot.effect_sequence
        self._observation_sequence = snapshot.observation_sequence
        self._queue_sequence = snapshot.queue_sequence
        self._known_event_ids = {event.event_id for event in self._events}

    def _serialize_queue(self) -> list[ScheduledWork]:
        """Project private heap work into a strict checkpoint contract."""
        serialized: list[ScheduledWork] = []
        for due_at, sequence, work in sorted(self._queue):
            if isinstance(work, EffectEnvelope):
                serialized.append(
                    ScheduledWork(
                        due_at=due_at,
                        sequence=sequence,
                        work_kind="effect",
                        effect=work.model_copy(deep=True),
                    )
                )
                continue
            serialized.append(
                ScheduledWork(
                    due_at=due_at,
                    sequence=sequence,
                    work_kind="delivery",
                    effect=work.effect.model_copy(deep=True),
                    route_kind=work.route.route_kind,
                    target_port_id=work.route.target_port_id,
                    route_delay=work.route.route_delay,
                    connection_id=work.route.connection_id,
                    container_id=work.route.container_id,
                )
            )
        return serialized

    def _validate_scheduled_work_topology(
        self, scheduled: Sequence[ScheduledWork]
    ) -> None:
        """Re-derive every retained delivery from the authored local topology."""
        emitted = {
            event.event_id: event
            for event in self._events
            if event.event_kind == "effect_emitted"
        }
        for item in scheduled:
            parent_ids = item.effect.causal_parent_event_ids
            if len(parent_ids) != 1:
                raise ValueError("scheduled work has invalid effect parentage")
            emission = emitted.get(parent_ids[0])
            if emission is None:
                raise ValueError("scheduled work parent is not an effect emission")
            source = self._state.ports.get(item.effect.source_port_id)
            if (
                source is None
                or source.direction != "output"
                or source.effect_type != item.effect.effect_type
            ):
                raise ValueError("scheduled work has an invalid source port")
            if item.work_kind == "effect":
                if item.due_at != emission.logical_time:
                    raise ValueError("pending effect has an invalid due time")
                continue
            if item.target_port_id is None or item.route_delay is None:
                raise ValueError("pending delivery lacks route fields")
            target = self._state.ports.get(item.target_port_id)
            if target is None or target.direction != "input":
                raise ValueError("pending delivery has an invalid target port")
            if target.effect_type != item.effect.effect_type:
                raise ValueError("pending delivery joins incompatible ports")
            if item.route_kind == "connection":
                connection = self._state.connections.get(item.connection_id or "")
                if (
                    connection is None
                    or not connection.enabled
                    or connection.source_port_id != source.port_id
                    or connection.target_port_id != target.port_id
                    or connection.delay != item.route_delay
                ):
                    raise ValueError("pending delivery disagrees with its connection")
            elif item.route_kind == "container":
                if (
                    item.container_id != source.container_id
                    or target.container_id != source.container_id
                    or item.route_delay != 0
                ):
                    raise ValueError("pending delivery disagrees with its container")
            else:  # pragma: no cover - ScheduledWork validates the union
                raise ValueError("pending delivery has an unknown route kind")
            if item.due_at != emission.logical_time + item.route_delay:
                raise ValueError("pending delivery has an invalid due time")

    @staticmethod
    def _deserialize_queue(
        scheduled: list[ScheduledWork],
    ) -> list[tuple[int, int, _QueuedWork]]:
        """Restore only the public, validated pending-work representation."""
        queue: list[tuple[int, int, _QueuedWork]] = []
        for item in scheduled:
            if item.work_kind == "effect":
                work: _QueuedWork = item.effect.model_copy(deep=True)
            else:
                if (
                    item.route_kind is None
                    or item.target_port_id is None
                    or item.route_delay is None
                ):
                    raise ValueError("validated delivery lost route fields")
                work = _RoutedDelivery(
                    effect=item.effect.model_copy(deep=True),
                    route=_RouteCandidate(
                        route_kind=item.route_kind,
                        target_port_id=item.target_port_id,
                        route_delay=item.route_delay,
                        connection_id=item.connection_id,
                        container_id=item.container_id,
                    ),
                )
            queue.append((item.due_at, item.sequence, work))
        heapify(queue)
        return queue

    def _build_indexes(self) -> None:
        """Precompute exact local adjacency without semantic world search."""
        self._input_bindings = {
            port_id: mechanism.mechanism_id
            for mechanism in self._state.mechanisms.values()
            for port_id in mechanism.input_port_ids
        }
        container_inputs: dict[tuple[str, str], list[str]] = defaultdict(list)
        for port in self._state.ports.values():
            if port.direction == "input" and port.container_id is not None:
                container_inputs[(port.container_id, port.effect_type)].append(
                    port.port_id
                )
        self._container_inputs = {
            key: sorted(port_ids) for key, port_ids in container_inputs.items()
        }
        connections: dict[str, list[ConnectionState]] = defaultdict(list)
        for connection in self._state.connections.values():
            connections[connection.source_port_id].append(connection)
        self._connections_by_source = {
            source: sorted(items, key=lambda item: item.connection_id)
            for source, items in connections.items()
        }

    def _validate_binding_registry(self) -> None:
        """Require one implementation-matched trusted binding per mechanism."""
        expected = set(self._state.mechanisms)
        actual = set(self._bindings)
        if expected != actual:
            raise MechanismContractError(
                f"binding registry mismatch: missing={sorted(expected - actual)!r}, "
                f"unknown={sorted(actual - expected)!r}"
            )
        for mechanism_id, mechanism in self._state.mechanisms.items():
            binding = self._bindings[mechanism_id]
            if binding.implementation_id != mechanism.implementation_id:
                raise MechanismContractError(
                    f"{mechanism_id}: exact implementation id mismatch"
                )
            expected_invariants = set(mechanism.invariant_ids)
            actual_invariants = set(binding.invariant_checkers)
            if expected_invariants != actual_invariants:
                raise MechanismContractError(
                    f"{mechanism_id}: invariant checker registry mismatch: "
                    f"missing={sorted(expected_invariants - actual_invariants)!r}, "
                    f"unknown={sorted(actual_invariants - expected_invariants)!r}"
                )

    def _current_logical_time(self) -> int:
        """Return the latest committed or traced logical time."""
        if not self._events:
            return self._state.logical_time
        return max(self._state.logical_time, self._events[-1].logical_time)

    @property
    def _positive_duration(self) -> bool:
        return self._scenario.timing_contract == "positive_duration"

    def _next_positive_time(self, *, requested: int, parent_event_id: str) -> int:
        """Return the earliest valid child time without creating a trace event."""
        if not self._positive_duration:
            return requested
        parent = next(
            event for event in self._events if event.event_id == parent_event_id
        )
        return max(
            requested,
            parent.logical_time + self._scenario.minimum_world_duration,
            self._events[-1].logical_time + self._scenario.minimum_world_duration,
        )

    @staticmethod
    def _effect_variance(effect: EffectEnvelope) -> VarianceSource:
        """Identify whether an effect originated at an action or exact mechanism."""
        return effect.variance_source


def _copy_queued_work(work: _QueuedWork) -> _QueuedWork:
    """Return an independent copy of either private agenda-item variant."""
    if isinstance(work, EffectEnvelope):
        return work.model_copy(deep=True)
    return _RoutedDelivery(
        effect=work.effect.model_copy(deep=True),
        route=work.route,
    )


def _json_values_equal(left: JsonValue, right: JsonValue) -> bool:
    """Compare strict JSON values without equating booleans and integers."""
    return json.dumps(left, sort_keys=True, separators=(",", ":")) == json.dumps(
        right,
        sort_keys=True,
        separators=(",", ":"),
    )


def _with_record_digest(values: dict[str, object]) -> dict[str, object]:
    """Attach a canonical corruption-detection digest to one persisted record."""
    result = dict(values)
    result["record_digest"] = canonical_record_digest(result)
    return result
