"""Simulator-owned frozen-snapshot and atomic active-system orchestration."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
import threading

from pydantic import ValidationError

from cybernetic_influence.active_runtime.models import (
    ActionIntent,
    ActiveObservation,
    ActiveProposal,
    ActiveRuntimeCheckpoint,
    ActiveRuntimeConfig,
    ActiveRuntimeResult,
    ActiveStepResult,
    ActiveSystemInput,
    ActiveSystemSpec,
    ActiveSystemState,
    ActivationCause,
    ActivationAttemptRecord,
    ExecutionBudget,
    ExactWorkRecord,
    ModelCallEvidence,
    ParticipantAttempt,
    RuntimeProgressKind,
    RuntimeProgressUpdate,
    private_state_size,
    project_action_interfaces,
    with_record_digest,
)
from cybernetic_influence.active_runtime.run_control import CompletionRecord
from cybernetic_influence.active_runtime.protocol import (
    ActiveSystemBinding,
    ActiveSystemExecutionError,
)
from cybernetic_influence.causal_core.engine import (
    CausalLimits,
    CausalSession,
    ExactMechanismBinding,
)
from cybernetic_influence.causal_core.models import (
    ActionAttempt,
    CausalCheckpoint,
    CausalScenario,
    CausalState,
    scenario_execution_fingerprint,
    scenario_fingerprint,
)


class ActiveRuntimeError(RuntimeError):
    """Base class for fail-loud active-runtime contract errors."""


class ParticipantContractError(ActiveRuntimeError):
    """A declared participant or its proposal violated the active protocol."""


class ActiveBudgetError(ActiveRuntimeError):
    """Observed or uncertain provider spend made continuation unsafe."""


@dataclass
class _CollectedParticipant:
    """Mutable attempt-local collection state never exposed as authority."""

    active_input: ActiveSystemInput
    proposal: ActiveProposal | None = None
    evidence: list[ModelCallEvidence] = field(default_factory=list)
    assigned_action_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DueActivation:
    """One derived earliest timestamp and every process due at that time."""

    logical_time: int
    causes: dict[str, tuple[ActivationCause, ...]]

    @property
    def active_system_ids(self) -> list[str]:
        """Return the due participant set in canonical order."""
        return sorted(self.causes)


RuntimeProgressObserver = Callable[[RuntimeProgressUpdate, ActiveRuntimeCheckpoint], None]


class ActiveRuntimeSession:
    """One canonical active run composing a single exact causal-core session."""

    def __init__(
        self,
        scenario: CausalScenario,
        exact_bindings: Mapping[str, ExactMechanismBinding],
        active_specs: Sequence[ActiveSystemSpec],
        active_bindings: Mapping[str, ActiveSystemBinding],
        *,
        run_id: str,
        config: ActiveRuntimeConfig,
        causal_limits: CausalLimits | None = None,
        progress_observer: RuntimeProgressObserver | None = None,
    ) -> None:
        self._scenario = CausalScenario.model_validate(
            scenario.model_dump(mode="json")
        )
        self._exact_bindings = dict(exact_bindings)
        self._specs = {
            spec.active_system_id: ActiveSystemSpec.model_validate(
                spec.model_dump(mode="json")
            )
            for spec in active_specs
        }
        self._active_bindings = dict(active_bindings)
        self._run_id = run_id
        self._config = ActiveRuntimeConfig.model_validate(
            config.model_dump(mode="json")
        )
        self._validate_registry(self._scenario.initial_state)
        self._states = {
            active_system_id: ActiveSystemState(
                active_system_id=active_system_id,
                entity_id=spec.entity_id,
                implementation_id=spec.implementation_id,
                private_state=spec.initial_private_state,
                next_update_at=spec.initial_next_update_at,
            )
            for active_system_id, spec in self._specs.items()
        }
        self._core = CausalSession(
            self._scenario,
            self._exact_bindings,
            run_id=run_id,
            limits=causal_limits,
        )
        self._attempts: list[ActivationAttemptRecord] = []
        self._exact_work: list[ExactWorkRecord] = []
        self._next_attempt_index = 0
        self._next_commit_index = 0
        self._terminal = False
        self._lock = threading.RLock()
        self._progress_observer = progress_observer

    @property
    def core_state(self) -> CausalState:
        """Return a defensive copy of the sole canonical world state."""
        return self._core.state

    @property
    def active_states(self) -> dict[str, ActiveSystemState]:
        """Return defensive copies of canonical protected active-system state."""
        with self._lock:
            return {
                active_system_id: state.model_copy(deep=True)
                for active_system_id, state in self._states.items()
            }

    @property
    def pending_active_system_ids(self) -> list[str]:
        """Return systems with at least one newly delivered declared observation."""
        with self._lock:
            pending: list[str] = []
            for active_system_id, spec in self._specs.items():
                state = self._states[active_system_id]
                consumed = set(state.consumed_observation_ids)
                declared_ports = set(spec.observation_port_ids)
                if any(
                    observation_id not in consumed
                    and self._core.state.observations[
                        observation_id
                    ].via_port_id
                    in declared_ports
                    for observation_id in self._core.state.inboxes.get(
                        spec.entity_id, []
                    )
                ):
                    pending.append(active_system_id)
            return sorted(pending)

    def next_due_activation(self, *, through: int | None = None) -> DueActivation | None:
        """Return the earliest due set, without settling exact work after ``through``."""
        with self._lock:
            while True:
                due = self._next_due_activation_after_exact_work(through=through)
                if due is not None:
                    return due
                exact_due = self._core.next_pending_time
                if exact_due is None:
                    return None
                if through is not None and exact_due > through:
                    return None
                if not self._settle_exact_due(exact_due, through=through):
                    return None

    def next_scheduled_time(self) -> int | None:
        """Inspect pending participant or exact work without advancing the trace."""
        with self._lock:
            times: list[int] = []
            if self._core.next_pending_time is not None:
                times.append(self._core.next_pending_time)
            for active_system_id, spec in self._specs.items():
                state = self._states[active_system_id]
                if state.next_update_at is not None:
                    times.append(state.next_update_at)
                consumed = set(state.consumed_observation_ids)
                times.extend(
                    self._core.state.observations[observation_id].logical_time
                    for observation_id in self._core.state.inboxes.get(
                        spec.entity_id, []
                    )
                    if observation_id not in consumed
                    and self._core.state.observations[observation_id].via_port_id
                    in set(spec.observation_port_ids)
                )
            return min(times) if times else None

    def drain_pending_exact_work(self) -> None:
        """Commit already-triggered exact work without activating new participants.

        A terminal fact can become true while its mechanism still has retained
        deliveries queued (for example, the closure receipt).  Those effects
        are part of the committed causal consequence of the terminal action;
        complete them before sealing the run, but do not schedule a new
        participant decision after the selected terminal boundary.
        """
        with self._lock:
            self._require_active()
            while (due := self._core.next_pending_time) is not None:
                if not self._settle_exact_due(due):
                    raise ActiveRuntimeError(
                        "pending exact work did not advance while draining a "
                        "terminal boundary"
                    )

    def _next_due_activation_after_exact_work(
        self, *, through: int | None = None
    ) -> DueActivation | None:
        """Find participant work, first settling any earlier exact future work."""
        while True:
            due_candidates: dict[str, int] = {}
            pending_observations: dict[str, list[ActiveObservation]] = {}
            core_state = self._core.state
            for active_system_id, spec in self._specs.items():
                state = self._states[active_system_id]
                consumed = set(state.consumed_observation_ids)
                declared_ports = set(spec.observation_port_ids)
                observations = [
                    ActiveObservation(
                        observation_id=observation.observation_id,
                        via_port_id=observation.via_port_id,
                        apparent_content=observation.apparent_content,
                        apparent_source_ref=observation.apparent_source_ref,
                        representation_id=observation.representation_id,
                        logical_time=observation.logical_time,
                    )
                    for observation_id in core_state.inboxes.get(
                        spec.entity_id, []
                    )
                    if observation_id not in consumed
                    and (
                        observation := core_state.observations[observation_id]
                    ).via_port_id
                    in declared_ports
                ]
                pending_observations[active_system_id] = observations
                times = [item.logical_time for item in observations]
                if state.next_update_at is not None:
                    times.append(state.next_update_at)
                if times:
                    due_candidates[active_system_id] = min(times)
            participant_earliest = min(due_candidates.values(), default=None)
            exact_due = self._core.next_pending_time
            candidates = [
                item for item in (participant_earliest, exact_due) if item is not None
            ]
            earliest_work = min(candidates) if candidates else None
            if through is not None and earliest_work is not None and earliest_work > through:
                return None
            if exact_due is not None and (
                participant_earliest is None or exact_due <= participant_earliest
            ):
                if not self._settle_exact_due(exact_due, through=through):
                    return None
                continue
            if participant_earliest is None:
                return None

            earliest = participant_earliest
            logical_time = max(earliest, core_state.logical_time)
            # A positive-duration trace can advance canonical world time past a
            # participant's nominal wake while older exact siblings remain
            # queued.  Settle every transition now due at the normalized
            # activation time before freezing participant inputs.  Otherwise
            # the first participant action can commit those transitions and
            # make later siblings in the same frozen set appear to regress.
            if exact_due is not None and exact_due <= logical_time:
                if not self._settle_exact_due(exact_due, through=through):
                    return None
                continue
            causes: dict[str, tuple[ActivationCause, ...]] = {}
            for active_system_id in sorted(due_candidates):
                state = self._states[active_system_id]
                observations = [
                    item
                    for item in pending_observations[active_system_id]
                    if item.logical_time <= logical_time
                ]
                due_for_observation = bool(observations)
                due_for_wake = (
                    state.next_update_at is not None
                    and state.next_update_at <= logical_time
                )
                if not due_for_observation and not due_for_wake:
                    continue
                participant_causes: list[ActivationCause] = []
                if observations:
                    participant_causes.append(
                        ActivationCause(
                            kind="observation_delivery",
                            scheduled_for=logical_time,
                            observation_ids=sorted(
                                item.observation_id for item in observations
                            ),
                            description=(
                                "One or more declared observations became "
                                "available to this process."
                            ),
                        )
                    )
                if due_for_wake:
                    participant_causes.append(
                        ActivationCause(
                            kind="internal_wake",
                            scheduled_for=logical_time,
                            description=(
                                "A retained internal update became due without "
                                "requiring a new external observation."
                            ),
                        )
                    )
                causes[active_system_id] = tuple(participant_causes)
            if not causes:  # pragma: no cover - guarded by candidate construction
                raise AssertionError("due activation has no due participants")
            return DueActivation(logical_time=logical_time, causes=causes)

    @property
    def attempts(self) -> list[ActivationAttemptRecord]:
        """Return defensive protected activation-attempt evidence."""
        with self._lock:
            return [item.model_copy(deep=True) for item in self._attempts]

    @property
    def total_observed_cost(self) -> float:
        """Return priced spend across committed and rolled-back attempts."""
        with self._lock:
            return sum((item.observed_cost for item in self._attempts), 0.0)

    @property
    def cost_fully_observable(self) -> bool:
        """Return false after any provider-bound call lacks trustworthy cost."""
        with self._lock:
            return all(item.cost_fully_observable for item in self._attempts)

    def activate(
        self,
        active_system_ids: Sequence[str],
        *,
        logical_time: int,
        activation_causes: Mapping[
            str, Sequence[ActivationCause]
        ] | None = None,
    ) -> ActivationAttemptRecord:
        """Collect one frozen participant set and atomically commit all proposals."""
        with self._lock:
            self._require_active()
            supplied_ids = list(active_system_ids)
            if not supplied_ids:
                raise ParticipantContractError("activation set must be nonempty")
            if len(supplied_ids) != len(set(supplied_ids)):
                raise ParticipantContractError(
                    "activation set contains duplicate active-system ids"
                )
            unknown = set(supplied_ids) - set(self._specs)
            if unknown:
                raise ParticipantContractError(
                    f"activation set contains unknown members {sorted(unknown)!r}"
                )
            if logical_time < self._core.state.logical_time:
                raise ParticipantContractError("activation logical time regresses")
            if activation_causes is None:
                validated_causes = {
                    active_system_id: [
                        ActivationCause(
                            kind="manual_schedule",
                            scheduled_for=logical_time,
                            description=(
                                "A caller explicitly requested this legacy or "
                                "scenario-authored activation."
                            ),
                        )
                    ]
                    for active_system_id in supplied_ids
                }
            else:
                if set(activation_causes) != set(supplied_ids):
                    raise ParticipantContractError(
                        "activation-cause registry does not match participant set"
                    )
                validated_causes = {
                    active_system_id: [
                        ActivationCause.model_validate(
                            cause.model_dump(mode="json")
                            if isinstance(cause, ActivationCause)
                            else cause
                        )
                        for cause in activation_causes[active_system_id]
                    ]
                    for active_system_id in supplied_ids
                }
                if any(not causes for causes in validated_causes.values()):
                    raise ParticipantContractError(
                        "every participant requires an activation cause"
                    )
            self._require_spend_observable()

            canonical_ids = sorted(supplied_ids)
            pre_core = self._core.checkpoint()
            activation_id = f"activation_{self._next_attempt_index:06d}"
            collected = {
                active_system_id: _CollectedParticipant(
                    active_input=self._build_input(
                        self._specs[active_system_id],
                        self._states[active_system_id],
                        pre_core,
                        activation_id=activation_id,
                        logical_time=logical_time,
                        activation_causes=validated_causes[active_system_id],
                    )
                )
                for active_system_id in canonical_ids
            }
            self._emit_progress(
                kind="activation_started",
                logical_time=logical_time,
                participant_ids=canonical_ids,
                activation_id=activation_id,
            )

            collection_error: Exception | None = None
            for active_system_id in supplied_ids:
                item = collected[active_system_id]
                binding = self._active_bindings[active_system_id]
                try:
                    if getattr(binding.implementation, "provider_bound", False):
                        self._require_call_authorization()
                    raw = binding.implementation.step(
                        item.active_input.model_copy(deep=True)
                    )
                    result = self._validate_step_result(raw)
                    item.proposal = result.proposal.model_copy(deep=True)
                    item.evidence = [
                        evidence.model_copy(deep=True)
                        for evidence in result.call_evidence
                    ]
                except ActiveSystemExecutionError as error:
                    item.evidence = [
                        evidence.model_copy(deep=True)
                        for evidence in error.call_evidence
                    ]
                    collection_error = error
                    break
                except Exception as error:
                    collection_error = error
                    break

            if collection_error is None:
                try:
                    self._validate_call_evidence(collected)
                    self._validate_complete_proposals(canonical_ids, collected)
                except Exception as error:
                    collection_error = error

            if collection_error is not None:
                self._commit_failed_attempt(
                    canonical_ids=canonical_ids,
                    collected=collected,
                    logical_time=logical_time,
                    pre_core=pre_core,
                    error=collection_error,
                )
                raise collection_error

            for participant_index, active_system_id in enumerate(canonical_ids):
                proposal = collected[active_system_id].proposal
                if proposal is None:  # pragma: no cover - guarded above
                    raise AssertionError("validated participant lacks proposal")
                collected[active_system_id].assigned_action_ids = [
                    (
                        f"action_{self._next_commit_index:06d}_"
                        f"{participant_index:03d}_{action_index:03d}"
                    )
                    for action_index in range(len(proposal.actions))
                ]

            try:
                trial = CausalSession.restore(
                    self._scenario,
                    self._exact_bindings,
                    pre_core,
                )
                for active_system_id in canonical_ids:
                    item = collected[active_system_id]
                    proposal = item.proposal
                    if proposal is None:  # pragma: no cover - guarded above
                        raise AssertionError("validated participant lacks proposal")
                    spec = self._specs[active_system_id]
                    for action_id, intent in zip(
                        item.assigned_action_ids,
                        proposal.actions,
                        strict=True,
                    ):
                        trial.advance(
                            self._materialize_action(
                                action_id=action_id,
                                actor_entity_id=spec.entity_id,
                                intent=intent,
                                logical_time=logical_time,
                            ),
                            drain_through=logical_time,
                        )
                post_core = trial.checkpoint()
                new_states = self._proposed_states(canonical_ids, collected)
                participant_records = self._participant_records(
                    canonical_ids,
                    collected,
                )
                event_start = len(pre_core.events)
                record = self._build_attempt_record(
                    canonical_ids=canonical_ids,
                    participants=participant_records,
                    logical_time=logical_time,
                    pre_core=pre_core,
                    post_core=post_core,
                    core_event_ids=[
                        event.event_id for event in post_core.events[event_start:]
                    ],
                )
                attempts = [*self._attempts, record]
                self._build_checkpoint(
                    core_checkpoint=post_core,
                    states=new_states,
                    attempts=attempts,
                    next_attempt_index=self._next_attempt_index + 1,
                    next_commit_index=self._next_commit_index + 1,
                )
            except Exception as error:
                self._commit_failed_attempt(
                    canonical_ids=canonical_ids,
                    collected=collected,
                    logical_time=logical_time,
                    pre_core=pre_core,
                    error=error,
                )
                raise

            self._core = trial
            self._states = new_states
            self._attempts = attempts
            self._next_attempt_index += 1
            self._next_commit_index += 1
            self._emit_progress(
                kind="causal_moment_committed",
                logical_time=logical_time,
                participant_ids=canonical_ids,
                activation_id=record.activation_id,
                event_ids=record.core_event_ids,
            )
            return record.model_copy(deep=True)

    def checkpoint(self) -> ActiveRuntimeCheckpoint:
        """Return the sole validating continuation artifact for an active run."""
        with self._lock:
            self._require_active()
            return self._build_checkpoint(
                core_checkpoint=self._core.checkpoint(),
                states=self._states,
                attempts=self._attempts,
                next_attempt_index=self._next_attempt_index,
                next_commit_index=self._next_commit_index,
            )

    def _emit_progress(
        self,
        *,
        kind: RuntimeProgressKind,
        logical_time: int,
        participant_ids: Sequence[str] = (),
        activation_id: str | None = None,
        exact_work_id: str | None = None,
        event_ids: Sequence[str] = (),
    ) -> None:
        """Notify one observer from a validated immutable runtime prefix.

        Observers receive no mutable session reference.  An observer failure is
        deliberately allowed to propagate: claiming live progress while
        silently dropping it would make the retained execution misleading.
        """
        if self._progress_observer is None:
            return
        checkpoint = self._build_checkpoint(
            core_checkpoint=self._core.checkpoint(),
            states=self._states,
            attempts=self._attempts,
            next_attempt_index=self._next_attempt_index,
            next_commit_index=self._next_commit_index,
        )
        update = RuntimeProgressUpdate(
            kind=kind,
            logical_time=logical_time,
            participant_ids=sorted(participant_ids),
            activation_id=activation_id,
            exact_work_id=exact_work_id,
            event_ids=sorted(event_ids),
            state_revision=checkpoint.core_checkpoint.state.revision,
            checkpoint_digest=checkpoint.record_digest,
        )
        self._progress_observer(update.model_copy(deep=True), checkpoint.model_copy(deep=True))

    @classmethod
    def restore(
        cls,
        scenario: CausalScenario,
        exact_bindings: Mapping[str, ExactMechanismBinding],
        active_bindings: Mapping[str, ActiveSystemBinding],
        checkpoint: ActiveRuntimeCheckpoint,
        *,
        progress_observer: RuntimeProgressObserver | None = None,
    ) -> "ActiveRuntimeSession":
        """Restore one strictly matching aggregate checkpoint and registries."""
        validated = ActiveRuntimeCheckpoint.model_validate(
            checkpoint.model_dump(mode="json")
        )
        if validated.scenario_id != scenario.scenario_id:
            raise ValueError("active checkpoint scenario id does not match")
        if validated.scenario_fingerprint != scenario_fingerprint(scenario):
            raise ValueError("active checkpoint scenario fingerprint does not match")
        if (
            validated.scenario_execution_fingerprint
            != scenario_execution_fingerprint(scenario)
        ):
            raise ValueError(
                "active checkpoint scenario execution fingerprint does not match"
            )
        session = cls(
            scenario,
            exact_bindings,
            validated.specs,
            active_bindings,
            run_id=validated.run_id,
            config=validated.config,
            causal_limits=CausalLimits(
                max_effects=validated.core_checkpoint.max_effects,
                max_zero_time_depth=(
                    validated.core_checkpoint.max_zero_time_depth
                ),
            ),
            progress_observer=progress_observer,
        )
        session._core = CausalSession.restore(
            scenario,
            exact_bindings,
            validated.core_checkpoint,
        )
        session._states = {
            active_system_id: state.model_copy(deep=True)
            for active_system_id, state in validated.states.items()
        }
        session._attempts = [
            attempt.model_copy(deep=True) for attempt in validated.attempts
        ]
        session._exact_work = [
            item.model_copy(deep=True) for item in validated.exact_work
        ]
        session._next_attempt_index = validated.next_attempt_index
        session._next_commit_index = validated.next_commit_index
        return session

    def complete(
        self,
        *,
        completion: CompletionRecord | None = None,
        discard_pending_effects: bool = False,
    ) -> ActiveRuntimeResult:
        """Complete exact mechanics and bind them to all protected active evidence."""
        with self._lock:
            self._require_active()
            before = self._core.checkpoint()
            try:
                if discard_pending_effects:
                    self._discard_pending_exact_work(
                        reason=(
                            completion.reason
                            if completion is not None
                            else "runtime_completion"
                        )
                    )
                core_result = self._core.complete()
                result = ActiveRuntimeResult.model_validate(
                    with_record_digest(
                        {
                            "runtime_contract": "active-runtime.v1",
                            "schema_version": 1,
                            "run_id": self._run_id,
                            "scenario_id": self._scenario.scenario_id,
                            "scenario_fingerprint": scenario_fingerprint(
                                self._scenario
                            ),
                            "scenario_execution_fingerprint": (
                                scenario_execution_fingerprint(self._scenario)
                            ),
                            "status": "completed",
                            "config": self._config.model_dump(mode="json"),
                            "specs": [
                                spec.model_dump(mode="json")
                                for spec in self._ordered_specs()
                            ],
                            "final_states": {
                                active_system_id: state.model_dump(mode="json")
                                for active_system_id, state in self._states.items()
                            },
                            "core_result": core_result.model_dump(mode="json"),
                            "attempts": [
                                item.model_dump(mode="json")
                                for item in self._attempts
                            ],
                            "exact_work": [
                                item.model_dump(mode="json")
                                for item in self._exact_work
                            ],
                            "next_attempt_index": self._next_attempt_index,
                            "next_commit_index": self._next_commit_index,
                            "model_calls": sum(
                                len(participant.call_evidence)
                                for attempt in self._attempts
                                for participant in attempt.participants
                            ),
                            "total_observed_cost": self.total_observed_cost,
                            "cost_fully_observable": self.cost_fully_observable,
                            "completion": (
                                completion.model_dump(mode="json")
                                if completion is not None
                                else None
                            ),
                            "outcome_summary": (
                                f"completed {self._next_commit_index} active "
                                f"activation(s), {len(core_result.accepted_action_ids)} "
                                f"action(s), and {len(core_result.final_state.observations)} "
                                "delivered observation(s)"
                            ),
                        }
                    )
                )
            except Exception:
                self._core = CausalSession.restore(
                    self._scenario,
                    self._exact_bindings,
                    before,
                )
                raise
            self._terminal = True
            return result

    def _build_input(
        self,
        spec: ActiveSystemSpec,
        active_state: ActiveSystemState,
        core: CausalCheckpoint,
        *,
        activation_id: str,
        logical_time: int,
        activation_causes: Sequence[ActivationCause],
    ) -> ActiveSystemInput:
        """Project only declared, agent-visible data from the frozen checkpoint."""
        consumed = set(active_state.consumed_observation_ids)
        declared_ports = set(spec.observation_port_ids)
        observation_ids = core.state.inboxes.get(spec.entity_id, [])
        observations = [
            core.state.observations[observation_id]
            for observation_id in observation_ids
            if observation_id not in consumed
            and core.state.observations[observation_id].via_port_id in declared_ports
            and core.state.observations[observation_id].logical_time
            <= logical_time
        ]
        if len(observations) > self._config.max_observations_per_system:
            raise ParticipantContractError(
                f"active system {spec.active_system_id!r} has "
                f"{len(observations)} pending observations, exceeding limit "
                f"{self._config.max_observations_per_system}"
            )
        active_observations = [
            ActiveObservation(
                observation_id=item.observation_id,
                via_port_id=item.via_port_id,
                apparent_content=item.apparent_content,
                apparent_source_ref=item.apparent_source_ref,
                representation_id=item.representation_id,
                logical_time=item.logical_time,
            )
            for item in observations
        ]
        return ActiveSystemInput(
            activation_id=activation_id,
            active_system_id=spec.active_system_id,
            entity_id=spec.entity_id,
            logical_time=logical_time,
            time_unit=self._scenario.time_unit,
            activation_causes=list(activation_causes),
            next_update_at=active_state.next_update_at,
            observations=active_observations,
            action_interfaces=project_action_interfaces(
                spec,
                active_observations,
                core.state,
            ),
            private_state=active_state.private_state,
            budget=ExecutionBudget(
                max_call_cost=self._config.per_call_budget,
                max_actions=self._config.max_actions_per_system,
            ),
        )

    def _settle_exact_due(
        self, logical_time: int, *, through: int | None = None
    ) -> bool:
        """Retain a due exact transition as its own causal provenance record."""
        # Positive-duration traces may serialize a same-due exact cascade into
        # later retained world events.  Never ask the core to move its world
        # state backward merely because an already-queued sibling had an older
        # nominal due time.
        logical_time = max(logical_time, self._core.state.logical_time)
        before = self._core.checkpoint()
        pending_before = self._core.next_pending_time
        events = self._core.advance_due(
            logical_time, event_time_limit=through
        )
        if not events:
            # A legitimate exact transition can have no retained event (for
            # example, a disabled route). A bounded transition leaves the
            # exact queue unchanged after its transactional rollback.
            return self._core.next_pending_time != pending_before
        after = self._core.checkpoint()
        record = ExactWorkRecord.model_validate(
            with_record_digest(
                {
                    "work_index": len(self._exact_work),
                    "work_id": f"exact_work_{len(self._exact_work):06d}",
                    "prior_attempt_count": self._next_attempt_index,
                    "logical_time": logical_time,
                    "pre_core_state_digest": before.state_digest,
                    "pre_core_event_tail_digest": before.event_tail_digest,
                    "post_core_state_digest": after.state_digest,
                    "post_core_event_tail_digest": after.event_tail_digest,
                    "core_event_ids": [event.event_id for event in events],
                }
            )
        )
        self._exact_work.append(record)
        self._emit_progress(
            kind="exact_work_committed",
            logical_time=record.logical_time,
            exact_work_id=record.work_id,
            event_ids=record.core_event_ids,
        )
        return True

    def _discard_pending_exact_work(self, *, reason: str) -> None:
        """Retain deliberate non-execution as exact work at a terminal boundary."""
        before = self._core.checkpoint()
        self._core.discard_pending_effects(reason=reason)
        after = self._core.checkpoint()
        event_ids = [
            event.event_id
            for event in after.events[len(before.events):]
            if event.event_kind != "run_completed"
        ]
        if not event_ids:
            return
        record = ExactWorkRecord.model_validate(
                with_record_digest(
                    {
                        "work_index": len(self._exact_work),
                        "work_id": f"exact_work_{len(self._exact_work):06d}",
                        "prior_attempt_count": self._next_attempt_index,
                        "logical_time": after.state.logical_time,
                        "pre_core_state_digest": before.state_digest,
                        "pre_core_event_tail_digest": before.event_tail_digest,
                        "post_core_state_digest": after.state_digest,
                        "post_core_event_tail_digest": after.event_tail_digest,
                        "core_event_ids": event_ids,
                    }
                )
        )
        self._exact_work.append(record)
        self._emit_progress(
            kind="exact_work_committed",
            logical_time=record.logical_time,
            exact_work_id=record.work_id,
            event_ids=record.core_event_ids,
        )

    @staticmethod
    def _validate_step_result(raw: object) -> ActiveStepResult:
        """Decode every implementation through the same strict response schema."""
        if raw is None:
            raise ParticipantContractError("missing active-system proposal")
        try:
            if isinstance(raw, ActiveStepResult):
                return ActiveStepResult.model_validate(raw.model_dump(mode="json"))
            return ActiveStepResult.model_validate(raw)
        except (ValidationError, TypeError, ValueError) as error:
            raise ParticipantContractError(
                f"malformed active-system response: {error}"
            ) from error

    def _validate_call_evidence(
        self,
        collected: Mapping[str, _CollectedParticipant],
    ) -> None:
        """Account provider calls before any proposal can mutate the world."""
        evidence = [
            call
            for item in collected.values()
            for call in item.evidence
        ]
        trace_ids = [call.trace_id for call in evidence]
        if len(trace_ids) != len(set(trace_ids)):
            raise ParticipantContractError("duplicate model-call trace id")
        for call in evidence:
            if call.status != "completed":
                raise ActiveBudgetError(
                    f"provider call {call.trace_id!r} failed; activation cannot commit"
                )
            if call.cost is None:
                raise ActiveBudgetError(
                    f"provider call {call.trace_id!r} has unobservable cost"
                )
            if call.cost > self._config.per_call_budget:
                raise ActiveBudgetError(
                    f"provider call {call.trace_id!r} cost {call.cost:.8f} exceeds "
                    f"per-call budget {self._config.per_call_budget:.8f}"
                )
        prospective = self.total_observed_cost + sum(
            call.cost or 0.0 for call in evidence
        )
        if prospective > self._config.per_run_budget:
            raise ActiveBudgetError(
                f"observed run cost {prospective:.8f} exceeds per-run budget "
                f"{self._config.per_run_budget:.8f}"
            )

    def _validate_complete_proposals(
        self,
        canonical_ids: Sequence[str],
        collected: Mapping[str, _CollectedParticipant],
    ) -> None:
        """Validate the exact participant set, identities, and action envelope."""
        proposals = [
            item.proposal for item in collected.values() if item.proposal is not None
        ]
        actual_ids = [proposal.active_system_id for proposal in proposals]
        duplicates = sorted(
            active_system_id
            for active_system_id in set(actual_ids)
            if actual_ids.count(active_system_id) > 1
        )
        if duplicates:
            raise ParticipantContractError(
                f"duplicate proposal identities {duplicates!r}"
            )
        unexpected = sorted(set(actual_ids) - set(canonical_ids))
        if unexpected:
            raise ParticipantContractError(
                f"unexpected proposal identities {unexpected!r}"
            )
        missing = sorted(set(canonical_ids) - set(actual_ids))
        if missing:
            raise ParticipantContractError(f"missing proposals {missing!r}")
        for active_system_id in canonical_ids:
            item = collected[active_system_id]
            proposal = item.proposal
            if proposal is None:  # pragma: no cover - set validation above
                raise AssertionError("complete set lacks proposal")
            spec = self._specs[active_system_id]
            if proposal.active_system_id != active_system_id:
                raise ParticipantContractError(
                    f"proposal identity mismatch for {active_system_id!r}"
                )
            if proposal.implementation_id != spec.implementation_id:
                raise ParticipantContractError(
                    f"proposal implementation mismatch for {active_system_id!r}"
                )
            if len(proposal.actions) > item.active_input.budget.max_actions:
                raise ParticipantContractError(
                    f"active system {active_system_id!r} proposed too many actions"
                )
            if (
                private_state_size(proposal.private_state)
                > self._config.max_private_state_bytes
            ):
                raise ParticipantContractError(
                    f"active system {active_system_id!r} private state exceeds limit"
                )
            if (
                proposal.update_schedule.mode == "schedule"
                and (
                    proposal.update_schedule.next_update_at is None
                    or proposal.update_schedule.next_update_at
                    <= item.active_input.logical_time
                )
            ):
                raise ParticipantContractError(
                    f"active system {active_system_id!r} scheduled a non-future "
                    "update"
                )
            interfaces = {
                surface.output_port_id: surface
                for surface in item.active_input.action_interfaces
            }
            for intent in proposal.actions:
                surface = interfaces.get(intent.output_port_id)
                if surface is None:
                    raise ParticipantContractError(
                        f"active system {active_system_id!r} used an unexposed "
                        f"output {intent.output_port_id!r}"
                    )
                if (
                    intent.representation_id is not None
                    and intent.representation_id not in surface.representation_ids
                ):
                    raise ParticipantContractError(
                        f"active system {active_system_id!r} referenced inaccessible "
                        f"representation {intent.representation_id!r}"
                    )

    def _proposed_states(
        self,
        canonical_ids: Sequence[str],
        collected: Mapping[str, _CollectedParticipant],
    ) -> dict[str, ActiveSystemState]:
        """Build every private/cursor update before adopting any of them."""
        output = {
            active_system_id: state.model_copy(deep=True)
            for active_system_id, state in self._states.items()
        }
        for active_system_id in canonical_ids:
            before = self._states[active_system_id]
            item = collected[active_system_id]
            proposal = item.proposal
            if proposal is None:  # pragma: no cover - validated earlier
                raise AssertionError("validated participant lacks proposal")
            consumed = [
                *before.consumed_observation_ids,
                *(observation.observation_id for observation in item.active_input.observations),
            ]
            output[active_system_id] = ActiveSystemState(
                active_system_id=active_system_id,
                entity_id=before.entity_id,
                implementation_id=before.implementation_id,
                revision=before.revision + 1,
                activation_count=before.activation_count + 1,
                private_state=proposal.private_state,
                consumed_observation_ids=consumed,
                next_update_at=self._resolve_next_update_at(
                    before.next_update_at,
                    proposal,
                    logical_time=item.active_input.logical_time,
                ),
            )
        return output

    @staticmethod
    def _resolve_next_update_at(
        prior: int | None,
        proposal: ActiveProposal,
        *,
        logical_time: int,
    ) -> int | None:
        """Apply a proposal's scheduling directive after consuming a due wake."""
        directive = proposal.update_schedule
        if directive.mode == "schedule":
            if (
                directive.next_update_at is None
                or directive.next_update_at <= logical_time
            ):
                raise ParticipantContractError(
                    "scheduled update must be strictly in the future"
                )
            return directive.next_update_at
        if directive.mode == "dormant":
            return None
        return prior if prior is not None and prior > logical_time else None

    @staticmethod
    def _materialize_action(
        *,
        action_id: str,
        actor_entity_id: str,
        intent: ActionIntent,
        logical_time: int,
    ) -> ActionAttempt:
        """Assign every canonical action identity outside the implementation."""
        return ActionAttempt(
            action_id=action_id,
            actor_entity_id=actor_entity_id,
            output_port_id=intent.output_port_id,
            representation_id=intent.representation_id,
            payload=intent.payload,
            logical_time=logical_time,
            public_summary=intent.public_summary,
        )

    def _commit_failed_attempt(
        self,
        *,
        canonical_ids: Sequence[str],
        collected: Mapping[str, _CollectedParticipant],
        logical_time: int,
        pre_core: CausalCheckpoint,
        error: Exception,
    ) -> ActivationAttemptRecord:
        """Retain forensic spend while leaving world/private state untouched."""
        record = self._build_attempt_record(
            canonical_ids=canonical_ids,
            participants=self._participant_records(canonical_ids, collected),
            logical_time=logical_time,
            pre_core=pre_core,
            error=error,
        )
        attempts = [*self._attempts, record]
        self._build_checkpoint(
            core_checkpoint=pre_core,
            states=self._states,
            attempts=attempts,
            next_attempt_index=self._next_attempt_index + 1,
            next_commit_index=self._next_commit_index,
        )
        self._attempts = attempts
        self._next_attempt_index += 1
        self._emit_progress(
            kind="activation_failed",
            logical_time=logical_time,
            participant_ids=canonical_ids,
            activation_id=record.activation_id,
        )
        return record

    @staticmethod
    def _participant_records(
        canonical_ids: Sequence[str],
        collected: Mapping[str, _CollectedParticipant],
    ) -> list[ParticipantAttempt]:
        """Freeze attempt-local collection state into strict protected records."""
        return [
            ParticipantAttempt(
                requested_active_system_id=active_system_id,
                input=collected[active_system_id].active_input,
                proposal=collected[active_system_id].proposal,
                call_evidence=collected[active_system_id].evidence,
                assigned_action_ids=collected[active_system_id].assigned_action_ids,
            )
            for active_system_id in canonical_ids
        ]

    def _build_attempt_record(
        self,
        *,
        canonical_ids: Sequence[str],
        participants: Sequence[ParticipantAttempt],
        logical_time: int,
        pre_core: CausalCheckpoint,
        post_core: CausalCheckpoint | None = None,
        core_event_ids: Sequence[str] = (),
        error: Exception | None = None,
    ) -> ActivationAttemptRecord:
        """Construct one self-validating success or failure record."""
        evidence = [
            call for participant in participants for call in participant.call_evidence
        ]
        committed = post_core is not None and error is None
        return ActivationAttemptRecord.model_validate(
            with_record_digest(
                {
                    "runtime_contract": "active-runtime.v1",
                    "schema_version": 1,
                    "attempt_index": self._next_attempt_index,
                    "activation_id": f"activation_{self._next_attempt_index:06d}",
                    "candidate_commit_index": self._next_commit_index,
                    "committed_activation_index": (
                        self._next_commit_index if committed else None
                    ),
                    "logical_time": logical_time,
                    "status": "committed" if committed else "failed",
                    "declared_active_system_ids": list(canonical_ids),
                    "participants": [
                        participant.model_dump(mode="json")
                        for participant in participants
                    ],
                    "pre_core_state_digest": pre_core.state_digest,
                    "pre_core_event_tail_digest": pre_core.event_tail_digest,
                    "post_core_state_digest": (
                        post_core.state_digest if post_core is not None else None
                    ),
                    "post_core_event_tail_digest": (
                        post_core.event_tail_digest if post_core is not None else None
                    ),
                    "core_event_ids": list(core_event_ids),
                    "observed_cost": sum(
                        (call.cost or 0.0 for call in evidence),
                        0.0,
                    ),
                    "cost_fully_observable": all(
                        call.cost_observable for call in evidence
                    ),
                    "error_type": None if committed else type(error).__name__,
                    "error_message": None if committed else str(error),
                }
            )
        )

    def _build_checkpoint(
        self,
        *,
        core_checkpoint: CausalCheckpoint,
        states: Mapping[str, ActiveSystemState],
        attempts: Sequence[ActivationAttemptRecord],
        next_attempt_index: int,
        next_commit_index: int,
    ) -> ActiveRuntimeCheckpoint:
        """Validate a complete candidate aggregate before it becomes authority."""
        total_cost = sum((item.observed_cost for item in attempts), 0.0)
        return ActiveRuntimeCheckpoint.model_validate(
            with_record_digest(
                {
                    "runtime_contract": "active-runtime.v1",
                    "schema_version": 1,
                    "run_id": self._run_id,
                    "scenario_id": self._scenario.scenario_id,
                    "scenario_fingerprint": scenario_fingerprint(self._scenario),
                    "scenario_execution_fingerprint": (
                        scenario_execution_fingerprint(self._scenario)
                    ),
                    "config": self._config.model_dump(mode="json"),
                    "specs": [
                        spec.model_dump(mode="json")
                        for spec in self._ordered_specs()
                    ],
                    "states": {
                        active_system_id: state.model_dump(mode="json")
                        for active_system_id, state in states.items()
                    },
                    "core_checkpoint": core_checkpoint.model_dump(mode="json"),
                    "attempts": [
                        item.model_dump(mode="json") for item in attempts
                    ],
                    "exact_work": [
                        item.model_dump(mode="json") for item in self._exact_work
                    ],
                    "next_attempt_index": next_attempt_index,
                    "next_commit_index": next_commit_index,
                    "total_observed_cost": total_cost,
                    "cost_fully_observable": all(
                        item.cost_fully_observable for item in attempts
                    ),
                }
            )
        )

    def _validate_registry(self, state: CausalState) -> None:
        """Bind active declarations to concrete core entities and interfaces."""
        if not self._specs:
            raise ValueError("active runtime requires at least one active system")
        if len(self._specs) != len(set(self._specs)):
            raise ValueError("active-system ids must be unique")
        entity_ids = [spec.entity_id for spec in self._specs.values()]
        if len(entity_ids) != len(set(entity_ids)):
            raise ValueError("one entity may have only one Phase-2 active system")
        if set(self._active_bindings) != set(self._specs):
            raise ValueError("active binding registry does not match active specs")
        for active_system_id, spec in self._specs.items():
            if spec.entity_id not in state.entities:
                raise ValueError(
                    f"active system {active_system_id!r} has unknown entity"
                )
            binding = self._active_bindings[active_system_id]
            if binding.implementation_id != spec.implementation_id:
                raise ValueError(
                    f"active system {active_system_id!r} implementation mismatch"
                )
            if private_state_size(spec.initial_private_state) > (
                self._config.max_private_state_bytes
            ):
                raise ValueError(
                    f"active system {active_system_id!r} initial private state "
                    "exceeds limit"
                )
            for port_id in spec.output_port_ids:
                port = state.ports.get(port_id)
                if (
                    port is None
                    or port.direction != "output"
                    or port.owner_ref != spec.entity_id
                ):
                    raise ValueError(
                        f"active system {active_system_id!r} has unowned/non-output "
                        f"port {port_id!r}"
                    )
            for unavailable_when in spec.output_port_unavailable_when.values():
                unknown_facts: list[str] = []
                for fact_id in unavailable_when:
                    try:
                        state.fact(fact_id)
                    except ValueError:
                        unknown_facts.append(fact_id)
                if unknown_facts:
                    raise ValueError(
                        f"active system {active_system_id!r} availability rule "
                        f"has unknown facts {sorted(unknown_facts)!r}"
                    )
            for port_id in spec.observation_port_ids:
                port = state.ports.get(port_id)
                if port is None or port.direction != "input":
                    raise ValueError(
                        f"active system {active_system_id!r} has invalid "
                        f"observation port {port_id!r}"
                    )
                mechanism = state.mechanism_for_input_port(port_id)
                if spec.entity_id not in mechanism.observation_target_ids:
                    raise ValueError(
                        f"observation port {port_id!r} cannot deliver to "
                        f"{spec.entity_id!r}"
                    )
            for representation_id in spec.initial_representation_ids:
                representation = state.representations.get(representation_id)
                if representation is None:
                    raise ValueError(
                        f"active system {active_system_id!r} has unknown initial "
                        f"representation {representation_id!r}"
                    )
                carrier = state.carriers[representation.carrier_id]
                if carrier.owner_ref != spec.entity_id:
                    raise ValueError(
                        f"active system {active_system_id!r} cannot initially access "
                        f"representation {representation_id!r}"
                    )

    def _require_active(self) -> None:
        """Reject activation, checkpoint, or completion after terminal commit."""
        if self._terminal:
            raise RuntimeError("active runtime is already terminal")

    def _require_spend_observable(self) -> None:
        """Prevent another provider call after unknown or exhausted spend."""
        if not self.cost_fully_observable:
            raise ActiveBudgetError(
                "prior provider spend is unobservable; refusing further activation"
            )
        if self.total_observed_cost >= self._config.per_run_budget:
            raise ActiveBudgetError("per-run budget is exhausted")

    def _require_call_authorization(self) -> None:
        """Reserve a full call ceiling before dispatching a provider-bound step."""
        remaining = self._config.per_run_budget - self.total_observed_cost
        if remaining + 1e-12 < self._config.per_call_budget:
            raise ActiveBudgetError(
                f"remaining run authorization {remaining:.8f} cannot fit "
                f"per-call ceiling {self._config.per_call_budget:.8f}"
            )

    def _ordered_specs(self) -> list[ActiveSystemSpec]:
        """Return canonical defensive active-system declarations."""
        return [
            self._specs[active_system_id].model_copy(deep=True)
            for active_system_id in sorted(self._specs)
        ]
