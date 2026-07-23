"""Redacted graph and evidence-linked narrative projections for exact runs."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from cybernetic_influence.causal_core.models import (
    CausalEvent,
    CausalCheckpoint,
    CausalRunResult,
    CausalScenario,
    CausalState,
    EventKind,
    scenario_execution_fingerprint,
    scenario_fingerprint,
)

_FORBID = ConfigDict(extra="forbid", strict=True)


class GraphNode(BaseModel):
    """One selectable grounded referent or analytical boundary."""

    model_config = _FORBID

    node_id: str = Field(min_length=1)
    node_kind: Literal[
        "entity",
        "container",
        "place",
        "port",
        "mechanism",
        "carrier",
        "representation",
        "boundary",
    ]
    label: str = Field(min_length=1)
    properties: dict[str, JsonValue] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """One selectable ownership, topology, substrate, or view relationship."""

    model_config = _FORBID

    edge_id: str = Field(min_length=1)
    source_node_id: str = Field(min_length=1)
    target_node_id: str = Field(min_length=1)
    edge_kind: Literal[
        "owns",
        "contains",
        "connects",
        "binds_input",
        "declares_output",
        "uses_substrate",
        "reads_representation",
        "carries",
        "derived_from",
        "located_in",
        "within",
        "spatially_connected",
        "derived_member",
    ]
    label: str = Field(min_length=1)
    properties: dict[str, JsonValue] = Field(default_factory=dict)


class GraphOccurrence(BaseModel):
    """One canonical event projected onto selectable graph referents."""

    model_config = _FORBID

    occurrence_id: str = Field(min_length=1)
    event_id: str = Field(pattern=r"^event_[0-9]{6}$")
    sequence: int = Field(ge=0)
    event_kind: EventKind
    logical_time: int = Field(ge=0)
    state_revision: int = Field(ge=0)
    summary: str = Field(min_length=1)
    node_refs: list[str] = Field(default_factory=list)
    edge_refs: list[str] = Field(default_factory=list)
    causal_parent_occurrence_ids: list[str] = Field(default_factory=list)


class CausalGraphArtifact(BaseModel):
    """Versioned redacted graph plus one occurrence and narrative per event."""

    model_config = _FORBID

    artifact_contract: Literal["causal-graph.v2"] = "causal-graph.v2"
    schema_version: Literal[2] = 2
    source_runtime_contract: Literal["causal-core.v2"] = "causal-core.v2"
    scenario_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    source_scenario_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    projection_scenario_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_execution_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_event_tail_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_final_state_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_event_count: int = Field(ge=1)
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    occurrences: list[GraphOccurrence]
    narrative: list[str]

    @model_validator(mode="after")
    def validate_artifact(self) -> "CausalGraphArtifact":
        """Keep identifiers, topology, occurrences, and narrative aligned."""
        _validate_graph_structure(
            nodes=self.nodes,
            edges=self.edges,
            occurrences=self.occurrences,
            narrative=self.narrative,
            source_event_count=self.source_event_count,
        )
        return self


class CausalPrefixGraphArtifact(BaseModel):
    """Versioned redacted graph over one validated quiescent checkpoint."""

    model_config = _FORBID

    artifact_contract: Literal["causal-graph-prefix.v2"] = "causal-graph-prefix.v2"
    schema_version: Literal[2] = 2
    source_runtime_contract: Literal["causal-core.v2"] = "causal-core.v2"
    scenario_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    source_checkpoint_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_scenario_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    projection_scenario_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_execution_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_event_tail_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_state_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_event_count: int = Field(ge=1)
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    occurrences: list[GraphOccurrence]
    narrative: list[str]

    @model_validator(mode="after")
    def validate_artifact(self) -> "CausalPrefixGraphArtifact":
        """Keep checkpoint topology, occurrences, and narrative aligned."""
        _validate_graph_structure(
            nodes=self.nodes,
            edges=self.edges,
            occurrences=self.occurrences,
            narrative=self.narrative,
            source_event_count=self.source_event_count,
        )
        return self


def _validate_graph_structure(
    *,
    nodes: Sequence[GraphNode],
    edges: Sequence[GraphEdge],
    occurrences: Sequence[GraphOccurrence],
    narrative: Sequence[str],
    source_event_count: int,
) -> None:
    """Validate the graph body shared by terminal and checkpoint envelopes."""
    node_ids = [node.node_id for node in nodes]
    edge_ids = [edge.edge_id for edge in edges]
    occurrence_ids = [item.occurrence_id for item in occurrences]
    event_ids = [item.event_id for item in occurrences]
    if len(node_ids) != len(set(node_ids)):
        raise ValueError("graph node ids must be unique")
    if len(edge_ids) != len(set(edge_ids)):
        raise ValueError("graph edge ids must be unique")
    if len(occurrence_ids) != len(set(occurrence_ids)):
        raise ValueError("graph occurrence ids must be unique")
    if len(event_ids) != len(set(event_ids)):
        raise ValueError("graph occurrence event ids must be unique")
    if source_event_count != len(occurrences):
        raise ValueError("source event count must equal occurrence count")
    known_nodes = set(node_ids)
    known_edges = set(edge_ids)
    for edge in edges:
        if (
            edge.source_node_id not in known_nodes
            or edge.target_node_id not in known_nodes
        ):
            raise ValueError(f"edge {edge.edge_id!r} has unknown endpoint")
    known_occurrences: set[str] = set()
    for sequence, occurrence in enumerate(occurrences):
        if occurrence.sequence != sequence:
            raise ValueError("graph occurrence sequences must be contiguous")
        if occurrence.event_id != f"event_{sequence:06d}":
            raise ValueError("graph occurrence event id must match sequence")
        if occurrence.occurrence_id != f"occurrence:{occurrence.event_id}":
            raise ValueError("graph occurrence id must match its event id")
        if len(occurrence.node_refs) != len(set(occurrence.node_refs)):
            raise ValueError("graph occurrence node refs must be unique")
        if len(occurrence.edge_refs) != len(set(occurrence.edge_refs)):
            raise ValueError("graph occurrence edge refs must be unique")
        unknown_nodes = set(occurrence.node_refs) - known_nodes
        if unknown_nodes:
            raise ValueError(
                f"occurrence {occurrence.occurrence_id!r} has unknown nodes"
            )
        unknown_edges = set(occurrence.edge_refs) - known_edges
        if unknown_edges:
            raise ValueError(
                f"occurrence {occurrence.occurrence_id!r} has unknown edges"
            )
        unknown_parents = (
            set(occurrence.causal_parent_occurrence_ids) - known_occurrences
        )
        if unknown_parents:
            raise ValueError(
                f"occurrence {occurrence.occurrence_id!r} has unknown parents"
            )
        known_occurrences.add(occurrence.occurrence_id)
    if len(narrative) != len(occurrences):
        raise ValueError("narrative must contain one line per occurrence")
    expected_narrative = [f"{item.event_id}: {item.summary}" for item in occurrences]
    if list(narrative) != expected_narrative:
        raise ValueError("narrative must be the canonical event-derived text")


def narrative_lines(result: CausalRunResult) -> list[str]:
    """Render one evidence-addressed human-readable line per canonical event."""
    validated = CausalRunResult.model_validate(result.model_dump(mode="json"))
    return [f"{event.event_id}: {event.summary}" for event in validated.events]


def checkpoint_narrative_lines(checkpoint: CausalCheckpoint) -> list[str]:
    """Render evidence-addressed lines for one canonical checkpoint prefix."""
    validated = CausalCheckpoint.model_validate(checkpoint.model_dump(mode="json"))
    return [f"{event.event_id}: {event.summary}" for event in validated.events]


def project_graph(
    scenario: CausalScenario,
    result: CausalRunResult,
) -> CausalGraphArtifact:
    """Project one completed result without exposing protected fact values."""
    scenario = CausalScenario.model_validate(scenario.model_dump(mode="json"))
    result = CausalRunResult.model_validate(result.model_dump(mode="json"))
    if scenario.scenario_id != result.scenario_id:
        raise ValueError("scenario and result ids do not match")
    if result.scenario_execution_fingerprint != scenario_execution_fingerprint(
        scenario
    ):
        raise ValueError("scenario and result execution fingerprints do not match")
    nodes, edges, occurrences = _project_graph_components(
        scenario,
        result.final_state,
        result.events,
    )
    return CausalGraphArtifact(
        scenario_id=scenario.scenario_id,
        run_id=result.run_id,
        source_scenario_fingerprint=result.scenario_fingerprint,
        projection_scenario_fingerprint=scenario_fingerprint(scenario),
        source_execution_fingerprint=result.scenario_execution_fingerprint,
        source_event_tail_digest=result.event_tail_digest,
        source_final_state_digest=result.final_state_digest,
        source_event_count=len(result.events),
        nodes=nodes,
        edges=edges,
        occurrences=occurrences,
        narrative=narrative_lines(result),
    )


def project_checkpoint_graph(
    scenario: CausalScenario,
    checkpoint: CausalCheckpoint,
) -> CausalPrefixGraphArtifact:
    """Project one quiescent committed prefix without terminal implications."""
    scenario = CausalScenario.model_validate(scenario.model_dump(mode="json"))
    checkpoint = CausalCheckpoint.model_validate(checkpoint.model_dump(mode="json"))
    if scenario.scenario_id != checkpoint.scenario_id:
        raise ValueError("scenario and checkpoint ids do not match")
    if checkpoint.scenario_execution_fingerprint != scenario_execution_fingerprint(
        scenario
    ):
        raise ValueError("scenario and checkpoint execution fingerprints do not match")
    nodes, edges, occurrences = _project_graph_components(
        scenario,
        checkpoint.state,
        checkpoint.events,
    )
    return CausalPrefixGraphArtifact(
        scenario_id=scenario.scenario_id,
        run_id=checkpoint.run_id,
        source_checkpoint_digest=checkpoint.record_digest,
        source_scenario_fingerprint=checkpoint.scenario_fingerprint,
        projection_scenario_fingerprint=scenario_fingerprint(scenario),
        source_execution_fingerprint=checkpoint.scenario_execution_fingerprint,
        source_event_tail_digest=checkpoint.event_tail_digest,
        source_state_digest=checkpoint.state_digest,
        source_event_count=len(checkpoint.events),
        nodes=nodes,
        edges=edges,
        occurrences=occurrences,
        narrative=checkpoint_narrative_lines(checkpoint),
    )


def validate_checkpoint_graph_artifact(
    scenario: CausalScenario,
    checkpoint: CausalCheckpoint,
    artifact: CausalPrefixGraphArtifact,
) -> CausalPrefixGraphArtifact:
    """Recompute one prefix graph so a re-digested forgery still fails."""
    validated = CausalPrefixGraphArtifact.model_validate(
        artifact.model_dump(mode="json")
    )
    if validated != project_checkpoint_graph(scenario, checkpoint):
        raise ValueError("causal prefix graph disagrees with source checkpoint")
    return validated


def _project_graph_components(
    scenario: CausalScenario,
    state: CausalState,
    events: Sequence[CausalEvent],
) -> tuple[list[GraphNode], list[GraphEdge], list[GraphOccurrence]]:
    """Build the redacted graph body shared by terminal and prefix envelopes."""
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []

    for entity in sorted(state.entities.values(), key=lambda item: item.entity_id):
        facts: dict[str, JsonValue] = {}
        for name, fact in sorted(entity.attributes.items()):
            record: dict[str, JsonValue] = {"visibility": fact.visibility}
            if fact.visibility == "public":
                record["value"] = fact.value
            facts[name] = record
        nodes.append(
            GraphNode(
                node_id=_node("entity", entity.entity_id),
                node_kind="entity",
                label=entity.entity_id,
                properties={
                    "entity_kind": entity.entity_kind,
                    "description": entity.description,
                    "facts": facts,
                },
            )
        )

    for container in sorted(
        state.containers.values(), key=lambda item: item.container_id
    ):
        nodes.append(
            GraphNode(
                node_id=_node("container", container.container_id),
                node_kind="container",
                label=container.container_id,
                properties={"description": container.description},
            )
        )
        for entity_id in sorted(container.member_entity_ids):
            edges.append(
                GraphEdge(
                    edge_id=f"contains:{container.container_id}:{entity_id}",
                    source_node_id=_node("container", container.container_id),
                    target_node_id=_node("entity", entity_id),
                    edge_kind="contains",
                    label="contains",
                )
            )

    for place in sorted(state.places.values(), key=lambda item: item.place_id):
        nodes.append(
            GraphNode(
                node_id=_node("place", place.place_id),
                node_kind="place",
                label=place.place_id,
                properties={
                    "place_kind": place.place_kind,
                    "description": place.description,
                    "parent_place_id": place.parent_place_id,
                },
            )
        )
        if place.parent_place_id is not None:
            edges.append(
                GraphEdge(
                    edge_id=f"within:{place.place_id}:{place.parent_place_id}",
                    source_node_id=_node("place", place.place_id),
                    target_node_id=_node("place", place.parent_place_id),
                    edge_kind="within",
                    label="within",
                )
            )

    for placement in sorted(
        state.placements.values(), key=lambda item: item.entity_id
    ):
        edges.append(
            GraphEdge(
                edge_id=f"entity_location:{placement.entity_id}",
                source_node_id=_node("entity", placement.entity_id),
                target_node_id=_node("place", placement.place_id),
                edge_kind="located_in",
                label="located in",
            )
        )

    for spatial_link in sorted(
        state.spatial_links.values(),
        key=lambda item: item.spatial_link_id,
    ):
        edges.append(
            GraphEdge(
                edge_id=f"spatial_link:{spatial_link.spatial_link_id}",
                source_node_id=_node(
                    "place", spatial_link.endpoint_a_place_id
                ),
                target_node_id=_node(
                    "place", spatial_link.endpoint_b_place_id
                ),
                edge_kind="spatially_connected",
                label="topologically connected",
                properties={
                    "spatial_link_id": spatial_link.spatial_link_id,
                    "link_kind": spatial_link.link_kind,
                    "substrate_entity_ids": cast(
                        JsonValue,
                        list(spatial_link.substrate_entity_ids),
                    ),
                    "directed": False,
                    "does_not_imply_traversability": True,
                    "description": spatial_link.description,
                },
            )
        )

    for port in sorted(state.ports.values(), key=lambda item: item.port_id):
        nodes.append(
            GraphNode(
                node_id=_node("port", port.port_id),
                node_kind="port",
                label=port.port_id,
                properties={
                    "direction": port.direction,
                    "effect_type": port.effect_type,
                    "description": port.description,
                    "container_id": port.container_id,
                },
            )
        )
        owner_kind = "mechanism" if port.owner_ref in state.mechanisms else "entity"
        edges.append(
            GraphEdge(
                edge_id=f"owns:{port.owner_ref}:{port.port_id}",
                source_node_id=_node(owner_kind, port.owner_ref),
                target_node_id=_node("port", port.port_id),
                edge_kind="owns",
                label="owns interface",
            )
        )
        if port.container_id is not None:
            edges.append(
                GraphEdge(
                    edge_id=f"located_in:{port.port_id}:{port.container_id}",
                    source_node_id=_node("port", port.port_id),
                    target_node_id=_node("container", port.container_id),
                    edge_kind="located_in",
                    label="located in",
                )
            )

    for mechanism in sorted(
        state.mechanisms.values(), key=lambda item: item.mechanism_id
    ):
        mechanism_properties: dict[str, JsonValue] = {
            "mechanism_kind": mechanism.mechanism_kind,
            "mode": mechanism.mode,
            "implementation_id": mechanism.implementation_id,
            "description": mechanism.description,
            "read_fact_ids": _json_string_list(mechanism.read_fact_ids),
            "read_representation_ids": _json_string_list(
                mechanism.read_representation_ids
            ),
            "read_placement_entity_ids": _json_string_list(
                mechanism.read_placement_entity_ids
            ),
            "read_spatial_link_ids": _json_string_list(
                mechanism.read_spatial_link_ids
            ),
            "write_fact_ids": _json_string_list(mechanism.write_fact_ids),
            "write_placement_entity_ids": _json_string_list(
                mechanism.write_placement_entity_ids
            ),
            "write_carrier_ids": _json_string_list(mechanism.write_carrier_ids),
            "observation_target_ids": _json_string_list(
                mechanism.observation_target_ids
            ),
            "invariant_ids": _json_string_list(mechanism.invariant_ids),
            "fidelity": mechanism.fidelity.model_dump(mode="json"),
        }
        nodes.append(
            GraphNode(
                node_id=_node("mechanism", mechanism.mechanism_id),
                node_kind="mechanism",
                label=mechanism.mechanism_id,
                properties=mechanism_properties,
            )
        )
        for port_id in mechanism.input_port_ids:
            edges.append(
                GraphEdge(
                    edge_id=f"input:{mechanism.mechanism_id}:{port_id}",
                    source_node_id=_node("port", port_id),
                    target_node_id=_node("mechanism", mechanism.mechanism_id),
                    edge_kind="binds_input",
                    label="dispatches to",
                )
            )
        for port_id in mechanism.output_port_ids:
            edges.append(
                GraphEdge(
                    edge_id=f"output:{mechanism.mechanism_id}:{port_id}",
                    source_node_id=_node("mechanism", mechanism.mechanism_id),
                    target_node_id=_node("port", port_id),
                    edge_kind="declares_output",
                    label="emits through",
                )
            )
        for substrate_ref in mechanism.substrate_refs:
            substrate_kind = "carrier" if substrate_ref in state.carriers else "entity"
            edges.append(
                GraphEdge(
                    edge_id=(f"substrate:{mechanism.mechanism_id}:{substrate_ref}"),
                    source_node_id=_node("mechanism", mechanism.mechanism_id),
                    target_node_id=_node(substrate_kind, substrate_ref),
                    edge_kind="uses_substrate",
                    label="uses substrate",
                )
            )
        for representation_id in mechanism.read_representation_ids:
            edges.append(
                GraphEdge(
                    edge_id=(
                        f"reads_representation:{mechanism.mechanism_id}:"
                        f"{representation_id}"
                    ),
                    source_node_id=_node("mechanism", mechanism.mechanism_id),
                    target_node_id=_node("representation", representation_id),
                    edge_kind="reads_representation",
                    label="reads stored representation",
                )
            )

    for connection in sorted(
        state.connections.values(), key=lambda item: item.connection_id
    ):
        edges.append(
            GraphEdge(
                edge_id=f"connection:{connection.connection_id}",
                source_node_id=_node("port", connection.source_port_id),
                target_node_id=_node("port", connection.target_port_id),
                edge_kind="connects",
                label=connection.connection_id,
                properties={
                    "enabled": connection.enabled,
                    "delay": connection.delay,
                    "description": connection.description,
                },
            )
        )

    for carrier in sorted(state.carriers.values(), key=lambda item: item.carrier_id):
        carrier_properties: dict[str, JsonValue] = {
            "owner_ref": carrier.owner_ref,
            "medium": carrier.medium,
            "revision": carrier.revision,
            "visibility": carrier.visibility,
        }
        if carrier.visibility == "public":
            carrier_properties["locator"] = carrier.locator
        nodes.append(
            GraphNode(
                node_id=_node("carrier", carrier.carrier_id),
                node_kind="carrier",
                label=carrier.carrier_id,
                properties=carrier_properties,
            )
        )
        owner_kind = "mechanism" if carrier.owner_ref in state.mechanisms else "entity"
        edges.append(
            GraphEdge(
                edge_id=f"owns_carrier:{carrier.owner_ref}:{carrier.carrier_id}",
                source_node_id=_node(owner_kind, carrier.owner_ref),
                target_node_id=_node("carrier", carrier.carrier_id),
                edge_kind="owns",
                label="owns carrier",
            )
        )

    for representation in sorted(
        state.representations.values(), key=lambda item: item.representation_id
    ):
        representation_properties: dict[str, JsonValue] = {
            "encoding": representation.encoding,
            "visibility": representation.visibility,
        }
        if representation.visibility == "public":
            representation_properties.update(
                {
                    "carrier_id": representation.carrier_id,
                    "carrier_revision": representation.carrier_revision,
                    "content_hash": representation.content_hash,
                    "actual_source_ref": representation.actual_source_ref,
                    "parent_representation_ids": _json_string_list(
                        representation.parent_representation_ids
                    ),
                    "content": representation.content,
                }
            )
        else:
            representation_properties["redacted"] = True
        nodes.append(
            GraphNode(
                node_id=_node("representation", representation.representation_id),
                node_kind="representation",
                label=representation.representation_id,
                properties=representation_properties,
            )
        )
        edges.append(
            GraphEdge(
                edge_id=(
                    f"carries:{representation.carrier_id}:"
                    f"{representation.representation_id}"
                ),
                source_node_id=_node("carrier", representation.carrier_id),
                target_node_id=_node(
                    "representation", representation.representation_id
                ),
                edge_kind="carries",
                label="carries token",
            )
        )
        for parent_id in representation.parent_representation_ids:
            edges.append(
                GraphEdge(
                    edge_id=(
                        f"derived_from:{representation.representation_id}:{parent_id}"
                    ),
                    source_node_id=_node(
                        "representation", representation.representation_id
                    ),
                    target_node_id=_node("representation", parent_id),
                    edge_kind="derived_from",
                    label="derived from",
                )
            )

    runtime_node_refs = {
        **{
            item.entity_id: _node("entity", item.entity_id)
            for item in state.entities.values()
        },
            **{
                item.container_id: _node("container", item.container_id)
                for item in state.containers.values()
            },
            **{
                item.place_id: _node("place", item.place_id)
                for item in state.places.values()
            },
        **{item.port_id: _node("port", item.port_id) for item in state.ports.values()},
        **{
            item.mechanism_id: _node("mechanism", item.mechanism_id)
            for item in state.mechanisms.values()
        },
        **{
            item.carrier_id: _node("carrier", item.carrier_id)
            for item in state.carriers.values()
        },
        **{
            item.representation_id: _node("representation", item.representation_id)
            for item in state.representations.values()
        },
    }
    for boundary in sorted(
        scenario.analytical_boundaries, key=lambda item: item.boundary_id
    ):
        nodes.append(
            GraphNode(
                node_id=_node("boundary", boundary.boundary_id),
                node_kind="boundary",
                label=boundary.label,
                properties={
                    "description": boundary.description,
                    "executor": boundary.executor,
                },
            )
        )
        for member_ref in sorted(boundary.member_refs):
            member_node = runtime_node_refs.get(member_ref)
            if member_node is None:
                raise ValueError(f"boundary member {member_ref!r} has no graph node")
            edges.append(
                GraphEdge(
                    edge_id=f"boundary:{boundary.boundary_id}:{member_ref}",
                    source_node_id=_node("boundary", boundary.boundary_id),
                    target_node_id=member_node,
                    edge_kind="derived_member",
                    label="derived member",
                )
            )

    occurrences = [_project_occurrence(event, state) for event in events]
    return nodes, edges, occurrences


def _project_occurrence(event: CausalEvent, state: CausalState) -> GraphOccurrence:
    """Link one event to its concrete referents and authored relationships."""
    refs: set[str] = set()
    edge_refs: set[str] = set()

    def add_carrier(carrier_id: str) -> None:
        carrier = state.carriers[carrier_id]
        refs.add(_node("carrier", carrier_id))
        owner_kind = "mechanism" if carrier.owner_ref in state.mechanisms else "entity"
        refs.add(_node(owner_kind, carrier.owner_ref))
        edge_refs.add(f"owns_carrier:{carrier.owner_ref}:{carrier_id}")

    def add_representation(representation_id: str) -> None:
        representation = state.representations[representation_id]
        refs.add(_node("representation", representation_id))
        add_carrier(representation.carrier_id)
        edge_refs.add(f"carries:{representation.carrier_id}:{representation_id}")
        for parent_id in representation.parent_representation_ids:
            refs.add(_node("representation", parent_id))
            edge_refs.add(f"derived_from:{representation_id}:{parent_id}")

    def add_port(port_id: str) -> None:
        port = state.ports[port_id]
        refs.add(_node("port", port_id))
        owner_kind = "mechanism" if port.owner_ref in state.mechanisms else "entity"
        refs.add(_node(owner_kind, port.owner_ref))
        edge_refs.add(f"owns:{port.owner_ref}:{port_id}")
        if port.direction == "output" and port.owner_ref in state.mechanisms:
            edge_refs.add(f"output:{port.owner_ref}:{port_id}")
        if port.container_id is not None:
            refs.add(_node("container", port.container_id))
            edge_refs.add(f"located_in:{port_id}:{port.container_id}")

    def add_mechanism(mechanism_id: str) -> None:
        mechanism = state.mechanisms[mechanism_id]
        refs.add(_node("mechanism", mechanism_id))
        for substrate_ref in mechanism.substrate_refs:
            substrate_kind = "carrier" if substrate_ref in state.carriers else "entity"
            refs.add(_node(substrate_kind, substrate_ref))
            edge_refs.add(f"substrate:{mechanism_id}:{substrate_ref}")
        for fact_id in mechanism.read_fact_ids:
            entity_id = fact_id.split(".", maxsplit=1)[0]
            refs.add(_node("entity", entity_id))
        for representation_id in mechanism.read_representation_ids:
            add_representation(representation_id)
            edge_refs.add(
                f"reads_representation:{mechanism_id}:{representation_id}"
            )
        for entity_id in mechanism.read_placement_entity_ids:
            refs.add(_node("entity", entity_id))
        for spatial_link_id in mechanism.read_spatial_link_ids:
            spatial_link = state.spatial_links[spatial_link_id]
            refs.add(_node("place", spatial_link.endpoint_a_place_id))
            refs.add(_node("place", spatial_link.endpoint_b_place_id))
            edge_refs.add(f"spatial_link:{spatial_link_id}")

    if event.actor_entity_id is not None:
        refs.add(_node("entity", event.actor_entity_id))
    if event.mechanism_id is not None:
        add_mechanism(event.mechanism_id)
    for port_id in (event.source_port_id, event.target_port_id):
        if port_id is not None:
            add_port(port_id)
    if event.mechanism_id is not None and event.target_port_id is not None:
        edge_refs.add(f"input:{event.mechanism_id}:{event.target_port_id}")
    if event.representation_id is not None:
        add_representation(event.representation_id)
    if event.route_kind == "connection":
        assert event.connection_id is not None
        edge_refs.add(f"connection:{event.connection_id}")
    elif event.route_kind == "container":
        assert event.container_id is not None
        refs.add(_node("container", event.container_id))
    if event.observation_id is not None:
        observation = state.observations[event.observation_id]
        refs.add(_node("entity", observation.target_entity_id))
    if event.patch is not None:
        for change in event.patch.fact_changes:
            entity_id = change.fact_id.split(".", maxsplit=1)[0]
            refs.add(_node("entity", entity_id))
        for placement_change in event.patch.placement_changes:
            refs.add(_node("entity", placement_change.entity_id))
            refs.add(_node("place", placement_change.before_place_id))
            refs.add(_node("place", placement_change.after_place_id))
            edge_refs.add(
                f"spatial_link:{placement_change.via_spatial_link_id}"
            )
            edge_refs.add(f"entity_location:{placement_change.entity_id}")
        for carrier_change in event.patch.carrier_changes:
            add_carrier(carrier_change.carrier_id)
        for representation in event.patch.representations_added:
            add_representation(representation.representation_id)
        for observation in event.patch.observations_added:
            refs.add(_node("entity", observation.target_entity_id))
    return GraphOccurrence(
        occurrence_id=f"occurrence:{event.event_id}",
        event_id=event.event_id,
        sequence=event.sequence,
        event_kind=event.event_kind,
        logical_time=event.logical_time,
        state_revision=event.state_revision,
        summary=event.summary,
        node_refs=sorted(refs),
        edge_refs=sorted(edge_refs),
        causal_parent_occurrence_ids=[
            f"occurrence:{event_id}" for event_id in event.causal_parent_event_ids
        ],
    )


def _node(kind: str, identifier: str) -> str:
    """Build one stable namespaced graph node identifier."""
    return f"{kind}:{identifier}"


def _json_string_list(values: list[str]) -> list[JsonValue]:
    """Widen a typed string list to the invariant JSON-value list type."""
    return [value for value in values]
