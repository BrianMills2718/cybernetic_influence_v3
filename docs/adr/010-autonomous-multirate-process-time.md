# ADR 010: Autonomous Multirate Process Time

**Status:** Accepted and implemented for the Service Desk and
purchase-to-payment MVP probes — 2026-07-23. Amended 2026-07-25 to require
positive elapsed time across world-event causal links.

## Decision

An agent is an ongoing stateful process, not a function invoked only by incoming
messages. Its state may change because of perceptions, retained intentions,
ongoing activity, elapsed time, or other internal dynamics. The scheduler must
not infer inertness merely from the absence of a newly delivered observation.

Scenario time, causal time, process updates, causal moments, and exact events
are distinct:

- scenario time is an integer clock in a scenario-declared base unit and may
  remain unchanged when no elapsed duration is modeled;
- causal time is a strictly increasing integer assigned once to each successive
  causal moment;
- a process update advances one stateful entity according to its own dynamics;
- a causal moment batches everything due together against one frozen
  pre-moment state and has a unique timestamp such as `c2`;
- exact events retain attempts, mechanism decisions, deliveries, and commits
  within that moment, with stable trace positions such as `c2.1` and `c2.2`.

Exact-event trace positions provide total replay order. They do not create a
causal edge between otherwise independent events: explicit causal-parent links
remain the authority for what caused what, and same-moment participants still
cannot observe one another's proposals.

Every process may produce `next_update_at`; every delayed effect or observation
has `arrives_at`. The simulator jumps to the earliest due timestamp and updates
the due set. Those fields use the scenario clock, while the committed activation
ledger supplies the independent causal clock. Scenario-clock divisions are
arbitrary integer multiples of the scenario unit, not powers of two. A fine
clock resolution orders fast effects but does not require an LLM call at every
representable instant.

## Positive-Duration World Causality

Every retained world event that is a causal consequence of another retained
world event must occur at a strictly later scenario time than its parent.
Independent events may complete at the same time, and siblings produced from
one prior state may share a completion time, but a descendant may not collapse
onto its ancestor's timestamp.

This applies to modeled cognition/action completion, transmission, mechanism
transitions, movement, and observation availability. A duration may be very
small relative to another process, but it must be positive at the scenario's
declared temporal resolution. A container crossing an ocean and a spoken
greeting therefore cannot become temporally equivalent merely because both are
represented as one scheduler step.

Simulator bookkeeping—database writes, ID allocation, indexing, serialization,
and trace formatting—is not a world event and consumes no scenario time. It
must not appear as an extra causal node merely to satisfy the timing invariant.

A duration is optional while a scenario is being drafted, but mandatory before
a world transition crosses the runtime scheduling boundary. Resolution uses
the narrowest applicable source:

1. an exact mechanism calculation, such as path length and speed;
2. a typed scenario value or distribution, whether supplied by a human or a
   scenario-authoring model; or
3. bounded runtime LLM adjudication when context makes the duration genuinely
   underspecified.

The resolved activity retains its start time, positive duration, due time,
source kind, source reference, and causal parents. Missing, zero, negative,
past-due, or untraceable duration data fails before the world transition is
scheduled.

## Multirate Agency

Processes evolve at their own meaningful rates. A matching engine may transition
in microseconds, an automated controller in milliseconds, and a human decision
process over seconds or hours. They share one temporal substrate without sharing
one invocation frequency.

Fast known behavior belongs in exact mechanisms or conventional controllers.
An LLM may configure a bounded contingent controller and reconsider it when a
material condition or scheduled boundary occurs; it should not narrate every
micro-transition. Agents due at the same timestamp may decide concurrently from
the frozen state in one causal moment. A later moment receives a strictly later
causal timestamp even when the scenario clock has not advanced.

Conceptually every stateful process advances with elapsed time. Computational
evaluation may be skipped only when the process contract establishes that no
observable state transition can occur before its scheduled update. Selective
activation is therefore a semantics-preserving optimization, not the source of
agency.

## Concrete Consequences

- Agents can act or revise intentions without an external signal.
- An activation records its cause: delivered input, internal wake, ongoing
  activity completion, or scenario/exogenous event.
- An agent may act now, continue an activity, schedule reconsideration, or
  become dormant without a pending wake.
- Multiple due agents remain separate participants in one atomic causal moment.
- Legacy zero-time cascades remain bounded until migrated; under the amended
  contract, new world-event causal links with zero duration fail before
  scheduling.
- Organizations, regulations, incentives, and procedures do not gain autonomous
  clocks. Concrete people, documents, records, software, and mechanisms change;
  organizational-scale dynamics are derived from those changes.

## Implemented MVP Boundary

V0.10 adds integer scenario time, `next_update_at`, recorded observation arrival
times, explicit activation causes, and due-set scheduling to the Service Desk.
The representative trajectory includes a human internal wake with no new
observation and a three-phase exact remediation process with no model calls.
The exact trace, replay, budgets, causal graph, participant inspector, and
sequential narration retain the simulated time and reason for each activation.
The analyst projection additionally assigns unique causal timestamps to moments
and exact-event substeps. Service Desk scenario time is currently expressed as
uncalibrated `process_tick` values, not real-world seconds.

V0.12 applies the same scheduler to purchase-to-payment. Only the requester is
an authored `scenario_start`; the approver and AP clerk become due from
unconsumed delivered observations, and the runner stops at quiescence. Its
legacy zero-delay routes preserve causal ancestry while leaving elapsed
workflow latency explicitly unmodeled. Its moments nevertheless have unique
causal timestamps. These routes must be migrated before that scenario can claim
the amended positive-duration contract.

The causal core now retains delayed future effects and deliveries across
checkpoints and can settle exact-only work between participant activations.
The remaining work is to require and source positive durations for every
world-event transition rather than preserving zero-delay causal cascades.

Do not yet add continuous-time solvers, speculative parallel execution,
rollback, generalized process algebra, automatic attention models, or a
universal library of clocks.
