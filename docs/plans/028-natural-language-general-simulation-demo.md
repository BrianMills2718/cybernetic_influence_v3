---
doc_role: implementation_plan
authority: bounded_design
status: implemented_not_deployed
created: 2026-08-13
updated: 2026-08-13
depends_on:
  - docs/GOAL.md
  - docs/adr/013-generalized-simulator-foundation.md
  - docs/handoffs/027-foundation-implementation.md
  - docs/research/027-concordia-architecture-revisit.md
plan_id: "cybernetic_influence_v3#28"
dependencies: []
dependencies_reviewed: "2026-09-15"
---

# Slice 28: Natural-language general simulation demo

## Completion record

Slices 28A through 28F were implemented on
`feature/slice-28-general-demo`. A subsequent requirement-by-requirement audit
corrected checkpoint continuation, assimilation provenance, trusted
transaction-envelope ownership, stock actor selection, and the missing second
example prompt. Focused evidence, authentic Luna traces,
known limitations, and the stakeholder script are recorded in
`docs/handoffs/028-natural-language-general-simulation-demo.md`. Public
deployment and exact deployed-build verification remain separate operator
actions.

## Implementation handoff

Execute 28A through 28F in order. Keep one coherent commit per slice and stop
at the named stop conditions rather than inventing a workaround. This plan is
ready to assign, but live model spend and deployment remain the operator's
separate authority at the point they occur.

Do not begin by creating more templates. The first architecture-bearing task
is 28B's authentic actor-to-world transition on stock Concordia; the first
user-visible task is 28A's authoring-input repair.

## Outcome

A first-time visitor opens the public **New simulation** page, immediately sees
where to describe a simulation, and can complete this path without new
scenario-specific Python:

```text
ordinary-language description
-> retained editable semantic world proposal
-> compiler-generated execution coverage report
-> human revision and approval
-> Concordia-owned live simulation
-> automatically generated walkthrough, graph, and evidence replay
```

The visible proof is not merely another authoring template. At least two
materially different descriptions must use the same proposal schema, compiler,
component registry, Concordia runner, evidence projection, and replay UI.

This is a stakeholder-facing pilot vertical. It is intended to make the
Waltzman handoff materially more useful: Waltzman can describe and run a
bounded simulation of his own rather than only inspect an outbreak example.

## Current truth

- The deployed page already contains `#create-prompt` and a working
  prompt-to-draft API. At a 1440x1000 viewport the prompt is pushed to the
  bottom edge and its primary action is below the fold because the hero
  consumes the first screen. The control exists but is not discoverable. This
  is a UI defect, not an absent endpoint.
- The existing `POST /api/authoring/drafts/{draft_id}/messages` path uses Luna
  by default and retains typed revisions.
- `ScenarioDraftProposal` is a closed union of five workflow templates:
  `resource_request_v1`, `information_campaign_v1`,
  `component_composition_v1`, `coordination_decision_v1`, and
  `influence_network_v1`.
- `component_composition_v1` is not a general composer. It projects one fixed
  eight-component selection into the information-campaign fixture.
- Every existing compiled workflow executes through `CausalSession` and/or
  `ActiveRuntimeSession`. The adopted Concordia production path is not yet in
  product code.
- The public completed-run catalogue and staged replay are already generic over
  retained run projections. They are the presentation seam to reuse.
- ADR-013 makes stock pinned Concordia the outer lifecycle owner. A new general
  path must not hide the old runtime behind a Concordia wrapper.

## Delivery decision

Implement this on the adopted Concordia path. Do not broaden the existing
closed workflow union into a second supposedly general product.

The faster alternative is to add a generic LLM game master to the current CI
runtime. That could produce a visually convincing demo in roughly 4–7 focused
days, but it would conflict with ADR-013, preserve two lifecycle foundations,
and make later work likely to bypass or replace this implementation. It is not
the selected route.

## Canonical stakeholder example

Use this prompt as the first complete live vertical:

> Model a relief-cargo port after a bridge failure. A port operations
> coordinator, customs officer, union representative, and trucking dispatcher
> must agree on and execute a joint dispatch plan using limited trucks, fuel,
> berths, and routes. All four receive the same public claim that the fuel is
> contaminated. Separate technical, legal, and labor messages reach different
> people. Let them exchange information, propose bounded actions, and decide
> whether cargo can move without violating their local requirements. Preserve
> who learned what, which resources actually moved, and why the joint plan did
> or did not become executable.

Why this example is canonical:

- it is centered on Waltzman's local-interaction-to-coordination question;
- it includes both homogeneous and heterogeneous information inputs;
- it includes people, inert things, places, resources, information, and world
  consequences;
- a persuasive narrative alone cannot complete it because resources and
  placement must change in canonical state; and
- it is materially different from the existing outbreak voting template.

Use a software/service incident as the cross-domain proof:

> Model an online service outage involving an incident commander, database
> engineer, security analyst, and customer liaison. Credentials, service
> dependencies, status messages, access permissions, and recovery attempts
> change over time. Different people receive different claims about the cause.
> The group must restore service without erasing forensic evidence.

The second example may be smaller, but it must compile and run through the same
production seams without adding domain fields to the universal kernel.

## User flow

### 1. Describe

The first desktop viewport must show:

- the short heading **Describe a simulation**;
- one five-row text area;
- `Generate editable simulation` as the primary action;
- two optional example prompts; and
- one concise boundary: the system generates only behavior it can classify as
  registered, coarse LLM-adjudicated, descriptive, or unsupported.

Do not place a large marketing hero above the input. The user must not scroll
to discover the primary action.

### 2. Review

After generation, show this order:

1. simulation question and intended outcome;
2. people and other active systems;
3. world elements and initial state;
4. information sources, representations, recipients, and timing;
5. transition authorities and execution coverage;
6. fidelity assumptions and unsupported requests; and
7. `Approve and run` only when no blocking unsupported behavior remains.

Every section supports both:

- a plain-language revision through the existing retained conversation; and
- direct semantic edits through typed controls. A complete raw JSON editor may
  remain under **Advanced**, but it cannot be the only way to edit the main
  question, people, world elements, information paths, timing, or coverage
  implementation choice when the compiler offers alternatives.

Coverage classifications themselves are compiler evidence and are not
editable. When the registry offers more than one executable implementation,
the user may select among those declared options. Otherwise the user must
revise the requested behavior; the UI must not let a user relabel unsupported
behavior as implemented.

### 3. Run

Show the approved configuration identity, selected model, maximum model-call
boundary, and the four execution stages:

```text
observe -> propose -> adjudicate -> commit
```

The page may reuse polling. Streaming is not required for this slice. A failed
or timed-out model stage leaves the approved draft and completed evidence
inspectable and exposes the exact resume boundary.

### 4. Replay

The completed run automatically appears in **All simulations** and opens in
the existing generated walkthrough. No port-specific or service-incident page
is permitted. The replay must expose:

- configured structure versus realized events;
- actor observations and private model outputs;
- semantic intents;
- adjudicator proposals;
- validation and commit results;
- world-state changes;
- collective outcome; and
- exact model-call and configuration provenance.

For the canonical port run, also expose a Waltzman-informed analysis derived
from the general evidence projection: broadcast versus targeted input topology,
changes in stated source reliance, named risks, blocking dependencies, and
coordination readiness across moments. Every finding steps down to retained
evidence and remains a within-simulation interpretation rather than a validated
measure or counterfactual causal claim.

## Architectural boundaries

### Lifecycle ownership

Stock Concordia owns actor selection, moment progression, component lifecycle,
and checkpoint invocation. Project code may answer authorized queries,
validate proposed transitions, commit canonical state, and emit durable
consequences. It may not choose the next actor, advance time, recursively run
actors, or maintain another executable scheduler.

Add a structural test that the new package cannot import
`cybernetic_influence.causal_core.engine.CausalSession` or
`cybernetic_influence.active_runtime.ActiveRuntimeSession`.

### Canonical truth and information

Keep these distinct:

```text
world truth
-> actor-authorized observation
-> private interpretation and memory
-> semantic action intent
-> adjudicator-authorized context
-> proposed world transaction
-> validation and atomic commit
-> actor-safe observations
```

An adjudicator may receive hidden state when its declared authority requires
it. Adjudicator prose never becomes an actor observation directly. Actor-visible
information is projected from committed consequences through the actor's
authorized information path.

### Transition ownership

An authoring model may generate semantic configuration. It may not generate
Python, implementation references, arbitrary prompts, or executable
predicates. The compiler resolves only registered implementations.

The common contract must be able to describe:

- deterministic mechanism;
- stochastic mechanism with an explicit seed/configuration contract;
- Luna semantic adjudicator;
- external simulator;
- scripted coarse process; and
- retained replay mode.

Only deterministic and Luna semantic transition authorities must execute in
this slice. Stochastic and external implementations are deferred. Replay is an
execution mode reproducing retained receipts, not an independent theory of
adjudication.

Each declares deterministic/nondeterministic, local/external,
synchronous/asynchronous, replayable/non-replayable, and
idempotent/non-idempotent properties separately. `kind` alone is not enough.

### Representation depth

An organization, computer, market, logistics subsystem, or other complex
system may be represented by detailed components or one declared coarse active
surrogate. Both representations may not independently own the same causal
function in one run. Compilation fails when causal ownership overlaps without
an explicit coupling component.

## Required contracts

Create these Pydantic contracts under a new
`cybernetic_influence.general_simulation` package. Names may vary only if all
responsibilities and stored fields remain intact.

### `GeneralSimulationProposalV1`

```text
schema_version = 1
proposal_kind = "general_world_v1"
simulation_id, title, question, description
people[]                         # reuse PersonDraft semantics
world_records[]                  # persistent referents and open typed state
active_systems[]                 # implementation binding is compiler-owned
component_requests[]             # semantic requested behavior/capability
spatial_extension?               # places, placements, spatial links
information_extension?           # carriers, representations, provenance, routes
resource_extension?              # named stock/custody/conservation declarations
relationship_extension?          # optional descriptive or executable relation records
schedule[]                       # semantic moments and external injects
fidelity_assumptions[]
declared_invariants[]
analysis_requests[]
unresolved_questions[]
```

Keep the universal kernel small. Spatial, information, resource, and
relationship semantics are registered typed extensions, not fields every world
must use. `world_records.kind` remains an open semantic string.

### `ComponentRequestV1` and registry

The proposal asks for behavior semantically:

```text
request_id
subject_refs[]
behavior_description
required_reads[]
desired_effects[]
fidelity_need
material_to_question: bool
```

The compiler—not the authoring LLM—maps each request to one registered
implementation or classifies it as descriptive/unsupported.

The registry entry contains:

```text
component_kind, version, implementation_ref
configuration_schema_ref
read_scope_schema, patch_grammar_ref
fidelity, assumptions, invalid_questions
causal_responsibility_tags[]
```

### `ExecutionCoverageReportV1`

For every material requested behavior retain:

```text
request_id
classification: exact | coarse_llm | descriptive | unsupported
resolved_component_ref?
what_can_change
what_cannot_change
assumptions[]
blocking: bool
compiler_evidence[]
```

The report is generated from compiler resolution, never copied from model
claims. Approval fails when a material item is `unsupported`. Descriptive-only
items remain allowed only when explicitly non-material to the question.

### Actor and action contracts

`ActorContextV1` contains only authorized observation IDs, representation
content, apparent sources, accessible records, current time, available
interfaces, and bounded private memory.

`SemanticActionIntentV1` contains actor ID, ordinary-language action,
referenced objects/targets, purpose, expected effect, and stated rationale. It
does not use a closed scenario verb union.

Add one explicit assimilation result before action selection:

```text
attended_observation_ids[]
memory_additions[]
memory_revisions[]
provenance_links[]
```

Natural-language memory remains allowed. Do not introduce numeric trust,
stress, or personality variables in this slice.

### `WorldTransactionV1`

```text
transaction_id
base_revision
authority_id
intent_ids[]
operations[]
preconditions[]
consequences[]
evidence_refs[]
```

Each operation uses a typed semantic target:

```text
record_type
record_id
field?
operation: create | remove | replace | rebind
value?
```

Do not make arbitrary JSON Pointer strings the public mutation identity.
Every authority has a registered patch grammar limiting operation types and
target record types beyond path-level write scopes.

### Commit and outbox

Validation applies reference integrity, revision/precondition checks,
authority patch grammar, topology/placement rules, information-path rules, and
only the resource/conservation invariants declared by the selected extensions.

Commit is atomic over canonical state, evidence, and a durable consequence
outbox. Concordia drains outbox items idempotently to deliver observations or
schedule follow-up activation. The world owns the semantic obligation;
Concordia owns its execution timing. There must not be two authoritative work
queues.

For same-moment group action, all actors reason from revision `R`. Concordia's
simultaneous engine collects their intents, one declared joint transition
authority proposes a transaction against `R`, and validation either commits
the complete transaction or rejects it. This slice does not implement general
multi-authority distributed transactions.

### `TransitionEvidenceV1`

Retain:

- proposal/configuration digest and coverage report;
- actor context and assimilation result;
- semantic intent;
- adjudicator context;
- provider, model, model version when available, route, decoding/reasoning
  configuration, exact structured output, and stated rationale;
- authority metadata and patch grammar identity;
- proposed transaction, validation results, committed revision, and outbox;
- resulting actor-safe observations;
- checkpoint lineage; and
- runtime-generated adoption receipt.

Call this auditability and replayability. Do not claim that rerunning an LLM
authority reproduces the same trajectory or that it implements a stable known
probability distribution.

## Existing seams to reuse

| Concern | Required disposition |
| --- | --- |
| `PersonDraft` and behavioral-profile semantics | Reuse; do not reduce people to role labels |
| `AuthoringDraftStore` revision/conflict behavior | Extend for the new proposal kind |
| `/api/authoring/drafts` conversation/revision lifecycle | Extend; do not create a competing public authoring product |
| `llm_client` | Reuse for authoring, actor, assimilation, and adjudicator calls |
| Existing closed workflows and retained runs | Preserve read/run compatibility; do not migrate historical artifacts |
| Public completed-run catalogue | Reuse as the only catalogue |
| Automatic staged replay and graph | Extend its generic projection; no scenario-specific walkthrough |
| Waltzman analysis | Adapt to a theory-neutral general run-evidence projection; preserve evidence step-down and nonclaims |
| Existing `composition.py` registry/receipt | Supersede with a versioned general registry/receipt; keep V1 readable |
| `data_contracts.composition` | Defer unless implementation exposes concrete duplication; it is not runtime authority |

## API contract

Preserve the current URL family and add the new proposal as the default
creation mode:

| Action | Endpoint | Result |
| --- | --- | --- |
| Create empty draft | `POST /api/authoring/drafts` | Existing revision-0 document with `target_kind=general_world_v1` |
| Generate/revise | `POST /api/authoring/drafts/{id}/messages` | Retained semantic proposal, diagnostics, and coverage |
| Read | `GET /api/authoring/drafts/{id}` | Complete retained draft revision |
| Preview | `GET /api/authoring/drafts/{id}/preview` | Canonical world projection, coverage report, composition receipt |
| Direct edit | `PUT /api/authoring/drafts/{id}/general-proposal` | Validated replacement at expected revision |
| Approve | `POST /api/authoring/drafts/{id}/approve` | Immutable approved proposal/registry/configuration identity |
| Run | `POST /api/authoring/drafts/{id}/runs` | Concordia run identity and polling surface |
| Read run | Existing run endpoints | Generic summary, projection, walkthrough, and evidence |

Existing template drafts remain readable and executable. New public drafts use
`general_world_v1`; do not append `general_world_v1` as another
`workflow.template_id` inside `ScenarioDraftProposal`.

## Implementation file map

Create:

```text
src/cybernetic_influence/general_simulation/
  models.py                 # contracts above
  registry.py               # trusted components and patch grammars
  compiler.py               # semantic proposal -> Concordia configuration
  world_component.py        # canonical state, validation, commit, outbox
  context.py                # actor/adjudicator context projections
  actors.py                 # Concordia person binding and assimilation/action calls
  authorities.py            # deterministic and Luna transition authorities
  evidence.py               # retained transition and adoption receipts
  runner.py                 # stock Concordia composition, no second loop
  projection.py             # generic run/replay projection
  analysis_projection.py    # general evidence surface consumed by theory modules
```

Extend:

```text
src/cybernetic_influence/authoring/models.py
src/cybernetic_influence/authoring/service.py
src/cybernetic_influence/authoring/store.py       # only if proposal-kind persistence requires it
src/cybernetic_influence/api.py
public/waltzman/index.html
public/waltzman/app.js
public/waltzman/styles.css
tests/test_public_waltzman.py
```

Add focused tests rather than another scenario package:

```text
tests/test_general_simulation_models.py
tests/test_general_simulation_compiler.py
tests/test_general_world_component.py
tests/test_general_simulation_information.py
tests/test_general_simulation_checkpoint.py
tests/test_general_simulation_authoring.py
tests/test_general_simulation_api.py
tests/test_general_simulation_replay.py
tests/fixtures/general_simulation/port_coordination.json
tests/fixtures/general_simulation/service_incident.json
```

Pin the tested stock Concordia revision before implementation. Start from
`131ed0d2ea14754539a3feb9dfd3717d11e859df`, the revision used by the accepted
current-source revisit. Add it to the exact environment lock and record whether
the installed artifact is a commit-pinned source install or an exactly matching
release. Do not depend on an unpinned local checkout.

## Ordered implementation slices

### 28A — Make authoring discoverable

**Estimate:** 2–4 hours. **Epistemic state:** fully specifiable now.

- Collapse the empty-draft hero.
- Place `#create-prompt` and `#create-generate` in the first desktop viewport.
- Rename the heading to **Describe a simulation** and the action to
  **Generate editable simulation**.
- Preserve the existing bounded influence-network route until the new general
  route is ready; label that boundary honestly.

**Pass:** at 1440x900 and 390x844, a fresh `?view=create` load shows the prompt
and primary action without scrolling; keyboard focus can reach both; the
existing example prompt still generates through the current API; no console or
failed-request errors.

This slice may be deployed independently with deployment approval.

### 28B — Productionize Slice 27's Concordia world-transition seam

**Estimate:** 4–6 focused days. **Epistemic state:** conditional on the pinned
Concordia install matching the reviewed public seams.

Implement the general contracts, canonical-world component, actor/adjudicator
contexts, patch grammar, base revision/preconditions, atomic commit/outbox,
strict checkpoint codec, and runtime-generated adoption receipt. Port the
bridge/port proof from configuration data without scenario-specific classes.

**Pass:** P27-1 through P27-11 pass, plus the transaction includes
`base_revision`, typed targets, preconditions, patch-grammar identity, and
durable consequences. Two authentic Luna calls complete. The new package has
no import or runtime receipt from the old sessions.

**Stop:** if stock Concordia requires a private fork, state cannot restore
losslessly, or project code must run another activation loop, stop at the
failing seam and return to ADR-013.

### 28C — General authoring, registry resolution, and coverage

**Estimate:** 3–4 focused days. **Epistemic state:** fully specifiable after
28B freezes the configuration contract.

Add `GeneralSimulationProposalV1` to the retained authoring lifecycle, update
the authoring prompt, resolve semantic component requests, compile to the
Concordia world, and generate `ExecutionCoverageReportV1` plus the adoption
receipt.

**Pass:** both canonical descriptions generate valid editable proposals; an
unknown material behavior remains visibly unapprovable; invented implementation
references are rejected; no domain-specific Python or workflow template is
added.

### 28D — General review and direct editing

**Estimate:** 2–3 focused days. **Epistemic state:** fully specifiable after
28C fixes the proposal/preview schemas.

Render question, people, world records, information paths, authorities,
coverage, assumptions, and unresolved items. Add direct typed edits for the
main semantic fields plus conversational revision. Keep raw JSON advanced.

**Pass:** a browser user can change one person's character, one information
recipient, one world-state value, and one timing value without a model call;
the revision is retained and recompiles; a stale revision receives an explicit
conflict rather than overwriting newer state.

### 28E — Live group execution and automatic replay

**Estimate:** 3–4 focused days. **Epistemic state:** exploration required for
Luna latency and structured-output reliability, not for architectural
ownership.

Bind the canonical port coalition to Concordia, run each same-moment actor from
one frozen revision, batch intents through the declared transition authority,
commit atomically, retain the evidence, and feed the existing run catalogue and
replay projector. Adapt the Waltzman module to consume the general evidence
projection without adding port-specific analysis rules.

**Pass:** one approved live port run completes; all expected model calls have
completed traces; refresh reopens the same run without more calls; the generic
walkthrough displays the run without port-specific rendering code; and every
Waltzman finding shown for the run identifies its method, evidence references,
uncertainty, and limitation.

### 28F — Cross-domain proof and Waltzman handoff

**Estimate:** 2–3 focused days. **Epistemic state:** exploration required.

Generate and run the smaller service-incident example through exactly the same
seams. Compare its registry and runtime receipt with the port run. Then prepare
the public entrypoint and three-action stakeholder script.

**Pass:** no production source change is required after the service-incident
proposal is generated; only retained proposal/run data changes. Both runs open
through **All simulations** and show automatically derived node/edge keys and
staged replay. The live public service reports the exact deployed commit.

## Acceptance matrix

| ID | Criterion | Evidence |
| --- | --- | --- |
| S28-1 | Prompt and primary action are visible on first load | Desktop/mobile browser screenshots and geometry assertions |
| S28-2 | Ordinary language produces a retained editable general proposal | Draft API, proposal digest, exact authoring trace |
| S28-3 | Compiler reports exact/coarse/descriptive/unsupported coverage from actual registry resolution | Positive and unsupported fixtures plus review UI |
| S28-4 | User can revise by prose and directly edit central semantic fields | API revision history and browser flow |
| S28-5 | Concordia owns the general run lifecycle and old sessions do not execute | Import guard, runtime-generated adoption receipt, execution trace |
| S28-6 | Actor and adjudicator contexts preserve the declared information boundary | Hidden-fact negative control and retained contexts |
| S28-7 | Open semantic intents become typed, revision-bound transactions validated before atomic commit | Port run transition evidence and invalid transaction tests |
| S28-8 | Same-moment actors reason from one revision and no incidental actor order decides the result | Frozen-context IDs, joint transaction evidence, contention fixture |
| S28-9 | Checkpoint restore is strict and lossless | Fresh-instance continuation and corrupt-checkpoint failure |
| S28-10 | Completed general runs automatically receive catalogue, walkthrough, graph, and evidence views | Port and service-incident browser flows |
| S28-11 | A second domain uses the same production seams without new scenario code | Source diff review and matching registry/compiler/runner receipt fields |
| S28-12 | Public claims remain bounded to synthetic conditional trajectories | Rendered limitations and methodology link |
| S28-13 | Waltzman findings consume the general run-evidence projection and step down to retained interactions | Port-run analysis API and browser evidence |

## Focused verification

Before broad regression work, execute in this order:

1. deterministic model/registry/patch/checkpoint tests;
2. one provider-free authoring-to-replay fixture for each domain;
3. one authentic Luna authoring canary parsed through the production schema;
4. one authentic Luna actor plus adjudicator bridge/port continuation;
5. the complete port run;
6. the smaller cross-domain run;
7. desktop public browser flow from empty prompt through reopened replay;
8. mobile first-screen and replay smoke check; and
9. deployed `/api/config`, browser console/network, service log, and exact-build
   verification.

Do not treat provider-free fixtures as completion of 28C, 28E, or 28F. Do not
run broad suites before the first authentic full vertical unless a focused
failure implicates shared code.

## External call budget

The canonical port target is:

- one authoring call;
- four actor calls per moment across three moments, run in a safe parallel
  batch: twelve actor calls;
- one joint adjudication call per moment: three adjudicator calls; and
- no mandatory narrator or separate critic call.

Target total: sixteen semantic calls with serial depth seven (authoring, then
three actor/adjudicator pairs). Assimilation should be integrated into the
actor call for the first live vertical unless a canary shows that the combined
schema is unreliable; the contract still retains attended observation and
memory-update fields separately.

Use Luna unless it causes an observed route or schema failure; report that
immediately rather than silently switching to Terra. Before the full run,
measure the exact prompt/schema size, latency, observed accounting, and
structured parse on one authoring and one actor/adjudicator canary. Retain every
completed moment so a late call resumes from the last validated checkpoint.
Use the existing public per-run cost boundary unless the user separately
changes it; do not invent a new budget or hidden fallback.

The second-domain run should use the smallest agent/moment count that still
tests the same seams. It is a generality probe, not another polished case
study.

## Time and stopping boundary

| Scope | Strong implementation agent | Less capable sequential agent |
| --- | ---: | ---: |
| Discoverability repair only | 2–4 hours | up to 1 day |
| Foundation plus general compiler, no polished public flow | 7–10 focused days | 2–3 weeks |
| Full plan through two live, automatically replayed domains | 14–20 focused days | 3–5 weeks |

The earlier one-week estimate applies only to a shortcut on the current runtime
or to stopping after an internal general-composition probe. It does not cover
the architecture-correct stakeholder pilot defined here.

Use the workspace progress tripwire. In addition, stop and reassess if:

- two consecutive increments produce only contracts/tests without a runnable
  actor-to-world transition;
- the implementation introduces a scenario-specific runtime or results page;
- the general proposal requires generated executable code;
- the project component begins choosing actors or advancing time;
- the second domain requires kernel fields rather than a registered extension;
  or
- three authentic attempts fail at the same Luna/schema boundary without new
  evidence.

## Non-goals

- predictive validity or calibrated human/institutional behavior;
- arbitrary executable semantics from arbitrary prose;
- a universal ontology containing every social or physical concept;
- general distributed transactions or several simultaneous transition
  authorities;
- live creation/removal of autonomous Concordia actors;
- dynamic coarse-to-fine resolution changes during a run;
- a new case-study page for either exemplar;
- a broad model comparison, prompt bakeoff, or security-hardening program; or
- deletion/migration of historical drafts and runs.

## Stakeholder handoff after completion

```text
URL: /waltzman/?view=create
Starting action: describe a coordination or influence situation in ordinary language
Review actions: inspect coverage; directly edit one person or information path
Run action: approve and run with Luna
Expected insight: see how local observations, interpretations, attempts, and world
  consequences accumulate into a collective trajectory
Known limitation: synthetic conditional exploration, not prediction or empirical
  measurement of real people or institutions
```

## Exact next action for the implementation agent

Implement 28A first and obtain the browser geometry evidence. Then implement
28B using `docs/handoffs/027-foundation-implementation.md`; do not begin the
general authoring schema until the bridge/port world can execute and restore
under stock pinned Concordia without the old runtime. The first authentic
actor-to-world transition—not a schema or mock—is the next architecture gate.
