---
doc_role: implementation_plan
authority: bounded_design
status: proposed
created: 2026-07-24
predecessor: 013-configurable-explainable-runs.md
---

# Slice 14: Pausable Live Runs

**Status: implementation started; not yet user-facing.**

## Current implementation evidence

The service-desk event scheduler can now stop only after a validated quiescent
`ActiveRuntimeCheckpoint` and restore that checkpoint into the same event-driven
schedule. The focused scripted test pauses after three causal moments and
proves that the resumed run has the same activation IDs, event IDs, and final
state as an uninterrupted reference. This is the continuation seam for Slice
14A; it is deliberately not advertised as pause/resume yet because no API/UI
control or durable checkpoint envelope exists.

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

### Slice 14A — durable causal pause/resume

Persist a full active checkpoint at a controlled causal boundary, implement the
lifecycle store/controller and two APIs, then resume a scripted Service Desk
run. Positive fixture pauses after a known moment and produces the same final
exact trace as an uninterrupted scripted reference. Negative fixtures reject a
corrupt checkpoint, wrong scenario fingerprint, and an already terminal run.

**Acceptance:** one resumed scripted run has no duplicated event IDs, action
attempts, or state revisions; the run history reports `paused` before resume
and `completed` after it.

### Slice 14B — live call/accounting boundary and narration prefix

Run a low-cost real DeepSeek-`none` live sample with a controlled pause after
one completed causal moment, resume it, and inspect the exact shared-client
trace. Exercise the negative in-flight condition through a deterministic test
double: it becomes interrupted/failed and is never automatically resubmitted.

**Acceptance:** retained provider-call logical IDs before pause occur once;
observed cost after resume equals the terminal receipts; narration resumes with
its retained prior account and emits no duplicate moment account.

## Verification and promotion

- Focused Pydantic/store tests: lifecycle transitions, corrupt/mismatched
  checkpoint rejection, compatibility for old records, atomic paused write.
- Runtime tests: scripted pause/resume exact-prefix equivalence; provider-call
  double verifies no replay after uncertain in-flight call.
- API tests: pause/resume status/error contracts and live-lock release.
- Browser verification: run → pause request → paused evidence → resume → final
  narrative on the private Mac; inspect the returned retained record.
- LLM evidence: exact full trace and cost receipts for the one Slice 14B live
  sample, not a claim of deterministic model behavior.

Required now: full checkpoint validation, immutable execution identity, typed
state transitions, and explicit provider uncertainty. Deferred until a real
need: cancellation, queues, multi-process ownership, automatic recovery, and
cross-host resume. Promote beyond this PoC only after a live pause/resume trace
has shown no duplicated calls or causal events and an operator has found the
state presentation understandable.
