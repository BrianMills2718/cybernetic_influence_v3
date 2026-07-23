# ADR 008: Separate Spatial Topology from Routing and Permission

**Status:** Accepted — 2026-07-23.

## Decision

The exact causal world owns three spatial concepts:

- places are spatial loci in an acyclic containment hierarchy;
- placements identify the current immediate place of a concrete entity;
- spatial links identify topological adjacency and their concrete substrates.

A spatial link does not assert permission, operability, reachability, perception,
or successful traversal. Exact mechanisms must declare the placements and links
they read and the entity placements they may change. The engine accepts a
placement change only across the endpoints of the declared link.

`ContainerState` remains a typed broadcast-routing locus. It is not reinterpreted
as authoritative spatial location. Analytical boundaries remain derived,
execution-inert coarse-grainings and are not spatial containers.

## Why

The physical-access scenario previously represented the equipment room as an
ordinary entity and the technician's location as an unvalidated string fact.
The graph therefore suggested spatial structure that the runtime did not own.
Reusing the routing container would further conflate co-location, typed signal
fan-out, physical containment, and permission.

The design borrows only the space-centred topological pattern from OGC
IndoorGML and the material-entity/spatial-region distinction from BFO. It does
not add either ontology or a GIS dependency.

## Consequences

- Causal-core and causal-graph contracts advance to version 2.
- Movement becomes a typed, replayable state transition.
- A world-topology projection may show place containers and links without
  inventing geometry.
- Existing retained analyst documents without a `world` projection continue to
  open in causal-flow mode.
- Metric geometry, automatic pathfinding, visibility, acoustics, movable
  containers, and spatially bounded perception remain deferred.

