---
doc_role: implementation_handoff
authority: bounded_design
status: implemented_through_slice_28
created: 2026-07-31
updated: 2026-08-18
depends_on:
  - docs/adr/013-generalized-simulator-foundation.md
  - docs/research/027-concordia-architecture-revisit.md
supersedes: physical-access parity proof previously specified in this file
---

# Slice 27 handoff: general Concordia world-transition vertical

## Gate

ADR-013 is adopted and its 2026-08-11 boundary clarification is accepted. This
handoff defined the first production implementation slice; per
[docs/ROADMAP.md](../ROADMAP.md)'s Artifact Dispositions table, it is
implemented through Slice 28 — the general bridge/port vertical exercises the
adopted world-transition seam without the old runtime as a hidden executor.
This handoff is retained for its original design rationale, not as a pending
gate.

## Outcome

Implement the smallest general world-composition and transition path on stock,
pinned Concordia:

```text
world truth
-> actor-authorized context
-> open semantic intent
-> declared transition authority
-> structured world patch
-> generic validation
-> atomic commit or visible rejection
-> bounded observation and retained evidence
```

Use one bridge/port configuration to prove the seam. The implementation must not
introduce a `PortScenario`, enumerate all possible action verbs, invoke
`CausalSession` or `ActiveRuntimeSession`, or create another simulation loop.
The scenario is an instance of general contracts, not a new workflow family.

The path must include one authentic Luna actor decision and one authentic Luna
semantic adjudication. If Luna is unavailable or repeatedly fails, stop and
report that fact rather than silently substituting Terra or a fixture.

## Stable example

A worker and fuel truck begin outside a port. A destroyed bridge blocks the
initial route. A temporary depot and a replacement route are created while the
simulation is running. The simulation checkpoints and restores. The worker then
proposes, in ordinary language, what to do next. A declared LLM transition
authority translates that intent into a structured patch; generic validation
accepts or rejects it; a successful commit places the worker and truck at the
port.

The worker may observe the blocked route and available replacement route but
must not receive the hidden cause of the bridge failure unless an explicit
information path delivers a representation of it.

This example discriminates among architecture candidates because it exercises:

- active and inert modeled things without pretending every thing is an actor;
- dynamic topology and placement;
- bounded observation rather than full-world prompting;
- an action verb not pre-enumerated by the scenario author;
- LLM adjudication constrained by generic state invariants; and
- checkpoint continuation under Concordia's outer lifecycle.

## Required general contracts

Names may change during implementation, but the responsibilities may not be
collapsed or hidden.

| Contract | Required responsibility |
|---|---|
| `GeneralWorldSpec` | Persistent things, state, places, placements, representations, resources, routes/topology, active-system bindings, timing, fidelity assumptions, and declared invariants |
| `ActorContext` | Only the observations, representations, affordance-relevant facts, and provenance the actor is allowed to receive |
| `SemanticActionIntent` | An open-ended attempted action with actor, objects, targets, purpose, and free semantic detail; no closed scenario verb union |
| `TransitionAuthoritySpec` | Authority kind, implementation reference, allowed reads/writes, assumptions, fidelity, provenance, and invalid questions |
| `WorldPatch` | Typed create/remove/replace/rebind operations against canonical world paths with evidence metadata |
| `PatchValidationResult` | Accepted/rejected status plus explicit reference, authority, topology, placement, information-boundary, and declared-invariant reasons |
| `TransitionEvidence` | Actor context, intent, authority invocation, proposed patch, validation, commit, resulting observation, model-call references, and checkpoint lineage |

The composition contract is semantic configuration. It may refer only to trusted
transition implementations already registered in code, except for explicitly
declared LLM-adjudicated behavior. Templates may compile into this same contract
but may not create parallel runtime families.

## Foundation boundary

| Concern | Slice owner |
|---|---|
| Actor/component lifecycle and actor selection | Stock Concordia entity, game-master, and engine path |
| Canonical world | Project-owned typed game-master component invoked through public Concordia seams |
| Active worker | Concordia entity/component |
| Bridge, truck, fuel, depot, route | Inert canonical-world records with state and affordances, not fake entities that act |
| Exact bridge failure and topology rules | Deterministic transition authority plus generic validation |
| Open worker intent | Luna through `llm_client` |
| Semantic action adjudication | Luna transition authority proposing a `WorldPatch` |
| Canonical-state mutation | Generic validator and atomic committer, never direct LLM mutation |
| Checkpoint/restore | Concordia-invoked lifecycle with a strict, lossless project codec for canonical world and evidence |
| Evidence | Typed transition evidence plus Concordia and `llm_client` trace references |
| Forbidden authority | Old CI runtime sessions, scenario-specific generated Python, narrator prose as truth, or a hidden second scheduler |

## Ordered work

### 27A — Define contracts and one semantic configuration

Implement only the contract fields needed by the stable example while keeping
the schema domain-neutral. Express the complete example in data. Register one
deterministic bridge/topology authority and one LLM semantic adjudicator.

**Pass:** no port-, outbreak-, organization-, or workflow-family class is needed
to assemble a valid world.

### 27B — Execute deterministic topology changes

Run the initial attempted delivery, reject traversal over the destroyed bridge,
then create the temporary depot and replacement route through validated patches.
Checkpoint and restore into a fresh simulation before the final action.

**Pass:** created topology and placements survive restore; corrupt or lossy state
fails visibly; neither old runtime session executes.

### 27C — Execute authentic open semantic action

Give Luna a bounded actor context and request an ordinary-language action. Pass
the resulting intent to the Luna transition authority. Validate and commit its
structured patch using generic rules.

**Pass:** the worker and truck reach the port without a pre-authored
`deliver_fuel`, `move_fuel_truck`, or equivalent scenario verb handler. Both
model calls have completed `llm_client` traces.

### 27D — Retain a human-reviewable execution artifact

Retain the initial world, actor context, action intent, proposed patch,
validation, committed patch, actor observation, checkpoint lineage, and model
trace references in one compact run artifact. No new public UI is required in
this slice.

**Pass:** a reviewer can distinguish what the actor selected, what the LLM game
master inferred, what the scenario author configured, and what the deterministic
validator allowed.

## Acceptance

| ID | Pass condition |
|---|---|
| P27-1 | Stock Concordia owns the outer entity/component, actor-selection, engine/game-master, and checkpoint invocation path |
| P27-2 | `CausalSession` and `ActiveRuntimeSession` do not execute on the new path |
| P27-3 | One domain-neutral composition contract instantiates the bridge/port world without scenario-specific Python |
| P27-4 | Dynamic depot/route creation and placement changes survive a fresh-instance restore |
| P27-5 | A corrupt, unsupported, or lossy checkpoint fails loudly |
| P27-6 | The actor never receives the hidden bridge-failure cause without a modeled information path |
| P27-7 | Luna proposes an open semantic intent whose action verb was not enumerated by the scenario |
| P27-8 | A declared Luna authority proposes a structured patch; generic validation owns commit or rejection |
| P27-9 | Invalid references, unauthorized writes, invalid topology/placement, and declared conservation violations are rejected without partial mutation |
| P27-10 | Retained evidence distinguishes authored configuration, actor choice, adjudicator inference, deterministic validation, and canonical outcome |
| P27-11 | Focused execution receipts include completed authentic Luna actor and adjudicator calls |

## Explicit uncertainties and stop conditions

These are not hidden acceptance claims for Slice 27.

| Uncertainty | Current status | Slice treatment |
|---|---|---|
| Safe live creation/removal of autonomous Concordia entities | Unknown | Defer; only inert world records are created dynamically. Stop if the example unexpectedly requires active-entity creation. |
| Dynamic component or transition-authority rebinding | Unknown | Configuration is fixed for this slice; record but do not generalize. |
| Simultaneous conflicting patches and transaction isolation | Unknown | Execute sequentially; do not claim concurrency semantics. |
| Atomic coordination across exact, LLM, and external simulators | Unknown | One authority per attempted transition in this slice. |
| Correct breadth of an LLM authority's read/write scope | Design-sensitive | Use the narrowest scope sufficient for the example and retain it in evidence. |
| General information noninterference | Not established | Prove only the named hidden-fact negative control; do not claim universal secrecy. |
| Universal versus scenario-declared invariants | Partly decided | Validate generic identity/topology/placement rules and explicitly declared conservation; do not invent a universal social ontology. |
| Coarse surrogate versus detailed subsystem double execution | Unresolved | No coarse surrogate in this slice; keep responsibility declaration in the contract. |
| Arbitrary prose-to-world authoring | Not established | Hand-author the semantic configuration; preserve the compilation seam for the next slice. |
| Cross-domain generality | Not established | Requires a materially different exemplar using the same contracts later. |
| Scale, latency, repeated-seed stability, and behavioral fidelity | Not tested | Defer; report exact call and runtime evidence only. |
| Concordia upstream API stability | Unknown beyond pinned source | Pin the tested revision and avoid private seams. |

Stop and return to the ADR if this vertical requires a private Concordia fork, a
second hidden runtime, scenario-specific generated Python, lossy checkpointing,
or direct unvalidated LLM state mutation. A failed Luna call is a provider/model
failure to report, not automatic evidence against the foundation.

## Non-goals

- migrating the outbreak demo, existing retained runs, or all public UI;
- implementing arbitrary conversational authoring;
- live creation/removal of autonomous actors;
- concurrent or distributed transactions;
- an exhaustive affordance, organization, trust, or social ontology;
- predictive validation or claims about real institutions;
- broad security, deployment, compatibility, or performance work; or
- deleting the existing runtime before an adopted consumer uses the new path.

## Verification budget

Use the focused bridge/port positive path, blocked-route negative path,
hidden-information negative control, invalid-patch tests, corrupt-checkpoint
test, and two authentic Luna calls. Run only directly relevant upstream
Concordia component/engine/checkpoint tests. Do not run broad suites or add a UI
before the vertical has been observed.

## Adoption requirement

Code and isolated tests establish implementation, not product adoption. The
next authorized slice must route one intended product consumer through these
contracts or explicitly retire the experiment. A bespoke scenario path that
bypasses the contract is a visible architecture violation, not an acceptable
shortcut.

## Required authority

- accepted [ADR-013](../adr/013-generalized-simulator-foundation.md);
- [current-source revisit and probe](../research/027-concordia-architecture-revisit.md);
- [Goal](../GOAL.md) and [roadmap](../ROADMAP.md); and
- explicit implementation authorization after this handoff.
