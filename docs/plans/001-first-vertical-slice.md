# First Vertical Slice

**Status: Slice 1 complete — 2026-07-23.**

## Frame

Create a clean simulator that can run one sociotechnical scenario and let an
operator understand the result without any V2 runtime or UI.

## Constraints

Fresh history; private repository; no legacy imports, artifacts, secrets,
compatibility adapters, organization executor, or second inspector product.
Keep `llm_client` as the provider boundary.

## Current-State Assessment

The causal core, active runtime, and service-desk scenario form a proven
self-contained source island in V2. The old backend and frontend do not.

## Gap

The clean repository needs one runnable path through configuration, execution,
narrative, world inspection, and person traces.

## Research Basis

Borrow the locally proven contracts and progressive-disclosure hierarchy.
Hand-roll only the small API and interface because carrying the old workbench
would reproduce the product debt this repository exists to remove.

## Modality Diagnosis

Architecture, dependency isolation, execution contracts, and trace
inspectability are deductive. Emergent live-agent behavior remains exploratory
and is read from traces rather than assigned a guessed success threshold.

## Vertical Scope

One service-desk run with two cognition profiles, three world conditions,
scripted and authorized-live execution, narrative, world-node selection, person
trace selection, and raw evidence.

## De-risks

Proves the clean repository is a functioning simulator rather than a source
archive or UI mock.

## Risk-Ordered Slices

### Slice 1 — Walking simulator

Extract the causal/runtime island, run service desk end to end, and expose the
result through one API and page.

### Slice 2 — Durable runs

Add crash-safe retained run identity only after the clean execution and
inspection contract passes.

### Directional later work

General scenario authoring, game-master adjudication, reusable position
entities, information-content modeling, and multiscale aggregate views are
introduced as vertical scenarios—not horizontal frameworks.

## Acceptance Criteria

1. A scripted run completes with zero calls and zero cost.
2. Missing path and speed pressure retain distinct traced outcomes.
3. Live execution is refused unless explicitly authorized.
4. Narrative, world nodes, and each person trace are selectable.
5. No source, import, artifact, UI label, or dependency references V2.
6. Tests, type checks, browser smoke, secret scan, and diff checks pass.

## Required Tests

API configuration, zero-cost run, intervention runs, authorization refusal,
static UI, core replay, type check, dependency scan, and browser interaction.

## Audit And Cleanup

Attack hidden legacy imports, copied protected prompts, secrets, unbounded
spend, organization executors, scripted-only product claims, raw-data-first UI,
and unused migrated code. Fix or register every finding before publication.

## Concern Register Triage

- C001 deferred to Slice 2: in-memory API runs are not durable.
- C002 mitigated: the first map exposes selectable typed nodes plus every
  declared source → target route. Time-animated causal flow remains deferred to
  Slice 2 rather than being falsely claimed complete.
- C003 accepted for Slice 1: scripted mode is the zero-cost test oracle; live
  mode remains the behavioral instrument.

## Implementation Result

The clean repository runs all three service-desk world conditions under either
cognition profile. The API refuses unauthorized live use; scripted tests
complete with zero calls and cost. The single Simulator page presents narrative,
declared routes, selectable world nodes, three person traces, and collapsed raw
evidence. Strict typing, four API/intervention tests, a headless browser
run/node/trace smoke check, visual review, legacy-import scan, and secret scan
pass.
