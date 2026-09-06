---
doc_role: implementation_plan
authority: bounded_design
status: implemented
created: 2026-08-23
updated: 2026-09-06
depends_on:
  - docs/ROADMAP.md
  - docs/research/001-from-minds-to-coordination.md
  - docs/adr/012-decision-environment-measures-are-derived.md
  - docs/adr/014-separate-simulation-and-analysis-authority.md
---

# Slice 31: make the flagship case the run that exercises the source framework

## Why

The operator asked whether the public case study would impress the paper's
author. Two reviews were run in fresh contexts, given only a URL and neutral
questions, with no hypotheses supplied. They converged.

The current flagship forks one execution four ways, varying a resource package
delivered identically to all 26 officials. That is broadcast logic, which the
paper's section 5.1 defines adaptive interaction *against*. Its four arms end
identically -- across 104 agent-decisions there is not one `support` and not one
`oppose` against a gate requiring 13 unconditional supports -- so "the group
remains blocked" is arithmetic rather than a finding. The pre-fork state
`{conditional: 23, defer: 3}` is retained in the evidence file and referenced
zero times in the frontend, so the one directional reading available is invisible.

Meanwhile `run_5010214f2466` (condition `adaptive_cso_stabilization`, 26
officials, 89 model calls, completed) does what the paper describes:

- four differentiated pressure sources -- community, legal, logistics,
  technical -- that change behaviour between rounds rather than repeating
  (`round_1:*:verify` then `round_2:community_pressure_source:escalate`);
- a measured shift from 26 `support` to 20 `conditional`, which is section
  3.1's move from implicit to conditional trust, with no false claim anywhere
  in the run;
- a Cognitive Security Operations chain implementing section 6 by name --
  monitor emits `coordination_readiness: blocked`, diagnostician emits
  `incompatible_requirements / cross_dimension / coalition_wide`, planner emits
  `cross_domain_compact`;
- recovery to 26 `support` and `joint_response_approved`, which is section
  5.3's "recovery may require active intervention rather than passive
  stabilization".

The case study already renders this run's network on step 1 while reporting a
different run's results on steps 4 to 6. Re-cutting removes that split.

The clearest-reading alternative is rejected on evidence, not taste: the
five-run set behind the older lab is the one a 2026-08-05 audit found disclosed
the condition identifier in participant prompts, so it cannot support
matched-condition inference.

## Scope

Public projection and case-study presentation only. No runtime, scenario,
prompt, or execution change. No new model calls: every number shown is already
retained in `run_5010214f2466`.

## Design

`scripts/build_cso_case_public.py` projects the retained run into
`public/waltzman/cso-case.json`: per-round decision, risk and request tallies so
direction is visible rather than one end state; the ordered CSO chain; the
source injects; and six paired rationales -- the same named official's retained
words while blocked and again after the compact, chosen to span countries and
roles rather than to flatter the result. No prompts are projected.

The six chapters become: the world; the coordination problem; the pressure; what
changed across three rounds plus which conditions moved; the same officials
before and after in their own words; and the detect/diagnose/stabilize chain.

## Acceptance

- The case study reports the run whose network it displays.
- Direction is visible: three rounds, not one end state.
- The paper's three variables appear by name, labelled as derived analyst views
  over retained evidence (ADR-012), never as hidden causal state.
- Analysis remains read-only over retained evidence and changes no model call,
  world revision, or evidence digest (ADR-014).
- The retained nonclaims survive: one execution, unseeded sampling,
  scenario-authored controls.

## Non-goals

- Re-running or re-executing anything.
- The evasion space (paper section 7); it is untested here and stays that way.
- Retiring the resource-fork projection, which remains retained evidence.
