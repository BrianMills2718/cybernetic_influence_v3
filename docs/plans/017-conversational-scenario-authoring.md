---
doc_role: active_plan
authority: implementation_plan
status: completed
created: 2026-07-25
predecessor: 016-canonical-analyst-demo.md
---

# Slice 17: Typed Scenario Authoring

## Outcome

An analyst can eventually describe a bounded situation conversationally,
review the resulting typed draft and its graph, approve it, and run it only
when its executable mechanisms are already validated implementations.

The stable example is an equipment checkout desk: an employee requests a
laptop, a clerk receives the request through a configured ticket route, and an
exact reservation gate reserves an available laptop only for an eligible
employee. The employee and clerk occupy connected rooms, but the hallway does
not itself carry the request or grant reservation authority. The department is
an execution-inert analytical boundary.

## Boundaries

- Natural language may propose a typed draft; it never creates mechanism code.
- `resource_request_v1` is the sole executable template in this slice.
- The compiler, not the draft, owns ports, connections, carriers, exact
  mechanisms, active bindings, and implementation identities.
- People receive position, disposition, and remembered context, not procedural
  instructions embedded in a persona.
- Spatial topology, configured interaction pathways, and realized causal graph
  retain their existing separate meanings.
- Analytical boundaries remain `executor: false` and cannot act.

## Thin slices

### 17A — deterministic template compiler

Implement strict draft contracts and semantic validation for people, objects,
information, places, topology, timing assumptions, the resource-request
workflow, and analytical boundaries. Compile only `resource_request_v1` to the
existing causal and active-runtime contracts. Prove it with zero-cost scripted
runs: an available resource is reserved, an unavailable resource is denied
after a reviewer attempt, replay reconstructs final state, no provider call is
made, and spatial adjacency does not manufacture a route.

The compiler must use positive-duration modeled minutes. A core checkpoint
must validate when an emitted effect has already been structurally fanned out
into future deliveries but those deliveries have not yet been retained as route
events.

### 17B — conversational revision and approval

Add a structured LLM drafting conversation, revision persistence, validation
diagnostics, graph preview, explicit approval manifest, and authored run API/UI.
The LLM supplies only `ScenarioDraftProposal`; an approved compiler digest
binds the later run. Provider failure preserves the previous draft; duplicate
messages cannot duplicate spend; unapproved or stale drafts cannot run.

Implemented as a provider-neutral structured-call seam using the shared
`llm_client`. The browser permits only a zero-cost scripted execution of the
approved template in this slice; live authored people require a separately
reviewed native binding and are intentionally not implied by approval.

The authoring seam attempts structured repair at most three times for one user
message. Each attempt has a distinct trace and per-call ceiling; the retained
draft shows accepted, repair, or provider-error status and observed cost when
available. The loop stops visibly at the cap, and a provider-only failure does
not erase an earlier valid proposal.

## Non-goals

No arbitrary mechanism/DSL generation, organization executors, additional
templates, automatic fallback model selection, comparison tooling, Levin-style
assays, live graph streaming, or deployment/live spend belongs to 17A.
