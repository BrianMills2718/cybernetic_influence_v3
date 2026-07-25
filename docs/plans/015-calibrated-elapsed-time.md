---
doc_role: proposed_plan
authority: scoped
status: proposed
created: 2026-07-24
predecessor: 014-pausable-live-runs.md
---

# Slice 15: Calibrated Elapsed Time

**Status: proposed; do not implement until Slice 14 is closed or explicitly
reset, and the timing-evidence source is chosen.**

## Outcome

An analyst can follow a Service Desk trajectory in modeled elapsed time without
mistaking provider latency or arbitrary scheduler ticks for real-world time.
For example: a report arrives at 09:00, triage completes at 09:02, remediation
finishes at 09:08, and the trace identifies the declared estimate that produced
each duration. The initial claim is *plausible, source-labelled simulation*,
not a claim that an organization really operates at those timings.

## Scope and non-goals

In scope:

- a Service Desk timing profile for human activity, delivery, exact remediation,
  and stipulated external feedback;
- fixed, sampled-prior, and later empirical timing estimates with provenance;
- a checkpointable future-work queue that permits independently timed work to
  overlap and advances to the next due time;
- elapsed-time display in the narrative, trace inspector, and pause state.

Out of scope:

- using LLM response time, token count, or wall-clock run duration as simulated
  time;
- asking an LLM to invent numeric durations at action time;
- a universal scheduler, continuous-time solver, resource-queue library,
  market model, or claim of general organizational fidelity;
- calling generic internet averages a calibration.

## Temporal contract

The existing causal clock stays intact. It answers ordering, while elapsed time
answers duration:

| Concept | Example | Meaning |
| --- | --- | --- |
| Causal timestamp | `c7`, `c7.3` | unique moment and exact replay position |
| Modeled elapsed time | `09:08:10` | scenario-clock instant, not provider time |
| Timing realization | `specialist_assessment = 4m12s` | one recorded sample from a declared estimate |

```text
TimingProfile(profile_id, epoch, base_unit, estimates)
TimingEstimate(
  estimate_id, applies_to,
  kind=fixed|triangular|empirical_sample,
  parameters, source_kind=measured|expert_prior|author_assumption,
  source_ref, uncertainty_note
)
TimedActivity(
  activity_id, owner, transition, starts_at, due_at,
  timing_estimate_id, sampled_duration, sampler_stream_id,
  status=pending|completed|cancelled
)
```

An LLM still proposes only a bounded action through its exposed interfaces. The
runtime maps a committed action or mechanism transition to its declared timing
estimate, samples once if applicable, records that realization, and schedules
completion. A malformed, absent, negative, or past-due timing value fails
loudly before a world commit.

## Runtime rules

1. The global future-work queue is part of the validated checkpoint.
2. At each earliest due elapsed time, all due participants see one frozen
   pre-moment state and may propose concurrently.
3. New observations become usable only at their declared arrival time.
4. A human has no second single-attention activity while one is pending; richer
   attention/resource models are deferred.
5. Exact mechanisms and controllers may progress at their own declared rates
   without an LLM call at every micro-transition.
6. Seeded uncertainty is replayable: the trace retains estimate ID, sampler
   stream, and sampled duration. Same seed and checkpoint reproduce declared
   timing; different seeds vary only declared stochastic timing.

The current causal core drains a routed cascade immediately. Slice 15 changes
that specific boundary to retained future work; it does not reinterpret exact
trace order as causal relation. Explicit causal-parent links remain the
causality authority.

## Service Desk first profile

The first vertical slice covers triage, specialist assessment, direct and
ticket-mediated delivery, three remediation phases, and customer feedback.
Each profile value must name its source. Until Brian supplies representative
logs or qualified domain estimates, values are marked `author_assumption` or
`expert_prior`, never `measured` or "realistic."

The direct-path and missing-direct-path arms must differ because their declared
activities and deliveries differ, not because a model saw hidden instruction or
because a provider responded slower. The scenario epoch and unit must be shown
in advanced evidence; prose mentions elapsed time only when it helps explain an
outcome.

## UI and evidence

- Narrative: concise causal account with elapsed time only where material,
  ending in the outcome.
- Inspector: causal position, elapsed timestamp, timing estimate/source, and
  realized duration for each activity.
- Process/participant trace: pending, completed, dormant; no fake real-time
  animation.
- Pause: the next scheduled activity and its due modeled time are visible.
- README/scenario explanation: source kind, uncertainty, and omissions are
  plain-language and discoverable.

## Acceptance evidence

1. A scripted Service Desk baseline has nontrivial elapsed time with every
   material duration traceable to a declared source.
2. Direct and missing-direct-path arms differ through declared timing only.
3. Independent future activities can overlap; all same-time actors use a frozen
   state.
4. Invalid timing data fails before commit; no provider/wall-clock duration is
   accepted as simulation time.
5. Pause/resume preserves pending IDs, due times, and sampled realizations.
6. Same-seed replay matches declared timing; different seeds change only
   declared stochastic estimates.
7. Desktop opens a newly timed and legacy uncalibrated run without mislabelling
   either, scroll jumps, console errors, or network failures.
8. One DeepSeek live run has the same timing-envelope checks as scripted runs;
   trace inspection proves timing was runtime-modelled, not provider-derived.

## Thin slices

### 15A — contract and future work

Add fixed durations, the retained queue, checkpoint validation, and corruption
plus resume tests. A single timed Service Desk transition is the first vertical
proof.

### 15B — profile and analyst readout

Add the source-labelled Service Desk profile, seeded sampling, scenario/UI
readout, and the direct-path comparison.

### 15C — calibration decision

Only if representative logs or qualified estimates are available: define data
privacy, aggregation, source mapping, calibration/holdout separation, and
promotion criteria. Otherwise retain the explicit-prior profile.

## Landscape and activation decision

The design reuses the discrete-event principle of scheduling a timeout and
advancing to the next event rather than wall-clock waiting; it does not adopt a
general simulation framework because V3 must retain typed causal evidence and
checkpoint semantics. See [SimPy overview](https://simpy.readthedocs.io/en/stable/index.html)
and its [timeout event contract](https://simpy.readthedocs.io/en/3.0.3/api_reference/simpy.events.html).
ADR 010 remains binding for causal versus scenario time.

Activation requires both the Slice 14 completion/reset decision and one chosen
evidence source for the first profile: representative measured data, qualified
expert prior, or clearly labelled author assumption. This is a product/evidence
decision, not an empirical benchmark disguised as a requirement.
