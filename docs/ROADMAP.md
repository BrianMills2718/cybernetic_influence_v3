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

V0.10 candidate behavior observed locally:

- two concrete scenario families: Service Desk and physical access;
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
  process.

The private Mac remains on the last verified V0.9 build until the V0.10
candidate completes its bounded live canary and exact-revision deployment
checks. The causal core also still drains one action's complete routed cascade
before accepting another; arbitrary interleaving within nonzero-delay routes is
not yet supported. The UI is technically reviewable; operator comprehension
and analytical usefulness remain under iterative stakeholder review rather
than being treated as proven.

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

### 1. Autonomous multirate temporal substrate — candidate implemented

Integer scenario time, scheduled process wakes, recorded observation-arrival
times, activation causes, and due-set causal moments now exist in the Service
Desk candidate. Exact mechanism adjudication, replay, budgets, and narrative
evidence remain in place.

Local acceptance demonstrates a person acting from a retained scheduled
intention without an external delivery, while a faster state-machine process
updates three times without model calls. Promotion awaits the bounded live
trace and Mac deployment check.

### 2. Validate one autonomous representative scenario

Run the autonomous Service Desk with live people and sequential live narration.
Inspect whether the exact retained trace distinguishes simulated time, internal
wakes, process updates, causal moments, and exact events without invented
information access. This remains an integrated outcome check, not a scheduler
bakeoff.

### 3. Introduce a surrogate boundary only on demand

When a second concrete scenario genuinely needs an unmodeled subsystem, expose
one declared surrogate behind the same typed boundary a finer implementation
could later use. Its fidelity note must state preserved readouts, omissions,
provenance, uncertainty, and invalid questions.

No stock-market implementation is currently on the critical path. A stochastic
price process is a useful future example, not sufficient justification for a
generalized framework today.

### 4. Expand multiscale agency only through concrete pressure

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
- production hosting, public access, and multi-user operations.

## Decision Rule

Prefer the smallest concrete slice that improves the analyst's ability to run,
understand, and interrogate a faithful trajectory. Document future complexity
when it constrains current architecture, but implement it only when a
representative scenario supplies the requirement and an inspectable acceptance
case.
