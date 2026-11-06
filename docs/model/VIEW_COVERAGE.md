# View coverage: what each Cybernetic Influence view shows of the system model

Status: observed evidence, 2026-10-08, at commit `16b1791`. Two kinds of evidence were used: HTTP probes with FastAPI's `TestClient` against `create_app` (local web root `web/` and public web root `public/waltzman/`, empty temporary stores), and reading the page sources (`public/waltzman/app.js`, `web/app.js`) with exact reference counts. No browser rendering was run in this pass, so a cell judged from source says what the page code reads and writes into the page, not what a person saw on screen. Cells that depend on rendering not checked here point to G15.

The model is [ODD.md](ODD.md) and [cybernetic_influence_model.toml](cybernetic_influence_model.toml). Each row asks: can someone using this view see this element? Values: **shown** (a structured, labelled display), **partial** (a subset of its fields, a count, or only the raw JSON panel or raw-run link), **hidden** (on purpose, reason given), **missing** (not reachable from this view), **n/a** (the view is not about this element). The same table is in the model file's `coverage` rows; `tests/test_system_model.py` checks that every entity and record has a row, every row names a declared element, and every view is filled.

Rule for raw JSON: the public Create page has an "Inspect complete typed configuration" panel (`public/waltzman/index.html:416`, filled at `app.js:2697`) and an "Open raw retained run" link to `GET /api/runs/{run_id}` (`app.js:4004`). An element reachable only through those is **partial**, not shown.

## The views

| View | What it is | Source |
| --- | --- | --- |
| `public_workbench` | Public Waltzman workbench: retained case study plus Create (converse, review world, people, information, processes and run; coverage; approve; run; experiments) | `public/waltzman/index.html` + `app.js`, served by `cybernetic_influence.public_waltzman:app` |
| `local_workbench` | Operator page from `make serve`: fixed-scenario runs, legacy drafts, pause, resume, trash | `web/index.html` + `web/app.js` (create_app's default web root) |
| `api_json` | The JSON API read directly by a script or agent | `src/cybernetic_influence/api.py`; `GET /api/public-limits` only on the public app |
| `cli` | `python -m cybernetic_influence.general_simulation --output PATH` (fixed bridge/port vertical) | `src/cybernetic_influence/general_simulation/__main__.py` |

`web/app.js` and `public/waltzman/app.js` are different files (3,913 and 4,423 lines; `diff -q` reports they differ), so the two workbenches are separate views, not one page at two addresses.

## Coverage table

| Model element | public_workbench | local_workbench | api_json | cli |
| --- | --- | --- | --- | --- |
| SimulationProposalV1 | shown | missing (G2) | shown | n/a |
| AuthoredBundleV2 | shown | missing (G2) | shown | n/a |
| ScenarioSpec | shown | missing (G2) | shown | n/a |
| RunSpec | partial (G12) | missing (G2) | shown | n/a |
| Person | shown | missing (G2) | shown | n/a |
| WorldRecord | shown | missing (G2) | shown | n/a |
| ActiveSystem | shown | missing (G2) | shown | n/a |
| ComponentRequest | shown | missing (G2) | shown | n/a |
| Place | shown | missing (G2) | shown | n/a |
| Placement | partial (G5) | missing (G2) | shown | n/a |
| SpatialLink | partial (G5) | missing (G2) | shown | n/a |
| InformationRepresentation | partial (G4) | missing (G2) | shown | n/a |
| ResourceStock | shown | missing (G2) | shown | n/a |
| Relationship | partial (G10) | missing (G2) | partial (G10) | n/a |
| ScheduledMoment | shown | missing (G2) | shown | n/a |
| SensingRule | partial (G5) | missing (G2) | shown | n/a |
| ResourceTransformation | partial (G5) | missing (G2) | shown | n/a |
| ResourceTransport | partial (G5) | missing (G2) | shown | n/a |
| AnalysisSpec | shown | missing (G2) | shown | n/a |
| CoverageReport | shown | missing (G2) | shown | n/a |
| CoverageItem | shown | missing (G2) | shown | n/a |
| AuthoringDiscussion | shown | missing (G2) | shown | n/a |
| DependencyReview | partial (G11) | missing (G2) | partial (G11) | n/a |
| CompiledSimulation | partial (G14) | missing (G2) | shown | n/a |
| WorldSpec | missing (G14) | missing (G2) | shown | n/a |
| TransitionAuthority | missing (G14) | missing (G2) | shown | n/a |
| ActorAccess | missing (G14) | missing (G2) | shown | n/a |
| CanonicalWorld | hidden | hidden | hidden | hidden |
| WorldState | partial (G6) | missing (G2) | shown | shown |
| ActorContext | partial (G15) | missing (G2) | shown | shown |
| ActionIntent | partial (G15) | missing (G2) | shown | partial (G16) |
| TransitionEvidence | partial (G15) | missing (G2) | shown | shown |
| ModelCallReceipt | partial (G15) | missing (G2) | shown | shown |
| MomentEvidence | shown | missing (G2) | shown | n/a |
| Checkpoint | partial (G7) | missing (G7) | shown | partial (G16) |
| AdoptionReceipt | partial (G7) | missing (G7) | shown | shown |
| SimulationResult | partial (G6) | missing (G2) | shown | partial (G16) |
| RunEvidenceBundle | partial (G6) | missing (G2) | shown | n/a |
| AnalysisResult | shown | missing (G2) | shown | n/a |
| AuthoringDraft | partial (G1) | partial (G1) | partial (G1) | n/a |
| Run | shown | shown | shown | n/a |
| Experiment | partial (G8) | missing (G8) | partial (G8) | n/a |
| SpendLedger | missing (G9) | n/a | shown | n/a |
| LegacyTemplateDraft | partial (G1) | partial (G1) | partial (G1) | n/a |
| authoring_draft | partial (G1) | partial (G1) | partial (G1) | n/a |
| retained_run | shown | shown | shown | n/a |
| experiment_record | partial (G8) | missing (G8) | partial (G8) | n/a |
| public_spend_ledger | missing (G9) | n/a | shown | n/a |
| bridge_port_result | n/a | n/a | n/a | shown |
| control_run | missing (G13) | shown | shown | n/a |
| serve_pages | shown | partial (G3) | n/a | n/a |

`CanonicalWorld` is **hidden** in every view on purpose: it is the in-memory Concordia component that owns the world during a run. What it holds reaches views as WorldState, TransitionEvidence and Checkpoint rows.

## Gaps

### G1. Saved authoring drafts cannot be listed
`AuthoringDraftStore` has `create`, `get` and `replace` and no list method (`src/cybernetic_influence/authoring/store.py:79-150`). The API has `POST /api/authoring/drafts` and `GET /api/authoring/drafts/{draft_id}` only; the probe `GET /api/authoring/drafts` returned **405**. The public page remembers one draft id in the URL (`?draft=`, `app.js:396`); the local page has no general-draft list either. A draft whose id is lost is reachable only on disk. Tracked as issue BrianMills2718/cybernetic_influence_v3#49.

### G2. The local workbench cannot show a general world at all
`web/app.js` has 0 references to `world_records`, `renderGeneral`, `component_requests`, `sensing_rules` or `configuration_graph` (the public `app.js` has 9, 20, 2, 2 and 4). `make serve` serves `web/`, so an operator using the local page cannot review, approve or inspect any general-world draft or run; only the public root can. Every authoring, compiled and runtime row is **missing** in this column for that reason.

### G3. Four local page routes return 500
Probe of `create_app()` with the default web root: `GET /review`, `/review/trace`, `/world-substrate` and `/world-substrate/revision.json` each returned **500** (`FileResponse` on a file that `web/` does not contain). The same four routes on the public root returned 200. `GET /` returned 200 on both.

### G4. Hidden provenance of information is never displayed
`hidden_provenance` has 0 references in both `app.js` files. The public page shows each representation's content, apparent source and recipients (`app.js:2289-2292`, node details `:2051`), so an author cannot review who really produced an item except in the raw JSON panel.

### G5. Several world-definition kinds appear only as counts, graph edges or raw JSON
Sensing rules are counted into "Information items/rules" (`app.js:2669-2678`) but not listed for a general world; resource transformations and transports are referenced only in the save-field list (`app.js:1816`) and so are visible only in the raw JSON panel; placements are drawn as graph edges only; spatial links are listed with origin, destination and operational flag (`app.js:2683-2684`) but their public/hidden state and `visible_to_actor_ids` are not shown.

### G6. The final world state and evidence bundle are reachable only as raw JSON
The run document retains the full `general_simulation` result (final state, every transition, every model call; `src/cybernetic_influence/general_simulation/projection.py`) and `run_evidence_bundle` (`api.py:4083-4085`), and `GET /api/runs/{run_id}` returns them. `public/waltzman/app.js` has 0 references to `general_simulation`, `final_state`, `accepted_transactions`, `rejected_transactions` or `run_evidence_bundle`; the page links to the raw run instead (`app.js:4004`).

### G7. Concordia checkpoints and the adoption receipt are not displayed
`general_checkpoint` and `adoption` have 0 references in both `app.js` files. These are the evidence that a run was executed by Concordia and can be resumed; they are in the run document (API) and, for the CLI, in its output file (checkpoint as hashes only, see G16).

### G8. Experiments cannot be listed
`ExperimentStore` has `save` and `get` only (`src/cybernetic_influence/experiment_store.py:95-145`); there is no list route. The public page polls one experiment by the id it just started (`app.js:4151-4160`); `web/app.js` never calls `/api/experiments`.

### G9. The public spend ledger is not shown on the public page
`GET /api/public-limits` exists (`src/cybernetic_influence/public_waltzman.py:33`) but `public/waltzman/app.js` has 0 references to `public-limits`, so a visitor sees a cap only when a request is refused.

### G10. Relationships are shown as if they shaped the run, but nothing executes them
`_compile_general_simulation` never reads `relationship_extension` (0 occurrences of `relationship` in `general_simulation/compiler.py`); relationships reach only the configuration graph (`general_simulation/composition_graph.py:74-78`), which the public page draws. No view says that a declared relationship does not enter the world state, actor context or any transition. The API returns the relationship as authored, with the same silence.

### G11. The dependency review leaves no structured record
`_DraftDocument` has no field for a `DependencyCompletenessReviewV1` (`authoring/store.py:27-47`). The review's outcome reaches the draft only as attempt messages and a trace id ending in `/dependency-review`; the public page checks only that such a trace id exists (`hasCurrentDependencyReview`, `app.js:2328-2332`) and has 0 references to `missing_dependencies` or `guard_repairs`.

### G12. Run settings are partly invisible before the run
The public page shows the schedule, `horizon_minutes` and `termination_conditions` (2 references each), but `per_call_budget`, `per_run_budget` and `seed_or_provider_seed_status` have 0 references; model and reasoning effort are chosen at run time rather than read from the RunSpec.

### G13. A public visitor cannot pause, stop or resume a run
`public/waltzman/app.js` has 0 references to `/pause` or `resume`; `web/app.js` has 16 and 14. Whether the public omission is deliberate is not recorded anywhere found in this pass (unknown).

### G14. The compiled world spec is not visible on either page
`world_spec` (initial state, transition authorities with their patch grammar, reads and writes, actor access) is returned only by `GET /api/authoring/drafts/{draft_id}/preview` (`CompiledGeneralSimulationV2.preview`, `general_simulation/compiler.py:89-100`). Neither `app.js` reads `world_spec` or `actor_access` (0 references); the public page shows coverage and the configuration graph instead, so who may change what is visible only as the coverage classification.

### G15. Which run-trace fields the authored replay renders was not checked
The public run result says it "separates what people received and attempted from what the simulated world actually accepted" (`app.js:3967`) and renders it through `renderAuthoredReplay`; per-person decisions and model-call counts are listed (`app.js:3973-3985`). Whether accessible records, private memory, available contracts, validation errors and per-operation attributions appear was not verified in a browser in this pass, so these rows are **partial** pending that check.

### G16. The CLI writes the older single-actor result shape
`run_bridge_port_vertical` returns `GeneralSimulationResult` (`general_simulation/models.py:396`), not `GeneralGroupSimulationResultV2`: it carries checkpoint hashes rather than checkpoints, actor intents only inside model-call outputs, and no moments.
