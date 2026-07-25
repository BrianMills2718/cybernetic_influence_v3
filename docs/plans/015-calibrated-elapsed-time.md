---
doc_role: proposed_plan
authority: scoped
status: superseded
created: 2026-07-24
predecessor: 014-pausable-live-runs.md
---

# Slice 15: Positive-Duration Modeled Time

**Status: Slices 15A–15C are implemented evidence. Their remaining integrated
browser/operator acceptance is owned by successor
[Slice 16](016-canonical-analyst-demo.md). The first realization uses the
Service Desk's explicit minimum world duration as a source-labelled scenario
assumption, not a real-world calibration.**

## Outcome

An analyst can follow a Service Desk trajectory in modeled elapsed time and as
a realized causal graph without mistaking provider latency, database operations,
or arbitrary scheduler ticks for world time.
For example: a report arrives at 09:00, triage completes at 09:02, remediation
finishes at 09:08, and the trace identifies the declared estimate that produced
each duration. The initial claim is *plausible, source-labelled simulation*,
not a claim that an organization really operates at those timings.

## Scope and non-goals

In scope:

- positive durations for human activity, delivery, exact remediation, and
  stipulated external feedback;
- fixed and sampled typed timing assumptions with provenance;
- bounded runtime LLM duration adjudication only where a transition remains
  contextually underspecified at the scheduling boundary;
- a checkpointable future-work queue that permits independently timed work to
  overlap and advances to the next due time;
- elapsed-time display in the narrative, trace inspector, and pause state;
- a realized causal-trajectory projection whose nodes are retained world
  activities/events and whose edges are explicit causal-parent links.

Out of scope:

- using LLM response time, token count, or wall-clock run duration as simulated
  time;
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
  kind=fixed|triangular,
  parameters,
  source_kind=exact_mechanism|scenario_assumption|runtime_model_estimate,
  source_ref, uncertainty_note
)
TimedActivity(
  activity_id, owner, transition, starts_at, due_at,
  timing_estimate_id, sampled_duration, sampler_stream_id,
  status=pending|completed|cancelled
)
```

Timing fields are ordinary typed scenario configuration. A human may author
them directly, and a future conversational scenario compiler may propose them
for review. They do not require a separate pre-run timing-profile subsystem.

Every retained world transition must resolve a positive duration before it
enters the scheduler. The runtime first uses an exact mechanism calculation,
then a configured value or distribution, and finally bounded runtime LLM
adjudication only for genuinely contextual omissions. Runtime adjudication
retains the model, prompt, structured output, validation result, and declared
uncertainty. An LLM acting as a participant still proposes only a bounded
action through exposed interfaces; it does not silently control scheduler time.
A malformed, absent, zero, negative, past-due, or untraceable timing value fails
loudly before a world transition is scheduled.

## Runtime rules

1. The global future-work queue is part of the validated checkpoint.
2. Every causal child world event completes strictly later than its parent.
   Independent due work may share a timestamp; simulator bookkeeping is outside
   world time and outside the causal graph.
3. At each earliest due elapsed time, all due participants see one frozen
   pre-moment state and may propose concurrently.
4. New observations become usable only at their declared arrival time.
5. A human has no second single-attention activity while one is pending; richer
   attention/resource models are deferred.
6. Exact mechanisms and controllers may progress at their own declared rates
   without an LLM call at every micro-transition.
7. Seeded uncertainty is replayable: the trace retains estimate ID, sampler
   stream, and sampled duration. Same seed and checkpoint reproduce declared
   timing; different seeds vary only declared stochastic timing.

Slice 15A changed the former immediate-drain boundary to retained future work.
The remaining slices do not reinterpret exact trace order as causal relation:
explicit causal-parent links remain the causality authority.

## Service Desk first profile

The first vertical slice covers triage, specialist assessment, direct and
ticket-mediated delivery, three remediation phases, and customer feedback.
Each timing value names whether it came from an exact mechanism, a typed
scenario assumption, or bounded runtime model adjudication. A model-generated
value names the model, prompt, and uncertainty note that produced it. The
simulator must never label such a value `measured`, `expert`, `calibrated`, or
"realistic." The model's output is an explicit simulation assumption, not
evidence about a real service organization.

The direct-path and missing-direct-path arms must differ because their declared
activities and deliveries differ, not because a model saw hidden instruction or
because a provider responded slower. The scenario epoch and unit must be shown
in advanced evidence; prose mentions elapsed time only when it helps explain an
outcome.

## UI and evidence

- Narrative: concise causal account with elapsed time only where material,
  ending in the outcome.
- Realized causal trajectory: selectable world activities/events arranged by
  elapsed time, connected only by retained causal-parent links. This is distinct
  from the existing structural causal-flow map of entities and possible routes.
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
2. No retained causal child world event shares its parent's elapsed timestamp;
   an attempted zero-duration transition fails before scheduling.
3. The realized causal graph contains the same world-event IDs and explicit
   parent links as the exact trace, while simulator bookkeeping produces no
   graph node.
4. Direct and missing-direct-path arms differ through declared timing only.
5. Independent future activities can overlap; all same-time actors use a frozen
   state.
6. Invalid timing data fails before commit; no provider/wall-clock duration is
   accepted as simulation time.
7. Pause/resume preserves pending IDs, due times, and sampled realizations.
8. Same-seed replay matches declared timing; different seeds change only
   declared stochastic estimates.
9. Desktop opens a newly timed and legacy uncalibrated run without mislabelling
   either, scroll jumps, console errors, or network failures.
10. One DeepSeek live run has the same timing-envelope checks as scripted runs;
   trace inspection proves timing was runtime-modelled, not provider-derived.

## Thin slices

### 15A — contract and future work

Add fixed durations, the retained queue, checkpoint validation, and corruption
plus resume tests. A single timed Service Desk transition is the first vertical
proof.

**Implementation evidence (2026-07-24):** delayed exact effects and deliveries
now remain in a strict `scheduled_work` checkpoint contract instead of being
drained prematurely. The active runtime retains each exact-only due transition
as an `ExactWorkRecord`, so its trace, causal moment, and narration remain
inspectable between agent activations. A focused Service Desk test pauses with
two 300-unit deliveries pending, restores the checkpoint, and verifies that the
specialist first activates at time 300. This establishes truthful future-work
semantics, not a generated or calibrated duration profile. Restore re-derives
every pending delivery from the authored connection/container topology and
rejects altered targets, delays, and due times before it can resume.

### 15B — positive-duration Service Desk trajectory

Add source-labelled positive durations at every Service Desk world-transition
boundary, fail-closed runtime resolution, seeded sampling where useful, and a
scripted baseline whose causal descendants always advance elapsed time.

**Implementation evidence (2026-07-25):** `CausalScenario` now declares a
`positive_duration` timing contract and a positive `minimum_world_duration`.
The multirate Service Desk opts into it. The core assigns every non-metadata
event a later modeled time than each explicit parent, retains a timing record
(`starts_at`, elapsed `duration`, minimum scenario duration, and any separately
labelled runtime-serialization delay), and
rejects a persisted trace whose child fails that relation. A scripted baseline
completed with 90 events and positive duration records; pause/resume and
tampered-route validation remain covered. This first vertical deliberately
uses one explicit scenario-wide assumption. It does not yet claim
per-mechanism estimates, sampled durations, or runtime LLM adjudication.

The live narrator reserves enough remaining authorization for every retained
causal moment before its first provider call. It either produces the complete
account or retains a no-spend preflight explanation; it never spends on a
partial account merely because a later moment cannot fit the budget.

### 15C — realized causal graph and live proof

Project the retained activity/event DAG separately from the structural
causal-flow map, synchronize it with the narrative and inspectors, then run and
inspect one bounded DeepSeek trajectory plus pause/resume.

**Implementation evidence (2026-07-25):** the analyst document now exposes a
`trajectory` projection with one node per retained event and one directed edge
per explicit causal-parent relation. The simulator adds **Realized trajectory**
beside spatial topology and structural causal flow. Selecting an event keeps the
moment control synchronized and exposes its elapsed time, duration, and causal
parents. API and presentation tests prove that the projection has exactly the
retained event IDs and that every nonterminal graph edge advances modeled time.
After the narrator output bound repair, isolated local API canary
`run_abc000000002` completed a live DeepSeek V4 Flash `none` baseline with ten
participant calls, 23 narration calls, 23 fully narrated causal moments, a
`closed_confirmed` outcome, and 93 modeled process ticks. The retained document
records `$0.007474738` total observed provider cost and no failed model calls.
This proves the current API/trace path, not the browser presentation or a
real-world timing calibration; a rendered browser review remains the final
evidence for this slice.

### 15D — later evidence integration (deferred)

Real data or expert estimates are outside this PoC. If a future project needs
them, it must define source mapping, privacy, aggregation, and calibration
separately rather than silently upgrading a model-generated prior.

## Landscape and activation decision

The design reuses the discrete-event principle of scheduling a timeout and
advancing to the next event rather than wall-clock waiting; it does not adopt a
general simulation framework because V3 must retain typed causal evidence and
checkpoint semantics. See [SimPy overview](https://simpy.readthedocs.io/en/stable/index.html)
and its [timeout event contract](https://simpy.readthedocs.io/en/3.0.3/api_reference/simpy.events.html).
ADR 010 remains binding for causal versus scenario time.

The operator-directed start of this packet is the explicit Slice 14 reset
decision. Model-generated configuration and runtime estimates are scenario
assumptions, not empirical benchmarks or calibration claims. The configured
generator's identity and retained structured output are required whenever a
model supplies a duration.
