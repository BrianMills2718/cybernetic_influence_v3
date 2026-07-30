# ADR-006: Analytical Boundaries Are Reversible Derived Coarse-Grainings

## Status

Accepted — 2026-07-23; boundary-flow clarification accepted 2026-07-28;
observational-versus-experimental agency clarification accepted 2026-07-30.

## Context

The causal model already declares execution-inert analytical boundaries, but
the operator surface omits them. The exact graph therefore shows components
without letting an analyst inspect a higher-level system view. Inventing an
organization node with its own state, decisions, or actions would contradict
the model: the boundary is a chosen coarse-graining over grounded members, not
another actor.

A useful aggregate must also avoid false simplicity. Collapsing a boundary
hides member identities, internal routes, state facts, representations, and
event distinctions. If that loss is not visible and reversible, the aggregate
becomes a second narrative truth.

## Decision

Project each authored `AnalyticalBoundary` as a derived operator view:

- it never enters the active-system registry, owns an action interface, or
  executes a mechanism;
- its state at a revision is calculated from the analyst-safe member snapshot;
- incoming, outgoing, and internal routes are calculated from exact concrete
  connections;
- its trace is the ordered subset of canonical events focused on its members;
- its coarse graph node replaces member nodes only in boundary mode;
- every coarse node can step down to the exact member graph at the same event
  and state revision;
- the projection reports what the coarse view hides.

The canonical state, event log, and exact graph remain unchanged. Aggregate
identities are namespaced operator-view IDs and cannot collide with runtime
referents.

### Derived boundary activity and coordination episodes

At an analytical scale, a concrete routed effect crossing the selected
membership boundary is the observable input/output of the composite view:

- an exact `effect_routed` event whose source-port owner is outside and whose
  target-port owner is inside is a **boundary input**;
- the reverse is a **boundary output** and may be described in the UI as a
  derived composite-scale action;
- a routed effect whose endpoint owners are both inside is internal
  coordination; and
- an event whose endpoint owners are both outside is unrelated to that
  boundary.

This vocabulary does not make the boundary an executor. A boundary output is
the coarse description of an exact member/mechanism effect that crossed the
chosen boundary. It remains distinct from any downstream mechanism decision or
committed external outcome. The presentation must therefore show the output
attempt and its exact downstream result separately.

For each boundary output, a derived **coordination episode** follows exact
causal-parent links backward through boundary-relevant internal events until it
reaches the nearest boundary inputs, prior boundary outputs, or retained root
triggers. One output anchors one episode in the first contract; outputs are not
merged by timestamp, textual similarity, or an LLM judgment. Shared internal
ancestry may consequently appear in more than one episode. An input with no
downstream output at the selected causal position is shown as coordination in
progress. The exact internal path remains expandable.

Configured routes alone do not establish activity. Focus overlap, temporal
proximity, and narrative prose do not establish a crossing. The projector must
resolve endpoint owners from exact ports at the event's retained revision. A
member mechanism directly mutating nonmember-owned state is unsupported by this
first contract, even when the same execution also emits an outgoing effect. It
must fail the projection loudly rather than manufacture a boundary output or
external result; a separate outside mechanism owns the outside commit.

Analytical membership is not a spatial boundary. Entering a place, changing a
job, or changing an authorization does not become a boundary crossing unless a
separate reviewed analytical membership or spatial-boundary contract says so.
Nested and overlapping analytical boundaries remain deferred.

The current implementation partitions configured routes and retains member-
focused events but does not yet retain typed boundary crossings or coordination
episodes. Packet 21A2 is the first planned implementation; Slice 22 reuses it
without changing runtime authority. The projection may be recomputed from the
currently retained event prefix while a run is live; “analytical” does not mean
“available only after completion.”

## Deferred Research Question: Systemic Influence Without Reification

An aggregate need not be an additional executor or mind for the aggregate
scale to support a meaningful causal question. A future analyst may ask, for
example:

> To what extent was an outcome controlled by particular people, and to what
> extent was it controlled by the organizational or economic system in which
> they acted?

Here, “systemic influence” would not mean that an organization, state, market,
or capitalism secretly emitted an action. It would refer to the outcome
constraint produced by concrete distributed structures such as:

- policies, incentives, ownership, and resource-allocation rules;
- information topology, records, interfaces, and access controls;
- software, machines, and other exact or coarsely represented processes;
- selection, replacement, competition, and feedback dynamics that persist
  while individual participants change.

The claim that a system behaves like a powerful composite cybernetic agent can
therefore be treated as an operational hypothesis rather than an ontological
axiom. Evidence might include persistent objective-like regularities,
feedback, memory, error correction, adaptation, and outcome stability under
member replacement. The realized trajectory would still be generated only by
the system's concrete components.

A defensible influence comparison would require explicit counterfactuals:
vary the distributed structure while holding participant dispositions as
stable as practical; vary or replace participants while retaining the
structure; interrupt particular feedback paths; and measure which changes
alter the outcome distribution. “System versus humans” may not admit an
additive percentage because people and structures interact, so any future
attribution method must declare its intervention, scale, readout, and treatment
of interaction effects.

### Research Grounding and Deferred Measurement Contract

Michael Levin's TAME research program supplies a useful experimental framing,
not a ready-made organization-agency score. It treats a higher-scale Self as a
testable control model: a coherent system whose goal pursuit, compound memory,
and credit assignment occur at a scale unavailable to its parts alone. Its
relevant operational ideas are:

- an **axis of persuadability**: compare intervention strategies by the
  prediction and control obtained relative to the effort and detailed knowledge
  they require;
- a **cognitive light cone**: characterize the spatial, temporal, and
  state-space scope of outcomes a system can represent and work to change;
- **collective glue**: identify concrete communication, memory, and feedback
  mechanisms that bind component competencies into a larger control loop;
- **perturbation assays**: test whether a candidate collective restores an
  outcome after shocks, reaches it from varied starts, or retains it while
  members change.

This framing is grounded in biological work on distributed bioelectric control
of regeneration, where interventions can alter and reset persistent target
morphologies. Its direct empirical support is strongest in biology, not in
organizations or economies. Applying it to social systems is therefore a
future hypothesis, not a validated conclusion. Sources: [Levin,
2019](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2019.02688/full),
[Levin, 2022](https://www.frontiersin.org/journals/systems-neuroscience/articles/10.3389/fnsys.2022.768201/full),
[McMillen and Levin, 2024](https://www.nature.com/articles/s42003-024-06037-4),
and [Durant et al., 2017](https://pmc.ncbi.nlm.nih.gov/articles/PMC5443973/).

If a future scenario creates concrete pressure for this capability, its
measurement contract must name:

1. a candidate outcome or target variable without presuming a unified system
   intention;
2. the proposed aggregate boundary and its concrete control, memory, and
   feedback substrate;
3. component-level, structural, and feedback-disruption interventions;
4. repeated outcome distributions, including recovery after shocks and member
   replacement; and
5. an intervention-specific influence profile, not an unjustified additive
   percentage of “system” versus “human” causation.

The first plausible test of systemic influence is thus whether a structural
intervention—such as changing an incentive, policy, information route, or
market mechanism—redirects outcomes more reliably or efficiently than
individual-by-individual changes. That supports a useful higher-scale control
model; it does not add a hidden executor to the runtime or establish
consciousness.

### Coordination degradation as a composite-control perturbation

Waltzman's trust structure, perceived risk, and coordination readiness supply
candidate observations about the internal conditions under which a composite
control loop operates. They do not themselves establish agency. In a concrete
multi-person decision scenario, however, they can help explain why a candidate
boundary did or did not preserve its reviewed goal:

- fragmented trust can prevent error or evidence signals from being accepted;
- expanding perceived risk can change action thresholds or the set of states
  treated as errors; and
- degraded coordination can prevent distributed commitments from becoming a
  timely collective action.

One run can support an observational Levin-informed readout: candidate goal and
constraints, boundary inputs and outputs, collective glue, internal coordination
episodes, and any error correction, persistence, adaptation, or fragmentation
that actually occurred. Unobserved robustness, recovery, member replacement,
and persuadability remain `not_tested`.

A stronger composite-agency claim requires a later experimental layer. It may
compare matched component, structural, feedback, and shock interventions and
measure goal preservation, correction, recovery, rerouting, and
member-replacement robustness. A slow or cautious decision is not by itself
loss of agency: the goal specification must include the relevant validity and
safety constraints, not only speed or deployment.

The per-run MVP connection is specified in
[Slice 24](../plans/024-configurable-theory-analysis-mvp.md); the stronger
experimental connection remains in post-MVP
[Slice 22](../plans/022-composite-agency-perturbation-assay.md). Neither changes
this ADR's prohibition on aggregate executors or authorizes a scalar agency
score.

This ADR records the question but does not authorize organization-level
executors, agency scores, causal-attribution machinery, or a new MVP scenario.
Those require a concrete analyst question and a bounded measurement contract.

## Borrow Versus Build

Borrow the existing analytical-boundary contract, event focus identities,
event-time analyst snapshots, concrete route declarations, mechanism input
bindings, carrier ownership, and representation lineage. Build a small
server-side coarse projection and dependency-free SVG rendering because the
required behavior is one reversible grouping operation; a graph framework or
general ontology reasoner would add more hidden behavior than value here.

## Consequences

The same realization can be inspected at two scales without creating another
mind or world state. Aggregate claims remain mechanically traceable to exact
members and events.

This decision does not infer new boundaries, overlapping-boundary semantics,
causal emergence metrics, or organization-level agency. A future requirement
for overlapping/nested boundaries must supersede this ADR with explicit
composition rules.
