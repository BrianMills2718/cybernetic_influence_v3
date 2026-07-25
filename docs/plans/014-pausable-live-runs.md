---
doc_role: active_plan
authority: implementation_plan
status: active
created: 2026-07-24
updated: 2026-07-24
predecessor: 013-configurable-explainable-runs.md
---

# Slice 14: Pausable Live Runs

**Status: Live pause/resume implemented and deployed; integrated demo acceptance
remains active.**

## Current implementation evidence

The service-desk event scheduler can stop only after a validated quiescent
`ActiveRuntimeCheckpoint` and restore that checkpoint into the same event-driven
schedule. The focused scripted test pauses after three causal moments and
proves that the resumed run has the same activation IDs, event IDs, and final
state as an uninterrupted reference. During every running Service Desk causal
boundary, the API now atomically retains the full validated checkpoint under a
private continuation envelope as well as its analyst-safe progress summary.
The failure path preserves that envelope with lifecycle `interrupted`; a
focused API test verifies its checkpoint digest rather than trusting a progress
summary. The scripted Service Desk control accepts a concurrent pause
request, stops after its current causal moment, and resumes the retained
checkpoint to a completed analyst document. The same continuation path is now
enabled for live Service Desk runs, and the browser exposes pause/resume
according to retained lifecycle state.

The deployed DeepSeek canary `run_abcd00000000` is current evidence that a live
run can complete from a retained checkpoint. It finished with lifecycle
`completed_from_checkpoint`, 12 causal moments, 105 events, 11 participant
calls, 12 narrator calls, 12 narratives, and `$0.0054597981` observed cost on
simulator `1be312441fcc934ab2fb72e044db3b5dc14f7985` and shared client
`9f61bd7c9419c93961a722a7ef6209adcf593382`. This licenses the bounded
completion claim. Full-trace inspection subsequently found 105 unique ordered
events, 23 unique provider logical calls, one start and completion per call,
zero retries or validation errors, a complete 0-through-11 prior-narrative
chain, and an exact match between 23 provider-reported receipts and the retained
`$0.0054597981` total. The pause occurred in the causal phase, so no narration
prefix existed to replay; all 12 accounts were generated after continuation
with the complete prior-account chain.

Behavioral note: after confirmed closure, the supervisor made two redundant
closure attempts. The exact mechanism denied both as already closed, and the
narratives exposed the attempts. This is participant judgment to assess during
the usability/fidelity review, not evidence of checkpoint replay.

The current desktop flow passed on deployed simulator
`997ce39890bdc9c0e222e6b029704623df10b848`. Browser-driven run
`run_251610100415` selected the default DeepSeek route, paused after one
provider call, resumed, and completed with 19 calls, ten narratives, and
`$0.003879` observed cost. The rendered product showed 9 spatial nodes/2
physical edges, 34 causal nodes/43 causal edges, five participant/composite
tabs, stable causal-moment controls, and retained-history readback. Projection
and moment changes preserved page position; a reproduced participant-trace jump
was repaired, and the exact regression remained at `scrollY=3359` across
triager, supervisor, and composite selections. Browser console, exceptions,
failed requests, HTTP errors, and backend errors were empty.

The operator review then identified a temporal-comprehension defect: successive
causal moments were labeled with repeated scenario-clock seconds, making an
uncalibrated two-tick process look like a realistic two-second incident. The
accepted correction gives every moment and exact subevent a unique causal
timestamp, keeps the scenario clock separate, and stops the Service Desk from
claiming calibrated seconds. It is deployed at
`ecce006c77e99f968230d9e5fb0f78cfcac727b4`. Scripted canary
`run_7124717c9dcd` retained `c1` through `c8` plus 67 unique exact trace
positions; the rendered desktop reopened both it and legacy live run
`run_251610100415` with unique causal labels, no repeated-seconds claim, and no
console, network, or new backend error. The final operator judgment remains the
only open demo gate.

## Demo completion gate

This packet is the sole active path to calling the current private PoC demo
finished. It does not require conversational scenario authoring or broader
scenario fidelity.

- [x] A current DeepSeek V4 Flash `none` Service Desk run completes with eight
  grounded moment narratives, participant traces, exact evidence, retained
  configuration, and observed provider cost.
- [x] A live run pauses at a validated causal boundary and later completes from
  that retained checkpoint.
- [x] Inspect the resumed run's full causal and provider-call trace: no repeated
  pre-pause event IDs or provider logical calls, a continuous narrative prefix,
  and observed cost supported by terminal receipts.
- [x] Exercise the current desktop path—choose scenario, Play, map, narrative,
  traces, pause, resume, and Run history—with no blocking console/network error,
  disruptive scroll jump, or misleading lifecycle control.
- [x] Confirm the roadmap, plan index, README, Mac operations page, and deployed
  configuration agree on revisions, model defaults, supported controls, and
  explicit non-claims.
- [ ] Have the operator use the current build for five to ten minutes. Fix only
  demo-blocking comprehension or control defects; otherwise record the judgment
  and mark this packet complete.

The demo is finished when all six checks are satisfied. Conversational scenario
drafting then becomes eligible as the next product phase; it is not part of
this completion boundary.

## Decision packet

- **Request mode:** plan and implement for the already-approved configurable
  live-run direction. This packet fixes the next bounded implementation scope;
  it does not authorize a background job system, distributed queue, cancellation,
  or cross-host hand-off.
- **Depth/profile:** Standard, private single-operator PoC. Runtime-state, LLM,
  UI, and strict JSON API overlays apply because live calls have spend and a
  paused run is durable state.
- **Sources consulted:** current `api.py` synchronous run path, `RunStore`,
  `ActiveRuntimeCheckpoint`, causal/active runtime restore paths, the existing
  scenario checkpoint observers, and Slice 13's retained live-configuration
  contract.
- **Landscape disposition:** inline. Existing checkpoints already validate the
  causal state, active-system state, event tail, trace record, costs, and
  attempts. The missing boundary is durable job lifecycle ownership, not a need
  for a queue or a new scheduler subsystem.

## Target outcome

An analyst running one long authorized live simulation can press **Pause**,
wait for the currently executing causal moment to finish, and later press
**Resume**. The retained run shows exactly where it stopped; continued execution
uses that validated checkpoint without replaying committed causal moments or
silently repeating a provider request whose outcome is unknown.

The target artifact is one retained paused live-run record plus its resumed,
completed analyst document. It must make a human-readable claim such as:

> Paused after causal moment 6 at simulated time 2. Resume will continue from
> the next quiescent causal boundary; all committed events and observed spend
> through that boundary are retained.

Allowed ambiguity: future LLM calls after resume can vary; pausing does not
promise bitwise-identical counterfactual output. Non-claim: this slice does not
interrupt an in-flight model request, recover a request lost mid-transport, or
turn a composite boundary into an executor.

| Target behavior | Required state | Owning operation | Contract | Acceptance check |
| --- | --- | --- | --- | --- |
| Pause at a truthful boundary | validated active checkpoint and lifecycle state | runtime checkpoint observer + job controller | retained run checkpoint envelope | pause after a causal moment and inspect its event/cost prefix |
| Resume without replay | same fixture fingerprint, config, trace ID lineage, and checkpoint digest | restore operator | `POST /api/runs/{id}/resume` | resumed trace has one copy of each pre-pause event/call summary |
| Do not hide uncertain provider spend | explicit in-flight/unknown-call state | job controller | paused/failed status + error/evidence | stop during a call is not automatically retried |
| Give the operator an understandable control | retained lifecycle state | web client | run detail + pause/resume endpoint | button explains boundary semantics and reports paused state |

## Boundaries and rules

### In scope

1. One local live run at a time, as today.
2. Pause requests accepted while the synchronous live request is executing.
3. Actual pause only immediately after a validated, quiescent causal checkpoint.
4. Resume a paused run on the same deployment when its fixture and LLM-client
   execution revision still match the retained checkpoint.
5. Pause/resume state visible in run history and run detail, through JSON APIs
   as well as the web client.

### Explicit non-goals

- Pause or kill a provider HTTP request mid-call.
- Automatic restart/resume after app restart, retry of unknown provider calls,
  or background worker distribution.
- Reconfigure model, reasoning, budget, scenario arm, or authored world while
  paused.
- Cancel/delete semantics beyond the current recoverable trash action.

### Domain concepts and owned invariants

`LiveRunLifecycle` is owned by the run store/controller, not the browser:

```text
running -> pause_requested -> paused -> resuming -> running -> completed
                                      \-> failed
running | pause_requested | resuming -> interrupted (process stops)
```

Rules:

1. **Quiescence:** `paused` is legal only with a fully validated
   `ActiveRuntimeCheckpoint`; it is never written before the first checkpoint
   or while effects are pending.
2. **Immutable execution identity:** resume requires identical scenario ID,
   scenario/execution fingerprints, run ID, effective LLM configuration, and
   shared-client revision. A mismatch fails loudly without calling a provider.
3. **No speculative replay:** a call that has left the local process but lacks a
   terminal receipt is `interrupted`/`failed`, not automatically repeated.
   The operator can inspect cost evidence and start a new run if desired.
4. **Exactly-once committed prefix:** all events, attempts, observed cost, and
   call summaries before the checkpoint remain immutable. Resume appends only
   new causal work.
5. **Narration integrity:** a narration is retained only after its full typed
   response and receipt are terminal. Slice 14 checkpoints the causal phase
   first; if pause is requested during narration, it takes effect between whole
   narrated moments and retains the completed narration prefix plus prior
   accounts.

## Contract and persistence design

### API

```text
POST /api/runs/{run_id}/pause
  -> 202 { run_id, status: "pause_requested", message }
  -> 409 for non-running/non-live runs

POST /api/runs/{run_id}/resume
  -> 202 { run_id, status: "resuming", message }
  -> 409 unless status is paused
  -> 422 if checkpoint or immutable execution identity fails validation
```

`POST /api/runs` remains the start operation. The first thin slice may retain
the existing synchronous request process while a small in-process job controller
owns lifecycle state; the resume endpoint must return immediately and run the
continuation in that controller rather than holding a browser request open.

### Retained envelope

Add a versioned `continuation` object only to live records:

```text
continuation:
  schema_version: 1
  phase: causal | narration
  lifecycle: running | pause_requested | paused | resuming
  checkpoint: ActiveRuntimeCheckpoint JSON | null
  checkpoint_digest: sha256 | null
  next_narration_moment_index: integer | null
  narration_prefix: [CausalMomentNarration JSON]
  prior_narrative_account: string
  last_terminal_call_receipt: string | null
```

The stored `checkpoint` is validated with `ActiveRuntimeCheckpoint` before any
restore. The run store writes atomically as it does today and a schema migration
reader accepts old records with no `continuation` as non-resumable history.
Only a redacted progress projection appears in history; the full checkpoint is
available to the server restore path and may be surfaced as evidence only after
the existing analyst-safe redaction rules are applied.

### Runtime flow

```text
browser Pause -> API records pause_requested
active run finishes current provider call/moment
  -> checkpoint observer validates and stores full checkpoint
  -> controller sees request -> stores paused -> releases live lock
browser Resume -> API validates immutable identity + checkpoint
  -> controller restores active session -> continues next causal moment
  -> completed causal trace -> narrates remaining moments -> completed document
```

The pause flag is checked after every observer notification and before the next
activation/narration request. A pause cannot be acknowledged as `paused` while
a model request is active. App startup keeps its conservative behavior for
`running`, `pause_requested`, and `resuming`: mark them `interrupted`; a valid
already-`paused` record remains resumable.

## UI plan

The existing Simulation run-control area owns this flow; no new workspace or
graph screen is justified.

- A running live run shows **Pause after this causal moment** and a short
  explanation that an in-flight call is allowed to finish.
- A pause request shows its requested state and disables duplicate requests.
- A paused detail/history row shows simulated time, retained event count, and
  observed spend, then offers **Resume**.
- A resumed run preserves map, narrative, evidence selection, and status rather
  than jumping the page. It must not scroll the user to a different section.
- Scripted, completed, failed, interrupted, and old non-resumable records show
  no misleading pause/resume action.

The backend owns eligibility and transition validation; the UI only renders the
retained lifecycle and invokes the JSON endpoints.

## Fixtures, negative cases, and slices

### Slice 14A — durable causal pause/resume — complete

Persist a full active checkpoint at a controlled causal boundary, implement the
lifecycle store/controller and two APIs, then resume a scripted Service Desk
run. Positive fixture pauses after a known moment and produces the same final
exact trace as an uninterrupted scripted reference. Negative fixtures reject a
corrupt checkpoint, wrong scenario fingerprint, and an already terminal run.

**Acceptance:** one resumed scripted run has no duplicated event IDs, action
attempts, or state revisions; the run history reports `paused` before resume
and `completed` after it.

### Slice 14B — live call/accounting boundary and narration prefix — acceptance open

The low-cost DeepSeek-`none` sample has paused and resumed to completion.
Inspect its exact shared-client trace and exercise the negative in-flight
condition through the existing deterministic test double: it becomes
interrupted/failed and is never automatically resubmitted.

**Acceptance:** retained provider-call logical IDs before pause occur once;
observed cost after resume equals the terminal receipts; narration resumes with
its retained prior account and emits no duplicate moment account.

## Verification and promotion

Focused store, runtime, and API tests cover lifecycle transitions,
corrupt/mismatched checkpoints, compatibility, scripted exact-prefix
equivalence, uncertain-call non-replay, status contracts, live-lock release,
and native live continuation. Remaining promotion evidence is exactly the open
work in the demo completion gate: inspect the live full trace and cost receipts,
then exercise pause/resume through the private-Mac browser.

Required now: full checkpoint validation, immutable execution identity, typed
state transitions, and explicit provider uncertainty. Deferred until a real
need: cancellation, queues, multi-process ownership, automatic recovery, and
cross-host resume. Promote beyond this PoC only after a live pause/resume trace
has shown no duplicated calls or causal events and an operator has found the
state presentation understandable.
