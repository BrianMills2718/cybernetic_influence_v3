---
doc_role: architecture_decision
authority: canonical
status: accepted
created: 2026-08-14
depends_on:
  - docs/adr/004-analyst-evidence-boundary.md
  - docs/adr/012-decision-environment-measures-are-derived.md
  - docs/adr/013-generalized-simulator-foundation.md
supersedes_in_part:
  - docs/plans/028-natural-language-general-simulation-demo.md
---

# ADR 014: Separate simulation execution from analytical purpose

## Context

The first general-world authoring vertical proved that ordinary language can
produce an editable world, compile through trusted component contracts, run on
stock Concordia, and retain an inspectable trajectory. It also collapsed four
different responsibilities into `GeneralSimulationProposalV1`:

1. the world and its causal possibilities;
2. the conditions and controls of one execution;
3. the analyst's question and selected theory lens; and
4. the assessment of whether a desired outcome occurred.

The coupling is not only documentary. The proposal's `question` is sent to
each simulated person as `research_question`. The joint transition authority
receives the same question and, in its final transition call, both proposes a
world mutation and assesses whether the research objective was achieved.
`material_to_question` also controls whether missing executable behavior blocks
compilation.

This conflicts with the earlier accepted separation of `ScenarioSpec`,
`RunSpec`, `AnalysisSpec`, and future `ExperimentSpec`. It can create demand
characteristics in simulated people, goal-conditioned transition adjudication,
and an unnecessary assumption that every simulation has one collective
research question.

## Decision

One conversational authoring experience may produce a convenient study bundle,
but the bundle compiles into separate versioned contracts:

```text
AuthoringConversation
  -> AuthoringInterpretation
       -> ScenarioSpec
       -> RunSpec
       -> zero or more AnalysisSpecs
       -> optional future ExperimentSpec

ScenarioSpec + RunSpec
  -> simulation runtime
  -> theory-neutral RunEvidence

RunEvidence + AnalysisSpec
  -> AnalysisResult
```

Physical co-location in one retained JSON document is permitted. Authority
co-location is not. The simulation runtime accepts only the scenario and run
contracts and therefore cannot inspect an analysis specification.

### Scenario authority

`ScenarioSpec` owns what exists and how it may change:

- people, private memories, behavioral profiles, capabilities, and limits;
- world records, resources, places, topology, representations, and provenance;
- active systems, transition contracts, patch grammars, and invariants; and
- fidelity assumptions and declared causal responsibilities.

An objective known to a simulated person is represented in that person's
memory or through an explicit information representation and delivery path. A
shared mission is not inserted into every person's prompt merely because the
analyst supplied it.

### Run authority

`RunSpec` owns one execution:

- scenario revision or starting checkpoint;
- scheduled exogenous injects and activation opportunities;
- time horizon and lifecycle termination conditions;
- model, reasoning, budgets, and execution mode; and
- seed or replay identity where supported.

A run may have no collective success condition. A condition that stops
execution belongs to `RunSpec` because it affects lifecycle. A condition that
only evaluates a completed trajectory is analytical and execution-inert.

### Analysis authority

`AnalysisSpec` owns a read-only request over retained evidence:

- construct and method definitions;
- required evidence kinds;
- aggregation, uncertainty, and limitations; and
- the requested output contract.

An analysis can be added, removed, or replaced after execution. It cannot add
actors, observations, schedules, mechanisms, actions, transitions, or world
state. Missing evidence produces an unsupported or degraded analysis result;
it does not silently modify the simulation to manufacture observability.

### Experiment authority

`ExperimentSpec` will own controlled variations, forks, repetitions, matching,
and cross-run comparisons. For example, targeted versus broadcast information
conditions are experiment configuration, while the Waltzman interpretation of
their retained effects is analysis. General experiment execution remains
outside this refactor, but the new contracts must preserve the seam.

### Transition and outcome assessment

The transition authority adjudicates actor intents and proposes a validated
world transaction. It does not judge whether the analyst's objective was
achieved in the same call. Post-run outcome assessment reads retained canonical
state and evidence through an exact, calculated, or explicitly LLM-coded
analysis method.

World constraints remain executable. A customs system rejecting an unsigned
manifest is a scenario mechanism, not analysis. A port director receiving a
delivery order is an information event, not analysis. The distinction is
whether the statement changes what can happen or what a simulated participant
can know, rather than whether an analyst finds it interesting.

### Materiality

Execution coverage uses causal and fidelity materiality, not materiality to a
research question. A requested behavior blocks approval when omitting or
describing it would invalidate the declared causal path or fidelity boundary.
Analysis coverage separately determines whether retained evidence can support
the selected analytical method.

### Representation

The causal configuration graph depicts only entities, information paths,
resources, capabilities, mechanisms, topology, and run events. Analytical
findings may be rendered later as a clearly labeled removable overlay. They are
not causal nodes in the configured world.

## Consequences

- The general authoring contract requires a versioned replacement rather than
  additive fields on `GeneralSimulationProposalV1`.
- The existing full `AnalysisSpecV1` seam remains the analysis capability owner;
  the simplified general-simulation `AnalysisSpecV1` is superseded.
- Retained V1 drafts and runs remain readable. New drafts write only the split
  contract. Any V1 re-execution compiles through one explicit adapter into the
  new contracts rather than retaining a second execution path.
- Run evidence no longer requires a selected analysis specification.
- Analysis results receive identities and digests separate from the run.
- Actor and adjudicator prompt fixtures must prove that analysis is absent.
- The public creation experience remains one conversation and one Configure
  action; users are not required to understand the internal contract names.

## Non-decisions

This ADR does not define a general experiment engine, add new theory modules,
calibrate human behavior, require separate database tables, or require migration
of immutable historical run bodies. It does not prevent an analyst, monitor, or
CSO from being simulated endogenously; such a participant must be declared in
the scenario with explicit observations and capabilities.

## Adoption proof

The decision is adopted only when one authentic general-world run establishes:

1. the runtime received only scenario and run contracts;
2. actor and adjudicator contexts contain no external analysis question or
   analysis specification;
3. adding Waltzman analysis after completion creates no simulation model calls
   and no canonical world revisions;
4. removing that analysis leaves scenario, run, context, and evidence digests
   unchanged; and
5. the public authoring and replay surfaces use the split path rather than a
   parallel compatibility implementation.
