---
doc_role: implementation_handoff
authority: proposed
status: awaiting_owner_adoption
created: 2026-07-31
updated: 2026-07-31
depends_on: docs/adr/013-generalized-simulator-foundation.md
---

# Slice 27 handoff: Concordia-compatible cognition adapter

## Gate

**Do not execute this handoff until the product owner adopts ADR-013 Candidate
C.** If the owner selects Candidate B or revises the authority boundary, replace
this handoff before implementation.

## Outcome

Add one narrow Concordia `Entity` implementation of the existing
`ActiveSystemImplementation` protocol and run the canonical physical-access
vertical through a minimal provider-free entity using the pinned Concordia API
without changing world behavior, evidence, checkpoint, or replay. The adapter
translates authorized observations and a free-form action without granting the
entity world authority.

The user-visible behavioral example remains: Alice attempts equipment-room
entry; authentication, authorization, latch success, traversal, elapsed time,
and explaining evidence have the same outcome before and after the port.

## Scope

### 27A — Freeze the adapter mapping

Do not create a new cognition protocol. Record the exact mapping between the
existing `ActiveSystemInput`/`ActiveStepResult` contract and the pinned
Concordia `Entity` API: `observe(str)`, `act(ActionSpec) -> str`, `get_state`, and
`set_state`. The adapter must:

- accept the current typed participant input, including only observations the
  runtime already authorized;
- return the existing strict typed proposal/result shape without loss;
- restore and snapshot JSON-serializable entity state through the existing
  versioned active-system private-state envelope;
- retain no authoritative entity state between `step` calls; reconstruct or
  reset from the supplied private state so checkpoints remain the sole
  continuation authority;
- receive no mutable `CausalState`, scheduler, mechanism registry, run store, or
  observation router; and
- surface invalid output as a typed failure with retained context.

Confine the exact immutable Concordia pin to an optional adapter/test boundary;
product execution must not depend on Concordia's engine or component lifecycle.
Do not generalize authoring or component composition in this slice.

### 27B — Implement the compatibility adapter

Implement one `ActiveSystemImplementation` adapter that renders only the
supplied authorized observations/action surfaces, restores the compatible
entity's private state, obtains one free-form action, parses one reviewed action
grammar, and returns an `ActiveStepResult` with the new private-state snapshot.
Unknown or ambiguous text must fail visibly. Do not add another generic
framework layer.

### 27C — Preserve the physical-access vertical

Create a minimal provider-free test entity against the actual pinned Concordia
`Entity`/`ActionSpec` API. The adapter routes Alice's physical-access
participant through that entity. Do not instantiate a Concordia engine, game
master, scheduler, server, or language model.

Show that terminal state, authentication/authorization/latch/traversal
decisions, modeled time, attempt/decision/commit/observation evidence,
checkpoint, and replay match the current provider-free behavior.

The negative control is mandatory: an unknown, ambiguous, or invalid string
must produce an explicit retained participant failure and no world mutation.
Do not add Concordia as a runtime dependency, call an LLM, or implement its
engine/component lifecycle.

## Acceptance

| ID | Pass condition | Evidence |
|---|---|---|
| C27-1 | The adapter implements the existing active-system protocol; no second cognition abstraction is added | Contract/source review and type tests |
| C27-2 | The physical-access outcome and causal evidence are unchanged through the compatibility adapter | Focused before/after fixture or golden assertion |
| C27-3 | Checkpoint/restore carries the compatible entity state in the existing versioned private-state envelope, the adapter retains no second state, and execution resumes deterministically | Focused round-trip and fresh-adapter restore test |
| C27-4 | A minimal entity using the pinned Concordia API receives only authorized observations/action surfaces and yields one valid typed proposal | Adapter test with exact captured inputs/output |
| C27-5 | Invalid free-form output fails visibly and commits no causal effect | Negative-control trace and state equality assertion |
| C27-6 | The immutable Concordia dependency is confined to the optional adapter/test boundary; no Concordia engine/game-master/scheduler/server, live model call, component expansion, UI work, or retained-run migration enters the slice | Dependency/diff review |

Run focused tests for the changed participant/runtime/checkpoint boundaries and
inspect the exact full retained trace. Broad unrelated suite debt is not a gate.

## Non-goals

- adopting Concordia's engine/component lifecycle or `data_contracts.composition`;
- replacing or wrapping the existing active-system protocol with another port;
- changing the causal engine, scheduler, observation router, or analysis;
- adding a new scenario/component family;
- provider-backed cognition or model-quality evaluation;
- migrating historical runs; or
- completing the separate MVP stakeholder-comprehension judgment.

## Stop conditions

Stop and return to architecture judgment if the adapter needs a second world
state, lets cognition mutate or schedule the world, cannot checkpoint private
state without silent loss, requires generated executable code, creates another
cognition abstraction, or changes the physical-access result/evidence to
accommodate the adapter.

## Required authority

- [ADR-013](../adr/013-generalized-simulator-foundation.md), adopted rather than
  proposed;
- [Slice 26 research](../research/026-foundation-comparison.md);
- [Goal](../GOAL.md) and [roadmap](../ROADMAP.md); and
- the nearest canonical project instructions before editing.
