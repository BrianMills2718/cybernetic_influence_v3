---
doc_role: implementation_plan
authority: bounded_design
status: in_progress
created: 2026-07-25
updated: 2026-07-27
---

# Slice 20: Inspectable extended runs

## Assignment

Implement Slice 20 in order: 20A, audit and commit; then 20B, audit and commit;
then 20C's generic live-playback implementation and zero-cost proof; then 20D's
integrated, separately authorized operator proof. Do not begin Slice 21, add a
general game-master actor, generate mechanism code, or broaden the authored
workflow language while this slice is active.

Use a clean linked worktree based on the current clean descendant of
`278f5d17bf11dc6cc126ac4537211f56d091d462`. Preserve the existing causal core,
three graph meanings, exact-mechanism authority, retained-run compatibility,
pause/resume behavior, and shared `llm_client` boundary.

Use scripted/reference evidence for implementation checks. Before a paid live
canary or deployment, report the exact call topology and configured budget and
obtain explicit authorization.

## Implementation progress

- **20A complete:** one retained narrator call now returns a concise timeline
  account and one to three evidence-cited detailed paragraphs per causal
  moment, with legacy records remaining readable.
- **20B complete in this worktree:** Service Desk resolves only its compiled
  terminal condition, horizon, and safety bounds before execution; it retains
  a separate completion record, preserves the plan across resume, and exposes
  pause/irreversible stop at causal boundaries. A horizon or stop retains
  pending exact work as explicit non-execution rather than silently dropping
  it.
- **20C implementation checkpoint:** the runtime now publishes strict,
  ordered checkpoint updates for every scenario using the active-runtime
  adapter. Live catalog and approved-authored runs start in a background
  worker; a resumed live Service Desk run uses the same worker path. Both
  retain analyst-safe progress and expose it through a cursor-based polling
  endpoint. The shared canvas highlights a pending frozen participant set and
  animates only event-derived configured edges after commitment. This preserves
  the distinction between configured pathways, world topology, and realized
  causal trajectory. No paid canary has been run.
- **20C zero-cost proof:** focused API tests now retain the same ordered public
  progress schema for Service Desk and Physical Access authorization denial,
  while the approved information-campaign test proves the authored compiler
  path. Runtime/presentation tests cover pending activation, retained failure,
  exact denial cues, redaction, stale cursor behavior, and worker lock release.
- **20D live execution observed through `08614b4`:** deployed Service Desk
  `run_ca0e512a5763` paused after one DeepSeek participant call, resumed from
  the retained checkpoint, and completed `closed_confirmed` with 110 unique
  events, 11 participant calls, two exact denials of premature closure, a
  delivered confirmed-closure receipt, and `$0.002085029` provider-observed
  cost. The live proof exposed and led to repairs for invalid-ID lock leakage,
  terminal completion with already-emitted effects, and stale failure evidence
  after resume.
- **20D narration blocker reproduced:** the `$0.10` proof correctly refused to
  start 29 narrator calls because it could not reserve their ceilings. With
  adequate authorization, `run_6c4975979cec` retained five valid detailed
  accounts before DeepSeek returned an out-of-context detailed citation;
  after explicitly enumerating allowed IDs, `run_e589d6e3a769` retained seven
  before the same failure family recurred. Both runs failed narration visibly
  while retaining completed world trajectories and exact observed spend. This
  is not a transport or empty-structured-output failure.
- **20D1 complete:** v3 narrator output contains prose only. The simulator now
  retains an immutable evidence-context envelope per account with exact current
  event IDs, earlier narrated-record IDs, prompt version, run identity, and a
  canonical digest of the analyst-visible prompt context. Reopening validates
  the envelope and fails visibly on unknown/cross-run/future/digest corruption;
  v1/v2 records remain readable. The UI labels this **Evidence supplied to the
  narrator** and explicitly distinguishes provenance from proof of entailment.
- **20D2 remains:** certify the changed narrator schema, run one separately
  authorized integrated DeepSeek proof, inspect every participant/narrator
  trace, rerender the retained authored example, and obtain the three human
  readouts below. Slice 21 remains blocked until 20D2 is recorded complete.

## Outcome

An analyst can inspect a run with many causal moments without choosing between
an unreadably terse timeline and raw evidence. Each moment has both a concise
account and a grounded detailed narrative. The run also states whether it ended
because a configured terminal condition was met, the modeled horizon was
reached, the world became quiescent, an operator stopped it, or a
safety/resource bound prevented continuation. Scenario outcome is reported
separately: reaching a terminal state does not imply that state was desirable.

This slice makes longer runs understandable and governable. It does not make a
short scenario longer merely to appear sophisticated. Scenario duration still
comes from concrete agents, scheduled processes, deliveries, and world
mechanisms.

## Canonical examples

### Narrative example

Use the retained authored information-campaign shape:

1. a source decides whether to publish a retained claim;
2. an exact configured route delivers it;
3. a recipient assesses only the delivered representation; and
4. an exact mechanism records the assessment.

The concise account should remain a quick four-step story. The detailed account
must explain, in prose, the information and remembered context the participant
used, the decision it made or deferred, what the exact mechanism subsequently
committed, and what remained unresolved. It must not infer hidden motives,
persuasion, truth, or geopolitical effects.

### Completion example

Use the Service Desk baseline:

- exact terminal condition: incident status becomes `closed_confirmed`;
- modeled-time horizon: scenario-authored maximum;
- safety limits: participant calls, causal moments, exact effects, and spend;
- fallback completion: quiescence.

The retained completion record must say that confirmed closure was reached and
cite the exact event/state evidence. In a negative fixture whose terminal
condition never becomes true and whose processes have no more work, the record
must say `quiescent_before_terminal`, not imply success.

## Non-goals

- No artificial turns, heartbeat calls, or random chatter to lengthen a run.
- No organization, analyst boundary, or “game master” becomes a world actor.
- No LLM adjudicates exact world effects in this slice.
- No semantic LLM stop judge in Slice 20. The future boundary below records how
  to add one only when a reviewed scenario cannot use exact state.
- No arbitrary user-authored predicate language or executable code.
- No new workflow template.
- No change to the meaning of pause: pause remains a nonterminal, resumable
  retained causal boundary. A checkpoint may truthfully retain future exact
  work for resume.

## Baseline before Slice 20

- `CausalMomentNarration` retains one short `narrative` string and one to four
  current-moment event IDs.
- The narrator makes one structured call per retained causal moment and receives
  earlier narratives plus the current analyst-visible trace.
- The UI renders a list of short moment cards and a selected-moment account.
- Scenario runners loop until `next_due_activation()` returns `None`, then call
  `complete()`.
- Service Desk has a hardcoded 24-moment scheduler guard; the two authored
  templates have guards of six and eight attempts.
- `ActiveRuntimeConfig` has spend and state-growth limits but no typed domain
  terminal condition, modeled-time horizon, or completion reason.
- A core run can complete only with no queued exact work. Current `completed`
  status therefore means the trace was closed successfully as a record, not
  that its outcome was favorable.

## Design decisions

### 1. One narrator call returns both levels

Do not double the number of narration calls. Replace the live response contract
with a versioned dual-level result from the existing call:

```python
class NarrativeParagraph(BaseModel):
    text: str
    source_event_ids: list[str]

class CausalMomentNarrationV2(BaseModel):
    concise_narrative: str
    concise_source_event_ids: list[str]
    detailed_paragraphs: list[NarrativeParagraph]
```

Required constraints:

- `concise_narrative`: one sentence, at most 360 stored characters and 240
  requested characters;
- `detailed_paragraphs`: one to three prose paragraphs;
- each paragraph: 1–900 characters and one to six source event IDs;
- every cited ID must be in the current moment or in the source IDs of an
  earlier retained narrative supplied to this call;
- at least one cited ID across the detailed paragraphs must belong to the
  current moment;
- the concise account continues to cite one to four current-moment decisive
  events through a separate `concise_source_event_ids` field;
- model output forbids extras; retained consumers tolerate unknown future
  fields where the existing storage compatibility policy requires it.

Use the shared `llm_client` with `task=`, `trace_id=`, `max_budget=`, and native
`json_schema`. Observe cost from the retained client/observability record; do
not estimate it or modify `llm_client` in this slice.

The detailed account may connect the current moment to prior events, but it may
not invent a perception, causal edge, authorization, outcome, or private state.
When participant orientation is present, prose may say that the trace records
the participant considering or reporting something. It may not claim that a
profile field caused the action.

### 2. Retain backward readability

New retained moment records contain:

```json
{
  "narrative_version": 2,
  "narrative": "legacy-compatible concise text",
  "source_event_ids": ["event_..."],
  "concise_narrative": "same concise text",
  "concise_source_event_ids": ["event_..."],
  "detailed_paragraphs": [
    {"text": "...", "source_event_ids": ["event_..."]}
  ]
}
```

Existing runs with only `narrative` and `source_event_ids` continue to render
their concise account. They show a truthful “Detailed account was not retained
for this older run” state rather than synthesized replacement prose.

### 3. Separate domain completion from safety bounds

Add a typed run-control contract owned by the active runtime layer:

```python
class ExactFactTerminalCondition(BaseModel):
    kind: Literal["fact_equals"]
    condition_id: str
    fact_id: str
    expected_value: JsonValue
    public_description: str

class ModeledTimeHorizon(BaseModel):
    kind: Literal["modeled_time_horizon"]
    condition_id: str
    logical_time: int
    public_description: str

class RunControlOptions(BaseModel):
    available_terminal_conditions: list[ExactFactTerminalCondition]
    default_terminal_condition_ids: list[str]
    allowed_terminal_modes: list[Literal["any", "all"]]
    minimum_horizon: int | None
    default_horizon: int | None
    maximum_horizon: int | None
    max_causal_moments_cap: int
    max_participant_calls_cap: int

class RunControlSelection(BaseModel):
    terminal_condition_ids: list[str]
    terminal_mode: Literal["any", "all"]
    modeled_time_horizon: int | None
    max_causal_moments: int
    max_participant_calls: int

class ResolvedRunControlPlan(BaseModel):
    terminal_conditions: list[ExactFactTerminalCondition]
    terminal_mode: Literal["any", "all"]
    modeled_time_horizon: ModeledTimeHorizon | None
    stop_on_quiescence: Literal[True]
    max_causal_moments: int
    max_participant_calls: int

class CompletionRecord(BaseModel):
    reason: Literal[
        "terminal_condition_met",
        "modeled_time_horizon",
        "quiescent_before_terminal",
        "operator_stopped",
        "safety_limit",
    ]
    condition_ids: list[str]
    causal_time: int
    logical_time: int
    public_summary: str
    evidence_event_ids: list[str]
```

The exact names may change to fit the repository's type organization, but these
semantics may not.

Rules:

1. A scenario/compiler owns its allowed fact predicates and public labels.
2. A scenario exposes options and a default selection. Runtime callers may
   select only compiled condition IDs and values inside compiled horizon and
   safety caps; they cannot submit arbitrary fact IDs, values, expressions, or
   code.
3. Unless a scenario explicitly supports horizon-only execution, the selected
   terminal-condition list must be nonempty.
4. The API resolves and retains the immutable plan before execution. The
   scenario options, user selection, and resolved plan are separately
   inspectable.
5. Evaluate completion after each committed causal boundary and after settling
   due exact work.
6. A satisfied terminal condition stops future participant activation but
   first retains all exact work already due at that boundary.
7. A future scheduled effect after a terminal condition is not silently
   executed unless the compiled stop policy explicitly requires draining it.
8. Quiescence means no due participant, no retained future participant wake,
   and no queued exact work. It is a completion reason, not proof of success.
9. Reaching a safety limit fails loud or returns `safety_limit`; it never
   masquerades as a terminal condition or favorable outcome.
10. A satisfied terminal condition or reached horizon completes before Pause or
    Stop. Pause never creates a resumable checkpoint for an already terminal
    run.
11. Resume rejects a changed run-control plan just as it rejects changed model
   policy or scenario execution identity.
12. Operator Stop is a separate non-resumable request honored at a safe causal
    boundary; it retains `operator_stopped` and never interrupts an in-flight
    provider call or atomic mechanism commit.
13. `CompletionRecord` explains termination only. The scenario's existing
    outcome record independently states the favorable, unfavorable, or
    unresolved result.
14. The controller is execution infrastructure, not an entity, analytical
    boundary, or agent in the world graph.

### 4. Semantic stop judgment remains a gated future extension

A later semantic stop condition may be useful when a reviewed termination
criterion cannot be expressed as exact world state. Do not implement it in
Slice 20. If a later scenario demonstrates the need, use:

```python
class SemanticStopEvaluation(BaseModel):
    decision: Literal["continue", "stop"]
    criterion_id: str
    rationale: str
    source_event_ids: list[str]
```

It receives only the reviewed criterion, analyst-visible retained state, prior
evaluations, and current causal-moment evidence. It runs only at configured
causal boundaries, uses `llm_client`, retains full call evidence and cost, and
cannot create an action, mutate state, or override a safety limit. `continue`
when the world is quiescent still ends as `quiescent_before_terminal`.

Do not implement this boundary merely to use the phrase “game master.” The
canonical Service Desk and coordination assay use exact terminal records.

### 5. UI contract

On desktop, the narrative section becomes:

- a compact causal-step timeline that always displays concise accounts; and
- a synchronized continuous reading pane that concatenates every moment's one
  to three detailed prose paragraphs into one run narrative, visibly marks the
  selected moment, and provides a small evidence link for each passage.

Selecting a moment in either pane selects the corresponding passage, graph
state, and exact inspector without moving the outer page scroll position. The
detailed pane may scroll internally to its selected passage. It is ordinary
prose, not a dump of events or a checklist. No second run-level LLM call is
needed; the continuous account is the retained moment passages in causal order.

The narrative ends with **Why the run ended**, rendered from
`CompletionRecord`. The existing outcome headline remains, but must not
contradict the completion reason.

Before Play, the run controls show:

- the scenario purpose and possible outcomes in plain language;
- **Stop when**, selecting only scenario-compiled terminal condition IDs and
  `any`/`all` semantics when the scenario exposes reviewed alternatives;
- the modeled-time horizon if present;
- the maximum causal moments and provider calls as safety bounds; and
- the distinction between terminal condition, outcome, horizon, quiescence,
  pause, and budget.

Do not label these controls “world condition” or imply that maximum steps is
the objective. A terminal condition may represent a favorable, unfavorable, or
neutral outcome.

While running, Pause and Stop are separate controls. Pause produces a resumable
checkpoint. Stop finishes at the next safe causal boundary, retains
`operator_stopped`, and cannot be resumed.

## Runtime sequence

```text
committed causal boundary
  -> settle exact work due at that boundary
  -> evaluate compiled exact terminal conditions
  -> check modeled-time horizon
  -> if terminal condition or horizon applies, retain CompletionRecord
  -> enforce safety/resource bounds
  -> honor operator Stop
  -> honor operator Pause
  -> select next due participant/exact work
  -> if none, complete as quiescent
  -> narrate each causal moment once into concise + detailed prose
  -> render completion passage
```

The implementation must encode this priority in one tested helper and use it in
new runs and resume. Add collision fixtures for terminal-plus-pause,
terminal-plus-stop, safety-plus-pause, and stop-plus-pause. Do not duplicate
the ordering across scenario runners.

## Slice 20A — Dual-level evidence-bound narration

**Classification:** vertical.

**Owned paths:** `src/cybernetic_influence/narration.py`,
`src/cybernetic_influence/active_runtime/prompts/causal_moment_narrator.yaml`,
`src/cybernetic_influence/presentation.py`,
`src/cybernetic_influence/api.py`, `web/index.html`, `web/app.js`,
`web/styles.css`, and focused narration/API/presentation tests. The frontend
build owns only the React graph-canvas assets under `web/`; the simulator shell
and narrative UI are authored directly in these `web/` source files.

**Acceptance:**

- one structured call per moment produces both narrative levels;
- every detailed paragraph cites only allowed retained evidence;
- a current-moment citation is mandatory;
- prior context is preserved sequentially;
- invalid, missing, or out-of-scope citations stop narration visibly;
- legacy runs remain readable;
- the information-campaign fixture renders four concise accounts and four
  detailed passages;
- the detailed prose distinguishes participant decisions, exact delivery or
  recording, consequences, and unresolved uncertainty;
- model-call and observed-cost accounting remains exact.

**Negative controls:**

- a paragraph citing an unknown event fails;
- a paragraph citing only earlier events fails;
- prose cannot be retained when the structured response is missing a paragraph;
- a legacy run does not trigger new LLM spend.

**Stop condition:** if one call cannot reliably return both levels within the
current per-call ceiling, retain the schema and measure the exact current-route
failure before changing model, budget, or call topology.

## Slice 20B — Typed completion and horizon contract

**Classification:** direct blocker for extended scenarios.

**Owned paths:** `src/cybernetic_influence/active_runtime/models.py`,
`src/cybernetic_influence/active_runtime/engine.py`, the smallest shared
completion helper under `active_runtime/`,
`src/cybernetic_influence/run_store.py`,
`src/cybernetic_influence/api.py`,
`src/cybernetic_influence/scenarios/service_desk.py`, the two reviewed
authoring-template runners only as needed for compiled defaults,
`web/index.html`, `web/app.js`, `web/styles.css`, and focused
runtime/API/checkpoint/replay tests. Do not put scenario-specific terminal
facts into the generic engine.

**Acceptance:**

- exact terminal condition, horizon, quiescence, operator stop, pause, and
  safety-limit paths produce distinct retained states or records;
- completion evaluation is deterministic and replayable;
- resume retains and revalidates the same plan;
- Service Desk ends with `terminal_condition_met` on confirmed closure and
  retains its favorable scenario outcome separately;
- a no-progress fixture ends `quiescent_before_terminal`;
- a horizon fixture stops before later scheduled work and retains that work's
  non-execution truthfully;
- Stop at the next safe boundary retains `operator_stopped` and is not
  resumable, while Pause remains resumable;
- a safety-limit fixture never reports success;
- the UI explains and displays the selected plan and actual completion reason.

**Negative controls:**

- unknown condition IDs and arbitrary predicates are rejected before a run;
- a hidden fact value is not leaked through `public_summary`;
- a changed plan cannot resume a checkpoint;
- a terminal condition cannot be satisfied by an LLM narrative.

**Stop condition:** if the current `completed` status cannot remain backward
compatible, stop and write a migration decision before changing retained-run
schema.

## Slice 20C — Scenario-generic live causal playback

**Classification:** shared runtime/UI vertical.

Live execution retains a public, ordered stream of checkpoint updates while the
causal runtime is still executing. Every current catalog scenario and approved
authored scenario uses the same optional `ActiveRuntimeSession` observer and
presentation adapter; no scenario or entity identifier selects playback
behavior. `POST /api/runs` returns a retained `running` record with HTTP 202,
then a bounded worker executes the run. The browser polls the retained stream;
it does not infer activity from prompts, hidden state, or a scenario name.

The observer emits a strict `activation_started` record from a frozen causal
activation set before participant implementations run, then a committed
causal-moment or exact-work record only after exact causal evidence exists.
Failed activations remain forensic records and never become committed world
outcomes. Progress projections redact protected material and contain only
analyst-safe graph state, timeline events, and typed visual cues.

The Simulation screen keeps the configured graph visible during a live run.
Pending same-moment participants receive simultaneous halos. After commitment,
the canvas pulses evidence-backed nodes and edges. A moving labeled token is
permitted only for a retained routed effect or delivery that names a resolved
visible edge; all other event kinds use non-travel pulses. Animation is
presentation time only, respects reduced-motion preferences, and does not
alter causal state or logical time. Narration starts after causal execution so
its spend cannot influence a participant trajectory.

**Acceptance:**

- cursor polling returns only records after the supplied sequence and never
  moves a stale browser view backward;
- pause, stop, resume, retained reopening, observed cost, failure cleanup, and
  redaction remain correct with a worker in flight;
- unknown edges/events have no token path; uncommitted/failed work has no
  committed projection; and same-moment participants are not serialized;
- zero-cost Service Desk, Physical Access authorization-denied, and approved
  authored information-campaign runs prove the shared schema and adapter.

## Slice 20D — Integrated compatibility proof

**Classification:** representative vertical.

Run the existing Service Desk baseline through its real scheduled work and
participant decisions, then rerender one retained authored
information-campaign run. Do not extend either scenario with no-op activations.
The first naturally longer, twelve-or-more-moment product proof belongs to
Slice 21A because that scenario has recurring modeled work.

The integrated result must show:

- pre-run purpose/terminal-condition/horizon/safety explanation;
- concise timeline plus detailed selected-step prose;
- spatial topology, configured interaction pathways, and realized causal DAG;
- exact step-down from every narrative paragraph;
- an explicit completion reason;
- pause/resume continuity if Service Desk is used;
- observed participant and narrator call counts and costs.

Inspect every full LLM trace. A human reviewer then answers only:

1. Can each run's meaningful arc be understood without opening raw evidence?
2. Can a disputed statement be traced to the exact retained events?
3. Is it clear why the simulation stopped?

### Packet 20D1 — Simulator-owned narrative evidence context

**Classification:** direct blocker repair.

The live counterexample shows that asking the narrator to reproduce arbitrary
event IDs is not a reliable structured-generation task. An ID is provenance
metadata, not narrative judgment. The simulator already knows the exact prompt
context and must own that record.

Change the producer contract to a new version in which the model returns only:

- one concise narrative sentence; and
- one to three connected detailed prose paragraphs.

After the structured response validates, the simulator creates one immutable
evidence-context record containing:

- every current-moment event ID supplied to the call;
- the prior narrated-moment record IDs supplied to the call;
- the narrator schema/prompt version; and
- a canonical digest of that analyst-visible context.

The concise passage and every detailed paragraph reference that context record.
They do not contain model-selected event IDs. The UI label is **Evidence
supplied to the narrator**, not “evidence proving this statement.” Selecting it
opens the current exact events and prior narrative chain that the model could
use. This is truthful provenance and dispute support; it is not automated
semantic entailment.

**Owned paths:** `src/cybernetic_influence/narration.py`, the causal-moment
narrator prompt, the smallest presentation/API consumer changes, narrative UI
source, and focused narration/presentation/API tests. Do not change the active
runtime, scenario mechanics, person prompts, run-control semantics, models or
reasoning defaults, or `llm_client`.

**Compatibility and failure behavior:**

- legacy v1 concise-only and v2 model-cited records remain readable;
- new v3 records require a valid context digest and locally resolvable exact
  current events and prior narration references;
- a corrupt, missing, cross-run, future-moment, or mismatched context reference
  fails reopening visibly;
- missing prose or provider/schema failure still makes narration unavailable;
- no code may repair narrative text, invent a citation, synthesize fallback
  prose, or turn partial narration into `completed`.

**Both-sign acceptance:**

1. A zero-cost fake call produces a complete v3 concise/detailed sequence whose
   context records exactly equal the evidence supplied to each call.
2. The second call's context names the first retained narrative record and may
   not name a future one.
3. Unknown/cross-run event IDs, a changed context digest, future narrative
   references, missing paragraphs, and a partial provider failure are rejected
   or retained visibly unavailable as appropriate.
4. Legacy v1/v2 runs reopen without a provider call.
5. The rendered evidence control steps down to exact context and explicitly
   avoids an entailment claim.

**Verification:**

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_narration.py tests/test_api.py -k narration
.venv/bin/python -m mypy src/cybernetic_influence/narration.py src/cybernetic_influence/api.py
npm --prefix frontend run build
git diff --check
```

Audit the complete owned diff, commit the packet, and stop. The changed output
schema invalidates the old narrator route observation by design. Do not copy or
edit certification IDs, deploy, call a provider, or begin 20D2.

#### Assignment prompt for the implementation agent

> Implement Packet 20D1 only from
> `docs/plans/020-inspectable-extended-runs.md` in a clean linked worktree based
> on the current clean descendant of canonical `main`. First confirm that
> `main` contains `08614b4e9f4c7d6bd84c34922c16e83314faa814` and that no other
> writer claims the owned paths. If either check fails, stop and report it.
>
> Replace model-selected narrator citation IDs with the v3 simulator-owned
> evidence-context contract specified in 20D1. The LLM-facing response contains
> only the concise sentence and one-to-three detailed prose paragraphs. After a
> valid response, simulator code must retain the exact current event IDs, prior
> narrative-record IDs, prompt/schema version, and canonical context digest
> that were supplied to that call. Every new passage references this immutable
> context record. Label the UI step-down “Evidence supplied to the narrator”
> and state that supplied context is provenance, not proof of entailment.
>
> Preserve readable v1 concise-only and v2 model-cited records. Add every
> positive and negative test named in 20D1. Fail visibly on corrupt, missing,
> cross-run, future-moment, or digest-mismatched context. Do not silently filter
> an invalid model citation, synthesize fallback prose, change runtime or
> scenario mechanics, alter people, switch models/reasoning, modify
> `llm_client`, edit certification IDs, deploy, spend money, or begin 20D2.
>
> Run the focused pytest, mypy, frontend build, and `git diff --check` commands
> in 20D1. Inspect the owned diff for hidden fallbacks, semantic-proof
> overclaims, stale compatibility assumptions, unrelated changes, or weakened
> fail-loud behavior. Fix owned defects, rerun the checks, commit the coherent
> packet, report the commit and exact evidence, and stop.

### Packet 20D2 — Certified integrated operator proof

**Classification:** representative live vertical; separate authorization
required.

Preconditions: committed 20D1, clean canonical descendant, full focused checks,
and an explicit spend authorization after reporting the exact topology. The
participant schema/certification is unchanged; the v3 narrator schema requires
one fresh successful route observation. Do not advertise the route until the
shared client replays the exact model, schema digest, revision, transport
evidence, and freshness.

Then deploy the exact canonical revision to the private Mac, require the config
endpoint to report that revision and DeepSeek V4 Flash `none`, and run one
Service Desk baseline with the existing maximum of 48 participant and 32
narrator calls under the operator-approved hard cap (currently at most `$0.74`).
Pause after a validated causal boundary, resume the same checkpoint, and require
terminal completion. Reopen the run after restart and rerender retained authored
`run_6ff09016a6e0` without execution or spend.

Acceptance requires complete—not partial—v3 narration; unique events and calls;
provider-observed cost; exact completion reason and outcome; delivered terminal
effects; all three graph meanings; full participant/narrator trace inspection;
and affirmative human answers to the three 20D questions. If DeepSeek still
fails prose/schema generation, retain the exact failure and stop for a model or
call-topology decision. Do not silently switch to Terra or relax the v3
contract.

## Verification

At each packet:

```bash
.venv/bin/python -m pytest -q tests/test_narration.py tests/test_api.py
.venv/bin/python -m mypy
npm --prefix frontend run build
git diff --check
```

At terminal acceptance:

```bash
make check
```

Inspect the rendered desktop flow, browser console/network errors, retained
run after restart, and full `llm_client` traces for participant and narrator
calls. A passing build does not establish narrative quality or run-control
correctness.

## Deferred from Slice 20

- authoring arbitrary recurring processes;
- coordination-state measurements;
- comparison across repeated trajectories;
- evasion-space variants;
- generalized semantic game-master adjudication;
- changing exact mechanism authority; and
- increasing global call or cost ceilings before one representative longer run
  demonstrates the need.

## Done when

20A and 20B pass their positive and negative contracts, 20C's shared playback
contract passes its cross-scenario proof, and 20D's integrated examples are
observed on the deployed private host. Full traces are inspected,
documentation names the actual completion semantics, no code path equates a
terminal condition, quiescence, or a safety bound with a favorable scenario
outcome, and Slice 21 can consume the contracts without another runtime
redesign.
