---
doc_role: active_authority
authority: canonical
status: accepted
created: 2026-07-31
updated: 2026-08-11
supersedes: proposed Candidate C revision at e8429b0e2e769931e8d211262d70fc48bc5032da
---

# ADR-013: Use Concordia as the generalized simulation foundation

## Status

**Accepted by the product owner on 2026-07-31.** Architecture adoption does not
by itself authorize product implementation or deployment.

## Context

Slice 26 compared four foundations:

- A — Concordia as the foundation;
- B — Concordia cognition around a Cybernetic Influence environment;
- C — Cybernetic Influence as the foundation with compatibility adapters; and
- D — an independent Cybernetic Influence product.

The [source audit and same-case comparison](../research/026-foundation-comparison.md)
recommended Candidate C under a frozen contract that treated every current
Cybernetic Influence invariant as non-negotiable. The product owner then
clarified the higher-level objective:

- build a generalizable simulation system for bounded socio-technical worlds;
- treat wargaming, economic modeling, organizational analysis, and similar
  domains as exemplars rather than the product definition;
- optimize fidelity as useful structure, decisions, mechanisms, information,
  and inspectability under declared assumptions; and
- do not claim that generated trajectories predict chaotic socio-technical
  systems or supply real-world probabilities without separate calibration.

That clarification changes the product tradeoff. Cybernetic Influence's exact
runtime guarantees improve internal consistency and auditability, but
preserving all of them as foundational requirements risks maintaining a second
simulation framework and restricting exploratory breadth. Existing code is
evidence and a parity baseline, not a sunk-cost reason to retain its runtime.

## Decision

Choose **A — Concordia foundation**.

Concordia owns the primary simulation lifecycle:

- entity identity, private component state, memory, cognition, and action;
- environment/game-master control and action resolution;
- simulated-time and actor-selection policy;
- component assembly and state restoration; and
- the foundation checkpoint/log lifecycle.

Cybernetic Influence does not remain as a hidden authoritative environment
behind Concordia. Selected capabilities may migrate when they add observable
value:

- exact deterministic components for hard rules and constrained state;
- distinctions among capability, permission, attempt, adjudication, and
  realized outcome where the modeled question requires them;
- information-copy lineage and selective causal provenance;
- spatial, configured-pathway, and realized-event projections;
- reviewed conversational authoring and compilation;
- retained-run inspection, replay, maps, narration, and comparison surfaces;
- analytical boundaries and Waltzman-/Levin-informed analysis; and
- shared `llm_client` invocation and retained model-call evidence.

Typed state is question-relative. A component should be exact where a modeled
constraint or analytical question needs exactness. Narrative or explicitly
coarse state is acceptable elsewhere. Exact components must use Concordia's
public component/state seams rather than recreating `CausalSession` or
`ActiveRuntimeSession` as a second engine.

### 2026-08-11 boundary clarification

The [current-source and bridge/port revisit](../research/027-concordia-architecture-revisit.md)
reaffirms Candidate A and makes its internal boundary explicit.

Concordia owns the **outer simulation lifecycle**. A project-owned canonical
world is implemented as one or more public game-master components. That world
component may contain typed entities, things, places, representations,
resources, topology, placements, active-system bindings, and evidence. It is
not a second engine while Concordia still owns actor invocation, turn/moment
progression, component lifecycle, and the call into game-master resolution.
Calling the old causal/active runtime behind the component remains forbidden.

The standard transition path is:

```text
canonical world truth
-> actor-authorized context or observation
-> open semantic action intent
-> declared transition authority
-> structured world patch proposal
-> generic references, authority, topology, information, and declared invariant checks
-> atomic commit or visible rejection
-> actor-specific observation and retained evidence
```

A transition authority may be deterministic, stochastic, LLM-adjudicated,
externally simulated, scripted, or replayed. Every authority declares what it
may read and write, its fidelity/assumptions, and invalid questions. An LLM game
master is therefore a legitimate first-class coarse transition authority, not
merely a fallback, but it never writes canonical state without a validated
patch commit.

Concordia entities are used for autonomous or externally driven processes. An
inert truck, bridge, computer, record, route, or resource normally remains a
canonical-world record with affordances and state; it does not receive a fake
`act` lifecycle. A coarse organizational surrogate may be an active entity
when the internal machinery is intentionally out of resolution. It may not
independently duplicate the causal function of a simultaneously active detailed
representation.

## Authority boundaries

| Concern | Adopted authority |
|---|---|
| Entity cognition, memory, and planning | Concordia entities/components; provider calls route through `llm_client` |
| Simulation loop and actor selection | Concordia engine/game-master foundation |
| World and component state | Concordia component state, with exact typed state only where declared |
| Action interpretation | Open semantic intents through project-owned structured components; scenario-specific verb enumeration is not the general seam |
| Adjudication | A declared transition authority proposes a structured patch; generic validation and the canonical-world component own commit |
| Time and scheduling | Concordia scheduling/time components, extended through public seams when needed |
| Checkpoint and continuation | Concordia-invoked checkpoint/component lifecycle with a strict lossless canonical-state codec; stock silent dropping is not acceptable |
| Evidence and provenance | Concordia logs plus typed context, intent, proposed patch, validation, commit, observation, and selected causal projections |
| Authoring | A general world-composition contract binds only registered components/authorities; convenience templates compile into the same contract |
| Analysis and UI | Adapt existing CI analysis and presentation over the new retained-run projection |

No component may claim predictive validity merely because its internal state is
exact. Exactness describes execution under assumptions, not correspondence to
the real world.

### Automatic presentation adoption

Replay is a runtime projection contract, not scenario-specific UI work. Every
completed run must automatically appear in the retained-simulation catalogue
and receive the same progressively disclosed replay from its canonical graph,
retained events or rounds, decisions, and outcome. Node and edge keys are
derived from the types present in that projection. A specialized case-study
page may add interpretation, but it may not be the only way to inspect a run.

Adding a new scenario must not require a new results page or hand-authored
walkthrough. Unknown canonical entity kinds remain visible through a generic
object presentation until a reusable visual-family mapping is registered;
they do not silently disappear. Adoption is proven by opening a newly retained
run through the shared catalogue and replay renderer, not merely by unit-testing
the projector in isolation.

## Strongest rejected alternative

**C — Cybernetic Influence foundation with compatibility adapters** best
preserves existing behavior and minimizes migration risk. It was the Slice 26
technical recommendation. It is rejected as the product foundation because it
makes Concordia an optional edge around a bespoke runtime, while the adopted
goal values a broader simulation ecosystem and accepts selective rather than
universal causal typing.

Candidate C remains the fallback if the first Concordia-owned parity proof
cannot reproduce a current capability without embedding the old runtime or
losing behavior the product owner judges indispensable.

## Other alternatives

- **B — Concordia cognition around a CI environment:** rejects the migration
  risk of A but permanently carries two lifecycle/state/checkpoint models. It
  is not selected unless the parity proof demonstrates that a separate exact
  environment is indispensable.
- **D — independent CI product:** retains maximum local control but gains the
  least ecosystem leverage and does not address the maintenance concern that
  motivated the decision.

## Migration consequences

- Existing retained runs, traces, analyses, and screenshots remain historical
  evidence and the behavioral parity baseline. They are not rewritten.
- Existing code is classified capability by capability as `reuse_unchanged`,
  `adapt`, `replace`, or `retire`; no repository-wide rewrite is authorized.
- `data_contracts.composition` remains an optional compile-time authoring
  substrate. It is not a runtime authority and is deferred until authoring
  migration presents a concrete duplication or validation problem.
- The first proof now exercises the general bridge/port world-context-intent-
  patch path with Concordia actually executing it. The old causal/active runtime
  must not run behind the new surface. Physical access remains a later exact-
  mechanism parity case rather than the foundation's first discriminating test.
- Broader parity work begins only after that proof. Cross-domain generalization
  begins only after current public capabilities have an explicit disposition.
- A materially different exemplar must reuse the same authoring and execution
  seams before the product claims generality.
- Wargaming may be that later exemplar, but it is not privileged in the core
  architecture.
- The separate MVP stakeholder-comprehension judgment remains open and is not
  closed by this decision.

## Non-claims

This decision does not establish that Concordia is empirically predictive,
that every Cybernetic Influence feature should be ported, that exact components
increase real-world accuracy, or that one successful scenario proves a
generalized simulator.

It also does not establish live autonomous-entity creation/removal, dynamic
component rebinding, general simultaneous-patch conflict semantics, general
information noninterference, reliable LLM adjudication, cross-domain authoring,
scale, or behavioral fidelity. The evidence record separates what the current
source proves, what the bridge/port probe indicates, and what remains unknown.

## Execution gate

The amended [Slice 27 handoff](../handoffs/027-foundation-implementation.md) is
a bounded design for the first general Concordia-owned world/transition
vertical. Begin product implementation only after explicit implementation
authorization; the disposable architecture probe is not production adoption.
