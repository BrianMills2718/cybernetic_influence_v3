---
doc_role: implementation_plan
authority: bounded_design
status: active
created: 2026-08-18
updated: 2026-08-18
depends_on:
  - docs/GOAL.md
  - docs/ROADMAP.md
  - docs/adr/006-boundaries-are-derived-coarse-grainings.md
  - docs/adr/008-separate-spatial-topology-from-routing-and-permission.md
  - docs/adr/014-separate-simulation-and-analysis-authority.md
  - docs/plans/029-separate-simulation-run-analysis.md
---

# Slice 30: unify the two frontends, add Experimentation, add a real Levin lens

## Context

`web/` (the older "Cybernetic Influence Simulator") and `public/waltzman/` (the
"Coordination Environment Lab") are two independently-maintained frontend
trees sharing one backend (`create_app()`) but almost no frontend code —
`graph-canvas.js`/`.css` are byte-identical; `app.js`, `index.html`, and
`styles.css` have diverged (7235 / 1117 / 2098 diff lines respectively).
`web/` has not been touched since 2026-08-04 and lacks the natural-language
`general_simulation` authoring flow entirely; `public/waltzman/` has received
all authoring/demo development since but lacks several capabilities `web/`
still has: matched-condition experimentation, pause/stop/resume, a
Levin analysis lens, a client-side graph projection/boundary-collapse
control, an inline contextual-help pattern, and explicit model/reasoning
selection.

An audit on 2026-08-18 (two research passes, file:line-cited) established
which of these are genuine frontend ports versus which require real backend
work:

| Capability | Backend readiness | Scope |
|---|---|---|
| Graph projection / analytical-scale collapse | `general_simulation`'s replay path hardcodes `boundaries:[]`, `trajectory:{nodes:[],edges:[]}`, `viewMode:'causal'` (`public/waltzman/app.js:2847-2851`). No boundary/grouping data is computed for `general_simulation` evidence at all. | Blocked on a product decision (§ Design C) — the underlying ontology may not transfer, not just unbuilt work. |
| Pause / stop / resume | Explicitly scenario-gated in `api.py:4813-4816` (`pause_run`) and `api.py:4848-4854` (`stop_run`) to `{service_desk, coordination_decision, coordination_decision_v1}` / the `influence_network_v1` template. `general_world_v1`/`v2` is absent from every gate. Whether the live execution loop can even be interrupted mid-run for a Concordia-driven run is unverified. | `exploration_required` before a cost estimate exists. Not scoped further in this document. |
| Experimentation (composite-assay / coordination-experiment) | `POST /api/composite-assays` (`api.py:3205-3218`) and `POST /api/coordination-experiments` (`api.py:3245-3260`) take **zero request body** — both call frozen, parameterless functions against hardcoded `coordination_decision` fixtures (`experiments/composite_agency.py:157`; `experiments/coordination_experiment.py`). A user-authored scenario cannot be run through either endpoint today. | Design A below — real backend work, first slice fully specified. |
| Levin analysis lens | `build_levin_reference_readout()` (`analysis/theory_analysis.py:881`) is already a pure function over a theory-neutral bundle plus a retained execution result — no live model call, no execution hook. But it targets the **V1** bundle contract and `coordination_decision`-specific event/fact names (`meeting_wake_recorded`, `commitment_recorded`, etc.), not the **V2** contract (`RunEvidenceBundleV2`/`AnalysisSpecV2`) the post-hoc `POST /api/runs/{run_id}/analyses` mechanism actually reads (`api.py:4547`, `analysis_service.py:702`). | Design B below — real but bounded port, first slice fully specified. |

`_waltzman_findings` (`analysis_service.py:225`) — the function this slice's
Levin work is modeled on — reads **generic** V2 evidence kinds
(`information_lineage`, `participant_activation`, `causal_event`), not
scenario-specific field names. This was confirmed by re-examining a live
finding from 2026-08-18's testing: a Waltzman-lens attachment on a thin
2-person "community garden" scenario returned mostly-empty calculated
findings, which looked like a possible bug at the time. Re-reading the
implementation shows it is not — the logic is scenario-agnostic; a richer
scenario (Slice 29F's 4-person, 27-node relief-port proof case) produced real
non-empty findings from the identical code path. The lesson for this slice:
**Levin's V2 port must follow the same generic pattern**, not a literal
translation of V1's `coordination_decision`-specific field names, or it will
inherit the same "meaningless on most scenarios" property Waltzman's lens
avoided by design.

## Objective

1. Give a user-approved `general_simulation` scenario a way to run under
   multiple controlled conditions without re-authoring it (Design A).
2. Make Levin available through the same isolation-preserving, attach/remove
   mechanism Waltzman already uses (Design B).
3. Record graph-projection/boundary-collapse (Design C) and pause/stop/resume
   as explicitly blocked follow-ups with their exact blocking condition named,
   so they are not silently dropped.

## Non-goals

- Retiring or deleting `web/`. It remains the only surface for the
  capabilities this slice does not close (Design C, pause/resume, the
  legacy structured-authoring templates). No file removal in this slice.
- Migrating `web/`'s unique scenario types (`service_desk`, `physical_access`,
  `purchase_payment`, `regional_outbreak`) to `general_simulation`.
- A generalized `ExperimentSpec` covering declared scenario perturbations
  (ADR-014's "targeted vs. broadcast" example). This slice's Experimentation
  scope is RunSpec-level conditions only (§ Design A, Slice A1); perturbation
  conditions are a named follow-up (§ Design A, Slice A2).
- Deciding whether `general_simulation`'s world model should grow a
  boundary/grouping concept at all (Design C is a human decision, not an
  engineering estimate, per `bounded-design`'s handling of
  `human_decision_required` items).

## Governing authority

- ADR-014 already commits to the Experiment authority this slice implements:
  *"`ExperimentSpec` will own controlled variations, forks, repetitions,
  matching, and cross-run comparisons... General experiment execution remains
  outside this refactor, but the new contracts must preserve the seam."*
  This slice does not create a new architectural decision; it exercises an
  already-adopted one that Plan 029 explicitly deferred.
- Plan 029 (lines 386-399) already sketches the `ExperimentSpec` field list
  this design's contract matches: `experiment_id`, `base_scenario_digest`,
  `conditions[]`, `repetitions_per_condition`, `analysis references`. Design
  A below is a narrowed, fully-specified first slice of that sketch, not a
  competing design.

## Design A — Experimentation (RunSpec-level conditions)

### Domain contract

```
ExperimentSpec:
  experiment_id: str
  base_scenario_digest: str        # pins the approved ScenarioSpec; proves it is untouched
  conditions: list[ExperimentCondition]
  repetitions_per_condition: int = 1

ExperimentCondition:
  condition_id: str
  label: str
  run_overrides: RunLlmOptions     # model / agent_reasoning_effort / max_total_cost only — no scenario field

ExperimentResult:
  experiment_id: str
  base_scenario_digest: str
  conditions: list[ExperimentConditionResult]

ExperimentConditionResult:
  condition_id: str
  repetition_index: int
  run_id: str
  run_evidence_bundle_digest: str
  status: Literal["completed", "failed"]
  error: str | None
```

### Boundary rule

Experimentation consumes an **already-approved** `draft_id`/scenario. It may
select `RunLlmOptions` per condition (the same typed object `resolve_live_configuration`
already validates for a single run) and nothing else. It has no write access
to `ScenarioSpec`, `AuthoredSimulationBundleV2`, or the draft's proposal —
enforced structurally by the endpoint never accepting a scenario-shaped field,
not by convention.

### Endpoint

`POST /api/authoring/drafts/{draft_id}/experiments`

Request:
```json
{
  "conditions": [
    {"condition_id": "medium-reasoning", "label": "Medium reasoning", "run_overrides": {"model": "openrouter/openai/gpt-5.6-sol", "agent_reasoning_effort": "medium", "max_total_cost": 0.74}},
    {"condition_id": "low-reasoning", "label": "Low reasoning", "run_overrides": {"model": "openrouter/openai/gpt-5.6-sol", "agent_reasoning_effort": "low", "max_total_cost": 0.74}}
  ],
  "repetitions_per_condition": 1
}
```

Response: `202` with `experiment_id` and `job_id` (reuses the existing
background-job/poll pattern `run_approved_draft` already uses — conditions
execute sequentially, sharing the existing single-live-run lock, since
concurrent live execution is out of scope for this slice).

### Acceptance

- All `conditions × repetitions_per_condition` runs complete (or fail
  individually) against the identical `base_scenario_digest`.
- Every completed condition's retained `llm_configuration.model` matches its
  requested `run_overrides.model`.
- The experiment record links every `run_id` it produced; each run remains
  independently readable through the existing `/api/runs/{run_id}/summary`
  and independently analyzable through the existing (unmodified)
  `/api/runs/{run_id}/analyses`.

### Failure behavior

- Draft not `approved` → `422`, no experiment record created.
- A condition's `run_overrides.model` not in `authoring_model_ids()`/
  `model_catalog()` → `422` naming the exact `condition_id`, before any
  condition executes.
- One condition's run failing does not stop the remaining conditions
  (isolated per-condition failure, matching `ExperimentConditionResult.status`
  — no all-or-nothing rollback).

### Fixtures

- Positive: 2 conditions, same model, `medium` vs `low` reasoning effort —
  both complete, both retain the correct `agent_reasoning_effort`, both share
  `base_scenario_digest`.
- Negative — unapproved draft: `422`, no experiment record, no run created.
- Negative — uncertified model in one condition: `422` naming that
  `condition_id`; the other (valid) condition is never started.

### Slice A2 (named, not specified) — declared scenario-perturbation conditions

Per ADR-014's own example ("targeted versus broadcast information conditions
are experiment configuration"), a future slice extends `ExperimentCondition`
with **declared, pre-authored perturbation toggles** — switches the Configure
step marks as experimentable at authoring time. Experimentation still never
free-edits the scenario; it only selects among switches Configuration already
declared. This requires new authoring-side schema (a `perturbable: true` flag
on eligible scenario elements) and is explicitly out of this slice's scope.

## Design B — Levin as a real `AnalysisSpecV2` profile

### Domain contract

Reuses the existing `AnalysisSpecV2`/`AnalysisResultV2`/`AnalysisFindingV2`
contracts unchanged — no schema changes. Adds one new `profile` value,
`levin_collective_competence_v1`, and one new dispatch branch in
`analyze_run_evidence_v2` (`analysis_service.py:726`), parallel to the
existing `waltzman_coordination_v1` branch.

### First-slice construct scope (thin, not the full V1 seven-construct set)

Two constructs, both derived generically from V2 evidence kinds (mirroring
`_waltzman_findings`'s pattern, not V1 Levin's `coordination_decision`-specific
field names):

1. **`levin_goal_progress`** — reads `terminal_state` + `completion` evidence
   records; reports accepted vs. rejected transition counts and terminal
   status, generically (no scenario-specific goal-ref lookup required for
   this first slice — `exact_outcome_v1`'s existing `terminal_outcome`
   construct already proves this data is generically present).
2. **`levin_coordination_activity`** — reads `causal_event` +
   `participant_activation` records; reports, per moment, how many actors
   held/deferred vs. attempted a validated transition (the generic analogue
   of V1's crossing/episode counts), without requiring a
   scenario-specific boundary reference.

Remaining V1 constructs (collective glue, error correction, persistence/
adaptation, untested capacities) are a named follow-up once this shape is
proven against a real run, not part of this slice.

### Acceptance

- `POST /api/runs/{run_id}/analyses` with `profile: "levin_collective_competence_v1"`
  returns a non-empty, `coverage_status: "supported"` result on a completed
  `general_simulation` run with at least one committed transition.
- Isolation: attaching or removing the Levin analysis changes
  `participant_model_calls`, canonical revision, and evidence digest by
  exactly zero — verified with the same before/after comparison already
  proven for Waltzman today (`participant_model_calls` unchanged across
  attach/remove/re-attach on `run_adb0f3e326ee`).

### Failure behavior

Identical to the existing `analyze_run_evidence_v2` contract: missing
required evidence kinds → `coverage_status: "unsupported"`, `missing_evidence`
lists exactly which kinds were absent — no exception, no partial mutation.

### Fixtures

- Positive: the retained community-garden run (`run_adb0f3e326ee`, already on
  the live deployment) — has `causal_event`, `participant_activation`,
  `terminal_state` records; expect non-empty findings.
- Negative: a run evidence bundle missing `causal_event` records entirely →
  `coverage_status: "unsupported"`, no exception raised.

## Design C — graph projection / boundary collapse for `general_simulation` (blocked)

**Not specified further in this document.** `human_decision_required`:
`general_simulation`'s Concordia-based world model may not have an
equivalent of the older ADR-006/ADR-008 "analytical boundary" concept at
all — porting `web/`'s collapse control could mean forcing an ontology that
doesn't fit, not just missing UI. Resume trigger: Brian decides whether
`general_simulation` should grow a boundary/grouping concept, and if so what
it means for a Concordia-authored world specifically. Until then, the
rendering engine's existing `collapsedBoundaryId`/`viewMode` options remain
unused by `public/waltzman/app.js`, which is correct given there is
currently no data to drive them.

## Verification

- `mypy --strict` clean (matches the rest of the repo's current state).
- Existing full suite must still pass at the same pre-existing-failure
  baseline (10 known failures, unrelated to this slice, documented in prior
  session evidence — no new failures introduced).
- Design A: fixtures above, run against the real deployment where feasible
  (matches this project's existing practice of authentic-trace verification
  over mocked-only tests for LLM-touching paths).
- Design B: fixtures above; explicit isolation-receipt check reusing the
  pattern already proven for Waltzman.

## Status

- Design A (Experimentation, Slice A1): specified above, ready to implement.
- Design B (Levin analysis profile): specified above, ready to implement.
- Design A Slice A2 (perturbation conditions): named, not specified.
- Design C (graph projection/collapse): blocked on a human decision, not
  specified further.
- Pause/stop/resume for `general_simulation`: named as a gap, not specified;
  needs an execution-loop-interruptibility exploration pass before any
  further design.
