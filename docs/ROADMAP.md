---
doc_role: active_authority
authority: canonical
status: active
created: 2026-07-23
updated: 2026-07-23
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

V0.12 is implemented, verified, and deployed on the private Mac development
host from behavior commit
`e6c935f6352e937f2307342757f2f04ddaa02285`.

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

The causal core still drains one action's complete routed cascade before
accepting another; arbitrary interleaving within nonzero-delay routes is not
yet supported. The UI is technically reviewable; operator comprehension and
analytical usefulness remain under iterative stakeholder review rather than
being treated as proven.

Technical execution is established for V0.12, and the deployed simulator is
stakeholder-reviewable. Stakeholder comprehension and analytical usefulness of
the autonomous purchase-to-payment vertical have not yet been observed.

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

### 5. Expand multiscale agency only through concrete pressure

Add overlapping/nested aggregate views, richer composite analysis, additional
process implementations, or representation refinement only when a scenario
requires them to answer an analyst question that current contracts cannot.

Return to stakeholder observation of the deployed analyst workflow before
another substrate or ontology packet starts.

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
