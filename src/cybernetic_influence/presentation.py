"""Visibility-safe temporal projection for the analyst-facing simulator."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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
    "mechanism_executed",
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


def analyst_progress_projection(
    checkpoint: ActiveRuntimeCheckpoint,
    update: RuntimeProgressUpdate,
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
    return {
        "state_revision": state.revision,
        "nodes": analyst_nodes(state),
        "edges": analyst_edges(state),
        "world": world,
        "events": events,
        "animation_cues": cues,
    }


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
        # A mechanism event proves execution, but not an unrecorded semantic
        # judgement such as "accepted" or "denied".  Keep the visual claim
        # exactly at the retained event's evidence level.
        cue_kind = "mechanism_executed"
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
from cybernetic_influence.causal_core.replay import replay_event_prefix
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
    states: dict[str, CausalState] = {
        str(initial_state.revision): initial_state.model_copy(deep=True)
    }
    prefix: list[CausalEvent] = []
    for event in events:
        prefix.append(event)
        revision = str(event.state_revision)
        if revision not in states:
            states[revision] = replay_event_prefix(initial_state, prefix)
    return states


def analyst_boundaries(
    boundaries: Sequence[AnalyticalBoundary],
    temporal_states: Mapping[str, CausalState],
    edges: Sequence[Mapping[str, object]],
    timeline: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Derive reversible aggregate evidence without creating runtime state."""
    projected: list[dict[str, object]] = []
    members_by_boundary_revision: dict[tuple[str, str], set[str]] = {}

    for boundary in boundaries:
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
