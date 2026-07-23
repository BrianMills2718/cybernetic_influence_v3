"""Visibility-safe temporal projection for the analyst-facing simulator."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy

from cybernetic_influence.active_runtime import ActiveRuntimeResult
from cybernetic_influence.causal_core.models import (
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
    readout: ServiceDeskTrialReadout,
    profile: ServiceDeskCognitionProfile,
    arm_id: ServiceDeskArmId,
    execution: str,
    created_at: str,
) -> dict[str, object]:
    """Project one protected result into a retained analyst document."""
    outcome = readout.model_dump(mode="json")
    return build_analyst_document(
        initial_state=fixture.scenario.initial_state,
        result=result,
        scenario="service_desk",
        profile=profile,
        arm_id=arm_id,
        execution=execution,
        created_at=created_at,
        outcome=outcome,
        headline=readout.target_outcome.replace("_", " ").title(),
        summary=service_desk_summary(arm_id, outcome),
    )


def build_analyst_document(
    *,
    initial_state: CausalState,
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
    snapshots = analyst_snapshots(initial_state, result.core_result.events)
    nodes = snapshots[str(final_state.revision)]
    edges = [
        {
            "id": connection.connection_id,
            "source": final_state.ports[connection.source_port_id].owner_ref,
            "target": final_state.ports[connection.target_port_id].owner_ref,
            "enabled": connection.enabled,
            "description": connection.description,
        }
        for connection in final_state.connections.values()
    ]
    timeline = analyst_timeline(result)
    traces = analyst_traces(result)
    return {
        "run_id": result.run_id,
        "created_at": created_at,
        "status": result.status,
        "scenario": scenario,
        "profile": profile,
        "arm": arm_id,
        "execution": execution,
        "model_calls": result.model_calls,
        "cost": result.total_observed_cost,
        "cost_fully_observable": result.cost_fully_observable,
        "story": {
            "headline": headline,
            "summary": summary,
            "steps": [event for event in timeline if event["kind"] == "action_attempted"],
        },
        "outcome": dict(outcome),
        "nodes": nodes,
        "snapshots": snapshots,
        "edges": edges,
        "timeline": timeline,
        "events": [analyst_event(event) for event in result.core_result.events],
        "traces": traces,
    }


def analyst_snapshots(
    initial_state: CausalState,
    events: Sequence[CausalEvent],
) -> dict[str, list[dict[str, object]]]:
    """Reconstruct and project one canonical state for every observed revision."""
    snapshots: dict[str, list[dict[str, object]]] = {
        str(initial_state.revision): analyst_nodes(initial_state)
    }
    prefix: list[CausalEvent] = []
    for event in events:
        prefix.append(event)
        revision = str(event.state_revision)
        if revision not in snapshots:
            snapshots[revision] = analyst_nodes(
                replay_event_prefix(initial_state, prefix)
            )
    return snapshots


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


def analyst_timeline(result: ActiveRuntimeResult) -> list[dict[str, object]]:
    """Link each event to exact temporal, activation, entity, and route identities."""
    state = result.core_result.final_state
    node_ids = {str(node["id"]) for node in analyst_nodes(state)}
    event_activation: dict[str, tuple[str, str | None]] = {}
    for attempt in result.attempts:
        people = {
            participant.requested_active_system_id
            for participant in attempt.participants
        }
        person = next(iter(people)) if len(people) == 1 else None
        for event_id in attempt.core_event_ids:
            event_activation[event_id] = (attempt.activation_id, person)

    timeline: list[dict[str, object]] = []
    for event in result.core_result.events:
        exact = event.model_dump(mode="json")
        focus_ids: set[str] = set()
        focus_edges: set[str] = set()
        for field in ("actor_entity_id", "mechanism_id", "representation_id"):
            value = exact.get(field)
            if isinstance(value, str) and value in node_ids:
                focus_ids.add(value)
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
            for observation in patch.get("observations_added", []):
                if isinstance(observation, dict):
                    target = observation.get("target_entity_id")
                    if isinstance(target, str) and target in node_ids:
                        focus_ids.add(target)
        activation, person = event_activation.get(event.event_id, (None, None))
        timeline.append(
            {
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
            }
        )
    return timeline


def analyst_traces(result: ActiveRuntimeResult) -> list[dict[str, object]]:
    """Project person activations while redacting protected action payloads."""
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
                    "logical_time": attempt.logical_time,
                    "person": participant.requested_active_system_id,
                    "status": attempt.status,
                    "orientation": (
                        (
                            participant.call_evidence[-1].structured_output
                            or {}
                        ).get("orientation")
                        if participant.call_evidence
                        else "Scripted zero-cost reference action."
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
    remediation = outcome.get("remediation_activation")
    closure = outcome.get("confirmed_closure_activation")
    raw_denied = outcome.get("denied_closure_attempt_count", 0)
    denied = raw_denied if isinstance(raw_denied, int) and not isinstance(raw_denied, bool) else 0
    if closure is not None:
        result = (
            f"The incident was remediated at activation {remediation} and safely "
            f"closed after confirmation at activation {closure}."
        )
    elif remediation is not None:
        result = (
            f"The incident was remediated at activation {remediation}, but the run "
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
