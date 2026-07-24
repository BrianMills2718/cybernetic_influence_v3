---
doc_role: active_authority
authority: canonical
status: active
created: 2026-07-23
updated: 2026-07-24
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

Stage: MVP/PoC.

V0.13 plus live checkpoint continuation is implemented and deployed as the
current private demo candidate on the Mac development host at simulator
`1be312441fcc934ab2fb72e044db3b5dc14f7985` with shared-client revision
`9f61bd7c9419c93961a722a7ef6209adcf593382`. The API reports DeepSeek V4
Flash with `none` reasoning as the default and Terra as the other certified
route. DeepSeek `high` and `xhigh` remain explicitly experimental; `medium` is
rejected by shared-client policy. Exact scenario mechanisms make no model call.

Current participant/narrator route observations are:

- Terra: `routeobs1_7cc1c51f065c181a33ff422d` and
  `routeobs1_bb5643a65107960dadc76a36`;
- DeepSeek V4 Flash `none`: `routeobs1_029097c508a11554b6b9301f` and
  `routeobs1_ba61b37be133f07f47177352`.

The deployed DeepSeek baseline `run_954220d513c3` reached
`closed_confirmed` in eight causal moments with seven participant calls, eight
narrator calls, eight narratives, and `$0.0034581043` observed cost. The
deployed continuation canary `run_abcd00000000` later completed from a retained
live checkpoint with lifecycle `completed_from_checkpoint`, 12 causal moments,
105 events, 11 participant calls, 12 narrator calls, 12 narratives, and
`$0.0054597981` observed cost.

Technical execution is therefore observed for the configured live path and for
one live checkpoint continuation. The continuation canary's full
duplicate/cost-continuity trace inspection and a current-revision desktop
workflow pass remain open. Stakeholder reviewability is established; the final
operator usability judgment for this demo candidate is not yet recorded.

V0.12.2 remains the last fully narrated and browser-certified release. It adds
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
- autonomous due-set scheduling with scenario-declared integer time;
- a Service Desk baseline with eight causal moments, including a human
  internal wake with no new observation and a three-phase exact process with
  no model calls;
- one frozen simulated-second-1 activation set shared by that person and
  process;
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
AP clerk from delivered observations; all four moments remained causally
ordered at logical time 0 because route latency is deliberately unmodeled.
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

The causal core still drains one action's complete routed cascade before
accepting another; arbitrary interleaving within nonzero-delay routes is not
yet supported. The UI is technically reviewable; operator comprehension and
analytical usefulness remain under iterative stakeholder review rather than
being treated as proven.

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
- separate participant perceptions, proposed actions, mechanism decisions,
  world commits, and later observations;
- one evidence-cited narrative per causal moment;
- exact step-down from aggregate views and prose.

Negative cases: absent information routes must cause grounded rerouting rather
than invented access; speed pressure may produce an attempted unsafe action but
exact mechanisms must still deny it.

Non-claims: this probe does not establish realistic organizations, general
human psychology, calibrated human timing, arbitrary delayed-route
interleaving, continuous time, or fidelity outside its stipulated service
workflow.

## Current Demo Completion Boundary

“Finished” currently means a reviewable private PoC demo, not completion of the
North Star or a production simulator. The sole active packet is
[Slice 14](plans/014-pausable-live-runs.md), and the demo is complete when:

1. the current DeepSeek-default Service Desk run exposes synchronized spatial
   and causal maps, grounded moment narratives, participant/composite traces,
   exact evidence, effective configuration, and observed cost;
2. a live run pauses at a validated causal boundary and resumes without
   duplicated pre-pause causal events or provider logical calls, with continuous
   narration and receipt-supported observed cost;
3. the current desktop path—choose scenario, Play, map, narrative, traces,
   pause/resume, and Run history—has no demo-blocking error, scroll jump, or
   misleading lifecycle control;
4. the roadmap, plan index, README, and deployed configuration agree; and
5. the operator uses the current build for five to ten minutes and finds no
   remaining demo-blocking comprehension or control defect.

The live run/data portion of check 1 and the pause/resume execution portion of
check 2 have current deployed evidence. Full continuation-trace inspection, the
integrated desktop presentation pass, and the final operator judgment remain
open. Once those pass, mark Slice 14 and the current demo complete. Do not add
another substrate or feature packet to this gate.

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

### 6. Finish the integrated private demo — active

[Slice 14](plans/014-pausable-live-runs.md) is the sole active packet. Live
pause/resume is implemented and one retained run completed from its checkpoint.
The shortest remaining path is full continuation-trace inspection, one current
desktop workflow pass, and the operator's short usability judgment. Passing the
[Current Demo Completion Boundary](#current-demo-completion-boundary) ends this
PoC demo stage.

### 7. Add conversational scenario drafting behind a typed compiler — post-demo next

After the current demo is marked complete, design one representative authoring
vertical:

```text
conversation -> typed scenario draft -> validation and unresolved questions
  -> spatial/causal preview -> analyst approval -> compiled scenario -> run
```

Reuse the current causal-state, active-system, fidelity-note, representation,
spatial, and analytical-boundary contracts. Begin with a small library of
approved mechanism templates and one bounded novel workflow. Unsupported
mechanisms remain unresolved or explicitly coarse; they never become silently
generated adjudication code.

Do not activate this packet until the demo completion gate is closed. Its
bounded design must freeze a human-reviewed target draft and one ambiguity case
before implementation.

### 8. Expand multiscale agency only through concrete pressure

Add overlapping/nested aggregate views, richer composite analysis, additional
process implementations, or representation refinement only when a scenario
requires them to answer an analyst question that current contracts cannot.

Do not start another substrate or ontology packet while demo completion and
conversational authoring are the shorter routes to the observed user need.

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
- systemic-influence attribution or aggregate-agency scoring; the open question
  is retained in [ADR 006](adr/006-boundaries-are-derived-coarse-grainings.md)
  without changing the component-grounded execution model;
- production hosting, public access, and multi-user operations.

## Decision Rule

Prefer the smallest concrete slice that improves the analyst's ability to run,
understand, and interrogate a faithful trajectory. Document future complexity
when it constrains current architecture, but implement it only when a
representative scenario supplies the requirement and an inspectable acceptance
case.
