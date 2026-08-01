---
doc_role: implementation_plan
authority: bounded_design
status: active
created: 2026-07-30
updated: 2026-07-30
---

# Slice 24: Configurable theory-informed simulation MVP

## Objective

For an analyst studying influence and multiscale agency, turn a conversational
description of a multi-episode organizational decision into an approved typed
configuration, execute it through the existing simulator, and render separate
Waltzman and Levin per-run findings over one retained evidence bundle.

This is the active implementation plan for
[the MVP goal](../GOAL.md). It replaces the former continuation from Packet
21C0 to a paid repeated comparison.

## Current progress

Packets 24A0, 24A1, 24B, and the technical portion of 24C are implemented. The strict
reviewed coordination configuration compiles onto the existing runtime, one
scripted trajectory produces `RunEvidenceBundleV1`, and separate Waltzman and
Levin reference readouts validate against that common evidence. The existing
Author scenario flow can load the reviewed configuration without a provider
call, distinguish scenario inputs, run controls, and selected analyses, then
approve, run, reopen, and inspect both readouts alongside the retained maps,
narrative, and participant/group accounts. Its structured authoring contract
can now generate the coordination template without provider-owned runtime IDs,
the full semantic configuration can be edited directly, and selected analyses
also project over a completed live trajectory.

The canonical Packet 24C draft is `draft_019c16228a62`; its approved revision 2
compiled to live run `run_e1a91d0a47e1`. The run, complete traces, narration
recovery, restart/reopen behavior, and rendered UI have been inspected. M1–M6
and M8 were initially reported as technically demonstrated. A subsequent
audit found that the canonical draft classified every terminal outcome as
goal-satisfying, so its Levin goal finding could not discriminate success from
mere termination. The same audit found omitted configured-graph relationships
and ambiguous terminal narration. Packet 24D repaired those contracts and
retained a corrected reference readout. M6 is now technically satisfied; M7
remains the operator's comprehension judgment.

## Current-to-target Delta

Current:

- conversational authoring compiles two short template-backed workflows;
- the coordination scenario is fixed in scenario-specific Python;
- Waltzman measurement consumes a coordination-specific evidence bundle;
- boundary activity exists, but no Levin-oriented per-run readout exists; and
- the fixed run, measurement, and comparison surfaces do not expose
  `ScenarioSpec`, `RunSpec`, `AnalysisSpec`, and `ExperimentSpec` as different
  concerns.

Target:

- `coordination_decision_v1` is a third reviewed authoring template;
- its approved configuration compiles into the existing coordination runtime;
- the retained run binds scenario, run, analysis, and evidence-bundle identity;
- Waltzman and Levin modules independently consume that common bundle; and
- the existing Simulation and Run history surfaces render both readouts.

## Canonical Configuration

The canonical positive fixture describes a multinational partnership making a
bio-surveillance deployment decision. The configurable fields include:

- decision topic, candidate collective goal, acceptable outcomes, constraints,
  horizon, meetings, and terminal conditions;
- five reviewed people occupying the existing tested decision positions, with
  BDM-informed descriptive profiles;
- sources and heterogeneous concerns;
- message content, recipient, source identity, route, timing, and repetition;
- decision records, verification feedback, commitments, and configured
  stabilizing resources;
- places, spatial links, and one execution-inert partnership boundary; and
- selected analysis modules and fidelity assumptions.

The template may map those reviewed values onto existing tested mechanism
implementations. It may not generate Python, invent an implementation, add an
organization executor, or accept arbitrary predicates.

## Domain Separation

### `ScenarioSpec`

Produced by the approved authoring compiler. Owns world semantics and contains
only reviewed fields that affect the simulation.

### `RunSpec`

Produced from the run form and server configuration. Owns execution controls:
execution mode, model, reasoning, horizon, budgets, authorization, and
checkpoint identity. It never silently changes scenario semantics.

### `AnalysisSpec`

Approved with the scenario but execution-inert. Each selected module declares:

- `analysis_id` and version;
- construct definitions;
- required evidence kinds;
- method class (`exact`, `calculated`, or `llm_coded`);
- aggregation and uncertainty;
- limitations; and
- the candidate boundary/goal references needed by the Levin module.

The initial closed set is:

- `waltzman_decision_environment_v1`;
- `levin_collective_competence_v1`.

### `ExperimentSpec`

Not implemented in Slice 24. No field in the other specifications may pretend
to own repetitions, perturbations, matching, or cross-run causal conclusions.

## Common Evidence Contract

Introduce a scenario-neutral `RunEvidenceBundleV1` as an additive retained
projection over existing authoritative records. It contains or references:

- run ID, scenario fingerprint, and approved draft/configuration digest;
- immutable `ScenarioSpec`, `RunSpec`, and selected `AnalysisSpec` snapshots;
- initial and terminal world-state evidence;
- exact events and causal parents;
- information representations, source identity, ownership, lineage, and
  deliveries;
- participant activations, observations, attempted actions, and retained
  public analytical output;
- mechanism attempts, decisions, commits, and rejections;
- analytical-boundary membership, crossings, and coordination episodes;
- modeled time, outcome, completion reason, and fidelity notes; and
- evidence attachment identities and integrity digests.

The bundle does not use narrator prose as source evidence. It may link to
narrative as a presentation artifact.

Producer models reject extras and validate all retained references. Consumer
models tolerate unknown additive fields but preserve required identity,
version, digest, and reference-integrity checks. A corrupt analysis bundle
invalidates only that analysis; it cannot rewrite a completed world run.

## Per-run Findings

Use one common finding envelope:

- framework and construct ID;
- method class;
- typed value or categorical state;
- evidence references;
- uncertainty/ambiguity;
- limitations;
- analysis-spec version; and
- optional LLM call evidence.

### Waltzman module

Retain the existing exact and coded measures where they remain truthful, but
adapt them to the common bundle. Cover:

- source reliance and authority divergence;
- verification behavior;
- locally expressed and expanded risk;
- precautionary/hedging behavior;
- decision latency and meeting/verification load;
- issue reopening, commitment divergence, withdrawal, and subgroup alignment;
- per-run trust-, risk-, and coordination-related trajectories.

Do not emit an invariant or causal influence claim from one run.

### Levin module

Produce an observational, per-run collective-competence profile:

- candidate boundary and candidate goal/constraints;
- boundary inputs, internal coordination episodes, and boundary outputs;
- concrete communication, memory, records, feedback, and mechanisms forming
  the observed collective glue;
- goal progress and terminal goal status;
- observed error signals and corrections;
- observed persistence, goal change, adaptation, or fragmentation;
- spatial, temporal, and state-space scope evidenced in the run; and
- component-level step-down for every composite-scale finding.

Absence of a perturbation means robustness, recovery from controlled shock,
member-replacement tolerance, and persuadability remain `not_tested`, not
negative.

## Failure Behavior

- Unsupported requested behavior remains an explicit unimplemented capability.
- Unknown references, duplicate IDs, invalid timing, incompatible routes,
  missing terminal conditions, missing collective goal, or analysis references
  outside the scenario fail before approval.
- A candidate collective goal that classifies every terminal outcome as
  goal-satisfying fails before approval; safe termination and goal satisfaction
  remain distinct.
- Configured nodes are classified as causal, analytical-only, spatial-only, or
  unexplained. Unexplained isolation is a visible lint finding, while an
  execution-inert analytical member is not mislabeled as dead causal state.
- A stale approved revision cannot run.
- A model-generation failure retains the previous valid draft plus diagnostics.
- A world-run failure remains a failed run; analysis does not start.
- One failed analysis module is retained as failed without hiding the completed
  run or another valid module.
- Reopening a retained draft, run, evidence bundle, or readout makes no provider
  call.

## Compatibility

- Existing authored templates and retained runs remain readable.
- Existing fixed coordination runs retain their current measurement artifact.
  An adapter may project them into `RunEvidenceBundleV1`; no migration is
  required for MVP completion.
- Existing exact scenario mechanisms, active-system bindings, event kinds,
  pause/resume checkpoints, maps, narratives, and run-history behavior remain
  authoritative.
- Existing comparison code is unchanged unless an additive consumer update is
  required to keep its tests passing; it is not exposed as active MVP work.
- Shared `llm_client` is consumed at its pinned working contract and is not
  modified.

## Ordered Packets

### Packet 24A0 — configuration, evidence, and finding contracts

**Classification:** direct blocker with an explicit return to 24A1.

**Status:** complete.

Implement:

1. strict authoring models and semantic validation for
   `coordination_decision_v1`;
2. compiler mapping into the existing coordination runtime;
3. additive `RunSpec`, `AnalysisSpec`, `RunEvidenceBundleV1`, and common finding
   contracts;
4. provider-free adapters for Waltzman and the initial deterministic/reference
   Levin findings.

Positive fixture: the canonical configuration validates, compiles into the
existing coordination runtime, runs through the existing scripted path, and
produces a valid common bundle plus both typed readouts.

Negative fixtures:

- missing candidate goal;
- terminal condition referring to an unknown outcome;
- message recipient or source outside the scenario;
- route with incompatible representation kind;
- analysis boundary/goal reference outside the configuration;
- attempted organization executor;
- invented mechanism implementation;
- corrupt evidence reference; and
- narrator prose supplied as measurement evidence.

Focused verification:

- authoring model/compiler tests;
- coordination runtime and measurement tests;
- evidence-bundle and Levin-readout tests;
- mypy over changed source packages;
- `git diff --check`.

Stop after an owned-diff audit, commit, and push. Do not edit the API/UI,
authoring prompt, provider route, or deployment.

### Packet 24A1 — provider-free configured review flow

**Classification:** representative vertical.

**Status:** complete.

Add API projections and the smallest existing-UI path from a reviewed
coordination draft through approval, a zero-cost reference run, the common
evidence bundle, and both readouts.

The pre-run surface must distinguish scenario inputs, run controls, and selected
per-run analyses. The result surface must preserve the existing narrative,
maps, participant/boundary accounts, and Advanced evidence while adding
separate “Decision environment” and “Collective competence” sections.

Positive fixture: the approved canonical configuration runs, retains both
readouts, reopens without execution, and exposes map/evidence step-down.

Negative fixture: one failed or corrupt analysis remains visible without
hiding or invalidating the completed reference run or the other valid module.

Focused verification:

- authoring and run API tests;
- evidence-bundle/readout API tests;
- presentation tests;
- focused frontend component tests where present;
- frontend production build;
- mypy over changed source packages;
- `git diff --check`.

Stop after an owned-diff audit, commit, push, and provider-free rendered
inspection. Do not modify prompts, certify, deploy, or make a live model call.

### Packet 24B — conversational generation and complete UI review

**Classification:** representative vertical.

**Status:** complete.

Extend the existing structured authoring prompt and repair loop to produce the
new template without inventing system IDs or executable implementations.
Expose direct editing for all decision-relevant configuration and analysis
fields. The preview must explain in plain language:

- what situation will be simulated;
- which fields are scenario inputs;
- which controls affect only this run;
- which findings will be calculated after the run; and
- which comparison/perturbation questions remain post-MVP.

The result page renders the normal narrative/maps first, followed by separate
“Decision environment” and “Collective competence” sections. Each finding
shows method, evidence, uncertainty, and limitations. Advanced evidence remains
collapsed by default.

Use fake structured calls for deterministic tests. Then report the exact
authoring and analysis call topology, schema digests, route, reasoning, and
maximum exposure. Stop before provider calls or deployment.

Provider-free evidence:

- authoring uses task `cybernetic_influence_v3_scenario_draft`, prompt
  `scenario_draft.v3`, prompt digest
  `889fa1392b2229421efbe100fa015763f3ff692057bac34f21f0e280c327a5b3`,
  and schema digest
  `538c97c19570d26d847b67c3b513e2bafc8b4a6354ff86add7a081ca3be663a9`;
- each authoring message uses an operator-selected subscription or OpenRouter
  route and thinking level. Packet 24C uses OpenRouter-backed Terra medium as
  the usable default after the subscription route reached its account limit.
  A message permits at most three structured attempts of at most 8,000 output
  tokens and a `$0.10` per-attempt request ceiling (`$0.30` maximum usage-based
  exposure per message);
- selected MVP analyses make zero model calls and use no route or reasoning
  level. `RunEvidenceBundleV1` has schema digest
  `75e70ba826efcf9f19e7cd2e52ed09c502d6e69eec5568079634e2ce74df5a96`;
  `FrameworkReadoutV1` has schema digest
  `dbd92a6e695096f3d0f580442bc7f23b31ddfceb8e131a2bc208970f45c510d1`;
- the existing live-run contract permits at most 150 participant calls at
  `$0.05` per request and 57 narrator calls at `$0.025` per request. Therefore
  one 24C run plus one usage-based authoring message has at most 210 external
  calls and `$9.225` in summed per-request ceilings. The retained `$0.74` run
  amount is a planning control, not a promise that the runtime terminates at
  that observed cost; and
- focused authoring, analysis, API, resume-regression, and presentation tests,
  strict mypy, production frontend build, positive and negative rendered
  desktop checks, source/API reopen checks, and `git diff --check` passed.

### Packet 24C — authorized canonical live proof and MVP readout

**Classification:** canonical outcome exemplar.

**Status:** historical technical evidence; superseded for M6 goal evaluation by
Packet 24D.

After explicit route/deployment/live authorization:

1. preflight the exact authoring, participant, narrator, and analysis schemas;
2. certify only the required route/schema combinations;
3. deploy one immutable candidate;
4. author or revise the canonical configuration conversationally;
5. approve and run one live trajectory;
6. inspect every complete participant, narrator, and coded-analysis trace;
7. restart and reopen the retained draft and run without new calls; and
8. obtain the operator readout against M1–M8.

Retain a useful `draft` or `blocked` artifact if a late live call fails. Resume
only the missing phase from validated identities; do not restart successful
authoring or world execution merely because one analysis module failed.

The exact external-call budget is measured and reported at the end of 24B. Do
not invent it in this plan or inherit the former comparison batch's topology.

Retained evidence:

- OpenRouter-backed Terra medium produced the approved authored draft in one
  structured attempt.
- The live world completed 46 participant calls, 537 events, 57 participant
  activations, and four meetings. Its exact outcome was
  `no_decision_by_horizon`, with no deployment scope approved.
- The original 66-moment narrator projection exceeded the configured 57-call
  preflight. The repaired projection coalesced exact-work-only moments to 45
  narratable moments while preserving every moment event reference and exact
  work reference. Narration-only resume made 45 low-reasoning narrator calls
  and explicitly retained `world_replayed: false`.
- Total observed usage was 91 completed calls and `$0.4935855`: 46 participant
  calls costing `$0.19576035` and 45 narrator calls costing `$0.29782515`.
  One narrator logical call required a visible structured-output retry; no
  fallback or hidden replay occurred.
- Restart/reopen preserved the approved proposal digest, exact world and
  evidence digests, theory bundle digest, calls, and cost. Reopening made no
  provider call.
- Focused changed-boundary tests passed (51 tests); two default-route isolation
  regressions passed; strict typing passed over all 43 source files; the
  production frontend build and graph build passed. Repository-wide test typing
  still reports 18 pre-existing errors isolated to
  `tests/test_configurable_theory_analysis.py`.
- Rendered desktop review passed the initial-situation, maps,
  collapse/expand, concise/detailed narrative, participant/composite,
  Waltzman, Levin, exact-outcome, fresh-browser, and restart/reopen checks.
  One detailed terminal exact-mechanism sentence says a terminal decision was
  accepted without naming `no_decision_by_horizon`; the concise account and
  exact outcome state the result correctly. Treat this as a presentation
  limitation, not evidence of a different world outcome.

Acceptance disposition:

| Criterion | Status | Packet 24C evidence |
|---|---|---|
| M1 | pass | Conversational draft, revision, approval, compile, and live run retained |
| M2 | pass | Reviewed people, information, mechanisms, places, boundary, goal, termination, and assumptions shown before Play |
| M3 | pass | Reference and live paths, retained exact runtime, maps, narratives, evidence, and non-replaying resume verified |
| M4 | pass | Validated theory-neutral bundle reopened with unchanged digest |
| M5 | pass | Sixteen provenance-labeled Waltzman findings rendered |
| M6 | pass | Corrected retained reference run renders seven findings from a discriminating goal configuration and preserved evidence bundle |
| M7 | stakeholder judgment pending | Technical browser flow passes on the corrected run; operator comprehension remains unobserved |
| M8 | pass | Canonical documents and rendered UI separate scenario, run, analysis, and post-MVP experiment concerns |

### Packet 24D — truthful configured graph, goal result, and terminal account

**Classification:** direct MVP truthfulness repair.

**Status:** technically complete; stakeholder readout pending.

1. Project declared mechanism reads, writes, substrates, observation targets,
   and representation relationships onto analyst-visible configured nodes.
2. Classify zero-degree nodes as analytical-only, spatial-only, or unexplained;
   warn only about unexplained isolation.
3. Reject a candidate collective goal that counts every terminal outcome as
   satisfying that goal.
4. Give the live narrator exact terminal status only at the terminal evidence
   moment, and make reference narration distinguish an approved decision from
   `no_decision_by_horizon`.
5. Verify graph fit, three-view continuity, analytical-scale controls,
   narrative hierarchy, pause/resume, console, and failed requests in a fresh
   desktop browser.

The historical Packet 24C run remains immutable evidence of its exact world
trajectory. It is not silently reinterpreted as valid goal-satisfaction
evidence. Corrected draft `draft_6fbb279df69b` was separately approved and
compiled on private Mac build
`92a310cfc93128d46acd97c4b21e5c1acc47a4a3`. Reference run
`run_eded0f70b15f` ended `scope_reduced` with zero model calls and zero cost;
both theory modules are available, and reopen preserved the evidence-bundle
and Levin-readout digests. Its Levin goal finding is `calculated`, cites the
reviewed scenario, exact terminal state, and completion record, and reports
that `scope_reduced` satisfies the configured goal.

The corrected preview classifies 51 nodes as causal and 3 as analytical-only,
with no unexplained-isolation warning. A deployed negative control that marked
all terminal outcomes goal-satisfying returned the declared 422 rejection and
left the approved revision unchanged. The desktop browser flow passed deep
link, three graph projections, both analytical composites, spatial
containment, pause/resume, narrative, and theory-card checks with no console,
request, or current-service log errors. The harness now derives authored
boundary labels from the selector rather than assuming fixture labels.

M6 is technically satisfied. M7 remains the operator's judgment of whether the
corrected situation, trajectory, two theoretical readouts, evidence, and
limitations are understandable without raw JSON.

### Packet 24E — 24-hour Waltzman stakeholder demo

**Classification:** canonical outcome presentation.

**Status:** implementation candidate verified locally; private deployment and
operator judgment pending.

On 2026-07-31 the operator paused the generalized-foundation decision and set a
hard 24-hour limit to finish a demo for Waltzman. The smallest accepted change
is a presentation layer over the already retained Packet 24D evidence, not a
new simulation runtime, a comparison study, or a scientific-validation claim.

The completed run must lead with:

1. a plain-language modeled result;
2. separate trust-structure, perceived-risk, and coordination-readiness
   observations;
3. an inspectable trajectory from information pressure through individual
   response and coordination-rule change to collective outcome;
4. direct event evidence where the retained finding cites events; and
5. an always-visible statement that the synthetic run demonstrates an
   implementation but does not validate a detector, establish real-world
   causation, or predict an institution.

The full 16-finding Waltzman readout, Levin readout, narrative, three graph
projections, participant and boundary views, exact evidence, and pause/resume
remain available. Local desktop verification against a completed authored
provider-free run passed the deep link, new walkthrough content and order, all
existing interaction checks, console, and failed-request checks. M7 remains
open until the operator reviews the deployed corrected run.

## Review and Reset

Review only the changed contract, one provider-free canonical path, and one
authorized live path. Do not reopen broad scientific validation or comparison
methodology.

Reset after two packets or four elapsed hours without a new visible portion of
the canonical author-configure-run-readout flow. Reset immediately if the
template requires arbitrary generated mechanism code, hidden aggregate state,
or a second runtime.

## Post-MVP Promotion Triggers

- Promote `ExperimentSpec` only when the operator wants a question that one run
  cannot answer.
- Promote repeated comparison when candidate directional invariants or outcome
  variation would change an analyst decision.
- Promote Slice 22 perturbations when robustness, recovery, member replacement,
  or persuadability becomes the selected question.
- Promote generalized component composition only when a second materially
  different authored scenario cannot reuse the bounded template approach.
