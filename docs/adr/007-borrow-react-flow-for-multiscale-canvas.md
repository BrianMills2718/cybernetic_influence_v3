# ADR-007: Borrow React Flow for the Multiscale Canvas

## Status

Accepted — 2026-07-23.

## Context

The dependency-free Slice 6 graph can highlight exact relations and reverse one
coarse projection, but it is a card grid rather than a graph-navigation
instrument. It has no viewport, fit-to-view, stable graph layout, node dragging,
edge selection, or expanded composite hull. The previous V2 workbench already
proved these interactions with React Flow and Dagre.

The simulator's goal requires moving up and down scale while retaining a route
to the exact people, information, mechanisms, and world objects. Reimplementing
a viewport and graph interaction layer would not be YAGNI; it would duplicate a
solved local implementation and keep the weaker readout.

## Decision

Borrow the proven React Flow 11 and Dagre canvas from V2, adapted to V3's
analyst-safe retained document:

- keep the existing V3 API, runtime, temporal snapshots, boundary projection,
  narrative, timeline, and inspector;
- build one isolated React/TypeScript graph bundle and mount it inside the
  current operator-first page;
- render exact members inside a labeled analytical hull when expanded;
- replace those exact members with one explicitly execution-inert macro node
  when collapsed;
- pan, zoom, fit, drag, select, and event-highlight without changing canonical
  state or the selected event/revision;
- show concrete connections, mechanism bindings, information locations, and
  representation lineage as visually distinct relations.

The canvas may visualize only authored boundary membership and retained exact
relations. A displayed composite is not thereby a mind, executor, organization,
or causal source.

## Alternatives

- Keep extending the hand-rolled SVG grid: rejected because viewport, layout,
  hit-testing, and grouping are graph-library responsibilities already solved
  in the prior implementation.
- Restore the whole V2 workbench: rejected because it would reintroduce the UI
  and conceptual complexity V3 deliberately removed.
- Infer composite agents or nested boundaries: deferred until explicit
  composition semantics and scenario evidence exist.

## Consequences

The frontend regains one mature dependency island and a build step. Graph
failures remain observable through React Flow state, browser checks, and the
unchanged exact evidence inspector. The rest of the V3 UI remains small and
framework-independent.

This ADR is superseded if a later canvas demonstrates the same interaction and
inspection behavior with materially lower lifecycle cost.
