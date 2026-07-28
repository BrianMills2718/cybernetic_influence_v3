"""Visibility-safe temporal projection for the analyst-facing simulator."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from cybernetic_influence.active_runtime import (
    ActivationAttemptRecord,
    ActiveRuntimeResult,
    ActiveRuntimeCheckpoint,
    ExactWorkRecord,
    RuntimeProgressUpdate,
)

AnalystAnimationKind = Literal[
    "action_attempt",
    "information_transfer",
    "mechanism_accepted",
    "mechanism_denied",
    "state_changed",
    "observation_delivered",
    "effect_dissipated",
]


class AnalystAnimationCue(BaseModel):
    """One analyst-safe visual cue derived from a retained causal event."""

    model_config = ConfigDict(extra="forbid", strict=True)

    cue_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    kind: AnalystAnimationKind
    label: str = Field(min_length=1)
    source_id: str | None = None
    target_id: str | None = None
    edge_ids: list[str] = Field(default_factory=list)
    causal_parent_event_ids: list[str] = Field(default_factory=list)


class BoundaryProjectionError(ValueError):
    """Retained evidence cannot support a safe analytical-boundary account."""


class BoundaryCrossing(BaseModel):
    """One realized exact route crossing an execution-inert boundary."""

    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal[1] = 1
    crossing_id: str = Field(min_length=1)
    boundary_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    sequence: int
    causal_time: int | None = None
    direction: Literal["incoming", "outgoing"]
    source_ref: str = Field(min_length=1)
    target_ref: str = Field(min_length=1)
    route_kind: Literal["connection", "container"]
    route_ref: str = Field(min_length=1)
    effect_id: str = Field(min_length=1)
    representation_id: str | None = None

    @model_validator(mode="after")
    def validate_identity(self) -> "BoundaryCrossing":
        if self.crossing_id != (
            f"boundary_crossing_{self.boundary_id}_{self.event_id}"
        ):
            raise ValueError("boundary crossing ID does not match its evidence")
        return self


class BoundaryCoordinationEpisode(BaseModel):
    """One exact causal episode anchored by output or an unmatched input."""

    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal[1] = 1
    episode_id: str = Field(min_length=1)
    boundary_id: str = Field(min_length=1)
    status: Literal["completed", "in_progress"]
    input_crossing_ids: list[str]
    prior_output_crossing_ids: list[str]
    trigger_event_ids: list[str]
    internal_event_ids: list[str]
    output_crossing_id: str | None
    external_result_event_ids: list[str]
    contributing_member_ids: list[str]
    start_sequence: int
    end_sequence: int | None = None

    @model_validator(mode="after")
    def validate_episode(self) -> "BoundaryCoordinationEpisode":
        lists = (
            self.input_crossing_ids,
            self.prior_output_crossing_ids,
            self.trigger_event_ids,
            self.internal_event_ids,
            self.external_result_event_ids,
            self.contributing_member_ids,
        )
        if any(len(items) != len(set(items)) for items in lists):
            raise ValueError("boundary episode lists must contain unique IDs")
        if self.status == "completed":
            if self.output_crossing_id is None or self.end_sequence is None:
                raise ValueError("completed boundary episode requires an output")
            expected = (
                f"boundary_episode_{self.boundary_id}_"
                f"{self.output_crossing_id.removeprefix(f'boundary_crossing_{self.boundary_id}_')}"
            )
        else:
            if self.output_crossing_id is not None or self.end_sequence is not None:
                raise ValueError("in-progress boundary episode cannot claim an output")
            if len(self.input_crossing_ids) != 1:
                raise ValueError("in-progress boundary episode requires one input")
            input_event_id = self.input_crossing_ids[0].removeprefix(
                f"boundary_crossing_{self.boundary_id}_"
            )
            expected = f"boundary_episode_{self.boundary_id}_{input_event_id}"
        if self.episode_id != expected:
            raise ValueError("boundary episode ID does not match its anchor")
        return self


class BoundaryActivityProjection(BaseModel):
    """Strict server-owned boundary activity over one retained event prefix."""

    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal[1] = 1
    boundary_id: str = Field(min_length=1)
    crossings: list[BoundaryCrossing]
    episodes: list[BoundaryCoordinationEpisode]

    @model_validator(mode="after")
    def validate_projection(self) -> "BoundaryActivityProjection":
        crossing_ids = [item.crossing_id for item in self.crossings]
        episode_ids = [item.episode_id for item in self.episodes]
        if len(crossing_ids) != len(set(crossing_ids)):
            raise ValueError("boundary projection has duplicate crossings")
        if len(episode_ids) != len(set(episode_ids)):
            raise ValueError("boundary projection has duplicate episodes")
        if any(item.boundary_id != self.boundary_id for item in self.crossings):
            raise ValueError("boundary crossing belongs to another boundary")
        if any(item.boundary_id != self.boundary_id for item in self.episodes):
            raise ValueError("boundary episode belongs to another boundary")
        if [item.sequence for item in self.crossings] != sorted(
            item.sequence for item in self.crossings
        ):
            raise ValueError("boundary crossings must follow canonical sequence")
        return self


def validate_retained_boundary_activities(
    document: Mapping[str, object],
) -> None:
    """Fail reopening when retained typed activity has dangling evidence."""
    raw_boundaries = document.get("boundaries", [])
    raw_events = document.get("events", [])
    if not isinstance(raw_boundaries, list) or not isinstance(raw_events, list):
        raise ValueError("retained boundary activity envelope is malformed")
    events = {
        str(item["event_id"]): item
        for item in raw_events
        if isinstance(item, dict) and isinstance(item.get("event_id"), str)
    }
    if len(events) != len(raw_events):
        raise ValueError("retained boundary activity has malformed events")
    for raw_boundary in raw_boundaries:
        if not isinstance(raw_boundary, dict):
            raise ValueError("retained boundary is malformed")
        raw_activity = raw_boundary.get("activity")
        if raw_activity is None:
            continue
        activity = BoundaryActivityProjection.model_validate(raw_activity)
        if activity.boundary_id != raw_boundary.get("id"):
            raise ValueError("retained activity belongs to another boundary")
        raw_index = raw_boundary.get("activity_event_index")
        if not isinstance(raw_index, list) or len(raw_index) != len(events):
            raise ValueError("retained boundary event index is incomplete")
        raw_snapshots = raw_boundary.get("snapshots")
        if not isinstance(raw_snapshots, dict):
            raise ValueError("retained boundary snapshots are malformed")
        known_members: set[str] = set()
        for snapshot in raw_snapshots.values():
            if not isinstance(snapshot, dict):
                raise ValueError("retained boundary snapshot is malformed")
            raw_members = snapshot.get("member_ids")
            if not isinstance(raw_members, list) or not all(
                isinstance(member_id, str) for member_id in raw_members
            ):
                raise ValueError("retained boundary members are malformed")
            known_members.update(cast(list[str], raw_members))
        indexed_ids: set[str] = set()
        for item in raw_index:
            if not isinstance(item, dict):
                raise ValueError("retained boundary event index is malformed")
            event_id = item.get("event_id")
            contributors = item.get("contributing_member_ids")
            if (
                not isinstance(event_id, str)
                or event_id in indexed_ids
                or event_id not in events
                or item.get("sequence") != events[event_id].get("sequence")
                or not isinstance(item.get("boundary_relevant"), bool)
                or not isinstance(contributors, list)
                or not all(isinstance(value, str) for value in contributors)
                or len(contributors) != len(set(contributors))
                or not set(cast(list[str], contributors)).issubset(known_members)
            ):
                raise ValueError("retained boundary event index is malformed")
            indexed_ids.add(event_id)
        crossing_ids = {item.crossing_id: item for item in activity.crossings}
        for crossing in activity.crossings:
            event = events.get(crossing.event_id)
            if event is None:
                raise ValueError("retained crossing references an unknown event")
            if event.get("event_kind") != "effect_routed":
                raise ValueError("retained crossing does not reference a routed effect")
            if event.get("sequence") != crossing.sequence:
                raise ValueError("retained crossing sequence disagrees with evidence")
            route_field = (
                "connection_id"
                if crossing.route_kind == "connection"
                else "container_id"
            )
            other_route_field = (
                "container_id"
                if crossing.route_kind == "connection"
                else "connection_id"
            )
            if (
                event.get("route_kind") != crossing.route_kind
                or event.get(route_field) != crossing.route_ref
                or event.get(other_route_field) is not None
                or event.get("effect_id") != crossing.effect_id
                or event.get("representation_id") != crossing.representation_id
            ):
                raise ValueError("retained crossing disagrees with exact route evidence")
        for episode in activity.episodes:
            for crossing_id in [
                *episode.input_crossing_ids,
                *episode.prior_output_crossing_ids,
                *([episode.output_crossing_id] if episode.output_crossing_id else []),
            ]:
                if crossing_id not in crossing_ids:
                    raise ValueError("retained episode references an unknown crossing")
            for event_id in [
                *episode.trigger_event_ids,
                *episode.internal_event_ids,
                *episode.external_result_event_ids,
            ]:
                if event_id not in events:
                    raise ValueError("retained episode references an unknown event")
            for event_ids in (
                episode.trigger_event_ids,
                episode.internal_event_ids,
                episode.external_result_event_ids,
            ):
                if [events[item]["sequence"] for item in event_ids] != sorted(
                    events[item]["sequence"] for item in event_ids
                ):
                    raise ValueError("retained episode events are not canonically ordered")


def clip_boundary_activity_projection(
    activity: BoundaryActivityProjection,
    events: Sequence[Mapping[str, object]],
    event_index: Sequence[Mapping[str, object]],
    *,
    through_sequence: int,
) -> BoundaryActivityProjection:
    """Reconstruct one exact selected prefix from server-retained event facts."""
    event_by_id: dict[str, Mapping[str, object]] = {}
    for event in events:
        event_id = event.get("event_id")
        sequence = event.get("sequence")
        if (
            not isinstance(event_id, str)
            or not isinstance(sequence, int)
            or isinstance(sequence, bool)
            or event_id in event_by_id
        ):
            raise ValueError("retained activity evidence is malformed")
        if sequence <= through_sequence:
            unknown_parents = set(cast(list[str], event.get("causal_parent_event_ids", []))) - set(event_by_id)
            if unknown_parents:
                raise ValueError("retained activity has unknown or future parents")
            event_by_id[event_id] = event

    indexed: dict[str, Mapping[str, object]] = {}
    for item in event_index:
        event_id = item.get("event_id")
        sequence = item.get("sequence")
        relevant = item.get("boundary_relevant")
        contributors = item.get("contributing_member_ids")
        if (
            not isinstance(event_id, str)
            or event_id in indexed
            or not isinstance(sequence, int)
            or isinstance(sequence, bool)
            or not isinstance(relevant, bool)
            or not isinstance(contributors, list)
            or not all(isinstance(value, str) for value in contributors)
            or len(contributors) != len(set(contributors))
        ):
            raise ValueError("retained boundary event index is malformed")
        if event_id in event_by_id:
            if event_by_id[event_id].get("sequence") != sequence:
                raise ValueError("boundary event index sequence disagrees with evidence")
            indexed[event_id] = item
    if set(indexed) != set(event_by_id):
        raise ValueError("boundary event index does not cover the selected prefix")

    crossings = [
        item for item in activity.crossings if item.sequence <= through_sequence
    ]
    crossing_by_event = {item.event_id: item for item in crossings}
    children: dict[str, list[str]] = {event_id: [] for event_id in event_by_id}
    for event_id, event in event_by_id.items():
        for parent_id in cast(list[str], event.get("causal_parent_event_ids", [])):
            children[parent_id].append(event_id)

    def order(event_id: str) -> int:
        return cast(int, event_by_id[event_id]["sequence"])

    def contributing(internal_ids: Sequence[str]) -> list[str]:
        contributors: list[str] = []
        for event_id in internal_ids:
            for member_id in cast(list[str], indexed[event_id]["contributing_member_ids"]):
                if member_id not in contributors:
                    contributors.append(member_id)
        return contributors

    def ancestry(output_event_id: str) -> tuple[list[BoundaryCrossing], list[BoundaryCrossing], list[str], list[str]]:
        inputs: dict[str, BoundaryCrossing] = {}
        prior_outputs: dict[str, BoundaryCrossing] = {}
        triggers: set[str] = set()
        internal: set[str] = set()
        seen: set[str] = set()
        stack = list(cast(list[str], event_by_id[output_event_id].get("causal_parent_event_ids", [])))
        while stack:
            event_id = stack.pop()
            if event_id in seen:
                continue
            seen.add(event_id)
            crossing = crossing_by_event.get(event_id)
            if crossing is not None:
                (inputs if crossing.direction == "incoming" else prior_outputs)[event_id] = crossing
                continue
            if indexed[event_id]["boundary_relevant"] is True:
                internal.add(event_id)
                stack.extend(cast(list[str], event_by_id[event_id].get("causal_parent_event_ids", [])))
            else:
                triggers.add(event_id)
        return (
            sorted(inputs.values(), key=lambda item: item.sequence),
            sorted(prior_outputs.values(), key=lambda item: item.sequence),
            sorted(triggers, key=order),
            sorted(internal, key=order),
        )

    def external_results(output_event_id: str) -> list[str]:
        retained: set[str] = set()
        seen: set[str] = set()
        stack = list(children.get(output_event_id, []))
        while stack:
            event_id = stack.pop()
            if event_id in seen:
                continue
            seen.add(event_id)
            crossing = crossing_by_event.get(event_id)
            if crossing is not None and crossing.direction == "incoming":
                continue
            if indexed[event_id]["boundary_relevant"] is True:
                continue
            if event_by_id[event_id].get("event_kind") in {
                "mechanism_executed", "state_committed", "observation_delivered", "effect_dissipated",
            }:
                retained.add(event_id)
            stack.extend(children.get(event_id, []))
        return sorted(retained, key=order)

    def unmatched_descendants(input_event_id: str) -> list[str]:
        internal: set[str] = set()
        seen: set[str] = set()
        stack = list(children.get(input_event_id, []))
        while stack:
            event_id = stack.pop()
            if event_id in seen:
                continue
            seen.add(event_id)
            if event_id in crossing_by_event:
                continue
            if indexed[event_id]["boundary_relevant"] is True:
                internal.add(event_id)
                stack.extend(children.get(event_id, []))
        return sorted(internal, key=order)

    episodes: list[BoundaryCoordinationEpisode] = []
    used_inputs: set[str] = set()
    for output in (item for item in crossings if item.direction == "outgoing"):
        inputs, prior_outputs, triggers, internal = ancestry(output.event_id)
        used_inputs.update(item.event_id for item in inputs)
        starts = [
            *(item.sequence for item in inputs), *(item.sequence for item in prior_outputs),
            *(order(item) for item in triggers), *(order(item) for item in internal), output.sequence,
        ]
        episodes.append(BoundaryCoordinationEpisode(
            episode_id=f"boundary_episode_{activity.boundary_id}_{output.event_id}",
            boundary_id=activity.boundary_id,
            status="completed",
            input_crossing_ids=[item.crossing_id for item in inputs],
            prior_output_crossing_ids=[item.crossing_id for item in prior_outputs],
            trigger_event_ids=triggers,
            internal_event_ids=internal,
            output_crossing_id=output.crossing_id,
            external_result_event_ids=external_results(output.event_id),
            contributing_member_ids=contributing(internal),
            start_sequence=min(starts), end_sequence=output.sequence,
        ))
    for incoming in (item for item in crossings if item.direction == "incoming" and item.event_id not in used_inputs):
        internal = unmatched_descendants(incoming.event_id)
        episodes.append(BoundaryCoordinationEpisode(
            episode_id=f"boundary_episode_{activity.boundary_id}_{incoming.event_id}",
            boundary_id=activity.boundary_id,
            status="in_progress",
            input_crossing_ids=[incoming.crossing_id], prior_output_crossing_ids=[],
            trigger_event_ids=[], internal_event_ids=internal,
            output_crossing_id=None, external_result_event_ids=[],
            contributing_member_ids=contributing(internal),
            start_sequence=incoming.sequence, end_sequence=None,
        ))
    episodes.sort(key=lambda item: (item.start_sequence, item.episode_id))
    return BoundaryActivityProjection(
        boundary_id=activity.boundary_id,
        crossings=crossings,
        episodes=episodes,
    )


def analyst_progress_projection(
    checkpoint: ActiveRuntimeCheckpoint,
    update: RuntimeProgressUpdate,
    *,
    initial_state: CausalState | None = None,
    analytical_boundaries: Sequence[AnalyticalBoundary] = (),
) -> dict[str, object]:
    """Project one retained runtime prefix without exposing protected cognition.

    The runtime owns the update and checkpoint; this presentation adapter owns
    all event-to-animation interpretation.  No browser code needs scenario
    identifiers or private active-system state to decide what moved.
    """
    state = checkpoint.core_checkpoint.state
    by_id = {event.event_id: event for event in checkpoint.core_checkpoint.events}
    events = []
    cues: list[dict[str, object]] = []
    for event_id in update.event_ids:
        event = by_id.get(event_id)
        if event is None:
            raise ValueError("runtime progress references an unknown causal event")
        events.append(analyst_event(event))
        cues.extend(_analyst_animation_cues(event, state))
    world = analyst_world({str(state.revision): state})
    projection: dict[str, object] = {
        "state_revision": state.revision,
        "nodes": analyst_nodes(state),
        "edges": analyst_edges(state),
        "world": world,
        "events": events,
        "animation_cues": cues,
    }
    if analytical_boundaries:
        if initial_state is None:
            raise ValueError("boundary progress requires the initial causal state")
        temporal_states = _temporal_states(
            initial_state,
            checkpoint.core_checkpoint.events,
        )
        progress_boundaries = analyst_boundaries(
            analytical_boundaries,
            temporal_states,
            analyst_edges(state),
            [],
            events=checkpoint.core_checkpoint.events,
        )
        projection["boundaries"] = [
            {
                "id": item["id"],
                "activity": item["activity"],
                "activity_event_index": item["activity_event_index"],
            }
            for item in progress_boundaries
        ]
    return projection


def _analyst_animation_cues(
    event: CausalEvent, state: CausalState
) -> list[dict[str, object]]:
    """Map exact event kinds to honest graph cues, never inferred pathways."""
    def owner(port_id: str | None) -> str | None:
        if port_id is None:
            return None
        port = state.ports.get(port_id)
        return port.owner_ref if port is not None else None

    source_id = event.actor_entity_id or owner(event.source_port_id)
    target_id: str | None = None
    edge_ids: list[str] = []
    cue_kind: AnalystAnimationKind | None = None
    if event.event_kind == "action_attempted":
        cue_kind = "action_attempt"
        target_id = owner(event.source_port_id)
    elif event.event_kind == "effect_routed":
        cue_kind = "information_transfer"
        target_id = owner(event.target_port_id)
        if event.connection_id is not None:
            edge_ids = [event.connection_id]
    elif event.event_kind == "mechanism_executed":
        outcome_code = event.details.get("outcome_code")
        if not isinstance(outcome_code, str):
            raise ValueError("mechanism event lacks its public outcome code")
        cue_kind = (
            "mechanism_denied"
            if "denied" in outcome_code or "rejected" in outcome_code
            else "mechanism_accepted"
        )
        target_id = event.mechanism_id
        if event.target_port_id is not None:
            edge_ids = [f"binding_{event.target_port_id}"]
    elif event.event_kind == "state_committed":
        cue_kind = "state_changed"
        source_id = event.mechanism_id
        target_id = event.mechanism_id
    elif event.event_kind == "observation_delivered":
        cue_kind = "observation_delivered"
        source_id = event.mechanism_id
        target_id = owner(event.target_port_id)
    elif event.event_kind == "effect_dissipated":
        cue_kind = "effect_dissipated"
    if cue_kind is None:
        return []
    return [
        AnalystAnimationCue(
            cue_id=f"cue_{event.event_id}_{cue_kind}",
            event_id=event.event_id,
            kind=cue_kind,
            label=event.summary,
            source_id=source_id,
            target_id=target_id,
            edge_ids=edge_ids,
            causal_parent_event_ids=list(event.causal_parent_event_ids),
        ).model_dump(mode="json")
    ]
from cybernetic_influence.causal_core.models import (
    AnalyticalBoundary,
    CausalEvent,
    CausalState,
    RepresentationToken,
)
from cybernetic_influence.causal_core.replay import apply_state_patch
from cybernetic_influence.scenarios.service_desk import (
    ServiceDeskArmId,
    ServiceDeskCognitionProfile,
    ServiceDeskFixture,
)
from cybernetic_influence.scenarios.service_desk_fidelity import (
    ServiceDeskTrialReadout,
)


def build_service_desk_analyst_document(
    *,
    fixture: ServiceDeskFixture,
    result: ActiveRuntimeResult,
    readout: ServiceDeskTrialReadout | Mapping[str, object],
    profile: ServiceDeskCognitionProfile,
    arm_id: ServiceDeskArmId,
    execution: str,
    created_at: str,
) -> dict[str, object]:
    """Project one protected result into a retained analyst document."""
    outcome = (
        readout.model_dump(mode="json")
        if isinstance(readout, ServiceDeskTrialReadout)
        else dict(readout)
    )
    target_outcome = str(outcome["target_outcome"])
    return build_analyst_document(
        initial_state=fixture.scenario.initial_state,
        analytical_boundaries=fixture.scenario.analytical_boundaries,
        result=result,
        scenario="service_desk",
        profile=profile,
        arm_id=arm_id,
        execution=execution,
        created_at=created_at,
        outcome=outcome,
        headline=target_outcome.replace("_", " ").title(),
        summary=service_desk_summary(arm_id, outcome),
    )


def event_driven_service_desk_outcome(
    result: ActiveRuntimeResult,
) -> dict[str, object]:
    """Derive the compact outcome for an event-triggered Service Desk run."""
    event_by_id = {
        event.event_id: event for event in result.core_result.events
    }
    remediation_moment: int | None = None
    closure_moment: int | None = None
    for moment_number, (_, record) in enumerate(
        _causal_records(result), start=1
    ):
        for event_id in record.core_event_ids:
            event = event_by_id[event_id]
            if event.patch is None:
                continue
            for change in event.patch.fact_changes:
                if (
                    change.fact_id == "incident_17.remediated"
                    and change.after is True
                    and remediation_moment is None
                ):
                    remediation_moment = moment_number
                if (
                    change.fact_id == "incident_17.status"
                    and change.after == "closed_confirmed"
                    and closure_moment is None
                ):
                    closure_moment = moment_number
    final = result.core_result.final_state
    final_status = str(final.fact("incident_17.status").value)
    target_outcome = (
        "resolved_confirmed"
        if final_status == "closed_confirmed"
        else "resolved_unconfirmed"
        if final.fact("incident_17.remediated").value is True
        else "open"
    )
    return {
        "execution_status": "completed",
        "target_outcome": target_outcome,
        "remediation_moment": remediation_moment,
        "confirmed_closure_moment": closure_moment,
        # Compatibility aliases for retained consumers written before moments
        # became the primary temporal unit.
        "remediation_activation": remediation_moment,
        "confirmed_closure_activation": closure_moment,
        "target_censored": closure_moment is None,
        "causal_moment_count": len(_causal_records(result)),
        "participant_activation_count": sum(
            len(attempt.participants) for attempt in result.attempts
        ),
        "autonomous_activation_count": sum(
            1
            for attempt in result.attempts
            for participant in attempt.participants
            if any(
                cause.kind == "internal_wake"
                for cause in participant.input.activation_causes
            )
        ),
        "exact_process_activation_count": sum(
            1
            for attempt in result.attempts
            for participant in attempt.participants
            if result.core_result.final_state.entities[
                participant.input.entity_id
            ].entity_kind
            == "state_machine"
        ),
        "final_simulation_time": result.core_result.final_state.logical_time,
        "time_unit": result.core_result.time_unit,
        "model_calls": result.model_calls,
        "accepted_action_count": len(result.core_result.accepted_action_ids),
        "closure_attempt_count": final.fact(
            "incident_17.closure_attempts"
        ).value,
        "denied_closure_attempt_count": final.fact(
            "incident_17.denied_closure_attempts"
        ).value,
        "known_cost": result.total_observed_cost,
        "cost_fully_observable": result.cost_fully_observable,
        "final_status": final_status,
    }


def build_analyst_document(
    *,
    initial_state: CausalState,
    analytical_boundaries: Sequence[AnalyticalBoundary],
    result: ActiveRuntimeResult,
    scenario: str,
    profile: str,
    arm_id: str,
    execution: str,
    created_at: str,
    outcome: Mapping[str, object],
    headline: str,
    summary: str,
    include_boundary_activity: bool = False,
) -> dict[str, object]:
    """Build the common retained analyst surface proven across scenarios."""
    final_state = result.core_result.final_state
    temporal_states = _temporal_states(initial_state, result.core_result.events)
    snapshots = {
        revision: analyst_nodes(state)
        for revision, state in temporal_states.items()
    }
    nodes = snapshots[str(final_state.revision)]
    edges = analyst_edges(final_state)
    timeline = analyst_timeline(result, temporal_states)
    trajectory = analyst_trajectory(timeline)
    moments = analyst_moments(result, timeline)
    boundaries = analyst_boundaries(
        analytical_boundaries,
        temporal_states,
        edges,
        timeline,
        events=(result.core_result.events if include_boundary_activity else None),
    )
    traces = analyst_traces(result)
    world = analyst_world(temporal_states)
    return {
        "run_id": result.run_id,
        "created_at": created_at,
        "status": result.status,
        "scenario": scenario,
        "profile": profile,
        "arm": arm_id,
        "execution": execution,
        "time_unit": result.core_result.time_unit,
        "model_calls": result.model_calls,
        "cost": result.total_observed_cost,
        "cost_fully_observable": result.cost_fully_observable,
        "story": {
            "headline": headline,
            "summary": summary,
            "steps": [event for event in timeline if event["kind"] == "action_attempted"],
        },
        "outcome": dict(outcome),
        "world": world,
        "nodes": nodes,
        "snapshots": snapshots,
        "edges": edges,
        "boundaries": boundaries,
        "timeline": timeline,
        "trajectory": trajectory,
        "moments": moments,
        "events": [analyst_event(event) for event in result.core_result.events],
        "traces": traces,
    }


def analyst_trajectory(
    timeline: Sequence[Mapping[str, object]],
) -> dict[str, list[dict[str, object]]]:
    """Project the realized event DAG without conflating it with declared routes."""
    nodes: list[dict[str, object]] = []
    edges: list[dict[str, object]] = []
    for event in timeline:
        event_id = event["event_id"]
        assert isinstance(event_id, str)
        nodes.append(
            {
                "id": event_id,
                "kind": event["kind"],
                "label": str(event["summary"]),
                "logical_time": event["logical_time"],
                "causal_timestamp": event.get("causal_timestamp"),
                "timing": event.get("timing"),
            }
        )
        parent_ids = event.get("causal_parent_event_ids", [])
        assert isinstance(parent_ids, list)
        for parent_id in parent_ids:
            if isinstance(parent_id, str):
                edges.append(
                    {
                        "id": f"{parent_id}__{event_id}",
                        "source": parent_id,
                        "target": event_id,
                    }
                )
    return {"nodes": nodes, "edges": edges}


def analyst_moments(
    result: ActiveRuntimeResult,
    timeline: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    """Project atomic activation sets as the primary human time units."""
    timeline_ids = {
        str(event["event_id"]): index for index, event in enumerate(timeline)
    }
    last_event_index = 0
    moments: list[dict[str, object]] = []
    entity_kinds = {
        entity_id: entity.entity_kind
        for entity_id, entity in result.core_result.final_state.entities.items()
    }
    for moment_number, (record_kind, record) in enumerate(
        _causal_records(result), start=1
    ):
        event_indices = [
            timeline_ids[event_id]
            for event_id in record.core_event_ids
            if event_id in timeline_ids
        ]
        if event_indices:
            last_event_index = event_indices[-1]
        if record_kind == "exact":
            exact_record = record
            assert isinstance(exact_record, ExactWorkRecord)
            moments.append(
                {
                    "moment": moment_number,
                    "activation": exact_record.work_id,
                    "causal_time": moment_number,
                    "causal_timestamp": f"c{moment_number}",
                    "logical_time": exact_record.logical_time,
                    "participants": ["exact_mechanisms"],
                    "participant_kinds": {"exact_mechanisms": "exact"},
                    "activation_causes": {
                        "exact_mechanisms": [
                            {
                                "kind": "scheduled_exact_work",
                                "scheduled_for": exact_record.logical_time,
                                "description": (
                                    "Previously retained exact work reached "
                                    "its declared due time."
                                ),
                            }
                        ]
                    },
                    "event_ids": [
                        str(timeline[index]["event_id"])
                        for index in event_indices
                    ],
                    "representative_event_index": last_event_index,
                    "silent": False,
                }
            )
            continue
        attempt = record
        assert isinstance(attempt, ActivationAttemptRecord)
        moments.append(
            {
                "moment": moment_number,
                "activation": attempt.activation_id,
                "causal_time": moment_number,
                "causal_timestamp": f"c{moment_number}",
                "logical_time": attempt.logical_time,
                "participants": [
                    participant.requested_active_system_id
                    for participant in attempt.participants
                ],
                "participant_kinds": {
                    participant.requested_active_system_id: entity_kinds[
                        participant.input.entity_id
                    ]
                    for participant in attempt.participants
                },
                "activation_causes": {
                    participant.requested_active_system_id: [
                        cause.model_dump(mode="json")
                        for cause in participant.input.activation_causes
                    ]
                    for participant in attempt.participants
                },
                "event_ids": [
                    str(timeline[index]["event_id"])
                    for index in event_indices
                ],
                "representative_event_index": last_event_index,
                "silent": not event_indices,
            }
        )
    return moments


def analyst_snapshots(
    initial_state: CausalState,
    events: Sequence[CausalEvent],
) -> dict[str, list[dict[str, object]]]:
    """Reconstruct and project one canonical state for every observed revision."""
    return {
        revision: analyst_nodes(state)
        for revision, state in _temporal_states(initial_state, events).items()
    }


def analyst_world(
    temporal_states: Mapping[str, CausalState],
) -> dict[str, object] | None:
    """Project exact topological places and event-revision placements."""
    if not temporal_states:
        return None
    final_state = list(temporal_states.values())[-1]
    if not final_state.places:
        return None
    places = [
        {
            "id": place.place_id,
            "kind": place.place_kind,
            "label": _label(place.place_id),
            "description": place.description,
            "parent_place_id": place.parent_place_id,
        }
        for place in sorted(
            final_state.places.values(),
            key=lambda item: item.place_id,
        )
    ]
    links = [
        {
            "id": link.spatial_link_id,
            "kind": link.link_kind,
            "label": _label(link.spatial_link_id),
            "description": link.description,
            "endpoint_a_place_id": link.endpoint_a_place_id,
            "endpoint_b_place_id": link.endpoint_b_place_id,
            "substrate_entity_ids": list(link.substrate_entity_ids),
            "does_not_imply_traversability": True,
        }
        for link in sorted(
            final_state.spatial_links.values(),
            key=lambda item: item.spatial_link_id,
        )
    ]
    snapshots = {
        revision: {
            "placements": [
                {
                    "entity_id": placement.entity_id,
                    "place_id": placement.place_id,
                }
                for placement in sorted(
                    state.placements.values(),
                    key=lambda item: item.entity_id,
                )
            ],
            "unplaced_entity_ids": sorted(
                set(state.entities) - set(state.placements)
            ),
        }
        for revision, state in temporal_states.items()
    }
    return {
        "places": places,
        "links": links,
        "snapshots": snapshots,
    }


def _temporal_states(
    initial_state: CausalState,
    events: Sequence[CausalEvent],
) -> dict[str, CausalState]:
    """Reconstruct one canonical state for every observed revision."""
    state = initial_state.model_copy(deep=True)
    states: dict[str, CausalState] = {str(state.revision): state.model_copy(deep=True)}
    known_event_ids: set[str] = set()
    for event in events:
        unknown_parents = set(event.causal_parent_event_ids) - known_event_ids
        if unknown_parents:
            raise BoundaryProjectionError(
                f"event {event.event_id!r} has unknown or future parents"
            )
        if event.event_kind == "state_committed":
            if event.patch is None:
                raise BoundaryProjectionError("commit event is missing its patch")
            state = apply_state_patch(
                state,
                event.patch,
                known_event_ids=known_event_ids,
            )
        if event.state_revision != state.revision:
            raise BoundaryProjectionError(
                f"event {event.event_id!r} disagrees with replay state revision"
            )
        known_event_ids.add(event.event_id)
        revision = str(state.revision)
        if revision not in states:
            states[revision] = state.model_copy(deep=True)
    return states


def project_boundary_activity(
    boundary: AnalyticalBoundary,
    temporal_states: Mapping[str, CausalState],
    events: Sequence[CausalEvent],
    *,
    causal_times: Mapping[str, int] | None = None,
    through_sequence: int | None = None,
) -> BoundaryActivityProjection:
    """Derive exact crossings and episodes from one retained event prefix."""
    retained = [
        event
        for event in events
        if through_sequence is None or event.sequence <= through_sequence
    ]
    event_by_id: dict[str, CausalEvent] = {}
    seen_sequences: set[int] = set()
    run_ids = {event.run_id for event in retained}
    if len(run_ids) > 1:
        raise BoundaryProjectionError("retained boundary evidence crosses runs")
    for event in retained:
        if event.event_id in event_by_id or event.sequence in seen_sequences:
            raise BoundaryProjectionError("retained boundary evidence has duplicate IDs")
        unknown_parents = set(event.causal_parent_event_ids) - set(event_by_id)
        if unknown_parents:
            raise BoundaryProjectionError(
                f"event {event.event_id!r} has unknown or future parents"
            )
        event_by_id[event.event_id] = event
        seen_sequences.add(event.sequence)
    if retained and [event.sequence for event in retained] != sorted(
        event.sequence for event in retained
    ):
        raise BoundaryProjectionError("retained events are not canonically ordered")

    state_by_event = {
        event.event_id: _boundary_event_state(event, temporal_states)
        for event in retained
    }
    for state in {
        state.revision: state for state in state_by_event.values()
    }.values():
        _validate_boundary_members(boundary, state)
    members_by_revision = {
        revision: _boundary_member_refs(boundary, state)
        for revision, state in {
            state.revision: state for state in state_by_event.values()
        }.items()
    }
    members_by_event = {
        event.event_id: members_by_revision[state_by_event[event.event_id].revision]
        for event in retained
    }
    for event in retained:
        _validate_boundary_event_references(event, state_by_event[event.event_id])
        _reject_direct_cross_boundary_patch(
            event,
            state_by_event[event.event_id],
            members_by_event[event.event_id],
        )

    crossings: list[BoundaryCrossing] = []
    for event in retained:
        if event.event_kind != "effect_routed":
            continue
        state = state_by_event[event.event_id]
        members = members_by_event[event.event_id]
        assert event.source_port_id is not None
        assert event.target_port_id is not None
        source_ref = state.ports[event.source_port_id].owner_ref
        target_ref = state.ports[event.target_port_id].owner_ref
        source_inside = source_ref in members
        target_inside = target_ref in members
        if source_inside == target_inside:
            continue
        if event.route_kind == "connection":
            if event.connection_id is None or event.connection_id not in state.connections:
                raise BoundaryProjectionError("crossing names an unknown connection")
            route_ref = event.connection_id
        elif event.route_kind == "container":
            if event.container_id is None or event.container_id not in state.containers:
                raise BoundaryProjectionError("crossing names an unknown container")
            route_ref = event.container_id
        else:  # pragma: no cover - CausalEvent already guards this
            raise BoundaryProjectionError("crossing lacks one exact route")
        if event.effect_id is None:
            raise BoundaryProjectionError("crossing lacks an exact effect")
        crossings.append(
            BoundaryCrossing(
                crossing_id=(
                    f"boundary_crossing_{boundary.boundary_id}_{event.event_id}"
                ),
                boundary_id=boundary.boundary_id,
                event_id=event.event_id,
                sequence=event.sequence,
                causal_time=(causal_times or {}).get(event.event_id),
                direction="outgoing" if source_inside else "incoming",
                source_ref=source_ref,
                target_ref=target_ref,
                route_kind=event.route_kind,
                route_ref=route_ref,
                effect_id=event.effect_id,
                representation_id=event.representation_id,
            )
        )

    crossing_by_event = {item.event_id: item for item in crossings}
    children: dict[str, list[str]] = {event_id: [] for event_id in event_by_id}
    for event in retained:
        for parent_id in event.causal_parent_event_ids:
            children[parent_id].append(event.event_id)

    episodes: list[BoundaryCoordinationEpisode] = []
    used_inputs: set[str] = set()
    for output in (item for item in crossings if item.direction == "outgoing"):
        inputs, prior_outputs, triggers, internal = _walk_boundary_ancestry(
            boundary,
            output.event_id,
            event_by_id,
            state_by_event,
            members_by_event,
            crossing_by_event,
        )
        used_inputs.update(item.event_id for item in inputs)
        external = _walk_external_results(
            boundary,
            output.event_id,
            event_by_id,
            state_by_event,
            members_by_event,
            crossing_by_event,
            children,
        )
        contributing = _contributing_members(
            boundary,
            internal,
            event_by_id,
            state_by_event,
            members_by_event,
        )
        start_candidates = [
            *(item.sequence for item in inputs),
            *(item.sequence for item in prior_outputs),
            *(event_by_id[item].sequence for item in triggers),
            *(event_by_id[item].sequence for item in internal),
            output.sequence,
        ]
        episodes.append(
            BoundaryCoordinationEpisode(
                episode_id=(
                    f"boundary_episode_{boundary.boundary_id}_{output.event_id}"
                ),
                boundary_id=boundary.boundary_id,
                status="completed",
                input_crossing_ids=[item.crossing_id for item in inputs],
                prior_output_crossing_ids=[
                    item.crossing_id for item in prior_outputs
                ],
                trigger_event_ids=triggers,
                internal_event_ids=internal,
                output_crossing_id=output.crossing_id,
                external_result_event_ids=external,
                contributing_member_ids=contributing,
                start_sequence=min(start_candidates),
                end_sequence=output.sequence,
            )
        )

    for incoming in (
        item
        for item in crossings
        if item.direction == "incoming" and item.event_id not in used_inputs
    ):
        internal = _walk_unmatched_input_descendants(
            boundary,
            incoming.event_id,
            event_by_id,
            state_by_event,
            members_by_event,
            crossing_by_event,
            children,
        )
        contributing = _contributing_members(
            boundary,
            internal,
            event_by_id,
            state_by_event,
            members_by_event,
        )
        episodes.append(
            BoundaryCoordinationEpisode(
                episode_id=(
                    f"boundary_episode_{boundary.boundary_id}_{incoming.event_id}"
                ),
                boundary_id=boundary.boundary_id,
                status="in_progress",
                input_crossing_ids=[incoming.crossing_id],
                prior_output_crossing_ids=[],
                trigger_event_ids=[],
                internal_event_ids=internal,
                output_crossing_id=None,
                external_result_event_ids=[],
                contributing_member_ids=contributing,
                start_sequence=incoming.sequence,
                end_sequence=None,
            )
        )
    episodes.sort(key=lambda item: (item.start_sequence, item.episode_id))
    return BoundaryActivityProjection(
        boundary_id=boundary.boundary_id,
        crossings=crossings,
        episodes=episodes,
    )


def boundary_activity_event_index(
    boundary: AnalyticalBoundary,
    temporal_states: Mapping[str, CausalState],
    events: Sequence[CausalEvent],
) -> list[dict[str, object]]:
    """Retain the minimal server-owned facts needed for exact prefix views."""
    indexed: list[dict[str, object]] = []
    for event in events:
        state = _boundary_event_state(event, temporal_states)
        members = _boundary_member_refs(boundary, state)
        refs = [event.actor_entity_id, event.mechanism_id]
        refs.extend(
            state.ports[port_id].owner_ref
            for port_id in (event.source_port_id, event.target_port_id)
            if port_id is not None
        )
        contributors: list[str] = []
        for ref in refs:
            if ref is not None and ref in members and ref not in contributors:
                contributors.append(ref)
        relevant_refs = set(item for item in refs if item is not None)
        relevant_refs.update(_patch_owner_refs(event, state))
        indexed.append(
            {
                "event_id": event.event_id,
                "sequence": event.sequence,
                "boundary_relevant": bool(members.intersection(relevant_refs)),
                "contributing_member_ids": contributors,
            }
        )
    return indexed


def _boundary_event_state(
    event: CausalEvent,
    temporal_states: Mapping[str, CausalState],
) -> CausalState:
    state = temporal_states.get(str(event.state_revision))
    if state is None:
        raise BoundaryProjectionError(
            f"event {event.event_id!r} references an unknown state revision"
        )
    return state


def _validate_boundary_members(
    boundary: AnalyticalBoundary,
    state: CausalState,
) -> None:
    known = (
        set(state.entities)
        | set(state.mechanisms)
        | set(state.ports)
        | set(state.carriers)
        | set(state.representations)
        | set(state.connections)
        | set(state.containers)
        | set(state.places)
        | set(state.spatial_links)
    )
    unknown = set(boundary.member_refs) - known
    if unknown:
        raise BoundaryProjectionError(
            f"boundary {boundary.boundary_id!r} has unknown members"
        )


def _validate_boundary_event_references(
    event: CausalEvent,
    state: CausalState,
) -> None:
    if event.actor_entity_id is not None and event.actor_entity_id not in state.entities:
        raise BoundaryProjectionError("event references an unknown actor")
    if event.mechanism_id is not None and event.mechanism_id not in state.mechanisms:
        raise BoundaryProjectionError("event references an unknown mechanism")
    for port_id in (event.source_port_id, event.target_port_id):
        if port_id is not None and port_id not in state.ports:
            raise BoundaryProjectionError("event references an unknown port")
    if (
        event.representation_id is not None
        and event.representation_id not in state.representations
    ):
        raise BoundaryProjectionError("event references an unknown representation")
    if event.event_kind == "effect_routed":
        if event.route_kind == "connection" and (
            event.connection_id is None
            or event.connection_id not in state.connections
        ):
            raise BoundaryProjectionError("event references an unknown connection")
        if event.route_kind == "container" and (
            event.container_id is None or event.container_id not in state.containers
        ):
            raise BoundaryProjectionError("event references an unknown container")


def _reject_direct_cross_boundary_patch(
    event: CausalEvent,
    state: CausalState,
    members: set[str],
) -> None:
    if event.patch is None or event.mechanism_id is None:
        return
    if event.mechanism_id not in members:
        return
    outside: list[str] = []
    for fact_change in event.patch.fact_changes:
        owner = fact_change.fact_id.split(".", 1)[0]
        if owner not in state.entities:
            raise BoundaryProjectionError("fact change has an unknown owner")
        if owner not in members:
            outside.append(owner)
    for placement_change in event.patch.placement_changes:
        if placement_change.entity_id not in state.entities:
            raise BoundaryProjectionError("placement change has an unknown owner")
        if placement_change.entity_id not in members:
            outside.append(placement_change.entity_id)
    for carrier_change in event.patch.carrier_changes:
        carrier = state.carriers.get(carrier_change.carrier_id)
        if carrier is None:
            raise BoundaryProjectionError("carrier change has an unknown owner")
        if (
            carrier_change.carrier_id not in members
            and carrier.owner_ref not in members
        ):
            outside.append(carrier_change.carrier_id)
    for representation in event.patch.representations_added:
        carrier = state.carriers.get(representation.carrier_id)
        if carrier is None:
            raise BoundaryProjectionError("representation has an unknown carrier")
        if (
            representation.carrier_id not in members
            and carrier.owner_ref not in members
        ):
            outside.append(representation.carrier_id)
    for observation in event.patch.observations_added:
        if observation.target_entity_id not in state.entities:
            raise BoundaryProjectionError("observation has an unknown owner")
        if observation.target_entity_id not in members:
            outside.append(observation.target_entity_id)
    if outside:
        raise BoundaryProjectionError(
            f"member mechanism {event.mechanism_id!r} directly mutates "
            f"nonmember-owned state {sorted(set(outside))!r} at "
            f"{event.event_id!r}"
        )


def _event_boundary_relevant(
    event: CausalEvent,
    state: CausalState,
    members: set[str],
) -> bool:
    refs = {event.actor_entity_id, event.mechanism_id}
    for port_id in (event.source_port_id, event.target_port_id):
        if port_id is not None:
            refs.add(state.ports[port_id].owner_ref)
    refs.update(_patch_owner_refs(event, state))
    return bool(members.intersection(item for item in refs if item is not None))


def _patch_owner_refs(event: CausalEvent, state: CausalState) -> set[str]:
    """Resolve typed patch ownership without consulting prose or focus IDs."""
    if event.patch is None:
        return set()
    owners: set[str] = set()
    for fact_change in event.patch.fact_changes:
        owner = fact_change.fact_id.split(".", 1)[0]
        if owner not in state.entities:
            raise BoundaryProjectionError("fact change has an unknown owner")
        owners.add(owner)
    for placement_change in event.patch.placement_changes:
        if placement_change.entity_id not in state.entities:
            raise BoundaryProjectionError("placement change has an unknown owner")
        owners.add(placement_change.entity_id)
    for carrier_change in event.patch.carrier_changes:
        carrier = state.carriers.get(carrier_change.carrier_id)
        if carrier is None:
            raise BoundaryProjectionError("carrier change has an unknown owner")
        owners.update({carrier_change.carrier_id, carrier.owner_ref})
    for representation in event.patch.representations_added:
        carrier = state.carriers.get(representation.carrier_id)
        if carrier is None:
            raise BoundaryProjectionError("representation has an unknown carrier")
        owners.update({representation.carrier_id, carrier.owner_ref})
    for observation in event.patch.observations_added:
        if observation.target_entity_id not in state.entities:
            raise BoundaryProjectionError("observation has an unknown owner")
        owners.add(observation.target_entity_id)
    return owners


def _walk_boundary_ancestry(
    boundary: AnalyticalBoundary,
    output_event_id: str,
    event_by_id: Mapping[str, CausalEvent],
    state_by_event: Mapping[str, CausalState],
    members_by_event: Mapping[str, set[str]],
    crossing_by_event: Mapping[str, BoundaryCrossing],
) -> tuple[
    list[BoundaryCrossing],
    list[BoundaryCrossing],
    list[str],
    list[str],
]:
    inputs: dict[str, BoundaryCrossing] = {}
    prior_outputs: dict[str, BoundaryCrossing] = {}
    triggers: set[str] = set()
    internal: set[str] = set()
    seen: set[str] = set()
    stack = list(event_by_id[output_event_id].causal_parent_event_ids)
    while stack:
        event_id = stack.pop()
        if event_id in seen:
            continue
        seen.add(event_id)
        event = event_by_id[event_id]
        crossing = crossing_by_event.get(event_id)
        if crossing is not None:
            target = inputs if crossing.direction == "incoming" else prior_outputs
            target[event_id] = crossing
            continue
        if _event_boundary_relevant(
            event, state_by_event[event_id], members_by_event[event_id]
        ):
            internal.add(event_id)
            stack.extend(event.causal_parent_event_ids)
        else:
            triggers.add(event_id)
    order = lambda event_id: event_by_id[event_id].sequence
    return (
        sorted(inputs.values(), key=lambda item: item.sequence),
        sorted(prior_outputs.values(), key=lambda item: item.sequence),
        sorted(triggers, key=order),
        sorted(internal, key=order),
    )


def _walk_external_results(
    boundary: AnalyticalBoundary,
    output_event_id: str,
    event_by_id: Mapping[str, CausalEvent],
    state_by_event: Mapping[str, CausalState],
    members_by_event: Mapping[str, set[str]],
    crossing_by_event: Mapping[str, BoundaryCrossing],
    children: Mapping[str, Sequence[str]],
) -> list[str]:
    retained: set[str] = set()
    seen: set[str] = set()
    stack = list(children.get(output_event_id, []))
    while stack:
        event_id = stack.pop()
        if event_id in seen:
            continue
        seen.add(event_id)
        crossing = crossing_by_event.get(event_id)
        if crossing is not None and crossing.direction == "incoming":
            continue
        event = event_by_id[event_id]
        if _event_boundary_relevant(
            event, state_by_event[event_id], members_by_event[event_id]
        ):
            continue
        if event.event_kind in {
            "mechanism_executed",
            "state_committed",
            "observation_delivered",
            "effect_dissipated",
        }:
            retained.add(event_id)
        stack.extend(children.get(event_id, []))
    return sorted(retained, key=lambda item: event_by_id[item].sequence)


def _walk_unmatched_input_descendants(
    boundary: AnalyticalBoundary,
    input_event_id: str,
    event_by_id: Mapping[str, CausalEvent],
    state_by_event: Mapping[str, CausalState],
    members_by_event: Mapping[str, set[str]],
    crossing_by_event: Mapping[str, BoundaryCrossing],
    children: Mapping[str, Sequence[str]],
) -> list[str]:
    internal: set[str] = set()
    seen: set[str] = set()
    stack = list(children.get(input_event_id, []))
    while stack:
        event_id = stack.pop()
        if event_id in seen:
            continue
        seen.add(event_id)
        if event_id in crossing_by_event:
            continue
        event = event_by_id[event_id]
        if _event_boundary_relevant(
            event, state_by_event[event_id], members_by_event[event_id]
        ):
            internal.add(event_id)
            stack.extend(children.get(event_id, []))
    return sorted(internal, key=lambda item: event_by_id[item].sequence)


def _contributing_members(
    boundary: AnalyticalBoundary,
    internal_event_ids: Sequence[str],
    event_by_id: Mapping[str, CausalEvent],
    state_by_event: Mapping[str, CausalState],
    members_by_event: Mapping[str, set[str]],
) -> list[str]:
    contributors: list[str] = []
    for event_id in internal_event_ids:
        event = event_by_id[event_id]
        state = state_by_event[event_id]
        members = members_by_event[event_id]
        refs = [event.actor_entity_id, event.mechanism_id]
        refs.extend(
            state.ports[port_id].owner_ref
            for port_id in (event.source_port_id, event.target_port_id)
            if port_id is not None
        )
        for ref in refs:
            if ref is not None and ref in members and ref not in contributors:
                contributors.append(ref)
    return contributors


def analyst_boundaries(
    boundaries: Sequence[AnalyticalBoundary],
    temporal_states: Mapping[str, CausalState],
    edges: Sequence[Mapping[str, object]],
    timeline: list[dict[str, object]],
    *,
    events: Sequence[CausalEvent] | None = None,
) -> list[dict[str, object]]:
    """Derive reversible aggregate evidence without creating runtime state."""
    projected: list[dict[str, object]] = []
    members_by_boundary_revision: dict[tuple[str, str], set[str]] = {}

    for boundary in boundaries:
        causal_times = {
            str(item["event_id"]): cast(int, item["causal_time"])
            for item in timeline
            if isinstance(item.get("event_id"), str)
            and isinstance(item.get("causal_time"), int)
            and not isinstance(item.get("causal_time"), bool)
        }
        activity = (
            project_boundary_activity(
                boundary,
                temporal_states,
                events,
                causal_times=causal_times,
            )
            if events is not None
            else None
        )
        snapshots: dict[str, dict[str, object]] = {}
        for revision, state in temporal_states.items():
            member_refs = _boundary_member_refs(boundary, state)
            members_by_boundary_revision[
                (boundary.boundary_id, revision)
            ] = member_refs
            visible_nodes = [
                node
                for node in analyst_nodes(state)
                if str(node["id"]) in member_refs
            ]
            visible_ids = {str(node["id"]) for node in visible_nodes}
            member_kind_counts: dict[str, int] = {}
            hidden_fact_count = 0
            hidden_information_count = 0
            for node in visible_nodes:
                kind = str(node["kind"])
                member_kind_counts[kind] = member_kind_counts.get(kind, 0) + 1
                if kind == "information":
                    hidden_information_count += 1
                elif kind != "mechanism":
                    state_values = node.get("state")
                    if isinstance(state_values, dict):
                        hidden_fact_count += len(state_values)

            internal_routes: list[str] = []
            inbound_routes: list[str] = []
            outbound_routes: list[str] = []
            for edge in edges:
                if edge.get("kind") != "connection":
                    continue
                edge_id = str(edge["id"])
                source_inside = str(edge["source"]) in member_refs
                target_inside = str(edge["target"]) in member_refs
                if source_inside and target_inside:
                    internal_routes.append(edge_id)
                elif source_inside:
                    outbound_routes.append(edge_id)
                elif target_inside:
                    inbound_routes.append(edge_id)

            snapshots[revision] = {
                "state_revision": int(revision),
                "member_ids": sorted(visible_ids),
                "member_kind_counts": dict(sorted(member_kind_counts.items())),
                "authored_member_count": len(boundary.member_refs),
                "derived_member_count": len(member_refs),
                "selectable_member_count": len(visible_ids),
                "nonselectable_member_count": len(member_refs - visible_ids),
                "hidden_fact_count": hidden_fact_count,
                "hidden_information_count": hidden_information_count,
                "internal_route_ids": sorted(internal_routes),
                "inbound_route_ids": sorted(inbound_routes),
                "outbound_route_ids": sorted(outbound_routes),
            }

        projected.append(
            {
                "id": boundary.boundary_id,
                "kind": "analytical_boundary",
                "label": boundary.label,
                "description": boundary.description,
                "executor": boundary.executor,
                "authored_member_ids": list(boundary.member_refs),
                "snapshots": snapshots,
                "trace_event_ids": [],
                **(
                    {
                        "activity": activity.model_dump(mode="json"),
                        "activity_event_index": boundary_activity_event_index(
                            boundary,
                            temporal_states,
                            cast(Sequence[CausalEvent], events),
                        ),
                    }
                    if activity is not None
                    else {}
                ),
            }
        )

    trace_ids: dict[str, list[str]] = {
        str(projected_boundary["id"]): []
        for projected_boundary in projected
    }
    for event in timeline:
        revision = str(event["state_revision"])
        raw_focus_ids = event.get("focus_ids")
        focus_ids = (
            {str(item) for item in raw_focus_ids}
            if isinstance(raw_focus_ids, list)
            else set()
        )
        boundary_ids: list[str] = []
        for projected_boundary in projected:
            boundary_id = str(projected_boundary["id"])
            members = members_by_boundary_revision[(boundary_id, revision)]
            if focus_ids.intersection(members):
                boundary_ids.append(boundary_id)
                trace_ids[boundary_id].append(str(event["event_id"]))
        event["boundary_ids"] = boundary_ids
    for projected_boundary in projected:
        projected_boundary["trace_event_ids"] = trace_ids[
            str(projected_boundary["id"])
        ]
    return projected


def _boundary_member_refs(
    boundary: AnalyticalBoundary,
    state: CausalState,
) -> set[str]:
    """Close authored membership over representations on member carriers."""
    member_refs = set(boundary.member_refs)
    for representation in state.representations.values():
        carrier = state.carriers[representation.carrier_id]
        if (
            representation.carrier_id in member_refs
            or carrier.owner_ref in member_refs
        ):
            member_refs.add(representation.representation_id)
    return member_refs


def analyst_edges(state: CausalState) -> list[dict[str, object]]:
    """Project concrete connections, bindings, and representation lineage."""
    edges: list[dict[str, object]] = []
    routes_by_target_port: dict[str, list[str]] = {}
    for connection in state.connections.values():
        routes_by_target_port.setdefault(connection.target_port_id, []).append(
            connection.connection_id
        )
        edges.append(
            {
                "id": connection.connection_id,
                "kind": "connection",
                "source": state.ports[connection.source_port_id].owner_ref,
                "target": state.ports[connection.target_port_id].owner_ref,
                "enabled": connection.enabled,
                "exact_route_ids": [connection.connection_id],
                "description": connection.description,
            }
        )
    for mechanism in state.mechanisms.values():
        for port_id in mechanism.input_port_ids:
            owner_ref = state.ports[port_id].owner_ref
            if owner_ref == mechanism.mechanism_id:
                continue
            edges.append(
                {
                    "id": f"binding_{port_id}",
                    "kind": "mechanism_binding",
                    "source": owner_ref,
                    "target": mechanism.mechanism_id,
                    "enabled": True,
                    "exact_route_ids": sorted(routes_by_target_port.get(port_id, [])),
                    "description": (
                        f"Declared input {port_id} binds {owner_ref} to exact "
                        f"mechanism {mechanism.mechanism_id}."
                    ),
                }
            )
    for representation in state.representations.values():
        carrier_owner = state.carriers[representation.carrier_id].owner_ref
        if carrier_owner != representation.representation_id:
            edges.append(
                {
                    "id": (
                        f"location_{carrier_owner}_to_"
                        f"{representation.representation_id}"
                    ),
                    "kind": "information_location",
                    "source": carrier_owner,
                    "target": representation.representation_id,
                    "enabled": True,
                    "exact_route_ids": [],
                    "description": (
                        f"{representation.representation_id} is retained on a "
                        f"carrier owned by {carrier_owner}."
                    ),
                }
            )
        sources = (
            representation.parent_representation_ids
            if representation.parent_representation_ids
            else [representation.actual_source_ref]
        )
        for source_ref in sources:
            edges.append(
                {
                    "id": (
                        f"lineage_{source_ref}_to_"
                        f"{representation.representation_id}"
                    ),
                    "kind": "information_lineage",
                    "source": source_ref,
                    "target": representation.representation_id,
                    "enabled": True,
                    "exact_route_ids": [],
                    "description": (
                        f"Retained representation lineage from {source_ref} to "
                        f"{representation.representation_id}."
                    ),
                }
            )
    return edges


def analyst_nodes(state: CausalState) -> list[dict[str, object]]:
    """Project addressable nodes without mechanism-only values."""
    nodes: list[dict[str, object]] = []
    for entity in state.entities.values():
        attributes: dict[str, object] = {}
        for name, fact in entity.attributes.items():
            attributes[name] = (
                {"visibility": "mechanism", "redacted": True}
                if fact.visibility == "mechanism"
                else fact.model_dump(mode="json")
            )
        nodes.append(
            {
                "id": entity.entity_id,
                "kind": entity.entity_kind,
                "label": _label(entity.entity_id),
                "description": entity.description,
                "state": attributes,
            }
        )
    for representation in state.representations.values():
        nodes.append(_representation_node(representation))
    for mechanism in state.mechanisms.values():
        nodes.append(
            {
                "id": mechanism.mechanism_id,
                "kind": "mechanism",
                "label": _label(mechanism.mechanism_id),
                "description": mechanism.description,
                "state": mechanism.model_dump(mode="json"),
            }
        )
    return nodes


def analyst_event(event: CausalEvent) -> dict[str, object]:
    """Redact protected patch values while preserving exact event identity."""
    projected = event.model_dump(mode="json")
    patch = projected.get("patch")
    if not isinstance(patch, dict):
        return projected
    for change in patch.get("fact_changes", []):
        if isinstance(change, dict) and change.get("visibility") == "mechanism":
            change["before"] = "[redacted]"
            change["after"] = "[redacted]"
            change["redacted"] = True
    additions = patch.get("representations_added", [])
    if isinstance(additions, list):
        patch["representations_added"] = [
            _redact_representation_mapping(item)
            if isinstance(item, dict) and item.get("visibility") == "mechanism"
            else item
            for item in additions
        ]
    return projected


def analyst_timeline(
    result: ActiveRuntimeResult,
    temporal_states: Mapping[str, CausalState],
) -> list[dict[str, object]]:
    """Link each event to exact temporal, activation, entity, and route identities."""
    state = result.core_result.final_state
    node_ids = {str(node["id"]) for node in analyst_nodes(state)}
    event_activation: dict[str, tuple[str, str | None, int, int]] = {}
    events_by_id = {
        event.event_id: event for event in result.core_result.events
    }
    for causal_moment, (record_kind, record) in enumerate(
        _causal_records(result), start=1
    ):
        if record_kind == "exact":
            exact_record = record
            assert isinstance(exact_record, ExactWorkRecord)
            for causal_substep, event_id in enumerate(
                exact_record.core_event_ids, start=1
            ):
                event_activation[event_id] = (
                    exact_record.work_id,
                    None,
                    causal_moment,
                    causal_substep,
                )
            continue
        attempt = record
        assert isinstance(attempt, ActivationAttemptRecord)
        action_owner = {
            action_id: participant.requested_active_system_id
            for participant in attempt.participants
            for action_id in participant.assigned_action_ids
        }
        event_owner: dict[str, str] = {}
        for causal_substep, event_id in enumerate(attempt.core_event_ids, start=1):
            event = events_by_id[event_id]
            owner = (
                action_owner.get(event.action_id)
                if event.action_id is not None
                else None
            )
            if owner is None:
                parent_owners = {
                    event_owner[parent_id]
                    for parent_id in event.causal_parent_event_ids
                    if parent_id in event_owner
                }
                if len(parent_owners) == 1:
                    owner = next(iter(parent_owners))
            if owner is not None:
                event_owner[event_id] = owner
            event_activation[event_id] = (
                attempt.activation_id,
                owner,
                causal_moment,
                causal_substep,
            )

    timeline: list[dict[str, object]] = []
    for event in result.core_result.events:
        exact = event.model_dump(mode="json")
        event_state = temporal_states[str(event.state_revision)]
        focus_ids: set[str] = set()
        focus_edges: set[str] = set()
        spatial_focus_ids: set[str] = set()
        spatial_link_ids: set[str] = set()
        for field in ("actor_entity_id", "mechanism_id", "representation_id"):
            value = exact.get(field)
            if isinstance(value, str) and value in node_ids:
                focus_ids.add(value)
        if (
            event.actor_entity_id is not None
            and event.actor_entity_id in event_state.placements
        ):
            spatial_focus_ids.add(event.actor_entity_id)
            spatial_focus_ids.add(
                event_state.placements[event.actor_entity_id].place_id
            )
        for representation_id in exact.get("read_representation_ids", []):
            if isinstance(representation_id, str) and representation_id in node_ids:
                focus_ids.add(representation_id)
        connection_id = exact.get("connection_id")
        if isinstance(connection_id, str):
            focus_edges.add(connection_id)
            connection = state.connections.get(connection_id)
            if connection is not None:
                focus_ids.add(state.ports[connection.source_port_id].owner_ref)
                focus_ids.add(state.ports[connection.target_port_id].owner_ref)
        for field in ("source_port_id", "target_port_id"):
            port_id = exact.get(field)
            if isinstance(port_id, str) and port_id in state.ports:
                focus_ids.add(state.ports[port_id].owner_ref)
        patch = exact.get("patch")
        if isinstance(patch, dict):
            for change in patch.get("fact_changes", []):
                if isinstance(change, dict):
                    fact_id = change.get("fact_id")
                    owner = fact_id.partition(".")[0] if isinstance(fact_id, str) else None
                    if owner in node_ids:
                        focus_ids.add(owner)
            for change in patch.get("placement_changes", []):
                if isinstance(change, dict):
                    for field in (
                        "entity_id",
                        "before_place_id",
                        "after_place_id",
                    ):
                        value = change.get(field)
                        if isinstance(value, str):
                            spatial_focus_ids.add(value)
                    spatial_link_id = change.get("via_spatial_link_id")
                    if isinstance(spatial_link_id, str):
                        spatial_link_ids.add(spatial_link_id)
            for observation in patch.get("observations_added", []):
                if isinstance(observation, dict):
                    target = observation.get("target_entity_id")
                    if isinstance(target, str) and target in node_ids:
                        focus_ids.add(target)
        for entity_id in exact.get("read_placement_entity_ids", []):
            if isinstance(entity_id, str):
                spatial_focus_ids.add(entity_id)
                placement = event_state.placements.get(entity_id)
                if placement is not None:
                    spatial_focus_ids.add(placement.place_id)
        for spatial_link_id in exact.get("read_spatial_link_ids", []):
            if isinstance(spatial_link_id, str):
                spatial_link_ids.add(spatial_link_id)
                spatial_link = state.spatial_links.get(spatial_link_id)
                if spatial_link is not None:
                    spatial_focus_ids.add(
                        spatial_link.endpoint_a_place_id
                    )
                    spatial_focus_ids.add(
                        spatial_link.endpoint_b_place_id
                    )
                    spatial_focus_ids.update(
                        spatial_link.substrate_entity_ids
                    )
        activation_record = event_activation.get(event.event_id)
        activation = activation_record[0] if activation_record is not None else None
        person = activation_record[1] if activation_record is not None else None
        projected_event: dict[str, object] = {
            "event_id": event.event_id,
            "sequence": event.sequence,
            "logical_time": event.logical_time,
            "state_revision": event.state_revision,
            "kind": event.event_kind,
            "summary": event.summary,
            "activation": activation,
            "person": person,
            "focus_ids": sorted(focus_ids),
            "focus_edges": sorted(focus_edges),
            "spatial_focus_ids": sorted(spatial_focus_ids),
            "spatial_link_ids": sorted(spatial_link_ids),
            "causal_parent_event_ids": list(event.causal_parent_event_ids),
        }
        details = exact.get("details")
        timing = details.get("timing") if isinstance(details, dict) else None
        if isinstance(timing, dict):
            projected_event["timing"] = timing
        if activation_record is not None:
            causal_time = activation_record[2]
            causal_substep = activation_record[3]
            projected_event.update(
                {
                    "causal_time": causal_time,
                    "causal_substep": causal_substep,
                    "causal_timestamp": f"c{causal_time}.{causal_substep}",
                }
            )
        mechanism = (
            state.mechanisms.get(event.mechanism_id)
            if event.mechanism_id is not None
            else None
        )
        if mechanism is not None:
            projected_event.update(
                {
                    "mechanism_id": mechanism.mechanism_id,
                    "mechanism_kind": mechanism.mechanism_kind,
                    "mechanism_description": mechanism.description,
                    "transition_contract": mechanism.mode,
                    "representation_abstraction": (
                        mechanism.fidelity.abstraction
                    ),
                    "representation_known_omissions": list(
                        mechanism.fidelity.known_omissions
                    ),
                }
            )
        timeline.append(projected_event)
    return timeline


def _causal_records(
    result: ActiveRuntimeResult,
) -> list[tuple[str, ActivationAttemptRecord | ExactWorkRecord]]:
    """Return retained agent and exact-only work in committed causal order."""
    by_prior_attempt_count: dict[int, list[ExactWorkRecord]] = {}
    for record in result.exact_work:
        by_prior_attempt_count.setdefault(record.prior_attempt_count, []).append(record)
    records: list[tuple[str, ActivationAttemptRecord | ExactWorkRecord]] = []
    for attempt_index, attempt in enumerate(result.attempts):
        records.extend(
            ("exact", record)
            for record in by_prior_attempt_count.get(attempt_index, [])
        )
        records.append(("activation", attempt))
    records.extend(
        ("exact", record)
        for record in by_prior_attempt_count.get(len(result.attempts), [])
    )
    return records


def analyst_traces(result: ActiveRuntimeResult) -> list[dict[str, object]]:
    """Project active people and exact processes with protected payloads redacted."""
    state = result.core_result.final_state
    traces: list[dict[str, object]] = []
    for attempt in result.attempts:
        for participant in attempt.participants:
            actions: list[dict[str, object]] = []
            if participant.proposal is not None:
                for action in participant.proposal.actions:
                    projected = action.model_dump(mode="json")
                    representation = (
                        state.representations.get(action.representation_id)
                        if action.representation_id is not None
                        else None
                    )
                    if representation is not None and representation.visibility == "mechanism":
                        projected["payload"] = "[redacted]"
                        projected["redacted"] = True
                    actions.append(projected)
            traces.append(
                {
                    "activation": attempt.activation_id,
                    "causal_time": attempt.attempt_index + 1,
                    "causal_timestamp": f"c{attempt.attempt_index + 1}",
                    "logical_time": attempt.logical_time,
                    "person": participant.requested_active_system_id,
                    "participant_kind": state.entities[
                        participant.input.entity_id
                    ].entity_kind,
                    "status": attempt.status,
                    "orientation": (
                        (
                            participant.call_evidence[-1].structured_output
                            or {}
                        ).get("orientation")
                        if participant.call_evidence
                        else (
                            "Deterministic exact process transition."
                            if state.entities[
                                participant.input.entity_id
                            ].entity_kind
                            == "state_machine"
                            else "Scripted zero-cost reference action."
                        )
                    ),
                    "activation_causes": [
                        cause.model_dump(mode="json")
                        for cause in participant.input.activation_causes
                    ],
                    "scheduled_update_before": (
                        participant.input.next_update_at
                    ),
                    "update_schedule": (
                        participant.proposal.update_schedule.model_dump(
                            mode="json"
                        )
                        if participant.proposal is not None
                        else None
                    ),
                    "model_call_count": len(participant.call_evidence),
                    "private_state_updated": (
                        participant.proposal is not None
                        and participant.input.private_state
                        != participant.proposal.private_state
                    ),
                    "actions": actions,
                    "observations": [
                        observation.model_dump(mode="json")
                        for observation in participant.input.observations
                    ],
                }
            )
    return traces


def service_desk_summary(
    arm_id: ServiceDeskArmId,
    outcome: Mapping[str, object],
) -> str:
    """Describe the realized outcome without presuming scripted success."""
    prefix = {
        "baseline": "The normal direct report path was available.",
        "no_direct_path": "The direct report path was unavailable.",
        "speed_priority": "The supervisor was exposed to a speed-priority incentive.",
    }[arm_id]
    final_status = str(outcome.get("final_status", "unknown")).replace("_", " ")
    remediation = outcome.get(
        "remediation_moment", outcome.get("remediation_activation")
    )
    closure = outcome.get(
        "confirmed_closure_moment",
        outcome.get("confirmed_closure_activation"),
    )
    raw_denied = outcome.get("denied_closure_attempt_count", 0)
    denied = raw_denied if isinstance(raw_denied, int) and not isinstance(raw_denied, bool) else 0
    if closure is not None:
        result = (
            f"The incident was remediated at causal step {remediation} and safely "
            f"closed after confirmation at causal step {closure}."
        )
    elif remediation is not None:
        result = (
            f"The incident was remediated at causal step {remediation}, but the run "
            f"ended {final_status} without confirmed closure."
        )
    else:
        result = f"The run ended {final_status} without remediation or confirmed closure."
    denial = (
        f" Exact mechanisms denied {denied} premature closure "
        f"{'attempt' if denied == 1 else 'attempts'}."
        if denied
        else ""
    )
    return f"{prefix} {result}{denial}"


def _representation_node(representation: RepresentationToken) -> dict[str, object]:
    if representation.visibility == "mechanism":
        state: dict[str, object] = {
            "representation_id": representation.representation_id,
            "encoding": representation.encoding,
            "visibility": "mechanism",
            "redacted": True,
        }
        description = "Protected mechanism-only representation."
    else:
        state = representation.model_dump(mode="json")
        description = representation.encoding
    return {
        "id": representation.representation_id,
        "kind": "information",
        "label": _label(representation.representation_id),
        "description": description,
        "state": state,
    }


def _redact_representation_mapping(item: Mapping[str, object]) -> dict[str, object]:
    return {
        "representation_id": item.get("representation_id"),
        "encoding": item.get("encoding"),
        "visibility": "mechanism",
        "redacted": True,
    }


def _label(identifier: str) -> str:
    return identifier.replace("_", " ").title()
