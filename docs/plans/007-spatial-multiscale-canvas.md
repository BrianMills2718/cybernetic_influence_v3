# Slice 7: Spatial Multiscale Canvas

**Status: In progress — 2026-07-23.**

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
2. After the readout, decide whether the next risk is denser layout/filtering
   or explicit multiple/nested composites. Do not implement nesting before
   composition semantics and a scenario that needs it.
3. Later, investigate whether any coarse-graining warrants the stronger
   descriptive label “composite agent”; visualization alone is insufficient.

## Concern Register

- C034 open invariant: the graph library must remain a pure view and never
  become a second topology authority.
- C035 open architecture: the current static V3 page needs one isolated
  frontend bundle without forcing a whole-page React migration.
- C036 open readout: the expanded hull must improve spatial comprehension at
  service-desk and physical-access sizes rather than merely reproduce a dense
  screenshot.
- C037 open product policy: exact members should remain the initial view unless
  browser evidence shows the macro view is a better entry point.
- C038 deferred architecture: overlapping and nested analytical boundaries
  need explicit composition and collapse rules.
- C039 deferred ontology: “composite agent” requires criteria beyond authored
  membership and must not be inferred by the canvas.
