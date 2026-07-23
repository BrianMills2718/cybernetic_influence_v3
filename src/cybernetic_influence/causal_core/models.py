"""Strict versioned contracts for the exact model-free causal core.

The module deliberately contains no cognition, stochastic sampler, model
adapter, v2 compatibility layer, or workbench model.  It defines the canonical
records needed to execute and reconstruct one exact locally routed trajectory.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

RUNTIME_CONTRACT = "causal-core.v2"
SCHEMA_VERSION = 2

_FORBID = ConfigDict(extra="forbid", strict=True)
_ID_PATTERN = r"^[a-z][a-z0-9_]*$"
_FACT_PATTERN = r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$"
_DIGEST_PATTERN = r"^[0-9a-f]{64}$"

Visibility = Literal["public", "analyst", "mechanism"]
RouteKind = Literal["container", "connection"]
EventKind = Literal[
    "run_started",
    "action_attempted",
    "effect_emitted",
    "effect_routed",
    "effect_dissipated",
    "mechanism_executed",
    "state_committed",
    "observation_delivered",
    "run_completed",
]
VarianceSource = Literal["none", "external_action", "exact"]


class _StrictModel(BaseModel):
    """Base class that rejects coercion and unknown fields."""

    model_config = _FORBID


class FactState(_StrictModel):
    """One addressable state value with an audience boundary."""

    value: JsonValue
    visibility: Visibility = "public"


class EntityState(_StrictModel):
    """One persistent referent; its kind does not assert agency."""

    entity_id: str = Field(pattern=_ID_PATTERN)
    entity_kind: str = Field(pattern=_ID_PATTERN)
    description: str = Field(min_length=1)
    attributes: dict[str, FactState] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_attribute_names(self) -> "EntityState":
        """Keep fact paths normalized and unambiguous."""
        for attribute in self.attributes:
            _validate_id_token(attribute, "attribute")
        return self


class ContainerState(_StrictModel):
    """Authored typed-broadcast locus; not authoritative spatial location."""

    container_id: str = Field(pattern=_ID_PATTERN)
    description: str = Field(min_length=1)
    member_entity_ids: list[str] = Field(default_factory=list)


class PlaceState(_StrictModel):
    """One spatial locus in an acyclic topological containment hierarchy."""

    place_id: str = Field(pattern=_ID_PATTERN)
    place_kind: str = Field(pattern=_ID_PATTERN)
    description: str = Field(min_length=1)
    parent_place_id: str | None = Field(default=None, pattern=_ID_PATTERN)


class PlacementState(_StrictModel):
    """The current immediate place of one concrete entity."""

    entity_id: str = Field(pattern=_ID_PATTERN)
    place_id: str = Field(pattern=_ID_PATTERN)


class SpatialLinkState(_StrictModel):
    """Topological adjacency whose existence does not imply traversability."""

    spatial_link_id: str = Field(pattern=_ID_PATTERN)
    endpoint_a_place_id: str = Field(pattern=_ID_PATTERN)
    endpoint_b_place_id: str = Field(pattern=_ID_PATTERN)
    link_kind: str = Field(pattern=_ID_PATTERN)
    substrate_entity_ids: list[str] = Field(default_factory=list)
    description: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_link(self) -> "SpatialLinkState":
        """Require two distinct endpoints and nonduplicated substrates."""
        if self.endpoint_a_place_id == self.endpoint_b_place_id:
            raise ValueError("spatial link endpoints must be distinct")
        _require_unique(self.substrate_entity_ids, "spatial link substrates")
        return self


class PortState(_StrictModel):
    """Typed input or output interface owned by an entity or mechanism."""

    port_id: str = Field(pattern=_ID_PATTERN)
    owner_ref: str = Field(pattern=_ID_PATTERN)
    direction: Literal["input", "output"]
    effect_type: str = Field(pattern=_ID_PATTERN)
    description: str = Field(min_length=1)
    container_id: str | None = Field(default=None, pattern=_ID_PATTERN)


class ConnectionState(_StrictModel):
    """One explicit directed route between compatible ports."""

    connection_id: str = Field(pattern=_ID_PATTERN)
    source_port_id: str = Field(pattern=_ID_PATTERN)
    target_port_id: str = Field(pattern=_ID_PATTERN)
    delay: int = Field(default=0, ge=0)
    enabled: bool = True
    description: str = Field(min_length=1)


class FidelityNote(_StrictModel):
    """Declared abstraction, assumptions, omissions, and validation basis."""

    abstraction: str = Field(min_length=1)
    assumptions: list[str] = Field(min_length=1)
    known_omissions: list[str] = Field(min_length=1)
    validation_basis: list[str] = Field(min_length=1)


class MechanismSpec(_StrictModel):
    """Exact transition authority and fidelity envelope."""

    mechanism_id: str = Field(pattern=_ID_PATTERN)
    mechanism_kind: str = Field(pattern=_ID_PATTERN)
    implementation_id: str = Field(pattern=_ID_PATTERN)
    description: str = Field(min_length=1)
    mode: Literal["exact"] = "exact"
    input_port_ids: list[str] = Field(min_length=1)
    output_port_ids: list[str] = Field(default_factory=list)
    read_fact_ids: list[str] = Field(default_factory=list)
    read_representation_ids: list[str] = Field(default_factory=list)
    read_placement_entity_ids: list[str] = Field(default_factory=list)
    read_spatial_link_ids: list[str] = Field(default_factory=list)
    write_fact_ids: list[str] = Field(default_factory=list)
    write_placement_entity_ids: list[str] = Field(default_factory=list)
    write_carrier_ids: list[str] = Field(default_factory=list)
    observation_target_ids: list[str] = Field(default_factory=list)
    substrate_refs: list[str] = Field(min_length=1)
    invariant_ids: list[str] = Field(min_length=1)
    fidelity: FidelityNote

    @model_validator(mode="after")
    def validate_contract(self) -> "MechanismSpec":
        """Reject duplicate authority surfaces and malformed fact paths."""
        for label, values in (
            ("input_port_ids", self.input_port_ids),
            ("output_port_ids", self.output_port_ids),
            ("read_fact_ids", self.read_fact_ids),
            ("read_representation_ids", self.read_representation_ids),
            ("read_placement_entity_ids", self.read_placement_entity_ids),
            ("read_spatial_link_ids", self.read_spatial_link_ids),
            ("write_fact_ids", self.write_fact_ids),
            ("write_placement_entity_ids", self.write_placement_entity_ids),
            ("write_carrier_ids", self.write_carrier_ids),
            ("observation_target_ids", self.observation_target_ids),
            ("substrate_refs", self.substrate_refs),
            ("invariant_ids", self.invariant_ids),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"{self.mechanism_id}: duplicate {label}")
        for fact_id in [*self.read_fact_ids, *self.write_fact_ids]:
            _split_fact_id(fact_id)
        if not set(self.write_placement_entity_ids).issubset(
            self.read_placement_entity_ids
        ):
            raise ValueError(
                f"{self.mechanism_id}: placement writes require declared "
                "placement reads"
            )
        return self


class CarrierState(_StrictModel):
    """Concrete state surface capable of retaining an encoded pattern."""

    carrier_id: str = Field(pattern=_ID_PATTERN)
    owner_ref: str = Field(pattern=_ID_PATTERN)
    medium: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    revision: int = Field(default=0, ge=0)
    visibility: Visibility = "public"


class RepresentationToken(_StrictModel):
    """One encoded pattern at a particular carrier and revision."""

    representation_id: str = Field(pattern=_ID_PATTERN)
    carrier_id: str = Field(pattern=_ID_PATTERN)
    carrier_revision: int = Field(ge=0)
    encoding: str = Field(min_length=1)
    content: str = Field(min_length=1)
    content_hash: str = Field(pattern=_DIGEST_PATTERN)
    actual_source_ref: str = Field(pattern=_ID_PATTERN)
    parent_representation_ids: list[str] = Field(default_factory=list)
    visibility: Visibility = "public"

    @model_validator(mode="after")
    def validate_content_hash(self) -> "RepresentationToken":
        """Bind the identity record to the exact encoded content."""
        expected = representation_digest(self.content)
        if self.content_hash != expected:
            raise ValueError("representation content_hash does not match content")
        if len(self.parent_representation_ids) != len(
            set(self.parent_representation_ids)
        ):
            raise ValueError("representation parents must be unique")
        if self.representation_id in self.parent_representation_ids:
            raise ValueError("representation cannot derive from itself")
        return self


class ObservationRecord(_StrictModel):
    """One delivered active-system surface, separate from hidden provenance."""

    observation_id: str = Field(pattern=_ID_PATTERN)
    target_entity_id: str = Field(pattern=_ID_PATTERN)
    via_port_id: str = Field(pattern=_ID_PATTERN)
    apparent_content: str = Field(min_length=1)
    apparent_source_ref: str | None = Field(default=None, pattern=_ID_PATTERN)
    representation_id: str | None = Field(default=None, pattern=_ID_PATTERN)
    logical_time: int = Field(ge=0)
    causal_parent_event_ids: list[str] = Field(min_length=1)


class CausalState(_StrictModel):
    """Complete canonical world state at one committed revision."""

    revision: int = Field(default=0, ge=0)
    logical_time: int = Field(default=0, ge=0)
    entities: dict[str, EntityState]
    containers: dict[str, ContainerState] = Field(default_factory=dict)
    places: dict[str, PlaceState] = Field(default_factory=dict)
    placements: dict[str, PlacementState] = Field(default_factory=dict)
    spatial_links: dict[str, SpatialLinkState] = Field(default_factory=dict)
    ports: dict[str, PortState]
    connections: dict[str, ConnectionState] = Field(default_factory=dict)
    mechanisms: dict[str, MechanismSpec]
    carriers: dict[str, CarrierState] = Field(default_factory=dict)
    representations: dict[str, RepresentationToken] = Field(default_factory=dict)
    observations: dict[str, ObservationRecord] = Field(default_factory=dict)
    inboxes: dict[str, list[str]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_references(self) -> "CausalState":
        """Reject duplicate truths and every dangling runtime reference."""
        _keys_match(self.entities, "entity_id", "entities")
        _keys_match(self.containers, "container_id", "containers")
        _keys_match(self.places, "place_id", "places")
        _keys_match(self.placements, "entity_id", "placements")
        _keys_match(
            self.spatial_links,
            "spatial_link_id",
            "spatial_links",
        )
        _keys_match(self.ports, "port_id", "ports")
        _keys_match(self.connections, "connection_id", "connections")
        _keys_match(self.mechanisms, "mechanism_id", "mechanisms")
        _keys_match(self.carriers, "carrier_id", "carriers")
        _keys_match(
            self.representations, "representation_id", "representations"
        )
        _keys_match(self.observations, "observation_id", "observations")

        _require_disjoint_ids(
            {
                "entities": set(self.entities),
                "containers": set(self.containers),
                "places": set(self.places),
                "spatial_links": set(self.spatial_links),
                "ports": set(self.ports),
                "connections": set(self.connections),
                "mechanisms": set(self.mechanisms),
                "carriers": set(self.carriers),
                "representations": set(self.representations),
            }
        )

        entity_ids = set(self.entities)
        mechanism_ids = set(self.mechanisms)
        owner_refs = entity_ids | mechanism_ids
        container_ids = set(self.containers)
        place_ids = set(self.places)
        spatial_link_ids = set(self.spatial_links)
        port_ids = set(self.ports)

        _validate_place_tree(self.places)
        for placement in self.placements.values():
            if placement.entity_id not in entity_ids:
                raise ValueError(
                    f"placement has unknown entity {placement.entity_id!r}"
                )
            if placement.place_id not in place_ids:
                raise ValueError(
                    f"placement for {placement.entity_id!r} has unknown place "
                    f"{placement.place_id!r}"
                )
        for spatial_link in self.spatial_links.values():
            unknown_endpoints = {
                spatial_link.endpoint_a_place_id,
                spatial_link.endpoint_b_place_id,
            } - place_ids
            if unknown_endpoints:
                raise ValueError(
                    f"spatial link {spatial_link.spatial_link_id!r} has unknown "
                    f"endpoints {sorted(unknown_endpoints)!r}"
                )
            unknown_substrates = (
                set(spatial_link.substrate_entity_ids) - entity_ids
            )
            if unknown_substrates:
                raise ValueError(
                    f"spatial link {spatial_link.spatial_link_id!r} has unknown "
                    f"substrates {sorted(unknown_substrates)!r}"
                )

        for container in self.containers.values():
            _require_unique(container.member_entity_ids, "container members")
            unknown = set(container.member_entity_ids) - entity_ids
            if unknown:
                raise ValueError(
                    f"container {container.container_id!r} has unknown members "
                    f"{sorted(unknown)!r}"
                )

        for port in self.ports.values():
            if port.owner_ref not in owner_refs:
                raise ValueError(
                    f"port {port.port_id!r} has unknown owner {port.owner_ref!r}"
                )
            if port.container_id is not None and port.container_id not in container_ids:
                raise ValueError(
                    f"port {port.port_id!r} has unknown container "
                    f"{port.container_id!r}"
                )

        input_bindings: dict[str, str] = {}
        known_substrates = entity_ids | set(self.carriers)
        for mechanism in self.mechanisms.values():
            unknown_ports = (
                set(mechanism.input_port_ids)
                | set(mechanism.output_port_ids)
            ) - port_ids
            if unknown_ports:
                raise ValueError(
                    f"mechanism {mechanism.mechanism_id!r} has unknown ports "
                    f"{sorted(unknown_ports)!r}"
                )
            for port_id in mechanism.input_port_ids:
                port = self.ports[port_id]
                if port.direction != "input":
                    raise ValueError(f"mechanism input {port_id!r} is not input")
                if port_id in input_bindings:
                    raise ValueError(f"input port {port_id!r} has multiple bindings")
                input_bindings[port_id] = mechanism.mechanism_id
            for port_id in mechanism.output_port_ids:
                port = self.ports[port_id]
                if port.direction != "output":
                    raise ValueError(f"mechanism output {port_id!r} is not output")
                if port.owner_ref != mechanism.mechanism_id:
                    raise ValueError(
                        f"mechanism output {port_id!r} must be owned by "
                        f"{mechanism.mechanism_id!r}"
                    )
            for fact_id in [*mechanism.read_fact_ids, *mechanism.write_fact_ids]:
                self.fact(fact_id)
            unknown_write_carriers = set(mechanism.write_carrier_ids) - set(
                self.carriers
            )
            if unknown_write_carriers:
                raise ValueError(
                    f"mechanism {mechanism.mechanism_id!r} has unknown writable "
                    f"carriers {sorted(unknown_write_carriers)!r}"
                )
            unknown_read_representations = (
                set(mechanism.read_representation_ids)
                - set(self.representations)
            )
            if unknown_read_representations:
                raise ValueError(
                    f"mechanism {mechanism.mechanism_id!r} has unknown readable "
                    "representations "
                    f"{sorted(unknown_read_representations)!r}"
                )
            unknown_read_placements = (
                set(mechanism.read_placement_entity_ids) - set(self.placements)
            )
            if unknown_read_placements:
                raise ValueError(
                    f"mechanism {mechanism.mechanism_id!r} has unknown readable "
                    f"placements {sorted(unknown_read_placements)!r}"
                )
            unknown_read_spatial_links = (
                set(mechanism.read_spatial_link_ids) - spatial_link_ids
            )
            if unknown_read_spatial_links:
                raise ValueError(
                    f"mechanism {mechanism.mechanism_id!r} has unknown readable "
                    f"spatial links {sorted(unknown_read_spatial_links)!r}"
                )
            unknown_write_placements = (
                set(mechanism.write_placement_entity_ids) - set(self.placements)
            )
            if unknown_write_placements:
                raise ValueError(
                    f"mechanism {mechanism.mechanism_id!r} has unknown writable "
                    f"placements {sorted(unknown_write_placements)!r}"
                )
            unknown_targets = set(mechanism.observation_target_ids) - entity_ids
            if unknown_targets:
                raise ValueError(
                    f"mechanism {mechanism.mechanism_id!r} has unknown observation "
                    f"targets {sorted(unknown_targets)!r}"
                )
            unknown_substrates = set(mechanism.substrate_refs) - known_substrates
            if unknown_substrates:
                raise ValueError(
                    f"mechanism {mechanism.mechanism_id!r} has unknown substrates "
                    f"{sorted(unknown_substrates)!r}"
                )
        unbound_inputs = {
            port.port_id
            for port in self.ports.values()
            if port.direction == "input" and port.port_id not in input_bindings
        }
        if unbound_inputs:
            raise ValueError(
                f"input ports have no mechanism binding: {sorted(unbound_inputs)!r}"
            )

        for connection in self.connections.values():
            if (
                connection.source_port_id not in port_ids
                or connection.target_port_id not in port_ids
            ):
                raise ValueError(
                    f"connection {connection.connection_id!r} has unknown port"
                )
            source = self.ports[connection.source_port_id]
            target = self.ports[connection.target_port_id]
            if source.direction != "output" or target.direction != "input":
                raise ValueError(
                    f"connection {connection.connection_id!r} must link output to input"
                )
            if source.effect_type != target.effect_type:
                raise ValueError(
                    f"connection {connection.connection_id!r} has incompatible types"
                )

        for carrier in self.carriers.values():
            if carrier.owner_ref not in owner_refs:
                raise ValueError(
                    f"carrier {carrier.carrier_id!r} has unknown owner "
                    f"{carrier.owner_ref!r}"
                )
        for representation in self.representations.values():
            resolved_carrier = self.carriers.get(representation.carrier_id)
            if resolved_carrier is None:
                raise ValueError(
                    f"representation {representation.representation_id!r} has "
                    "unknown carrier"
                )
            if representation.carrier_revision > resolved_carrier.revision:
                raise ValueError(
                    f"representation {representation.representation_id!r} has "
                    "a future carrier revision"
                )
            if representation.actual_source_ref not in owner_refs:
                raise ValueError(
                    f"representation {representation.representation_id!r} has "
                    "unknown actual source"
                )
            unknown_parents = set(representation.parent_representation_ids) - set(
                self.representations
            )
            if unknown_parents:
                raise ValueError(
                    f"representation {representation.representation_id!r} has "
                    f"unknown parents {sorted(unknown_parents)!r}"
                )
        _validate_representation_lineage(self.representations)
        carrier_revisions = [
            (item.carrier_id, item.carrier_revision)
            for item in self.representations.values()
        ]
        if len(carrier_revisions) != len(set(carrier_revisions)):
            raise ValueError("one carrier revision may hold only one representation")

        known_observations = set(self.observations)
        for observation in self.observations.values():
            if observation.target_entity_id not in entity_ids:
                raise ValueError(
                    f"observation {observation.observation_id!r} has unknown target"
                )
            observation_port = self.ports.get(observation.via_port_id)
            if observation_port is None or observation_port.direction != "input":
                raise ValueError(
                    f"observation {observation.observation_id!r} has invalid port"
                )
            if (
                observation.apparent_source_ref is not None
                and observation.apparent_source_ref not in owner_refs
            ):
                raise ValueError(
                    f"observation {observation.observation_id!r} has unknown "
                    "apparent source"
                )
            if (
                observation.representation_id is not None
                and observation.representation_id not in self.representations
            ):
                raise ValueError(
                    f"observation {observation.observation_id!r} has unknown "
                    "representation"
                )
        for entity_id, observation_ids in self.inboxes.items():
            if entity_id not in entity_ids:
                raise ValueError(f"inbox has unknown entity {entity_id!r}")
            _require_unique(observation_ids, f"inbox {entity_id!r}")
            unknown = set(observation_ids) - known_observations
            if unknown:
                raise ValueError(
                    f"inbox {entity_id!r} has unknown observations "
                    f"{sorted(unknown)!r}"
                )
        inbox_list = [
            observation_id
            for observation_ids in self.inboxes.values()
            for observation_id in observation_ids
        ]
        if set(inbox_list) != known_observations or len(inbox_list) != len(
            known_observations
        ):
            raise ValueError("every observation must appear in exactly one inbox")
        return self

    def fact(self, fact_id: str) -> FactState:
        """Return one addressable fact or fail with its exact path."""
        entity_id, attribute = _split_fact_id(fact_id)
        entity = self.entities.get(entity_id)
        if entity is None or attribute not in entity.attributes:
            raise ValueError(f"unknown fact id {fact_id!r}")
        return entity.attributes[attribute]

    def mechanism_for_input_port(self, port_id: str) -> MechanismSpec:
        """Return the unique mechanism bound to an input port."""
        matches = [
            mechanism
            for mechanism in self.mechanisms.values()
            if port_id in mechanism.input_port_ids
        ]
        if len(matches) != 1:
            raise ValueError(f"input port {port_id!r} has {len(matches)} bindings")
        return matches[0]


class AnalyticalBoundary(_StrictModel):
    """Versioned analyst grouping that can never execute."""

    boundary_id: str = Field(pattern=_ID_PATTERN)
    label: str = Field(min_length=1)
    description: str = Field(min_length=1)
    member_refs: list[str] = Field(min_length=1)
    executor: Literal[False] = False

    @model_validator(mode="after")
    def validate_members(self) -> "AnalyticalBoundary":
        """Reject duplicate view members instead of failing during projection."""
        _require_unique(self.member_refs, "analytical boundary members")
        return self


class CausalScenario(_StrictModel):
    """Versioned authored initial world without embedded action scripts."""

    runtime_contract: Literal["causal-core.v2"] = "causal-core.v2"
    schema_version: Literal[2] = 2
    scenario_id: str = Field(pattern=_ID_PATTERN)
    description: str = Field(min_length=1)
    initial_state: CausalState
    analytical_boundaries: list[AnalyticalBoundary] = Field(default_factory=list)
    fidelity_questions: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_scenario(self) -> "CausalScenario":
        """Bind boundaries to grounded referents and require turn-zero state."""
        if self.initial_state.revision != 0 or self.initial_state.logical_time != 0:
            raise ValueError("scenario initial state must be revision/time zero")
        if self.initial_state.observations or self.initial_state.inboxes:
            raise ValueError("scenario initial state cannot contain delivered observations")
        boundary_ids = [item.boundary_id for item in self.analytical_boundaries]
        _require_unique(boundary_ids, "boundary ids")
        node_refs = (
            set(self.initial_state.entities)
            | set(self.initial_state.containers)
            | set(self.initial_state.places)
            | set(self.initial_state.ports)
            | set(self.initial_state.mechanisms)
            | set(self.initial_state.carriers)
            | set(self.initial_state.representations)
        )
        runtime_refs = (
            node_refs
            | set(self.initial_state.connections)
            | set(self.initial_state.spatial_links)
        )
        collisions = set(boundary_ids) & runtime_refs
        if collisions:
            raise ValueError(
                f"analytical boundaries collide with runtime refs {sorted(collisions)!r}"
            )
        for boundary in self.analytical_boundaries:
            unknown = set(boundary.member_refs) - node_refs
            if unknown:
                raise ValueError(
                    f"boundary {boundary.boundary_id!r} has unknown or non-node members "
                    f"{sorted(unknown)!r}"
                )
        return self


class ActionAttempt(_StrictModel):
    """Externally supplied attempt entering one owned output interface."""

    action_id: str = Field(pattern=_ID_PATTERN)
    actor_entity_id: str = Field(pattern=_ID_PATTERN)
    output_port_id: str = Field(pattern=_ID_PATTERN)
    representation_id: str | None = Field(default=None, pattern=_ID_PATTERN)
    payload: dict[str, JsonValue] = Field(default_factory=dict)
    logical_time: int = Field(default=0, ge=0)
    public_summary: str = Field(min_length=1)


class EffectEnvelope(_StrictModel):
    """Typed effect queued for structural routing."""

    effect_id: str = Field(pattern=_ID_PATTERN)
    effect_type: str = Field(pattern=_ID_PATTERN)
    source_port_id: str = Field(pattern=_ID_PATTERN)
    representation_id: str | None = Field(default=None, pattern=_ID_PATTERN)
    payload: dict[str, JsonValue] = Field(default_factory=dict)
    logical_time: int = Field(ge=0)
    zero_time_depth: int = Field(default=0, ge=0)
    variance_source: Literal["external_action", "exact"]
    causal_parent_event_ids: list[str] = Field(min_length=1)


class EffectDraft(_StrictModel):
    """Mechanism-proposed downstream effect validated before emission."""

    output_port_id: str = Field(pattern=_ID_PATTERN)
    effect_type: str = Field(pattern=_ID_PATTERN)
    representation_id: str | None = Field(default=None, pattern=_ID_PATTERN)
    payload: dict[str, JsonValue] = Field(default_factory=dict)
    delay: int = Field(default=0, ge=0)


class FactUpdate(_StrictModel):
    """Mechanism-proposed update inside its declared write surface."""

    fact_id: str = Field(pattern=_FACT_PATTERN)
    value: JsonValue


class PlacementDraft(_StrictModel):
    """Mechanism-proposed movement across one declared topological link."""

    entity_id: str = Field(pattern=_ID_PATTERN)
    destination_place_id: str = Field(pattern=_ID_PATTERN)
    via_spatial_link_id: str = Field(pattern=_ID_PATTERN)


class ObservationDraft(_StrictModel):
    """Mechanism-proposed agent-visible delivery."""

    target_entity_id: str = Field(pattern=_ID_PATTERN)
    via_port_id: str = Field(pattern=_ID_PATTERN)
    apparent_content: str = Field(min_length=1)
    apparent_source_ref: str | None = Field(default=None, pattern=_ID_PATTERN)
    representation_id: str | None = Field(default=None, pattern=_ID_PATTERN)


class RepresentationDraft(_StrictModel):
    """Proposed encoded copy on one predeclared writable carrier."""

    representation_id: str = Field(pattern=_ID_PATTERN)
    carrier_id: str = Field(pattern=_ID_PATTERN)
    encoding: str = Field(min_length=1)
    content: str = Field(min_length=1)
    actual_source_ref: str = Field(pattern=_ID_PATTERN)
    parent_representation_ids: list[str] = Field(default_factory=list)
    visibility: Visibility = "public"

    @model_validator(mode="after")
    def validate_parents(self) -> "RepresentationDraft":
        """Keep proposed lineage unique and non-self-referential."""
        _require_unique(
            self.parent_representation_ids,
            "representation draft parents",
        )
        if self.representation_id in self.parent_representation_ids:
            raise ValueError("representation draft cannot derive from itself")
        return self


class InvariantResult(_StrictModel):
    """One engine-recorded result from an independently registered checker."""

    invariant_id: str = Field(pattern=_ID_PATTERN)
    passed: bool
    detail: str = Field(min_length=1)


class MechanismOutcome(_StrictModel):
    """Trusted exact-handler proposal, still subject to engine validation."""

    outcome_code: str = Field(pattern=_ID_PATTERN)
    updates: list[FactUpdate] = Field(default_factory=list)
    placement_updates: list[PlacementDraft] = Field(default_factory=list)
    representations: list[RepresentationDraft] = Field(default_factory=list)
    effects: list[EffectDraft] = Field(default_factory=list)
    observations: list[ObservationDraft] = Field(default_factory=list)


class FactChange(_StrictModel):
    """Replayable before/after value for one committed fact."""

    fact_id: str = Field(pattern=_FACT_PATTERN)
    visibility: Visibility
    before: JsonValue
    after: JsonValue

    @model_validator(mode="after")
    def validate_actual_change(self) -> "FactChange":
        """Keep no-op assignments out of the causal change record."""
        if _canonical_json(self.before) == _canonical_json(self.after):
            raise ValueError("fact change must alter the canonical JSON value")
        return self


class PlacementChange(_StrictModel):
    """Replayable before/after location plus the concrete mediating link."""

    entity_id: str = Field(pattern=_ID_PATTERN)
    before_place_id: str = Field(pattern=_ID_PATTERN)
    after_place_id: str = Field(pattern=_ID_PATTERN)
    via_spatial_link_id: str = Field(pattern=_ID_PATTERN)

    @model_validator(mode="after")
    def validate_actual_change(self) -> "PlacementChange":
        """Keep no-op movements out of committed causal evidence."""
        if self.before_place_id == self.after_place_id:
            raise ValueError("placement change must alter the immediate place")
        return self


class CarrierRevisionChange(_StrictModel):
    """Replayable revision advance for one concrete carrier write."""

    carrier_id: str = Field(pattern=_ID_PATTERN)
    before_revision: int = Field(ge=0)
    after_revision: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_revision(self) -> "CarrierRevisionChange":
        """Each committed carrier write advances exactly one revision."""
        if self.after_revision != self.before_revision + 1:
            raise ValueError("carrier write must advance exactly one revision")
        return self


class StatePatch(_StrictModel):
    """Complete replayable mutation committed by one mechanism execution."""

    before_revision: int = Field(ge=0)
    after_revision: int = Field(ge=1)
    before_logical_time: int = Field(ge=0)
    after_logical_time: int = Field(ge=0)
    before_digest: str = Field(pattern=_DIGEST_PATTERN)
    after_digest: str = Field(pattern=_DIGEST_PATTERN)
    fact_changes: list[FactChange] = Field(default_factory=list)
    placement_changes: list[PlacementChange] = Field(default_factory=list)
    carrier_changes: list[CarrierRevisionChange] = Field(default_factory=list)
    representations_added: list[RepresentationToken] = Field(default_factory=list)
    observations_added: list[ObservationRecord] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_transition(self) -> "StatePatch":
        """Require one monotonic revision and unique patch targets."""
        if self.after_revision != self.before_revision + 1:
            raise ValueError("state patch must advance exactly one revision")
        if self.after_logical_time < self.before_logical_time:
            raise ValueError("state patch logical time may not regress")
        fact_ids = [item.fact_id for item in self.fact_changes]
        placement_entity_ids = [
            item.entity_id for item in self.placement_changes
        ]
        carrier_ids = [item.carrier_id for item in self.carrier_changes]
        representation_ids = [
            item.representation_id for item in self.representations_added
        ]
        observation_ids = [item.observation_id for item in self.observations_added]
        _require_unique(fact_ids, "patch fact ids")
        _require_unique(placement_entity_ids, "patch placement entity ids")
        _require_unique(carrier_ids, "patch carrier ids")
        _require_unique(representation_ids, "patch representation ids")
        _require_unique(observation_ids, "patch observation ids")
        if set(carrier_ids) != {
            item.carrier_id for item in self.representations_added
        }:
            raise ValueError(
                "each carrier revision change must add exactly one representation"
            )
        carrier_after = {
            item.carrier_id: item.after_revision for item in self.carrier_changes
        }
        if any(
            item.carrier_revision != carrier_after[item.carrier_id]
            for item in self.representations_added
        ):
            raise ValueError("added representation has the wrong carrier revision")
        if self.before_digest == self.after_digest:
            raise ValueError("state patch must change the versioned state digest")
        return self


class CausalEvent(_StrictModel):
    """One versioned, human-readable, causally linked execution occurrence."""

    runtime_contract: Literal["causal-core.v2"] = "causal-core.v2"
    schema_version: Literal[2] = 2
    run_id: str = Field(pattern=_ID_PATTERN)
    event_id: str = Field(pattern=r"^event_[0-9]{6}$")
    sequence: int = Field(ge=0)
    event_kind: EventKind
    logical_time: int = Field(ge=0)
    state_revision: int = Field(ge=0)
    causal_parent_event_ids: list[str] = Field(default_factory=list)
    summary: str = Field(min_length=1)
    variance_source: VarianceSource = "none"
    action_id: str | None = Field(default=None, pattern=_ID_PATTERN)
    actor_entity_id: str | None = Field(default=None, pattern=_ID_PATTERN)
    mechanism_id: str | None = Field(default=None, pattern=_ID_PATTERN)
    effect_id: str | None = Field(default=None, pattern=_ID_PATTERN)
    source_port_id: str | None = Field(default=None, pattern=_ID_PATTERN)
    target_port_id: str | None = Field(default=None, pattern=_ID_PATTERN)
    route_kind: RouteKind | None = None
    connection_id: str | None = Field(default=None, pattern=_ID_PATTERN)
    container_id: str | None = Field(default=None, pattern=_ID_PATTERN)
    representation_id: str | None = Field(default=None, pattern=_ID_PATTERN)
    observation_id: str | None = Field(default=None, pattern=_ID_PATTERN)
    read_fact_ids: list[str] = Field(default_factory=list)
    read_representation_ids: list[str] = Field(default_factory=list)
    read_placement_entity_ids: list[str] = Field(default_factory=list)
    read_spatial_link_ids: list[str] = Field(default_factory=list)
    invariants: list[InvariantResult] = Field(default_factory=list)
    patch: StatePatch | None = None
    details: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_event_shape(self) -> "CausalEvent":
        """Require identifiers and evidence implied by each event kind."""
        expected_id = f"event_{self.sequence:06d}"
        if self.event_id != expected_id:
            raise ValueError("event id must match its canonical sequence")
        if self.event_kind == "run_started":
            if self.sequence != 0 or self.causal_parent_event_ids:
                raise ValueError("run_started must be the only root event")
        elif not self.causal_parent_event_ids:
            raise ValueError("every non-root event requires a causal parent")
        if self.event_kind == "action_attempted":
            _require_fields(self, "action_id", "actor_entity_id", "source_port_id")
        elif self.event_kind == "effect_emitted":
            _require_fields(self, "effect_id", "source_port_id")
        elif self.event_kind == "effect_routed":
            _require_fields(self, "effect_id", "source_port_id", "target_port_id")
            if self.route_kind == "connection":
                _require_fields(self, "connection_id")
                if self.container_id is not None:
                    raise ValueError("connection route cannot name a container")
            elif self.route_kind == "container":
                _require_fields(self, "container_id")
                if self.connection_id is not None:
                    raise ValueError("container route cannot name a connection")
            else:
                raise ValueError("effect_routed requires one concrete route kind")
        elif self.event_kind == "effect_dissipated":
            _require_fields(self, "effect_id", "source_port_id")
        elif self.event_kind == "mechanism_executed":
            _require_fields(self, "mechanism_id", "effect_id", "target_port_id")
            if not self.invariants:
                raise ValueError("mechanism execution requires invariant evidence")
        elif self.event_kind == "state_committed":
            _require_fields(
                self,
                "mechanism_id",
                "effect_id",
                "target_port_id",
                "patch",
            )
            if self.patch is None or self.state_revision != self.patch.after_revision:
                raise ValueError("commit event revision must match its patch")
        elif self.event_kind == "observation_delivered":
            _require_fields(self, "mechanism_id", "observation_id", "target_port_id")
        if self.patch is not None and self.event_kind != "state_committed":
            raise ValueError("only state_committed events may contain a patch")
        if self.event_kind != "effect_routed" and any(
            value is not None
            for value in (self.route_kind, self.connection_id, self.container_id)
        ):
            raise ValueError("only effect_routed events may identify a route")
        return self


class CausalMetrics(_StrictModel):
    """Observable queue, routing, and exact-execution accounting."""

    effects_emitted: int = Field(default=0, ge=0)
    effects_processed: int = Field(default=0, ge=0)
    candidates_considered: int = Field(default=0, ge=0)
    routed_deliveries: int = Field(default=0, ge=0)
    dissipated_effects: int = Field(default=0, ge=0)
    mechanism_executions: int = Field(default=0, ge=0)
    state_commits: int = Field(default=0, ge=0)
    observations_delivered: int = Field(default=0, ge=0)
    maximum_fanout: int = Field(default=0, ge=0)
    maximum_zero_time_depth: int = Field(default=0, ge=0)
    queue_high_water: int = Field(default=0, ge=0)
    random_samples: Literal[0] = 0
    model_calls: Literal[0] = 0


class CausalStep(_StrictModel):
    """Committed evidence returned from one atomic action advancement."""

    action_id: str = Field(pattern=_ID_PATTERN)
    events: list[CausalEvent] = Field(min_length=1)
    observations: list[ObservationRecord] = Field(default_factory=list)
    state: CausalState


class CausalCheckpoint(_StrictModel):
    """Complete quiescent continuation record for one nonterminal session."""

    runtime_contract: Literal["causal-core.v2"] = "causal-core.v2"
    schema_version: Literal[2] = 2
    scenario_id: str = Field(pattern=_ID_PATTERN)
    scenario_fingerprint: str = Field(pattern=_DIGEST_PATTERN)
    scenario_execution_fingerprint: str = Field(pattern=_DIGEST_PATTERN)
    run_id: str = Field(pattern=_ID_PATTERN)
    max_effects: int = Field(ge=1)
    max_zero_time_depth: int = Field(ge=0)
    state: CausalState
    state_digest: str = Field(pattern=_DIGEST_PATTERN)
    events: list[CausalEvent] = Field(min_length=1)
    event_tail_digest: str = Field(pattern=_DIGEST_PATTERN)
    metrics: CausalMetrics
    accepted_action_ids: list[str] = Field(default_factory=list)
    event_sequence: int = Field(ge=1)
    effect_sequence: int = Field(ge=0)
    observation_sequence: int = Field(ge=0)
    queue_sequence: int = Field(ge=0)
    record_digest: str = Field(pattern=_DIGEST_PATTERN)

    @model_validator(mode="after")
    def validate_checkpoint(self) -> "CausalCheckpoint":
        """Reject terminal, corrupt, or counter-regressed continuation state."""
        _validate_trace(self.events, terminal=False, run_id=self.run_id)
        _validate_run_binding(
            self.events,
            scenario_id=self.scenario_id,
            scenario_execution_fingerprint=self.scenario_execution_fingerprint,
            max_effects=self.max_effects,
            max_zero_time_depth=self.max_zero_time_depth,
        )
        if self.event_tail_digest != trace_digest(self.events):
            raise ValueError("checkpoint event-tail digest mismatch")
        if self.state_digest != state_digest(self.state):
            raise ValueError("checkpoint state digest mismatch")
        _require_unique(self.accepted_action_ids, "accepted action ids")
        _validate_actions(self.accepted_action_ids, self.events)
        _validate_event_references(self.state, self.events)
        _validate_state_evidence(self.state, self.events)
        _validate_metrics(self.metrics, self.events)
        if self.event_sequence != len(self.events):
            raise ValueError("event sequence must equal the next trace position")
        if self.effect_sequence != self.metrics.effects_emitted:
            raise ValueError("effect sequence must equal emitted effects")
        if self.observation_sequence != len(self.state.observations):
            raise ValueError("observation sequence must equal delivered state")
        expected_queue_sequence = (
            self.metrics.effects_emitted + self.metrics.routed_deliveries
        )
        if self.queue_sequence != expected_queue_sequence:
            raise ValueError("queue sequence disagrees with scheduled work")
        if self.metrics.state_commits != self.state.revision:
            raise ValueError("state revision must equal committed patch count")
        if self.metrics.effects_emitted > self.max_effects:
            raise ValueError("checkpoint exceeds its effect limit")
        if self.metrics.maximum_zero_time_depth > self.max_zero_time_depth:
            raise ValueError("checkpoint exceeds its zero-time-depth limit")
        if self.events[-1].state_revision != self.state.revision:
            raise ValueError("checkpoint event tail has wrong state revision")
        if self.record_digest != canonical_record_digest(
            self.model_dump(mode="json", exclude={"record_digest"})
        ):
            raise ValueError("checkpoint record digest mismatch")
        return self


class CausalRunResult(_StrictModel):
    """One completed exact trajectory and its self-validating canonical state."""

    runtime_contract: Literal["causal-core.v2"] = "causal-core.v2"
    schema_version: Literal[2] = 2
    run_id: str = Field(pattern=_ID_PATTERN)
    scenario_id: str = Field(pattern=_ID_PATTERN)
    scenario_fingerprint: str = Field(pattern=_DIGEST_PATTERN)
    scenario_execution_fingerprint: str = Field(pattern=_DIGEST_PATTERN)
    max_effects: int = Field(ge=1)
    max_zero_time_depth: int = Field(ge=0)
    status: Literal["completed"] = "completed"
    initial_state_digest: str = Field(pattern=_DIGEST_PATTERN)
    final_state_digest: str = Field(pattern=_DIGEST_PATTERN)
    event_tail_digest: str = Field(pattern=_DIGEST_PATTERN)
    final_state: CausalState
    events: list[CausalEvent] = Field(min_length=2)
    metrics: CausalMetrics
    accepted_action_ids: list[str] = Field(default_factory=list)
    outcome_summary: str = Field(min_length=1)
    record_digest: str = Field(pattern=_DIGEST_PATTERN)

    @model_validator(mode="after")
    def validate_result(self) -> "CausalRunResult":
        """Keep terminal trace, digests, state, and metrics mutually coherent."""
        _validate_trace(self.events, terminal=True, run_id=self.run_id)
        _validate_run_binding(
            self.events,
            scenario_id=self.scenario_id,
            scenario_execution_fingerprint=self.scenario_execution_fingerprint,
            max_effects=self.max_effects,
            max_zero_time_depth=self.max_zero_time_depth,
        )
        if self.event_tail_digest != trace_digest(self.events):
            raise ValueError("run event-tail digest mismatch")
        if self.final_state_digest != state_digest(self.final_state):
            raise ValueError("run final-state digest mismatch")
        if self.events[-1].state_revision != self.final_state.revision:
            raise ValueError("terminal event has wrong state revision")
        if self.metrics.state_commits != self.final_state.revision:
            raise ValueError("state revision must equal committed patch count")
        if self.metrics.observations_delivered != len(self.final_state.observations):
            raise ValueError("observation metrics disagree with final state")
        _require_unique(self.accepted_action_ids, "accepted action ids")
        _validate_actions(self.accepted_action_ids, self.events)
        _validate_event_references(self.final_state, self.events)
        _validate_state_evidence(self.final_state, self.events)
        _validate_metrics(self.metrics, self.events)
        if self.metrics.effects_emitted > self.max_effects:
            raise ValueError("run exceeds its effect limit")
        if self.metrics.maximum_zero_time_depth > self.max_zero_time_depth:
            raise ValueError("run exceeds its zero-time-depth limit")
        if self.record_digest != canonical_record_digest(
            self.model_dump(mode="json", exclude={"record_digest"})
        ):
            raise ValueError("run record digest mismatch")
        return self


def representation_digest(content: str) -> str:
    """Return the canonical SHA-256 digest for encoded text content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def state_digest(state: CausalState) -> str:
    """Return a stable digest of complete protected canonical state."""
    payload = json.dumps(
        state.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def scenario_fingerprint(scenario: CausalScenario) -> str:
    """Bind checkpoints and results to the complete authored scenario."""
    payload = json.dumps(
        scenario.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def scenario_execution_fingerprint(scenario: CausalScenario) -> str:
    """Bind only authored content that can affect exact-core execution."""
    payload = {
        "runtime_contract": scenario.runtime_contract,
        "schema_version": scenario.schema_version,
        "scenario_id": scenario.scenario_id,
        "initial_state": scenario.initial_state.model_dump(mode="json"),
    }
    return canonical_record_digest(payload)


def trace_digest(events: Sequence[CausalEvent]) -> str:
    """Return a stable digest of the ordered canonical event sequence."""
    payload = _canonical_json(
        [event.model_dump(mode="json") for event in events],
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def canonical_record_digest(value: object) -> str:
    """Return a stable non-authenticating digest for one JSON-shaped record."""
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _canonical_json(value: JsonValue) -> str:
    """Serialize one JSON value without Python equality ambiguities."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _split_fact_id(fact_id: str) -> tuple[str, str]:
    """Split and validate one normalized ``entity.attribute`` path."""
    parts = fact_id.split(".")
    if len(parts) != 2:
        raise ValueError(f"invalid fact id {fact_id!r}")
    entity_id, attribute = parts
    _validate_id_token(entity_id, "fact entity")
    _validate_id_token(attribute, "fact attribute")
    return entity_id, attribute


def _validate_id_token(value: str, label: str) -> None:
    """Validate the normalized identifier subset used inside fact paths."""
    if not value or not value[0].isalpha() or not value.islower():
        raise ValueError(f"invalid {label} {value!r}")
    if not value.replace("_", "a").isalnum():
        raise ValueError(f"invalid {label} {value!r}")


def _keys_match(
    records: Mapping[str, BaseModel], id_field: str, collection_name: str
) -> None:
    """Require each map key to equal the embedded canonical record ID."""
    for key, record in records.items():
        if getattr(record, id_field) != key:
            raise ValueError(
                f"{collection_name} key {key!r} does not match {id_field}"
            )


def _require_unique(values: Sequence[str], label: str) -> None:
    """Reject duplicate identifiers without silently normalizing order."""
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must be unique")


def _require_disjoint_ids(collections: Mapping[str, set[str]]) -> None:
    """Keep every untyped runtime reference globally unambiguous."""
    owners: dict[str, str] = {}
    for collection_name, identifiers in collections.items():
        for identifier in identifiers:
            previous = owners.get(identifier)
            if previous is not None:
                raise ValueError(
                    f"runtime id {identifier!r} appears in both {previous} and "
                    f"{collection_name}"
                )
            owners[identifier] = collection_name


def _validate_place_tree(places: Mapping[str, PlaceState]) -> None:
    """Reject unknown parents and containment cycles."""
    place_ids = set(places)
    for place in places.values():
        if (
            place.parent_place_id is not None
            and place.parent_place_id not in place_ids
        ):
            raise ValueError(
                f"place {place.place_id!r} has unknown parent "
                f"{place.parent_place_id!r}"
            )

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(place_id: str) -> None:
        if place_id in visited:
            return
        if place_id in visiting:
            raise ValueError("place containment contains a cycle")
        visiting.add(place_id)
        parent_id = places[place_id].parent_place_id
        if parent_id is not None:
            visit(parent_id)
        visiting.remove(place_id)
        visited.add(place_id)

    for place_id in places:
        visit(place_id)


def _validate_representation_lineage(
    representations: Mapping[str, RepresentationToken],
) -> None:
    """Reject indirect cycles in authored representation provenance."""
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(representation_id: str) -> None:
        if representation_id in visited:
            return
        if representation_id in visiting:
            raise ValueError("representation parent lineage contains a cycle")
        visiting.add(representation_id)
        for parent_id in representations[representation_id].parent_representation_ids:
            visit(parent_id)
        visiting.remove(representation_id)
        visited.add(representation_id)

    for representation_id in representations:
        visit(representation_id)


def _require_fields(event: CausalEvent, *field_names: str) -> None:
    """Require event-kind-specific identifying fields."""
    missing = [field for field in field_names if getattr(event, field) is None]
    if missing:
        raise ValueError(
            f"{event.event_kind} event missing required fields {missing!r}"
        )


def _validate_trace(
    events: Sequence[CausalEvent],
    *,
    terminal: bool,
    run_id: str,
) -> None:
    """Validate event order, parent lineage, and terminal shape."""
    if not events or events[0].event_kind != "run_started":
        raise ValueError("trace must begin with run_started")
    if events[0].logical_time != 0 or events[0].state_revision != 0:
        raise ValueError("run_started must occur at logical time/revision zero")
    if terminal and events[-1].event_kind != "run_completed":
        raise ValueError("completed trace must end with run_completed")
    if not terminal and events[-1].event_kind == "run_completed":
        raise ValueError("checkpoint trace may not be terminal")
    seen: set[str] = set()
    previous_revision = 0
    previous_logical_time = 0
    for sequence, event in enumerate(events):
        if event.run_id != run_id:
            raise ValueError("every event must bind the enclosing run id")
        if event.event_kind == "run_completed" and sequence != len(events) - 1:
            raise ValueError("run_completed may appear only at the trace tail")
        if event.sequence != sequence:
            raise ValueError("event sequences must be contiguous")
        unknown = set(event.causal_parent_event_ids) - seen
        if unknown:
            raise ValueError(
                f"event {event.event_id!r} has missing/future parents "
                f"{sorted(unknown)!r}"
            )
        if event.state_revision < previous_revision:
            raise ValueError("event state revisions may not regress")
        if event.logical_time < previous_logical_time:
            raise ValueError("event logical time may not regress")
        if event.event_kind == "state_committed":
            if event.state_revision != previous_revision + 1:
                raise ValueError("commit events must advance one state revision")
        elif event.state_revision != previous_revision:
            raise ValueError("non-commit events may not change state revision")
        previous_revision = event.state_revision
        previous_logical_time = event.logical_time
        seen.add(event.event_id)
    _validate_event_causality(events)


def _validate_run_binding(
    events: Sequence[CausalEvent],
    *,
    scenario_id: str,
    scenario_execution_fingerprint: str,
    max_effects: int,
    max_zero_time_depth: int,
) -> None:
    """Bind persisted limits and execution identity to the root occurrence."""
    root = events[0]
    expected: dict[str, JsonValue] = {
        "scenario_id": scenario_id,
        "runtime_contract": RUNTIME_CONTRACT,
        "scenario_execution_fingerprint": scenario_execution_fingerprint,
        "max_effects": max_effects,
        "max_zero_time_depth": max_zero_time_depth,
    }
    if root.details != expected:
        raise ValueError("run root disagrees with execution identity or limits")


def _validate_event_causality(events: Sequence[CausalEvent]) -> None:
    """Require each typed occurrence to name the event that actually caused it."""
    by_id: dict[str, CausalEvent] = {}
    emitted_ids: set[str] = set()
    resolution_kinds: dict[str, set[EventKind]] = {}
    action_effect_counts: dict[str, int] = {}
    routed_child_counts: dict[str, int] = {}
    mechanism_child_counts: dict[str, int] = {}

    for index, event in enumerate(events):
        parents = [by_id[parent_id] for parent_id in event.causal_parent_event_ids]
        if event.event_kind == "run_started":
            if event.variance_source != "none":
                raise ValueError("run_started cannot claim a variance source")
        elif event.event_kind == "action_attempted":
            if len(parents) != 1 or parents[0] is not events[index - 1]:
                raise ValueError("action must descend from the prior trace tail")
            if event.variance_source != "external_action":
                raise ValueError("action attempt must identify external variance")
        elif event.event_kind == "effect_emitted":
            parent = _only_parent(event, parents)
            if parent.event_kind not in {"action_attempted", "state_committed"}:
                raise ValueError("effect emission has the wrong parent kind")
            assert event.effect_id is not None
            if event.effect_id in emitted_ids:
                raise ValueError("effect ids must be unique")
            emitted_ids.add(event.effect_id)
            if parent.event_kind == "action_attempted":
                if event.variance_source != "external_action":
                    raise ValueError("action effect must retain external variance")
                action_effect_counts[parent.event_id] = (
                    action_effect_counts.get(parent.event_id, 0) + 1
                )
                if (
                    event.source_port_id != parent.source_port_id
                    or event.representation_id != parent.representation_id
                ):
                    raise ValueError("action effect disagrees with its attempt")
            elif event.variance_source != "exact":
                raise ValueError("mechanism effect must identify exact execution")
        elif event.event_kind in {"effect_routed", "effect_dissipated"}:
            parent = _only_parent(event, parents)
            if parent.event_kind != "effect_emitted":
                raise ValueError("effect resolution must descend from its emission")
            if (
                event.effect_id != parent.effect_id
                or event.source_port_id != parent.source_port_id
                or event.representation_id != parent.representation_id
                or event.variance_source != parent.variance_source
            ):
                raise ValueError("effect resolution disagrees with its emission")
            if event.event_kind == "effect_routed":
                route_delay = event.details.get("route_delay")
                if (
                    not isinstance(route_delay, int)
                    or isinstance(route_delay, bool)
                    or route_delay < 0
                    or event.logical_time != parent.logical_time + route_delay
                ):
                    raise ValueError("effect route has invalid delay evidence")
            elif event.logical_time != parent.logical_time:
                raise ValueError("effect dissipation time disagrees with emission")
            assert event.effect_id is not None
            resolution_kinds.setdefault(event.effect_id, set()).add(
                event.event_kind
            )
        elif event.event_kind == "mechanism_executed":
            parent = _only_parent(event, parents)
            if parent.event_kind != "effect_routed":
                raise ValueError("mechanism execution must descend from one route")
            if (
                event.effect_id != parent.effect_id
                or event.target_port_id != parent.target_port_id
                or event.representation_id != parent.representation_id
                or event.variance_source != "exact"
            ):
                raise ValueError("mechanism execution disagrees with its route")
            routed_child_counts[parent.event_id] = (
                routed_child_counts.get(parent.event_id, 0) + 1
            )
        elif event.event_kind == "state_committed":
            parent = _only_parent(event, parents)
            if parent.event_kind != "mechanism_executed":
                raise ValueError("state commit must descend from one mechanism")
            if (
                event.mechanism_id != parent.mechanism_id
                or event.effect_id != parent.effect_id
                or event.target_port_id != parent.target_port_id
                or event.variance_source != "exact"
            ):
                raise ValueError("state commit disagrees with its mechanism")
            if event.patch is None or event.logical_time != event.patch.after_logical_time:
                raise ValueError("state commit time disagrees with its patch")
            mechanism_child_counts[parent.event_id] = (
                mechanism_child_counts.get(parent.event_id, 0) + 1
            )
        elif event.event_kind == "observation_delivered":
            parent = _only_parent(event, parents)
            if parent.event_kind != "state_committed":
                raise ValueError("observation delivery must descend from one commit")
            if (
                event.mechanism_id != parent.mechanism_id
                or event.state_revision != parent.state_revision
                or event.variance_source != "exact"
            ):
                raise ValueError("observation delivery disagrees with its commit")
        elif event.event_kind == "run_completed":
            if len(parents) != 1 or parents[0] is not events[index - 1]:
                raise ValueError("run completion must descend from the prior tail")
            if event.variance_source != "none":
                raise ValueError("run completion cannot claim a variance source")
        by_id[event.event_id] = event

    action_event_ids = {
        event.event_id for event in events if event.event_kind == "action_attempted"
    }
    if any(action_effect_counts.get(event_id, 0) != 1 for event_id in action_event_ids):
        raise ValueError("every accepted action must emit exactly one initial effect")
    if emitted_ids != set(resolution_kinds):
        raise ValueError("every emitted effect must have a terminal routing decision")
    if any(
        kinds not in ({"effect_routed"}, {"effect_dissipated"})
        for kinds in resolution_kinds.values()
    ):
        raise ValueError("one effect cannot both route and dissipate")
    routed_event_ids = {
        event.event_id for event in events if event.event_kind == "effect_routed"
    }
    if any(routed_child_counts.get(event_id, 0) != 1 for event_id in routed_event_ids):
        raise ValueError("every route must execute exactly one mechanism")
    mechanism_event_ids = {
        event.event_id
        for event in events
        if event.event_kind == "mechanism_executed"
    }
    if any(
        mechanism_child_counts.get(event_id, 0) != 1
        for event_id in mechanism_event_ids
    ):
        raise ValueError("every mechanism execution must commit exactly once")


def _only_parent(event: CausalEvent, parents: Sequence[CausalEvent]) -> CausalEvent:
    """Return the one typed parent required by a causal-core event."""
    if len(parents) != 1:
        raise ValueError(f"{event.event_kind} requires exactly one causal parent")
    return parents[0]


def _validate_actions(
    accepted_action_ids: Sequence[str], events: Sequence[CausalEvent]
) -> None:
    """Bind the accepted-action ledger to canonical action events in order."""
    event_action_ids = [
        event.action_id
        for event in events
        if event.event_kind == "action_attempted" and event.action_id is not None
    ]
    if list(accepted_action_ids) != event_action_ids:
        raise ValueError("accepted action ids disagree with action events")


def _validate_event_references(
    state: CausalState, events: Sequence[CausalEvent]
) -> None:
    """Resolve every event reference against the canonical runtime world."""
    for event in events:
        if (
            event.actor_entity_id is not None
            and event.actor_entity_id not in state.entities
        ):
            raise ValueError(f"event {event.event_id!r} has unknown actor")
        if event.mechanism_id is not None:
            mechanism = state.mechanisms.get(event.mechanism_id)
            if mechanism is None:
                raise ValueError(f"event {event.event_id!r} has unknown mechanism")
            if event.event_kind == "mechanism_executed":
                if event.target_port_id not in mechanism.input_port_ids:
                    raise ValueError("mechanism event has an unbound input port")
                if event.read_fact_ids != mechanism.read_fact_ids:
                    raise ValueError("mechanism event has the wrong read surface")
                if (
                    event.read_representation_ids
                    != mechanism.read_representation_ids
                ):
                    raise ValueError(
                        "mechanism event has the wrong representation-read surface"
                    )
                if (
                    event.read_placement_entity_ids
                    != mechanism.read_placement_entity_ids
                ):
                    raise ValueError(
                        "mechanism event has the wrong placement-read surface"
                    )
                if event.read_spatial_link_ids != mechanism.read_spatial_link_ids:
                    raise ValueError(
                        "mechanism event has the wrong spatial-link-read surface"
                    )
                invariant_ids = [item.invariant_id for item in event.invariants]
                if set(invariant_ids) != set(mechanism.invariant_ids) or not all(
                    item.passed for item in event.invariants
                ):
                    raise ValueError("mechanism event has invalid invariant evidence")
        for port_id in (event.source_port_id, event.target_port_id):
            if port_id is not None and port_id not in state.ports:
                raise ValueError(f"event {event.event_id!r} has unknown port")
        if event.event_kind in {"action_attempted", "effect_emitted"}:
            assert event.source_port_id is not None
            source = state.ports[event.source_port_id]
            if source.direction != "output":
                raise ValueError("action/effect source must be an output port")
            if (
                event.event_kind == "action_attempted"
                and source.owner_ref != event.actor_entity_id
            ):
                raise ValueError("action event uses an output not owned by its actor")
        if event.event_kind in {
            "effect_routed",
            "mechanism_executed",
            "state_committed",
            "observation_delivered",
        }:
            assert event.target_port_id is not None
            if state.ports[event.target_port_id].direction != "input":
                raise ValueError("routed event target must be an input port")
        if (
            event.event_kind == "effect_routed"
            and event.source_port_id is not None
            and event.target_port_id is not None
            and state.ports[event.source_port_id].effect_type
            != state.ports[event.target_port_id].effect_type
        ):
            raise ValueError("routed event joins incompatible port types")
        if event.event_kind == "effect_routed":
            assert event.source_port_id is not None
            assert event.target_port_id is not None
            route_delay = event.details.get("route_delay")
            if event.route_kind == "connection":
                assert event.connection_id is not None
                connection = state.connections.get(event.connection_id)
                if connection is None:
                    raise ValueError("routed event has unknown connection")
                if not connection.enabled:
                    raise ValueError("routed event uses a disabled connection")
                if (
                    connection.source_port_id != event.source_port_id
                    or connection.target_port_id != event.target_port_id
                    or connection.delay != route_delay
                ):
                    raise ValueError("routed event disagrees with its connection")
            else:
                assert event.route_kind == "container"
                assert event.container_id is not None
                source = state.ports[event.source_port_id]
                target = state.ports[event.target_port_id]
                if (
                    event.container_id not in state.containers
                    or source.container_id != event.container_id
                    or target.container_id != event.container_id
                    or route_delay != 0
                ):
                    raise ValueError("routed event disagrees with local container")
        if (
            event.representation_id is not None
            and event.representation_id not in state.representations
        ):
            raise ValueError(f"event {event.event_id!r} has unknown representation")
        for fact_id in event.read_fact_ids:
            state.fact(fact_id)
        unknown_read_representations = (
            set(event.read_representation_ids) - set(state.representations)
        )
        if unknown_read_representations:
            raise ValueError(
                f"event {event.event_id!r} reads unknown representations "
                f"{sorted(unknown_read_representations)!r}"
            )
        unknown_read_placements = (
            set(event.read_placement_entity_ids) - set(state.placements)
        )
        if unknown_read_placements:
            raise ValueError(
                f"event {event.event_id!r} reads unknown placements "
                f"{sorted(unknown_read_placements)!r}"
            )
        unknown_read_spatial_links = (
            set(event.read_spatial_link_ids) - set(state.spatial_links)
        )
        if unknown_read_spatial_links:
            raise ValueError(
                f"event {event.event_id!r} reads unknown spatial links "
                f"{sorted(unknown_read_spatial_links)!r}"
            )
        if event.patch is not None:
            assert event.mechanism_id is not None
            mechanism = state.mechanisms[event.mechanism_id]
            for change in event.patch.fact_changes:
                fact = state.fact(change.fact_id)
                if change.fact_id not in mechanism.write_fact_ids:
                    raise ValueError("commit patch exceeds mechanism write authority")
                if change.visibility != fact.visibility:
                    raise ValueError("commit patch fact visibility disagrees with state")
            for placement_change in event.patch.placement_changes:
                if (
                    placement_change.entity_id
                    not in mechanism.write_placement_entity_ids
                ):
                    raise ValueError(
                        "commit patch exceeds placement write authority"
                    )
                if (
                    placement_change.via_spatial_link_id
                    not in mechanism.read_spatial_link_ids
                ):
                    raise ValueError(
                        "commit patch uses an undeclared spatial link"
                    )
            for carrier_change in event.patch.carrier_changes:
                if carrier_change.carrier_id not in mechanism.write_carrier_ids:
                    raise ValueError("commit patch exceeds carrier write authority")
            for representation in event.patch.representations_added:
                if representation.carrier_id not in mechanism.write_carrier_ids:
                    raise ValueError(
                        "commit representation exceeds carrier write authority"
                    )


def _validate_state_evidence(
    state: CausalState, events: Sequence[CausalEvent]
) -> None:
    """Bind each observation to one patch, commit, and delivery occurrence."""
    by_id = {event.event_id: event for event in events}
    patched: dict[str, tuple[ObservationRecord, CausalEvent]] = {}
    delivered: dict[str, CausalEvent] = {}
    added_representations: dict[str, RepresentationToken] = {}
    carrier_revision: dict[str, int] = {}
    placement_after: dict[str, str] = {}
    for event in events:
        if event.event_kind == "state_committed":
            assert event.patch is not None
            for placement_change in event.patch.placement_changes:
                expected_place = placement_after.get(
                    placement_change.entity_id
                )
                if (
                    expected_place is not None
                    and placement_change.before_place_id != expected_place
                ):
                    raise ValueError("placement patches are not contiguous")
                placement_after[placement_change.entity_id] = (
                    placement_change.after_place_id
                )
            for carrier_change in event.patch.carrier_changes:
                expected_revision = carrier_revision.get(
                    carrier_change.carrier_id
                )
                if (
                    expected_revision is not None
                    and carrier_change.before_revision != expected_revision
                ):
                    raise ValueError("carrier patch revisions are not contiguous")
                carrier_revision[carrier_change.carrier_id] = (
                    carrier_change.after_revision
                )
            for representation in event.patch.representations_added:
                if representation.representation_id in added_representations:
                    raise ValueError("representation is added by multiple patches")
                added_representations[representation.representation_id] = representation
            for observation in event.patch.observations_added:
                if observation.observation_id in patched:
                    raise ValueError("observation is added by multiple patches")
                if observation.causal_parent_event_ids != event.causal_parent_event_ids:
                    raise ValueError("observation parents disagree with its mechanism")
                patched[observation.observation_id] = (observation, event)
        elif event.event_kind == "observation_delivered":
            assert event.observation_id is not None
            if event.observation_id in delivered:
                raise ValueError("observation has multiple delivery events")
            delivered[event.observation_id] = event

    expected_ids = set(state.observations)
    if expected_ids != set(patched) or expected_ids != set(delivered):
        raise ValueError("observation state, patches, and deliveries disagree")
    for observation_id, state_observation in state.observations.items():
        patch_observation, commit = patched[observation_id]
        delivery = delivered[observation_id]
        if patch_observation != state_observation:
            raise ValueError("patched observation disagrees with canonical state")
        if any(parent_id not in by_id for parent_id in state_observation.causal_parent_event_ids):
            raise ValueError("observation has an unknown causal parent")
        if delivery.causal_parent_event_ids != [commit.event_id]:
            raise ValueError("observation delivery has the wrong commit parent")
        if (
            delivery.mechanism_id != commit.mechanism_id
            or delivery.target_port_id != state_observation.via_port_id
            or delivery.representation_id != state_observation.representation_id
            or delivery.logical_time != state_observation.logical_time
        ):
            raise ValueError("observation delivery disagrees with its state record")
    for representation_id, representation in added_representations.items():
        if state.representations.get(representation_id) != representation:
            raise ValueError(
                "patched representation disagrees with canonical state"
            )
    for carrier_id, last_revision in carrier_revision.items():
        if state.carriers[carrier_id].revision != last_revision:
            raise ValueError("patched carrier revision disagrees with canonical state")
    for entity_id, last_place_id in placement_after.items():
        if state.placements[entity_id].place_id != last_place_id:
            raise ValueError("patched placement disagrees with canonical state")


def _validate_metrics(
    metrics: CausalMetrics, events: Sequence[CausalEvent]
) -> None:
    """Recompute exact event-count metrics that have canonical trace witnesses."""
    counts = {
        kind: sum(event.event_kind == kind for event in events)
        for kind in (
            "effect_emitted",
            "effect_routed",
            "effect_dissipated",
            "mechanism_executed",
            "state_committed",
            "observation_delivered",
        )
    }
    expected = {
        "effect_emitted": metrics.effects_emitted,
        "effect_routed": metrics.routed_deliveries,
        "effect_dissipated": metrics.dissipated_effects,
        "mechanism_executed": metrics.mechanism_executions,
        "state_committed": metrics.state_commits,
        "observation_delivered": metrics.observations_delivered,
    }
    if counts != expected:
        raise ValueError("metrics disagree with canonical event counts")
    if metrics.effects_processed != metrics.effects_emitted:
        raise ValueError("quiescent evidence must account for every emitted effect")
    if metrics.candidates_considered != metrics.routed_deliveries:
        raise ValueError("candidate accounting must equal realized typed routes")
    route_counts: dict[str, int] = {}
    zero_time_depths: list[int] = []
    for event in events:
        if event.event_kind == "effect_routed":
            assert event.effect_id is not None
            route_counts[event.effect_id] = route_counts.get(event.effect_id, 0) + 1
        if event.event_kind == "effect_emitted":
            depth = event.details.get("zero_time_depth")
            if not isinstance(depth, int) or isinstance(depth, bool) or depth < 0:
                raise ValueError("effect emission has invalid zero-time depth")
            zero_time_depths.append(depth)
    expected_fanout = max(route_counts.values(), default=0)
    expected_depth = max(zero_time_depths, default=0)
    if metrics.maximum_fanout != expected_fanout:
        raise ValueError("maximum fan-out disagrees with routed events")
    if metrics.maximum_zero_time_depth != expected_depth:
        raise ValueError("maximum zero-time depth disagrees with emitted effects")
    minimum_queue_high_water = max(
        1 if metrics.effects_emitted else 0,
        expected_fanout,
    )
    if metrics.queue_high_water < minimum_queue_high_water:
        raise ValueError("queue high-water mark is below witnessed scheduled work")
