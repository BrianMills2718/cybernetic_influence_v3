---
doc_role: active_authority
authority: canonical
status: active
created: 2026-07-23
updated: 2026-07-25
---

# Cybernetic Influence V3 Roadmap

## North Star

For an analyst studying multiscale agency, turn a concrete scenario containing
people, information, objects, software, and institutions into an inspectable
simulation where:

- atomic agents and mechanisms produce the realized world trajectory;
- organizations and other aggregates are derived views, not hidden executors;
- information and action flow can be followed through causal and spatial maps;
- every human-readable account steps down to retained exact evidence;
- each subsystem states what it represents faithfully and what it abstracts.

The simulator is a tool for understanding possible causal trajectories, not a
claim to reproduce every omitted computation or predict a real system.

## Current Stage and Truth

Stage: MVP/PoC. [Slice 19: live authored people]
(plans/019-live-authored-people.md) is technically complete on the current
implementation branch. An analyst can conversationally produce either of two
reviewed scenario templates, inspect and directly edit BDM-informed person
assumptions, approve the compiled graph, and choose a zero-cost reference or a
live run. Live people receive only reviewed descriptive context, private
memory, delivered observations, and currently exposed interfaces; exact
mechanisms alone deliver information and commit world effects.

The current branch is a candidate, not yet the canonical `main` revision or Mac
deployment. [Mac development operations](operations/mac-mini.md) owns the
separately dated last-observed deployed revision and route evidence. Do not
infer that a branch canary is deployed merely because it is documented here.

Technical execution is observed for both authored templates and for the
configured Service Desk live/pause/resume path. Resume now rechecks explicit
live-spend authorization and current route certification, preserves the
retained model policy, and holds the single-live-run lock through narration.
Exact scenario mechanisms make no model call.

The next gate is stakeholder observation of the complete authored flow:
describe or revise a scenario, edit its people, approve it, inspect Spatial
topology and Configured interaction pathways, run it live, then decide whether
the narrative, Realized causal graph, and participant/composite traces make the
modeled behavior understandable. The existing trace evidence establishes
bounded technical execution, not empirical psychological validity, predictive
accuracy, or a claim that any one profile field caused an action.

V0.12.2 is retained as the earlier narrated and browser-certified baseline. It adds
the separate run-history workspace and stable in-place scale/time inspection
from UI repair commit `c55dddd7de0abb66cf615511a11842a3f0c743e7`,
while preserving the earlier event-driven and narrative-fidelity behavior.

- three concrete scenario families: Service Desk, physical access, and
  purchase to payment;
- exact mechanisms separated from LLM-modeled people;
- typed information carriers, declared routes, protected values, and replay;
- spatial topology separated from communication, capability, and permission;
- execution-inert aggregate graph views;
- retained causal traces and sequential LLM causal-moment narration;
- autonomous due-set scheduling with a separate scenario clock and unique
  causal timestamps for successive moments and exact subevents;
- a Service Desk baseline with eight causal moments, including a human
  internal wake with no new observation and a three-phase exact process with
  no model calls;
- one frozen process-tick-1 activation set shared by that person and process;
- a purchase-to-payment probe that separates human approval, copied policy and
  signing evidence, exact internal payment authorization, and a declared coarse
  external processor;
- three execution-inert purchase views—operating unit, finance operations, and
  end to end—with all exact components still selectable after expansion;
- deterministic settled, human-denied, and externally-declined arms, including
  negative checks proving that a forced unauthorized request is stopped before
  the processor;
- one authored purchase requester start followed only by
  observation-delivery activations, bounded quiescence, and no
  `manual_schedule` causes.

The bounded live baseline `run_3be342635ebb` exercised behavior commit
`1e7a99e0cd0949f9f2e79f02f65c24284d9f4a8c` with seven human cognition calls
at medium reasoning and eight causal-moment narration calls at low reasoning.
All 15 structured calls validated on their first provider attempt. The run
reached confirmed closure in eight causal moments and ten participant
activations, including three autonomous wakes and three exact-process
activations, for $0.085632375. Full-trace inspection confirmed that each human
acted only through supplied interfaces and representations, each narrator saw
the exact prior narrative chain plus the current moment, all citations remained
inside the cited moment, and the exact process made no model call. The retained
run reopened through the operator-facing tailnet URL with all eight narratives
and the exact process visible in the graph and participant traces.

The purchase-to-payment live canary `run_ac10cc7a4b23` exercised V0.11 with
four human cognition calls at medium reasoning and four causal-moment narrator
calls at low reasoning for $0.041418125. All eight structured calls validated
on their first provider attempt. Full-trace inspection confirmed that each
person used only retained or delivered documents and an exposed interface, the
exact internal gate alone authorized the payment instruction, narrator
citations stayed within each current moment, and the coarse processor made no
LLM call. The retained run reopened in the deployed UI with four narratives,
all three analytical scales, spatial and causal projections, and exact
participant traces.

The autonomous purchase-to-payment canary `run_609b4503dda6` exercised V0.12
behavior commit `e6c935f6352e937f2307342757f2f04ddaa02285` with four human
calls at medium reasoning and four narrator calls at low reasoning for
$0.04058125. It began only with the requester, then activated the approver and
AP clerk from delivered observations; all four moments remained at scenario
clock 0 because route latency is deliberately unmodeled, while their causal
order is the unique sequence `c1` through `c4`.
All eight structured calls validated with zero retries. Full-trace inspection
confirmed bounded information/interface access, complete prior-narrative
context, current-moment-only citations, exact-gate authorization, and zero
processor LLM calls. The deployed run reopened with four narratives, four
analytical scales, both layouts, exact traces, and no browser errors.

The narrative-fidelity canary `run_d187cea6b5ec` exercised V0.12.1 repair
commit `fc985ac89d11a649b1afd232b6620fa05966d8e7` with four human calls at
medium reasoning and four narrator calls at low reasoning for $0.04639125.
All eight calls validated with zero retries. Full-trace inspection confirmed
that the narrator received the coarse processor's stipulated abstraction and
known omissions, received only a boolean indication of protected private-state
change, preserved the complete prior-narrative chain, and cited only its
current moment. The retained account called the processor “stipulated coarse”
rather than exact and distinguished the final AP clerk's protected memory
update from the absence of an external action or world-state effect. Desktop
and mobile browser checks reopened the run with four narratives, both layouts,
no horizontal overflow, and no console or network errors.

V0.12.2 desktop and mobile browser checks measured zero page-scroll movement
after analytical-scale and causal-moment changes. They also opened the separate
run-history view, reopened a legacy retained run, and found no console or
network errors. The repair removes an unintended trace-card auto-scroll and
normalizes legacy untyped routes at the graph presentation boundary.

The causal core now retains future exact effects and deliveries across
checkpoints and can settle exact-only work between participant activations. The
multirate Service Desk now satisfies the positive-duration world-time contract
using its declared minimum duration; any trace-serialization delay is retained
separately from that scenario assumption. It exposes its realized event DAG. Physical
access and purchase-to-payment remain legacy zero-duration traces until a
concrete timing slice migrates them.
The UI is technically reviewable; operator comprehension and analytical
usefulness remain under iterative stakeholder review rather than being treated
as proven.

## Completed Foundation: Positive-Duration Modeled Time

[Slice 15](plans/015-calibrated-elapsed-time.md) established the Service Desk's
retained positive-duration contract and realized activity/event causal graph.
Timing values are ordinary typed scenario configuration: humans may supply
empirical values when available, and authoring may propose estimates for
review. This foundation does not make the current durations empirically
calibrated, and other legacy scenarios may still retain zero-duration traces.

Stakeholder observation has occurred repeatedly on the deployed workflow: the
operator ran and inspected authored scenarios and directly shaped the map,
narrative, configuration, and lifecycle controls. This licenses the current
integrated demo completion pass and the later conversational-authoring
direction. It does not establish analytical usefulness on a real research
question.

## Canonical MVP Probe

Starting state: one stale-session login incident, concrete people, policy and
incentive copies, credentials, records, exact routing/remediation/closure
mechanisms, and authored spatial topology.

Operator action: select the baseline, missing-direct-path, or speed-pressure
condition and play a live or zero-cost reference simulation.

Inspectable result:

- causal and spatial projections synchronized to causal moments;
- a realized activity/event causal graph whose explicit parent edges and
  elapsed positions agree with the exact trace;
- separate participant perceptions, proposed actions, mechanism decisions,
  world commits, and later observations;
- one evidence-cited narrative per causal moment;
- exact step-down from aggregate views and prose.

Negative cases: absent information routes must cause grounded rerouting rather
than invented access; speed pressure may produce an attempted unsafe action but
exact mechanisms must still deny it; a zero-duration causal child must be
rejected before scheduling.

Non-claims: this probe does not establish realistic organizations, general
human psychology, calibrated human timing, continuous time, or fidelity outside
its stipulated service workflow.

## Current Demo Completion Boundary

“Finished” currently means a reviewable private PoC demo, not completion of the
North Star or a production simulator. [Slice 16](plans/016-canonical-analyst-demo.md)
is the sole demo-completion boundary. It integrates the prior pause/resume and
timing implementation evidence into the operator's actual workflow. The demo
is complete when:

1. the current DeepSeek-default Service Desk run exposes Spatial topology,
   Configured interaction pathways, and a Realized causal graph, grounded step
   narratives, participant/composite traces, exact evidence, effective
   configuration, and observed cost;
2. a live run pauses at a validated causal boundary, visibly offers Resume
   after reload/history reopening, and resumes without
   duplicated pre-pause causal events or provider logical calls, with continuous
   narration and receipt-supported observed cost;
3. the current desktop path—choose scenario, Play, map, narrative, traces,
   pause/resume, and Run history—has no demo-blocking error, scroll jump, or
   misleading lifecycle control;
4. the roadmap, plan index, README, Mac operations page, and deployed
   configuration agree; and
5. the operator uses the current build for five to ten minutes and finds no
   remaining demo-blocking comprehension or control defect.

Earlier implementation evidence supports parts of checks 1 through 4, but the
operator's reported confusion reopens the integrated UI claim. Once this packet
passes, mark Slice 16 and the current demo complete. Do not add another
substrate or feature packet to this gate.

## Approved Outcome Extension

The approved direction beyond the current demo preserves the same analyst and
inspectable result while removing the remaining closed-catalog restriction:

The analyst can describe a bounded situation conversationally, review and
correct a typed scenario draft and its unresolved assumptions, approve its
graph, and run it only when every executable mechanism has a validated
implementation.

This is not permission for a chatbot to generate arbitrary runtime code.
Natural language will propose a typed draft; validation,
template-backed mechanism composition, explicit coarse boundaries, and human
approval remain separate gates.

## Binding Architectural Direction

- [ADR 006](adr/006-boundaries-are-derived-coarse-grainings.md): aggregate
  organizations are derived execution-inert views.
- [ADR 008](adr/008-separate-spatial-topology-from-routing-and-permission.md):
  spatial adjacency is not communication, capability, or authorization.
- [ADR 010](adr/010-autonomous-multirate-process-time.md): autonomous stateful
  processes evolve on their own timescales; causal moments batch due updates.
- [ADR 011](adr/011-declared-representation-depth.md): subsystem representation
  depth is explicit, question-relative, and replaceable behind typed boundaries.

## Critical Path

### 1. Autonomous multirate temporal substrate — complete for the MVP probe

Integer scenario time, scheduled process wakes, recorded observation-arrival
times, activation causes, and due-set causal moments now exist in the Service
Desk MVP. Exact mechanism adjudication, replay, budgets, and narrative
evidence remain in place.

Scripted and live acceptance demonstrate a person acting from a retained
scheduled intention without an external delivery, while a faster state-machine
process updates three times without model calls. Deterministic arm checks,
desktop/mobile browser checks, full live-trace inspection, and exact-revision
Mac deployment are complete.

### 2. Validate one autonomous representative scenario — complete

The autonomous Service Desk has run with live people and sequential live
narration. Its retained evidence distinguishes simulated time, initial triggers,
internal wakes, delivered observations, exact process updates, causal moments,
and exact events without invented information access. This is an integrated
outcome proof for the stipulated scenario, not a claim of calibrated human
timing or general fidelity.

### 3. Introduce a coarse subsystem boundary only on demand — complete

The purchase-to-payment scenario now exposes one coarse external processor
behind the same typed payment-instruction/result boundary a finer
implementation could later use. Its fidelity note states preserved behavior,
assumptions, omissions, validation basis, and the invalid question it cannot
answer: why an external decline occurred. Exact internal authorization remains
separate and no processor call occurs after a human denial.

The bounded live settled run and full agent/narrator trace inspection passed.
No generalized surrogate library or stock-market implementation is justified
by this concrete slice.

### 4. Extend autonomous causality to purchase-to-payment — complete

The purchase scenario now uses one authored requester start followed by the
existing due-set scheduler. Causal moment order is preserved without inventing
elapsed route latency: equal logical timestamps mean that purchase-workflow
timing is omitted at this representation depth.

The bounded design is [Slice 12](plans/012-event-driven-purchase-payment.md).
It reuses the existing runtime and UI, preserves all authorization and
processor-fidelity behavior, and stops at quiescence. Deterministic controls,
full live traces, deployed UI reopening, and fail-closed credential/access
checks passed.

### 5. Make one run configurable and self-explanatory — complete

Expose model, agent reasoning, and a bounded total-spend authorization through
one typed request contract and the existing simulator screen. The shared
`llm_client` registry and execution policy remain authoritative for model
eligibility; the simulator must not grow a provider capability database.
Scenario assumptions, known omissions, and fidelity questions are visible and
explained but remain read-only unless an authored scenario contract actually
supports changing them.

The completed bounded design is
[Slice 13](plans/013-configurable-explainable-runs.md). Terra and DeepSeek
`none` pass the participant/narrator schema boundary and complete deployed
canaries. DeepSeek is the default; `high` and `xhigh` remain experiments rather
than inheriting the `none` evidence. Its final desktop observation is
consolidated into the integrated demo gate rather than left as a competing
active packet.

### 6. Preserve the integrated private demo — implemented, usability judgment deferred

[Slice 14](plans/014-pausable-live-runs.md) remains the demo boundary. Live
pause/resume is implemented and one retained run completed from its checkpoint.
The operator explicitly advanced modeled-time work before recording the final
short usability judgment; that judgment remains a later acceptance check rather
than a competing active implementation packet.

### 7. Make world time and realized causal chains truthful — implemented evidence

Complete [Slice 15](plans/015-calibrated-elapsed-time.md) as the current
representative vertical:

```text
typed or runtime-resolved positive duration
  -> scheduled activity/world transition
  -> exact retained event and parent link
  -> elapsed-time causal graph, narrative, and inspector
```

This is one product slice, not scheduler work followed by a disconnected graph
project. If it stopped after Service Desk passed, the analyst would have a small
but useful simulation whose realized causal chain is temporally meaningful and
inspectable.

### 8. Canonical analyst demo — technically implemented; operator gate active

The MVP outcome is one clear answerable flow: an analyst chooses or later
authors a bounded Service Desk condition, presses Play, reads what changed and
why, then steps down through a map and exact evidence to answer why the outcome
occurred. This packet owns reliable pause/resume visibility, plain language,
and the three distinct graph views:

- **Spatial topology**: authored places, occupants, and physical links.
- **Configured interaction pathways**: scenario-configured relationships that
  may carry information or action when other mechanism conditions hold; they do
  not themselves grant authorization.
- **Realized causal graph**: retained events that occurred in this run, linked
  only by explicit causal-parent relations.

It also distinguishes unique causal order (`c1`, `c2`, …) from **modeled elapsed
time**. The initial display must not call uncalibrated process ticks seconds or
wall-clock timestamps.

### 9. Add conversational scenario drafting behind a typed compiler — technically implemented; operator gate active

This comes before comparisons: it removes the closed scenario catalog while
preserving human review of the executable world model.

```text
conversation -> typed scenario draft, including timing assumptions
  -> validation and unresolved questions
  -> spatial, configured-interaction, and planned-intervention preview
  -> analyst approval -> compiled scenario -> run
```

Reuse the current causal-state, active-system, fidelity-note, representation,
spatial, timing, and analytical-boundary contracts. Slice 17A proved the
approved `resource_request_v1` workflow with zero-cost scripted evidence; 17B
added conversational drafting, revision persistence, approval, and UI. Slice
17C adds the bounded `information_campaign_v1` workflow: exact claim delivery
through one configured channel followed by a recipient assessment record. It
does not infer persuasion, truth, virality, or geopolitical outcome.
Unsupported mechanisms remain unresolved or explicitly coarse; they never
become silently generated adjudication code.

Slice 18 makes each authored person’s scenario assumptions tractable before
approval. It uses the Behavioural Drivers Model as a selective vocabulary, not
an exhaustive personality taxonomy: perceived social conditions remain
fallible beliefs, while actual policies, incentives, relationships, information
deliveries, interfaces, and constraints remain external world state.

Slice 19 connects those reviewed profiles to live authored people through the
existing private-memory, delivered-observation, and exposed-interface boundary.
The approved-draft UI now distinguishes a fixed zero-cost reference from live
people with an explicit model, reasoning, and hard-cost selection. The
information-campaign canary retained the source's publication decision, exact
claim delivery, the recipient's grounded contested assessment, exact recording,
and sequential evidence-citing narration. Its analytical boundaries remained
execution-inert. This establishes technical execution, not empirical
psychological validity or a claim that any one profile field caused the action.

The next decision is stakeholder observation of the complete authored flow:
revise people, approve, inspect both maps, run live, and decide whether the
narrative and person traces make the modeled behavior understandable. Extend
the compiler beyond the two reviewed templates only after that check identifies
a concrete blocked scenario or approves the current interaction.

### 10. Comparative causal analysis — post-MVP

Compare approved conditions only after an analyst can author/review one bounded
scenario. The comparison must explain the outcome, modeled delay, and changed
path with exact evidence rather than presenting two disconnected graphs.

### 11. Run one Levin-style composite-agency assay — post-MVP

Use one authored scenario and its execution-inert analytical boundary to ask a
specific multiscale question: does the candidate composite preserve or restore
a declared outcome under shocks and member replacement, and which concrete
policies, information routes, memories, incentives, and feedback mechanisms
make that behavior possible?

The first assay must compare component-level, structural, and
feedback-disruption interventions across repeated trajectories. Its output is
an intervention-specific influence profile with uncertainty and exact
trace/graph step-down—not a claim that the aggregate is another executor, a
mind, or a single additive percentage of causation.
[ADR 006](adr/006-boundaries-are-derived-coarse-grainings.md) owns that
interpretation.

This is post-MVP. It follows conversational authoring and comparison because
those flows must first make an authored scenario and its intervention evidence
inspectable to the analyst.

### 12. Expand representation depth only through concrete pressure

Add overlapping/nested aggregate views, richer composite analysis, additional
process implementations, or representation refinement only when a scenario
requires them to answer an analyst question that current contracts cannot.

## Explicit MVP Deferrals

- continuous-time numerical solvers and physics engines;
- speculative parallel simulation and rollback;
- universal attention or cognition scheduling;
- generalized stochastic-process and surrogate libraries;
- learned-policy calibration infrastructure;
- automatic fidelity scoring or representation switching;
- stock exchanges, HFT systems, or market calibration;
- treating an organization, market, policy, or incentive system as an
  ungrounded acting mind;
- a universal scalar “agency score,” organization-level executor, or
  consciousness claim; the next research slice may test one
  intervention-specific composite-control hypothesis under
  [ADR 006](adr/006-boundaries-are-derived-coarse-grainings.md) without changing
  the component-grounded execution model;
- production hosting, public access, and multi-user operations.

## Decision Rule

Prefer the smallest concrete slice that improves the analyst's ability to run,
understand, and interrogate a faithful trajectory. Document future complexity
when it constrains current architecture, but implement it only when a
representative scenario supplies the requirement and an inspectable acceptance
case.
