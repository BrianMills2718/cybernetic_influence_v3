---
doc_role: implementation_plan
authority: bounded_design
status: technically_complete
created: 2026-08-03
updated: 2026-08-03
---

# Slice 27: Four-condition coordination dynamics experiment

## Outcome

Give an analyst one retained, provider-free experiment that operationalizes the
Waltzman paper's coordination hypothesis without turning a synthetic result into
a real-world causal or attribution claim. The analyst can compare pressure
presence, feedback-driven adaptation, and one authoritative-validation
intervention, then open either exact replicate behind every summary.

## Canonical behavioral example

The same five-person bio-surveillance partnership is executed twice under each
condition, for eight ordinary retained runs:

1. `baseline` — no heterogeneous pressure sources;
2. `fixed_heterogeneous_pressure` — the existing scheduled source behavior,
   retained as a fixed control;
3. `adaptive_heterogeneous_pressure` — each pressure source observes public
   meeting snapshots and can change its second retained message; and
4. `adaptive_pressure_with_stabilization` — the adaptive sources remain active
   while one authoritative validation record can answer verification with
   bounded support.

The experiment reports terminal outcomes, exact numeric measures, time
trajectories, subgroup source-reliance edges, and the event IDs for adaptive
follow-ups and authoritative validation. The UI presents three declared
contrasts and steps each condition down to both exact runs.

## Frozen comparison contract

| Contrast | Reference | Treatment | Question isolated |
|---|---|---|---|
| Pressure presence | baseline | fixed heterogeneous pressure | What changes when the existing pressure processes are present? |
| Adaptation | fixed heterogeneous pressure | adaptive heterogeneous pressure | What changes when those processes read feedback and alter a later message? |
| Stabilization | adaptive heterogeneous pressure | adaptive pressure with stabilization | What changes when authoritative validation is concretely available? |

The experiment specification and full readout are strict versioned models. All
eight run documents retain the same validated readout plus their own matrix
slot. Retrieval fails on an incomplete, duplicated, malformed, or disagreeing
matrix instead of silently presenting a partial comparison.

## Mechanism boundaries

- Adaptive behavior reads delivered meeting-snapshot observations and
  person-local commitments. It does not read the experiment condition label or
  hidden aggregate trust/risk state.
- The stabilization handler reads the concrete
  `authoritative_validation_record.available` fact and retained validation
  representation. It does not branch on an arm label.
- Analytical boundaries remain execution-inert.
- All executions use scripted active-system bindings and must retain zero model
  calls and zero observed provider cost.

## Acceptance

- Exactly four ordered conditions and two replicates per condition are frozen
  in the experiment specification.
- All eight runs complete through the ordinary causal runtime, retain theory
  analysis and boundary activity, and reopen unchanged from `RunStore`.
- Only adaptive rows emit retained adaptive follow-up evidence.
- Only the stabilization rows emit authoritative-validation outcome evidence.
- POST creates one complete experiment; GET revalidates and reopens it without
  execution; DELETE moves all eight rows to recoverable trash.
- The history UI groups the experiment, shows condition outcomes/means and
  three directional contrasts, states the synthetic limits, and opens each
  exact replicate.

## Explicit nonclaims

- Deterministic repetitions prove lifecycle and retention consistency; they do
  not estimate population uncertainty.
- Reported directions describe this synthetic batch only. They are not
  invariants, causal-effect estimates, predictive validation, or hostile
  attribution.
- A slower or more cautious decision is not automatically coordination failure.

## Observed mechanism proof

The provider-free reference batch produced the same outcome in both replicates
of each condition:

- baseline: full deployment, 0 final open risks, 4,366 modeled minutes;
- fixed pressure: no decision, 2 final open risks, 5,768 modeled minutes;
- adaptive pressure: no decision, 2 final open risks, 5,768 modeled minutes;
- adaptive pressure plus validation: reduced scope, 0 final open risks, 4,371
  modeled minutes.

The adaptive rows retained 20 follow-up-related events per condition pair, but
the selected exact metrics did not differ from fixed pressure. That is a useful
null mechanism result: the source changed a later representation, while the
recipient reference policies did not make the selected outcome measures respond
differently. Richer recipient semantics are a future hypothesis, not something
to hide in this fixture.

Focused verification executes all eight runs once, reopens the complete matrix,
rejects an incomplete matrix, exercises recoverable group deletion, and opens
the grouped readout and exact-run step-down in Chromium at desktop and mobile
viewports. Stakeholder comprehension remains unobserved.
