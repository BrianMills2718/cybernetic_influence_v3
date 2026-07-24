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

V0.13 is implemented and deployed as a release candidate on the private Mac
development host at simulator commit
`00ea2342a6c5e3125366e59820f1e49b12dec17c` with shared-client revision
`07b168ffc10ab28834d8571fdf48aa9b775d57bc`. It adds typed model/reasoning/spend
configuration, model-specific reasoning choices, accessible explanations,
scenario assumptions and omissions, retained effective configuration, and
pre-call total-budget admission while preserving the V0.12.2 history and
in-place inspection repairs.

The complete Linux and Mac simulator gates pass: mypy, 57 tests, the production
React Flow build, and launcher syntax. The shared-client certification seam has
44 relevant synchronous policy/attempt/route tests passing on the simulator
environment; seven async-only tests are uncollected there because that
environment does not install `pytest-asyncio`.

Only `openrouter/openai/gpt-5.6-terra` is currently advertised. Its exact
participant and narrator schema observations are
`routeobs1_a7a692e9a6893e15d36f30ab` and
`routeobs1_8d61ca73ab6c08249e5cdf59`. The catalog exposes low, medium, and high
agent reasoning for Terra, defaults to medium, and retains low narrator
reasoning. Exact scenario mechanisms still make no model call.

The exact-revision deployed canary `run_feb8ed10258d` completed the Service Desk
baseline and reached `closed_confirmed` in eight causal moments. Seven Terra
participant calls used medium reasoning and all eight moment narrations used
low reasoning for a fully provider-observed total of `$0.103861875`. Every one
of the 15 retained provider records completed on the native-schema path with
zero retries, warnings, or validation errors. Seven narratives cite only
events retained in their causal moment; the silent eighth cites its validated
synthetic silence marker. The retained configuration names the selected model,
reasoning levels, `$0.55` authorization, and exact shared-client revision.

DeepSeek V4 Flash is deliberately absent. On the final shared-client revision,
high-reasoning certification attempts repeatedly consumed their output
allowance without returning structured content at both 384 and 512 tokens.
Earlier observations on superseded revisions do not qualify. Do not advertise
DeepSeek until fresh exact-schema observations and one complete
participant-plus-narrator canary pass.

Rendered desktop certification is also still open: production assets
build, API/static checks pass, and prior V0.12 browser evidence exists, but both
headless Chrome and Safari automation hung from the current SSH session. Do not
upgrade this to a visual pass without a successful current-revision browser
run.

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

Technical execution is established for V0.12.2 locally and on the private Mac
development host. Stakeholder observation has now occurred on the deployed
workflow: the operator successfully ran and inspected authored scenarios, and
identified fixed LLM settings, insufficient control explanations, and the
closed scenario catalog as the next barriers to the intended modeling job.
This licenses the next product direction; it does not yet establish analytical
usefulness on a real research question.

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

## Approved Outcome Extension

The next product increment preserves the same analyst and inspectable result
while removing two observed restrictions in sequence:

1. The analyst can choose an available, policy-allowed structured-output model,
   agent reasoning level, and maximum total LLM spend; understand the meaning
   of each control and the scenario's read-only fidelity assumptions; then
   recover the effective configuration from the retained run.
2. After that configuration contract is proven, the analyst can describe a
   bounded situation conversationally, review and correct a typed scenario
   draft and its unresolved assumptions, approve its graph, and run it only
   when every executable mechanism has a validated implementation.

The second increment is not permission for a chatbot to generate arbitrary
runtime code. Natural language will propose a typed draft; validation,
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

### 5. Make one run configurable and self-explanatory — implemented, acceptance open

Expose model, agent reasoning, and a bounded total-spend authorization through
one typed request contract and the existing simulator screen. The shared
`llm_client` registry and execution policy remain authoritative for model
eligibility; the simulator must not grow a provider capability database.
Scenario assumptions, known omissions, and fidelity questions are visible and
explained but remain read-only unless an authored scenario contract actually
supports changing them.

The active bounded design is
[Slice 13](plans/013-configurable-explainable-runs.md). Its implementation and
deterministic gates are complete. Terra passes route/schema certification and
the complete deployed participant-plus-narrator canary. DeepSeek remains
unadvertised after unstable structured output. Current-revision rendered
browser verification is still open. Slice 13 remains the sole active packet
until a desktop pass is inspected; a second model is promoted only when
it independently passes the same gates.

### 6. Add conversational scenario drafting behind a typed compiler — next

After Slice 13 is completely observed in use, design one representative authoring
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

Do not activate this packet until configurable runs are technically verified
and reviewed by the stakeholder. Its bounded design must freeze a
human-reviewed target draft and one ambiguity case before implementation.

### 7. Expand multiscale agency only through concrete pressure

Add overlapping/nested aggregate views, richer composite analysis, additional
process implementations, or representation refinement only when a scenario
requires them to answer an analyst question that current contracts cannot.

Do not start another substrate or ontology packet while the configurable-run
and conversational-authoring path is the shorter route to the observed user
need.

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
