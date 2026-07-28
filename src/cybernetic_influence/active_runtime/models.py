"""Strict records for the non-default pluggable active-system runtime.

The active runtime composes one ``causal-core.v2`` session.  These records own
only scheduling, bounded cognition inputs, private state, protected execution
evidence, spend, and aggregate recovery; causal state and mechanics remain in
the causal core.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from cybernetic_influence.causal_core.models import (
    CausalCheckpoint,
    CausalEvent,
    CausalRunResult,
    CausalState,
    canonical_record_digest,
    state_digest,
    trace_digest,
)
from cybernetic_influence.active_runtime.run_control import CompletionRecord

RUNTIME_CONTRACT = "active-runtime.v1"
SCHEMA_VERSION = 1

_FORBID = ConfigDict(extra="forbid", strict=True)
_ID_PATTERN = r"^[a-z][a-z0-9_]*$"
_DIGEST_PATTERN = r"^[0-9a-f]{64}$"
_ACTIVATION_PATTERN = r"^activation_[0-9]{6}$"
_EXACT_WORK_PATTERN = r"^exact_work_[0-9]{6}$"
_UNPRICED_COST_SOURCES = frozenset({"unavailable", "unspecified"})
ActivationCauseKind = Literal[
    "scenario_start",
    "observation_delivery",
    "internal_wake",
    "manual_schedule",
]


class _StrictModel(BaseModel):
    """Reject coercion and unknown fields at every persisted boundary."""

    model_config = _FORBID


class ActiveRuntimeConfig(_StrictModel):
    """Fail-loud execution and growth limits for one active run."""

    per_call_budget: float = Field(gt=0.0)
    per_run_budget: float = Field(gt=0.0)
    max_actions_per_system: int = Field(default=4, ge=0)
    max_observations_per_system: int = Field(default=100, ge=1)
    max_private_state_bytes: int = Field(default=65_536, ge=2)


class ActiveSystemSpec(_StrictModel):
    """One scheduled entity's bounded protocol and implementation binding."""

    active_system_id: str = Field(pattern=_ID_PATTERN)
    entity_id: str = Field(pattern=_ID_PATTERN)
    implementation_id: str = Field(pattern=_ID_PATTERN)
    description: str = Field(min_length=1)
    observation_port_ids: list[str] = Field(default_factory=list)
    output_port_ids: list[str] = Field(default_factory=list)
    output_port_representation_sources: dict[str, list[str]] = Field(
        default_factory=dict,
        exclude_if=lambda value: not value,
    )
    output_port_initial_representation_ids: dict[str, list[str]] = Field(
        default_factory=dict,
        exclude_if=lambda value: not value,
    )
    output_port_unavailable_when: dict[str, dict[str, JsonValue]] = Field(
        default_factory=dict,
        exclude_if=lambda value: not value,
    )
    """Exact world-state conjunctions that withdraw an output interface.

    This models technical availability, not permission: a matching rule keeps
    the port out of the bounded input and proposal validator for that snapshot.
    """
    initial_representation_ids: list[str] = Field(default_factory=list)
    initial_private_state: dict[str, JsonValue] = Field(default_factory=dict)
    initial_next_update_at: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_unique_surfaces(self) -> "ActiveSystemSpec":
        """Keep each declared projection and authority surface unambiguous."""
        _require_unique(self.observation_port_ids, "observation port ids")
        _require_unique(self.output_port_ids, "output port ids")
        _require_unique(
            self.initial_representation_ids,
            "initial representation ids",
        )
        declared_outputs = set(self.output_port_ids)
        declared_observations = set(self.observation_port_ids)
        for output_port_id, source_port_ids in (
            self.output_port_representation_sources.items()
        ):
            if output_port_id not in declared_outputs:
                raise ValueError(
                    "representation-source binding names an undeclared output "
                    f"port {output_port_id!r}"
                )
            if not source_port_ids:
                raise ValueError(
                    f"representation-source binding for {output_port_id!r} "
                    "must name at least one observation port"
                )
            _require_unique(
                source_port_ids,
                f"{output_port_id} representation-source ports",
            )
            unknown_sources = set(source_port_ids) - declared_observations
            if unknown_sources:
                raise ValueError(
                    f"representation-source binding for {output_port_id!r} "
                    f"names undeclared observation ports {sorted(unknown_sources)!r}"
                )
        declared_initial = set(self.initial_representation_ids)
        for output_port_id, representation_ids in (
            self.output_port_initial_representation_ids.items()
        ):
            if output_port_id not in declared_outputs:
                raise ValueError(
                    "initial-representation binding names an undeclared output "
                    f"port {output_port_id!r}"
                )
            if not representation_ids:
                raise ValueError(
                    f"initial-representation binding for {output_port_id!r} "
                    "must name at least one representation"
                )
            _require_unique(
                representation_ids,
                f"{output_port_id} initial representation ids",
            )
            unknown_representations = set(representation_ids) - declared_initial
            if unknown_representations:
                raise ValueError(
                    f"initial-representation binding for {output_port_id!r} "
                    "names undeclared initial representations "
                    f"{sorted(unknown_representations)!r}"
                )
        for output_port_id, unavailable_when in (
            self.output_port_unavailable_when.items()
        ):
            if output_port_id not in declared_outputs:
                raise ValueError(
                    "availability binding names an undeclared output port "
                    f"{output_port_id!r}"
                )
            if not unavailable_when:
                raise ValueError(
                    f"availability binding for {output_port_id!r} must name "
                    "at least one world fact"
                )
            if any(not fact_id.strip() for fact_id in unavailable_when):
                raise ValueError("availability binding fact ids must be non-empty")
        return self


class ActiveSystemState(_StrictModel):
    """Canonical persisted private state and observation-consumption cursor."""

    active_system_id: str = Field(pattern=_ID_PATTERN)
    entity_id: str = Field(pattern=_ID_PATTERN)
    implementation_id: str = Field(pattern=_ID_PATTERN)
    revision: int = Field(default=0, ge=0)
    activation_count: int = Field(default=0, ge=0)
    private_state: dict[str, JsonValue] = Field(default_factory=dict)
    consumed_observation_ids: list[str] = Field(default_factory=list)
    next_update_at: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_cursor(self) -> "ActiveSystemState":
        """An observation is incorporated at most once by one active system."""
        _require_unique(
            self.consumed_observation_ids,
            "consumed observation ids",
        )
        if self.revision != self.activation_count:
            raise ValueError("active-state revision must equal activation count")
        return self


class ActiveObservation(_StrictModel):
    """Agent-visible observation surface with hidden causal lineage removed."""

    observation_id: str = Field(pattern=_ID_PATTERN)
    via_port_id: str = Field(pattern=_ID_PATTERN)
    apparent_content: str = Field(min_length=1)
    apparent_source_ref: str | None = Field(default=None, pattern=_ID_PATTERN)
    representation_id: str | None = Field(default=None, pattern=_ID_PATTERN)
    logical_time: int = Field(ge=0)


class ActionInterfaceSurface(_StrictModel):
    """One exposed owned output plus currently accessible token references."""

    output_port_id: str = Field(pattern=_ID_PATTERN)
    effect_type: str = Field(pattern=_ID_PATTERN)
    description: str = Field(min_length=1)
    representation_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_representations(self) -> "ActionInterfaceSurface":
        """Do not expose the same representation reference twice."""
        _require_unique(self.representation_ids, "surface representation ids")
        return self


class ExecutionBudget(_StrictModel):
    """Budget and output envelope visible to one active-system invocation."""

    max_call_cost: float = Field(gt=0.0)
    max_actions: int = Field(ge=0)


class ActivationCause(_StrictModel):
    """One retained reason a stateful process was due at this timestamp."""

    kind: ActivationCauseKind
    scheduled_for: int = Field(ge=0)
    observation_ids: list[str] = Field(default_factory=list)
    description: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_shape(self) -> "ActivationCause":
        """Bind observation causes to observations and other causes to none."""
        _require_unique(self.observation_ids, "activation-cause observation ids")
        if self.kind == "observation_delivery":
            if not self.observation_ids:
                raise ValueError(
                    "observation-delivery activation cause requires observations"
                )
        elif self.observation_ids:
            raise ValueError(
                "only observation-delivery activation causes may name observations"
            )
        return self


class ActiveSystemInput(_StrictModel):
    """Complete bounded input built from one frozen pre-activation snapshot."""

    runtime_contract: Literal["active-runtime.v1"] = "active-runtime.v1"
    schema_version: Literal[1] = 1
    activation_id: str = Field(pattern=_ACTIVATION_PATTERN)
    active_system_id: str = Field(pattern=_ID_PATTERN)
    entity_id: str = Field(pattern=_ID_PATTERN)
    logical_time: int = Field(ge=0)
    time_unit: str = Field(pattern=_ID_PATTERN)
    activation_causes: list[ActivationCause] = Field(min_length=1)
    next_update_at: int | None = Field(default=None, ge=0)
    observations: list[ActiveObservation] = Field(default_factory=list)
    action_interfaces: list[ActionInterfaceSurface] = Field(default_factory=list)
    private_state: dict[str, JsonValue] = Field(default_factory=dict)
    budget: ExecutionBudget

    @model_validator(mode="after")
    def validate_projection(self) -> "ActiveSystemInput":
        """Keep projected observation and output identities unique."""
        _require_unique(
            [item.observation_id for item in self.observations],
            "input observation ids",
        )
        _require_unique(
            [item.output_port_id for item in self.action_interfaces],
            "input output-port ids",
        )
        if any(
            cause.scheduled_for != self.logical_time
            for cause in self.activation_causes
        ):
            raise ValueError("activation cause timestamp disagrees with input")
        caused_observations = [
            observation_id
            for cause in self.activation_causes
            for observation_id in cause.observation_ids
        ]
        _require_unique(
            caused_observations,
            "activation-cause observation ids",
        )
        input_observations = {
            observation.observation_id for observation in self.observations
        }
        if not set(caused_observations).issubset(input_observations):
            raise ValueError("activation cause names an unavailable observation")
        if any(
            observation.logical_time > self.logical_time
            for observation in self.observations
        ):
            raise ValueError("active input exposes a future observation")
        return self


def project_action_interfaces(
    spec: ActiveSystemSpec,
    observations: Sequence[ActiveObservation],
    core_state: CausalState,
    *,
    availability_fact_values: Mapping[str, JsonValue] | None = None,
) -> list[ActionInterfaceSurface]:
    """Project output ports with representation access scoped by delivery port.

    Fully unmapped outputs retain the v1 legacy surface: all declared initial
    tokens plus tokens on currently projected observations.  A port-specific
    initial binding exposes only its named initial tokens.  A source binding
    adds only current representation-bearing observations delivered through
    its named ports.  A constrained output with no accessible token is hidden.
    """

    accessible_representations = set(spec.initial_representation_ids)
    accessible_representations.update(
        observation.representation_id
        for observation in observations
        if observation.representation_id is not None
    )
    surfaces: list[ActionInterfaceSurface] = []
    for output_port_id in sorted(spec.output_port_ids):
        unavailable_when = spec.output_port_unavailable_when.get(output_port_id)
        if unavailable_when is not None and all(
            (
                availability_fact_values[fact_id]
                if availability_fact_values is not None
                else core_state.fact(fact_id).value
            )
            == expected_value
            for fact_id, expected_value in unavailable_when.items()
        ):
            continue
        initial_representation_ids = (
            spec.output_port_initial_representation_ids.get(output_port_id)
        )
        source_port_ids = spec.output_port_representation_sources.get(
            output_port_id
        )
        if initial_representation_ids is None and source_port_ids is None:
            representation_ids = accessible_representations
        else:
            representation_ids = set(initial_representation_ids or ())
            allowed_sources = set(source_port_ids or ())
            representation_ids.update(
                observation.representation_id
                for observation in observations
                if observation.via_port_id in allowed_sources
                and observation.representation_id is not None
            )
            if not representation_ids:
                continue
        port = core_state.ports[output_port_id]
        surfaces.append(
            ActionInterfaceSurface(
                output_port_id=output_port_id,
                effect_type=port.effect_type,
                description=port.description,
                representation_ids=sorted(representation_ids),
            )
        )
    return surfaces


class ActionIntent(_StrictModel):
    """Implementation-authored action content without engine identifiers."""

    output_port_id: str = Field(pattern=_ID_PATTERN)
    representation_id: str | None = Field(default=None, pattern=_ID_PATTERN)
    payload: dict[str, JsonValue] = Field(default_factory=dict)
    public_summary: str = Field(min_length=1)


class UpdateScheduleDirective(_StrictModel):
    """One explicit post-activation scheduling choice."""

    mode: Literal["preserve", "schedule", "dormant"] = "preserve"
    next_update_at: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_directive(self) -> "UpdateScheduleDirective":
        """Require a timestamp only for an explicit schedule operation."""
        if self.mode == "schedule" and self.next_update_at is None:
            raise ValueError("schedule directive requires next_update_at")
        if self.mode != "schedule" and self.next_update_at is not None:
            raise ValueError(
                "only a schedule directive may carry next_update_at"
            )
        return self


class ActiveProposal(_StrictModel):
    """One participant's private-state and action proposal."""

    active_system_id: str = Field(pattern=_ID_PATTERN)
    implementation_id: str = Field(pattern=_ID_PATTERN)
    private_state: dict[str, JsonValue] = Field(default_factory=dict)
    actions: list[ActionIntent] = Field(default_factory=list)
    update_schedule: UpdateScheduleDirective = Field(
        default_factory=UpdateScheduleDirective
    )


class ModelCallEvidence(_StrictModel):
    """Protected evidence for one provider-bound structured model call."""

    status: Literal["completed", "failed"]
    trace_id: str = Field(min_length=1)
    model: str = Field(min_length=1)
    task: str = Field(min_length=1)
    reasoning_effort: str | None = Field(
        default=None,
        min_length=1,
        exclude_if=lambda value: value is None,
    )
    system_prompt: str = Field(min_length=1)
    user_prompt: str = Field(min_length=1)
    structured_output: dict[str, JsonValue] | None = None
    cost: float | None = Field(default=None, ge=0.0)
    cost_source: str = Field(min_length=1)
    error_type: str | None = None
    error_message: str | None = None

    @model_validator(mode="after")
    def validate_call_shape(self) -> "ModelCallEvidence":
        """Distinguish decoded calls from provider failures without fake cost."""
        if self.status == "completed":
            if self.structured_output is None:
                raise ValueError("completed model call requires structured output")
            if self.error_type is not None or self.error_message is not None:
                raise ValueError("completed model call cannot contain an error")
        else:
            if self.structured_output is not None:
                raise ValueError("failed model call cannot contain structured output")
            if not self.error_type or not self.error_message:
                raise ValueError("failed model call requires error evidence")
        if self.cost is not None and self.cost_source in _UNPRICED_COST_SOURCES:
            raise ValueError("unpriced cost source cannot carry an observed price")
        return self

    @property
    def cost_observable(self) -> bool:
        """Report whether this provider-bound call has a trustworthy price."""
        return self.cost is not None


class ActiveStepResult(_StrictModel):
    """One protocol response plus protected implementation evidence."""

    proposal: ActiveProposal
    call_evidence: list[ModelCallEvidence] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_call_ids(self) -> "ActiveStepResult":
        """Do not silently merge duplicate provider trace identities."""
        _require_unique(
            [item.trace_id for item in self.call_evidence],
            "model-call trace ids",
        )
        return self


class ParticipantAttempt(_StrictModel):
    """Protected input, response, and assigned actions for one requested member."""

    requested_active_system_id: str = Field(pattern=_ID_PATTERN)
    input: ActiveSystemInput
    proposal: ActiveProposal | None = None
    call_evidence: list[ModelCallEvidence] = Field(default_factory=list)
    assigned_action_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_requested_input(self) -> "ParticipantAttempt":
        """Bind each retained input to the participant the scheduler requested."""
        if self.input.active_system_id != self.requested_active_system_id:
            raise ValueError("participant input identity mismatch")
        _require_unique(self.assigned_action_ids, "assigned action ids")
        _require_unique(
            [item.trace_id for item in self.call_evidence],
            "participant call trace ids",
        )
        if self.proposal is None and self.assigned_action_ids:
            raise ValueError("actions cannot be assigned without a proposal")
        if (
            self.proposal is not None
            and len(self.assigned_action_ids) > len(self.proposal.actions)
        ):
            raise ValueError("more action ids than proposed actions")
        return self


class ActivationAttemptRecord(_StrictModel):
    """Immutable canonical record for one successful or failed activation."""

    runtime_contract: Literal["active-runtime.v1"] = "active-runtime.v1"
    schema_version: Literal[1] = 1
    attempt_index: int = Field(ge=0)
    activation_id: str = Field(pattern=_ACTIVATION_PATTERN)
    candidate_commit_index: int = Field(ge=0)
    committed_activation_index: int | None = Field(default=None, ge=0)
    logical_time: int = Field(ge=0)
    status: Literal["committed", "failed"]
    declared_active_system_ids: list[str] = Field(min_length=1)
    participants: list[ParticipantAttempt] = Field(min_length=1)
    pre_core_state_digest: str = Field(pattern=_DIGEST_PATTERN)
    pre_core_event_tail_digest: str = Field(pattern=_DIGEST_PATTERN)
    post_core_state_digest: str | None = Field(default=None, pattern=_DIGEST_PATTERN)
    post_core_event_tail_digest: str | None = Field(
        default=None,
        pattern=_DIGEST_PATTERN,
    )
    core_event_ids: list[str] = Field(default_factory=list)
    observed_cost: float = Field(ge=0.0)
    cost_fully_observable: bool
    error_type: str | None = None
    error_message: str | None = None
    record_digest: str = Field(pattern=_DIGEST_PATTERN)

    @model_validator(mode="after")
    def validate_attempt(self) -> "ActivationAttemptRecord":
        """Bind status, participants, cost, core transition, and record digest."""
        if self.activation_id != f"activation_{self.attempt_index:06d}":
            raise ValueError("activation id must match attempt index")
        expected_ids = sorted(self.declared_active_system_ids)
        if self.declared_active_system_ids != expected_ids:
            raise ValueError("declared active-system ids must be sorted")
        _require_unique(expected_ids, "declared active-system ids")
        requested_ids = [item.requested_active_system_id for item in self.participants]
        if requested_ids != expected_ids:
            raise ValueError("participant records must match the declared set")
        _require_unique(self.core_event_ids, "activation core event ids")
        if any(
            item.input.activation_id != self.activation_id
            or item.input.logical_time != self.logical_time
            for item in self.participants
        ):
            raise ValueError("participant input context disagrees with activation")
        assigned_ids = [
            action_id
            for participant in self.participants
            for action_id in participant.assigned_action_ids
        ]
        _require_unique(assigned_ids, "activation assigned action ids")
        if assigned_ids or self.status == "committed":
            for participant_index, participant in enumerate(self.participants):
                if participant.proposal is None:
                    raise ValueError("assigned actions require every proposal")
                expected_action_ids = [
                    (
                        f"action_{self.candidate_commit_index:06d}_"
                        f"{participant_index:03d}_{action_index:03d}"
                    )
                    for action_index in range(len(participant.proposal.actions))
                ]
                if participant.assigned_action_ids != expected_action_ids:
                    raise ValueError("assigned action ids disagree with engine order")

        evidence = [
            call
            for participant in self.participants
            for call in participant.call_evidence
        ]
        expected_cost = sum(call.cost or 0.0 for call in evidence)
        if not _same_float(self.observed_cost, expected_cost):
            raise ValueError("activation observed cost disagrees with call evidence")
        expected_observable = all(call.cost_observable for call in evidence)
        if self.cost_fully_observable != expected_observable:
            raise ValueError("activation cost observability disagrees with calls")

        if self.status == "committed":
            if self.committed_activation_index != self.candidate_commit_index:
                raise ValueError("committed activation index mismatch")
            if any(item.proposal is None for item in self.participants):
                raise ValueError("committed activation requires every proposal")
            if any(
                item.proposal is not None
                and item.proposal.active_system_id
                != item.requested_active_system_id
                for item in self.participants
            ):
                raise ValueError("committed proposal identity mismatch")
            if any(
                item.proposal is not None
                and len(item.assigned_action_ids) != len(item.proposal.actions)
                for item in self.participants
            ):
                raise ValueError("committed proposal actions require assigned ids")
            if (
                self.post_core_state_digest is None
                or self.post_core_event_tail_digest is None
            ):
                raise ValueError("committed activation requires post-core binding")
            if self.error_type is not None or self.error_message is not None:
                raise ValueError("committed activation cannot contain an error")
            if not self.cost_fully_observable:
                raise ValueError("unpriced activation may not commit")
        else:
            if self.committed_activation_index is not None:
                raise ValueError("failed activation cannot have a commit index")
            if (
                self.post_core_state_digest is not None
                or self.post_core_event_tail_digest is not None
                or self.core_event_ids
            ):
                raise ValueError("failed activation cannot claim a core commit")
            if not self.error_type or not self.error_message:
                raise ValueError("failed activation requires error evidence")

        if self.record_digest != canonical_record_digest(
            self.model_dump(mode="json", exclude={"record_digest"})
        ):
            raise ValueError("activation-attempt record digest mismatch")
        return self


class ExactWorkRecord(_StrictModel):
    """One retained exact-only transition between active-system activations."""

    work_index: int = Field(ge=0)
    work_id: str = Field(pattern=_EXACT_WORK_PATTERN)
    prior_attempt_count: int = Field(ge=0)
    logical_time: int = Field(ge=0)
    pre_core_state_digest: str = Field(pattern=_DIGEST_PATTERN)
    pre_core_event_tail_digest: str = Field(pattern=_DIGEST_PATTERN)
    post_core_state_digest: str = Field(pattern=_DIGEST_PATTERN)
    post_core_event_tail_digest: str = Field(pattern=_DIGEST_PATTERN)
    core_event_ids: list[str] = Field(min_length=1)
    record_digest: str = Field(pattern=_DIGEST_PATTERN)

    @model_validator(mode="after")
    def validate_exact_work(self) -> "ExactWorkRecord":
        """Bind exact work to one contiguous, independently inspectable range."""
        if self.work_id != f"exact_work_{self.work_index:06d}":
            raise ValueError("exact-work id must match its index")
        _require_unique(self.core_event_ids, "exact-work core event ids")
        if self.record_digest != canonical_record_digest(
            self.model_dump(mode="json", exclude={"record_digest"})
        ):
            raise ValueError("exact-work record digest mismatch")
        return self


RuntimeProgressKind = Literal[
    "activation_started",
    "causal_moment_committed",
    "exact_work_committed",
    "activation_failed",
]


class RuntimeProgressUpdate(_StrictModel):
    """One observer-safe lifecycle update from the shared active runtime.

    The update names only public execution identities.  The paired checkpoint
    supplied to an observer remains the authoritative continuation artifact;
    presentation code must project it before exposing anything to an analyst.
    """

    kind: RuntimeProgressKind
    logical_time: int = Field(ge=0)
    participant_ids: list[str] = Field(default_factory=list)
    activation_id: str | None = Field(default=None, pattern=_ACTIVATION_PATTERN)
    exact_work_id: str | None = Field(default=None, pattern=_EXACT_WORK_PATTERN)
    event_ids: list[str] = Field(default_factory=list)
    state_revision: int = Field(ge=0)
    checkpoint_digest: str = Field(pattern=_DIGEST_PATTERN)

    @model_validator(mode="after")
    def validate_progress_shape(self) -> "RuntimeProgressUpdate":
        if self.participant_ids != sorted(set(self.participant_ids)):
            raise ValueError("progress participant ids must be unique and sorted")
        if self.event_ids != sorted(set(self.event_ids)):
            raise ValueError("progress event ids must be unique and sorted")
        if self.kind == "activation_started":
            if self.activation_id is None or not self.participant_ids:
                raise ValueError("activation start requires an activation and participants")
            if self.exact_work_id is not None or self.event_ids:
                raise ValueError("activation start cannot claim exact work or events")
        elif self.kind == "causal_moment_committed":
            if self.activation_id is None or not self.participant_ids:
                raise ValueError("committed activation requires an activation and participants")
            if self.exact_work_id is not None:
                raise ValueError("committed activation cannot name exact work")
        elif self.kind == "exact_work_committed":
            if self.exact_work_id is None:
                raise ValueError("exact-work progress requires an exact-work id")
            if self.activation_id is not None or self.participant_ids:
                raise ValueError("exact-work progress cannot name an activation or participants")
            if not self.event_ids:
                raise ValueError("exact-work progress requires retained events")
        else:
            if self.activation_id is None or not self.participant_ids:
                raise ValueError("failed activation requires an activation and participants")
            if self.exact_work_id is not None or self.event_ids:
                raise ValueError("failed activation cannot claim committed work")
        return self


class ActiveRuntimeCheckpoint(_StrictModel):
    """Complete nonterminal continuation record for one active runtime."""

    runtime_contract: Literal["active-runtime.v1"] = "active-runtime.v1"
    schema_version: Literal[1] = 1
    run_id: str = Field(pattern=_ID_PATTERN)
    scenario_id: str = Field(pattern=_ID_PATTERN)
    scenario_fingerprint: str = Field(pattern=_DIGEST_PATTERN)
    scenario_execution_fingerprint: str = Field(pattern=_DIGEST_PATTERN)
    config: ActiveRuntimeConfig
    specs: list[ActiveSystemSpec] = Field(min_length=1)
    states: dict[str, ActiveSystemState]
    core_checkpoint: CausalCheckpoint
    attempts: list[ActivationAttemptRecord] = Field(default_factory=list)
    exact_work: list[ExactWorkRecord] = Field(default_factory=list)
    next_attempt_index: int = Field(ge=0)
    next_commit_index: int = Field(ge=0)
    total_observed_cost: float = Field(ge=0.0)
    cost_fully_observable: bool
    record_digest: str = Field(pattern=_DIGEST_PATTERN)

    @model_validator(mode="after")
    def validate_checkpoint(self) -> "ActiveRuntimeCheckpoint":
        """Reject corrupt aggregate state before any continuation is possible."""
        _validate_enclosing_core(
            run_id=self.run_id,
            scenario_id=self.scenario_id,
            scenario_fingerprint=self.scenario_fingerprint,
            scenario_execution_fingerprint=self.scenario_execution_fingerprint,
            core=self.core_checkpoint,
        )
        _validate_specs_and_states(self.specs, self.states)
        _validate_attempt_ledger(
            attempts=self.attempts,
            exact_work=self.exact_work,
            specs=self.specs,
            states=self.states,
            core=self.core_checkpoint,
            config=self.config,
            next_attempt_index=self.next_attempt_index,
            next_commit_index=self.next_commit_index,
            total_observed_cost=self.total_observed_cost,
            cost_fully_observable=self.cost_fully_observable,
        )
        _validate_consumed_observations(self.states, self.core_checkpoint.state)
        if self.total_observed_cost > self.config.per_run_budget:
            # A provider can cross a post-hoc cap; the failure remains forensic.
            if not self.attempts or self.attempts[-1].status != "failed":
                raise ValueError("over-budget checkpoint lacks failed-attempt evidence")
        if self.record_digest != canonical_record_digest(
            self.model_dump(mode="json", exclude={"record_digest"})
        ):
            raise ValueError("active-runtime checkpoint record digest mismatch")
        return self


class ActiveRuntimeResult(_StrictModel):
    """Completed active trajectory with exact world and protected cognition evidence."""

    runtime_contract: Literal["active-runtime.v1"] = "active-runtime.v1"
    schema_version: Literal[1] = 1
    run_id: str = Field(pattern=_ID_PATTERN)
    scenario_id: str = Field(pattern=_ID_PATTERN)
    scenario_fingerprint: str = Field(pattern=_DIGEST_PATTERN)
    scenario_execution_fingerprint: str = Field(pattern=_DIGEST_PATTERN)
    status: Literal["completed"] = "completed"
    config: ActiveRuntimeConfig
    specs: list[ActiveSystemSpec] = Field(min_length=1)
    final_states: dict[str, ActiveSystemState]
    core_result: CausalRunResult
    attempts: list[ActivationAttemptRecord] = Field(default_factory=list)
    exact_work: list[ExactWorkRecord] = Field(default_factory=list)
    next_attempt_index: int = Field(ge=0)
    next_commit_index: int = Field(ge=0)
    model_calls: int = Field(ge=0)
    total_observed_cost: float = Field(ge=0.0)
    cost_fully_observable: bool
    completion: CompletionRecord | None = None
    outcome_summary: str = Field(min_length=1)
    record_digest: str = Field(pattern=_DIGEST_PATTERN)

    @model_validator(mode="after")
    def validate_result(self) -> "ActiveRuntimeResult":
        """Bind the terminal exact trace to active state and call evidence."""
        _validate_enclosing_core(
            run_id=self.run_id,
            scenario_id=self.scenario_id,
            scenario_fingerprint=self.scenario_fingerprint,
            scenario_execution_fingerprint=self.scenario_execution_fingerprint,
            core=self.core_result,
        )
        _validate_specs_and_states(self.specs, self.final_states)
        _validate_attempt_ledger(
            attempts=self.attempts,
            exact_work=self.exact_work,
            specs=self.specs,
            states=self.final_states,
            core=self.core_result,
            config=self.config,
            next_attempt_index=self.next_attempt_index,
            next_commit_index=self.next_commit_index,
            total_observed_cost=self.total_observed_cost,
            cost_fully_observable=self.cost_fully_observable,
        )
        _validate_consumed_observations(
            self.final_states,
            self.core_result.final_state,
        )
        calls = sum(
            len(participant.call_evidence)
            for attempt in self.attempts
            for participant in attempt.participants
        )
        if self.model_calls != calls:
            raise ValueError("model-call count disagrees with protected evidence")
        if self.record_digest != canonical_record_digest(
            self.model_dump(mode="json", exclude={"record_digest"})
        ):
            raise ValueError("active-runtime result record digest mismatch")
        return self


def private_state_digest(state: Mapping[str, JsonValue]) -> str:
    """Return a stable protected digest for one implementation-private state."""
    return canonical_record_digest(dict(state))


def active_input_digest(active_input: ActiveSystemInput) -> str:
    """Bind a retained participant input to its exact protected contents."""
    return canonical_record_digest(active_input.model_dump(mode="json"))


def private_state_size(state: Mapping[str, JsonValue]) -> int:
    """Measure canonical UTF-8 bytes for the configured fail-loud state limit."""
    rendered = json.dumps(dict(state), sort_keys=True, separators=(",", ":"))
    return len(rendered.encode("utf-8"))


def with_record_digest(value: Mapping[str, object]) -> dict[str, object]:
    """Return a JSON-shaped record with its non-authenticating integrity digest."""
    output = dict(value)
    output["record_digest"] = canonical_record_digest(output)
    return output


def _validate_specs_and_states(
    specs: Sequence[ActiveSystemSpec],
    states: Mapping[str, ActiveSystemState],
) -> None:
    """Bind each persisted state to exactly one immutable active declaration."""
    spec_ids = [item.active_system_id for item in specs]
    if spec_ids != sorted(spec_ids):
        raise ValueError("active-system specs must be sorted")
    _require_unique(spec_ids, "active-system spec ids")
    _require_unique([item.entity_id for item in specs], "active-system entity ids")
    if set(states) != set(spec_ids):
        raise ValueError("active-system states do not match specs")
    for spec in specs:
        state = states[spec.active_system_id]
        if (
            state.active_system_id != spec.active_system_id
            or state.entity_id != spec.entity_id
            or state.implementation_id != spec.implementation_id
        ):
            raise ValueError("active-system state identity does not match spec")
        if state.revision == 0:
            if private_state_digest(state.private_state) != private_state_digest(
                spec.initial_private_state
            ):
                raise ValueError("inactive private state differs from its initial spec")
            if state.consumed_observation_ids:
                raise ValueError("inactive system cannot have consumed observations")
            if state.next_update_at != spec.initial_next_update_at:
                raise ValueError(
                    "inactive system schedule differs from its initial spec"
                )


def _validate_attempt_ledger(
    *,
    attempts: Sequence[ActivationAttemptRecord],
    exact_work: Sequence[ExactWorkRecord],
    specs: Sequence[ActiveSystemSpec],
    states: Mapping[str, ActiveSystemState],
    core: CausalCheckpoint | CausalRunResult,
    config: ActiveRuntimeConfig,
    next_attempt_index: int,
    next_commit_index: int,
    total_observed_cost: float,
    cost_fully_observable: bool,
) -> None:
    """Cross-check attempt order, committed actions, states, and spend."""
    if [item.attempt_index for item in attempts] != list(range(len(attempts))):
        raise ValueError("activation attempt indexes must be contiguous")
    if next_attempt_index != len(attempts):
        raise ValueError("next attempt index disagrees with attempt ledger")
    _require_unique(
        [
            call.trace_id
            for attempt in attempts
            for participant in attempt.participants
            for call in participant.call_evidence
        ],
        "runtime model-call trace ids",
    )
    committed = [item for item in attempts if item.status == "committed"]
    if [item.committed_activation_index for item in committed] != list(
        range(len(committed))
    ):
        raise ValueError("committed activation indexes must be contiguous")
    if next_commit_index != len(committed):
        raise ValueError("next commit index disagrees with committed attempts")
    for expected_commit_index, attempt in enumerate(committed):
        if attempt.candidate_commit_index != expected_commit_index:
            raise ValueError("candidate commit index disagrees with committed order")
    committed_so_far = 0
    for attempt in attempts:
        if attempt.candidate_commit_index != committed_so_far:
            raise ValueError("attempt candidate commit index is not recoverable")
        if attempt.status == "committed":
            committed_so_far += 1
    expected_actions = [
        action_id
        for attempt in committed
        for participant in attempt.participants
        for action_id in participant.assigned_action_ids
    ]
    if list(core.accepted_action_ids) != expected_actions:
        raise ValueError("causal-core actions disagree with committed activations")

    spec_by_id = {spec.active_system_id: spec for spec in specs}
    expected_private = {
        active_system_id: dict(spec.initial_private_state)
        for active_system_id, spec in spec_by_id.items()
    }
    expected_consumed: dict[str, list[str]] = {
        active_system_id: [] for active_system_id in states
    }
    expected_revisions = {active_system_id: 0 for active_system_id in states}
    expected_next_update_at = {
        active_system_id: spec.initial_next_update_at
        for active_system_id, spec in spec_by_id.items()
    }
    core_state = (
        core.state if isinstance(core, CausalCheckpoint) else core.final_state
    )
    time_unit = core.events[0].details.get("time_unit")
    if not isinstance(time_unit, str):
        raise ValueError("causal run lacks its scenario time unit")
    guarded_fact_ids = {
        fact_id
        for spec in specs
        for unavailable_when in spec.output_port_unavailable_when.values()
        for fact_id in unavailable_when
    }
    availability_fact_values: dict[str, JsonValue] = {}
    for fact_id in guarded_fact_ids:
        first_change = next(
            (
                change
                for event in core.events
                if event.patch is not None
                for change in event.patch.fact_changes
                if change.fact_id == fact_id
            ),
            None,
        )
        availability_fact_values[fact_id] = (
            first_change.before
            if first_change is not None
            else core_state.fact(fact_id).value
        )
    event_by_id = {event.event_id: event for event in core.events}
    exact_work_by_prior_attempt_count: dict[int, list[ExactWorkRecord]] = {}
    for record in exact_work:
        exact_work_by_prior_attempt_count.setdefault(
            record.prior_attempt_count, []
        ).append(record)

    def apply_availability_history(event_ids: Sequence[str]) -> None:
        for event_id in event_ids:
            event = event_by_id[event_id]
            if event.patch is None:
                continue
            for change in event.patch.fact_changes:
                if change.fact_id in availability_fact_values:
                    if availability_fact_values[change.fact_id] != change.before:
                        raise ValueError(
                            "availability fact history disagrees with causal patch"
                        )
                    availability_fact_values[change.fact_id] = change.after

    for attempt_index, attempt in enumerate(attempts):
        for record in exact_work_by_prior_attempt_count.get(attempt_index, []):
            apply_availability_history(record.core_event_ids)
        for participant in attempt.participants:
            active_system_id = participant.requested_active_system_id
            spec = spec_by_id[active_system_id]
            if participant.input.entity_id != spec.entity_id:
                raise ValueError("attempt input entity disagrees with active spec")
            if private_state_digest(
                participant.input.private_state
            ) != private_state_digest(expected_private[active_system_id]):
                raise ValueError("attempt input private state is not the prior commit")
            if participant.input.next_update_at != expected_next_update_at[
                active_system_id
            ]:
                raise ValueError(
                    "attempt input schedule is not the prior committed schedule"
                )
            if participant.input.time_unit != time_unit:
                raise ValueError("attempt input time unit disagrees with scenario")
            if (
                not _same_float(
                    participant.input.budget.max_call_cost,
                    config.per_call_budget,
                )
                or participant.input.budget.max_actions
                != config.max_actions_per_system
            ):
                raise ValueError("attempt input budget disagrees with runtime limits")
            expected_surfaces = [
                surface.model_dump(mode="json")
                for surface in project_action_interfaces(
                    spec,
                    participant.input.observations,
                    core_state,
                    availability_fact_values=availability_fact_values,
                )
            ]
            actual_surfaces = [
                surface.model_dump(mode="json")
                for surface in participant.input.action_interfaces
            ]
            if canonical_record_digest(actual_surfaces) != canonical_record_digest(
                expected_surfaces
            ):
                raise ValueError("attempt action surfaces disagree with active spec")
            for observation in participant.input.observations:
                if observation.via_port_id not in spec.observation_port_ids:
                    raise ValueError("attempt input used an undeclared observation port")
                if observation.observation_id in expected_consumed[active_system_id]:
                    raise ValueError("attempt re-presented a consumed observation")
                canonical_observation = core_state.observations.get(
                    observation.observation_id
                )
                if canonical_observation is None:
                    raise ValueError("attempt input contains an unknown observation")
                expected_observation = {
                    "observation_id": canonical_observation.observation_id,
                    "via_port_id": canonical_observation.via_port_id,
                    "apparent_content": canonical_observation.apparent_content,
                    "apparent_source_ref": canonical_observation.apparent_source_ref,
                    "representation_id": canonical_observation.representation_id,
                    "logical_time": canonical_observation.logical_time,
                }
                if canonical_record_digest(
                    observation.model_dump(mode="json")
                ) != canonical_record_digest(expected_observation):
                    raise ValueError(
                        "attempt observation surface disagrees with causal state"
                    )
                if canonical_observation.target_entity_id != spec.entity_id:
                    raise ValueError("attempt observation targets another entity")
            if attempt.status == "committed":
                proposal = participant.proposal
                if proposal is None:  # pragma: no cover - record validates first
                    raise AssertionError("committed participant lacks proposal")
                if proposal.implementation_id != spec.implementation_id:
                    raise ValueError("committed implementation identity mismatch")
                expected_private[active_system_id] = dict(proposal.private_state)
                expected_next_update_at[active_system_id] = (
                    _next_update_after_proposal(
                        expected_next_update_at[active_system_id],
                        proposal,
                        logical_time=participant.input.logical_time,
                    )
                )
                expected_consumed[active_system_id].extend(
                    observation.observation_id
                    for observation in participant.input.observations
                )
                expected_revisions[active_system_id] += 1
        apply_availability_history(attempt.core_event_ids)
    for record in exact_work_by_prior_attempt_count.get(len(attempts), []):
        apply_availability_history(record.core_event_ids)
    for active_system_id, state in states.items():
        if state.revision != expected_revisions[active_system_id]:
            raise ValueError("active-state revisions disagree with activation ledger")
        if private_state_digest(state.private_state) != private_state_digest(
            expected_private[active_system_id]
        ):
            raise ValueError("final private state disagrees with activation ledger")
        if state.consumed_observation_ids != expected_consumed[active_system_id]:
            raise ValueError("observation cursor disagrees with activation ledger")
        if state.next_update_at != expected_next_update_at[active_system_id]:
            raise ValueError("active-state schedule disagrees with activation ledger")

    _validate_core_attempt_slices(attempts, exact_work, core)
    expected_cost = sum(item.observed_cost for item in attempts)
    if not _same_float(total_observed_cost, expected_cost):
        raise ValueError("runtime total cost disagrees with attempt ledger")
    expected_observable = all(item.cost_fully_observable for item in attempts)
    if cost_fully_observable != expected_observable:
        raise ValueError("runtime cost observability disagrees with attempts")


def _validate_consumed_observations(
    states: Mapping[str, ActiveSystemState],
    core_state: CausalState,
) -> None:
    """Require every consumed cursor entry to name its entity's real observation."""
    observations = core_state.observations
    for state in states.values():
        for observation_id in state.consumed_observation_ids:
            observation = observations.get(observation_id)
            if observation is None:
                raise ValueError("active state consumed an unknown observation")
            if observation.target_entity_id != state.entity_id:
                raise ValueError("active state consumed another entity's observation")


def _next_update_after_proposal(
    prior: int | None,
    proposal: ActiveProposal,
    *,
    logical_time: int,
) -> int | None:
    """Replay one scheduling directive without importing the runtime engine."""
    directive = proposal.update_schedule
    if directive.mode == "schedule":
        if (
            directive.next_update_at is None
            or directive.next_update_at <= logical_time
        ):
            raise ValueError("scheduled update is not strictly in the future")
        return directive.next_update_at
    if directive.mode == "dormant":
        return None
    return prior if prior is not None and prior > logical_time else None


def _validate_enclosing_core(
    *,
    run_id: str,
    scenario_id: str,
    scenario_fingerprint: str,
    scenario_execution_fingerprint: str,
    core: CausalCheckpoint | CausalRunResult,
) -> None:
    """Bind an aggregate artifact to exactly one causal-core execution."""
    if core.run_id != run_id or core.scenario_id != scenario_id:
        raise ValueError("active runtime and causal core identity mismatch")
    if core.scenario_fingerprint != scenario_fingerprint:
        raise ValueError("active runtime and causal scenario fingerprint mismatch")
    if core.scenario_execution_fingerprint != scenario_execution_fingerprint:
        raise ValueError("active runtime and core execution fingerprint mismatch")


def _validate_core_attempt_slices(
    attempts: Sequence[ActivationAttemptRecord],
    exact_work: Sequence[ExactWorkRecord],
    core: CausalCheckpoint | CausalRunResult,
) -> None:
    """Bind activation event ranges and state digests to exact core prefixes."""
    events = core.events
    terminal_offset = 1 if isinstance(core, CausalRunResult) else 0
    event_limit = len(events) - terminal_offset
    _require_unique([item.work_id for item in exact_work], "exact-work ids")
    if [item.work_index for item in exact_work] != list(range(len(exact_work))):
        raise ValueError("exact-work indexes must be contiguous")
    work_by_prior_count: dict[int, list[ExactWorkRecord]] = {}
    for item in exact_work:
        if item.prior_attempt_count > len(attempts):
            raise ValueError("exact work names a future attempt count")
        work_by_prior_count.setdefault(item.prior_attempt_count, []).append(item)

    cursor = 1

    def consume_exact(item: ExactWorkRecord) -> int:
        nonlocal cursor
        if item.pre_core_event_tail_digest != trace_digest(events[:cursor]):
            raise ValueError("exact work pre-core tail is not the prior prefix")
        if item.pre_core_state_digest != _prefix_state_digest(events, cursor, core):
            raise ValueError("exact work pre-core state is not the prior prefix")
        stop = cursor + len(item.core_event_ids)
        if stop > event_limit:
            raise ValueError("exact-work event range exceeds the causal trace")
        if [event.event_id for event in events[cursor:stop]] != item.core_event_ids:
            raise ValueError("exact-work event range is not contiguous")
        if item.post_core_event_tail_digest != trace_digest(events[:stop]):
            raise ValueError("exact-work post-core tail disagrees with its range")
        if item.post_core_state_digest != _prefix_state_digest(events, stop, core):
            raise ValueError("exact-work post-core state disagrees with its range")
        cursor = stop
        return cursor

    for attempt_index, attempt in enumerate(attempts):
        for item in work_by_prior_count.get(attempt_index, []):
            consume_exact(item)
        expected_pre_events = events[:cursor]
        if attempt.pre_core_event_tail_digest != trace_digest(expected_pre_events):
            raise ValueError("attempt pre-core event tail is not the prior prefix")
        expected_pre_state = _prefix_state_digest(events, cursor, core)
        if attempt.pre_core_state_digest != expected_pre_state:
            raise ValueError("attempt pre-core state is not the prior prefix")
        available_observation_ids = {
            event.observation_id
            for event in events[:cursor]
            if event.event_kind == "observation_delivered"
            and event.observation_id is not None
        }
        for participant in attempt.participants:
            unseen = {
                observation.observation_id
                for observation in participant.input.observations
            } - available_observation_ids
            if unseen:
                raise ValueError(
                    "attempt input contains observations unavailable at its snapshot"
                )
        if attempt.status == "failed":
            continue
        stop = cursor + len(attempt.core_event_ids)
        if stop > event_limit:
            raise ValueError("activation core event range exceeds the causal trace")
        actual_ids = [event.event_id for event in events[cursor:stop]]
        if actual_ids != attempt.core_event_ids:
            raise ValueError("activation core event range is not contiguous")
        cursor = stop
        if attempt.post_core_event_tail_digest != trace_digest(events[:cursor]):
            raise ValueError("attempt post-core event tail disagrees with its range")
        if attempt.post_core_state_digest != _prefix_state_digest(events, cursor, core):
            raise ValueError("attempt post-core state disagrees with its range")
    for item in work_by_prior_count.get(len(attempts), []):
        consume_exact(item)
    if cursor != event_limit:
        raise ValueError("causal-core events are not owned by committed activations")


def _prefix_state_digest(
    events: Sequence[CausalEvent],
    stop: int,
    core: CausalCheckpoint | CausalRunResult,
) -> str:
    """Recover the typed state digest at one canonical event prefix."""
    commits = [
        event.patch
        for event in events[:stop]
        if event.event_kind == "state_committed" and event.patch is not None
    ]
    if commits:
        return commits[-1].after_digest
    later_commits = [
        event.patch
        for event in events[stop:]
        if event.event_kind == "state_committed" and event.patch is not None
    ]
    if later_commits:
        return later_commits[0].before_digest
    final_state = (
        core.state if isinstance(core, CausalCheckpoint) else core.final_state
    )
    return state_digest(final_state)


def _require_unique(values: Sequence[str], label: str) -> None:
    """Reject duplicate identities without silently normalizing input."""
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must be unique")


def _same_float(left: float, right: float) -> bool:
    """Compare accumulated prices at a precision tighter than billed evidence."""
    return abs(left - right) <= 1e-12
