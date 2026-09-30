---
doc_role: implementation_plan
authority: bounded_design
status: access_gated
created: 2026-09-30
updated: 2026-09-30
plan_id: "cybernetic_influence_v3#39"
---

# Slice 39: Simudyne replacement trial

## Outcome

Determine whether **Simudyne Nexus + Agentic Simulation Lab Python SDK** can replace Cybernetic Influence V3's generalized simulation platform on the retained regional-outbreak coordination case.

This is a deletion/adoption gate, not a migration exercise.

## Hard rule

The trial may read retained Cybernetic Influence case inputs/results for comparison.

It may **not** import or invoke:

- `cybernetic_influence.active_runtime`;
- `cybernetic_influence.causal_core`;
- `cybernetic_influence.general_simulation`;
- CI authoring/compiler/runtime/experiment stores;
- CI replay infrastructure.

If the external trial secretly delegates to those layers, it proves nothing.

## Frozen case

Use the twelve-participant outbreak-response probe because it is small enough to reproduce and exercises the relevant stack.

### Participants

- Alba epidemiologist, policy delegate, operations lead;
- Borin epidemiologist, policy delegate, operations lead;
- Cyrenia epidemiologist, policy delegate, operations lead;
- regional coordinator, scientific adviser, logistics coordinator.

### Round structure

Three decision rounds.

Each participant returns structured:

- `decision`: support / conditional / defer / oppose;
- `primary_risk`;
- `requested_next_step`;
- rationale.

### Hard coalition decision rule

Final approval requires:

- at least 6 `support`;
- at least 9 `support + conditional`;
- no more than 1 `oppose`.

The rule is deterministic model logic, not an LLM judgment.

### Conditions

1. **baseline** — common retained round snapshot only;
2. **responsive_capacity_pressure** — common snapshot plus declared country-specific capacity developments after a round;
3. **capacity_pressure_plus_stabilization** — pressure replay plus the declared feasible allocation package.

Run at least two independent executions per condition.

The original historical outcomes are comparison evidence, not required targets. A replacement is allowed to produce different LLM trajectories if its mechanics/inputs differ transparently.

## Stage 0 — access

Required before implementation:

- authentic Nexus / `abm-lab` trial or licensed package access;
- ability to run locally or in an approved trial environment;
- documentation/API version recorded.

Do not emulate Nexus locally and call that the trial.

## Stage 1 — authoring test

Start from this research question in Nexus:

> Model a twelve-person regional outbreak-response coalition deciding whether to launch a joint response over three rounds. Participants have role-specific priorities. After each round, later conditions may receive targeted capacity developments; a stabilization condition later receives a feasible regional allocation package. Measure whether the coalition meets an explicit deterministic approval rule, how decisions and requested resources change, and retain participant-level rationales.

Record:

- models/templates Nexus retrieves;
- selected starting template;
- CMS before and after refinement;
- mechanisms/constraints added manually;
- generated Python model;
- any generated feature/validation targets;
- every place custom source code was required.

The point is to measure how much authoring infrastructure Nexus replaces.

## Stage 2 — execution model

Prefer native SDK primitives:

- `LLMAgent` or `HybridAgent` for participants;
- rule-based agents/processes for exercise control and stabilization;
- Links/Messages for participant-specific delivery;
- SDK parameters for condition and repetition;
- deterministic model function for coalition approval;
- standard recorder/checkpoint facilities.

Do not reproduce CI's generic world/transaction abstraction unless the Simudyne model genuinely cannot express the required case without it.

## Stage 3 — matched experiment

For each condition:

- run 2+ executions;
- retain seed/model-response-cache identity;
- retain participant decisions/rationales;
- retain delivered pressure/stabilization messages;
- compute final coalition rule;
- count resource requests;
- record run-level outcome.

Use native experiment/Monte Carlo tooling where available.

## Stage 4 — inspection

Minimum usable evidence:

- model/configuration visible;
- assumptions visible;
- participant-level outputs recoverable;
- condition and seed/repetition identity recoverable;
- final metrics linked to the run;
- enough output to explain why the deterministic coalition gate passed or failed.

A bespoke CI-style replay UI is **not** required for replacement success.

## Stage 5 — code disposition audit

Classify every local file needed by the trial as one of:

- `case_model` — outbreak-specific model logic;
- `domain_analysis` — Waltzman or other genuinely domain-specific interpretation;
- `adapter` — thin external integration;
- `generic_infrastructure` — simulation/authoring/experiment/replay/lifecycle machinery.

### Pass

Replacement gate passes if:

- Simudyne owns agent execution and scheduling;
- Simudyne owns communication/topology primitives;
- Simudyne owns experiment repetition/evaluation;
- Simudyne owns run recording/checkpoint/model lifecycle;
- Nexus materially reduces model-authoring infrastructure;
- no local `generic_infrastructure` is needed beyond thin integration;
- no CI runtime is invoked.

On pass:

1. stop Concordia parity migration;
2. identify overlapping CI modules for archive/retirement;
3. preserve only domain models, analyses, evidence, and required adapters;
4. do not port features merely for compatibility.

### Conditional pass

If the generic simulator is replaced but one narrow CI capability is genuinely useful—e.g. a theory-specific evidence projection—retain only that capability as an adapter/analysis package.

### Fail

Failure requires a concrete blocking observation, such as:

- participant-local information cannot be expressed;
- hard deterministic rule/refusal cannot coexist with LLM agents;
- required condition/repetition design cannot be represented;
- retained evidence is insufficient for the actual research question;
- platform licensing/deployment makes the intended workflow operationally unacceptable.

A different API style or less elegant architecture is not failure.

## Comparative fallback

If Simudyne access cannot be obtained, record **access failure**, not semantic failure.

Then:

- run the same case on Concordia using the already adopted foundation;
- if LLM residents are unnecessary, evaluate GAMA before expanding Concordia;
- if conventional multi-method enterprise simulation is the actual need, evaluate AnyLogic before adding CI capabilities.

## Evidence receipt

The final trial record must state:

- Simudyne/Nexus version;
- access/license mode;
- environment;
- original research prompt;
- selected template/CMS;
- generated model hash;
- local custom files and disposition;
- conditions/seeds;
- result table;
- limitations;
- replacement verdict;
- exact CI modules proposed for retirement or the exact blocker preventing replacement.
