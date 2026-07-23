# Slice 8: Topological World Substrate

**Status: Complete — 2026-07-23.**

## Frame

Make spatial location authoritative simulation state before making it a visual
layout. An operator inspecting the physical-access scenario must be able to
answer where each relevant entity was, which places were topologically
connected, what concrete substrate mediated the connection, why traversal was
accepted or denied, and whether placement actually changed.

Mode is plan-and-implement, design depth is Standard, and execution profile is
PoC. Runtime-state, migration, and UI overlays apply.

## Frozen Target

The authorized physical-access reference run contains a maintenance facility
with hallway and equipment-room places, a controlled threshold backed by the
secure door, the technician initially in the hallway, and pump_7 in the
equipment room. Exactly one crossing commit moves the technician through that
threshold. Policy-denied and latch-jammed arms retain the same topology without
moving the technician.

The retained machine-readable target is the run document's `world` projection,
event-revision snapshots, spatial focus identifiers, exact placement patch, and
replayable core result.

## Requirements and Owned Rules

- `CausalState` owns places, placements, and spatial links.
- Place validation owns known-parent and acyclic-containment rules.
- `MechanismSpec` owns declared spatial read/write authority.
- The causal engine owns endpoint, destination, link-declaration, and
  placement-write enforcement.
- Exact scenario mechanisms own door, policy, credential, and operability
  decisions.
- Replay owns before-value, link, endpoint, and final-digest verification.
- Presentation derives temporal world snapshots without mutating canonical
  state.
- React Flow renders either world topology or causal flow at the same selected
  event; it never becomes topology authority.

## Contract

New runtime records are `PlaceState`, `PlacementState`, `SpatialLinkState`,
`PlacementDraft`, and `PlacementChange`. Causal-core advances to v2.

The world projection contains:

- stable places with optional parent place;
- stable undirected topological links with substrate entity IDs and an explicit
  non-traversability claim;
- placements and unplaced entity IDs for every retained state revision.

Old retained documents without `world` remain usable and default to the causal
canvas.

## Critical UI Flow

1. Open the authorized physical-access reference run.
2. See the technician in the hallway, pump in the equipment room, and secure
   doorway between the place containers.
3. Select the threshold-crossing mechanism/commit and see the exact spatial
   referents highlighted.
4. Observe the technician move only at the placement commit.
5. Switch to causal flow at the same event and inspect exact mechanism and
   information evidence.
6. Open a denied arm and verify the topology persists while placement does not
   change.

## Acceptance and Disproof

Accept when:

- authorized crossing has one replayable hallway-to-equipment-room placement
  change through `equipment_room_threshold`;
- denied arms have no placement change;
- invalid place cycles, unknown links, wrong endpoints, and undeclared
  placement writes fail loudly;
- earlier revisions never show later placement;
- the link is visibly described as topology, not permission or capability;
- world/causal switching preserves event revision and exact selection context;
- service-desk behavior and old retained documents regress cleanly;
- desktop/mobile rendering, console, API, and server logs pass.

Disproof includes topology stored only in UI metadata, duplicate string-location
truth, traversal inferred from adjacency, placement changes that do not replay,
or a visually improved map that obscures the exact causal step-down.

## YAGNI Boundary

Do not add coordinates, physics, collision, pathfinding, fields of view,
automatic acoustic/visual propagation, GIS/OWL dependencies, avatar movement,
mobile nested places, or a claim that a spatial/analytical container is an
agent.

## Landscape Disposition

- OGC IndoorGML: reuse the space-node/connectivity-edge pattern; defer its
  geometry, navigation, exchange schema, and dependencies.
- BFO 2020: align with the distinction between material entities and spatial
  regions; do not adopt the ontology runtime.
- SOSA/SSN: retain as later guidance for spatially bounded observation and
  actuation; it is not required by this slice.

## Concern Register

- C040: `ContainerState` conflates typed broadcast routing with spatial
  language. Resolved by clarifying it as a routing locus and introducing
  separate spatial contracts.
- C041: adjacency could be mistaken for authorization or operability. Guarded
  by type names, engine ownership, link metadata, UI copy, and denied-arm tests.
- C042: physical objects may occupy boundaries rather than one place. Resolved
  for this slice by attaching the secure door as a spatial-link substrate.
- C043: spatial and analytical containment can overlap. Resolved by synchronized
  projections rather than one mixed nesting hierarchy.
- C044: deeper nesting and movable places remain deferred until a scenario
  requires them.

## Verification

Run `make check`, execute all three scripted physical-access arms, inspect the
exact placement patches and retained world snapshots, and exercise the critical
flow in desktop and mobile browsers. Preserve technical execution separately
from the user's later comprehension judgment.

Completed evidence:

- local and Mac-host gates passed static typing, 33 tests, and the production
  TypeScript/Vite build;
- the authorized arm committed and replayed exactly one
  hallway-to-equipment-room placement change, while both denied arms committed
  none;
- adversarial tests reject cyclic places, unknown and undeclared links, wrong
  link endpoints, and undeclared placement writes;
- the retained API document exposes three places, one explicitly
  non-traversability-implying link, and seven revision-keyed world snapshots;
- Chrome exercised the revision-5 crossing in both world and causal views
  without losing the selected revision or emitting console errors;
- the 1440 px desktop canvas showed both places, their event-time occupants,
  the secure-door link substrate, and the exact spatial evidence list;
- the 390 px mobile canvas retained pan/zoom, readable labels at its bounded
  starting scale, and no page-level horizontal overflow;
- the private Mac service restarted on version 0.8.0, reopened an older retained
  run, and completed a fresh zero-cost physical-access run.

This establishes technical execution and traceability. Whether the projection
is sufficiently intuitive for the operator remains a separate comprehension
judgment to collect through use rather than infer from automated gates.
