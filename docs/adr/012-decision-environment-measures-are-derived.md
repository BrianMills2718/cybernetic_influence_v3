---
doc_role: active_authority
authority: canonical
status: accepted
created: 2026-07-25
updated: 2026-07-30
---

# ADR-012: Decision-environment measures are derived

## Context

Waltzman's *From Minds to Coordination* proposes three useful dimensions for
analyzing collective decision environments: trust structure, perceived risk,
and coordination readiness. It argues that heterogeneous interactions may
produce a consistent directional change in these dimensions even when messages
and sources do not share a visible narrative.

These dimensions are useful analyst constructs, but the paper does not provide
validated scalar state variables or a causal update equation. Encoding a global
`trust`, `risk`, or `coordination` number as canonical world state and then
placing that number in every person's prompt would make the desired collective
effect true by construction. It would also reify the organization as a hidden
actor and obscure which concrete interactions produced the result.

## Decision

Trust structure, perceived risk, coordination readiness, and candidate
directional invariants are analyst projections over concrete retained evidence.
They are not universal canonical world variables and cannot directly execute,
authorize, deliver information, or change an agent.

The runtime continues to model:

- each person's fallible beliefs, memories, perceptions, goals, and current
  state locally;
- concrete information representations and deliveries;
- observable requests, commitments, delays, reopenings, withdrawals, and
  decisions;
- exact or explicitly coarse mechanisms that commit world effects; and
- execution-inert analytical boundaries over concrete components.

A measurement layer may derive a decision-environment readout from a retained
run-evidence bundle. The trace is one evidence source, not the definition of a
construct. The bundle may include:

- approved scenario configuration and analysis specification;
- initial, intermediate, and terminal world-state evidence;
- events and causal parents;
- information source, representation, ownership, lineage, and delivery;
- participant observations, attempts, and retained analytical output;
- mechanism decisions, commits, and rejections;
- analytical-boundary activity and coordination episodes;
- modeled timing, outcome, completion reason, and fidelity declarations; and
- run/model identity and integrity metadata.

Narrator prose is a presentation artifact and is not measurement source truth.

Every derived indicator must declare:

1. its construct and operational definition;
2. whether it is exact, calculated, or LLM-coded;
3. the configuration, event, state, representation, participant, boundary, or
   other retained evidence it uses;
4. its aggregation rule, direction, and uncertainty;
5. what passing the indicator does not establish; and
6. the version of the measurement specification that produced it.

LLM-coded indicators are typed analytical judgments. They must cite retained
analyst-visible evidence, retain their full `llm_client` trace, fail visibly on
invalid output, and never mutate the simulated world. The model generating a
trajectory must not silently grade the same trajectory as independent truth.

A single run may expose an indicator trajectory. It cannot establish an
invariant. A `candidate_directional_pattern` requires repeated trajectories,
an explicit baseline or counterfactual arm, subgroup/context reporting, and
uncertainty. The word `invariant` remains a paper-defined hypothesis until that
measurement contract is satisfied.

## Consequences

- A scenario can contain local trust judgments or perceived risks in a person's
  memory because those are properties attributed to that person.
- Aggregate trust fragmentation is calculated from concrete source reliance,
  verification, and acceptance evidence; it is not copied into people's minds.
- Coordination readiness is read from behavior such as decision latency,
  reopened issues, commitment divergence, and disengagement rather than from a
  hidden organizational mood.
- Scenario, run, analysis, and experiment specifications remain distinct.
  Measurement specifications are replaceable and versioned independently of
  scenario execution.
- A corrupt or failed analysis cannot invalidate or mutate an otherwise
  completed world run.
- Intervention comparisons can test whether configured policies, information
  routes, or feedback mechanisms change outcomes without inventing an
  organization-level executor.

This decision does not claim that the proposed indicators are empirically
validated, that the three dimensions are complete, or that they combine into a
single meaningful score. Calibration against real observations remains future
work.

## Source

[Coordination state-variable source note](../research/001-from-minds-to-coordination.md)
records the paper's definitions, proposed indicators, evasion dimensions, and
limitations. [ADR 006](006-boundaries-are-derived-coarse-grainings.md) governs
the related treatment of organizations and other aggregates.
