# ADR 010: Autonomous Multirate Process Time

**Status:** Accepted direction — 2026-07-23. Implementation planned.

## Decision

An agent is an ongoing stateful process, not a function invoked only by incoming
messages. Its state may change because of perceptions, retained intentions,
ongoing activity, elapsed time, or other internal dynamics. The scheduler must
not infer inertness merely from the absence of a newly delivered observation.

Simulation time, process updates, causal moments, and exact events are distinct:

- simulation time is an integer timestamp in a scenario-declared base unit;
- a process update advances one stateful entity according to its own dynamics;
- a causal moment batches everything due at one timestamp against one frozen
  pre-moment state;
- exact events retain attempts, mechanism decisions, deliveries, and commits
  within that moment.

Every process may produce `next_update_at`; every delayed effect or observation
has `arrives_at`. The simulator jumps to the earliest due timestamp and updates
the due set. Timestamp divisions are arbitrary integer multiples of the
scenario unit, not powers of two. A fine clock resolution orders fast effects
but does not require an LLM call at every representable instant.

## Multirate Agency

Processes evolve at their own meaningful rates. A matching engine may transition
in microseconds, an automated controller in milliseconds, and a human decision
process over seconds or hours. They share one temporal substrate without sharing
one invocation frequency.

Fast known behavior belongs in exact mechanisms or conventional controllers.
An LLM may configure a bounded contingent controller and reconsider it when a
material condition or scheduled boundary occurs; it should not narrate every
micro-transition. Agents due at the same timestamp may decide concurrently from
the frozen state. Causally dependent updates at later timestamps remain ordered.

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
- Zero-time cascades and self-scheduling loops remain bounded and fail loudly.
- Organizations, regulations, incentives, and procedures do not gain autonomous
  clocks. Concrete people, documents, records, software, and mechanisms change;
  organizational-scale dynamics are derived from those changes.

## MVP Boundary

The next temporal slice should add only integer simulation time,
`next_update_at`, `arrives_at`, activation causes, and due-set scheduling to one
existing scenario. It should retain the current exact trace and narration
step-down.

Do not yet add continuous-time solvers, speculative parallel execution,
rollback, generalized process algebra, automatic attention models, or a
universal library of clocks. The current observation-triggered Service Desk
remains usable until this bounded replacement is implemented.
