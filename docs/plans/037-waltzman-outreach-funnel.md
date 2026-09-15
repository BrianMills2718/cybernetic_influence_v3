---
doc_role: implementation_plan
authority: bounded_design
status: implemented
created: 2026-09-09
updated: 2026-09-09
depends_on:
  - ../ROADMAP.md
  - ../GOAL.md
  - ../adr/014-separate-simulation-and-analysis-authority.md
  - 029-separate-simulation-run-analysis.md
plan_id: "cybernetic_influence_v3#37"
dependencies: ["cybernetic_influence_v3#29"]
dependency_evidence:
  "cybernetic_influence_v3#29": "- 029-separate-simulation-run-analysis.md"
dependencies_reviewed: "2026-09-15"
---

# Slice 37: Waltzman outreach funnel

## Product decision

The stakeholder-facing demo is being built specifically as a continuation of the
product owner's discussion with Rand Waltzman around *From Minds to Coordination*.
The acquisition surface therefore optimizes for an expert who already cares about
how local information, cognition, constraints, and interaction aggregate into
collective organizational behavior. It is not a generic simulator tutorial.

The public demo has three attention horizons:

1. **0–30 seconds — hook:** the initial journey must make the core question
   recognizable without prerequisite reading. Desktop keeps one concrete retained
   coordination result in the first viewport; narrow mobile prioritizes the composer
   and places that proof immediately after it.
2. **30–120 seconds — participation:** the visitor must be able to start typing a
   situation of their own from that same initial journey and launch generation
   with one primary action.
3. **After commitment — depth:** only after the visitor chooses to explore should
   the workbench expose progressive review, mechanics/coverage, provenance,
   methodology, experiments, and detailed evidence.

The success condition is not that the visitor understands the whole architecture
in two minutes. It is that they understand why the problem is interesting in the
first 30 seconds and are using the system themselves within roughly two minutes.

## Fastest implementation path

Do **not** rebuild natural-language authoring or the general simulator in World
Substrate for this demo. Reuse the implemented Cybernetic Influence V3 public V2
path:

```text
ordinary language
-> retained separated scenario/run proposal
-> compiler + dependency/coverage review
-> editable approval
-> Concordia-owned fresh run
-> retained evidence + detachable analysis
```

World Substrate is the presentation donor for the next visual slice: living world,
local information visibility, constraints/resources, event animation, causal
ancestry, timeline scrubbing, and exact-history intervention/fork presentation.
This slice does not create a cross-repository runtime dependency.

## First-screen contract

The default Overview must lead with plain-language concepts:

- local information;
- people and technical systems;
- constraints and requirements;
- collective decision/action;
- what happened;
- why; and
- what if something changes.

Do not require the reader to understand World Substrate, Concordia, semantic
configuration, execution coverage, causal mechanics, or analytical lenses before
they can use the product.

The retained flagship result remains the first proof:

```text
26 ready to proceed
-> 20 of 26 conditional after locally relevant concerns
-> 26 ready after one intervention addresses those conditions together
```

The point is that the collective outcome changes without requiring a false claim
to be corrected.

## Outreach authoring contract

The first screen contains a natural-language composer with one primary action:
**Build this simulation**.

That action:

1. retains exactly what the visitor typed;
2. enters the existing Create surface;
3. uses the existing `configure` authoring mode immediately;
4. tells the model to make reasonable assumptions explicitly rather than forcing
   a clarify/configure choice before the visitor has seen value; and
5. leaves the ordinary clarifying conversation available as an optional deeper
   path in the full Create view.

No model selector, workflow selector, analysis selector, raw JSON, or methodology
choice belongs in this first interaction.

## World Substrate living-view adapter boundary

The next visual slice should consume retained Cybernetic V3 run projections rather
than rerun the simulation. The adapter should map only presentation semantics:

| Cybernetic V3 retained surface | Living-view presentation |
| --- | --- |
| people / active systems | residents / active nodes |
| world records / resources / places | world objects, constraints, resources |
| information representations + recipients | information overlays and deliveries |
| scheduled moments | canonical timeline markers |
| accepted world operations | visible world changes |
| rejected transactions | visible failed attempts, never state changes |
| retained evidence references | click-through explanation/evidence |
| execution-parent / transition evidence | declared causal ancestry overlay |
| post-run Waltzman analysis | detachable analysis overlay |

The adapter must not convert analytical conclusions into canonical state or imply
that information delivery proves belief/persuasion.

### Existing public API seams to reuse

The current public workbench already drives the complete stakeholder lifecycle
through these same-origin routes. The living-view slice should consume these
contracts rather than invent a parallel service:

| Stage | Existing route | Use |
| --- | --- | --- |
| Start draft | `POST /api/authoring/drafts` | retain one editable authoring identity |
| Natural-language generation | `POST /api/authoring/drafts/{draft_id}/messages` with `mode=configure` | build the typed proposal from the visitor's prose |
| Generation progress | `GET /api/authoring/jobs/{job_id}` | expose retained authoring stages while the model/compilers work |
| Direct semantic edits | `PUT /api/authoring/drafts/{draft_id}/general-proposal` and existing scoped editors | change people/world/information/run values without another model call |
| Approval | `POST /api/authoring/drafts/{draft_id}/approve` | freeze the reviewed typed configuration |
| Fresh execution | `POST /api/authoring/drafts/{draft_id}/runs` | start the existing live general-world run |
| Run progress | `GET /api/runs/{run_id}/progress?include_projection=false` | show live call/stage progress without requiring a streaming protocol |
| Retained presentation | `GET /api/runs/{run_id}/summary` | current generated walkthrough/replay source and primary living-view adapter input |
| Raw evidence | `GET /api/runs/{run_id}` | deeper event/state/provenance inspection when the summary projection is insufficient |
| Detachable lenses | `POST /api/runs/{run_id}/analyses` / `DELETE /api/runs/{run_id}/analyses/{analysis_id}` | add/remove Waltzman or other analysis without rerunning the world |

The next slice should first prove that one retained general-world `summary` can be
projected into the living view. Only request raw run evidence for fields the summary
does not retain. Do not make a live streaming transport a prerequisite; polling is
already an implemented, comprehensible path.

## Acceptance

- [x] The default initial journey names *From Minds to Coordination* and states the
      local-information-to-collective-action question in plain language.
- [x] The retained 26 -> 20 -> 26 trajectory is visible without navigating; it
      shares the first viewport with the composer on desktop and follows the composer
      on narrow mobile.
- [x] A natural-language input and **Build this simulation** are present on the
      default Overview; a visitor does not need to find the New Simulation tab.
- [x] The outreach action routes directly to the existing `configure` authoring
      mode; clarifying questions remain available only as an optional deeper path.
- [x] The existing World/People/Information/Processes/Run/Analysis review,
      approval, fresh-run, retained replay, experiments, evidence, and methodology
      capabilities remain reachable.
- [x] No new simulation engine, scenario-specific runtime, or cross-repository
      executable dependency is introduced.
- [x] Public UI tests assert the acquisition controls and the configure-first
      handoff.
- [x] `make check` passes before merge.


## Verification

Final local verification on 2026-09-09:

- `make check`: 470 tests passed; strict mypy, wait-pattern check, frontend build, served-bundle parity, and deploy syntax all passed.
- `pytest -q tests/test_public_waltzman.py`: 19 focused public-surface tests passed.
- `check_primary_controls_visible.py`: 130 primary-control placements passed across 390, 768, 1024, 1280, 1366, 1440, 1512, 1600, 1728, and 1920 pixel widths.
- Real Chromium geometry checks at 1440x1000, 1280x800, and 390x844 showed no horizontal overflow, console errors, failed requests, or automatic tour overlay; the outreach textarea and Build action were fully visible.
- Page claims remained consistent with retained CSO/evasion evidence.

## Stop condition

Stop this slice once the funnel is implemented and verified. Do not expand the
mechanics language or migrate the runtime to World Substrate in order to improve
the first two minutes. The next slice may implement the retained-run-to-living-view
adapter after this acquisition surface is stable.
