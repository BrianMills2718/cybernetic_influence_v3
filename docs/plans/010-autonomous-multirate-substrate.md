---
doc_role: historical_evidence
authority: evidence
status: complete
updated: 2026-07-23
---

# Slice 10: Autonomous Multirate Process Time

**Status: Complete — 2026-07-23.**

## Outcome

An operator runs the Service Desk and can see that a person may reconsider from
a retained intention without receiving a new message, while a faster exact
process advances on its own cadence without consuming LLM calls. The map,
causal-moment narrative, participant trace, and retained evidence all expose
the simulated timestamp and activation cause.

## Target and Boundaries

| Observable target | Required source/state | Owning operation | Contract | Acceptance |
|---|---|---|---|---|
| Unsignaled human reconsideration | retained follow-up time | active scheduler | `next_update_at` plus `internal_wake` | triager activates with zero observations |
| Faster non-LLM activity | remediation process phase | exact process controller and mechanisms | scheduled proposal plus typed process action | three process activations, zero model calls |
| Frozen simultaneous update | all work due at one timestamp | active scheduler | one activation set and pre-state digest | human and process share the same pre-state |
| Understandable temporal evidence | attempt inputs and exact events | presentation and narration | time unit, causes, participant kind | API and UI show why and when |

The active runtime owns schedules, due-set construction, activation causes,
private process state, and zero-time/moment bounds. Exact mechanisms retain
world-state authority. Service Desk owns its initial scenario trigger, retained
human follow-up, and one exact remediation process. Presentation and narration
remain non-authoritative projections.

## Rules

- Scenario time is an integer in an authored base unit.
- A delivered observation becomes eligible at its recorded arrival time.
- `next_update_at` must be strictly later than the activation that schedules it.
- A scheduled wake is consumed when it becomes due unless the process schedules
  another future update.
- Everyone due at the same timestamp receives the same frozen pre-state.
- Exact process activations may produce actions but never create model-call
  evidence or consume the LLM budget.
- A finite causal-moment bound fails loudly on a zero-time or self-scheduling
  loop.

## Canonical Service Desk Walkthrough

1. The scenario starts the triager at time 0 while a retained follow-up remains
   scheduled.
2. The specialist receives grounded incident information and queues
   remediation.
3. The exact remediation process receives that request and advances through
   queued, running, and applied states on one-second updates.
4. The triager's internal follow-up becomes due without a new observation. If
   an exact process update is due at the same time, both participate in one
   frozen causal moment.
5. Remediation receipts and customer feedback then re-enter the ordinary
   information-delivery path; exact closure safeguards remain unchanged.

## Acceptance and Negative Controls

- The scripted baseline reaches confirmed closure and exact replay.
- At least one human activation has only an `internal_wake` cause and zero new
  observations.
- At least one causal moment contains both the triager and remediation process,
  with equal pre-state digests.
- The remediation process has at least three activations and zero model calls.
- An update scheduled at the current or past timestamp is rejected.
- A future observation is not exposed before its arrival timestamp.
- Baseline, missing-direct-path, and speed-pressure intervention behavior
  remains distinguishable.
- Narrator inputs include participant kinds, activation causes, and simulated
  time, and citations remain confined to the current moment.
- The rendered desktop and mobile UI expose time and cause without breaking the
  map/trace workflow or producing console errors.

## Completion Evidence

- `make check` passed: mypy, 38 Python tests, the production frontend build,
  and shell lint.
- Scripted baseline, missing-direct-path, and speed-pressure arms retained
  distinct outcomes. The baseline has eight causal moments, ten participant
  activations, three autonomous wakes, and three exact-process activations;
  remediation occurs at moment 5 and confirmed closure at moment 7.
- Desktop and mobile browser checks retained the synchronized causal map,
  participant traces, simulated time, and activation causes without console
  errors or viewport overflow.
- The private Mac development host passed its Python type/test gate and served
  behavior commit `1e7a99e0cd0949f9f2e79f02f65c24284d9f4a8c`.
- Live baseline `run_3be342635ebb` completed with seven human cognition calls
  at medium reasoning and eight narrator calls at low reasoning using
  `openrouter/openai/gpt-5.6-terra`. All 15 structured calls validated on
  attempt zero, with no execution or validation errors, for a reconciled total
  cost of $0.085632375.
- Full-trace inspection matched every human response to its retained
  activation, observations, exposed interfaces, and committed action. The
  exact remediation process made zero model calls. Every narration prompt
  contained the exact earlier retained narrative chain and only the current
  causal moment; every cited source belonged to that moment and no account
  mislabeled `scenario_start` as an internal wake.
- The retained live run reopened through the tailnet UI with all eight
  causal-moment narratives, the remediation process in both graph and
  participant traces, and no browser console or page errors.

## Non-goals and Non-claims

Do not add continuous-time numerical integration, a universal process algebra,
speculative execution, rollback, a generalized stochastic/surrogate library,
or a stock-market/HFT scenario. This slice demonstrates one inspectable
multirate discrete trajectory; it does not establish calibrated human timing or
general fidelity outside the stipulated Service Desk.

The exact causal core remains quiescent at action boundaries: it drains a
single accepted action's complete routed cascade before another action may be
accepted. The representative proof therefore uses zero-delay message routes
and explicit scheduled process wakes. Arbitrary interleaving inside nonzero
route delays is not part of this acceptance claim.

## Landscape and Compatibility

This design is linked to ADR 010's accepted first-principles temporal model and
ADR 011's representation-depth boundary. It extends the existing
`ActiveRuntimeSession` and existing operator UI rather than creating another
scheduler or workbench. The historical fixed nine-activation fidelity harness
remains callable; its activations are retained as manual schedule causes.
