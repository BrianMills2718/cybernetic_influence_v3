---
doc_role: implementation_plan
authority: bounded_design
status: implemented
created: 2026-09-09
updated: 2026-09-09
depends_on:
  - ../ROADMAP.md
  - ../GOAL.md
  - 037-waltzman-outreach-funnel.md
---

# Slice 38: Living replay for generated worlds

## Outcome

After a visitor generates and runs a `general_world_v2` simulation, the first
result surface should look like a world changing over time rather than a graph
they must decode. Reuse the retained `/api/runs/{run_id}/summary` contract and
its `simulation-replay.v1` scenes; do not add a second runner or backend.

## Presentation contract

- primary completed-run view: **Living world replay**;
- one shared scene index drives living replay and the existing detailed graph;
- play, previous/next, and scrub controls advance retained scenes only;
- three independently visible relation layers: Information, World links, Causal;
- people, information, and world/constraint nodes remain visibly distinct;
- accepted/rejected world-change facts and scene focus are shown beside the world;
- clicking a visible node explains its retained meaning and current state;
- the existing graph replay remains available immediately below for expert inspection;
- Waltzman/Levin/outcome lenses remain detachable post-run analysis.

## Data boundary

Use only fields already in the compact summary:

`influence_network.nodes/edges`, `simulation_replay.scenes`, scene
`visible_*`, `focus_*`, `node_overrides`, and `facts`. Do not infer belief from
information delivery and do not turn analysis findings into world state.

## Acceptance

- [x] completed `general_world_v2` runs show the living replay above the graph replay;
- [x] play/step/scrub stay synchronized with the existing retained scene sequence;
- [x] Information / World links / Causal toggles affect presentation only;
- [x] node click inspection uses retained node/override/edge data;
- [x] non-general historical runs keep their existing result behavior;
- [x] no new API endpoint, model call, or runtime dependency is introduced;
- [x] focused public tests and browser checks cover the new surface.

## Verification

- `pytest -q tests/test_public_waltzman.py`: 20 focused tests passed.
- provider-free `general_world_v2` probe: 21 retained nodes, 28 edges, 9 replay scenes.
- Chromium: living replay rendered at 1440x1000, 768x900, and 390x844 with no horizontal overflow, console errors, or failed requests.
- Browser interactions verified Next, scrub, layer toggles, node inspection, and non-general fallback.
- The living adapter reads only the existing compact summary/replay fields; static regression forbids `apiRequest`/`fetch` inside the adapter block.

## Stop condition

Stop after one retained general-world summary renders clearly in the living view.
Do not add spatial authoring, a new graph library, streaming, or engine migration
in this slice.
