---
doc_role: implementation_plan
authority: bounded_design
status: implemented
created: 2026-10-08
updated: 2026-10-08
plan_id: "cybernetic_influence_v3#40"
depends_on:
  - docs/ROADMAP.md
  - docs/adr/013-generalized-simulator-foundation.md
  - docs/adr/014-separate-simulation-and-analysis-authority.md
  - docs/adr/017-replacement-first-simulation-platform.md
---

# Slice 40: System model of the repository

## Gap

**Current:** No model of what this system stores, which code writes each record, which kinds of things an author can declare, or what each view shows. Questions such as "can a relationship affect a run?" or "where are saved drafts listed?" were answered by reading code each time.

**Target:** Company Planning's system-model artifacts (`references/system-model.md`, default since 2026-10-06): `docs/model/ODD.md`, the machine-readable twin `docs/model/cybernetic_influence_model.toml`, `docs/model/VIEW_COVERAGE.md`, and a drift test `tests/test_system_model.py` that parses the code with `ast` and fails when a record writer, API route, authoring-schema class or vocabulary value changes without the model.

**Why:** Another repository's model (World Substrate) is to be compared against this one kind by kind; that needs the world-definition schema listed with its defining classes, and kept true by a test.

## User Outcome

A person or agent can open `docs/model/ODD.md` section 4 and see every kind of thing a Cybernetic Influence world can contain, with the class that defines it and what it becomes at run time, and trust it because `make check` fails when the code drifts.

## Canonical Behavioral Example

**Starting input/state:** commit `16b1791`.

**Action:** rename the experiment record's writer `persist` in `api.py` and run `pytest -q tests/test_system_model.py`.

**Expected observable result:** the test fails with `record 'experiment_record': ExperimentStore is written in code at sites the model does not declare` naming `('src/cybernetic_influence/api.py', 'persist_experiment')`; reverting restores 9 passed.

**Behavioral evidence:** observed (2026-10-08, see PR).

**Failure signal:** the renamed writer passes the test.

## Scope boundary

Documentation and one test only. No runtime, API, UI, prompt or evidence behavior changes, so ADR-017's gate on new simulator capability is not touched. Gaps found are recorded in `VIEW_COVERAGE.md` (G1-G16), not fixed here.

## References Reviewed

- `src/cybernetic_influence/general_simulation/authoring_models.py`, `contracts_v2.py`, `study_models.py`, `models.py`, `compiler.py`, `runner.py`, `world.py`, `concordia_runtime.py`, `projection.py`
- `src/cybernetic_influence/authoring/store.py`, `run_store.py`, `experiment_store.py`, `public_spend_controls.py`, `api.py`, `public_waltzman.py`
- `public/waltzman/app.js`, `web/app.js`
- `~/code/world-substrate/docs/model/` and `tests/test_system_model.py` (worked example)
