---
doc_role: active_authority
authority: canonical
status: accepted
created: 2026-07-31
updated: 2026-07-31
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

## Authority boundaries

| Concern | Adopted authority |
|---|---|
| Entity cognition, memory, and planning | Concordia entities/components; provider calls route through `llm_client` |
| Simulation loop and actor selection | Concordia engine/game-master foundation |
| World and component state | Concordia component state, with exact typed state only where declared |
| Action interpretation | Concordia action seam plus reviewed parsers or structured components |
| Adjudication | Game-master resolution; deterministic components own declared hard rules |
| Time and scheduling | Concordia scheduling/time components, extended through public seams when needed |
| Checkpoint and continuation | Concordia checkpoint/component state; migration artifacts must fail on silent loss |
| Evidence and provenance | Concordia logs plus selected typed evidence projections required by the question |
| Authoring | Adapt the existing reviewed workflow to emit Concordia configuration/components |
| Analysis and UI | Adapt existing CI analysis and presentation over the new retained-run projection |

No component may claim predictive validity merely because its internal state is
exact. Exactness describes execution under assumptions, not correspondence to
the real world.

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
- The first proof reproduces the current physical-access behavior with
  Concordia actually executing it. The old causal/active runtime must not run
  behind the new surface.
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

## Execution gate

The replacement [Slice 27 handoff](../handoffs/027-foundation-implementation.md)
is a bounded design for the first Concordia-owned parity proof. Begin it only
after explicit implementation authorization.
