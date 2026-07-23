# Slice 2: Durable Temporal Inspection

**Status: Complete — 2026-07-23.**

## Frame

Make a simulation remain understandable after refresh or restart, and let the
operator move through causal time without mentally joining narrative, entities,
routes, and person traces.

## Constraints

Keep the single-process development shape, zero-cost scripted oracle, provider
boundary, exact causal evidence, and one-page product. Do not add a database,
job queue, public hosting, authentication, scenario framework, or speculative
ontology.

## Borrow Versus Build

Borrow the core's ordered event log and typed identifiers. Build a small atomic
JSON repository because the required operations are only retain, list, reopen,
and recoverable delete. Build the timeline projection in the API so all clients
receive the same causal focus metadata.

## Modality

- **Deductive:** atomic retention, stable IDs, restart behavior, API validation,
  recoverable deletion, event ordering, and exact ID linkage.
- **Exploratory:** whether stepping through the projected events makes the
  emergent process understandable. The readout is whether an operator can move
  from a concise event to the exact focused entities, route, person trace, and
  raw evidence without searching unrelated panels.

## Slice Contract

### Advances

Turns the walking simulator into a retained evidence instrument suitable for a
later always-on development host.

### Vertical Scope

Create or reopen one run, step through ordered causal events, see the active
narrative step, entities, route, and relevant person trace, then inspect exact
evidence.

### De-risks

Tests whether the event log can support human temporal explanation without
inventing a second narrative truth or flattening attempts, decisions, outcomes,
and observations.

### Success

1. A completed run survives a new application instance using the same run
   directory.
2. A pre-execution identity is retained and later classified as interrupted
   rather than silently lost.
3. Invalid IDs cannot address files outside the run directory.
4. Delete is recoverable and the deleted run disappears from normal history.
5. Every timeline item preserves event order and exact evidence identity.
6. Selecting an event synchronizes its narrative, focused nodes and route, and
   relevant person trace when one exists.
7. Baseline, missing-path, and speed-pressure runs remain distinguishable.

### Audit

Attempt path traversal, corrupt files, refresh/restart loss, partial writes,
empty histories, failed runs, unrelated-node highlighting, route
misattribution, invented psychological explanations, and accidental paid calls.

### Cleanup

Keep storage separate from scenario execution, keep projection server-side,
remove duplicated client rendering paths, and update the operator documentation.

### Done When

Tests and the exploratory readout pass, every audit finding is fixed or
dispositioned, cleanup is complete, and the concern register is triaged.

## Concern Register

- C004 accepted: JSON-per-run fits the current single-process retain/list/open
  operations. Supersede ADR-002 only after querying or multi-process execution
  becomes an observed requirement.
- C005 resolved: all three arms link every action to its actor, every routed
  effect to its exact connection and endpoints, every mechanism execution to
  its mechanism, and every observation to at least one focused entity.
- C006 deferred: Mac Mini hosting should follow this slice, using private
  access and an approved-commit deployment flow.
- C007 deferred: aggregate/multiscale graph views remain a later vertical
  scenario rather than an inferred grouping feature.
- C008 deferred: FastAPI's test client emits an upstream `httpx` transition
  warning. It does not affect runtime behavior; replace the adapter when the
  dependency ecosystem completes that transition.

## Audit Result

Seven API/storage/intervention tests and strict typing pass. A browser reopened
a retained speed-pressure run directly from its stable URL and rendered six
human action steps, 63 exact events, focused entities, and person traces.
Cross-arm projection checks found no missing action, route, mechanism, or
observation linkage. Secret, legacy-import, JavaScript syntax, and diff checks
pass.

Two audit findings were fixed:

1. The first-slice narrative selected event names the core does not emit. It
   now uses the exact `action_attempted` vocabulary while the timeline exposes
   mechanism and state detail.
2. Live model text previously entered HTML templates without escaping. All
   model- and trace-derived strings are now escaped before template insertion.

The exploratory readout passes: a selected human action steps directly down to
its exact event, focused entities, and matching person activation without
searching unrelated panels.

## Next Slice

### Slice 3 — Private development host

- **Advances:** makes retained long runs available away from the development
  shell without turning the simulator into a public service.
- **Vertical scope:** deploy one approved V3 commit to the Mac Mini, retain runs
  outside the checkout, keep secrets on the host, and reach the simulator over
  a private network.
- **De-risks:** tests whether remote availability improves the development loop
  enough to justify its operational surface.
- **Success:** restart-safe service, private access, scripted smoke run,
  retained reopen, explicit live authorization, and a documented pull/restart
  update path.
- **Audit:** attempt unauthenticated public access, missing secrets, stale
  checkout, service restart, disk-path loss, and accidental live spend.
- **Cleanup:** one service definition and one operator note; no CI/CD platform
  or container layer unless an observed host constraint requires it.
- **Done when:** gates pass, findings are dispositioned, cleanup is complete,
  and the register is triaged.
