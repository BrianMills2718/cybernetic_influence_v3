---
doc_role: implementation_plan
authority: bounded_design
status: planned_after_slice_20
created: 2026-07-25
updated: 2026-07-27
---

# Slice 21: Coordination-environment assay

## Assignment boundary

Begin only after Packet 20D2's completion record and dual-level narration are
implemented and observed. Implement 21A and obtain its human readout before
21B. Implement 21B and inspect its full measurement traces before 21C. Do not
begin the evasion variants or Levin-style composite-agency assay until the
baseline/pressure/stabilization vertical passes.

Work in a clean linked worktree based on the current clean descendant of
`main`. For each packet below: implement only that packet, run its
focused positive and negative checks, audit the owned diff, commit, and report
before starting the next packet. Do not spend on live calls or comparison
batches without explicit authorization after reporting their maximum call and
cost bounds.

### Lower-agent execution contract

The packet headings below are the complete execution order. A delegated agent
must receive exactly one packet at a time and must stop after its commit and
evidence report. For every packet it must:

1. start from a clean linked worktree on the current canonical descendant;
2. verify the named precondition and path ownership before editing;
3. implement only the named contract and both-sign tests;
4. run the packet's focused checks plus `git diff --check`;
5. audit the complete owned diff for silent fallback, weakened validation,
   hidden aggregate execution, and unrelated edits;
6. commit the coherent packet and report the commit, checks, and open risks;
7. stop at any human-readout, certification, deployment, or spend gate.

An agent may not infer that “continue” authorizes a later packet, paid call,
deployment, model switch, relaxed schema, generalized game master, generated
mechanism code, or change to `llm_client`. If a required runtime generalization
is not already named, it must retain the smallest failing test and stop for a
design decision.

Use this message for every later delegation, replacing only `<PACKET>`:

> Implement Packet `<PACKET>` only from
> `docs/plans/021-coordination-environment-assay.md`. Follow its preconditions,
> owned paths, acceptance criteria, negative controls, verification commands,
> and the lower-agent execution contract. Work in a clean linked worktree on
> the current canonical descendant. Do not begin the next packet. Stop and
> report before any certification, deployment, provider spend, human-readout,
> or independent-sign-off gate, and stop on any unnamed runtime redesign.
> Commit only the coherent verified packet and report the commit and evidence.

This plan is grounded in the complete
[source note](../research/001-from-minds-to-coordination.md) and
[ADR 012](../adr/012-decision-environment-measures-are-derived.md). The paper
supplies constructs and candidate indicators, not validated scales or causal
truth.

### Start precondition

Do not start implementation merely because this plan exists. The start commit
must be a clean descendant of canonical `main` that contains completed Slice
20A–20D behavior. Verify that the retained Service Desk proof exposes dual-level
narration, completion reason, live progress, pause/resume continuity, all three
graph meanings, and exact evidence step-down. If Slice 20 is still an unmerged
branch or its plan remains `in_progress`, stop and report that precondition.

## Analyst outcome

An analyst can simulate a multi-episode collective decision under heterogeneous
information pressure, inspect how concrete interactions changed the decision
process, compare an ordinary baseline with pressure and stabilization
conditions, and see evidence-bound measures related to trust structure,
perceived risk, and coordination readiness.

The result is a traceable experimental model of possible dynamics. It is not a
prediction of a real institution, attribution of hostile intent, or empirical
validation of the paper.

### Micro-to-macro interpretation

The reviewed person profiles use the existing BDM-informed fields only where
they matter to this scenario. These descriptions may support heterogeneous
local reactions, but they do not create numeric susceptibility, trust, risk, or
coordination state. Concrete messages and world conditions produce person
actions; post-run analysis derives collective patterns from those actions.

The partnership's analytical boundary is a reversible view over the people,
records, routes, and mechanisms below it. Slice 21 asks how its decision process
changes. It does not yet ask whether that boundary is a useful composite-agent
model. The latter question is owned by
[Slice 22](022-composite-agency-perturbation-assay.md) after 21C.

## Canonical scenario

Use the paper's multinational bio-surveillance deployment problem as a
synthetic scenario:

> A multinational partnership must decide whether and how to deploy an upgraded
> bio-surveillance system by a modeled deadline. Technical evidence initially
> supports deployment. Over several meetings, different participants receive
> different technically, politically, or locally framed concerns. The group may
> deploy, delay, reduce scope, lose a partner, or reach the horizon without a
> decision.

### Concrete people

The scenario defines five human person records:

1. **Mission coordinator** — maintains the decision schedule and commitments.
2. **Technical validation lead** — assesses calibration and independent
   validation requests.
3. **Sovereignty and policy representative** — assesses oversight,
   transparency, and authority concerns.
4. **Local public-health liaison** — assesses local safety and legitimacy
   concerns.
5. **Partner representative** — decides whether its organization remains
   committed.

Their positions, dispositions, memories, values, goals, beliefs, decision
tendencies, perceived social conditions, current states, capabilities, and
limitations are reviewed person assumptions. They are not procedural commands.
Packet 21A1 exercises the contracts with fixed scripted implementations at zero
cost; Packet 21A3 later binds the same reviewed people to the existing native
LLM implementation behind an explicit canary gate.

### Concrete world state

At minimum:

- deployment proposal and technical validation dossier;
- decision deadline and meeting schedule;
- issue register with open/resolved/reopened lifecycle;
- verification requests and responses;
- source references and each participant's recorded reliance or rejection;
- proposed scope and decision threshold;
- participant commitments and partner participation;
- meeting/decision record;
- configured communication channels and spatial locations; and
- exact final status:
  `deploy_on_time | delayed | scope_reduced | partner_disengaged |
  no_decision_by_horizon`.

### Active systems and mechanisms

- People orient and act only from private memory, delivered observations, and
  exposed interfaces.
- A deterministic meeting scheduler creates recurring decision opportunities
  without an LLM call.
- Exact mechanisms deliver messages, record verification requests, update issue
  lifecycle, record commitments, and commit final decisions when their reviewed
  preconditions are met.
- Pressure sources are concrete software agents or source processes with
  target-specific information and interfaces. A campaign/swarm analytical
  boundary may group them, but the boundary never acts.
- The first vertical uses three source processes—technical, policy, and local—
  carrying different messages while retaining one concrete shared objective
  record. No global narrative is inserted into recipient prompts.

### Modeled cadence and causal depth

Use authored scenario days, not claimed empirical timing:

- day 0: proposal introduction and first decision meeting;
- days 1–2: ordinary questions or first pressure-source delivery;
- day 3: second meeting and verification/issue actions;
- days 4–5: exact verification responses plus adaptive source follow-up based
  only on observable recorded reactions;
- day 6: third meeting and commitment updates;
- days 7–8: remaining responses or stabilization feedback;
- day 9: fourth decision meeting; and
- day 10: exact decision horizon if no earlier terminal status was committed.

Every scheduled meeting must expose a real opportunity to inspect or change
issues, source reliance, thresholds, commitments, scope, or final decision.
The scripted 21A acceptance trajectory must contain at least four meeting
cycles and twelve meaningful causal moments. Its expected working range is
twelve to twenty-eight narrated moments, leaving headroom under the current
thirty-two-call narrator ceiling. Compilation or preview must fail visibly if
the projected narrated-moment maximum exceeds that ceiling. Do not create
silence-only wakes to meet the minimum.

At each meeting, all due people orient from the same frozen pre-moment state.
An exact recorder commits their typed attempts after the due set completes.
Between meetings, exact delivery and source processes may advance at their own
positive durations. The schedule is an explicit synthetic assumption that a
future empirically grounded scenario may replace.

### Decision interfaces and exact commitment

People may use only reviewed interfaces to:

- request or answer verification;
- add, resolve, or reopen an issue;
- record reliance on or rejection of a delivered source;
- propose a threshold or scope change;
- update their own commitment;
- send an informal alignment message;
- propose a terminal decision; or
- withdraw the represented partner when that interface is assigned to them.

The exact decision mechanism checks the retained commitments, open blocking
issues, active partners, approved scope, and reviewed decision threshold. It
commits a terminal status only when those typed conditions are satisfied. At
day 10, the scheduler commits `no_decision_by_horizon` if no earlier terminal
status exists. A narrator, measurement coder, or semantic evaluator cannot
commit a decision.

## Conditions

### Baseline

Ordinary decision-making with the technical dossier, normal review questions,
meeting schedule, and no adaptive pressure source. This is not a frictionless
or perfectly trusting control.

### Heterogeneous pressure

Three source processes deliver different locally relevant concerns:

- technical uncertainty to the validation lead;
- sovereignty/transparency concerns to the policy representative; and
- safety/legitimacy concerns to the local liaison.

The messages may be individually plausible. The condition differs from
baseline through concrete source activity, delivery topology, adaptation
history, and shared objective—not through a hidden decrement to trust or
coordination.

### Stabilization

The same pressure operates while concrete CSO-inspired mechanisms are present:

- an explicit authoritative-source and validation process;
- reviewed criteria for adding a risk to the decision register;
- decision thresholds and unresolved-uncertainty bounds;
- retained commitments, deadlines, and responsibility assignments; and
- feedback to participants about verified issues and current commitments.

Stabilization may fail or have side effects. The plan does not hardcode a
successful outcome.

## Run-control contract

The compiled scenario uses Slice 20's typed plan:

- terminal conditions: any exact terminal decision status;
- modeled horizon: the configured decision deadline;
- recurring work: scheduled meetings and retained participant reconsideration;
- quiescence: possible only when no future meeting, wake, or exact work remains;
- safety bounds: causal moments, participant calls, exact effects, spend, and
  private-state growth.

The run ends on a terminal decision, deadline, quiescence, operator stop, or
safety limit and retains the exact reason. An LLM judge is not required for the
canonical terminal states.

At day 10, settle the scheduler's exact
`no_decision_by_horizon` transition before evaluating run completion. A valid
run therefore ends through `terminal_condition_met` with that unfavorable
scenario outcome. The run-controller horizon remains a backstop; reaching it
without the compiled deadline transition is an invalid scenario execution, not
a successful no-decision outcome.

### Three distinct judgment boundaries

Do not combine these into a general game master:

1. **World adjudication:** exact mechanisms validate actions and commit state.
2. **Run completion:** exact terminal facts and horizon normally decide when to
   stop; Slice 20's optional semantic evaluator may only classify a reviewed
   non-exact criterion.
3. **Post-run measurement:** exact calculators and a separate evidence coder
   analyze a completed trace without changing it.

## Measurement model

### Measurement classes

Every measure has one of three provenance classes:

1. **Exact trace measure** — counted or calculated from typed events/state.
2. **Evidence-coded indicator** — an LLM or human classifies analyst-visible
   evidence using a typed rubric and cited event IDs.
3. **Derived comparison** — calculated from exact and/or coded measures across
   time, subgroups, runs, or conditions.

The UI must display this provenance class. It must not present an LLM-coded
indicator as an exact world fact.

### Primary outcome measures

| Construct | Measure | Class | Unit |
|---|---|---|---|
| Decision result | Final deployment status | Exact | categorical |
| Decision speed | Modeled time to terminal status or horizon | Exact | scenario minutes/days |
| Participation | Partners retained at completion | Exact | count/proportion |
| Scope | Final approved deployment scope | Exact | typed category |

### Trust-structure indicators

| Indicator | Operational definition | Class |
|---|---|---|
| Verification demand | New verification requests per meeting and cumulatively | Exact |
| Source reliance topology | Directed actor-to-source reliance/rejection edges retained in decisions | Exact |
| Authority divergence | Pairwise disagreement over relied-upon source classes | Derived |
| Intermediary bypass | Previously configured authoritative route bypassed in favor of another source | Exact |
| Conditional-trust episode | Actor explicitly conditions acceptance on additional validation | Evidence-coded |

Do not collapse these into one trust score in the MVP.

### Perceived-risk indicators

| Indicator | Operational definition | Class |
|---|---|---|
| Risk-register expansion | New distinct risks added over modeled time | Exact |
| Action-threshold change | Recorded change to required evidence or approval threshold | Exact |
| Precautionary/hedging episode | Decision language explicitly favors delay or caution under uncertainty | Evidence-coded |
| Relevance classification | Whether a newly introduced risk is directly tied, indirectly tied, or unsupported by retained evidence | Evidence-coded |
| Unresolved risk load | Open risk items at each meeting boundary | Exact |

The evidence coder may label relevance; it cannot decide whether the underlying
claim is true.

### Coordination-readiness indicators

| Indicator | Operational definition | Class |
|---|---|---|
| Decision latency | Modeled time from proposal to terminal decision | Exact |
| Deliberation load | Number of meeting cycles and external actions before completion | Exact |
| Issue reopening | Resolved issues returned to open state | Exact |
| Commitment divergence | Number and duration of incompatible participant commitment states | Derived |
| Informal alignment | Concrete alignment messages sent through configured informal channels | Exact |
| Disengagement | Participant withdrawal from the partnership | Exact |

Meeting duration is measured only if the scenario explicitly models it. The
event count must not be relabeled as elapsed time.

### Candidate directional patterns

For each condition and indicator, retain a time series by run and subgroup.
After repeated trajectories, calculate:

- direction relative to baseline;
- magnitude in the indicator's native unit;
- proportion of valid runs with the same direction;
- between-run variation;
- subgroup disagreement; and
- missing/invalid measurement counts.

Label the output `candidate_directional_pattern`. Do not use `invariant` in the
UI until a later acceptance rule defines the required consistency and
generalization across contexts.

## Evidence-coding contract

Use a separate analysis task after the run:

```python
class IndicatorEvidence(BaseModel):
    indicator_id: str
    direction: Literal["increase", "decrease", "no_change", "unclear"]
    explanation: str
    source_event_ids: list[str]
    source_trace_ids: list[str]

class RunMeasurement(BaseModel):
    measurement_spec_version: Literal[1]
    exact_values: dict[str, JsonValue]
    coded_indicators: list[IndicatorEvidence]
    limitations: list[str]
```

Rules:

- exact values are produced by code, never copied from model output;
- the coder sees analyst-visible trace evidence, not hidden canonical facts or
  another model's chain of thought;
- every coded claim cites existing evidence;
- the coder model/task/trace/budget and raw structured result are retained;
- missing or ambiguous evidence returns `unclear`;
- the coder cannot update agents, mechanisms, outcomes, or completion state;
- a corruption fixture with mismatched or nonexistent event IDs must fail;
- measurement prompts and revisions are frozen before the first comparison
  batch; and
- the system-under-test model and evaluator identity remain visibly separate,
  even if the same provider family is used in the PoC.

Use the shared `llm_client` with `task=`, `trace_id=`, `max_budget=`, and native
`json_schema`; do not add a direct provider call or modify `llm_client`.
Observed cost comes from retained client/observability evidence, not an
estimated price table.

## Evaluation design

### Claim

The simulator can represent heterogeneous local interactions that produce
inspectable changes in a collective decision process, and it can measure those
changes without inserting the aggregate measures into agents' minds.

### Decision

If the vertical passes, proceed to repeated baseline/pressure/stabilization
comparison and only then consider evasion and composite-agency assays. If the
measurement layer cannot distinguish known controls or the trace cannot explain
an indicator, revise the measurement contract before adding scenario breadth.

### Unit of analysis

One complete trajectory of the synthetic deployment decision. Comparison units
are valid trajectories grouped by condition and replicate.

### Validity controls

- **Positive control:** scripted pressure trajectory with known verification,
  reopening, delay, and commitment events produces the corresponding exact
  indicators.
- **Negative control:** heterogeneous messages that are delivered but cause no
  verification, risk, commitment, or decision change must not be labeled as a
  directional system effect merely because their content sounds concerning.
- **Corruption control:** invalid evidence IDs or measurement/spec revision
  mismatch invalidates the analysis.
- **Environmental-event control:** a real scenario event that legitimately
  increases risk is retained separately from pressure-source activity; the
  measurement reports ambiguity rather than attributing intent.
- **Build adequacy:** all intended people, sources, schedules, routes,
  mechanisms, conditions, and run-control rules are present in the compiled
  scenario fingerprint.

### Initial execution matrix

1. One zero-cost scripted run per condition to validate mechanics and controls.
2. One live canary per condition with full participant, narrator, and
   measurement trace inspection.
3. Only after valid canaries, a small repeated batch with the same model,
   reasoning, budgets, scenario revision, and measurement specification.

The repeated batch is an exploratory PoC. Report every run and uncertainty; do
not claim statistical representativeness. Before paid execution, calculate
maximum calls from people × scheduled activations plus narration and
measurement calls, state the authorization and expected observed range, and
run one canary to calibrate cost/latency.

### Invalid runs

Exclude from comparison but report separately:

- provider or schema failure;
- unobservable spend;
- safety-limit termination before the declared horizon or terminal condition;
- missing scheduled source or participant activation;
- measurement corruption or incomplete trace; or
- scenario/configuration fingerprint mismatch.

Do not score invalid infrastructure as a poor social outcome.

### Pre-registered first readout

Primary readout:

- exact final status;
- decision latency;
- issue reopenings;
- verification requests;
- partner retention; and
- per-run indicator trajectories.

Secondary readout:

- source-reliance divergence;
- coded conditional-trust and precautionary episodes;
- cost, calls, and latency.

Continue to 21C only if positive and negative controls behave correctly, all
claims step down to evidence, and at least one valid live trajectory per
condition completes. Revise if controls fail or coded evidence is not
reproducible. Stop if the scenario requires global trust/risk/readiness values
to drive people or if exact world effects require an unconstrained LLM judge.

## Slice 21A — Multi-episode decision vertical

**Classification:** representative vertical.

Build one reviewed typed scenario family named `coordination_decision_v1`, its
recurring scheduler, exact mechanisms, three conditions, run-control plan,
existing maps, dual narratives, participant traces, and final decision record.
Use fixed scripted participant policies before native LLM bindings. Do not
extend conversational authoring in 21A.

### Required domain vocabulary

Keep scenario-specific vocabulary in
`src/cybernetic_influence/scenarios/coordination_decision.py`; do not generalize
the causal core unless a focused negative fixture proves the existing contract
cannot express a required transition.

- condition: `baseline | heterogeneous_pressure | stabilization`;
- issue lifecycle: `open | resolved | reopened`;
- source disposition: `unreviewed | relied_on | rejected | validation_pending`;
- commitment: `support_full | support_reduced | defer | withdraw`;
- scope: `full | reduced | none`;
- final decision: `deploy_on_time | delayed | scope_reduced |
  partner_disengaged | no_decision_by_horizon`;
- recurring schedule: meeting indices 0–3 at modeled days 0, 3, 6, and 9,
  followed by the exact day-10 deadline transition.

The entire reviewed condition surface is one strict configuration record:

```python
class CoordinationConditionConfig(_StrictModel):
    schema_version: Literal[1]
    condition: Literal["baseline", "heterogeneous_pressure", "stabilization"]
    pressure_sources_enabled: bool
    adaptive_follow_up_enabled: bool
    authoritative_validation_enabled: bool
    evidence_based_risk_admission_enabled: bool
    uncertainty_bounds_enabled: bool
    commitment_feedback_enabled: bool
```

Baseline sets every flag false. Heterogeneous pressure enables only pressure
sources and adaptive follow-up. Stabilization enables all six. The concrete
people, source records, routes, mechanisms, schedule, initial dossier, goal,
and safety bounds remain present and identical; these flags control whether
the corresponding source or mechanism schedules work and accepts its reviewed
operation. Compile the record into one mechanism-readable configuration entity
in initial canonical state so checkpoints and scenario fingerprints bind the
selected arm. It has the same ID in every arm and is never delivered to a
person or copied into a person's memory or prompt as an instruction or hidden
social variable. Keep the same `scenario_id` across arms. A fixture comparison
that removes this one entity from each canonical scenario dump must be byte-
identical across the three arms, while the complete fingerprints must differ.

The exact decision operation owns the final-status transition. It accepts only
typed proposals whose retained commitments, blocking issues, active partners,
scope, and evidence threshold satisfy the reviewed condition. A syntactically
valid but ineligible proposal is denied and traced; it is not repaired by an
LLM. The deadline operation owns only `no_decision_by_horizon` and must lose a
collision to any already committed terminal decision.

### Packet 21A0 — Contract and fixture seam

**Classification:** boundary probe; it does not advance product status alone.

**Allowed edits:** create the scenario module and
`tests/test_coordination_decision.py`. Reuse existing active-runtime, causal,
timing, analytical-boundary, and run-control models. Do not edit API, UI,
presentation, authoring, `llm_client`, or generated `web/` assets.

**Implement:**

1. Strict scenario-local Pydantic records for condition configuration, issues,
   verification items, source dispositions, commitments, meeting schedule, and
   decision proposals.
2. One pure fixture builder per condition with identical people, initial
   dossier, schedule, spatial topology, decision goal, and safety bounds.
3. Three concrete pressure-source records and one execution-inert source-
   ensemble boundary. Baseline disables their activity through configuration;
   it does not delete unrelated world components or alter people's minds.
4. One execution-inert partnership boundary containing the five people,
   decision records, routes, and exact mechanisms.
5. A canonical-dump comparison proving that only the reviewed condition record
   differs across arms, plus a stable scenario fingerprint for each arm.

**Positive fixture:** all three conditions validate, expose positive-duration
routes, four scheduled meetings, a day-10 deadline, five people, and no
aggregate active-system ID.

**Negative fixtures:** duplicate meeting time, zero-duration delivery,
undeclared source/recipient, aggregate boundary used as port owner, final status
present initially, arbitrary decision predicate, an invalid condition/flag
combination, and condition drift outside the reviewed record all fail before
execution.

**Verification:**

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_coordination_decision.py -k contract
.venv/bin/python -m mypy src/cybernetic_influence/scenarios/coordination_decision.py
git diff --check
```

**Done when:** both-sign fixtures pass, no existing file was changed except a
necessary package export, an isolated code-diff audit finds no blocker, and the
packet is committed before 21A1. Stop rather than adding a generic mechanism or
predicate language.

#### Assignment prompt for the implementation agent

> Implement Packet 21A0 only, exactly as specified in
> `docs/plans/021-coordination-environment-assay.md`. First verify that the
> starting commit is a clean descendant of canonical `main`, that Slice 20A–20D
> is complete there, and that no other writer has claimed the paths you need.
> If any precondition fails, stop and report the exact failing precondition.
>
> Create the strict scenario-local contracts and pure baseline,
> heterogeneous-pressure, and stabilization fixture builders in
> `src/cybernetic_influence/scenarios/coordination_decision.py`, plus focused
> both-sign contract tests in `tests/test_coordination_decision.py`. Add a
> package export only if importability requires it. Preserve identical people,
> initial dossier, schedule, spatial topology, decision goal, and safety bounds
> across conditions; expose differences only through the reviewed condition
> surfaces. Include the five people, four positive-duration meeting times, the
> day-10 deadline, three concrete pressure-source records, one execution-inert
> source-ensemble boundary, and one execution-inert partnership boundary. No
> analytical boundary may own a port or active-system ID.
>
> Implement the positive and every named negative fixture in 21A0. The
> fingerprint and canonical-dump tests must fail for condition drift outside
> the strict condition record or for an invalid condition/flag combination. Do
> not implement scheduling, runtime bindings, agent policies, LLM calls, API, UI,
> presentation, authoring, measurement, comparison, generic predicates,
> generic mechanisms, or changes to `llm_client`. Do not weaken an existing
> contract to make a fixture pass. Do not spend money or deploy.
>
> Run exactly the focused pytest, mypy, and `git diff --check` commands listed
> in 21A0, then inspect the complete owned diff for silent fallback, hidden
> aggregate execution, invented global trust/risk/coordination state,
> zero-duration causal paths, unrelated edits, and missing negative controls.
> Fix owned defects, rerun the checks, commit the coherent packet, report the
> commit plus exact evidence, and stop. Do not begin 21A1.

### Packet 21A1 — Scripted recurring runtime

**Classification:** agent-drivable runtime vertical.

**Precondition:** committed 21A0 fixtures. Reopen and validate those exact
fixtures rather than recreating them in runner code.

**Allowed edits:** scenario module, its package export, and focused scenario
tests. A minimal reusable runtime change is allowed only after a failing test
demonstrates the requirement and the change remains scenario-neutral.

**Implement:**

1. A deterministic scheduler process that wakes at days 0, 3, 6, and 9 and
   exposes the due people from one frozen pre-moment state.
2. Exact bindings for message delivery, verification request/response,
   issue-state transition, source disposition, commitment, scope/threshold
   proposal, informal alignment, partner withdrawal, terminal decision, and
   day-10 no-decision transition.
3. Fixed scripted people and pressure sources that exercise every required
   mechanism without calling a model.
4. A typed Slice-20 run-control plan with terminal fact, day-10 horizon,
   safety bounds, and quiescence fallback.

**Worked path:** in the pressure fixture, a concern reaches its intended person;
that person requests verification; the request and later response travel
through exact routes; an issue is opened and later resolved or reopened; at
least one commitment changes; the exact decision or deadline mechanism commits
the terminal state. Every transition has positive modeled duration and exact
parents.

**Acceptance:**

- each arm completes at zero cost with four meeting cycles and at least twelve
  meaningful causal moments;
- baseline includes ordinary review friction rather than automatic success;
- no person observes same-moment proposals from another person;
- disabling one pressure route prevents its delivery and downstream access;
- denied terminal proposals do not mutate final state;
- replay reconstructs the final state and checkpoint/resume duplicates no
  event, attempt, or meeting;
- no trust, risk, readiness, BDM-driver, or organization-agent value appears in
  canonical world state.

**Verification:** focused scenario, causal-runtime, replay, and checkpoint tests
plus mypy and `git diff --check`. Audit and commit before API/UI work.

### Packet 21A2 — Existing simulator integration

**Classification:** first analyst-facing Slice-21 vertical.

Register the scripted scenario through the existing config, preview, run,
progress, retained-history, presentation, and Simulation UI paths. Reuse the
three existing graph meanings and Slice-20 narration/completion surfaces. Do
not create a separate workbench, endpoint family, graph renderer, or batch
store.

**Allowed edits:** API, presentation, frontend source, generated graph assets
only through `npm --prefix frontend run build`, and focused API/presentation/UI
tests. Do not edit conversational authoring.

**Acceptance:** an analyst selects any arm, sees spatial and configured maps
before execution, starts one zero-cost run, watches retained progress, reads the
multi-episode concise and detailed narratives, sees the explicit completion
reason separately from the decision outcome, selects either analytical
boundary, and steps every material claim down to exact evidence. Browser
refresh and server restart reopen the same run without execution.

### Packet 21A3 — Native participant seam and canary gate

Bind the five reviewed people to the existing `NativeLlmActiveSystem`; keep
the scheduler, sources, and exact mechanisms model-free. Structural fake-call
tests must prove each person receives only private memory, delivered
observations, reviewed BDM-informed descriptions, and owned interfaces. Do not
run a paid canary in this packet. Report the maximum participant and narrator
call topology, model/reasoning options, and hard cost cap, then stop for explicit
authorization.

**Acceptance:** all five native people use the existing strict action schema;
fake calls prove bounded observations and owned interfaces for each position;
no condition flag, aggregate measure, other person's private memory, or hidden
canonical fact reaches a person prompt; exact sources and mechanisms make no
model call; preview reports a worst-case participant/narrator topology no
greater than 48/32; and the packet performs no deployment or provider call.

### Packet 21A4 — Authorized baseline canary and human readout

**Classification:** representative live vertical; separate authorization
required.

After 21A3 is committed, report the exact revision, model/reasoning, participant
and narrator maxima, route-certification state, and hard spend cap. With explicit
authorization, certify only changed schemas, deploy that exact revision to the
private Mac, verify the config endpoint, and run one live baseline canary. Use
DeepSeek V4 Flash `none` unless the operator approves another reviewed option.
Inspect every participant and narrator trace, reopen the retained run after a
restart, and compare its structure with the zero-cost scripted baseline.

**Acceptance:** one valid live trajectory contains four meeting cycles and 12–28
meaningful narrated moments; completes through an exact terminal condition;
reports unique calls/events and provider-observed cost; exposes all three graph
meanings, evidence context, participant traces, and completion reason; and a
human can explain the arc without raw JSON and dispute one passage through exact
evidence. On provider/schema failure, retain the trace and stop—do not rerun,
switch models, or change the scenario without new authorization.

### Slice 21A terminal acceptance

**Done when:**

- every condition runs beyond one transaction through multiple meeting cycles;
- the configured messages and routes differ without a global trust variable;
- exact terminal and horizon paths work;
- the causal DAG shows source interaction, delivery, requests/reopenings,
  commitments, and decision;
- analytical boundaries for the partnership and pressure-source ensemble are
  reversible and execution-inert; and
- an analyst can explain one scripted trajectory from detailed narrative and
  exact evidence.

The 21A human readout must occur before 21B. If the scripted arc is not
understandable without raw evidence, repair the scenario or presentation; do
not add measurements to compensate for an incoherent trajectory.

## Slice 21B — Evidence-bound measurement vertical

**Classification:** direct outcome extension.

### Packet 21B0 — Frozen measurement contract and controls

Create strict scenario-local measurement models and frozen both-sign fixtures;
make no provider call and add no UI. The specification must enumerate every
measure in this plan with stable ID, construct, provenance class, unit,
limitations, and required source event kinds. Exact and evidence-coded fields
must be structurally distinct. Freeze positive, negative, environmental-event,
corruption, incomplete-run, and scenario/spec-fingerprint mismatch fixtures.

**Acceptance:** producers forbid extras; consumers tolerate future extras;
system-assigned IDs are absent from the LLM schema; exact values cannot be
accepted from coder output; `unclear` is valid; invalid/cross-run event IDs,
wrong spec revision, incomplete run, and mismatched scenario fingerprint fail
visibly. Run focused model/fixture tests and mypy, audit, commit, and stop.

### Packet 21B1 — Exact calculator and evidence-coder seam

Implement pure exact calculators, the strict shared-client coder call, and one
retained `RunMeasurement` artifact in the existing run store. Use fake coder
responses and frozen traces only; do not deploy or spend. Exact calculators
derive values from typed events/state. The coder receives only analyst-visible
evidence and returns prose/direction; the simulator attaches the supplied-
evidence context using the Slice-20 provenance pattern. Rerendering a retained
measurement makes no model call.

**Acceptance:** all controls in 21B0 produce their expected result; a concerning
message with no consequence does not become a directional system effect; the
environmental control remains unattributed/unclear; corrupt evidence invalidates
only the analysis, never the world run; task, trace, schema revision, model,
budget, and observed cost fields are retained; no value feeds back into world
state or people. Run focused analysis/run-store tests and mypy, audit, commit,
and stop.

### Packet 21B2 — Measurement readout and authorized canaries

Integrate the retained artifact into the existing run API, Simulation result,
and Run history. Show exact and evidence-coded sections with provenance labels,
limitations, invalid/unclear states, and step-down to source evidence. Do not
create a separate analysis application or store. First pass all UI/API tests
with retained fixtures and build the frontend. Then report the maximum coder
calls and hard cap and stop for authorization.

After authorization, deploy the exact revision and run one live pressure and
one live stabilization canary. The valid 21A4 baseline may be reused only when
its scenario, model, reasoning, measurement spec, and executable revision match;
otherwise request authorization for a new baseline. Inspect all participant,
narrator, and coder traces. A human must confirm that exact and coded measures
cannot be mistaken for each other and that one coded claim can be disputed from
its supplied evidence.

**Owned paths:** create a narrow
`src/cybernetic_influence/analysis/coordination.py` module and typed
`src/cybernetic_influence/analysis/models.py`; integrate retained artifacts
through the existing run store/API rather than a second run database; add the
measurement prompt under the active-runtime prompt conventions; extend `web/`
only through the generated frontend build after adding the
provenance-labeled readout and exact-evidence step-down in `frontend/src/`; and
create
`tests/test_coordination_measurement.py`.

**Slice 21B is done when:**

- every metric declares construct, provenance class, unit, and limitations;
- exact and coded values cannot be confused;
- all coded claims cite valid retained evidence;
- the known positive and negative controls produce their expected result;
- rerendering a retained measurement makes no provider call; and
- full measurement traces pass direct inspection.

## Slice 21C — Baseline, pressure, and stabilization comparison

**Classification:** representative comparison.

### Packet 21C0 — Comparison contract and zero-cost matrix

Freeze the comparison schema, validity rules, batch fingerprint, and replicate
count before paid execution. For the MVP use two valid trajectories per
condition (six total); this is an exploratory paired PoC, not statistical
inference. Run a six-run scripted matrix at zero cost. Calculation must preserve
per-run values, invalid runs, missing indicators, subgroup disagreement,
between-run range, and native units. It may label only
`candidate_directional_pattern`.

**Acceptance:** mismatched model/reasoning/scenario/spec fingerprints cannot
enter one comparison; invalid runs remain visible but excluded; changing one
fixture changes only its expected arm/readout; stabilization is not assumed to
succeed; no scalar trust/risk/readiness or agency score exists. Run focused
comparison tests, audit, commit, and stop before UI or paid execution.

### Packet 21C1 — Authorized repeated live matrix

Report the exact six-run topology, existing valid canaries eligible for reuse,
additional calls, route state, revision, and hard spend cap. Obtain explicit
authorization. Deploy the exact revision and collect two valid live trajectories
per condition with the same model, reasoning, scenario revision, and measurement
spec. Do not automatically replace an invalid run: retain it, report its cost
and cause, and request authorization for any replacement. Inspect full traces
and freeze the resulting batch.

### Packet 21C2 — Comparison readout, sign-off, and MVP closeout

Add the comparison to existing Run history with condition summaries,
trajectory/range views, invalid-run counts, subgroup disagreement, limitations,
and step-down to each retained run and exact evidence. Use independent
evaluation sign-off before the comparison changes a continue/stop decision.
Then obtain the human MVP readout: the operator can explain the synthetic result
from narrative/maps, dispute a measurement, identify why each run stopped, and
finds no demo-blocking comprehension or control defect. Record that evidence,
mark Slices 20–21 complete, update the roadmap and plan index, commit, and stop.

**Owned paths:** keep comparison calculation in the new analysis package,
expose it through the existing API and run-history surface, and add
`tests/test_coordination_comparison.py`. Do not create a separate comparison
application or a hidden batch-run store.

**Slice 21C is done when:**

- configuration fingerprints and valid-run rules are enforced;
- per-run results and uncertainty are visible;
- no aggregate hides subgroup disagreement or invalid runs;
- stabilization is described as a tested condition, not assumed success;
- the readout says only whether this synthetic model exhibited the proposed
  directional patterns; and
- consequential interpretation receives independent evaluation sign-off before
  it changes the roadmap.

## Later extensions, gated by 21C

### 21D — Evasion challenge conditions

Add one evasion dimension at a time behind the same scenario and measurement
contract:

1. temporal fragmentation;
2. segmented targeting/local equilibria;
3. oscillation;
4. variable switching; and
5. environmental masking.

Each extension requires a baseline-matched control and a named detector failure
it tests. Do not implement all five as feature breadth before one changes the
analysis in an inspectable way.

### Slice 22 — Composite-agency perturbation assay

After Slice 21C passes, follow the separate
[Slice 22 plan](022-composite-agency-perturbation-assay.md). It applies
[ADR 006](../adr/006-boundaries-are-derived-coarse-grainings.md) to the exact
same scenario and analytical boundary through matched component, structure,
feedback, and shock perturbations. Slice 22 owns its capability definition,
contracts, stopping rule, and lower-agent packets; this plan does not duplicate
or silently broaden them.

## Verification

The packet-level minimum commands are fixed below. A packet may add a narrower
regression command when its failing test requires it, but may not substitute a
smaller command for these checks.

| Packet | Required commands before audit/commit |
|---|---|
| 21A0 | `PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_coordination_decision.py -k contract`; `.venv/bin/python -m mypy src/cybernetic_influence/scenarios/coordination_decision.py`; `git diff --check` |
| 21A1 | `PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_coordination_decision.py tests/test_causal_runtime.py`; focused checkpoint/replay test file if separate; `.venv/bin/python -m mypy src/cybernetic_influence/scenarios/coordination_decision.py`; `git diff --check` |
| 21A2 | `PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_coordination_decision.py tests/test_api.py tests/test_presentation.py`; `npm --prefix frontend run build`; `git diff --check` |
| 21A3 | `PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_coordination_decision.py -k native`; `.venv/bin/python -m mypy src/cybernetic_influence/scenarios/coordination_decision.py`; `git diff --check` |
| 21A4 | Re-run 21A2/21A3 checks; then retain route-certification, config-revision, run, restart/reopen, full-trace, cost, and human-readout evidence |
| 21B0–B1 | `PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_coordination_measurement.py`; `.venv/bin/python -m mypy src/cybernetic_influence/analysis`; `git diff --check` |
| 21B2 | Prior row plus `PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_api.py tests/test_presentation.py`; `npm --prefix frontend run build`; then authorized full-trace/readout evidence |
| 21C0 | `PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_coordination_comparison.py tests/test_coordination_measurement.py`; `.venv/bin/python -m mypy src/cybernetic_influence/analysis`; `git diff --check` |
| 21C1 | Re-run 21C0 checks; then retain authorization, batch fingerprint, every run/trace/cost, invalid-run disposition, and frozen batch |
| 21C2 | Prior UI/API checks plus `npm --prefix frontend run build`, independent sign-off, human readout, `make check`, and `git diff --check` |

Focused checks cover scenario compilation, run control, exact measurement
calculators, evidence coding, comparison validity, UI/API parity, replay, and
corruption. Terminal acceptance requires:

```bash
make check
```

For every live canary, inspect complete `llm_client` traces for people,
narration, stop evaluation if present, and measurement coding. Before a
comparison supports a continue/stop decision, use independent evaluation
sign-off against the frozen batch and readout.

## Deferred

- empirical calibration to a real institution;
- real influence attribution;
- a universal trust/risk/coordination scale;
- a production detector or CSO operating system;
- automated policy recommendations;
- generalized swarm infrastructure;
- public deployment or multi-user operation; and
- all evasion and [Slice 22](022-composite-agency-perturbation-assay.md)
  composite-agency work until 21C passes.
