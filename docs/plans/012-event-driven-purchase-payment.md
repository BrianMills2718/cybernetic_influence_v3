---
doc_role: active_executable_plan
authority: scoped
status: proposed
created: 2026-07-23
updated: 2026-07-23
predecessor: 011-purchase-payment-representation-boundary.md
---

# Slice 12: Event-Driven Purchase-to-Payment Causal Chain

**Status: Proposed and ready for review; implementation has not started.**

## Outcome

For an analyst studying multiscale agency, the purchase-to-payment scenario
should unfold because concrete people receive information and become due—not
because the scenario runner manually gives each person a turn. The existing
map, narratives, participant traces, exact mechanisms, and analytical
boundaries must show why and when every process activated.

This is a representative vertical of the same analyst job as the canonical
Service Desk probe. It extends autonomous scheduling to a second scenario while
preserving the purchase scenario's distinct representation-depth question.

## Current and Target Delta

Current behavior:

- `run_purchase_payment` directly activates requester, approver, AP clerk, and
  AP clerk again at authored times 0–3;
- every retained cause is `manual_schedule`;
- the underlying observation ports already correspond to the intended causal
  handoffs;
- `ActiveRuntimeSession.next_due_activation()` already derives the earliest
  observation/internal-wake set and is proven in Service Desk.

Target behavior:

1. The scenario explicitly starts only the requester at time 0 with
   `scenario_start`.
2. The requester submission produces the review package that makes the
   approver due.
3. The recorded approval or denial makes the AP clerk due.
4. A settlement, decline, or gate denial makes the AP clerk due for a final
   observation-only update when such feedback exists.
5. The runner stops at quiescence and fails loudly at a scenario-local causal
   moment bound.
6. No purchase activation is labeled `manual_schedule`.

## Frozen Representative Trajectories

The scenario retains `minute` as its declared integer time unit but does not
invent elapsed latency. Existing purchase connections remain zero-delay.
Positive and declined paths therefore retain four causally ordered moments at
logical time 0. Equal timestamps mean that elapsed workflow latency is omitted
at this representation depth; they do not claim that real people or systems act
literally simultaneously.

Moment order remains inspectable through causal ancestry and activation
sequence. A later scenario may author nonzero connection delays only when the
analyst question and a defensible timing assumption require them.

Expected arm behavior:

| Condition | Causal development | Terminal readout |
|---|---|---|
| `settled` | requester start → delivered review → delivered approval → delivered settlement | settled |
| `approval_denied` | requester start → delivered review → delivered denial; AP clerk remains silent | approval denied; processor never executes |
| `processor_declined` | requester start → delivered review → delivered approval → delivered decline | processor declined without invented cause |
| mismatched documents | requester start → exact intake rejection → quiescence | submission rejected; no later person call |
| forced request after denial | delivered denial triggers the test policy's invalid attempt → exact gate denial | gate denied; processor never executes |

## Target Derivation

| Target behavior | Required source/state | Owning operation | Contract | Acceptance |
|---|---|---|---|---|
| One authored start | requester's retained request | purchase runner | `ActivationCause(kind="scenario_start")` | only requester has a scenario-start cause |
| Causal continuation | unconsumed delivered observations | active runtime | `next_due_activation()` | later participants activate only when due |
| Honest temporal readout | causal ancestry with no calibrated latency | active runtime and presentation | moment order plus logical time 0 | no fabricated elapsed-time claim |
| Dormancy without work | no observation and no retained wake | active runtime quiescence | `next_due_activation() -> None` | mismatch stops after intake rejection |
| Spend containment | variable number of due people/moments | runtime and narrator budgets | existing per-call/run caps plus moment bound | no unnecessary live call after quiescence |
| Understandable evidence | retained cause/time/trace | presentation and narrator | existing analyst document | UI says scenario start or observation delivery |

## Boundaries and Owned Rules

### Purchase scenario

Owns the initial requester trigger and a maximum of eight causal moments. It
does not decide who is due after the first moment or fabricate route latency.

### Active runtime

Owns unconsumed-observation detection, earliest timestamp selection, frozen due
sets, activation causes, private-state updates, spend enforcement, and
quiescence. Reuse the existing contract without adding another scheduler.

### People

The requester, approver, and AP clerk retain their current personas, memory,
observation surfaces, and action interfaces. A person may remain dormant when
its process contract establishes that no transition can occur before a
delivered observation. Autonomy does not require random or periodic LLM calls.

This slice does not expose dynamic `next_update_at` selection to the purchase
LLM policy: the representative workflow needs no unsignaled reconsideration,
and adding model-authored scheduling would be a separate contract change.

### Exact mechanisms and coarse processor

All authorization, document validation, state mutation, and external processor
behavior remain unchanged. They do not become schedulers or LLM agents.

### Presentation and UI

Remain read-only projections. The existing single simulator page owns the
workflow; no new screen or graph is justified.

## Runtime Contract and Worked Path

The canonical runner should:

1. construct the existing `ActiveRuntimeSession`;
2. activate `requester` at logical time 0 with an explicit
   `scenario_start` cause;
3. repeatedly obtain `next_due_activation()`;
4. reject continuation when the attempt count reaches
   `PURCHASE_PAYMENT_MAX_CAUSAL_MOMENTS`;
5. activate the complete returned due set at its returned logical time and with
   its returned causes;
6. complete only when the due query returns `None`.

Worked settled path:

```text
time 0, moment 1: requester [scenario_start]
  -> submission/intake exact cascade
  -> review becomes available
time 0, moment 2: approver [observation_delivery]
  -> approval recording exact cascade
  -> recorded approval becomes available
time 0, moment 3: AP clerk [observation_delivery]
  -> exact payment gate -> coarse processor
  -> result becomes available
time 0, moment 4: AP clerk [observation_delivery]
  -> observes result, emits no action
  -> quiescence
```

Each arrow means a declared typed effect/connection/mechanism path, not
permission, organizational command, or an aggregate actor.

## UI Contract

- **User:** analyst inspecting how a purchase outcome emerges.
- **Critical flow:** choose Purchase to payment → choose the settled condition
  → Play → read its four causal-moment narratives → select each moment in
  spatial or causal layout → inspect the triggering observation and participant
  trace. Failure arms may quiesce in fewer moments.
- **Hypothesis:** the analyst can distinguish an authored initial condition
  from later information-triggered activity without learning a new UI.
- **API parity:** the existing `POST /api/runs` and retained `GET` document
  remain the machine-accessible equivalent.
- **Visible failure:** mismatched documents stop early rather than showing
  empty scheduled turns; a denied arm never displays a processor execution.
- **Non-claim:** browser correctness does not prove that the timing assumptions
  are realistic or that the operator finds the scenario analytically useful.

## Implementation Slices

### Packet 1 — deterministic autonomous vertical

**Classification:** representative vertical, deductive.

- Replace `PURCHASE_PAYMENT_SCHEDULE` with one scenario-start activation and
  bounded due-set continuation inside the existing runner.
- Keep the public API and scenario identifier compatible.
- Update tests to assert causes, logical times, variable call counts,
  quiescence, replay, denial, mismatch, and processor non-execution.
- Update ADR 010 and current documentation only after the checks pass.

**Done when:** all reference arms and negative fixtures replay; no purchase
attempt has `manual_schedule`; every observation-delivery cause names exactly
the unconsumed observation consumed in that activation; the mismatch arm
performs no unnecessary later activation; the existing full check and
desktop/narrow browser flow pass.

### Packet 2 — bounded live confirmation

**Classification:** representative live observation.

- Before spend, report the expected topology: at most four human calls and four
  narrator calls, same existing $0.38 ceiling.
- Run one settled live canary on the exact deployed revision.
- Inspect every agent/narrator full trace and retained cause/time.
- Confirm the processor makes no LLM call and the narrative never invents a
  manual schedule or processor-internal cause.

**Done when:** the retained live run reopens with four evidence-cited,
causally ordered moments at logical time 0, all structured calls validate, the
exact revision is deployed, and the roadmap records the bounded evidence and
remaining non-claims.

## Acceptance, Disproof, and Failure Behavior

Accept only if:

- the only explicit initial activation is the requester;
- later activations are derived from delivered observations;
- all participants due at one timestamp would still share one frozen pre-state;
- all three principal arms retain their distinct outcomes;
- the denial and malformed paths stop safely and cheaply;
- the graph, narratives, and traces remain synchronized to exact evidence.

Disproof includes any `manual_schedule` cause, a person activated with neither
start/observation/wake cause, future information visible early, changed exact
authorization behavior, an unbounded due loop, a fabricated elapsed-time claim,
or a parallel scheduler/UI.

On loop-bound or participant failure, preserve the API's existing failed run
record with its error summary; do not silently fall back to the old fixed
schedule. Mid-run purchase checkpoints are not added by this slice.

## YAGNI and Deferred Work

Do not add periodic polling, random human activations, model-authored clock
selection, exogenous-event infrastructure, a priority-queue rewrite,
continuous time, nonzero route delays merely for display, arbitrary
interleaving inside delayed exact cascades, dynamic latency calibration,
nested-boundary semantics, or a general workflow DSL.

If a later scenario requires an agent to reconsider without an observation,
reuse the existing `next_update_at` contract first. If a concrete LLM-modeled
agent must choose its own future wake, design that structured-output extension
as its own bounded change.

## Landscape and Authority Disposition

Landscape disposition: **linked**. This slice reuses
[ADR 010](../adr/010-autonomous-multirate-process-time.md), the implemented
Service Desk runner, and `ActiveRuntimeSession.next_due_activation()`. No new
shared subsystem, interoperability standard, or build/buy decision is open, so
external prior-art research cannot change the bounded choice.

Canonical ownership:

- roadmap: project direction and current status;
- this plan: the next scoped implementation packet;
- ADR 010: temporal semantics;
- causal/active-runtime models: machine contracts;
- tests and retained traces: execution evidence.

## Review Gate

Before implementation, confirm the plan does not:

- confuse observation-triggered dormancy with lack of agency;
- disguise omitted timing or arbitrary timing as empirical calibration;
- alter authorization or processor fidelity while changing scheduling;
- preserve fixed turns under a different name;
- expand into generic scheduler infrastructure.

After implementation, run a non-independent isolated second-pass review if no
fresh independent reviewer is available, and keep the claim limited to this
synthetic scenario.
