# ADR-006: Analytical Boundaries Are Reversible Derived Coarse-Grainings

## Status

Accepted — 2026-07-23.

## Context

The causal model already declares execution-inert analytical boundaries, but
the operator surface omits them. The exact graph therefore shows components
without letting an analyst inspect a higher-level system view. Inventing an
organization node with its own state, decisions, or actions would contradict
the model: the boundary is a chosen coarse-graining over grounded members, not
another actor.

A useful aggregate must also avoid false simplicity. Collapsing a boundary
hides member identities, internal routes, state facts, representations, and
event distinctions. If that loss is not visible and reversible, the aggregate
becomes a second narrative truth.

## Decision

Project each authored `AnalyticalBoundary` as a derived operator view:

- it never enters the active-system registry, owns an action interface, or
  executes a mechanism;
- its state at a revision is calculated from the analyst-safe member snapshot;
- incoming, outgoing, and internal routes are calculated from exact concrete
  connections;
- its trace is the ordered subset of canonical events focused on its members;
- its coarse graph node replaces member nodes only in boundary mode;
- every coarse node can step down to the exact member graph at the same event
  and state revision;
- the projection reports what the coarse view hides.

The canonical state, event log, and exact graph remain unchanged. Aggregate
identities are namespaced operator-view IDs and cannot collide with runtime
referents.

## Borrow Versus Build

Borrow the existing analytical-boundary contract, event focus identities,
event-time analyst snapshots, concrete route declarations, mechanism input
bindings, carrier ownership, and representation lineage. Build a small
server-side coarse projection and dependency-free SVG rendering because the
required behavior is one reversible grouping operation; a graph framework or
general ontology reasoner would add more hidden behavior than value here.

## Consequences

The same realization can be inspected at two scales without creating another
mind or world state. Aggregate claims remain mechanically traceable to exact
members and events.

This decision does not infer new boundaries, overlapping-boundary semantics,
causal emergence metrics, or organization-level agency. A future requirement
for overlapping/nested boundaries must supersede this ADR with explicit
composition rules.
