---
doc_role: implementation_plan
authority: bounded_design
status: approved_for_implementation
created: 2026-08-14
updated: 2026-08-14
depends_on:
  - docs/GOAL.md
  - docs/ROADMAP.md
  - docs/adr/012-decision-environment-measures-are-derived.md
  - docs/adr/013-generalized-simulator-foundation.md
  - docs/adr/014-separate-simulation-and-analysis-authority.md
supersedes_in_part:
  - docs/plans/028-natural-language-general-simulation-demo.md
---

# Slice 29: Separate scenario, run, analysis, and experiment authority

## Implementation status · 2026-08-14

- **29A complete:** strict V2 scenario, run, evidence, and analysis contracts,
  independent digests, and the V1 compatibility adapter are on `main`.
- **29B complete for the selected vertical:** the general runtime accepts the
  separated contracts, actor/adjudicator inputs exclude analyst framing, and
  the transition authority no longer emits objective assessment.
- **29C complete at the service boundary:** completed V2 runs retain a
  theory-neutral evidence bundle and separately computed analysis results.
- **29D complete for the selected vertical:** new conversational drafts write
  a native separated V2 bundle. Public draft `draft_2336c4427396` was authored
  from the relief-port description with no research question and no selected
  analysis. Its compiled graph contains 39 nodes, 73 edges, and no isolated
  nodes; the public review separates World, Run, and optional Analysis.
- **29E complete for public-path adoption, partial for retirement:** retained
  native run `run_0047f43377f8` completed through V2 with 15 authentic Terra
  calls, three causal moments, 26 evidence records, and zero analyses at
  execution. Waltzman and exact-outcome lenses were attached after completion,
  the exact lens was removed, and all three generated isolation receipts show
  unchanged model-call count, world revision, and run-evidence digest. V1
  historical readers and execution branches have not yet been retired.

Luna certification refresh was attempted against the current shared-client
revision and failed at the provider boundary because the Codex subscription
usage limit is exhausted until 2026-08-20 11:00 local time. The retained
public native-V2 proof therefore used the currently advertised OpenRouter
Terra route; do not describe either the authoring trace or run as Luna.

## Planning mode and target

This is a durable solo refactor plan for the general simulator. It is detailed
for sequential implementation by an agent that should not have to infer product
or architectural decisions. It does not authorize deployment or publication.

Target actor: an analyst using the natural-language simulator.

Target result: the analyst can describe one situation in one conversation,
review and run the resulting world, and attach or change analytical lenses
without those lenses changing what simulated people know, how the transition
authority adjudicates, or what the world does.

Delivery maturity remains a private functional PoC. The refactor protects the
public Waltzman demo path but does not add production hardening, empirical
validity, or a universal experiment engine.

## Canonical outcome probe

### Starting input

Use the retained relief-port description:

> Model a relief-cargo port after a bridge failure. A port operations
> coordinator, customs officer, union representative, and trucking dispatcher
> must attempt to move humanitarian cargo using limited trucks, fuel, berths,
> and routes. Everyone receives one public fuel-contamination claim, while
> separate technical, legal, and labor messages reach different people.
> Preserve who learned what, which actions were attempted, which resources
> moved, and why cargo did or did not move.

The analyst separately requests a Waltzman-informed analysis of information
topology, stated source reliance, perceived risk, dependencies, and
coordination readiness.

### User operation

1. Configure the description through the existing authoring conversation.
2. Review three plain-language sections: **World**, **Run**, and optional
   **Analysis**.
3. Approve and execute the port run with Luna.
4. Reopen the completed run before any analytical lens is attached.
5. Attach the Waltzman lens and inspect its evidence-linked result.
6. Remove or replace the lens without rerunning the simulation.

### Inspectable result

- one authored-study identity with separate scenario, run, and analysis
  digests;
- one retained run whose actor contexts, adjudicator contexts, model-call
  traces, transition evidence, checkpoints, and final state reference only the
  scenario and run digests;
- an analysis result with its own specification and result digest;
- a base graph containing only configured causal structure;
- an optional analytical overlay clearly labeled as a post-run interpretation;
  and
- a runtime-generated isolation receipt comparing inputs before and after the
  analysis attachment.

### Negative control

Submit an analysis request that attempts to deliver a new message, add an
actor, schedule an event, or change world state. Analysis validation rejects it
without changing the draft's scenario/run digests or the retained run.

### Non-claim

The probe establishes contract and authority separation in one synthetic
execution. It does not establish predictive validity, stable behavioral
distributions, counterfactual causality, or that the Waltzman constructs are
empirically valid measures of real institutions.

## Current state

Current source baseline: `d0719a5815ebac7cb11762eaff6ed5d924274289` on
`origin/main` when this plan was written.

### What works

- Ordinary-language authoring produces a retained editable
  `GeneralSimulationProposalV1`.
- Trusted compilation resolves component requests and reports executable,
  coarse, descriptive, or unsupported coverage.
- Stock Concordia owns simultaneous actor activation and the general-world
  lifecycle.
- Simulated people receive scoped world records, observations, memories, and
  available transition contracts.
- One joint transition authority proposes typed transactions that canonical
  validation either commits or rejects.
- Checkpoints, model receipts, transition evidence, generic graphs,
  walkthroughs, and a Waltzman-informed projection are retained.
- The port and service examples used the same general runner rather than
  scenario-specific runtime packages.

### Current coupling

| Current seam | Observed behavior | Why it is a gap |
| --- | --- | --- |
| `GeneralSimulationProposalV1.question` | Required beside world, schedule, and analysis | Assumes one global question and cannot distinguish actor mission, stopping condition, or analyst inquiry |
| Actor call input | Sends proposal question as `research_question` to every person | Gives simulated people analyst framing without a modeled information path |
| Joint transition call | Receives the same `research_question` | Lets analytical purpose influence causal adjudication |
| Final `WorldTransaction` | Transition authority also emits `objective_assessment` | Component changing the world also judges whether the analyst's objective succeeded |
| `analysis_requests` and simplified `analysis_spec` | Stored inside the executable proposal | Binds one analytical lens to scenario authoring and duplicates the existing analysis owner |
| `material_to_question` | Makes unsupported/descriptive coverage blocking | Confuses analytical interest with causal/fidelity materiality |
| `schedule` | Embedded in the scenario proposal | Prevents clean reuse of one world across different run conditions |
| General run projection | Runs Waltzman projection when proposal selects it | Analysis is not independently attachable after completion |
| `RunEvidenceBundleV1.analysis_specs` | Requires at least one analysis | A nominally theory-neutral run cannot exist without analysis selection |
| Configuration walkthrough | Includes analysis as a simulation-configuration scene | Visually suggests that the lens is part of the causal world |

### Existing capability owners

| Concern | Canonical seam | Disposition | Adoption proof |
| --- | --- | --- | --- |
| General world semantics | `cybernetic_influence.general_simulation` models/compiler | extend | New `ScenarioSpec` compiles to the existing canonical world and registry |
| General execution | Concordia runner and world component | extend | Runtime signature accepts only compiled scenario plus run |
| Execution controls | `analysis.theory_analysis.RunSpecV1` concept | supersede with general `RunSpecV2` while retaining V1 reads | Retained run snapshots the V2 digest and executes from it |
| Analysis semantics | `analysis.theory_analysis.AnalysisSpecV1` | extend/version in the analysis package | General authoring no longer declares a second analysis type |
| Evidence | general transition evidence plus `RunEvidenceBundleV1` | extend | Theory-neutral bundle validates with zero analysis specs |
| Waltzman projection | general `analysis_projection` and existing theory analysis | adapt | Analysis service consumes only retained evidence |
| Conversational draft lifecycle | `AuthoringDraftStore` and authoring service | extend | One draft retains separate contract revisions/digests |
| Public authoring/replay | current Waltzman workbench | extend | Canonical browser journey displays split sections and post-run attachment |
| Historical V1 artifacts | immutable retained drafts and runs | bounded compatibility adapter | Historical artifacts reopen; no V1-native execution path remains |

## Desired end state

### Artifact and authority flow

```text
GeneralAuthoringConversationV2
        |
        v
AuthoringInterpretationV2          # conversational, not executable
        |
        v
AuthoredSimulationBundleV2         # convenience envelope only
  scenario: ScenarioSpecV2
  default_run: RunSpecV2
  analyses: AnalysisSpecV2[]
  unresolved_questions: string[]
        |
        +---- scenario + run ----> GeneralSimulationRunner
        |                               |
        |                               v
        |                         RunEvidenceBundleV2
        |                               |
        +---- analysis -----------------+
                                        v
                                  AnalysisResultV2
```

The envelope improves UX and retention. It grants no authority. Runtime code
must receive the nested scenario and run objects explicitly rather than the
envelope.

### Contract boundaries

#### `ScenarioSpecV2`

Owns only world semantics:

```text
scenario_spec_version = 2
scenario_id, title, description
people[]
world_records[]
active_systems[]
component_requests[]
spatial_extension?
information_extension?
resource_extension?
relationship_extension?
sensing_rules[]
resource_transformations[]
resource_transports[]
fidelity_assumptions[]
declared_invariants[]
```

It does not contain `question`, `schedule`, model configuration, analysis
requests, analysis specifications, unresolved authoring questions, repetitions,
or comparisons.

#### `RunSpecV2`

Owns one execution:

```text
run_spec_version = 2
run_id
scenario_digest
execution_mode: reference | live | replay
model?
reasoning_effort?
budget fields?
starting_checkpoint_id?
horizon_minutes
scheduled_moments[]
external_injects[]
termination_conditions[]
seed_or_provider_seed_status?
```

`scheduled_moments` provides activation opportunities and external events. It
does not prescribe actor choices or successful transitions. A stopping
condition may inspect canonical state only through a registered exact or coarse
lifecycle predicate.

#### `AnalysisSpecV2`

Lives under the analysis capability owner and is execution-inert:

```text
analysis_spec_version = 2
analysis_id
profile
purpose
construct_definitions[]
required_evidence_kinds[]
method_classes[]
aggregation
uncertainty
limitations[]
subject_refs[]
```

Supported profiles remain a registered set. The first general profile is
`waltzman_coordination_v1`. An exact terminal outcome readout may use the same
analysis envelope with an exact method; it is not emitted inside a world
transaction.

#### `ExperimentSpec`

This plan preserves, but does not implement, the general experiment seam:

```text
experiment_id
base_scenario_digest
conditions[] -> RunSpec references or overrides
fork/checkpoint rules
replication rules
matching rules
analysis references
comparison contract
```

No scenario, run, or analysis field may pretend to own these responsibilities.

#### `RunEvidenceBundleV2`

Owns immutable theory-neutral evidence:

```text
bundle_version = 2
bundle_id, run_id, scenario_id
scenario_digest, run_spec_digest
initial_state_digest, terminal_state_digest
evidence_records[]
fidelity_assumptions[]
known_omissions[]
record_digest
```

It contains no required `analysis_specs`. An analysis result references the
bundle digest and cannot mutate or replace the bundle.

#### `AnalysisResultV2`

```text
analysis_result_version = 2
result_id
run_evidence_bundle_digest
analysis_spec_digest
findings[]
coverage_status: supported | degraded | unsupported
missing_evidence[]
model_call_receipts[]
result_digest
```

An LLM-coded analysis retains a separate analyst trace. It never reuses an
actor or adjudicator role and never writes an actor observation.

### Goal and question classification

The authoring interpretation must classify ordinary-language statements before
configuration:

| Meaning | Representation |
| --- | --- |
| Person's own goal | behavioral profile or private memory |
| Shared mission known to participants | explicit representation delivered through an information path |
| Enforced world requirement | scenario mechanism or invariant |
| Run horizon or stopping condition | `RunSpecV2` |
| Desired post-run judgment | `AnalysisSpecV2` |
| Controlled condition or fork | future `ExperimentSpec` |

The authoring assistant may use the analyst's purpose to choose an appropriate
resolution and propose observability. After approval, analytical purpose cannot
enter execution unless it has been translated into an explicit scenario or run
fact visible in review.

### Coverage separation

Compilation produces two reports:

1. `ExecutionCoverageReportV2` classifies requested causal behavior and blocks
   approval when a `causally_material` or `fidelity_material` behavior is only
   descriptive or unsupported.
2. `AnalysisCoverageReportV1` compares an analysis specification's required
   evidence with the evidence schema retained by the scenario/run. It may mark
   an analysis degraded or unsupported but cannot block execution unless the
   analyst explicitly requires that analysis as a run prerequisite.

If an analysis requires a new sensing process, the authoring UI presents that
as a proposed scenario modification requiring review. It is never inserted
silently by the analysis compiler.

### Persistence and identity

- Draft revision identity covers the convenience envelope.
- Approval stores separate scenario, run, and analysis specification digests.
- A run identity binds exactly one scenario digest and one run-spec digest.
- A run-evidence digest is independent of every analysis digest.
- An analysis-result identity binds one evidence digest and one analysis-spec
  digest.
- Recomputing analysis creates a new result revision without changing the run.
- Retained model receipts name `authoring`, `actor`, `adjudicator`, or
  `analyst`; roles are not reused across authority boundaries.

## Gap-to-implementation matrix

| Gap | Required code change | Compatibility | Direct proof | Old-path disposition |
| --- | --- | --- | --- | --- |
| Monolithic proposal | Add bundle plus separate V2 specs | V1 reader/adapter | Separate digests in approved draft | New writes reject V1 proposal creation |
| Question in actor prompts | Remove `research_question`; model missions as authorized context | V1 adapter retains question for presentation/analysis only | Actor input fixture contains no analyst field | Delete `_question` from actor component |
| Question in adjudicator | Remove question and outcome language from joint transition call | None needed | Exact adjudicator input lacks analysis | Delete final-objective coupling |
| Assessment inside transaction | Move to post-run analysis result | Historical transactions remain readable | World revision stable while assessment is added | Stop producing new transaction assessments |
| Schedule in scenario | Move schedule/injects to run spec | V1 adapter projects schedule | Same scenario digest across two run schedules | Stop reading proposal schedule in runtime |
| Duplicate analysis type | Add/extend V2 in canonical analysis package | Read simplified V1 spec | Import/dependency check identifies one owner | Remove general-simulation analysis model |
| Analysis-bound evidence | Make analysis list optional/external | V1 bundle reader remains | Zero-analysis bundle validates | Stop writing specs inside V2 bundle |
| Material-to-question | Rename/split into causal/fidelity materiality | Adapter maps `true` conservatively | Unsupported causal behavior blocks; analysis gap does not mutate world | Remove compiler dependency on research question |
| Embedded projection | Add analysis service over evidence | Existing retained projections remain readable | Attach lens after completion with zero simulation calls | General run projector returns evidence only |
| Blended UI | Render World, Run, Analysis separately | Historical run pages unchanged | Browser comprehension and mutation checks | Remove analysis from causal graph scene |
| Bypass risk | Add architecture checks and runtime receipt | None | Public draft/run proves selected path | Legacy executor becomes unreachable for V2 |

## Implementation path

### 29A — Freeze V2 contracts and one-way compatibility

**Epistemic state:** fully specifiable now. **Type:** direct blocker.

Implement:

- `ScenarioSpecV2`, `RunSpecV2`, and `AuthoredSimulationBundleV2` under the
  general-simulation owner;
- `AnalysisSpecV2`, theory-neutral `RunEvidenceBundleV2`, and
  `AnalysisResultV2` under the analysis owner;
- independent digests and reference validation;
- one V1-to-V2 adapter at the draft/run loading boundary; and
- structural dependency tests proving the general runtime does not import the
  analysis package.

Do not change public behavior yet. Do not create a second store or API family.

**Pass:** the retained port proposal adapts into valid V2 contracts; new V2
serialization round-trips strictly; changing only the analysis list leaves the
scenario and run digests unchanged; zero-analysis evidence validates.

**Negative:** an `AnalysisSpecV2` containing a schedule, actor observation,
world patch, or transition field fails validation.

**Stop:** if V2 cannot reuse the current canonical world/compiler without a
second implementation, revise the contract rather than cloning the compiler.

### 29B — Isolate runtime and transition authority

**Epistemic state:** fully specifiable after 29A. **Type:** vertical.

Change the runner entrypoint to accept only:

```text
compiled_scenario: CompiledGeneralScenarioV2
run_spec: RunSpecV2
model_call: StructuredCall
checkpoint?: retained checkpoint
```

Remove:

- `question` from `GeneralPersonPrefab` and `GeneralActorActingComponent`;
- `research_question` from actor and adjudicator input;
- analysis-specific imports or fields from the runner;
- final objective-assessment instructions from the transition-authority
  system prompt; and
- required `objective_assessment` production from `WorldTransaction`.

Translate any shared mission in the port exemplar into an explicit information
representation delivered to the intended people. Personal goals remain in
their behavioral profiles and memories.

**Pass:** one authentic Luna port run completes or fails visibly through the
same canonical validators; every actor and adjudicator call retains a context
free of analysis fields; the run evidence identifies only scenario and run
digests; checkpoint restore still works.

**Negative:** attach a deliberately adversarial analysis purpose before the
run. Actor/adjudicator context hashes remain identical to the no-analysis run
when both execute from the same retained checkpoint and call inputs are
projected.

**Stop:** if an actor requires analyst purpose to choose an action, model the
missing mission or stake explicitly; do not restore the implicit question.

### 29C — Detach evidence, outcome assessment, and Waltzman analysis

**Epistemic state:** fully specifiable after 29B. **Type:** vertical.

Implement a post-run analysis service that accepts exactly one retained
evidence bundle and one analysis specification. Move the current exact outcome
assessment and Waltzman projection behind that boundary. Retain separate
analysis receipts and result digests.

The generic run projection exposes the world trajectory and evidence without
requiring a theory result. The analysis endpoint attaches, lists, reads, and
recomputes results by run ID without invoking actors or the transition
authority.

**Pass:** reopen the completed port run with no lens; attach Waltzman analysis;
observe the analysis result; remove or replace it; verify zero new simulation
calls, zero new world revisions, and unchanged run-evidence digest.

**Negative:** missing required evidence returns `degraded` or `unsupported`
with exact missing kinds. It does not create a sensing rule, inject, or world
record.

### 29D — Split conversational authoring without splitting the experience

**Epistemic state:** fully specifiable after 29A–29C freeze contracts.
**Type:** vertical.

Update the Luna authoring contract so one conversation produces an
`AuthoringInterpretationV2` and then the convenience bundle. The discussion
assistant distinguishes:

- world and people;
- actor-known goals and stakes;
- run conditions, injects, and horizon;
- optional analyst questions; and
- genuinely material unresolved choices.

The Configure-now action makes bounded assumptions as today. It must not invent
a research question. It may return no analysis specifications.

Update the review surface to show:

1. **World** — people, state, information, resources, mechanisms, assumptions;
2. **Run** — starting state, moments, injects, horizon, model, termination;
3. **Analysis (optional)** — selected lens, evidence needs, methods, limits.

The configuration graph and walkthrough omit analysis nodes. Before execution,
analysis appears as a compact read-only attachment summary. After execution,
findings can overlay the causal graph only when the user enables the labeled
overlay.

**Pass:** a fresh user can configure the port world without supplying a
research question, run it with no analysis, and attach Waltzman analysis later.
Direct edits preserve independent digests: editing analysis changes only the
analysis digest; editing schedule changes only run/bundle identity; editing a
person changes scenario identity and invalidates dependent approval.

### 29E — Adopt, migrate the flagship path, and remove the bypass

**Epistemic state:** fully specifiable after the authentic 29D flow.
**Type:** enabling closeout after the vertical.

- Make V2 the only new-write authoring path.
- Route approval, run, catalogue, replay, and analysis through V2.
- Keep historical V1 drafts/runs read-only or adapt them before re-execution.
- Remove dead V1 execution branches once the retained fixture and flagship
  reopen checks pass.
- Generate a runtime adoption receipt naming scenario/run digests, runner,
  evidence bundle, and attached analyses separately.
- Update methodology and public limitations only after the live behavior is
  observed.

**Pass:** the public **New simulation** journey and one retained port URL prove
V2 adoption. A structural test fails if the V2 runtime imports the simplified
analysis type, reads `GeneralSimulationProposalV1`, or emits analysis fields in
an actor/adjudicator context.

**Cleanup:** delete or quarantine superseded V1 writer/runner code only after
the committed V2 consumer proof. Preserve immutable historical artifacts and
their readers.

## Acceptance matrix

| ID | Criterion | Direct evidence |
| --- | --- | --- |
| S29-1 | Scenario, run, analysis, and future experiment responsibilities are separate | Strict schemas, independent digests, ADR 014 contract review |
| S29-2 | Runtime cannot inspect analysis | Function signature, dependency test, runtime receipt |
| S29-3 | Actors receive no analyst research question implicitly | Retained actor contexts and negative fixture |
| S29-4 | Transition authority does not assess the research objective while mutating world | Exact adjudicator prompt/output and transaction schema |
| S29-5 | Actor-visible missions have modeled provenance | Representation/delivery evidence or private-memory source |
| S29-6 | A run can complete and reopen with zero selected analyses | V2 evidence bundle and run UI |
| S29-7 | Analysis can be attached after completion without simulation effects | Model-call counts, world revision, and digest comparison |
| S29-8 | Missing analytical evidence fails or degrades visibly | Unsupported analysis fixture |
| S29-9 | Execution coverage uses causal/fidelity materiality | Compiler positive and unsupported fixtures |
| S29-10 | One conversation still configures the complete experience | Authentic Luna authoring trace and browser path |
| S29-11 | Causal graph excludes analysis and optional overlays are labeled | Browser graph/walkthrough inspection |
| S29-12 | New public drafts use V2 and the old path cannot be silently selected | Runtime-generated adoption receipt and architecture check |
| S29-13 | Retained flagship artifacts remain reviewable | Historical draft/run reopen check |

## Compatibility and failure behavior

- New drafts write only V2. Do not dual-write V1 and V2.
- Historical V1 objects remain immutable. A single explicit adapter may
  translate them for V2 re-execution; adapter output receives new V2 digests.
- If a V1 `question` cannot be unambiguously classified, retain it as
  presentation metadata and a candidate post-run question. Do not inject it
  into actor memory automatically.
- If analysis fails, the completed run remains intact and visible.
- If V2 compilation fails, preserve the authored interpretation and exact
  diagnostics; do not fall back to V1.
- If Luna cannot satisfy the new typed authoring or runtime contract after one
  bounded repair, retain the failed candidate and trace. Do not silently switch
  to Terra; report the route problem immediately.
- Existing public case-study runs continue through their historical reader.
  They need not be rewritten to claim V2 adoption for new simulations.

## Focused verification order

1. Contract/digest and forbidden-field checks.
2. V1-to-V2 retained port adapter check.
3. Provider-free runtime isolation fixture.
4. One authentic Luna actor plus adjudicator canary on V2.
5. One complete authentic port run.
6. Post-run analysis attach/remove check.
7. Browser authoring, approval, execution, reopen, and analysis-attachment flow.
8. Historical flagship reopen check.
9. Broader affected tests only after the authentic path passes.

Mocks and provider-free fixtures establish plumbing only. S29-2 through S29-7
require retained evidence from the authentic general-world route before the
stakeholder is asked to review it.

## External-call budget

The first authentic proof reuses the four-person, three-moment port shape:

- optional one Luna authoring call if the retained V1 draft adapter is not the
  selected starting state;
- twelve actor calls;
- three joint adjudicator calls; and
- no mandatory LLM analysis call for the existing Waltzman projection.

Expected total is fifteen simulation calls, or sixteen including fresh
authoring, with the existing three actor/adjudicator serial stages. Use Luna at
medium reasoning unless an observed route or schema failure is retained and
reported. Checkpoint after every committed or rejected moment. A late failure
resumes from the last strict checkpoint rather than replaying completed calls.

## Planning horizon and estimates

| Slice | Strong sequential agent | Less capable sequential agent |
| --- | ---: | ---: |
| 29A contracts and adapter | 0.5–1 day | 1–2 days |
| 29B runtime isolation plus authentic run | 1–2 days | 2–4 days |
| 29C evidence and analysis detachment | 1 day | 2–3 days |
| 29D authoring and UI | 1–2 days | 3–5 days |
| 29E adoption and cleanup | 0.5–1 day | 1–3 days |
| Total | 4–7 focused days | 9–17 focused days |

These are planning ranges, not commitments. Reassess after 29B's authentic
run because it resolves the highest-risk runtime boundary.

## Stop and course-correction conditions

Apply the workspace progress tripwire. Also reassess if:

- two consecutive increments produce only contracts or migrations without an
  authentic actor-to-world observation;
- implementation creates a second runner, analysis store, or authoring API;
- an analytical lens appears in any actor/adjudicator input;
- a compatibility adapter begins owning new behavior rather than translation;
- the public UI requires users to understand internal spec names;
- V2 requires another scenario-specific runtime or generated Python; or
- three authentic Luna attempts fail at the same boundary without new evidence.

The outcome remains unchanged at a tripwire. Switch to the shortest authentic
probe or freshly demonstrated blocker rather than narrowing the architecture.

## Non-goals

- general experiment execution or statistical replication;
- new Waltzman or Levin constructs;
- empirical calibration or predictive validity;
- a universal ontology or exhaustive capability/affordance resolver;
- migration of immutable historical run bodies;
- new scenario templates;
- a separate analysis product or database;
- security, privacy, compliance, or production hardening beyond existing
  invariants; and
- deployment or external stakeholder outreach.

## Exact first implementation action

Implement 29A and its independent-digest tests, then immediately route the
retained port fixture through 29B's runtime signature. Do not start with UI,
methodology prose, new analyses, or broad migration. The first decision-bearing
observation is an authentic Luna port continuation whose actor and adjudicator
contexts contain no analysis purpose.
