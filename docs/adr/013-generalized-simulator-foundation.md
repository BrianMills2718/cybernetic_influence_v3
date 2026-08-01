---
doc_role: active_authority
authority: proposed
status: proposed_awaiting_product_owner
created: 2026-07-31
updated: 2026-07-31
---

# ADR-013: Keep one Cybernetic Influence causal authority behind compatibility adapters

## Status

**Proposed; awaiting product-owner judgment.** This ADR does not authorize
implementation until the owner adopts, rejects, or revises it.

## Context

Cybernetic Influence has proven a typed causal runtime, multirate participant
execution, retained evidence, reviewed authoring, and analytical step-down. It
also owns bespoke cognition, composition, runtime, checkpoint, server, and
product machinery. Before expanding the component catalog, Slice 26 compared:

- A — Concordia as the foundation;
- B — Concordia cognition around a Cybernetic Influence environment;
- C — Cybernetic Influence as the foundation with compatibility adapters; and
- D — an independent Cybernetic Influence product without Concordia compatibility.

The comparison held the same product invariants and physical-access, hidden-
microphone, and heterogeneous-organization cases constant. The full source
audit, capability matrix, walkthroughs, and migration dispositions are in the
[Slice 26 research record](../research/026-foundation-comparison.md).

Concordia supports exact Python component state and is not disqualified by its
natural-language defaults. Its stock agent seam, resolution, observation,
scheduling, checkpoint, and logging semantics do not, however, own the typed
causal distinctions required by this product. Making Concordia foundational
would require replacing those recurring authorities. Keeping Concordia as a
privileged cognition layer would preserve the causal core but create a second
component and checkpoint lifecycle before a concrete component justifies it.

## Proposed decision

Choose **C — Cybernetic Influence foundation with compatibility adapters**.

One Cybernetic Influence causal session remains authoritative for world state,
modeled time, scheduling, routing, exact adjudication, committed effects,
observations, lineage, checkpointing, replay, and retained evidence. Analytical
boundaries and Waltzman-/Levin-informed measures remain derived views over that
evidence.

Retain the existing provider-neutral `ActiveSystemImplementation` protocol as
the participant-cognition port. A cognition implementation:

1. receives only the authorized, typed participant input selected by the causal
   runtime;
2. may interpret that input, update explicitly checkpointed private cognition
   state, and propose a reviewed typed intent;
3. cannot mutate canonical world state, schedule work, deliver observations, or
   adjudicate success; and
4. fails visibly when it cannot produce a valid proposal.

Native participant implementations already use this port. Concordia-compatible
entities may be hosted through an optional adapter at the same boundary.
Concordia's engine, game master, scheduler,
checkpoint, and log do not become product authorities. All provider-backed
cognition continues through shared `llm_client`.

`data_contracts.composition` is an eligible **compile-time** substrate, not a
runtime. Do not migrate Slice 25 contracts yet. First prove a narrow projection
that preserves causal declarations and reduces duplicate validation; Cybernetic
Influence continues to own implementation discovery, effects, state,
scheduling, evidence, persistence, and replay.

## Authority boundaries

| Concern | Authority |
|---|---|
| Cognition, private memory, planning | Existing `ActiveSystemImplementation` and versioned `ActiveSystemState.private_state` |
| Natural-language interpretation | Cognition adapter producing a validated typed proposal |
| Canonical world state and time | Cybernetic Influence causal/active runtime |
| Capability, permission, and success | Cybernetic Influence mechanisms and declared invariants |
| Observation selection and information lineage | Cybernetic Influence routing and representations |
| Checkpoint, replay, and evidence | Cybernetic Influence retained run; adapter state is an explicit payload |
| Scenario authoring and runtime implementation selection | Cybernetic Influence compiler/registry until a separate contract decision |
| Analysis and aggregate boundaries | Derived Cybernetic Influence views over retained lower-level evidence |

## Strongest rejected alternative

**B — Concordia cognition around a Cybernetic Influence environment** is the
strongest alternative. It preserves one world authority and offers immediate
access to Concordia's component lifecycle, memory, and social cognition. It is
not selected because every participant would cross Concordia's string action
seam, the product would carry two component/state/checkpoint lifecycles, and
Concordia/provider upgrades would become architectural coupling. Candidate C
can add the same concrete reuse through an optional adapter after its value is
demonstrated, without imposing it on native or non-LLM participants.

## Other rejected alternatives

- **A — Concordia foundation:** rejected because preserving the fixed causal,
  visibility, evidence, and replay invariants repeatedly replaces Concordia's
  engine-level ownership. The result would be a nominal Concordia foundation
  around a second product engine.
- **D — independent product:** viable and authority-clean, but rejected because
  refusing a compatibility boundary would unnecessarily make future cognition
  ecosystem reuse and interoperability product-specific.

## Consequences if adopted

- Existing causal state, runtime, retained runs, checkpoints, and analysis stay
  authoritative and require no migration.
- The first implementation increment is a smaller-than-rewrite
  Concordia-compatible adapter vertical through one canonical provider-free
  scenario; it does not create a second cognition abstraction.
- The exact Concordia pin is confined to an optional adapter/test boundary; a
  minimal provider-free entity proves compatibility without adopting the
  Concordia engine or granting it runtime authority.
- Invalid cognition output remains an explicit failed proposal; no productive
  fallback silently mutates the world.
- A materially different scenario, rather than additional variants of the
  current family, remains the test of generalized composition.
- This decision does not close the separate MVP stakeholder-comprehension gate
  or establish empirical validity.

## Adoption gate

The product owner must choose one of:

1. adopt Candidate C as written and authorize the Slice 27 handoff;
2. select Candidate B and request a revised authority/handoff packet; or
3. reject the framing and name the product tradeoff requiring more research.

Until then, Slice 27 is `awaiting_owner_adoption` and product implementation is
stopped.
