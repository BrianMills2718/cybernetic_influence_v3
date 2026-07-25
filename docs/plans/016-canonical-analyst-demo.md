---
doc_role: active_plan
authority: implementation_plan
status: active
created: 2026-07-25
predecessor: 015-calibrated-elapsed-time.md
---

# Slice 16: Canonical Analyst Demo

## Outcome

For an analyst, change a confusing internal-simulator screen into one
inspectable answer: choose a Service Desk condition, press Play, understand why
the incident reached its outcome, and step down to the relevant people,
mechanisms, records, maps, and exact evidence.

The canonical probe is the baseline and `no_direct_path` Service Desk arms. The
analyst must be able to answer why their outcomes differ without interpreting
raw JSON, provider traces, or simulator implementation vocabulary.

Non-claims: this packet does not calibrate real organizational time, add a new
world model, or make an organization an executor.

## Current and target state

The runtime already provides live/zero-cost runs, retained narratives, spatial
topology, a structural graph, a realized event DAG, time records, and checkpoint
resume API. The current screen exposes those as internal terms, and a reported
pause did not leave the operator with a discoverable resume path.

The target screen has one ordered flow:

```text
choose scenario + condition -> Play -> select one of three maps
  -> concise outcome account -> select evidence -> optional exact inspector
```

Run lifecycle state stays visible at the control that owns Play. A completed run
cannot look paused; a paused run exposes Resume at the same control and in run
history; an unavailable/failed pause explains the retained status.

## Terminology contract

| UI term | Backing projection | Meaning / non-meaning |
| --- | --- | --- |
| Spatial topology | `world` | Authored places, occupants, and physical links; no implied access or communication. |
| Configured interaction pathways | `causal` structural projection | Scenario-configured relationships that may support information or action if exact mechanisms permit them; not authorization. |
| Realized causal graph | `trajectory` | Events actually retained for this run and explicit causal-parent links; not all configured possibilities. |
| Causal step / order | `c1`, `c2`, … | Unique replay order; not elapsed time. |
| Modeled elapsed time | retained timing records | Source-labelled scenario time; never provider latency, wall time, or an empirical timestamp. |

## Owned boundaries and invariants

- The API/run store own lifecycle eligibility and persisted status. The browser
  renders retained state and invokes pause/resume APIs; it does not infer a
  checkpoint from local button state.
- A pause request can become `paused` only after a validated checkpoint. Resume
  is offered only for retained `paused` state with a continuation envelope.
- The structural graph remains a configured possibility view. A graph edge never
  grants authorization or independently causes an outcome.
- Modeled elapsed time is shown only when the retained run provides a
  source-labelled value. Otherwise the UI says that timing is omitted.

## Thin slices

### 16A — truthful control and vocabulary

Repair lifecycle rendering/recovery, rename the three graph views, and give each
an adjacent tooltip. Put the concise scenario purpose and the expected analyst
question beside Play. Add a compact causal-order versus modeled-elapsed-time
readout without calling process ticks seconds.

Acceptance: API fixtures for completed, pause-requested, paused, and failed
records render distinct states; a paused retained fixture exposes Resume; the
map labels and tooltips preserve the terminology contract.

### 16B — canonical map-to-account walkthrough

Keep the map directly beneath Play and put the narrative directly below the map,
as the operator requested. Lead that narrative with the outcome and its
condition-specific explanation, then offer the exact inspector below it. Add a
minimal comparison-ready readout for the one run: condition, outcome, modeled
timing availability, and the next exact evidence to inspect.

The spatial topology and configured interaction pathways must use a read-only
initial-state projection, so they appear and remain selectable before Play and
while a live request is in flight. The realized causal graph stays unavailable
until the run has committed an event; it must never be presented as a forecast.

Acceptance: a reviewer can run baseline and `no_direct_path`, identify the
changed direct report route before or after Play, then find retained evidence
without opening Advanced evidence.

### 16C — integrated live browser proof

Run a bounded live DeepSeek Service Desk baseline in an isolated local run
store; pause at a causal boundary, reopen/resume, and inspect all three map
views plus the narrative/evidence synchronization. Record only observed result,
revision, trace ID, and limitations.

Acceptance: no misleading lifecycle state, no console/network error, no scroll
jump, correct map names, and no claim that process ticks are real timestamps.

Technical evidence on 2026-07-25: the Mac Mini deployed
`23e2f37017d802911bb02b27c364c2d7c39194d5`; its focused API suite passed
(19 tests), and rendered 1440px desktop readbacks confirmed the configured
pre-run map, disabled realized-graph control, corrected spatial caption,
completed state, and retained cost. The actual operator usability judgment
remains outstanding.

## Verification and stop rule

Focused API/UI tests protect lifecycle and projection labels. A rendered browser
check exercises the canonical probe, including a real paused record and the
negative `no_direct_path` arm. Stop after 16C: if the analyst can understand and
interrogate the bounded example, move to conversational scenario authoring;
otherwise use the observed comprehension defect—not new simulator machinery—to
choose the next repair.
