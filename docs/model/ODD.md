# Cybernetic Influence v3 as a software system: an ODD-style model

Status: implemented-system description at commit `16b1791` (2026-10-08). It describes what the code does, not the target architecture in `docs/ROADMAP.md`. Machine-readable twin: [cybernetic_influence_model.toml](cybernetic_influence_model.toml), checked against the code by `tests/test_system_model.py`. What each view shows of this model: [VIEW_COVERAGE.md](VIEW_COVERAGE.md).

**Two levels, kept apart.** This repository simulates worlds: a regional outbreak, a service outage, a pencil supply chain. This document is **not** about any of those worlds. It models the *software system that holds them*: the kinds of things an author can declare, what the system stores, the processes that change what it stores, and the records each process writes. Section 4 is the part to compare against another repository's model, kind by kind.

The format follows ODD (Overview, Design concepts, Details), the standard protocol for describing agent-based models, applied to the system rather than to a simulated world. Shape and rules: Company Planning's `references/system-model.md`; closest worked example: World Substrate's `docs/model/`.

## 1. Purpose and the questions the system answers

**Purpose** (`AGENTS.md`, "Product Framing"). An analyst describes a bounded socio-technical world in conversation; a model drafts a typed world definition; a trusted compiler says exactly how each requested behavior would execute; the analyst edits and approves it; Concordia runs people (LLM actors) and the world (a game master holding typed state) moment by moment; every attempted change, model call and checkpoint is retained; analyses read that evidence afterwards and never change it (ADR-014). It explores conditional pathways under declared assumptions; it is not a prediction engine.

Questions the system is built to answer, for a person or an investigating agent:

1. What kinds of things can a world contain, and what did this author declare? (section 4.1)
2. For each behavior the author asked for, will it execute exactly, by an LLM judgment, only as description, or not at all? (CoverageReport)
3. Was this exact configuration approved before it ran? (draft approval digests, re-checked at run time)
4. Who could see what: which hidden state, which information, which routes? (visible_to_actor_ids, recipient_ids, sensing rules, ActorContext)
5. For each moment: what did each person receive and attempt, and what did the world accept or refuse, and why? (TransitionEvidence)
6. Was the run actually executed by Concordia, and can it be resumed? (AdoptionReceipt, checkpoints)
7. What did it cost, and which model calls produced it? (ModelCallReceipt)
8. What does an analysis lens conclude, from which evidence? (RunEvidenceBundle, AnalysisResult)

## 2. Expected observable patterns (if the system works)

| # | Pattern | Where it is observable |
| --- | --- | --- |
| P1 | A draft revision only ever advances by exactly one, and a stale revision is refused. | `AuthoringDraftStore.replace` raises `DraftConflictError` (`authoring/store.py:116-125`); HTTP 409 |
| P2 | A run starts only from an approved draft whose bundle, scenario, run spec and registry digests still match the approval. | `GeneralDraftAuthoringService.approved_compile` (`general_simulation/authoring.py:1379-1403`) |
| P3 | Approval is refused while any coverage item blocks or any diagnostic exists. | `approve` (`general_simulation/authoring.py:1330-1341`) |
| P4 | Only one live run executes at a time. | `live_lock` (`api.py:2642`); "another live run is already active" (`api.py:3923`) |
| P5 | Every attempted world transaction leaves one TransitionEvidence; a refused one leaves the world revision unchanged and names its errors. | `CanonicalWorld.validate_and_commit` (`general_simulation/world.py:233-423`) |
| P6 | Every model call leaves one ModelCallReceipt, and the run's `model_calls` equals their count. | `projection.py` `"model_calls": len(result.model_calls)` |
| P7 | A run is executed by Concordia's simulation and engine at the pinned revision, with actors selected by `NextActingAllEntities`. | `AdoptionReceipt` (`runner.py` `_run_compiled_general_simulation`); `CONCORDIA_REVISION` (`concordia_runtime.py:55`) |
| P8 | A person sees another record's hidden state only if listed in `visible_to_actor_ids`, and receives an information item only if listed in its `recipient_ids`. | `ActorAccessSpec` from the compiler (`compiler.py`, ~:1313); recipient check in `validate_and_commit` |
| P9 | Analysis never changes the run's world state, model-call count or evidence digest. | ADR-014; `analyze_run` writes only analysis fields on the run |
| P10 | A process restart never leaves a run claiming to be running. | `RunStore.mark_incomplete_interrupted` at app start (`run_store.py:190`, `api.py:2634`) |

## 3. Boundary

**Inside** this repository:

- The world-definition schema (section 4.1), the authoring conversation and repair loop, the dependency review, the trusted compiler and component registry, approval.
- The Concordia-owned run loop's project components: `CanonicalWorld` (typed world truth and atomic commit), person and world prefabs, acting components, checkpoint validation.
- Retained documents: drafts, runs, experiments, the public spend ledger.
- The FastAPI app (`api.py`), the public app wrapper (`public_waltzman.py`), the two workbench pages and the CLI vertical.
- The pre-migration fixed scenarios (`scenarios/`, `causal_core/`, `active_runtime/`) and scripted assays: inside, but summarized here as `LegacyTemplateDraft`, `run_fixed_scenario` and `scripted_assays` rather than modeled in detail.

**Outside:**

- Concordia (pinned revision `131ed0d2…`) owns entity lifecycle, actor selection, the game-master loop and checkpoint invocation (ADR-013).
- LLM providers, reached only through the shared `llm_client` (`call_llm_structured`); traces live there.
- Hosting: the public demo runs on the VPS (`/srv/apps/waltzman/`, per issue #49); `make serve` runs locally.
- World Substrate: its living-scene page is served here as a pinned, read-only artifact (`/world-substrate`), not executed.
- Whether any simulated world is true of the real world.

## 4. Entities and their state

Full field lists are in the defining classes; the model file's `[[entities]]` gives each class as `file:Class` and the drift test checks every one exists.

### 4.1 Kinds of things an author can declare (the world-definition schema)

All parts are defined in `src/cybernetic_influence/general_simulation/authoring_models.py` unless another file is named. They are shared by two envelopes:

- **V1** `GeneralSimulationProposalV1` (draft `target_kind = general_world_v1`): one document with everything, including the schedule. Its validator `unique_ids_and_references` (`:322`) requires unique IDs in every collection, that every component request and every transition contract has a scheduled moment, that a moment activating a request also activates its contracts, and that every transition contract belongs to a request.
- **V2** `AuthoredSimulationBundleV2` (`study_models.py`, draft `target_kind = general_world_v2`, what `POST /api/authoring/drafts` creates today): `ScenarioSpecV2` (what exists, `contracts_v2.py`) plus `RunSpecV2` (how it runs, including the schedule), `AnalysisSpecV2` list, unresolved questions and an optional analyst question. `validate_run_against_scenario` (`contracts_v2.py:246`) ties a run spec to its scenario digest.

| Kind | Defining class | What an author declares | What it becomes at run time |
| --- | --- | --- | --- |
| Person | `GeneralPersonDraft` (+ `GeneralBehavioralProfileDraft`) | `entity_id`, `label`, `position`, `disposition`, `memories` (≥1); behavioral profile lists: values, goals, beliefs, decision_tendencies, social_perceptions, current_state, capabilities, limitations | a `WorldRecord` of kind `person` with `position` public and `disposition` and `behavioral_profile` hidden (`compiler.py:1160-1172`); a Concordia entity (`GeneralPersonPrefab`, `runner.py:1967`); starting memories via `CanonicalWorld.retain_memory` (`runner.py:2027`) |
| World record | `GeneralWorldRecordProposalV1` | `record_id`, open `kind`, `label`, `public_state` and `hidden_state` (key/value `StateEntryV1`), `visible_to_actor_ids` | `models.WorldRecord` (`state`, `hidden_state`); visibility compiled into `ActorAccessSpec` |
| Active system | `GeneralActiveSystemProposalV1` | `subject_refs`, `behavior_summary`, `representation_strategy` (detailed / coarse_surrogate / inert), `causal_responsibility_tags` | `models.ActiveSystemSpec` |
| Component request | `ComponentRequestV1`; V2 `contracts_v2.ComponentRequestV2` | a behavior to execute: subjects, required reads, desired effects, `fidelity_need` (exact / bounded / coarse / descriptive), materiality, `transition_contract_ids` | one `CoverageItemV1`; a registry component or exact contracts under a `TransitionAuthoritySpec` |
| Place | `GeneralPlaceProposalV1` (in `SpatialExtensionV1`) | `place_id`, `label`, `state` | `models.Place` (id and label only; place `state` is not carried) |
| Placement | `GeneralPlacementProposalV1` | a record located at a place | `models.Placement` |
| Spatial link | `GeneralSpatialLinkProposalV1` | route between places, `operational`, public/hidden state, `visible_to_actor_ids` | `models.Route` |
| Information representation | `InformationRepresentationProposalV1` (in `InformationExtensionV1`) | `content`, `apparent_source`, `recipient_ids`, `hidden_provenance` | `models.Representation`; delivered as `Observation`/`Consequence` only to listed recipients |
| Resource stock | `ResourceStockProposalV1` (in `ResourceExtensionV1`) | `resource_id`, `quantity`, `custodian_id`, `conserved` | `models.ResourceStock` |
| Relationship | `RelationshipProposalV1` (in `RelationshipExtensionV1`) | `participant_refs` (≥2), `description`, `material_to_question` | **nothing executable**: the compiler never reads it; it appears only in the configuration graph (`composition_graph.py:74-78`). See 4.3 |
| Scheduled moment | `ScheduledMomentProposalV1` (V1 `schedule`; V2 `RunSpecV2.scheduled_moments`) | `minute`, description, injected representations, active component requests and transition contracts | one Concordia step; `GeneralMomentEvidence` |
| Sensing rule | `SensingRuleProposalV1` | observers may read named hidden keys of one subject; result written to an output record for named recipients | `models.SensingTransitionContract` (exact) |
| Resource transformation | `ResourceTransformationProposalV1` | operators turn input quantities into an output, up to `maximum_batches`, mirrored in a public inventory record | `models.ResourceTransformationContract` (exact) |
| Resource transport | `ResourceTransportProposalV1` (+ `TransitionPreconditionProposalV1`) | move a quantity between custodians and places along allowed routes; arrival keys; preconditions | `models.ResourceTransportContract` (exact) |
| Analysis spec | `AnalysisSpecV1` (profile `waltzman_coordination_v1` only); V2 `analysis/theory_analysis.AnalysisSpecV2` | a lens fixed before the run | applied after the run to the `RunEvidenceBundleV2` |
| Plain-text lists | fields of the envelopes | `fidelity_assumptions`, `declared_invariants`, `analysis_requests` (V1), `unresolved_questions`, title, question, description | assumptions and invariants copied into `GeneralWorldSpec`; unresolved questions become draft diagnostics |

What the compiler and reviewers add to a declaration:

| Kind | Defining class | State that matters |
| --- | --- | --- |
| Coverage report | `ExecutionCoverageReportV1` | `registry_digest`, items, `blocking_request_ids`; `approvable` is true only with no blockers |
| Coverage item | `CoverageItemV1` (+ `DependencyEnforcementItemV1`) | `classification` exact / coarse_llm / descriptive / unsupported; `causal_closure` exact / partial / coarse / descriptive / unsupported; what can and cannot change; per-dependency enforcement exact_read / exact_write_only / coarse_llm / descriptive / unsupported |
| Authoring discussion | `GeneralAuthoringDiscussionV1` | `reply`, `understood_summary`, `material_questions` |
| Dependency review | `DependencyCompletenessReviewV1` (+ `MissingDependencyFindingV1`, `ExactGuardRepairV1`) | `complete` / `repair_required`; each missing prerequisite with a required resolution |
| Compiled simulation | `compiler.CompiledGeneralSimulationV2` (V1: `CompiledGeneralSimulationV1`) | digests, coverage, `GeneralWorldSpec`, resolved components, configuration graph |
| World spec | `models.GeneralWorldSpec` | initial state, active systems, authorities, invariants, assumptions, timing, actor access, the three contract lists |
| Transition authority | `models.TransitionAuthoritySpec` | `general_deterministic_mechanics` (exact entries) and `general_semantic_adjudicator` (coarse_llm entries): patch grammar (operations create / remove / replace / rebind on record / place / placement / route / representation / resource), reads, writes |
| Actor access | `models.ActorAccessSpec` | per actor, which records' hidden state and which routes are visible |

The component registry (`general_simulation/registry.py`) holds five components: spatial topology, information delivery and conserved resources (exact), bounded person action and joint semantic adjudication (coarse_llm).

### 4.2 Run-time state and evidence (`general_simulation/models.py` unless named)

| Entity | Defining class | State that matters |
| --- | --- | --- |
| Canonical world | `world.CanonicalWorld` | the Concordia game-master component holding the current `GeneralWorldState`, the evidence list, per-actor private memory and the outbox; `validate_and_commit` is the only writer of state |
| World state | `GeneralWorldState` | revision, records, places, placements, routes, representations, resources, outbox, delivered consequence ids |
| Actor context | `ActorContext` | what one actor is shown at one moment: observations, accessible records and routes, private memory, available transition contracts, phase |
| Action intent | `SemanticActionIntent` | action, targets, purpose, expected effect, rationale, selected contracts and arguments |
| Transition evidence | `TransitionEvidence` | the `WorldTransaction`, envelope corrections, `ValidationResult` (accepted, revisions, errors), resulting state hash, per-operation attribution |
| Model call receipt | `ModelCallReceipt` | role actor / adjudicator, provider, model, trace id, input, output, corrections, cost |
| Moment evidence | `GeneralMomentEvidence` | frozen and resulting revision, actors, intents, checkpoint hash |
| Checkpoint | none (a Concordia checkpoint dict) | validated by `runner._strict_general_checkpoint` (`runner.py:933`); resume loads it |
| Adoption receipt | `AdoptionReceipt` | Concordia simulation and engine classes, actor selection component, revision, lifecycle events |
| Simulation result | `GeneralGroupSimulationResultV2` | final state, all evidence, all receipts, moments, checkpoints, adoption |
| Run evidence bundle | `analysis/theory_analysis.RunEvidenceBundleV2` | initial and terminal state digests, evidence records, assumptions, known omissions, record digest |
| Analysis result | `analysis/theory_analysis.AnalysisResultV2` | findings with evidence refs; coverage supported / degraded / unsupported |

### 4.3 What the schema can say that the runtime does not use

Established from the code at `16b1791`:

- **Relationships** are accepted, validated for unique IDs and drawn in the configuration graph, but `_compile_general_simulation` (`compiler.py:487`) never reads `relationship_extension`. A relationship changes no world state, no actor context and no transition. (VIEW_COVERAGE G10.)
- **Place state** (`GeneralPlaceProposalV1.state`) is not carried into `models.Place`, which has only `place_id` and `label` (`compiler.py:1178-1181`).
- **`analysis_requests`** (V1) and **`unresolved_questions`** do not reach the world spec; unresolved questions surface as draft diagnostics.

### 4.4 Stored documents

| Entity | Defining class | Where | State that matters |
| --- | --- | --- | --- |
| Authoring draft | `authoring/store._DraftDocument` | `<runs parent>/authoring_drafts/draft_<12 hex>.json` | `target_kind` (legacy_templates_v1 / general_world_v1 / general_world_v2), `revision`, `status` (draft / repairing / needs_input / ready_for_review / approved), messages (with `source`), attempts (accepted / repair / needs_input / provider_error), proposal, coverage, configuration graph, diagnostics, approval digests |
| Run | `run_store.RunStore` (document has **no** schema class) | `<runs dir>/run_<12 hex>.json`; trash in `.trash/` | `status`, scenario, profile, `model_calls`, cost, LLM configuration, authoring identity, live progress, `general_checkpoint`, projected nodes / edges / events / traces, `general_simulation`, `run_evidence_bundle`, analysis results |
| Experiment | `experiment_store.ExperimentResultV2` | `<runs parent>/experiments/experiment_<12 hex>.json` | draft id, base scenario digest, status running / completed, one result per condition × repetition (completed / failed, run id) |
| Spend ledger | `public_spend_controls.SpendLedger` | `spend_controls.json` beside the runs dir | per-day counters (durable); per-address windows (memory only) |
| Legacy template draft | `authoring/models.ScenarioDraftProposal` | inside a draft with `target_kind = legacy_templates_v1` | fixed-scenario people, objects, information, workflows |

Run status values found written in code (not a typed vocabulary, so the drift test does not enforce them): `running`, `completed`, `failed`, `paused`, `pause_requested`, `stop_requested`, `narrating`, `interrupted` (in `api.py` handlers and `RunStore.mark_incomplete_interrupted`). `DELETE /api/runs/{id}` answers `"status": "trashed"` but that is the response, not a stored status: the file is moved to `.trash/`.

## 5. Processes and scheduling

Request-driven service; long work runs on background threads. Inside a run, time is the scheduled moment (a minute value) and one Concordia step per moment.

| Process | Trigger (routes) | Changes | Writes |
| --- | --- | --- | --- |
| create_draft | `POST /api/authoring/drafts` (+ legacy, reviewed-coordination, reviewed-component-composition) | AuthoringDraft | authoring_draft |
| converse | `POST …/drafts/{id}/messages` (job), `GET /api/authoring/jobs/{job_id}` | draft, bundle, coverage, dependency review | authoring_draft |
| read_draft | `GET …/drafts/{id}`, `GET …/drafts/{id}/preview` | nothing | nothing |
| edit_draft | five `PUT …/drafts/{id}/…` routes | draft, bundle, coverage | authoring_draft |
| approve_draft | `POST …/drafts/{id}/approve` | draft approval | authoring_draft |
| run_approved_draft | `POST …/drafts/{id}/runs` | the whole of 4.2 | retained_run |
| run_experiment | `POST …/drafts/{id}/experiments`, `GET /api/experiments/{id}` | Experiment, Run | experiment_record, retained_run |
| run_fixed_scenario | `POST /api/runs`, scenario preview, regional-outbreak comparison | Run | retained_run |
| control_run | `POST /api/runs/{id}/pause`, `/stop`, `/resume` | Run, Checkpoint | retained_run |
| read_runs | `GET /api/runs`, `/{id}`, `/progress`, `/summary` | nothing | nothing |
| analyze_run | `POST`/`DELETE /api/runs/{id}/analyses…` | AnalysisResult | retained_run |
| trash_run | `DELETE /api/runs/{id}` | Run | retained_run |
| scripted_assays | composite-assay and coordination-experiment routes | Run | retained_run |
| recover_on_start | `create_app` | Run | retained_run |
| public_spend_control | middleware; `GET /api/public-limits` | SpendLedger | public_spend_ledger |
| serve_pages | `GET /`, `/assets`, `/api/config`, `/review`, `/world-substrate…` | nothing | nothing |
| bridge_port_cli | `python -m cybernetic_influence.general_simulation --output` | fixed vertical | bridge_port_result |

Every route the code declares is listed under exactly one process in the model file; the drift test fails on any route added or removed without updating it. There is **no route that lists drafts or experiments** (VIEW_COVERAGE G1, G8; issue #49).

**Moment order inside `run_approved_draft`** (`runner.py:2106-2225`). `_build_simulation` creates one Concordia entity per person and one world game master holding `CanonicalWorld`; a retained checkpoint is loaded when resuming; `simulation.play(max_steps=remaining)` runs one step per remaining scheduled moment, and after each step a checkpoint is retained and progress (`completed_moments`, `model_calls`) is saved into the run document. Each person acts on a bounded `ActorContext` (observation, assimilation and intent model calls, `role = actor`); the game master adjudicates or applies exact contracts and calls `validate_and_commit`. After the last moment the result is projected (`projection.project_general_run`), the evidence bundle built, and pre-registered analyses applied.

## 6. Design concepts

- **Proposal versus authority.** The model proposes typed data only; `authoring_models.py` holds "no Python references, prompt fragments, or executable predicates. The trusted compiler owns every implementation binding." Coverage says how each request will execute before anyone approves it.
- **Approval binds digests.** Approval records bundle, scenario, run-spec, registry and world-spec digests; execution recompiles and refuses on any mismatch.
- **Atomic commit or refusal.** `validate_and_commit` checks, in order: base revision equals current revision; transaction intent ids equal the actors' intents; the authority exists; each operation is inside that authority's patch grammar unless an exact contract covers it; each consequence names a representation the recipient is allowed to receive; preconditions hold; moves follow an operational route; the typed state validates; invariants hold. Any error leaves the world unchanged and is recorded.
- **Observation versus truth.** Actors see only `ActorContext`; hidden state is visible only through `visible_to_actor_ids` or a sensing rule; information reaches only its `recipient_ids`. Analyses are read-only (ADR-014); trust, risk and coordination measures are derived views (ADR-012).
- **Stochasticity.** Actor and adjudicator calls are LLM calls through `llm_client` (receipts record whether exact replay is possible); exact contracts are deterministic.
- **Fail closed.** Corrupt drafts and runs raise instead of loading; the spend ledger refuses spend it cannot reserve; restart marks unfinished runs interrupted.

## 7. Inputs

- Author messages and direct edits; run options (model, reasoning effort, cognition mode); experiment conditions.
- LLM outputs via `llm_client` (authoring: up to 5 attempts at most $0.60 each, `general_simulation/authoring.py:57-68`; simulation: $0.10 per call cap in `concordia_runtime._call_model`).
- Environment: `CYBERNETIC_INFLUENCE_RUNS_DIR`, `CYBERNETIC_INFLUENCE_LIVE` (live runs refused without it), `CYBERNETIC_INFLUENCE_ALLOWED_TAILSCALE_USERS` (`_require_access`, `api.py:6476`), public root and spend settings.

## 8. Events and records

The machine-readable list, with every writer's file and function, is the model file's `[[records]]`. Summary:

| Record | Store | Logical writers | Physical writer |
| --- | --- | --- | --- |
| `authoring_draft` | `AuthoringDraftStore.create/replace` | 15 functions in `api.py`, `authoring/service.py`, `general_simulation/authoring.py` | `authoring/store.py` `_write` |
| `retained_run` | `RunStore.save/trash/trash_many/mark_incomplete_interrupted` | 23 functions in `api.py`, `analysis/coordination.py`, `experiments/composite_agency.py`, `experiments/coordination_experiment.py` | `run_store.py` `save`, `trash`, `trash_many` |
| `experiment_record` | `ExperimentStore.save` | `api.py` `create_draft_experiment`, `persist` | `experiment_store.py` `save` |
| `public_spend_ledger` | none | `public_spend_controls.py` `_save` | same |
| `bridge_port_result` | none | `general_simulation/__main__.py` `main` | same |

In-run events (TransitionEvidence, ModelCallReceipt, MomentEvidence, checkpoints) are not separate files: they are retained inside the `retained_run` document (`general_simulation`, `general_checkpoint`, `live_progress`).

## 9. Views

Four views, each a projection of this model; [VIEW_COVERAGE.md](VIEW_COVERAGE.md) has the element-by-view table and 16 numbered gaps:

- `public_workbench`: `public/waltzman/` served by `cybernetic_influence.public_waltzman:app`. The only page that renders general-world drafts and runs.
- `local_workbench`: `web/` served by `make serve`. Fixed-scenario runs and legacy drafts; it has no general-world rendering (G2) and four of its page routes return 500 (G3).
- `api_json`: the API itself.
- `cli`: the bridge/port vertical's output file.

## 10. Unknowns and limits of this model

- The run document has no schema class, so its fields and status values are documented from the writing code, not enforced.
- View cells were judged from page source and HTTP probes, not from a rendered browser session (VIEW_COVERAGE G15).
- Fixed-scenario engines (`causal_core/`, `active_runtime/`, `scenarios/`) are summarized, not modeled entity by entity.
