# ADR 009: Causal Moments, Not Round-Robin Turns

**Status:** Superseded in part — 2026-07-23 by
[ADR 010](010-autonomous-multirate-process-time.md).

The causal-moment batching, frozen participant set, narration, and forensic
activation semantics remain accepted. External-observation-only activation and
quiescence are transitional V0.9 behavior, not the target temporal model.

## Decision

The primary simulation-time unit is a causal moment. A scenario supplies the
initial trigger; after that, every active system with at least one newly
delivered observation participates in the next moment. All participants receive
inputs projected from the same frozen pre-moment checkpoint. Their individual
proposals remain separately retained beneath one atomic activation-set record.

The narrator receives the complete analyst-visible trace for that activation
set plus the earlier moment narratives and produces one evidence-cited account.
The main UI calls these causal moments. It reserves “activation” for forensic
participant records and does not call either one a turn.

The closed Service Desk fidelity-report harness retains its original fixed
nine-activation schedule because its microstate comparison contract is indexed
to that schedule. The user-facing simulator uses the event-driven scheduler.

## Why

A fixed triager-specialist-supervisor rotation gave people opportunities to
reconsider the world without a causal trigger, delayed reactions until an
arbitrary slot, and made the narration look like a one-agent board game. It also
hid the runtime's existing ability to collect several decisions from one frozen
state.

Event triggering better represents bounded sensors and attention without
forcing every person to act at every clock tick. Grouping simultaneous
participants prevents the narrator from inventing an order between decisions
that were made from the same state.

## Invariants

- Spatial adjacency does not trigger cognition or deliver information.
- A declared, newly delivered observation may trigger its owning active system.
- Participants in one moment cannot observe another participant's same-moment
  proposal.
- Exact mechanisms, not the narrator or UI, decide and commit world effects.
- Mechanism execution may be canonically ordered for replay; that order must not
  be misrepresented as an observed decision order.
- Quiescence—no pending delivered observations—ends the scenario.
- A scenario-level moment bound fails loudly instead of allowing an observation
  loop to spend indefinitely.

## Deferred

Internal clocks, spontaneous reconsideration, continuous processes, exogenous
events, priority queues, and conflict policies richer than the runtime's
canonical proposal application order were deferred in V0.9. ADR 010 now accepts
internal autonomous updates and multirate scheduled time as the next temporal
substrate while continuing to defer continuous solvers and generalized conflict
languages.
