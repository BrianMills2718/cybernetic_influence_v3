---
doc_role: historical_evidence
authority: evidence
status: complete
updated: 2026-07-23
---

# Slice 7: Spatial Multiscale Canvas

**Status: Complete — 2026-07-23.**

## Frame

Restore the graph as the main multiscale inspection instrument: a pannable,
zoomable spatial network in which the operator can see exact humans,
information, mechanisms, and world objects inside a composite boundary,
collapse that boundary, and step back down without leaving the selected causal
event.

## Constraints

- Preserve the V3 runtime, retained contracts, redaction, narrative, timeline,
  access controls, and zero-cost scripted path.
- Borrow only the proven graph-canvas subset of V2, not the V2 workbench.
- Display authored membership and exact retained relations; do not infer
  organizations, agency, nested boundaries, permissions, or causal edges.
- Keep one-boundary collapse semantics until overlap/nesting rules are designed.

## Modality

Topology, temporal filtering, exact/coarse reversibility, non-execution, and
selection contracts are deductive. Layout legibility at realistic node counts
is exploratory and must be judged in a browser at multiple events and scales.

## Borrow Versus Build

- Borrow React Flow 11 controls, viewport, hit testing, and edge rendering.
- Borrow Dagre layout and the V2 expanded-hull/collapsed-macro transform.
- Build a narrow V3 adapter and node presentation because V3's retained
  document and ontology are different.
- Keep the existing exact server-side projection as authority.

## Slice Contract

- **Vertical scope:** open retained run → inspect exact network at one event →
  pan/zoom/select → see one expanded analytical hull → collapse to macro node →
  inspect loss/evidence → expand at the same event and revision.
- **Success:** exact nodes and relation kinds are legible and selectable;
  boundary members visibly occupy a composite hull; collapse/expand and
  event-step preserve temporal truth; the inspector and narrative remain
  synchronized.
- **Audit:** missing/stale nodes, future representations, boundary ID
  collisions, false macro execution, relation mislabeling, hidden external
  edges, selection drift, resize, direct retained-run reopen, old documents,
  CSP, build reproducibility, and protected-value leakage.
- **Cleanup:** remove the hand-rolled SVG layout as the primary path; retain a
  small failure fallback only if it is exercised and understandable.
- **Done when:** Linux and Mac gates pass, browser readout is materially closer
  to the prior spatial graph, every audit finding is dispositioned, docs are
  updated, and the accepted commit is pushed and deployed.

## Directional Roadmap

1. Restore the spatial canvas with one explicit analytical hull and one
   collapsed macro view.
2. The browser readout made the next risk explicit multiple/nested composites,
   not denser layout. Do not implement nesting before composition semantics and
   a scenario that needs it.
3. Later, investigate whether any coarse-graining warrants the stronger
   descriptive label “composite agent”; visualization alone is insufficient.

## Concern Register

- C034 passed: the graph library is a pure adapter over server-projected
  temporal nodes, edges, and boundaries and never becomes a topology authority.
- C035 resolved: one isolated React/TypeScript bundle mounts inside the static
  V3 page; the run controls, timeline, narrative, inspector, and traces remain
  framework-independent.
- C036 passed: browser review found the expanded 27-member service-desk hull and
  13-member physical-access hull materially closer to the prior spatial
  instrument, with legible external relationships and selectable exact nodes.
- C037 resolved: exact expanded members remain the initial view. Collapse is a
  visible canvas action and the loss report remains outside the canvas.
- C038 deferred → next architecture slice: overlapping and nested analytical
  boundaries need explicit composition and collapse rules plus a scenario that
  contains at least two meaningful composites.
- C039 deferred ontology: “composite agent” requires criteria beyond authored
  membership and must not be inferred by the canvas.

## Audit and Evidence

- Linux Python 3.12 and macOS Python 3.14 pass strict typing and 27 API/runtime
  tests; the TypeScript/Vite build passes on both hosts.
- The exact dependency lock installs 82 packages with zero npm audit findings.
- Headless Chrome exercised service run `run_3d96c7fe8fe4` and physical run
  `run_85b83fdc2565`: pan/zoom controls, fit, node drag, edge selection,
  event-time information growth, collapse, exact expansion, same-revision
  preservation, inspector synchronization, and direct retained-run reopen all
  passed with no severe console entries.
- At the first action, the service graph rendered 32 exact temporal nodes,
  including 27 inside its analytical hull, and collapsed to 6 visible nodes.
  The physical graph rendered 16 exact temporal nodes, including 13 inside its
  hull, and collapsed to 4.
- Stepping to the final event grew those graphs to 43 and 22 nodes
  respectively, proving that future representations were not shown early.
- The first bundle failed in the browser because a library-mode React build
  retained `process.env.NODE_ENV`. The build now defines production mode,
  halves the bundle, adds a static favicon, and passes a clean-console gate.
- Visual review found collapsed fit too conservative; the accepted fit permits
  a 1.35 maximum zoom without changing exact-node layout.
- Duplicate external scale buttons and route pills were removed when the
  spatial canvas is active. React Flow is now the single graph interaction
  surface; the old SVG remains only as a load-failure fallback.

## Reframe Gate

The remaining composite question is architectural, not a layout tuning
parameter. A future nested-composite slice must define explicit membership,
overlap, parent/child collapse, and cross-boundary edge rules before adding UI.
It must also keep “analytical composite” separate from the stronger claim
“composite agent.”
