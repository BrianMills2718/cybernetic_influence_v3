---
doc_role: implementation_plan
authority: bounded_design
status: planned_after_slice_20
created: 2026-07-25
updated: 2026-07-25
---

# Slice 21: Coordination-environment assay

## Assignment boundary

Begin only after Slice 20's completion record and dual-level narration are
implemented and observed. Implement 21A and obtain its human readout before
21B. Implement 21B and inspect its full measurement traces before 21C. Do not
begin the evasion variants or Levin-style composite-agency assay until the
baseline/pressure/stabilization vertical passes.

Work in a clean linked worktree based on the current clean descendant of
`main`. For each of 21A, 21B, and 21C: implement only that packet, run its
focused positive and negative checks, audit the owned diff, commit, and report
before starting the next packet. Do not spend on live calls or comparison
batches without explicit authorization after reporting their maximum call and
cost bounds.

This plan is grounded in the complete
[source note](../research/001-from-minds-to-coordination.md) and
[ADR 012](../adr/012-decision-environment-measures-are-derived.md). The paper
supplies constructs and candidate indicators, not validated scales or causal
truth.

## Analyst outcome

An analyst can simulate a multi-episode collective decision under heterogeneous
information pressure, inspect how concrete interactions changed the decision
process, compare an ordinary baseline with pressure and stabilization
conditions, and see evidence-bound measures related to trust structure,
perceived risk, and coordination readiness.

The result is a traceable experimental model of possible dynamics. It is not a
prediction of a real institution, attribution of hostile intent, or empirical
validation of the paper.

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

The first vertical uses five LLM-modeled people:

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
twelve to forty moments. Do not create silence-only wakes to meet the minimum.

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

Build one reviewed typed template named `coordination_decision_v1`, its
recurring scheduler, exact mechanisms, three conditions, run-control plan,
existing maps, dual narratives, participant traces, and final decision record.
Use fixed scripted participant policies first. Do not extend conversational
authoring to this template until the typed fixture and mechanisms pass; after
they do, exposing the reviewed fields through the existing authoring/compiler
boundary is allowed but is not required for 21A acceptance.

**Owned paths:** create
`src/cybernetic_influence/scenarios/coordination_decision.py`; extend
`src/cybernetic_influence/causal_core/` only for a demonstrated reusable
runtime need; register the scenario in `src/cybernetic_influence/api.py` and
`src/cybernetic_influence/presentation.py`; add its existing-map and narrative
surface in `frontend/src/main.tsx` and `frontend/src/styles.css`; and create
focused
`tests/test_coordination_decision.py` plus API/presentation checks. Do not
modify `authoring/` during the initial typed-fixture packet or hand-edit the
generated `web/` files.

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

## Slice 21B — Evidence-bound measurement vertical

**Classification:** direct outcome extension.

Implement the versioned measurement specification, exact calculators,
evidence-coder schema, retained measurement artifact, UI readout, positive,
negative, environmental, and corruption controls.

**Owned paths:** create a narrow
`src/cybernetic_influence/analysis/coordination.py` module and typed
`src/cybernetic_influence/analysis/models.py`; integrate retained artifacts
through the existing run store/API rather than a second run database; add the
measurement prompt under the active-runtime prompt conventions; extend `web/`
only through the generated frontend build after adding the
provenance-labeled readout and exact-evidence step-down in `frontend/src/`; and
create
`tests/test_coordination_measurement.py`.

**Done when:**

- every metric declares construct, provenance class, unit, and limitations;
- exact and coded values cannot be confused;
- all coded claims cite valid retained evidence;
- the known positive and negative controls produce their expected result;
- rerendering a retained measurement makes no provider call; and
- full measurement traces pass direct inspection.

## Slice 21C — Baseline, pressure, and stabilization comparison

**Classification:** representative comparison.

Run the pre-registered matrix after reporting call topology and cost. Add an
operator-facing comparison that shows outcomes and measure trajectories by
condition, with step-down to each run and exact evidence.

**Owned paths:** keep comparison calculation in the new analysis package,
expose it through the existing API and run-history surface, and add
`tests/test_coordination_comparison.py`. Do not create a separate comparison
application or a hidden batch-run store.

**Done when:**

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

### 21E — Composite-agency assay

Apply [ADR 006](../adr/006-boundaries-are-derived-coarse-grainings.md) to the
partnership or pressure-source ensemble:

- replace individual members while preserving structure;
- change shared objective, policy, or incentive while retaining members;
- interrupt feedback or memory paths;
- apply a shock and measure recovery;
- compare outcome distributions and intervention effort.

The output is an intervention-specific influence/control profile. It is not an
organization executor, consciousness claim, or additive “system versus humans”
percentage.

## Verification

Focused checks should cover scenario compilation, run control, exact
measurement calculators, evidence coding, comparison validity, UI/API parity,
replay, and corruption. Terminal acceptance requires:

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
- all evasion and composite-agency extensions until 21C passes.
